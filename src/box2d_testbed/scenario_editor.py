"""The panel that edits scenario source and reloads it into the running app."""

import re

from imgui_bundle import imgui, imgui_color_text_edit, imgui_ctx

from .base_test import BaseTest
from .scenario_loader import LoadError, loader, source_path_hint
from .scenario_store import (
    BuiltinStore,
    ScenarioRef,
    StoreError,
    UserStore,
    template_for,
    user_scenario_dir,
)
from .testbed_state import state

TextEditor = imgui_color_text_edit.TextEditor


def set_python_language(editor) -> None:
    """Turn on Python highlighting, whichever binding version this is.

    ImGuiColorTextEdit's Python API was reworked during imgui_bundle 1.92:
    ``set_language(TextEditor.Language.python)`` today, and
    ``set_language_definition(TextEditor.LanguageDefinitionId.python)`` before
    that -- which is the version Pyodide pins, so the browser build needs the
    older spelling. Same problem as add_polyline in debug_draw_imgui, and the
    same fix: ask the binding what it has rather than assume.
    """
    language = getattr(TextEditor, "Language", None)
    if language is not None and hasattr(editor, "set_language"):
        # Language.python is a static factory here, not an enum member -- and
        # the older API's LanguageDefinitionId.python is the other way round.
        python = language.python
        editor.set_language(python() if callable(python) else python)
        return
    identifiers = getattr(TextEditor, "LanguageDefinitionId", None)
    if identifiers is not None and hasattr(editor, "set_language_definition"):
        python = identifiers.python
        editor.set_language_definition(python() if callable(python) else python)
        return
    # Highlighting is a nicety; an editor without it still edits.
    print("scenario editor: no Python highlighting in this imgui_bundle")


def python_editor(line_numbers: bool = True, language: bool = True):
    """A text widget set up for Python.

    Shared with the console, whose prompt is a small one of these: both want the
    same highlighting, the same four-space indent, and the same answer to the
    binding-version question above.

    Args:
        line_numbers: Off for the console, where a prompt does not need them.
        language: Off for the console's transcript, which is output rather than
            source -- highlighting a traceback as if it were code reads oddly,
            and the plain palette leaves room to mark the error lines red.
    """
    editor = TextEditor()
    if language:
        set_python_language(editor)
    editor.set_show_line_numbers_enabled(line_numbers)
    editor.set_tab_size(4)
    editor.set_insert_spaces_on_tabs(True)
    editor.set_auto_indent_enabled(True)
    # A dot in every space is unreadable in Python, which is nothing but
    # leading whitespace. Tabs stay visible: one in an indented block is worth
    # seeing, since it is what a stray copy-paste brings in.
    editor.set_show_whitespaces_enabled(False)
    editor.set_show_tabs_enabled(True)
    return editor


#: A scenario's declared name, in the class header that registers it. The
#: negated character class crosses newlines, so a header wrapped over several
#: lines is still found.
_CLASS_NAME = re.compile(r"""(^class\s+\w+\s*\([^)]*?name\s*=\s*)(["'])(.+?)\2""", re.M)


#: A relative import, which is what the builtins use to reach their own
#: package. Only ever ``from .base_test``, ``from .shared`` and ``from .human``
#: in practice, but the pattern does not need to know that.
_RELATIVE_IMPORT = re.compile(r"^(\s*from\s+)\.(?=\w)", re.M)


def rewrite_relative_imports(source: str) -> str:
    """Spell a builtin's imports the way a standalone file has to.

    ``from .base_test import BaseTest`` works inside the package and nowhere
    else: a scenario file is executed on its own, so the leading dot resolves
    to a package that holds no modules. Forking rewrites it, which also leaves
    a file that still works if it is copied into a project of your own.
    """
    return _RELATIVE_IMPORT.sub(r"\1box2d_testbed.", source)


def taken_names() -> set:
    """Every scenario name currently registered, in any category."""
    return {name for tests in BaseTest.registry.values() for name in tests}


def rename_scenarios(source: str, taken: set) -> tuple:
    """Rename the scenarios a forked file declares.

    A scenario is registered under the name in its class header, so a copy that
    keeps that name does not appear beside the original -- it replaces it, and
    deleting the copy then takes the original out of the panel too. Forking
    renames instead, which is nearly always what was wanted anyway: the copy
    and the thing it was copied from, side by side.

    Returns:
        tuple: (source, the new names) -- an empty list if nothing matched.
    """
    renamed = []

    def replace(match):
        base = f"{match.group(3)} copy"
        name, suffix = base, 2
        while name in taken:
            name, suffix = f"{base} {suffix}", suffix + 1
        taken.add(name)
        renamed.append(name)
        return f"{match.group(1)}{match.group(2)}{name}{match.group(2)}"

    return _CLASS_NAME.sub(replace, source), renamed


