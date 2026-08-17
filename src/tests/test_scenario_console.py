# tests/test_scenario_console.py
"""The prompt, driven directly rather than through a window.

Everything here is about what a command does to the namespace and to the
output; that the panel draws is checked in test_testbed_headless.
"""

from types import SimpleNamespace

import pytest

# The console panel is imgui's, so without the testbed extra there is nothing
# to import.
pytest.importorskip("imgui_bundle", reason="needs the testbed extra")

from box2d import World  # noqa: E402
from box2d_testbed.scenario_console import Console  # noqa: E402
from box2d_testbed.testbed_state import state  # noqa: E402


@pytest.fixture
def world():
    world = World()
    world.new_body().static().segment((-10, 0), (10, 0)).build()
    yield world
    world.destroy()


@pytest.fixture
def console(world):
    """A console over a stub app holding one world."""
    console = Console(SimpleNamespace(simulation=SimpleNamespace(world=world)))
    console.clear()
    return console


def output(console):
    return [text for text, _ in console.lines]


def errors(console):
    return [text for text, is_error in console.lines if is_error]


def test_an_expression_is_echoed_the_way_a_prompt_echoes_it(console):
    console.submit("6 * 7")

    assert output(console) == [">>> 6 * 7", "42"]
    assert errors(console) == []


def test_a_statement_prints_nothing_but_still_shows_the_prompt(console):
    console.submit("x = 1")

    assert output(console) == [">>> x = 1"]


def test_what_a_command_prints_is_captured(console):
    console.submit("print('one'); print('two')")

    assert output(console) == [">>> print('one'); print('two')", "one", "two"]


def test_the_running_world_is_in_scope(console, world):
    console.submit("len(list(world.bodies))")

    assert output(console)[-1] == "1"


def test_the_scenario_that_is_running_is_in_scope(console):
    """``test`` is the whole point: the object with the scenario's own state."""
    marker = SimpleNamespace(label="the running scenario")
    state.current_test_obj = marker
    try:
        console.submit("test.label")
    finally:
        state.current_test_obj = None

    assert output(console)[-1] == "'the running scenario'"


def test_the_names_are_rebound_after_the_world_is_replaced(console):
    """A reset, a scenario change and every save throw the world away, so a
    handle bound at startup would be pointing at freed memory."""
    console.submit("world")
    replacement = World()
    try:
        console.app.simulation.world = replacement
        console.submit("world is app.simulation.world")
    finally:
        replacement.destroy()

    assert output(console)[-1] == "True"


def test_names_you_define_stay_defined(console):
    console.submit("saved = 3")
    console.submit("saved * 2")

    assert output(console)[-1] == "6"


def test_an_error_is_shown_rather_than_raised(console):
    console.submit("1 / 0")

    assert "ZeroDivisionError: division by zero" in errors(console)[-1]


def test_a_traceback_does_not_start_with_the_console_itself(console):
    """The frame that ran the code is noise; the frames under it are the bug."""
    console.submit("def broken():\n")
    console.submit("    raise ValueError('deliberate')")
    console.submit("")
    console.submit("broken()")

    traceback = "\n".join(errors(console))
    assert "deliberate" in traceback
    assert "scenario_console.py" not in traceback


def test_a_syntax_error_is_reported_and_clears_the_pending_block(console):
    console.submit("for i in range(3):")
    assert console.buffer, "an open block waits for more"

    console.submit("    ?")

    assert "SyntaxError" in "".join(errors(console))
    assert console.buffer == [], "and the broken block is not still pending"


def test_a_block_runs_once_it_is_complete(console):
    console.submit("total = 0")
    console.submit("for i in range(4):")
    console.submit("    total += i")
    assert console.buffer, "still waiting for the blank line that ends it"

    console.submit("")
    console.submit("total")

    assert output(console)[-1] == "6"


def test_the_prompt_cannot_close_the_window(console):
    """A stray exit() in a console over a GUI is otherwise fatal."""
    console.submit("raise SystemExit(1)")

    assert errors(console)[-1] == "SystemExit ignored"


def test_the_history_walks_back_and_then_forward_again(console):
    console.submit("first")
    console.submit("second")
    console.input = ""

    console._recall(-1)
    assert console.input == "second"
    console._recall(-1)
    assert console.input == "first"
    console._recall(-1)
    assert console.input == "first", "and stops at the oldest"

    console._recall(1)
    assert console.input == "second"
    console._recall(1)
    assert console.input == "", "past the newest is the empty line again"


def test_blank_input_is_not_kept_in_the_history(console):
    console.submit("something")
    console.submit("")
    console.submit("   ")

    assert console.history == ["something"]


def test_output_does_not_grow_without_bound(console):
    from box2d_testbed.scenario_console import MAX_LINES

    console.submit(f"print('line\\n' * {MAX_LINES * 2})")

    assert len(console.lines) == MAX_LINES


