from pathlib import Path
from typing import Optional

import pygame.mixer as mixer
from mutagen.mp3 import MP3
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Label,
    ProgressBar,
    Static,
)


class VentanaAyuda(ModalScreen):  # ventana help
    # Atajos para cerrar la ayuda rápidamente con Esc, ? o q
    BINDINGS = [Binding("escape,?,q", "dismiss", "Cerrar Ayuda")]

    def compose(self) -> ComposeResult:  # ayuda:
        texto_ayuda = (
            "[bold]Guía de Atajos de Teclado[/]\n\n"
            "[substantive]Navegación:[/]\n"
            "  [b]↑[/]                             - Subir en el árbol\n"
            "  [b]↓[/]                             - Bajar en el árbol\n\n"
            "[substantive]Acciones:[/]\n\n"
            "  [b]o[/]                             - Seleccionar carpeta\n"
            "  [b]Enter[/] o [b]Doble Click[/]           - Reproducir\n"
            "  [b]Espacio[/]                       - Play/Pause\n"
            "  [b]s[/]                             - Detener\n"
            "  [b]n[/]                             - Siguiente\n"
            "  [b]Supr[/]                          - Elimina archivo\n\n"
            "[substantive]General:[/]\n"
            "  [b]?[/]                             - Mostrar/Ocultar esta ayuda\n"
            "  [b]q[/]                             - Salir de la aplicación\n\n"
            "[dim]Presiona cualquier tecla asignada o ESC para cerrar[/]"
        )

        yield Grid(
            Label("AYUDA", id="help_title"),
            Static(texto_ayuda, id="help_content"),
            id="help_dialog",
        )


