#  MP3 Player

A terminal-based MP3 player built with [Textual](https://textual.textualize.io/) and [Pygame](https://www.pygame.org/). It scans your local directory for MP3 files and provides an intuitive TUI (Text User Interface) with playback controls, metadata display, and keyboard shortcuts.

---

##  Features

- **Local MP3 Library** — Automatically scans the script's directory for `.mp3` files.
- **Metadata Display** — Reads ID3 tags (title, artist, album) and shows track duration and file size.
- **Playback Controls** — Play, pause, stop, next, and previous track support.
- **Progress Bar** — Real-time playback progress with percentage.
- **Volume Control** — Adjustable volume with visual feedback.
- **Keyboard Shortcuts** — Full keyboard control for hands-free operation.
- **Track Deletion** — Remove unwanted MP3 files directly from the playlist.
- **Responsive UI** — Split-pane layout with playlist on the left and track info on the right.

---

## Requirements

- Python 3.9+
- [textual](https://pypi.org/project/textual/)
- [pygame](https://pypi.org/project/pygame/)
- [mutagen](https://pypi.org/project/mutagen/)

---

## 🚀 Installation

1. Clone or download this repository.
2. Install the dependencies:

```bash
pip install textual pygame mutagen
```

3. Place your `.mp3` files in the same directory as `app.py`.

---

## 🎮 Usage

Run the application:

```bash
python app.py
```

The player will scan the current directory for MP3 files and display them in the playlist. Select a track and press **Enter** or **Space** to start playback.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Play selected track |
| `Space` | Toggle play / pause |
| `S` | Stop playback |
| `N` | Next track |
| `P` | Previous track |
| `↑` | Volume up |
| `↓` | Volume down |
| `Delete` | Delete selected MP3 file |
| `?` | Show help |
| `Q` | Quit application |

---

## 📁 Project Structure

```
.
├── app.py          # Main application entry point
├── style.tcss      # Textual stylesheet (UI styling)
└── *.mp3           # Your music files
```

---

## Tech Stack

- **Textual** — Modern Python framework for building terminal user interfaces.
- **Pygame Mixer** — Cross-platform audio playback.
- **Mutagen** — MP3 metadata (ID3 tag) reading.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