class ScenarioEditor:
    """Open, edit, save and reload scenario files.

    Saving is what loads: a file is written, executed, and the scenario it
    defines replaces the one the previous save registered, with the world
    rebuilt around it. So the loop is edit, ctrl-S, watch.
    """

    def __init__(self, app):
        self.app = app
        self.builtin_store = BuiltinStore()
        self.user_store = UserStore(user_scenario_dir())
        self.editor = python_editor()

        self.ref: ScenarioRef = None
        #: The buffer as it was last read or written, which is what "unsaved
        #: changes" is measured against.
        self.loaded_text = ""
        self.message = ""
        self.message_is_error = False
        self.error_detail = None
        self._confirm_delete = False

    @property
    def mono_font(self):
        """The font code is shown in, once the app has loaded one.

        Read off the app each frame rather than held: the panel is built before
        there is a font atlas to load into. None means "leave the font alone",
        which is what imgui_ctx.push_font takes it as.
        """
        return getattr(self.app, "mono_font", None)

    # -- files ---------------------------------------------------------------

    def refs(self):
        """Everything openable: the user's scenarios first, then the builtins."""
        return self.user_store.refs() + self.builtin_store.refs()

    @property
    def dirty(self) -> bool:
        """Whether the buffer differs from what was last read or written.

        Compared as text rather than tracked as a flag: the editor's undo index
        would be cheaper, but it is reset by set_text, so a buffer replaced
        wholesale -- which is how a scenario arrives from anywhere but the
        keyboard -- would look saved when it is not.
        """
        return self.ref is not None and self.editor.get_text() != self.loaded_text

    def open(self, ref: ScenarioRef) -> None:
        """Show a scenario's source, discarding whatever was in the buffer."""
        try:
            source = ref.read()
        except StoreError as exc:
            self._say(str(exc), error=True)
            return
        self.ref = ref
        self.editor.set_text(source)
        self.editor.set_read_only_enabled(not ref.writable)
        # What the editor made of it, not what was handed to it: it normalises
        # line endings and the trailing newline, and the difference would read
        # as an unsaved change the moment the file was opened.
        self.loaded_text = self.editor.get_text()
        self.editor.clear_markers()
        self._say(
            f"{ref.label}"
            + ("" if ref.writable else "  --  read-only; Fork it to make changes")
        )

    def open_current_scenario(self) -> None:
        """Open the file behind the scenario that is running."""
        if state.current_test_cls is None:
            return
        name = source_path_hint(state.current_test_cls)
        if name is None:
            self._say("cannot tell which file that scenario came from", error=True)
            return
        for ref in self.refs():
            if ref.name == name:
                self.open(ref)
                return
        self._say(f"no scenario file named {name}", error=True)

    def new(self) -> None:
        """Create a scenario from the template and open it."""
        try:
            name = self.user_store.free_name("untitled")
            ref = self.user_store.write(name, template_for(name))
        except StoreError as exc:
            self._say(str(exc), error=True)
            return
        self.open(ref)
        self.load()

    def fork(self) -> None:
        """Copy what is open into the user's own scenarios, and open that."""
        if self.ref is None:
            return
        source = rewrite_relative_imports(self.editor.get_text())
        source, renamed = rename_scenarios(source, taken_names())
        try:
            name = self.user_store.free_name(f"{self.ref.name}_copy")
            ref = self.user_store.write(name, source)
        except StoreError as exc:
            self._say(str(exc), error=True)
            return
        self.open(ref)
        self.load()
        # Only over a message that is not a complaint: a fork that will not
        # load has something more useful to say than what it was renamed to.
        if renamed and not self.message_is_error:
            self._say(
                f"forked to {ref.label}, as {', '.join(renamed)} -- renamed so the "
                "copy sits beside the original instead of replacing it"
            )

    def save(self) -> None:
        """Write the buffer, then load it."""
        if self.ref is None or not self.ref.writable:
            return
        source = self.editor.get_text()
        try:
            self.ref.store.write(self.ref.name, source)
        except StoreError as exc:
            self._say(str(exc), error=True)
            return
        self.loaded_text = source
        self.load()

    def revert(self) -> None:
        if self.ref is not None:
            self.open(self.ref)

    def delete(self) -> None:
        """Remove the open scenario, and whatever it had registered."""
        if self.ref is None or not self.ref.writable:
            return
        name = self.ref.name
        try:
            self.ref.store.delete(name)
        except StoreError as exc:
            self._say(str(exc), error=True)
            return
        was_running = state.current_test_cls in loader.classes_for(name)
        loader.unload(name)
        self.ref = None
        self.editor.set_text("")
        if was_running:
            self._select_any_scenario()
        self._say(f"deleted {name}.py")

    # -- loading -------------------------------------------------------------

    def load(self) -> None:
        """Execute the buffer and put what it defines on screen."""
        if self.ref is None:
            return
        source = self.editor.get_text()
        path_for = getattr(self.ref.store, "path_for", None)
        filename = str(path_for(self.ref.name)) if path_for else None

        self.editor.clear_markers()
        try:
            classes = loader.load_source(self.ref.name, source, filename=filename)
        except LoadError as exc:
            self._show_load_error(exc)
            return

        self._say(f"loaded {', '.join(cls.name for cls in classes)}")

        # What you edited is what you want to look at. If the file defines
        # several scenarios, keep the one already on screen -- by name, since
        # every load produces new class objects and identity will not match.
        running = state.current_test_cls
        state.current_test_cls = next(
            (
                cls
                for cls in classes
                if running is not None and cls.name == running.name
            ),
            classes[0],
        )
        if self.app.simulation is not None:
            # Explicitly rather than leaving update_physics to notice the class
            # changed: that only runs while the simulation is stepping, and
            # saving with it paused should still show the new scene.
            self.app.simulation.init_test()

    def _show_load_error(self, exc: LoadError) -> None:
        self._say(exc.message, error=True)
        self.error_detail = exc.detail
        if exc.line:
            red = imgui.color_convert_float4_to_u32((1.0, 0.35, 0.35, 1.0))
            self.editor.add_marker(max(exc.line - 1, 0), red, red, exc.message, "")

    def _select_any_scenario(self) -> None:
        """Move onto some scenario that exists, after deleting the current one."""
        first = BaseTest.get_first_test()
        if first is not None:
            state.current_test_cls = first
            if self.app.simulation is not None:
                self.app.simulation.init_test()

    def _say(self, message: str, error: bool = False) -> None:
        self.message = message
        self.message_is_error = error
        self.error_detail = None
        if error:
            print(f"scenario editor: {message}")

    # -- gui -----------------------------------------------------------------

    def gui(self) -> None:
        """Draw the panel. Wired in as a dockable window."""
        self._toolbar()
        self._file_picker()
        self._status()
        if self.ref is None:
            imgui.text_wrapped(
                "New starts a scenario from a template. Or pick a builtin below, "
                "read it, and Fork it to make it yours.\n\n"
                f"Your scenarios are files in {self.user_store.path}"
            )
            return
        # Ctrl-S saves, as it does everywhere. Only while this panel has the
        # keyboard, so it cannot fire while the simulation is focused.
        if (
            imgui.is_window_focused(imgui.FocusedFlags_.root_and_child_windows)
            and imgui.get_io().key_ctrl
            and imgui.is_key_pressed(imgui.Key.s)
        ):
            self.save()
        with imgui_ctx.push_font(self.mono_font, 0.0):
            self.editor.render("##source", imgui.get_content_region_avail())

    def _toolbar(self) -> None:
        if imgui.button("New"):
            self.new()
        imgui.set_item_tooltip("A new scenario in your own directory")
        imgui.same_line()

        if _button_enabled("Fork", self.ref is not None):
            self.fork()
        imgui.set_item_tooltip("Copy what is open into your own scenarios")
        imgui.same_line()

        writable = self.ref is not None and self.ref.writable
        if _button_enabled(f"Save{' *' if self.dirty else ''}", writable):
            self.save()
        imgui.set_item_tooltip(
            "Write the file, load it, and rebuild the world (Ctrl+S)"
        )
        imgui.same_line()

        if _button_enabled("Run", writable):
            self.load()
        imgui.set_item_tooltip("Load the buffer without writing it to disk")
        imgui.same_line()

        if _button_enabled("Revert", writable):
            self.revert()
        imgui.same_line()

        if _button_enabled("Delete", writable):
            self._confirm_delete = True
        self._delete_popup()

    def _delete_popup(self) -> None:
        """Deleting a file is not undoable, so it gets asked about."""
        if self._confirm_delete:
            imgui.open_popup("Delete scenario?")
            self._confirm_delete = False
        if imgui.begin_popup_modal("Delete scenario?")[0]:
            if self.ref is None:
                imgui.close_current_popup()
                imgui.end_popup()
                return
            imgui.text(f"Delete {self.ref.name}.py?")
            imgui.text_disabled(str(self.user_store.path_for(self.ref.name)))
            if imgui.button("Delete"):
                self.delete()
                imgui.close_current_popup()
            imgui.same_line()
            if imgui.button("Cancel"):
                imgui.close_current_popup()
            imgui.end_popup()

    def _file_picker(self) -> None:
        refs = self.refs()
        labels = [ref.label for ref in refs]
        current = next(
            (i for i, ref in enumerate(refs) if self.ref and ref.name == self.ref.name),
            -1,
        )
        imgui.set_next_item_width(-1)
        changed, index = imgui.combo("##file", current, labels)
        if changed and 0 <= index < len(refs):
            self.open(refs[index])

    def _status(self) -> None:
        if self.message_is_error:
            imgui.push_style_color(imgui.Col_.text, (1.0, 0.4, 0.4, 1.0))
            imgui.text_wrapped(self.message)
            imgui.pop_style_color()
            if self.error_detail and imgui.tree_node("traceback"):
                imgui.text_unformatted(self.error_detail)
                imgui.tree_pop()
        elif self.message:
            imgui.text_wrapped(self.message)
        imgui.separator()


def _button_enabled(label: str, enabled: bool) -> bool:
    """A button that is visibly unavailable rather than missing."""
    if enabled:
        return imgui.button(label)
    imgui.begin_disabled()
    imgui.button(label)
    imgui.end_disabled()
    return False
