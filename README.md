# Autoclicker

A simple tool that automatically presses keys for you — on repeat, forever, in any app or game.

---

## Option A — Just use the EXE (no Python needed)

1. Download **`AutoClicker.exe`** from the `dist` folder
2. Double-click it to run — that's it

> Windows Defender or your antivirus may show a warning the first time. This is a common false positive with standalone Python executables. Click **"More info" → "Run anyway"** to proceed.

---

## Option B — Run from source (requires Python)

You need Python installed. If you don't have it:

1. Go to **https://www.python.org/downloads/**
2. Click the big **Download Python** button and install it
3. ⚠️ On the installer screen, tick **"Add Python to PATH"** before clicking Install

Then open **Command Prompt** (press `Win + R`, type `cmd`, press Enter) and run:

```
pip install pynput pywin32
```

That's it. You only do this once.

### How to Run

1. Open the `autoclicker` folder
2. Double-click **`autoclicker.py`**

> If double-clicking doesn't work, right-click it → **Open with** → **Python**

---

## How to Use

### 1. Add your keys

Click **+ Add Key**, then press the key you want on your keyboard.
You'll see a big preview of the key. Click **Add This Key** to confirm.

Repeat for as many keys as you want — no limit.

- Use **↑ ↓** to reorder keys in the sequence
- Click **Remove Selected** to delete one
- Click **Clear All** to start over

### 2. Set the interval

Type a number in the **Interval** box — this is how long (in milliseconds) to wait between each key press.

| Value | Speed |
|-------|-------|
| 100 ms | Very fast (10 presses/sec) |
| 500 ms | Normal (2 presses/sec) |
| 1000 ms | Slow (1 press/sec) |

Or click one of the **Quick** preset buttons.

### 3. Pick a target window (optional)

This lets the autoclicker send keys to a specific app **without you needing to keep it open on screen**.

1. Open the app or game you want to target
2. Click **⟳ Refresh** in the autoclicker
3. Pick your app from the dropdown list
4. Start — the app will keep receiving keys even while you do other things

> **Using a browser game?**
> Browser tabs all share one window, so you can't target a specific tab in the background.
> The fix: right-click the game tab → **"Move tab to new window"** → it gets its own window → select it in the list.

Leave it on **Active window** if you just want to click into an app yourself and have it type there.

### 4. Start / Stop

- Click **▶ START** to begin
- Click **■ STOP** to pause
- Press **F6** anywhere on your keyboard to toggle Start/Stop (even when the autoclicker window isn't focused)
- Press **F8** to quit

---

## Example: Game with skill keys 1, 2, 3, 4

1. Add keys: `1` → `2` → `3` → `4`
2. Set interval to `500` ms
3. Pick your game window from the dropdown
4. Click Start — the game keeps cycling skills while you browse, watch a video, etc.

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| F6  | Start / Stop |
| F8  | Quit the autoclicker |

---

## Troubleshooting

**Windows blocked the EXE / "Windows protected your PC" warning**
→ Click **"More info"** → **"Run anyway"**. This is a false positive common to all self-contained Python executables.

**Antivirus quarantined the EXE**
→ Add an exclusion for the file in your antivirus settings and re-download it.

**Double-clicking the .py file opens Notepad instead of running it**
→ Right-click → Open with → Choose another app → Python

**"pip is not recognized" error**
→ Python wasn't added to PATH during install. Reinstall Python and tick "Add Python to PATH"

**Keys aren't being sent to my game**
→ Some games with anti-cheat block automated input. Try using the autoclicker in Active Window mode and keep the game focused.

**The window I want isn't in the dropdown**
→ Click ⟳ Refresh. If it still doesn't appear, try running the autoclicker as Administrator (right-click → Run as administrator).
