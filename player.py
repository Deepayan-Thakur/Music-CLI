import curses
import time
import threading
import random
import re

# ----------------------------------------------------------------------------
# REQUIREMENTS:
# pip install python-vlc yt-dlp syncedlyrics windows-curses
# Note: Requires VLC Media Player to be installed on your OS.
# ----------------------------------------------------------------------------

try:
    import vlc
    import yt_dlp
    import syncedlyrics
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install python-vlc yt-dlp syncedlyrics windows-curses")
    raise SystemExit(1)


class CLIMusicPlayer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.stdscr.nodelay(1)
        self.stdscr.timeout(100)  # 100ms UI refresh
        self.stdscr.keypad(True)

        self.vlc_instance = vlc.Instance("--no-video --quiet")
        self.player = self.vlc_instance.media_player_new()

        self.playlist = []
        self.current_idx = 0
        self.volume = 70
        self.player.audio_set_volume(self.volume)

        self.is_playing = False
        self.loop = False
        self.shuffle = False
        self.speed = 1.0

        self.mode = "search"
        self.search_query = ""
        self.status_msg = "Welcome to CLI Music Player!"

        # Lyrics state
        self.lyrics = []  # list of (timestamp_sec, lyric_text)
        self.current_song_key = None
        self.lyrics_lock = threading.Lock()

        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)    # Playing
        curses.init_pair(2, curses.COLOR_CYAN, -1)     # Progress
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Lyrics Highlight
        curses.init_pair(4, curses.COLOR_MAGENTA, -1)  # Titles

        self.main_loop()

    def set_status(self, msg):
        self.status_msg = msg

    def safe_addstr(self, y, x, text, attr=0):
        """Safely add text without crashing on small terminals."""
        h, w = self.stdscr.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        text = str(text)
        if x < 0:
            x = 0
        max_len = max(0, w - x - 1)
        if max_len <= 0:
            return
        try:
            self.stdscr.addstr(y, x, text[:max_len], attr)
        except curses.error:
            pass

    def clean_title(self, title):
        """Remove common extra metadata from titles to improve lyric matching."""
        title = re.sub(r"\s*\(.*?official.*?\)\s*", " ", title, flags=re.I)
        title = re.sub(r"\s*\[.*?official.*?\]\s*", " ", title, flags=re.I)
        title = re.sub(r"\s*\(.*?lyrics.*?\)\s*", " ", title, flags=re.I)
        title = re.sub(r"\s*\[.*?lyrics.*?\]\s*", " ", title, flags=re.I)
        title = re.sub(r"\s*\(.*?audio.*?\)\s*", " ", title, flags=re.I)
        title = re.sub(r"\s*\[.*?audio.*?\]\s*", " ", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip()
        return title

    def build_lyrics_queries(self, song):
        title = self.clean_title(song.get("title", ""))
        uploader = song.get("uploader", "").strip()

        queries = []
        candidates = [
            f"{title} {uploader}".strip(),
            title,
            f"{uploader} {title}".strip(),
        ]

        for q in candidates:
            if q and q not in queries:
                queries.append(q)

        return queries

    def parse_lrc(self, lrc_text):
        """
        Parse LRC content into a sorted list of (time_in_seconds, line_text).
        Supports multiple timestamps on the same line.
        """
        parsed = []

        for raw_line in lrc_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Skip metadata tags like [ar:], [ti:], [by:], etc.
            if re.match(r"^\[(ar|al|ti|by|offset|length|re|ve):", line, flags=re.I):
                continue

            timestamps = re.findall(r"\[(\d+):(\d+(?:\.\d+)?)\]", line)
            text = re.sub(r"(\[\d+:\d+(?:\.\d+)?\])+", "", line).strip()

            if not timestamps or not text:
                continue

            for m, s in timestamps:
                sec = int(m) * 60 + float(s)
                parsed.append((sec, text))

        parsed.sort(key=lambda x: (x[0], x[1]))

        # De-duplicate exact timestamp/text duplicates
        deduped = []
        seen = set()
        for t, txt in parsed:
            key = (round(t, 2), txt)
            if key not in seen:
                seen.add(key)
                deduped.append((t, txt))

        return deduped

    def search_and_add(self, query):
        self.set_status(f"Searching for '{query}'...")
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "extract_flat": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)

                if "entries" in info and len(info["entries"]) > 0:
                    entry = info["entries"][0]

                    song = {
                        "title": entry.get("title", "Unknown"),
                        "url": entry.get("url"),
                        "duration": entry.get("duration", 0),
                        "id": entry.get("id"),
                        "uploader": entry.get("uploader", "Unknown"),
                        "webpage_url": entry.get("webpage_url") or entry.get("original_url") or entry.get("url"),
                    }

                    self.playlist.append(song)
                    self.set_status(f"Added: {song['title']}")

                    if len(self.playlist) == 1:
                        self.play_song(0)
                else:
                    self.set_status("No results found.")
        except Exception as e:
            self.set_status(f"Search error: {str(e)[:60]}")

    def download_current(self):
        if not self.playlist:
            return

        song = self.playlist[self.current_idx]
        self.set_status(f"Downloading {song['title'][:20]}...")

        def dl():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{song['title'][:30]}.%(ext)s",
                "quiet": True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    target = song.get("webpage_url") or song.get("url")
                    if target:
                        ydl.download([target])
                        self.set_status(f"Downloaded: {song['title'][:20]}")
                    else:
                        self.set_status("Download failed: missing URL")
            except Exception as e:
                self.set_status(f"Download failed: {str(e)[:40]}")

        threading.Thread(target=dl, daemon=True).start()

    def fetch_lyrics(self, song, song_key):
        """
        Fetch synced lyrics for the given song and only apply them if the
        current song is still the same by the time the fetch finishes.
        """
        queries = self.build_lyrics_queries(song)

        with self.lyrics_lock:
            self.lyrics = []

        self.set_status("Fetching synced lyrics...")

        for query in queries:
            if self.current_song_key != song_key:
                return

            try:
                lrc = syncedlyrics.search(query)
                if lrc:
                    parsed = self.parse_lrc(lrc)
                    if parsed:
                        if self.current_song_key == song_key:
                            with self.lyrics_lock:
                                self.lyrics = parsed
                            self.set_status("Synced lyrics loaded.")
                        return
            except Exception:
                continue

        if self.current_song_key == song_key:
            with self.lyrics_lock:
                self.lyrics = [(0, "No synced lyrics found.")]
            self.set_status("No synced lyrics found.")

    def play_song(self, idx):
        if idx >= len(self.playlist) or idx < 0:
            return

        self.current_idx = idx
        song = self.playlist[idx]

        # Unique key prevents old lyric threads from overwriting the current song
        self.current_song_key = song.get("id") or f"{song.get('title', '')}|{song.get('uploader', '')}"

        # Prepare VLC
        media = self.vlc_instance.media_new(song["url"])
        self.player.set_media(media)
        self.player.play()
        self.player.set_rate(self.speed)
        self.player.audio_set_volume(self.volume)

        self.is_playing = True
        self.set_status(f"Playing: {song['title'][:30]}")

        # Fetch lyrics in the background
        threading.Thread(
            target=self.fetch_lyrics,
            args=(song, self.current_song_key),
            daemon=True,
        ).start()

    def toggle_play(self):
        if self.is_playing:
            self.player.pause()
            self.set_status("Paused")
        else:
            self.player.play()
            self.set_status("Playing")
        self.is_playing = not self.is_playing

    def get_active_lyric_index(self, curr_time):
        with self.lyrics_lock:
            if not self.lyrics:
                return 0

            active_idx = 0
            for i, (l_time, _) in enumerate(self.lyrics):
                if curr_time >= l_time:
                    active_idx = i
                else:
                    break
            return active_idx

    def draw(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()

        # Header
        header = (
            f" PY-CLI MUSIC PLAYER | Vol: {self.volume}% | Speed: {self.speed}x | "
            f"Mode: {'Shuffle' if self.shuffle else 'Normal'} "
        )
        self.safe_addstr(0, max(0, (w - len(header)) // 2), header, curses.A_REVERSE)

        # Player info
        if self.playlist:
            song = self.playlist[self.current_idx]

            self.safe_addstr(2, 2, f"Title : {song['title'][:w-10]}", curses.color_pair(2) | curses.A_BOLD)
            self.safe_addstr(3, 2, f"Artist: {song['uploader'][:w-10]}")

            curr_time = max(0.0, self.player.get_time() / 1000.0)
            dur = float(song["duration"] or 0)

            # Use VLC length if YouTube duration is missing
            if dur <= 0:
                vlc_len = self.player.get_length()
                if vlc_len and vlc_len > 0:
                    dur = vlc_len / 1000.0
                else:
                    dur = max(curr_time, 1.0)

            progress = min(1.0, curr_time / dur) if dur > 0 else 0.0

            bar_w = max(10, w - 25)
            filled = int(bar_w * progress)
            bar = "[" + "=" * filled + "-" * (bar_w - filled) + "]"
            time_str = f" {int(curr_time // 60):02d}:{int(curr_time % 60):02d}/{int(dur // 60):02d}:{int(dur % 60):02d} "
            self.safe_addstr(5, 2, bar + time_str, curses.color_pair(1))

            # Auto-next / loop logic
            state = self.player.get_state()
            if state == vlc.State.Ended:
                if self.loop:
                    self.play_song(self.current_idx)
                else:
                    next_i = random.randint(0, len(self.playlist) - 1) if self.shuffle else self.current_idx + 1
                    if next_i < len(self.playlist):
                        self.play_song(next_i)
                    elif self.playlist:
                        self.play_song(0)

        # Lyrics
        with self.lyrics_lock:
            lyrics_snapshot = list(self.lyrics)

        if lyrics_snapshot:
            lyric_y = 8
            self.safe_addstr(lyric_y - 1, 2, "--- SYNCED LYRICS ---", curses.color_pair(4))

            curr_time = max(0.0, self.player.get_time() / 1000.0)
            active_idx = self.get_active_lyric_index(curr_time)

            start_idx = max(0, active_idx - 2)
            end_idx = min(len(lyrics_snapshot), active_idx + 3)

            for i in range(start_idx, end_idx):
                if lyric_y >= h - 6:
                    break

                text = lyrics_snapshot[i][1][:w - 4]
                x = max(2, (w - len(text)) // 2)

                if i == active_idx:
                    self.safe_addstr(lyric_y, x, text, curses.color_pair(3) | curses.A_BOLD)
                else:
                    self.safe_addstr(lyric_y, x, text, curses.A_DIM)

                lyric_y += 1

        # Status / controls
        self.safe_addstr(h - 3, 2, f"Status: {self.status_msg}", curses.color_pair(4) | curses.A_BOLD)
        help_txt = (
            "Controls: [s]Search  [SPACE]Play/Pause  [n]Next  [b]Prev  "
            "[↑/↓]Vol  [</>]Speed  [l]Loop  [r]Shuffle  [d]Download  [q]Quit"
        )
        self.safe_addstr(h - 2, 2, help_txt[:w - 4])

        if self.mode == "search":
            self.safe_addstr(h - 4, 2, f"Search YouTube: {self.search_query}_", curses.color_pair(2))

        self.stdscr.refresh()

    def main_loop(self):
        while True:
            self.draw()

            try:
                c = self.stdscr.getch()
            except Exception:
                c = -1

            if c != -1:
                if self.mode == "search":
                    if c == 27:  # ESC
                        self.mode = "idle"
                    elif c in (10, 13):  # Enter
                        if self.search_query.strip():
                            q = self.search_query.strip()
                            threading.Thread(target=self.search_and_add, args=(q,), daemon=True).start()
                        self.search_query = ""
                        self.mode = "idle"
                    elif c in (curses.KEY_BACKSPACE, 8, 127):
                        self.search_query = self.search_query[:-1]
                    elif 32 <= c <= 126:
                        self.search_query += chr(c)
                else:
                    if c == ord("q"):
                        break
                    elif c == ord("s"):
                        self.mode = "search"
                    elif c == ord(" "):
                        self.toggle_play()
                    elif c == curses.KEY_UP:
                        self.volume = min(100, self.volume + 5)
                        self.player.audio_set_volume(self.volume)
                    elif c == curses.KEY_DOWN:
                        self.volume = max(0, self.volume - 5)
                        self.player.audio_set_volume(self.volume)
                    elif c == ord(">"):
                        self.speed = min(2.0, self.speed + 0.25)
                        self.player.set_rate(self.speed)
                    elif c == ord("<"):
                        self.speed = max(0.25, self.speed - 0.25)
                        self.player.set_rate(self.speed)
                    elif c == ord("l"):
                        self.loop = not self.loop
                        self.set_status(f"Loop {'On' if self.loop else 'Off'}")
                    elif c == ord("r"):
                        self.shuffle = not self.shuffle
                        self.set_status(f"Shuffle {'On' if self.shuffle else 'Off'}")
                    elif c == ord("d"):
                        self.download_current()
                    elif c == ord("n"):
                        if self.playlist:
                            next_i = random.randint(0, len(self.playlist) - 1) if self.shuffle else (self.current_idx + 1) % len(self.playlist)
                            self.play_song(next_i)
                    elif c == ord("b"):
                        if self.playlist:
                            prev_i = (self.current_idx - 1) % len(self.playlist)
                            self.play_song(prev_i)

            time.sleep(0.05)


if __name__ == "__main__":
    curses.wrapper(CLIMusicPlayer)