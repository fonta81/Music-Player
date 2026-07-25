from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from pygame import mixer
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    ProgressBar,
    Static,
)

# Inicialización del reproductor
mixer.init(frequency=44100, size=-16, channels=2, buffer=512)


class Reproductor(App):
    CSS = """
    Screen { align: center middle; }
    
    #main-container {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    
    #left-panel {
        width: 60%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    #right-panel {
        width: 40%;
        height: 100%;
        border: solid $primary-lighten-2;
        padding: 1;
    }
    
    #track-info {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        border: solid $primary-darken-2;
        margin-bottom: 1;
    }
    
    #controls {
        height: auto;
        align: center middle;
        padding: 1;
    }
    
    #progress-container {
        height: auto;
        padding: 1 0;
    }
    
    #volume-container {
        height: auto;
        padding: 1 0;
    }
    
    DataTable {
        height: 1fr;
        border: none;
    }
    
    .info-label {
        color: $text-muted;
        text-style: bold;
    }
    
    .info-value {
        color: $text;
    }
    
    #status {
        text-align: center;
        color: $success;
        text-style: bold;
    }
    
    Button {
        width: auto;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding(key="q", action="quit", description="Salir"),
        Binding(
            key="space", action="toggle_play", description="Play/Pause", show=False
        ),
        Binding(key="s", action="stop", description="Detener", show=False),
        Binding(key="n", action="next_track", description="Siguiente", show=False),
        Binding(key="p", action="prev_track", description="Anterior", show=False),
        Binding(key="up", action="volume_up", description="Vol +", show=False),
        Binding(key="down", action="volume_down", description="Vol -", show=False),
        Binding(key="delete", action="delete_track", description="Eliminar"),
        Binding(key="enter", action="play_selected", description="Reproducir"),
        Binding(key="?", action="help", description="Ayuda", key_display="?"),
    ]

    # Estado reactivo
    current_track: reactive[Optional[Path]] = reactive(None)
    is_playing: reactive[bool] = reactive(False)
    volume: reactive[int] = reactive(70, init=False)
    current_index: reactive[int] = reactive(-1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mp3_files: list[Path] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            # Panel izquierdo: Lista de canciones
            with Vertical(id="left-panel"):
                yield Label("📁 Biblioteca MP3", id="library-title")
                table = DataTable(id="playlist")
                table.cursor_type = "row"
                table.zebra_stripes = True
                yield table

            # Panel derecho: Info y controles
            with Vertical(id="right-panel"):
                yield Static(
                    "Selecciona una canción\npara comenzar",
                    id="track-info",
                )

                with Vertical(id="progress-container"):
                    yield Label("Progreso", classes="info-label")
                    yield ProgressBar(
                        id="progress", show_eta=False, show_percentage=True
                    )

                with Horizontal(id="controls"):
                    yield Button("⏮", id="btn-prev", variant="primary")
                    yield Button("▶", id="btn-play", variant="success")
                    yield Button("⏹", id="btn-stop", variant="error")
                    yield Button("⏭", id="btn-next", variant="primary")

                with Vertical(id="volume-container"):
                    yield Label(f"🔊 Volumen: {self.volume}%", id="volume-label")
                    yield ProgressBar(
                        total=100,
                        id="volume-bar",
                        show_percentage=True,
                    )

                yield Label("⏸ Detenido", id="status")

        yield Footer()

    def on_mount(self) -> None:
        self.title = "🎵 Reproductor MP3"
        self.scan_mp3_files()
        mixer.music.set_volume(self.volume / 100.0)
        self.set_interval(0.5, self.update_progress)

    def scan_mp3_files(self) -> None:
        """Escanea la carpeta del script buscando MP3."""
        script_dir = Path(__file__).parent.resolve()
        self.mp3_files = sorted(script_dir.glob("*.mp3"))

        table = self.query_one("#playlist", DataTable)
        table.clear(columns=True)
        table.add_columns("#", "Canción", "Artista", "Duración", "Tamaño")

        if not self.mp3_files:
            table.add_row("—", "No hay archivos MP3", "—", "—", "—")
            return

        for idx, mp3 in enumerate(self.mp3_files, 1):
            try:
                audio = MP3(str(mp3))
                tags = audio.tags or {}
                title = str(tags.get("TIT2", mp3.stem))
                artist = str(tags.get("TPE1", "Desconocido"))
                mins = int(audio.info.length // 60)
                secs = int(audio.info.length % 60)
                duration = f"{mins}:{secs:02d}"
                size = f"{mp3.stat().st_size / 1024 / 1024:.1f} MB"
                table.add_row(str(idx), title, artist, duration, size)
            except Exception:
                table.add_row(str(idx), mp3.name, "—", "—", "—")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Al seleccionar una fila con Enter o clic."""
        if not self.mp3_files:
            return
        row_idx = event.cursor_row
        if 0 <= row_idx < len(self.mp3_files):
            self.current_index = row_idx
            self.play_track(self.mp3_files[row_idx])

    def action_play_selected(self) -> None:
        """Reproduce la canción seleccionada."""
        table = self.query_one("#playlist", DataTable)
        if table.row_count == 0 or not self.mp3_files:
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        row_idx = table.get_row_index(row_key)
        if 0 <= row_idx < len(self.mp3_files):
            self.current_index = row_idx
            self.play_track(self.mp3_files[row_idx])

    def play_track(self, track_path: Path) -> None:
        """Carga y reproduce un archivo MP3."""
        try:
            mixer.music.load(str(track_path))
            mixer.music.play()
            self.current_track = track_path
            self.is_playing = True
            self.update_track_info()
            self.query_one("#status", Label).update("▶ Reproduciendo")
            self.query_one("#btn-play", Button).label = "⏸"
        except Exception as e:
            self.notify(f"Error al reproducir: {e}", severity="error")

    def action_toggle_play(self) -> None:
        """Play/Pause."""
        if not self.current_track:
            self.action_play_selected()
            return

        if self.is_playing:
            mixer.music.pause()
            self.is_playing = False
            self.query_one("#status", Label).update("⏸ Pausado")
            self.query_one("#btn-play", Button).label = "▶"
        else:
            mixer.music.unpause()
            self.is_playing = True
            self.query_one("#status", Label).update("▶ Reproduciendo")
            self.query_one("#btn-play", Button).label = "⏸"

    def action_stop(self) -> None:
        """Detiene la reproducción."""
        mixer.music.stop()
        self.is_playing = False
        self.current_track = None
        self.query_one("#status", Label).update("⏹ Detenido")
        self.query_one("#btn-play", Button).label = "▶"
        self.query_one("#progress", ProgressBar).update(progress=0)

    def action_next_track(self) -> None:
        """Pasa a la siguiente canción."""
        if not self.mp3_files:
            return
        self.current_index = (self.current_index + 1) % len(self.mp3_files)
        self.play_track(self.mp3_files[self.current_index])
        self._highlight_row(self.current_index)

    def action_prev_track(self) -> None:
        """Vuelve a la anterior."""
        if not self.mp3_files:
            return
        self.current_index = (self.current_index - 1) % len(self.mp3_files)
        self.play_track(self.mp3_files[self.current_index])
        self._highlight_row(self.current_index)

    def _highlight_row(self, index: int) -> None:
        """Mueve el cursor del DataTable a la fila activa."""
        table = self.query_one("#playlist", DataTable)
        if index < table.row_count:
            table.move_cursor(row=index)

    def action_volume_up(self) -> None:
        """Sube el volumen."""
        self.volume = min(100, self.volume + 10)
        mixer.music.set_volume(self.volume / 100.0)

    def action_volume_down(self) -> None:
        """Baja el volumen."""
        self.volume = max(0, self.volume - 10)
        mixer.music.set_volume(self.volume / 100.0)

    def watch_volume(self, volume: int) -> None:
        """Actualiza la UI cuando cambia el volumen."""
        # Solo intentamos actualizar la interfaz si el componente ya fue montado
        if self.is_mounted:
            self.query_one("#volume-label", Label).update(f"🔊 Volumen: {volume}%")
            self.query_one("#volume-bar", ProgressBar).update(progress=volume)

    def update_track_info(self) -> None:
        """Actualiza el panel de información del track actual."""
        if not self.current_track:
            return

        try:
            audio = MP3(str(self.current_track))
            tags = audio.tags or {}
            title = str(tags.get("TIT2", self.current_track.stem))
            artist = str(tags.get("TPE1", "Desconocido"))
            album = str(tags.get("TALB", "—"))
            mins = int(audio.info.length // 60)
            secs = int(audio.info.length % 60)
            duration = f"{mins}:{secs:02d}"

            info_text = (
                f"[b]🎵 {title}[/b]\n\n"
                f"[b]Artista:[/b] {artist}\n"
                f"[b]Álbum:[/b] {album}\n"
                f"[b]Duración:[/b] {duration}\n"
                f"[b]Archivo:[/b] {self.current_track.name}"
            )
        except Exception:
            info_text = f"[b]🎵 {self.current_track.name}[/b]\n\nNo se pudieron leer los metadatos."

        self.query_one("#track-info", Static).update(info_text)

    def update_progress(self) -> None:
        """Actualiza la barra de progreso cada 0.5s."""
        if not self.is_playing or not self.current_track:
            return

        try:
            audio = MP3(str(self.current_track))
            total = audio.info.length
            pos_ms = mixer.music.get_pos()
            if pos_ms > 0:
                current = pos_ms / 1000.0
                progress = (current / total) * 100 if total > 0 else 0
                self.query_one("#progress", ProgressBar).update(
                    total=100, progress=min(100, progress)
                )
        except Exception:
            pass

    def action_delete_track(self) -> None:
        """Elimina el archivo MP3 seleccionado."""
        table = self.query_one("#playlist", DataTable)
        if table.row_count == 0 or not self.mp3_files:
            return

        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        row_idx = table.get_row_index(row_key)

        if 0 <= row_idx < len(self.mp3_files):
            track = self.mp3_files[row_idx]
            if self.current_track == track:
                self.action_stop()

            try:
                track.unlink()  # Elimina el archivo directamente con Path
                self.mp3_files.pop(row_idx)
                self.scan_mp3_files()
                self.notify(f"🗑 Eliminado: {track.name}", severity="information")
            except Exception as e:
                self.notify(f"Error al eliminar: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Maneja clicks en los botones."""
        btn_id = event.button.id
        if btn_id == "btn-play":
            self.action_toggle_play()
        elif btn_id == "btn-stop":
            self.action_stop()
        elif btn_id == "btn-next":
            self.action_next_track()
        elif btn_id == "btn-prev":
            self.action_prev_track()

    def action_help(self) -> None:
        self.notify(
            "Controles:\n"
            "• [Enter] o doble clic → Reproducir\n"
            "• [Espacio] → Play/Pause\n"
            "• [S] → Detener\n"
            "• [N] → Siguiente\n"
            "• [P] → Anterior\n"
            "• [↑/↓] → Volumen\n"
            "• [Supr] → Eliminar archivo\n"
            "• [Q] → Salir",
            title="Ayuda",
            severity="information",
            timeout=8,
        )

    def on_unmount(self) -> None:
        mixer.quit()


if __name__ == "__main__":
    app = Reproductor()
    app.run()
