# 🎧 CLI Music Player (Python)

A powerful, terminal-based music player built with Python that streams audio directly from YouTube, displays **real-time synced lyrics**, and provides an interactive keyboard-driven experience — all inside your CLI.

This isn’t just a basic player. It’s a full-featured, real-time system combining streaming, threading, terminal UI rendering, and lyric synchronization.

---

## 🚀 Features

* 🔍 **YouTube Search & Stream**

  * Instantly search and play songs without downloading

* 🎵 **Real-Time Audio Playback**

  * Powered by VLC for smooth and stable streaming

* 📝 **Synced Lyrics Display**

  * Parses LRC format and highlights lyrics in sync with playback

* 🎚️ **Playback Controls**

  * Play/Pause, Next/Previous, Volume Control
  * Speed adjustment (0.25x → 2.0x)

* 🔁 **Loop & Shuffle Modes**

  * Seamless playlist control

* 📥 **Download Songs**

  * Save currently playing track locally

* 🖥️ **Interactive CLI UI**

  * Built using `curses` with dynamic rendering

* ⚡ **Multithreading**

  * Non-blocking search, playback, and lyric fetching

---

## 🛠️ Tech Stack

* **Python**
* **VLC (python-vlc)** – audio playback engine
* **yt-dlp** – YouTube streaming & downloading
* **syncedlyrics** – synced lyrics fetching
* **curses** – terminal UI rendering
* **threading** – async operations

---

## 📦 Installation

### 1. Install Dependencies

```bash
pip install python-vlc yt-dlp syncedlyrics windows-curses
```

### 2. Install VLC Media Player

Download and install VLC from:
👉 [https://www.videolan.org/vlc/](https://www.videolan.org/vlc/)

---

## ▶️ Usage

Run the player:

```bash
python your_script_name.py
```

---

## 🎮 Controls

| Key       | Action                |
| --------- | --------------------- |
| `s`       | Search song           |
| `SPACE`   | Play / Pause          |
| `n`       | Next track            |
| `b`       | Previous track        |
| `↑ / ↓`   | Volume control        |
| `>` / `<` | Speed control         |
| `l`       | Toggle Loop           |
| `r`       | Toggle Shuffle        |
| `d`       | Download current song |
| `q`       | Quit                  |

---

## 🧠 How It Works

* Uses **yt-dlp** to fetch streaming URLs from YouTube
* Streams audio via **VLC media player instance**
* Fetches synced lyrics using **syncedlyrics API**
* Parses `.lrc` timestamps → aligns with playback time
* Displays dynamic UI using **curses rendering loop**
* Handles async tasks with **threading** to avoid UI blocking

---

## ⚠️ Requirements

* Python 3.8+
* VLC installed on system
* Stable internet connection

---

## 💡 Future Improvements

* Playlist persistence (save/load)
* Local file playback support
* Better search UI (multi-result selection)
* Equalizer support
* AI-based lyric translation / summarization

---

## 📌 Known Limitations

* Lyrics depend on availability from external sources
* Terminal UI may behave differently across OS
* Windows requires `windows-curses`

---

## 👨‍💻 Author

**[Deepayan-Thakur](https://github.com/Deepayan-Thakur)**

---
