"""C: slide demo driven by finalized labels received over UDP.

    python c_app\\slide_demo.py [--slides DIR] [--port 5005] [--cooldown 0.8]
                                [--neutral-hold 0.6] [--max-gap 0.35] [--log FILE.csv]

knock -> next page, rub (fingernail-edge scratch on bare wood) -> previous page, neutral -> nothing.
Only standard library is required. Pillow is optional (JPG support, smoother scaling).
The window never grabs focus, stays on top, injects keys or hooks global keys.
"""
import argparse
import csv
import queue
import re
import sys
import time
import tkinter as tk
from pathlib import Path

from gesture import NEXT, PREV, GestureGate, SlideDeck
from udp_listener import PortInUseError, UdpListener

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg'}
POLL_MS = 30
MAX_MESSAGES_PER_POLL = 500
FONT = 'Segoe UI' if sys.platform == 'win32' else 'Helvetica'
LABEL_COLORS = dict(knock='#ffd166', rub='#7ec8ff', neutral='#bbbbbb')

BUILTIN_SLIDES = [
    dict(title='Knock to go forward',
         body='One knuckle knock on the wooden board  ->  next slide',
         color='#1f4e79'),
    dict(title='Scratch to go back',
         body='Scratch the bare wood back and forth with a fingernail edge  ->  previous slide',
         color='#7a3b12'),
    dict(title='Pause between actions',
         body='The app waits for a confirmed neutral and uses a short cooldown\n'
              'to reduce repeated page turns.',
         color='#2e5e2e'),
]


def natural_key(path):
    """'2.png' < '10.png'; case-insensitive; ties broken by full name."""
    name = path.name.lower()
    parts = re.split(r'(\d+)', name)
    return [(0, int(p), '') if p.isdigit() else (1, 0, p) for p in parts], name


def load_slides(folder):
    """Return (slides, warning). Each slide is a dict with 'path' or builtin fields."""
    if folder is None:
        return [dict(s) for s in BUILTIN_SLIDES], None
    folder = Path(folder)
    if not folder.is_dir():
        return [dict(s) for s in BUILTIN_SLIDES], f'Slide folder not found: {folder} (showing built-in demo)'
    paths = sorted((p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES),
                   key=natural_key)
    if not paths:
        return [dict(s) for s in BUILTIN_SLIDES], f'No PNG/JPG in {folder} (showing built-in demo)'
    warning = None
    if Image is None and any(p.suffix.lower() != '.png' for p in paths):
        warning = 'JPG needs Pillow (pip install pillow); JPG pages show a placeholder'
    return [dict(path=p) for p in paths], warning


def clock_text(wall):
    return time.strftime('%H:%M:%S', time.localtime(wall)) + f'.{int(wall % 1 * 1000):03d}'