class FolderSelectScreen(ModalScreen[Optional[Path]]):
    """Pantalla modal para seleccionar una carpeta."""

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(
                "📁 Selecciona una carpeta con archivos MP3:", id="dialog-title"
            )
            yield DirectoryTree(Path.home(), id="dir-tree")
            with Horizontal(id="dialog-buttons"):
                yield Button("Seleccionar Carpeta", id="btn-select", variant="success")
                yield Button("Cancelar", id="btn-cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-select":
            tree = self.query_one("#dir-tree", DirectoryTree)
            node = tree.cursor_node

            if node is not None and node.data is not None:
                selected_path = Path(node.data.path)
            else:
                selected_path = Path(tree.path)

            if selected_path.is_file():
                selected_path = selected_path.parent

            self.dismiss(selected_path)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


class Reproductor(App):
    CSS_PATH = "style.tcss"

    BINDINGS = [
        Binding(key="q", action="quit", description="Salir"),
        Binding(key="o", action="select_folder", description="Abrir carpeta"),
        Binding(key="space", action="toggle_play", description="Play/Pause"),
        Binding(key="s", action="stop", description="Detener"),
        Binding(key="n", action="next_track", description="Siguiente"),
        Binding(key="p", action="prev_track", description="Anterior"),
        Binding(key="up", action="volume_up", description="Vol +"),
        Binding(key="down", action="volume_down", description="Vol -"),
        Binding(key="delete", action="delete_track", description="Eliminar"),
        Binding(key="?", action="help", description="Ayuda", key_display="?"),
    ]

    # Estado reactivo (solo volumen necesita watcher)
    volume: reactive[int] = reactive(70, init=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mp3_files: list[Path] = []
        self.current_dir = Path(__file__).parent.resolve()

        # Estado simple (no necesita reactividad)
        self.current_track: Optional[Path] = None
        self.is_playing = False
        self.current_index = -1

        # Cache de metadatos y progreso
        self._current_meta: dict = {}
        self._progress_offset: float = 0.0
        self._last_resume_time: float = 0.0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield Button("📂 Abrir Carpeta", id="btn-folder", variant="default")
                yield Label(
                    f"📁 Biblioteca MP3: {self.current_dir.name}", id="library-title"
                )
                table = DataTable(id="playlist")
                table.cursor_type = "row"
                table.zebra_stripes = True
                yield table

            with Vertical(id="right-panel"):
                yield Static(
                    "Selecciona una canción\npara comenzar",
                    id="track-info",
                )

                with Vertical(id="progress-container"):
                    yield Label("Progreso", classes="info-label")
                    yield ProgressBar(
                        id="progress", total=100, show_eta=False, show_percentage=True
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

                yield Label("⏹ Detenido", id="status")

        yield Footer()

    def on_mount(self) -> None:
        mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.title = "♪ Reproductor MP3"
        self.scan_mp3_files()
        mixer.music.set_volume(self.volume / 100.0)
        self.set_interval(0.5, self.update_progress)

    def action_select_folder(self) -> None:
        """Abre la pantalla modal para elegir carpeta."""

        def folder_selected(folder: Optional[Path]) -> None:
            if folder and folder.is_dir():
                self.current_dir = folder
                self.action_stop()
                self.scan_mp3_files()
                self.query_one("#library-title", Label).update(
                    f"📁 Biblioteca: {folder.name}"
                )

        self.push_screen(FolderSelectScreen(), folder_selected)

    def _get_track_metadata(self, track_path: Path) -> dict:
        """Extrae metadatos de un archivo MP3."""
        try:
            audio = MP3(str(track_path))
            tags = audio.tags or {}
            mins = int(audio.info.length // 60)
            secs = int(audio.info.length % 60)
            return {
                "title": str(tags.get("TIT2", track_path.stem)),
                "artist": str(tags.get("TPE1", "Desconocido")),
                "album": str(tags.get("TALB", "—")),
                "duration": f"{mins}:{secs:02d}",
                "length": audio.info.length,
            }
        except Exception:
            return {
                "title": track_path.stem,
                "artist": "Desconocido",
                "album": "—",
                "duration": "—",
                "length": 0,
            }

    def scan_mp3_files(self) -> None:
        """Escanea la carpeta seleccionada buscando MP3."""
        self.mp3_files = sorted(self.current_dir.glob("*.mp3"))

        table = self.query_one("#playlist", DataTable)
        table.clear(columns=True)
        table.add_columns("#", "Canción", "Artista", "Duración", "Tamaño")

        if not self.mp3_files:
            table.add_row("—", "No hay archivos MP3", "—", "—", "—")
            return

        for idx, mp3 in enumerate(self.mp3_files, 1):
            meta = self._get_track_metadata(mp3)
            size = f"{mp3.stat().st_size / 1024 / 1024:.1f} MB"
            table.add_row(
                str(idx), meta["title"], meta["artist"], meta["duration"], size
            )

    def _is_valid_index(self, index: int) -> bool:
        """Verifica si un índice está dentro del rango de la playlist."""
        return 0 <= index < len(self.mp3_files)

    def _get_cursor_index(self, table: DataTable) -> int:
        """Obtiene el índice de fila actual del cursor."""
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return table.get_row_index(row_key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Al seleccionar una fila con Enter o doble clic."""
        row_idx = event.cursor_row
        if self._is_valid_index(row_idx):
            self.current_index = row_idx
            self.play_track(self.mp3_files[row_idx])

    def play_track(self, track_path: Path) -> None:
        """Carga y reproduce un archivo MP3."""
        try:
            mixer.music.load(str(track_path))
            mixer.music.play()
            self.current_track = track_path
            self.is_playing = True
            self._current_meta = self._get_track_metadata(track_path)
            self._progress_offset = 0.0
            self._last_resume_time = mixer.music.get_pos() / 1000.0
            self._update_playback_ui(playing=True)
            self.update_track_info()
        except Exception as e:
            self.notify(f"Error al reproducir: {e}", severity="error")

    def _update_playback_ui(self, playing: bool, paused: bool = False) -> None:
        """Actualiza labels y botones según el estado de reproducción."""
        status_label = self.query_one("#status", Label)
        play_button = self.query_one("#btn-play", Button)

        if paused:
            status_label.update("⏸ Pausado")
            play_button.label = "▶"
        elif playing:
            status_label.update("▶ Reproduciendo")
            play_button.label = "⏸"
        else:
            status_label.update("⏹ Detenido")
            play_button.label = "▶"
            self.query_one("#progress", ProgressBar).update(progress=0)

    def action_toggle_play(self) -> None:
        """Play/Pause."""
        if not self.current_track:
            table = self.query_one("#playlist", DataTable)
            if table.row_count == 0 or not self.mp3_files:
                return
            row_idx = self._get_cursor_index(table)
            if self._is_valid_index(row_idx):
                self.current_index = row_idx
                self.play_track(self.mp3_files[row_idx])
            return

        if self.is_playing:
            mixer.music.pause()
            self.is_playing = False
            # Acumular progreso real antes de pausar
            elapsed = (mixer.music.get_pos() / 1000.0) - self._last_resume_time
            self._progress_offset += max(0, elapsed)
            self._update_playback_ui(playing=False, paused=True)
        else:
            mixer.music.unpause()
            self.is_playing = True
            self._last_resume_time = mixer.music.get_pos() / 1000.0
            self._update_playback_ui(playing=True)

    def action_stop(self) -> None:
        """Detiene la reproducción."""
        mixer.music.stop()
        self.is_playing = False
        self.current_track = None
        self._current_meta = {}
        self._progress_offset = 0.0
        self._update_playback_ui(playing=False)

    def _change_track(self, delta: int) -> None:
        """Cambia de pista en la dirección indicada (+1 siguiente, -1 anterior)."""
        if not self.mp3_files:
            return
        self.current_index = (self.current_index + delta) % len(self.mp3_files)
        self.play_track(self.mp3_files[self.current_index])
        self._highlight_row(self.current_index)

    def action_next_track(self) -> None:
        """Pasa a la siguiente canción."""
        self._change_track(1)

    def action_prev_track(self) -> None:
        """Vuelve a la anterior."""
        self._change_track(-1)

    def _highlight_row(self, index: int) -> None:
        """Mueve el cursor del DataTable a la fila activa."""
        table = self.query_one("#playlist", DataTable)
        if index < table.row_count:
            table.move_cursor(row=index)

    def action_volume_up(self) -> None:
        """Sube el volumen."""
        self.volume = min(100, self.volume + 10)

    def action_volume_down(self) -> None:
        """Baja el volumen."""
        self.volume = max(0, self.volume - 10)

    def watch_volume(self, volume: int) -> None:
        """Actualiza UI y mixer cuando cambia el volumen (única fuente de verdad)."""
        mixer.music.set_volume(volume / 100.0)
        self.query_one("#volume-label", Label).update(f"🔊 Volumen: {volume}%")
        self.query_one("#volume-bar", ProgressBar).update(progress=volume)

    def update_track_info(self) -> None:
        """Actualiza el panel de información del track actual."""
        if not self.current_track:
            return

        meta = self._current_meta
        info_text = (
            f"[b]♪ {meta['title']}[/b]\n\n"
            f"[b]Artista:[/b] {meta['artist']}\n"
            f"[b]Álbum:[/b] {meta['album']}\n"
            f"[b]Duración:[/b] {meta['duration']}\n"
            f"[b]Archivo:[/b] {self.current_track.name}"
        )
        self.query_one("#track-info", Static).update(info_text)

    def update_progress(self) -> None:
        """Actualiza la barra de progreso cada 0.5s."""
        if not self.is_playing or not self.current_track:
            return

        try:
            total = self._current_meta.get("length", 0)
            if total <= 0:
                return

            # Calcular progreso real considerando pausas
            current_pos = self._progress_offset + (
                (mixer.music.get_pos() / 1000.0) - self._last_resume_time
            )
            progress = (current_pos / total) * 100
            self.query_one("#progress", ProgressBar).update(
                progress=min(100, max(0, progress))
            )
        except Exception:
            pass

    def action_delete_track(self) -> None:
        """Elimina el archivo MP3 seleccionado."""
        table = self.query_one("#playlist", DataTable)
        if table.row_count == 0 or not self.mp3_files:
            return

        row_idx = self._get_cursor_index(table)

        if self._is_valid_index(row_idx):
            track = self.mp3_files[row_idx]
            if self.current_track == track:
                self.action_stop()

            try:
                track.unlink()
                self.mp3_files.pop(row_idx)
                self.scan_mp3_files()
                self.notify(f"🗑 Eliminado: {track.name}", severity="information")
            except Exception as e:
                self.notify(f"Error al eliminar: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Maneja clicks en los botones."""
        btn_id = event.button.id
        if btn_id == "btn-folder":
            self.action_select_folder()
        elif btn_id == "btn-play":
            self.action_toggle_play()
        elif btn_id == "btn-stop":
            self.action_stop()
        elif btn_id == "btn-next":
            self.action_next_track()
        elif btn_id == "btn-prev":
            self.action_prev_track()

    def action_help(self) -> None:
        self.push_screen(VentanaAyuda())

    def on_unmount(self) -> None:
        mixer.quit()


if __name__ == "__main__":
    app = Reproductor()
    app.run()
