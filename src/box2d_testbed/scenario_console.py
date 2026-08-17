"""A Python prompt with the running scenario already in scope.

The testbed's controls are the ones a scenario declared in advance. This is for
everything else: reach into the world that is running, move a body, read a
joint's force, add a shape and watch it fall. Between this and the editor, a
question about the physics can usually be answered without restarting anything.
"""

import code
import codeop
import contextlib
import io
import os
import re
import rlcompleter

from imgui_bundle import imgui, imgui_ctx

import box2d
from box2d import Vec2

from .scenario_editor import (
    TextEditor,
    add_editor_marker,
    clear_editor_markers,
    modern_text_editor,
    push_code_font,
    python_editor,
    render_text_editor,
)
from .testbed_state import state

#: Older output is dropped past this, so a loop that prints cannot grow the
#: window's memory without bound.
MAX_LINES = 2000

#: How tall the prompt is allowed to grow before it scrolls, in lines.
INPUT_MAX_ROWS = 8

#: How many completions the line under the prompt shows before it says
#: how many more there are.
MAX_COMPLETIONS_SHOWN = 12

#: The name being typed, ending at the cursor. Dots included, so the whole of
#: ``world.bod`` is handed to the completer rather than just ``bod``.
NAME_BEING_TYPED = re.compile(r"[\w.]*$")

BANNER = (
    "test, world, state and app are bound to what is running, and rebound "
    "after every rebuild. box2d and Vec2 are imported. Names you define stick "
    "around."
)

HINT = "Enter runs   Tab completes   Ctrl+R history   Up/Down recalls"


def is_complete(source: str) -> bool:
    """Whether this is a whole statement, or the start of a longer one.

    A syntax error counts as complete: the mistake is better reported than left
    sitting in a prompt that refuses to submit.
    """
    try:
        return codeop.compile_command(source + "\n", "<console>", "single") is not None
    except SyntaxError:
        return True


def should_run(source: str) -> bool:
    """Whether Enter runs what is typed, or adds another line to it.

    The rule every prompt uses: one complete statement runs, an incomplete one
    waits, and inside a block a blank line is what closes it. Which is why
    ``for body in world.bodies:`` does not run when you press Enter after it,
    and why the third Enter below runs the loop rather than extending it.

    Args:
        source: The prompt as it was *before* this Enter reached the widget.
    """
    body = source.rstrip()
    if not body:
        return False
    # split rather than splitlines: the line being typed is the text after the
    # last newline, and splitlines drops it when it is empty -- which is exactly
    # the case that means "the block was closed".
    if "\n" in body and source.split("\n")[-1].strip():
        # Inside a block, on a line with something on it: take another line.
        return False
    return is_complete(body)


