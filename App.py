# se importan librerias
from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, DataTable
from mutagen.mp3 import MP3


class Reproductor(App):  # Inicia la aplicacion
    BINDINGS = [  # las opciones del Footer
        Binding(key="q", action="quit", description="Salir"),
        Binding(key="?", action="help", description="Ayuda"),
    ]

    # lo que "imprimira"
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield DataTable()

    def on_mount(self) -> None:  # mp3_files
        # para ver los mp3 de la carpeta
        script_dir = Path(__file__).parent.resolve()
        mp3_files = sorted(script_dir.glob("*.mp3"))

        # modifica la tabla para ver cancion ect...
        table = self.query_one(DataTable)
        table.add_columns("Canción", "Artista", "Álbum", "Duración", "Tamaño")
        table.cursor_type = "row"

        # si no hya mp3 en la carpeta:
        if not mp3_files:
            table.add_row("— No hay MP3 en esta carpeta —", "", "", "", "")
            return

        # extrae la info del mp3 de todos
        for mp3 in mp3_files:
            try:
                audio = MP3(str(mp3))
                tags = audio.tags or {}

                titulo = tags.get("TIT2", mp3.stem)
                artista = tags.get("TPE1", "Desconocido")
                album = tags.get("TALB", "—")
                duracion = (
                    f"{int(audio.info.length // 60)}:{int(audio.info.length % 60):02d}"
                )
                tamaño = f"{mp3.stat().st_size / 1024 / 1024:.1f} MB"

                table.add_row(str(titulo), str(artista), str(album), duracion, tamaño)
            # en caso de error:
            except Exception:
                table.add_row(mp3.name, "Error", "—", "—", "—")


if __name__ == "__main__":  # inicia la aplicacion
    Reproductor().run()
