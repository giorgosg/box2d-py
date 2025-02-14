import dearpygui.dearpygui as dpg
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


def get_token_color(token_type):
    """
    Map token types from Pygments to RGBA color tuples.
    """
    if token_type in Token.Keyword:
        return (100, 100, 255, 255)  # Blue for keywords
    elif token_type in Token.Literal.String:
        return (0, 128, 0, 255)  # Green for strings
    elif token_type in Token.Comment:
        return (128, 128, 128, 255)  # Gray for comments
    elif token_type in Token.Name.Function:
        return (255, 165, 0, 255)  # Orange for function names
    elif token_type in Token.Operator:
        return (220, 20, 60, 255)  # Crimson for operators
    else:
        return (255, 255, 255, 255)  # White (default)


# Sample Python code to display
sample_code = """\
def hello_world():
    # This function prints hello world
    print("Hello, world!")
"""


def draw_code():
    """
    Tokenizes the sample code and draws it on a drawlist.
    Uses a fixed-width font assumption (we use an approximate 8px per character).
    """
    tokens = list(lex(sample_code, PythonLexer()))
    x_start = 5
    y_start = 5
    line_height = 15
    char_width = 8  # approximate width per character
    x = x_start
    y = y_start

    # Process each token returned by Pygments
    for token_type, token_text in tokens:
        token_color = get_token_color(token_type)
        # Split token text on newlines to handle multi-line tokens
        segments = token_text.split("\n")
        for i, segment in enumerate(segments):
            if segment:
                dpg.draw_text((x, y), segment, color=token_color, size=15)
                # Advance x: assume monospaced font, so width is proportional to len(segment)
                x += len(segment) * char_width
            # If there's a newline in the token, reset x and go to the next line
            if i < len(segments) - 1:
                x = x_start
                y += line_height


# Set up Dear PyGui context and window
dpg.create_context()
dpg.create_viewport(title="Syntax Highlighted Code", width=600, height=200)

with dpg.window(label="Syntax Highlighted Code", width=600, height=200):
    # Create a drawlist that will serve as the code canvas
    with dpg.drawlist(width=580, height=180):
        draw_code()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