class Console(code.InteractiveConsole):
    """An interactive prompt over the running testbed.

    The language side of a REPL is the standard library's: InteractiveConsole
    already buffers an unfinished block until the line that completes it,
    compiles in "single" mode so an expression's value is echoed, and formats
    tracebacks with its own frame trimmed off the top. What is added here is
    where the text goes -- a panel rather than a terminal -- and which names are
    in scope.
    """

    def __init__(self, app):
        super().__init__(locals={"__name__": "__console__"}, filename="<console>")
        self.app = app
        # (text, is_error) pairs.
        self.lines = [(BANNER, False)]
        self.history = []
        self.history_index = None
        # The prompt is a small code editor, so a block can be typed into it and
        # read back with the same highlighting the scenario editor gives it.
        self.editor = python_editor(line_numbers=False)
        # And the transcript is a read-only one, which is what makes the output
        # selectable: drag across it, double-click a word, Ctrl+C, Ctrl+F. A
        # column of text() calls looks the same and can only be read.
        self.transcript = python_editor(line_numbers=False, language=False)
        self.transcript.set_read_only_enabled(True)
        self._transcript_stale = True
        # Where the transcript ended up on screen, for the click test above.
        self._transcript_rect = None
        # Over self.locals, which rebind() updates in place, so the names on
        # offer are the ones that are actually there.
        self.completer = rlcompleter.Completer(self.locals)
        self.completions = []
        self.searching = False
        self.search_query = ""
        self._scroll_to_bottom = False
        self._focus_input = False
        # Corrected from what the footer measures each frame; this is only
        # the first frame's guess, before there is anything to measure.
        self._footer_height = 0.0

    @property
    def mono_font(self):
        """The font to show code in, once the app has loaded one."""
        return getattr(self.app, "mono_font", None)

    @property
    def input(self) -> str:
        """What is currently typed at the prompt."""
        return self.editor.get_text()

    @input.setter
    def input(self, text: str) -> None:
        self.editor.set_text(text)
        self.completions = []

    # -- evaluating ----------------------------------------------------------

    def rebind(self) -> None:
        """Point the well-known names at what is running now.

        Done before every command rather than once: the world is thrown away
        and rebuilt on reset, on a scenario change and on every save, so a name
        bound at startup would be a handle on a destroyed world within seconds.
        """
        simulation = self.app.simulation
        self.locals.update(
            test=state.current_test_obj,
            world=simulation.world if simulation is not None else None,
            state=state,
            app=self.app,
            box2d=box2d,
            Vec2=Vec2,
        )

    def submit(self, text: str) -> None:
        """Run one line of input, or hold it until the block is complete."""
        self.emit(("... " if self.buffer else ">>> ") + text)
        if text.strip():
            self.history.append(text)
        self.history_index = None
        self.rebind()
        # push appends to the buffer, compiles what is there, and runs it once
        # it is a complete statement; runcode below is where it lands.
        self.push(text)

    def submit_block(self, text: str) -> None:
        """Run everything at the prompt, however many lines it is.

        A line at a time, so the echoed transcript shows the same >>> and ...
        prompts a terminal would, and so the interpreter compiles it the way it
        would there.
        """
        for line in text.split("\n"):
            self.submit(line)
        # A block left open needs the blank line that closes it -- which a
        # terminal gets from the user pressing Enter on an empty line, and a
        # prompt that submits several lines at once has to supply itself.
        if self.buffer:
            self.submit("")

    def name_being_typed(self) -> str:
        """The name the cursor is sitting at the end of, dots included."""
        if modern_text_editor(self.editor):
            cursor = self.editor.get_main_cursor_position()
            line = self.editor.get_line_text(cursor.line)
            return NAME_BEING_TYPED.search(line[: cursor.index]).group()
        # The older binding exposes its cursor through unusable C++ output
        # parameters. Completion at the end of the prompt is still the common
        # and useful case in the browser.
        return NAME_BEING_TYPED.search(self.input.split("\n")[-1]).group()

    def complete(self) -> None:
        """Complete the name left of the cursor.

        Unambiguous completions go straight in; several offer what they have in
        common and list the rest under the prompt.

        rlcompleter evaluates the part before the last dot, so ``world.bod``
        evaluates ``world``. That is what makes it useful on live objects, and
        the reason to complete a name rather than the result of a call.
        """
        # The well-known names are bound before each command, so without this
        # they are missing until the first one has been run -- and completing
        # `world.` is the first thing anyone tries.
        self.rebind()
        cursor = (
            self.editor.get_main_cursor_position()
            if modern_text_editor(self.editor)
            else None
        )
        prefix = self.name_being_typed()
        if not prefix:
            self.completions = []
            return

        matches, seen = [], set()
        try:
            for index in range(100):
                match = self.completer.complete(prefix, index)
                if match is None:
                    break
                if match not in seen:
                    seen.add(match)
                    matches.append(match)
        except BaseException as exc:
            # Completing evaluates, and evaluating can fail. Not worth a
            # traceback in the transcript: the prompt is mid-word.
            self.completions = []
            self.emit(f"cannot complete {prefix}: {exc}", error=True)
            return

        if len(matches) == 1:
            self._replace_name(cursor, prefix, matches[0])
            self.completions = []
            return
        self.completions = matches
        shared = os.path.commonprefix(matches)
        if len(shared) > len(prefix):
            self._replace_name(cursor, prefix, shared)

    def _replace_name(self, cursor, prefix: str, completion: str) -> None:
        """Swap the name being typed for a longer one, keeping the cursor after it."""
        if cursor is None:
            self.input = self.input[: -len(prefix)] + completion
            lines = self.input.split("\n")
            self.editor.set_cursor_position(len(lines) - 1, len(lines[-1]))
            return
        start = TextEditor.DocPos(cursor.line, cursor.index - len(prefix))
        self.editor.select_region(start, cursor)
        self.editor.replace_text_in_current_cursor(completion)

    def runcode(self, compiled) -> None:
        """Execute one statement, capturing whatever it prints or raises.

        Overridden to redirect the output rather than let it reach the terminal
        the testbed was started from. Compiled in "single" mode, so an
        expression's value is echoed through sys.displayhook -- which writes to
        sys.stdout, and is therefore captured here too.
        """
        printed = io.StringIO()
        try:
            with (
                contextlib.redirect_stdout(printed),
                contextlib.redirect_stderr(printed),
            ):
                exec(compiled, self.locals)
        except SystemExit:
            # Nothing typed here should be able to close the window.
            self._emit_printed(printed)
            self.emit("SystemExit ignored", error=True)
        except BaseException:
            # Whatever it managed to print before it failed comes first, as it
            # would in a terminal. showtraceback is the standard library's, and
            # drops the exec frame above so the traceback starts at the mistake.
            self._emit_printed(printed)
            self.showtraceback()
        else:
            self._emit_printed(printed)

    def write(self, data: str) -> None:
        """Where InteractiveConsole sends syntax errors and tracebacks."""
        self.emit(data.rstrip("\n"), error=True)

    def emit(self, text: str, error: bool = False) -> None:
        """Add output to the panel, oldest dropped once there is too much."""
        for line in text.split("\n"):
            self.lines.append((line, error))
        del self.lines[: max(0, len(self.lines) - MAX_LINES)]
        self._scroll_to_bottom = True
        self._transcript_stale = True

    def _emit_printed(self, printed: io.StringIO) -> None:
        text = printed.getvalue()
        if text:
            self.emit(text.rstrip("\n"))

    def clear(self) -> None:
        self.lines = []
        self.resetbuffer()
        self._transcript_stale = True

    def refresh_transcript(self) -> None:
        """Push the output into the read-only widget that shows it.

        Rebuilt when a command produces output rather than every frame: it is
        one string of everything on screen, and setting it also throws away
        whatever the user had selected.
        """
        self.transcript.set_text("\n".join(text for text, _ in self.lines))
        clear_editor_markers(self.transcript)
        # A marker fills the line behind the text rather than recolouring it,
        # which at full strength is a solid red band three lines deep for every
        # traceback. Translucent, it reads as "these lines are the error".
        red = imgui.color_convert_float4_to_u32((1.0, 0.25, 0.25, 0.16))
        for index, (_, is_error) in enumerate(self.lines):
            if is_error:
                add_editor_marker(self.transcript, index, red, "")
        self._transcript_stale = False

    # -- gui -----------------------------------------------------------------

    def gui(self) -> None:
        """Draw the panel. Wired in as a dockable window."""
        if imgui.button("Clear"):
            self.clear()
        imgui.same_line()
        if imgui.button("Reset names"):
            # A namespace can be got into a state; this is the way out that
            # does not involve restarting the testbed.
            self.locals.clear()
            self.locals["__name__"] = "__console__"
            self.rebind()
            self.emit("namespace reset")
        imgui.same_line()
        if imgui.button("History"):
            self.searching = not self.searching
        imgui.same_line()
        imgui.text_disabled(f"{len(self.history)} commands")

        # Code, so it is shown in the same font the editor uses: aligned
        # tracebacks, and a repr with columns that line up.
        with push_code_font(self.mono_font):
            if self._transcript_stale:
                self.refresh_transcript()
            render_text_editor(
                self.transcript,
                "##output",
                (0, -self._footer_height),
                parent_is_focused=imgui.is_window_focused(
                    imgui.FocusedFlags_.root_and_child_windows
                ),
            )
            self._transcript_rect = (
                imgui.get_item_rect_min(),
                imgui.get_item_rect_max(),
            )
            # Clicking in the output hands the keyboard back to the prompt, so
            # you can read something and then keep typing. Unless the click
            # selected text -- then the transcript keeps the keyboard, because
            # the next thing pressed is going to be Ctrl+C.
            if (
                imgui.is_mouse_released(0)
                and imgui.is_item_hovered()
                and not self.transcript.any_cursor_has_selection()
            ):
                self._focus_input = True
            if self._scroll_to_bottom:
                line = self.transcript.get_line_count()
                if hasattr(self.transcript, "scroll_to_line"):
                    self.transcript.scroll_to_line(
                        line, TextEditor.Scroll.align_bottom
                    )
                else:
                    self.transcript.set_view_at_line(
                        max(0, line - 1),
                        TextEditor.SetViewAtLineMode.last_visible_line,
                    )
                self._scroll_to_bottom = False

            top = imgui.get_cursor_pos_y()
            if self.searching:
                self._history_search()
            self._completion_list()
            self._input_line()
            imgui.text_disabled(HINT)
            # What everything below the transcript actually took, borders and
            # padding included, for the transcript to reserve next frame.
            # Measured rather than added up: the prompt changes height as a
            # block is typed into it, and adding it up by hand was quietly a
            # line short, which clipped the hint.
            self._footer_height = imgui.get_cursor_pos_y() - top

    def _rows(self) -> int:
        """How many lines tall the prompt should be."""
        return max(1, min(self.editor.get_line_count(), INPUT_MAX_ROWS))

    def _input_line(self) -> None:
        imgui.text_disabled("..." if self.buffer else ">>>")
        imgui.same_line()
        if self._focus_input:
            # The widget's own call, not set_keyboard_focus_here: the prompt is
            # a child window rather than a plain item, so imgui's "focus the
            # next thing" left the keyboard nowhere and typing after Enter did
            # not reach it.
            if hasattr(self.editor, "set_focus"):
                self.editor.set_focus()
            else:
                imgui.set_keyboard_focus_here()
            self._focus_input = False

        # Read before the widget runs: Enter reaches it first and puts a newline
        # in, so what the prompt held a moment ago is what decides whether this
        # Enter runs it or extends it.
        before = self.input
        keyboard = imgui.is_window_focused(imgui.FocusedFlags_.root_and_child_windows)
        pressed_enter = keyboard and imgui.is_key_pressed(imgui.Key.enter)
        io = imgui.get_io()
        # Tab completes when there is a name to complete and indents otherwise,
        # as at any Python prompt. Decided here, before the widget sees the key:
        # it indents at the cursor, and by the time it has, what is left of the
        # cursor is whitespace and there is no name to look up any more.
        completing = (
            keyboard
            and imgui.is_key_pressed(imgui.Key.tab)
            and bool(self.name_being_typed())
        )

        line_height = (
            self.editor.get_line_height()
            if hasattr(self.editor, "get_line_height")
            else imgui.get_text_line_height()
        )
        size = (
            imgui.get_content_region_avail().x,
            line_height * self._rows(),
        )
        render_text_editor(
            self.editor,
            "##input",
            size,
            parent_is_focused=keyboard,
        )

        if completing:
            # Take back the indent it inserted on the way past -- but only if it
            # inserted one, or this would undo the user's last edit instead.
            if self.input != before:
                self.editor.undo()
            self.complete()
        elif keyboard:
            if io.key_ctrl and imgui.is_key_pressed(imgui.Key.r):
                self.searching = True
            # On one line, up and down are the history, as at any prompt. In a
            # block they move the cursor, which is what you need them for there.
            elif self.editor.get_line_count() == 1:
                if imgui.is_key_pressed(imgui.Key.up_arrow):
                    self._recall(-1)
                elif imgui.is_key_pressed(imgui.Key.down_arrow):
                    self._recall(1)

        if pressed_enter and should_run(before):
            self.input = ""
            self.submit_block(before)
            self._focus_input = True

    def _completion_list(self) -> None:
        """What Tab found, when it found more than one thing."""
        if not self.completions:
            return
        shown = self.completions[:MAX_COMPLETIONS_SHOWN]
        imgui.text_disabled("  ".join(shown))
        if len(self.completions) > len(shown):
            imgui.same_line()
            imgui.text_disabled(f"(+{len(self.completions) - len(shown)} more)")

    def _history_search(self) -> None:
        """A filter over what has been run, newest first."""
        imgui.set_next_item_width(-1)
        imgui.set_keyboard_focus_here()
        entered, self.search_query = imgui.input_text(
            "##search",
            self.search_query,
            flags=imgui.InputTextFlags_.enter_returns_true,
        )
        matches = self.search_matches()
        if entered or imgui.is_key_pressed(imgui.Key.escape):
            if entered and matches:
                self.input = matches[0]
            self.searching = False
            self.search_query = ""
            self._focus_input = True
            return
        if not matches:
            imgui.text_disabled("no match")
            return
        for command in matches[:1]:
            if imgui.selectable(command, False)[0]:
                self.input = command
                self.searching = False
                self.search_query = ""
                self._focus_input = True
        if len(matches) > 1:
            imgui.same_line()
            imgui.text_disabled(f"(+{len(matches) - 1} older)")

    def search_matches(self) -> list:
        """History entries containing the query, newest first and deduplicated."""
        found, seen = [], set()
        for command in reversed(self.history):
            if self.search_query in command and command not in seen:
                seen.add(command)
                found.append(command)
        return found

    def _recall(self, step: int) -> None:
        """Walk the history, oldest at the top as in a shell."""
        if not self.history:
            return
        if self.history_index is None:
            self.history_index = len(self.history)
        index = self.history_index + step
        if index >= len(self.history):
            # Past the newest: back to the empty line that was being typed.
            self.history_index = None
            self.input = ""
            return
        self.history_index = max(index, 0)
        self.input = self.history[self.history_index]