class SlideApp:
    def __init__(self, root, slides, listener, listen_error, gate, log_path=None, warning=None):
        self.root = root
        self.slides = slides
        self.deck = SlideDeck(len(slides))
        self.gate = gate
        self.listener = listener
        self.events = listener.out if listener else queue.Queue()
        self.counts = dict(received=0, invalid=0, turns=0)
        self.history = []
        self.prev_label = None          # last valid label received (detects changes)
        self.last_valid = None          # (wall time, monotonic time) of last valid message
        self._image_cache = {}
        self._log_file = self._log = None
        if log_path:
            self._log_file = open(log_path, 'a', newline='', encoding='utf-8')
            self._log = csv.writer(self._log_file)
            if self._log_file.tell() == 0:
                self._log.writerow(['wall_time', 'monotonic_s', 'kind', 'raw', 'label', 't',
                                    'decision', 'page'])

        root.title('Slide demo (C)')
        root.geometry('1000x720')
        root.configure(bg='#111')
        root.protocol('WM_DELETE_WINDOW', self.close)

        top = tk.Frame(root, bg='#111')
        top.pack(fill='x')
        self.page_var = tk.StringVar()
        tk.Label(top, textvariable=self.page_var, fg='white', bg='#111',
                 font=(FONT, 16, 'bold')).pack(side='left', padx=12, pady=6, anchor='n')
        feedback = tk.Frame(top, bg='#111')
        feedback.pack(side='right', padx=12, pady=4)
        # What the model said (even if the slide did not move) vs. what the slides did.
        self.recognized_var = tk.StringVar(value='Recognized: --')
        self.slide_var = tk.StringVar(value='Slide: --')
        self.current_var = tk.StringVar(value='Current label: --   |   last valid message: none yet')
        self.recognized_label = tk.Label(feedback, textvariable=self.recognized_var, bg='#111',
                                         fg='#ddd', font=(FONT, 20, 'bold'), anchor='e')
        self.recognized_label.pack(fill='x')
        self.slide_label = tk.Label(feedback, textvariable=self.slide_var, bg='#111', fg='#ddd',
                                    font=(FONT, 16), anchor='e')
        self.slide_label.pack(fill='x')
        tk.Label(feedback, textvariable=self.current_var, bg='#111', fg='#aaa',
                 font=(FONT, 10), anchor='e').pack(fill='x')

        self.canvas = tk.Canvas(root, bg='#222', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda e: self.render())

        bottom = tk.Frame(root, bg='#111')
        bottom.pack(fill='x')
        self.net_var = tk.StringVar()
        self.state_var = tk.StringVar()
        self.history_var = tk.StringVar()
        self.net_label = tk.Label(bottom, textvariable=self.net_var, bg='#111', anchor='w',
                                  font=(FONT, 10), justify='left')
        self.net_label.pack(fill='x', padx=12)
        tk.Label(bottom, textvariable=self.state_var, fg='#ccc', bg='#111', anchor='w',
                 font=(FONT, 10)).pack(fill='x', padx=12)
        tk.Label(bottom, textvariable=self.history_var, fg='#888', bg='#111', anchor='w',
                 font=('Consolas', 9), justify='left').pack(fill='x', padx=12, pady=(0, 6))

        if listen_error:
            self.net_var.set(f'NOT LISTENING: {listen_error}')
            self.net_label.configure(fg='#ff6b6b')
        else:
            host, port = listener.address
            self.net_var.set(f'Listening on UDP {host}:{port}')
            self.net_label.configure(fg='#8fd18f')
        if warning:
            self.net_var.set(self.net_var.get() + f'   |   {warning}')

        # Window-local keys for rehearsal only. Space is deliberately NOT bound.
        root.bind('<Right>', lambda e: self.manual(NEXT))
        root.bind('<Left>', lambda e: self.manual(PREV))
        root.bind('<Home>', lambda e: self.goto_first())
        root.bind('<F11>', lambda e: root.attributes(
            '-fullscreen', not root.attributes('-fullscreen')))
        root.bind('<Escape>', lambda e: root.attributes('-fullscreen', False))

        self.update_status()
        self.render()
        root.after(POLL_MS, self.poll)

    # ---------- network events ----------
    def poll(self):
        try:
            for _ in range(MAX_MESSAGES_PER_POLL):
                try:
                    item = self.events.get_nowait()
                except queue.Empty:
                    break
                self.handle(item)
            self.update_status()
        finally:
            self.root.after(POLL_MS, self.poll)

    def handle(self, item):
        if item[0] == 'invalid':
            _, raw, now = item
            self.counts['invalid'] += 1
            self.remember(f'invalid {raw!r}')
            self.write_log(now, 'invalid', raw, '', '', 'ignored')
            return
        _, msg, raw, now = item
        self.counts['received'] += 1
        self.last_valid = (time.time() - (time.monotonic() - now), now)
        changed = msg.label != self.prev_label
        self.prev_label = msg.label
        decision = self.gate.feed(msg.label, now)
        result = decision.reason
        if decision.action:
            result = self.turn(decision.action, msg.label)
        elif changed and msg.label != 'neutral':
            # Recognized but not executed (waiting for neutral / cooldown).
            self.show_recognized(msg.label)
            self.show_slide(f'Slide: not turned ({decision.reason.split(": ", 1)[-1]})', '#ff9f80')
        if decision.action or changed or 're-armed' in decision.reason:
            self.remember(result)
        self.write_log(now, 'msg', raw, msg.label, msg.t, result)

    def turn(self, action, source):
        changed = self.deck.apply(action)
        word = 'NEXT' if action == NEXT else 'PREVIOUS'
        if source != 'key':
            self.show_recognized(source)
        if changed:
            self.counts['turns'] += 1
            self.show_slide(f'Slide: {word} -> page {self.deck.index + 1}', '#8fd18f')
            self.render()
            return f'{source}: {word.lower()} -> page {self.deck.index + 1}'
        edge = 'last' if action == NEXT else 'first'
        self.show_slide(f'Slide: {word} blocked (already on {edge} page)', '#bbbbbb')
        return f'{source}: {word.lower()} blocked, already on {edge} page'

    def manual(self, action):
        self.remember(self.turn(action, 'key'))
        self.update_status()

    def goto_first(self):
        self.deck.index = 0
        self.render()
        self.update_status()

    # ---------- display ----------
    def show_recognized(self, label):
        stamp = clock_text(self.last_valid[0]) if self.last_valid else ''
        self.recognized_var.set(f'Recognized: {label.upper()}  {stamp}')
        self.recognized_label.configure(fg=LABEL_COLORS.get(label, '#ddd'))

    def show_slide(self, text, color):
        self.slide_var.set(text)
        self.slide_label.configure(fg=color)

    def remember(self, text):
        self.history.append(time.strftime('%H:%M:%S ') + text)
        del self.history[:-5]

    def update_status(self):
        now = time.monotonic()
        if not self.gate.armed:
            gate = (f'waiting for confirmed neutral '
                    f'({self.gate.neutral_held():.1f}/{self.gate.neutral_hold_s:g}s)')
        elif self.gate.in_cooldown(now):
            gate = f'cooldown ({self.gate.cooldown_s:g}s)'
        else:
            gate = 'ready'
        if self.last_valid:
            wall, mono = self.last_valid
            self.current_var.set(f'Current label: {self.prev_label}   |   last valid message: '
                                 f'{clock_text(wall)} ({now - mono:.1f}s ago)')
        self.page_var.set(f'Page {self.deck.index + 1} / {self.deck.count}')
        c = self.counts
        self.state_var.set(f'Gate: {gate}   |   received {c["received"]}   invalid {c["invalid"]}'
                           f'   page turns {c["turns"]}   |   keys: Left/Right/Home, F11')
        self.history_var.set('\n'.join(self.history) or 'No messages yet.')

    def render(self):
        w, h = max(self.canvas.winfo_width(), 50), max(self.canvas.winfo_height(), 50)
        self.canvas.delete('all')
        slide = self.slides[self.deck.index]
        if 'path' in slide:
            img = self.image_for(slide['path'], w, h)
            if img is not None:
                self.canvas.create_image(w // 2, h // 2, image=img)
                return
            slide = dict(title=slide['path'].name, color='#444',
                         body='Cannot display this file.\nPNG works without extras; '
                              'JPG needs: pip install pillow')
        self.canvas.configure(bg=slide['color'])
        self.canvas.create_text(w // 2, h * 0.38, text=slide['title'], fill='white',
                                font=(FONT, max(18, w // 22), 'bold'), width=w * 0.9)
        self.canvas.create_text(w // 2, h * 0.62, text=slide['body'], fill='#eee',
                                font=(FONT, max(12, w // 45)), width=w * 0.85, justify='center')

    def image_for(self, path, w, h):
        self.canvas.configure(bg='#222')
        key = (path, w, h)
        if key in self._image_cache:
            return self._image_cache[key]
        img = None
        try:
            if Image is not None:
                with Image.open(path) as im:
                    im = im.convert('RGB')
                    im.thumbnail((w, h))
                    img = ImageTk.PhotoImage(im)
            elif path.suffix.lower() == '.png':
                img = tk.PhotoImage(file=str(path))
                factor = max(1, -(-img.width() // w), -(-img.height() // h))
                if factor > 1:
                    img = img.subsample(factor)
        except (OSError, tk.TclError, ValueError):
            img = None
        self._image_cache = {k: v for k, v in self._image_cache.items() if k[0] != path}
        self._image_cache[key] = img
        return img

    # ---------- logging / shutdown ----------
    def write_log(self, now, kind, raw, label, t, decision):
        if self._log:
            raw = raw.decode('utf-8', 'replace') if isinstance(raw, bytes) else str(raw)
            self._log.writerow([time.strftime('%Y-%m-%d %H:%M:%S'), f'{now:.3f}', kind, raw,
                                label, '' if t is None else t, decision, self.deck.index + 1])
            self._log_file.flush()

    def close(self):
        if self.listener:
            self.listener.close()
        if self._log_file:
            self._log_file.close()
        self.root.destroy()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--slides', help='folder of PNG/JPG slides (natural sort: 1, 2, 10)')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=5005)
    ap.add_argument('--cooldown', type=float, default=0.8, help='seconds (default 0.8)')
    ap.add_argument('--neutral-hold', type=float, default=0.6,
                    help='seconds of continuously confirmed neutral before re-arming (default 0.6)')
    ap.add_argument('--max-gap', type=float, default=0.35,
                    help='max seconds between messages for neutral evidence to stay unbroken '
                         '(default 0.35; sender heartbeat is 0.1)')
    ap.add_argument('--log', help='append received messages/decisions to this CSV')
    ap.add_argument('--fullscreen', action='store_true')
    args = ap.parse_args(argv)
    if args.cooldown < 0 or args.neutral_hold < 0 or args.max_gap <= 0:
        ap.error('--cooldown/--neutral-hold must be >= 0 and --max-gap > 0')

    slides, warning = load_slides(args.slides)
    listener, listen_error = None, None
    try:
        listener = UdpListener(args.host, args.port).start()
    except PortInUseError as exc:
        listen_error = str(exc)
    except OSError as exc:
        listen_error = f'cannot open UDP {args.host}:{args.port}: {exc}'
    if listen_error:
        print('WARNING:', listen_error, file=sys.stderr)
    if warning:
        print('NOTE:', warning, file=sys.stderr)

    root = tk.Tk()
    if args.fullscreen:
        root.attributes('-fullscreen', True)
    gate = GestureGate(args.cooldown, args.neutral_hold, args.max_gap)
    SlideApp(root, slides, listener, listen_error, gate, args.log, warning)
    root.mainloop()


if __name__ == '__main__':
    main()
