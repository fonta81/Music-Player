from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header


class Reproductor(App):
    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(
            key="question_mark",
            action="help",
            description="Show help screen",
            key_display="?",
        ),
        Binding(key="delete", action="delete", description="Delete the thing"),
        Binding(key="j", action="down", description="Scroll down", show=False),
    ]
    CSS_PATH = "styles.css"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()


if __name__ == "__main__":
    app = Reproductor()
    app.run()
