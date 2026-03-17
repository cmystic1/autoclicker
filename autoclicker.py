"""
AUTOCLICKER — GUI Edition
=========================================
Requirements (one-time setup):
  pip install pynput pywin32

How to run:
  python autoclicker.py

Features:
  - Unlimited keys, press to capture
  - Reorder / remove keys freely
  - Any interval (min 10 ms)
  - Pick a window — keys sent in background
    (no need to keep the window focused)
  - F6 = Start/Stop from anywhere
  - F8 = Quit
=========================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

# ── dependency check ──────────────────────────────────────────

try:
    import ctypes
    import win32api, win32con, win32gui, win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    from pynput import keyboard as _pkb
    from pynput.keyboard import Key, Controller
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

# ── key tables ────────────────────────────────────────────────

# tkinter keysym → Windows Virtual Key code
_VK: dict[str, int] = {
    'space':      0x20, 'Return':     0x0D, 'Tab':        0x09,
    'BackSpace':  0x08, 'Escape':     0x1B, 'Delete':     0x2E,
    'Insert':     0x2D, 'Home':       0x24, 'End':        0x23,
    'Prior':      0x21, 'Next':       0x22,
    'Up':         0x26, 'Down':       0x28,
    'Left':       0x25, 'Right':      0x27,
    'Shift_L':    0x10, 'Shift_R':    0x10,
    'Control_L':  0x11, 'Control_R':  0x11,
    'Alt_L':      0x12, 'Alt_R':      0x12,
    'caps_lock':  0x14, 'Num_Lock':   0x90,
    **{f'F{i}': 0x6F + i for i in range(1, 13)},   # F1=0x70 … F12=0x7B
}

# tkinter keysym → pynput Key (built only if pynput present)
_PYNPUT: dict = {}
if HAS_PYNPUT:
    _PYNPUT = {
        'space':     Key.space,     'Return':    Key.enter,
        'Tab':       Key.tab,       'BackSpace':  Key.backspace,
        'Escape':    Key.esc,       'Delete':    Key.delete,
        'Up':        Key.up,        'Down':      Key.down,
        'Left':      Key.left,      'Right':     Key.right,
        'Home':      Key.home,      'End':       Key.end,
        'Prior':     Key.page_up,   'Next':      Key.page_down,
        'Shift_L':   Key.shift,     'Shift_R':   Key.shift_r,
        'Control_L': Key.ctrl,      'Control_R': Key.ctrl_r,
        'Alt_L':     Key.alt,       'Alt_R':     Key.alt_r,
        'caps_lock': Key.caps_lock,
        **{f'F{i}': getattr(Key, f'f{i}') for i in range(1, 13)},
    }

# Human-friendly labels
_NAMES: dict[str, str] = {
    'space': 'Space', 'Return': 'Enter', 'Tab': 'Tab',
    'BackSpace': 'Backspace', 'Escape': 'Esc', 'Delete': 'Del',
    'Insert': 'Ins', 'Home': 'Home', 'End': 'End',
    'Prior': 'PgUp', 'Next': 'PgDn',
    'Up': '↑', 'Down': '↓', 'Left': '←', 'Right': '→',
    'Shift_L': 'Shift', 'Shift_R': 'RShift',
    'Control_L': 'Ctrl', 'Control_R': 'RCtrl',
    'Alt_L': 'Alt', 'Alt_R': 'RAlt',
    'caps_lock': 'CapsLk', 'Num_Lock': 'NumLk',
    **{f'F{i}': f'F{i}' for i in range(1, 13)},
}

def _display(ks: str, ch: str) -> str:
    if ks in _NAMES:
        return _NAMES[ks]
    if ch and len(ch) == 1 and ch.isprintable():
        return ch
    return ks

def _to_vk(ks: str, ch: str):
    if ks in _VK:
        return _VK[ks]
    c = ch if (ch and len(ch) == 1) else (ks if len(ks) == 1 else None)
    return ord(c.upper()) if c else None

def _to_pk(ks: str, ch: str):
    if ks in _PYNPUT:
        return _PYNPUT[ks]
    c = ch if (ch and len(ch) == 1) else (ks if len(ks) == 1 else None)
    return c if c else None

# ── win32 helpers ─────────────────────────────────────────────

def _post_key(hwnd: int, vk: int, ch: str) -> None:
    """Send a key to a background window.

    Uses AttachThreadInput + SetFocus so the target window's input queue
    believes it is focused, which makes key delivery reliable for most
    desktop apps even when they are not the foreground window.
    """
    sc  = win32api.MapVirtualKey(vk, 0)
    dn  = (sc << 16) | 1
    up  = (sc << 16) | 0xC0000001

    cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    tgt_tid = win32process.GetWindowThreadProcessId(hwnd)[0]

    attached = False
    if cur_tid != tgt_tid:
        attached = bool(ctypes.windll.user32.AttachThreadInput(cur_tid, tgt_tid, True))

    try:
        ctypes.windll.user32.SetFocus(hwnd)
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, dn)
        if ch and len(ch) == 1 and ch.isprintable():
            win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(ch), dn)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, up)
    finally:
        if attached:
            ctypes.windll.user32.AttachThreadInput(cur_tid, tgt_tid, False)

# Window class names used by common browsers (all Chromium-based + Firefox)
_BROWSER_CLASSES = {'Chrome_WidgetWin_1', 'MozillaWindowClass', 'Chrome_WidgetWin_0'}

def _is_browser(hwnd: int) -> bool:
    try:
        return win32gui.GetClassName(hwnd) in _BROWSER_CLASSES
    except Exception:
        return False

def _list_windows() -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if t:
                out.append((hwnd, t))
    win32gui.EnumWindows(cb, None)
    return sorted(out, key=lambda x: x[1].lower())

# ── colours ───────────────────────────────────────────────────

BG   = '#1e1e2e'
SURF = '#313244'
FG   = '#cdd6f4'
DIM  = '#6c7086'
ACC  = '#cba6f7'
BLUE = '#89b4fa'
GRN  = '#a6e3a1'
RED  = '#f38ba8'
YLW  = '#f9e2af'

# ── App ───────────────────────────────────────────────────────

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('Autoclicker')
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.keys: list[dict] = []
        self.running = False
        self._lock = threading.Lock()
        self.count = 0
        self.win_list: list[tuple[int, str]] = []
        self.target_hwnd: int | None = None

        self._build_ui()
        self._start_hotkey_listener()
        self.root.protocol('WM_DELETE_WINDOW', self._quit)

    # ── helpers ───────────────────────────────────────────────

    def _lbl(self, p, text, **kw):
        kw.setdefault('bg', BG); kw.setdefault('fg', FG)
        kw.setdefault('font', ('Segoe UI', 9))
        return tk.Label(p, text=text, **kw)

    def _btn(self, p, text, cmd, bg=SURF, fg=FG, **kw):
        return tk.Button(p, text=text, command=cmd,
                         bg=bg, fg=fg, font=('Segoe UI', 9),
                         relief='flat', padx=8, pady=4,
                         cursor='hand2', activebackground=ACC, **kw)

    def _section(self, p, text):
        tk.Label(p, text=text, font=('Segoe UI', 8, 'bold'),
                 bg=BG, fg=DIM).pack(anchor='w', pady=(12, 2))

    # ── UI build ──────────────────────────────────────────────

    def _build_ui(self):
        # header stripe
        tk.Frame(self.root, bg=ACC, height=3).pack(fill='x')
        tk.Label(self.root, text='AUTOCLICKER',
                 font=('Segoe UI', 16, 'bold'), bg=BG, fg=ACC).pack(pady=(12, 1))
        tk.Label(self.root,
                 text='Unlimited keys  ·  Custom interval  ·  Background window targeting',
                 font=('Segoe UI', 8), bg=BG, fg=DIM).pack(pady=(0, 10))

        body = tk.Frame(self.root, bg=BG, padx=20)
        body.pack(fill='both', expand=True)

        # ── key sequence ──────────────────────────────────────
        self._section(body, 'KEY SEQUENCE')

        seq_card = tk.Frame(body, bg=SURF, padx=8, pady=8)
        seq_card.pack(fill='x')

        list_row = tk.Frame(seq_card, bg=SURF)
        list_row.pack(fill='x')

        self.listbox = tk.Listbox(
            list_row, height=6,
            bg=SURF, fg=FG,
            selectbackground=BLUE, selectforeground=BG,
            font=('Consolas', 10), relief='flat', activestyle='underline', bd=0)
        self.listbox.pack(side='left', fill='both', expand=True)

        sb = tk.Scrollbar(list_row, orient='vertical', command=self.listbox.yview)
        sb.pack(side='right', fill='y')
        self.listbox.configure(yscrollcommand=sb.set)

        br = tk.Frame(seq_card, bg=SURF)
        br.pack(fill='x', pady=(6, 0))
        self._btn(br, '+ Add Key',       self._add_key_dialog, bg=BLUE, fg=BG).pack(side='left', padx=(0, 3))
        self._btn(br, '↑',               self._move_up                        ).pack(side='left', padx=2)
        self._btn(br, '↓',               self._move_down                      ).pack(side='left', padx=2)
        self._btn(br, 'Remove Selected', self._remove_selected, bg=RED,  fg=BG).pack(side='left', padx=(3, 0))
        self._btn(br, 'Clear All',       self._clear_keys,      bg=RED,  fg=BG).pack(side='left', padx=3)

        # ── interval ──────────────────────────────────────────
        self._section(body, 'INTERVAL')

        iv = tk.Frame(body, bg=BG)
        iv.pack(anchor='w')
        self.interval_var = tk.StringVar(value='500')
        tk.Entry(iv, textvariable=self.interval_var, width=7,
                 font=('Consolas', 11), justify='center',
                 bg=SURF, fg=FG, insertbackground=FG, relief='flat').pack(side='left')
        self._lbl(iv, '  ms  between each key press').pack(side='left')

        pf = tk.Frame(body, bg=BG)
        pf.pack(anchor='w', pady=(4, 0))
        self._lbl(pf, 'Quick: ', fg=DIM, font=('Segoe UI', 8)).pack(side='left')
        for label, ms in [('100ms', 100), ('300ms', 300), ('500ms', 500),
                           ('1s', 1000), ('3s', 3000), ('5s', 5000)]:
            v = ms
            tk.Button(pf, text=label,
                      command=lambda x=v: self.interval_var.set(str(x)),
                      font=('Segoe UI', 8), bg=SURF, fg=FG, relief='flat',
                      padx=6, pady=2, cursor='hand2',
                      activebackground=BLUE).pack(side='left', padx=2)

        # ── target window ─────────────────────────────────────
        self._section(body, 'TARGET WINDOW')

        if HAS_WIN32:
            wf = tk.Frame(body, bg=BG)
            wf.pack(fill='x', pady=(0, 2))

            self.window_var = tk.StringVar()
            s = ttk.Style()
            s.theme_use('clam')
            s.configure('AC.TCombobox',
                        fieldbackground=SURF, background=SURF,
                        foreground=FG, arrowcolor=FG,
                        selectbackground=BLUE, selectforeground=BG)
            self.win_combo = ttk.Combobox(
                wf, textvariable=self.window_var,
                state='readonly', style='AC.TCombobox',
                font=('Consolas', 9), width=46)
            self.win_combo.pack(side='left', padx=(0, 6))
            self.win_combo.bind('<<ComboboxSelected>>', self._on_win_sel)

            self._btn(wf, '⟳ Refresh', self._refresh_wins).pack(side='left')

            self._win_hint = self._lbl(body, '',
                                       fg=DIM, font=('Segoe UI', 8),
                                       wraplength=460, justify='left')
            self._win_hint.pack(anchor='w', pady=(2, 0))

            self._refresh_wins()
        else:
            self._lbl(body,
                      '⚠  pywin32 not found. Run:  pip install pywin32  to enable background '
                      'window targeting.',
                      fg=YLW, font=('Segoe UI', 8),
                      wraplength=460, justify='left').pack(anchor='w')

        # ── start / stop ──────────────────────────────────────
        cf = tk.Frame(body, bg=BG)
        cf.pack(pady=14)

        self.start_btn = tk.Button(
            cf, text='▶  START', command=self._start,
            font=('Segoe UI', 13, 'bold'), bg=GRN, fg=BG,
            relief='flat', padx=28, pady=10, cursor='hand2')
        self.start_btn.pack(side='left', padx=(0, 10))

        self.stop_btn = tk.Button(
            cf, text='■  STOP', command=self._stop,
            font=('Segoe UI', 13, 'bold'), bg=RED, fg=BG,
            relief='flat', padx=28, pady=10, cursor='hand2', state='disabled')
        self.stop_btn.pack(side='left')

        # ── status bar ────────────────────────────────────────
        sb2 = tk.Frame(body, bg=SURF, pady=6)
        sb2.pack(fill='x')
        sb2.columnconfigure(1, weight=1)

        self.dot = tk.Label(sb2, text='●', font=('Segoe UI', 14), bg=SURF, fg=DIM)
        self.dot.grid(row=0, column=0, padx=(12, 6))

        self.status_var = tk.StringVar(value='Stopped')
        tk.Label(sb2, textvariable=self.status_var,
                 font=('Segoe UI', 10, 'bold'), bg=SURF, fg=FG).grid(row=0, column=1, sticky='w')

        self.count_var = tk.StringVar(value='0 keys sent')
        tk.Label(sb2, textvariable=self.count_var,
                 font=('Consolas', 9), bg=SURF, fg=DIM).grid(row=0, column=2, padx=12)

        # footer hint
        self._lbl(body, 'F6 = Start / Stop   ·   F8 = Quit',
                  fg='#45475a', font=('Segoe UI', 8)).pack(pady=(8, 14))

    # ── key list ──────────────────────────────────────────────

    def _refresh_list(self):
        self.listbox.delete(0, 'end')
        for i, k in enumerate(self.keys):
            self.listbox.insert('end', f'  {i+1:>2}.  {k["label"]}')

    def _add_key_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title('Add Key')
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.focus_force()

        tk.Label(dlg, text='Press any key to capture it',
                 font=('Segoe UI', 12, 'bold'), bg=BG, fg=FG).pack(padx=40, pady=(20, 4))
        tk.Label(dlg, text='or type a key name in the box below (e.g. space, f1, up)',
                 font=('Segoe UI', 8), bg=BG, fg=DIM).pack()

        # big preview label
        pv = tk.StringVar(value='—')
        tk.Label(dlg, textvariable=pv, font=('Consolas', 28, 'bold'),
                 bg=SURF, fg=ACC, width=10, pady=14, anchor='center').pack(
            padx=40, pady=12, fill='x')

        cap: dict = {'ks': None, 'ch': ''}

        def on_key(e: tk.Event):
            ks = e.keysym
            ch = e.char if (e.char and e.char.isprintable()) else ''
            cap['ks'] = ks
            cap['ch'] = ch
            pv.set(_display(ks, ch))

        dlg.bind('<Key>', on_key)

        tk.Label(dlg, text='or type manually:',
                 font=('Segoe UI', 8), bg=BG, fg=DIM).pack()
        typed_var = tk.StringVar()
        tk.Entry(dlg, textvariable=typed_var, font=('Consolas', 11),
                 width=16, justify='center', bg=SURF, fg=FG,
                 insertbackground=FG, relief='flat').pack(pady=4)

        def confirm():
            ks = cap['ks']
            ch = cap['ch']
            t = typed_var.get().strip()
            if not ks and t:
                ks = t
                ch = t if len(t) == 1 else ''
            if not ks:
                messagebox.showwarning('No key', 'Press a key or type one.', parent=dlg)
                return
            vk = _to_vk(ks, ch) if HAS_WIN32 else None
            pk = _to_pk(ks, ch) if HAS_PYNPUT else None
            label = _display(ks, ch)
            self.keys.append({'keysym': ks, 'char': ch, 'label': label, 'vk': vk, 'pk': pk})
            self._refresh_list()
            dlg.destroy()

        br = tk.Frame(dlg, bg=BG)
        br.pack(pady=14)
        tk.Button(br, text='Add This Key', command=confirm,
                  font=('Segoe UI', 10, 'bold'), bg=GRN, fg=BG,
                  relief='flat', padx=16, pady=6, cursor='hand2').pack(side='left', padx=4)
        tk.Button(br, text='Cancel', command=dlg.destroy,
                  font=('Segoe UI', 10), bg=SURF, fg=FG,
                  relief='flat', padx=12, pady=6, cursor='hand2').pack(side='left', padx=4)

        dlg.bind('<Return>', lambda e: confirm())
        dlg.bind('<Escape>', lambda e: dlg.destroy())

    def _move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.keys[i-1], self.keys[i] = self.keys[i], self.keys[i-1]
        self._refresh_list()
        self.listbox.selection_set(i-1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.keys) - 1:
            return
        i = sel[0]
        self.keys[i], self.keys[i+1] = self.keys[i+1], self.keys[i]
        self._refresh_list()
        self.listbox.selection_set(i+1)

    def _remove_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        self.keys.pop(sel[0])
        self._refresh_list()

    def _clear_keys(self):
        self.keys.clear()
        self._refresh_list()

    # ── window targeting ──────────────────────────────────────

    def _refresh_wins(self):
        self.win_list = _list_windows()
        entries = ['⊙  Active window (auto-focus)'] + [t for _, t in self.win_list]
        self.win_combo['values'] = entries
        if self.window_var.get() not in entries:
            self.window_var.set(entries[0])
            self.target_hwnd = None
        self._on_win_sel()

    def _on_win_sel(self, _=None):
        sel = self.window_var.get()
        if sel.startswith('⊙') or not sel:
            self.target_hwnd = None
            self._win_hint.config(
                text='Keys follow whichever window you click into (normal focus behaviour).',
                fg=DIM)
            return
        for hwnd, title in self.win_list:
            if title == sel:
                self.target_hwnd = hwnd
                if _is_browser(hwnd):
                    self._win_hint.config(
                        text='⚠  Browser window selected. All tabs inside it share one window '
                             'handle, so keys always go to whichever tab is currently visible in '
                             'that browser window — not a specific background tab.\n'
                             'Fix: move the game/app tab to its own window '
                             '(right-click the tab → "Move tab to new window"), '
                             'then re-select it here.',
                        fg=YLW)
                else:
                    self._win_hint.config(
                        text='✓  Background mode active — keys go to this window silently, '
                             'no need to keep it focused.',
                        fg=GRN)
                return
        self.target_hwnd = None

    # ── autoclicker core ──────────────────────────────────────

    def _interval_s(self) -> float:
        try:
            return max(10.0, float(self.interval_var.get())) / 1000.0
        except ValueError:
            return 0.5

    def _start(self):
        if not self.keys:
            messagebox.showwarning('No Keys',
                                   'Add at least one key to the sequence first.')
            return
        if self.running:
            return
        with self._lock:
            self.running = True
            self.count = 0
        self.count_var.set('0 keys sent')
        self.status_var.set('Running')
        self.dot.config(fg=GRN)
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        threading.Thread(target=self._loop, daemon=True).start()

    def _stop(self):
        with self._lock:
            self.running = False
        self.status_var.set('Stopped')
        self.dot.config(fg=DIM)
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def _loop(self):
        ctrl = Controller() if HAS_PYNPUT else None
        idx = 0
        while True:
            with self._lock:
                if not self.running:
                    break
                if not self.keys:
                    self.running = False
                    break
                k    = self.keys[idx % len(self.keys)]
                idx += 1
                self.count += 1
                c    = self.count
                hwnd = self.target_hwnd

            interval = self._interval_s()

            try:
                if HAS_WIN32 and hwnd:
                    vk = k['vk']
                    if vk:
                        _post_key(hwnd, vk, k['char'])
                elif HAS_PYNPUT and ctrl:
                    pk = k['pk']
                    if pk:
                        ctrl.press(pk)
                        ctrl.release(pk)
            except Exception:
                pass

            self.root.after(0, self.count_var.set, f'{c:,} keys sent')
            time.sleep(interval)

        # if loop exited because keys were cleared, reset UI
        self.root.after(0, self._stop)

    # ── global F6/F8 hotkeys ──────────────────────────────────

    def _start_hotkey_listener(self):
        if not HAS_PYNPUT:
            return

        def _on(key):
            try:
                if key == Key.f6:
                    if self.running:
                        self.root.after(0, self._stop)
                    else:
                        self.root.after(0, self._start)
                elif key == Key.f8:
                    self.root.after(0, self._quit)
            except Exception:
                pass

        t = _pkb.Listener(on_press=_on)
        t.daemon = True
        t.start()

    def _quit(self):
        with self._lock:
            self.running = False
        self.root.destroy()


# ── entry point ───────────────────────────────────────────────

def main():
    if not HAS_PYNPUT and not HAS_WIN32:
        import sys
        print('Missing dependencies. Run:  pip install pynput pywin32')
        sys.exit(1)

    root = tk.Tk()
    root.minsize(520, 540)
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