def test_clearing_empties_the_output_but_keeps_the_namespace(console):
    console.submit("kept = 1")
    console.clear()
    console.submit("kept")

    assert output(console) == [">>> kept", "1"]


def test_what_was_printed_before_a_failure_comes_before_the_traceback(console):
    """The order it happened in, which is the order a terminal shows it."""
    console.submit("print('got this far'); 1 / 0")

    texts = output(console)
    assert texts[:2] == [">>> print('got this far'); 1 / 0", "got this far"]
    assert "ZeroDivisionError" in "\n".join(texts[2:])


def test_a_syntax_error_says_what_was_wrong_and_where(console):
    console.submit("x = (1 +")
    console.submit("    2")
    console.submit("    3")

    reported = "\n".join(errors(console))
    assert "SyntaxError" in reported
    assert "<console>" in reported, "the traceback names the source it came from"


# --- multiline input, completion and history search --------------------------


def type_at_prompt(console, text):
    """Put text at the prompt with the cursor after it, as typing would."""
    from box2d_testbed.scenario_editor import TextEditor

    console.input = text
    lines = text.split("\n")
    console.editor.set_cursor(TextEditor.DocPos(len(lines) - 1, len(lines[-1])))


@pytest.mark.parametrize(
    "typed, runs, why",
    [
        ("1 + 1", True, "a complete statement runs"),
        ("", False, "an empty prompt does nothing"),
        ("   ", False, "nor does a blank one"),
        ("for i in x:", False, "a block header waits for its body"),
        ("x = (1 +", False, "so does an unclosed bracket"),
        ("?", True, "a syntax error is better reported than stuck at the prompt"),
        ("for i in x:\n    print(i)", False, "Enter on a body line takes another"),
        ("for i in x:\n    print(i)\n", True, "and a blank line closes the block"),
        ("for i in x:\n    print(i)\n    ", True, "even one the auto-indent filled in"),
    ],
)
def test_enter_either_runs_it_or_takes_another_line(typed, runs, why):
    from box2d_testbed.scenario_console import should_run

    assert should_run(typed) is runs, why


def test_a_block_typed_at_the_prompt_runs_in_one_go(console):
    """What the multiline prompt is for: the whole thing, one Enter."""
    console.submit_block("total = 0\nfor i in range(4):\n    total += i")
    console.submit("total")

    assert output(console)[-1] == "6"
    assert console.buffer == [], "and the block was closed, not left open"


def test_a_block_is_echoed_the_way_a_terminal_would(console):
    console.submit_block("for i in range(2):\n    print(i)")

    assert output(console) == [
        ">>> for i in range(2):",
        "...     print(i)",
        "... ",
        "0",
        "1",
    ]


def test_one_completion_goes_straight_in(console):
    console.locals["thing"] = SimpleNamespace(alpha=1, alpine=2, beta=3)
    type_at_prompt(console, "thing.be")

    console.complete()

    assert console.input == "thing.beta"
    assert console.completions == [], "nothing left to choose between"


def test_several_completions_are_offered(console):
    console.locals["thing"] = SimpleNamespace(alpha=1, alpine=2, beta=3)
    type_at_prompt(console, "thing.al")

    console.complete()

    assert set(console.completions) >= {"thing.alpha", "thing.alpine"}
    # As far as they agree, which is as far as it can go without guessing.
    assert console.input == "thing.alp"


def test_completion_reaches_into_the_running_world(console):
    """The point of it: attributes of the live objects, not a static list."""
    type_at_prompt(console, "world.bod")

    console.complete()

    assert console.input == "world.bodies"


def test_completing_the_middle_of_a_line_leaves_the_rest_alone(console):
    console.locals["thing"] = SimpleNamespace(beta=3)
    console.input = "print(thing.be)"
    from box2d_testbed.scenario_editor import TextEditor

    console.editor.set_cursor(TextEditor.DocPos(0, len("print(thing.be")))

    console.complete()

    assert console.input == "print(thing.beta)"


def test_nothing_to_complete_is_not_an_error(console):
    type_at_prompt(console, "1 + ")

    console.complete()

    assert console.completions == []
    assert errors(console) == []


def test_a_name_that_cannot_be_evaluated_is_reported_not_raised(console):
    """Completion evaluates what is left of the dot, and that can fail."""
    type_at_prompt(console, "no_such_name.attr")

    console.complete()

    assert console.completions == []


def test_history_search_finds_the_newest_first(console):
    for command in ["world.bodies", "test.reset", "world.gravity", "world.bodies"]:
        console.submit(command)
    console.search_query = "world"

    assert console.search_matches() == ["world.bodies", "world.gravity"]


def test_history_search_with_no_query_offers_everything(console):
    console.submit("first")
    console.submit("second")
    console.search_query = ""

    assert console.search_matches() == ["second", "first"]
