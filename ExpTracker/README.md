# Fantasia EXP Tracker

A real-time screen-OCR overlay for MapleStory **Fantasia** that reads your EXP
bar, character level, and minimap name directly from the game window, and
automatically logs per-map sessions with EXP/hr stats to a CSV file.

- Auto-detects the game (or Magpie-scaled) window on startup
- Recognises EXP and level digits via pixel-perfect template matching
- Fuzzy-matches minimap text against the full MapleStory map list
- Tracks a session per map, with rolling EXP/hr and time-to-level estimates
- Logs completed map sessions to `exp_sessions.csv`

## Requirements

- **Windows 10 / 11** (the app uses Win32 APIs for window detection)
- **Python 3.10+**
- **Tesseract OCR** — installed separately (see below)

## Installation

1. **Install Tesseract OCR** from the UB Mannheim build:

   https://github.com/UB-Mannheim/tesseract/wiki

   Accept the default install path (`C:\Program Files\Tesseract-OCR\`) and the
   tracker will find it automatically. If you install elsewhere, set
   `"tesseract_path"` in `exp_tracker_config.json` to the full path of
   `tesseract.exe`.

2. **Clone or download this repository.**

3. **Install Python dependencies:**

   ```
   pip install -r requirements.txt
   ```

4. **Run the tracker:**

   ```
   python exp_tracker.py
   ```

## First-run setup

1. Launch Fantasia (and Magpie, if you use it to upscale the window).
2. Launch the tracker. On startup it will auto-detect the EXP and Level
   regions from the game window.
3. Click **SETUP → Set MAP Region**, then drag a box over the map-name text
   on your minimap. (Map position varies, so this one must be set manually.)
4. Enter your character level (or let the level OCR pick it up).
5. Press **START**.

Completed map sessions (≥30 seconds by default) are appended to
`exp_sessions.csv` in the project folder.

## Configuration

Settings live in `exp_tracker_config.json` (created on first run, not
committed to the repo). A reference copy is provided as
`exp_tracker_config.sample.json`.

Notable keys:

| Key | Purpose |
|---|---|
| `tesseract_path` | Full path to `tesseract.exe` if it isn't in a default location |
| `poll_interval_sec` | How often OCR runs (default 1.0) |
| `map_confirm_reads` | Consecutive matching reads required before accepting a map change |
| `min_session_sec` | Sessions shorter than this are not logged to CSV |
| `theme` | `"dark"` or `"maple"` |
| `game_window_title` | Used by auto-detect; defaults to `"Fantasia"` |

## Troubleshooting

- **Map OCR not working** — Tesseract probably isn't installed. A dialog will
  appear on startup if it can't be found. Also check `exp_tracker.log`.
- **EXP reads look wrong** — use the ⚙ menu → **Rebuild Templates** to
  re-capture digit templates from the current game client.
- **Window auto-detect fails** — the game or Magpie window isn't visible yet
  when the tracker starts. Use **SETUP → Auto-detect Regions** after the
  game is up, or set the regions manually.
- **Crashes / unexpected behaviour** — check `exp_tracker.log` next to the
  script for a stack trace.

## Files

- `exp_tracker.py` — main application
- `make_templates.py` — interactive tool to (re)build digit templates
- `detect_window.py` — diagnostic script for window detection issues
- `templates/` — digit templates used for OCR
- `map_names.json` — bundled MapleStory map-name list (extracted from String.wz)
- `exp_sessions.csv` — session log (created on first run, not committed)
- `exp_tracker.log` — runtime log (created on first run, not committed)

## License

MIT — see [LICENSE](LICENSE).
