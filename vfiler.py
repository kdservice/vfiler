#!/usr/bin/env python3
"""
Small VZ-style terminal file manager using only the Python standard library.

Target:
  - Windows cmd.exe / PowerShell
  - macOS / Linux shells
"""

from __future__ import annotations

import argparse
import ast
import base64
import ctypes
import difflib
import fnmatch
import hashlib
import json
import locale
import os
import queue
import re
import select
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import string
import sys
import tarfile
import tempfile
import threading
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


IS_WINDOWS = os.name == "nt"
RESIDENT_PROTOCOL = 2

if not IS_WINDOWS:
    import termios
    import tty


KEY_UP = "UP"
KEY_DOWN = "DOWN"
KEY_LEFT = "LEFT"
KEY_RIGHT = "RIGHT"
KEY_ENTER = "ENTER"
KEY_BACKSPACE = "BACKSPACE"
KEY_ESCAPE = "ESCAPE"
KEY_HOME = "HOME"
KEY_END = "END"
KEY_PGUP = "PGUP"
KEY_PGDN = "PGDN"
KEY_DELETE = "DELETE"
KEY_INSERT = "INSERT"
KEY_F1 = "F1"
KEY_F2 = "F2"
KEY_F3 = "F3"
KEY_F4 = "F4"
KEY_F5 = "F5"
KEY_F6 = "F6"
KEY_F7 = "F7"
KEY_F8 = "F8"
KEY_F9 = "F9"
KEY_F10 = "F10"
KEY_F11 = "F11"
KEY_F12 = "F12"
KEY_CTRL_ENTER = "C-ENTER"
KEY_SHIFT_ENTER = "S-ENTER"
KEY_SHIFT_F9 = "S-F9"
KEY_SHIFT_F8 = "S-F8"
KEY_SHIFT_F10 = "S-F10"
KEY_SHIFT_F11 = "S-F11"
KEY_SHIFT_F12 = "S-F12"
KEY_CTRL_SHIFT_V = "CS-V"
KEY_SHIFT_UP = "S-UP"
KEY_SHIFT_DOWN = "S-DOWN"
KEY_SHIFT_LEFT = "S-LEFT"
KEY_SHIFT_RIGHT = "S-RIGHT"
KEY_SHIFT_TAB = "S-TAB"
KEY_CTRL_UP = "C-UP"
KEY_CTRL_DOWN = "C-DOWN"
KEY_CTRL_LEFT = "C-LEFT"
KEY_CTRL_RIGHT = "C-RIGHT"
KEY_KP_LEFT = "KP-LEFT"
KEY_KP_UP = "KP-UP"
KEY_KP_RIGHT = "KP-RIGHT"
KEY_KP_DOWN = "KP-DOWN"
KEY_MOUSE = "MOUSE"
KEY_WHEEL_UP = "WHEEL-UP"
KEY_WHEEL_DOWN = "WHEEL-DOWN"


@dataclass
class Entry:
    path: Path
    name: str
    is_dir: bool
    size: int
    zip_path: Path | None = None
    zip_name: str | None = None
    mtime: float = 0.0
    search_line: int | None = None
    search_text: str = ""
    search_match: str = ""
    compare_left_path: Path | None = None
    compare_left_zip_name: str = ""
    compare_left_is_dir: bool = False
    compare_left_size: int = 0
    compare_left_mtime: float = 0.0
    compare_right_path: Path | None = None
    compare_right_zip_name: str = ""
    compare_right_is_dir: bool = False
    compare_right_size: int = 0
    compare_right_mtime: float = 0.0


@dataclass
class EntryInfo:
    kind: str
    size: int
    created: float
    modified: float
    name: str
    path: str


@dataclass
class GitTreeCommit:
    commit: str
    parents: list[str]
    short: str
    stamp: str
    epoch: int
    subject: str
    refs: str


@dataclass
class PaneState:
    cwd: Path
    filter_text: str
    entries: list[Entry]
    cursor: int
    top: int
    sort_key: str = "name"
    sort_reverse: bool = False
    show_datetime: bool = False
    preview_numbers: bool = False
    preview_ratio: float = 0.58
    preview_focus: bool = False
    preview_top: int = 0
    zip_path: Path | None = None
    zip_dir: str = ""
    marks: set[str] | None = None
    search_mode: bool = False
    search_pattern: str = ""
    search_kind: str = "content"
    git_history_mode: bool = False
    git_history_file: Path | None = None
    git_status_mode: bool = False
    git_status_kind: str = "all"
    git_tree_mode: bool = False
    git_tree_scope: str = "local"
    git_tree_show_commit: bool = True
    git_tree_relative_time: bool = False
    git_tree_preview_commit: str = ""
    git_tree_preview_time: float = 0.0
    git_tree_detail_commit: str = ""
    git_commit_files_mode: bool = False
    git_commit_hash: str = ""
    git_commit_parent: str = ""
    compare_mode: bool = False
    compare_left: Path | None = None
    compare_right: Path | None = None
    compare_left_zip: Path | None = None
    compare_left_zip_dir: str = ""
    compare_right_zip: Path | None = None
    compare_right_zip_dir: str = ""
    duplex_mode: bool = False
    duplex_root: Path | None = None
    thuru_return_path: Path | None = None
    thuru_list_path: Path | None = None
    thuru_preview_path: Path | None = None
    watch_path: Path | None = None
    watch_token: int = 0
    watch_dirty: bool = False
    watch_stop: threading.Event | None = None
    watch_snapshot: dict[str, tuple[int, int, bool]] | None = None


@dataclass
class CommandItem:
    title: str
    command: str
    disabled: bool = False
    charset: str = ""
    screen: str = ""


@dataclass
class AppConfig:
    launchers: list[CommandItem]
    execs: dict[str, CommandItem]
    directories: list[CommandItem]
    editor: str
    shell: str
    autosave_runlog: bool
    autosave_runlog_path: str
    quit_prompt: bool
    def_name: str
    colors: dict[str, str]
    painwidth: float
    diff_jump_before: int
    thurupaths: list[Path]
    guards: list[Path]
    show_ownerpath: bool
    change_file_datetime: bool
    syntax: dict[str, dict[str, object]]


RUN_HISTORY_PATH = Path(__file__).resolve().with_name("vfiler_run.his")
STAT_PATH = Path(__file__).resolve().with_name("vfiler_stat.json")
STAT_LOCK_PATH = STAT_PATH.with_suffix(STAT_PATH.suffix + ".lock")
TEMPLATE_DIR = Path(__file__).resolve().with_name("templates")
GITIGNORE_TEMPLATE_NAMES = ["none", "xcode", "python", "web", "node"]
NO_STAT = False
SEARCH_MAX_ROWS = 5000
SEARCH_LINE_LIMIT = 300
EDITOR_SYNTAX_MAX_LINE_CHARS = 20000
EDITOR_BINARY_SAMPLE_SIZE = 4096
EDITOR_BINARY_NUL_RATIO = 0.01
GIT_ROOT_CACHE: dict[str, Path | None] = {}
GIT_BLOB_CACHE: dict[tuple[str, str, str], bytes | None] = {}
GIT_COMMIT_DETAIL_CACHE: dict[tuple[str, str], list[str] | None] = {}
GIT_DIFF_TEXT_CACHE: dict[tuple[object, ...], list[str] | None] = {}
GIT_DIFF_RENDER_CACHE: dict[tuple[object, ...], list[str]] = {}
COMPARE_DIFF_TEXT_CACHE: dict[tuple[object, ...], list[str]] = {}
COMPARE_DIFF_RENDER_CACHE: dict[tuple[object, ...], list[str]] = {}
GIT_DIFF_CONTEXT_LINES = 60
MAC_MOUNT_CACHE: tuple[float, list[tuple[str, str]]] = (0.0, [])
NETWORK_FS_TYPES = {"smbfs", "afpfs", "nfs", "webdav", "cifs", "sshfs", "fuse.sshfs", "autofs"}


@dataclass
class EditorState:
    clips: list[str]
    run_history: list[str]
    search_history: list[str] | None = None
    find_history: list[str] | None = None
    replace_history: list[str] | None = None
    bookmarks: list[CommandItem] | None = None
    tab_spaces: int = 4
    wrap: bool = False
    line_numbers: bool = True
    show_datetime: bool = False
    hide_empty_directories: bool = False
    mouse_cursor: bool = False
    wheel_scroll: bool = False
    ruler: bool = False
    cursor_underline: bool = False
    syntax: dict[str, dict[str, object]] | None = None
    calc_history: list[str] | None = None
    vi_mode: bool = False
    show_enter: bool = False
    show_tab: bool = False
    show_bin: bool = False


@dataclass
class EditorBuffer:
    path: Path
    lines: list[str]
    readonly: bool
    cy: int = 0
    cx: int = 0
    top: int = 0
    left: int = 0
    mark: tuple[int, int] | None = None
    select_mode: bool = False
    rect_select: bool = False
    find_text: str = ""
    insert_mode: bool = True
    edit_mode: bool = True
    undo: list[tuple[list[str], int, int]] | None = None
    redo: list[tuple[list[str], int, int]] | None = None
    dirty: bool = False
    saved: bool = False
    msg: str = ""
    encoding: str = "UTF-8"
    eol: str = "LF"
    show_bin: bool = False


@dataclass
class EditorShellState:
    cwd: Path
    input: list[str] | None = None
    cursor: int = 0
    lines: list[str] | None = None
    top: int = 0
    history_index: int = 0


@dataclass
class TailState:
    path: Path
    offset: int = 0
    pending: str = ""
    active: bool = False
    last_stamp: str = ""


EDITOR_STATE = EditorState([], [])
FILER_STAT: dict[str, object] = {}


class ConfigError(Exception):
    pass


class OperationCanceled(Exception):
    pass


class Terminal:
    def __init__(self) -> None:
        self._old_termios: list[int | bytes] | None = None
        self._active = False

    def __enter__(self) -> "Terminal":
        enable_ansi()
        self.enter_app_mode()
        return self

    def enter_app_mode(self) -> None:
        if not IS_WINDOWS and sys.stdin.isatty():
            if self._old_termios is None:
                self._old_termios = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            attrs = termios.tcgetattr(sys.stdin.fileno())
            attrs[0] &= ~(termios.IXON | termios.IXOFF)
            attrs[3] &= ~(termios.ISIG | getattr(termios, "IEXTEN", 0))
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, attrs)
            self.write("\x1b=")
        self._active = True
        self.hide_cursor()
        self.set_mouse(True)

    def leave_app_mode(self) -> None:
        self.write("\x1b[0m\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l\x1b[?2004l\x1b[?25h\x1b[?1l\x1b>\x1b[r")
        self.flush()
        if not IS_WINDOWS and self._old_termios is not None and sys.stdin.isatty():
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, self._old_termios)
            except termios.error:
                pass
        self._active = False

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._active:
            self.leave_app_mode()
        self.clear()

    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def clear(self) -> None:
        self.write("\x1b[2J\x1b[H")
        self.flush()

    def move(self, row: int, col: int) -> None:
        self.write(f"\x1b[{row};{col}H")

    def hide_cursor(self) -> None:
        self.write("\x1b[?25l")
        self.flush()

    def show_cursor(self) -> None:
        self.write("\x1b[?25h")
        self.flush()

    def set_mouse(self, enabled: bool) -> None:
        if enabled and (EDITOR_STATE.mouse_cursor or EDITOR_STATE.wheel_scroll):
            self.write("\x1b[?1000h\x1b[?1006h")
        else:
            self.write("\x1b[?1000l\x1b[?1006l")
        self.flush()

    def size(self) -> tuple[int, int]:
        size = shutil.get_terminal_size(fallback=(100, 28))
        return size.columns, size.lines


def enable_ansi() -> None:
    if not IS_WINDOWS:
        return
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)


def read_key() -> str:
    if IS_WINDOWS:
        return read_key_windows()
    return read_key_posix()


def read_key_timeout(timeout: float) -> str:
    if IS_WINDOWS:
        import msvcrt
        deadline = time.monotonic() + timeout
        while not msvcrt.kbhit():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return ""
            time.sleep(min(0.01, remaining))
        return read_key_windows()
    if not select.select([sys.stdin.fileno()], [], [], timeout)[0]:
        return ""
    return read_key_posix()


def flush_pending_input() -> None:
    if IS_WINDOWS:
        try:
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getwch()
        except Exception:
            pass
        return
    if not sys.stdin.isatty():
        return
    try:
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except termios.error:
        pass


def read_key_windows() -> str:
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        code = msvcrt.getwch()
        return {
            "H": KEY_UP,
            "P": KEY_DOWN,
            "K": KEY_LEFT,
            "M": KEY_RIGHT,
            "G": KEY_HOME,
            "O": KEY_END,
            "I": KEY_PGUP,
            "Q": KEY_PGDN,
            "R": KEY_INSERT,
            "S": KEY_DELETE,
            ";": KEY_F1,
            "<": KEY_F2,
            "=": KEY_F3,
            ">": KEY_F4,
            "?": KEY_F5,
            "@": KEY_F6,
            "A": KEY_F7,
            "B": KEY_F8,
            "C": KEY_F9,
            "D": KEY_F10,
            "\x85": KEY_F11,
            "\x86": KEY_F12,
            "\x0f": KEY_SHIFT_TAB,
            "[": KEY_SHIFT_F8,
            "\\": KEY_SHIFT_F9,
            "]": KEY_SHIFT_F10,
            "\x88": KEY_SHIFT_F12,
            "\x8d": KEY_CTRL_UP,
            "\x91": KEY_CTRL_DOWN,
            "s": KEY_CTRL_LEFT,
            "t": KEY_CTRL_RIGHT,
        }.get(code, "")
    if ch == "\r":
        return KEY_ENTER
    if ch == "\x08":
        return KEY_BACKSPACE
    if ch == "\x1b":
        return KEY_ESCAPE
    return ch


def read_key_posix() -> str:
    fd = sys.stdin.fileno()
    ch = os.read(fd, 1)
    if ch in (b"\n", b"\r"):
        return KEY_ENTER
    if ch in (b"\x7f", b"\b"):
        return KEY_BACKSPACE
    if ch != b"\x1b":
        return read_utf8_char(fd, ch)

    # Read the rest of a common ANSI sequence if present. Some terminals
    # deliver ESC and the following bytes with a small delay.
    rest = b""
    while select.select([fd], [], [], 0.08)[0]:
        rest += os.read(fd, 1)
        if rest.endswith(b"~") or (rest.startswith(b"[") and rest[-1:] in b"ABCDMm"):
            break
        if len(rest) >= 2 and not (rest[1:].isdigit() or b";" in rest or rest[1:2] == b"<"):
            break
        if len(rest) >= 16:
            break
    mouse = parse_mouse_sequence(rest)
    if mouse:
        return mouse
    if rest == b"[1;2A":
        return KEY_SHIFT_UP
    if rest == b"[1;2B":
        return KEY_SHIFT_DOWN
    if rest == b"[1;2C":
        return KEY_SHIFT_RIGHT
    if rest == b"[1;2D":
        return KEY_SHIFT_LEFT
    if rest in (b"[Z", b"[1;2Z"):
        return KEY_SHIFT_TAB
    if rest == b"[1;5A":
        return KEY_CTRL_UP
    if rest == b"[1;5B":
        return KEY_CTRL_DOWN
    if rest == b"[1;5C":
        return KEY_CTRL_RIGHT
    if rest == b"[1;5D":
        return KEY_CTRL_LEFT
    if rest == b"[A":
        return KEY_UP
    if rest == b"[B":
        return KEY_DOWN
    if rest == b"[C":
        return KEY_RIGHT
    if rest == b"[D":
        return KEY_LEFT
    if rest in (b"[H", b"[1~"):
        return KEY_HOME
    if rest in (b"[F", b"[4~"):
        return KEY_END
    if rest in (b"OP", b"[[A", b"[11~", b"[1P"):
        return KEY_F1
    if rest in (b"OQ", b"[12~", b"[1Q"):
        return KEY_F2
    if rest in (b"OR", b"[13~", b"[1R"):
        return KEY_F3
    if rest in (b"OS", b"[14~", b"[1S"):
        return KEY_F4
    if rest in (b"[15~",):
        return KEY_F5
    if rest in (b"[17~",):
        return KEY_F6
    if rest in (b"[18~",):
        return KEY_F7
    if rest in (b"[19~",):
        return KEY_F8
    if rest in (b"[19;2~",):
        return KEY_SHIFT_F8
    if rest in (b"[20~",):
        return KEY_F9
    if rest in (b"[21~",):
        return KEY_F10
    if rest in (b"[23~",):
        return KEY_F11
    if rest in (b"[24~",):
        return KEY_F12
    if rest in (b"[13;2u", b"[27;2;13~"):
        return KEY_SHIFT_ENTER
    if rest in (b"[13;5u", b"[27;5;13~"):
        return KEY_CTRL_ENTER
    if rest in (b"[20;2~",):
        return KEY_SHIFT_F9
    if rest in (b"[21;2~",):
        return KEY_SHIFT_F10
    if rest in (b"[23;2~",):
        return KEY_SHIFT_F11
    if rest in (b"[24;2~",):
        return KEY_SHIFT_F12
    if rest in (b"Ot", b"[1;9D"):
        return KEY_KP_LEFT
    if rest in (b"Ox", b"[1;9A"):
        return KEY_KP_UP
    if rest in (b"Ov", b"[1;9C"):
        return KEY_KP_RIGHT
    if rest in (b"Or", b"Ou", b"[1;9B"):
        return KEY_KP_DOWN
    if rest in (b"Oq",):
        return KEY_KP_LEFT
    if rest in (b"Os",):
        return KEY_KP_RIGHT
    if rest in (b"[1;2q", b"[1;2r", b"[1;2s", b"[1;2t", b"[1;2u", b"[1;2v", b"[1;2x"):
        return {
            b"[1;2q": "1",
            b"[1;2r": "2",
            b"[1;2s": "3",
            b"[1;2t": "4",
            b"[1;2u": "5",
            b"[1;2v": "6",
            b"[1;2x": "8",
        }[rest]
    if rest in (b"[27;6;118~", b"[86;6u"):
        return KEY_CTRL_SHIFT_V
    if rest == b"[5~":
        return KEY_PGUP
    if rest == b"[6~":
        return KEY_PGDN
    if rest in (b"[2~", b"[2;2~", b"[2;3~", b"[2;5~", b"[2;6~"):
        return KEY_INSERT
    if rest == b"[3~":
        return KEY_DELETE
    if rest:
        return ""
    return KEY_ESCAPE


def normalize_move_key(key: str) -> str:
    return {
        KEY_KP_LEFT: KEY_LEFT,
        KEY_KP_UP: KEY_UP,
        KEY_KP_RIGHT: KEY_RIGHT,
        KEY_KP_DOWN: KEY_DOWN,
    }.get(key, key)


def mark_watch_dirty(pane: PaneState, token: int) -> None:
    if pane.watch_token == token:
        pane.watch_dirty = True


def same_watch_path(left: Path | None, right: Path | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return same_existing_path(left, right)


def entry_watch_snapshot(entries: list[Entry]) -> dict[str, tuple[int, int, bool]]:
    snapshot: dict[str, tuple[int, int, bool]] = {}
    for entry in entries:
        if entry.zip_path is not None or is_owner_entry(entry):
            continue
        try:
            stat_result = entry.path.stat()
        except OSError:
            snapshot[str(entry.path)] = (-1, -1, entry.is_dir)
            continue
        snapshot[str(entry.path)] = (stat_result.st_size, stat_result.st_mtime_ns, entry.is_dir)
    return snapshot


def is_network_like_path(path: Path) -> bool:
    text = str(path)
    if IS_WINDOWS:
        return text.startswith("\\\\") or text.startswith("//")
    if sys.platform == "darwin":
        fs_type = mac_mount_fs_type(path)
        return fs_type in NETWORK_FS_TYPES
    return False


def mac_mount_fs_type(path: Path) -> str:
    entries = mac_mount_entries()
    target = os.path.realpath(str(path))
    best_mount = ""
    best_type = ""
    for mount_point, fs_type in entries:
        real_mount = os.path.realpath(mount_point)
        if target == real_mount or target.startswith(real_mount.rstrip("/") + "/"):
            if len(real_mount) > len(best_mount):
                best_mount = real_mount
                best_type = fs_type
    return best_type


def mac_mount_entries() -> list[tuple[str, str]]:
    global MAC_MOUNT_CACHE
    now = time.monotonic()
    cached_at, cached_entries = MAC_MOUNT_CACHE
    if now - cached_at < 5.0:
        return cached_entries
    try:
        result = subprocess.run(["/sbin/mount"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
        entries = parse_mount_entries(result.stdout)
    except OSError:
        entries = []
    MAC_MOUNT_CACHE = (now, entries)
    return entries


def parse_mount_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in text.splitlines():
        if " on " not in line or " (" not in line:
            continue
        _device, rest = line.rsplit(" on ", 1)
        mount_point, options = rest.split(" (", 1)
        fs_type = options.split(",", 1)[0].split(")", 1)[0].strip().lower()
        if mount_point and fs_type:
            entries.append((mount_point, fs_type))
    return entries


def watch_directory_kqueue(path: Path, stop_event: threading.Event, pane: PaneState, token: int) -> None:
    if IS_WINDOWS or not hasattr(select, "kqueue"):
        return
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        kqueue = select.kqueue()
    except (AttributeError, OSError):
        os.close(fd)
        return
    try:
        flags = select.KQ_NOTE_WRITE | select.KQ_NOTE_DELETE | select.KQ_NOTE_EXTEND | select.KQ_NOTE_ATTRIB | select.KQ_NOTE_RENAME
        event = select.kevent(fd, filter=select.KQ_FILTER_VNODE, flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR, fflags=flags)
        kqueue.control([event], 0, 0)
        last_mark = 0.0
        while not stop_event.is_set() and pane.watch_token == token:
            events = kqueue.control(None, 1, 0.5)
            if not events:
                continue
            now = time.monotonic()
            if now - last_mark >= 0.2:
                mark_watch_dirty(pane, token)
                last_mark = now
    except OSError:
        pass
    finally:
        try:
            kqueue.close()
        except OSError:
            pass
        os.close(fd)


def watch_directory_windows_poll(path: Path, stop_event: threading.Event, pane: PaneState, token: int) -> None:
    if not IS_WINDOWS:
        return
    try:
        last_stamp = path.stat().st_mtime_ns
    except OSError:
        return
    while not stop_event.wait(0.75) and pane.watch_token == token:
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            return
        if stamp != last_stamp:
            last_stamp = stamp
            mark_watch_dirty(pane, token)


def tail_initial_lines(path: Path, max_lines: int = 10, max_bytes: int = 65536) -> tuple[list[str], int]:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - max_bytes))
            data = handle.read()
    except OSError:
        return [], 0
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return timestamp_tail_rows(lines[-max_lines:]), size


TAIL_STAMP_WIDTH = 19


def tail_timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def format_tail_rows(rows: list[str], stamp: str | None = None, last_stamp: str = "") -> tuple[list[str], str]:
    stamp = tail_timestamp() if stamp is None else stamp
    formatted: list[str] = []
    previous = last_stamp
    for row in rows:
        prefix = " " * TAIL_STAMP_WIDTH if previous == stamp else stamp
        formatted.append(f"{prefix}|{row}")
        previous = stamp
    return formatted, previous


def timestamp_tail_rows(rows: list[str], stamp: str | None = None) -> list[str]:
    formatted, _ = format_tail_rows(rows, stamp)
    return formatted


def tail_last_stamp_from_rows(rows: list[str]) -> str:
    for row in reversed(rows):
        prefix = row.split("|", 1)[0]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", prefix):
            return prefix
    return ""


def read_tail_lines(state: TailState) -> list[str]:
    try:
        size = state.path.stat().st_size
    except OSError:
        state.active = False
        rows, state.last_stamp = format_tail_rows([f"[tail stopped: {state.path}]"], last_stamp=state.last_stamp)
        return rows
    if size < state.offset:
        state.offset = 0
        state.pending = ""
    if size == state.offset:
        return []
    try:
        with state.path.open("rb") as handle:
            handle.seek(state.offset)
            data = handle.read()
    except OSError:
        state.active = False
        rows, state.last_stamp = format_tail_rows([f"[tail stopped: {state.path}]"], last_stamp=state.last_stamp)
        return rows
    state.offset = size
    text = state.pending + data.decode("utf-8", errors="replace")
    if text.endswith(("\n", "\r")):
        state.pending = ""
        rows, state.last_stamp = format_tail_rows(text.splitlines(), last_stamp=state.last_stamp)
        return rows
    parts = text.splitlines()
    if not parts:
        state.pending = text
        return []
    state.pending = parts[-1]
    rows, state.last_stamp = format_tail_rows(parts[:-1], last_stamp=state.last_stamp)
    return rows


def append_tail_to_editor_lines(lines: list[str], rows: list[str]) -> None:
    for row in rows:
        lines.append(row)
    if not lines:
        lines.append("")


def editor_at_bottom(top: int, body: int, line_count: int) -> bool:
    return top >= max(0, line_count - max(1, body))


def parse_mouse_sequence(rest: bytes) -> str:
    match = re.fullmatch(br"\[<(\d+);(\d+);(\d+)([Mm])", rest)
    if not match:
        return ""
    button = int(match.group(1))
    col = int(match.group(2))
    row = int(match.group(3))
    press = match.group(4) == b"M"
    if button == 64 and press:
        return KEY_WHEEL_UP
    if button == 65 and press:
        return KEY_WHEEL_DOWN
    return f"{KEY_MOUSE}:{button}:{col}:{row}:{1 if press else 0}"


def mouse_event(key: str) -> tuple[int, int, int, bool] | None:
    if not key.startswith(KEY_MOUSE + ":"):
        return None
    parts = key.split(":")
    if len(parts) != 5:
        return None
    try:
        return int(parts[1]), int(parts[2]), int(parts[3]), parts[4] == "1"
    except ValueError:
        return None


def read_utf8_char(fd: int, first: bytes) -> str:
    lead = first[0]
    if lead < 0x80:
        return first.decode(errors="ignore")
    if 0xC2 <= lead <= 0xDF:
        needed = 1
    elif 0xE0 <= lead <= 0xEF:
        needed = 2
    elif 0xF0 <= lead <= 0xF4:
        needed = 3
    else:
        return ""

    data = first
    for _ in range(needed):
        if not select.select([fd], [], [], 0.08)[0]:
            return ""
        data += os.read(fd, 1)
    return data.decode("utf-8", errors="ignore")


def display_width(text: str) -> int:
    return sum(char_width(ch) for ch in text)


def char_width(ch: str) -> int:
    if not ch:
        return 0
    category = unicodedata.category(ch)
    if category[0] == "C" or category in ("Mn", "Me") or unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1


def fit(text: str, width: int) -> str:
    if width <= 0:
        return ""
    out = ""
    used = 0
    for ch in text:
        ch_width = display_width(ch)
        if used + ch_width > width:
            break
        out += ch
        used += ch_width
    if display_width(text) > width and width >= 1:
        while display_width(out + "...") > width and out:
            out = out[:-1]
        out += "." if width < 3 else "..."
    return out + (" " * max(0, width - display_width(out)))


def fit_raw(text: str, width: int) -> str:
    if width <= 0:
        return ""
    out = ""
    used = 0
    for ch in text:
        ch_width = display_width(ch)
        if used + ch_width > width:
            break
        out += ch
        used += ch_width
    return out


def log_prompt_row_text(text: str, cursor: int, width: int, prefix: str = "$ ") -> str:
    if width <= 0:
        return ""
    while display_width(prefix) > max(0, width - 1) and prefix:
        prefix = prefix[1:]
    field_width = max(1, width - display_width(prefix))
    cursor = min(max(0, cursor), len(text))
    before = text[:cursor]
    while display_width(before) >= field_width and before:
        before = before[1:]
    cursor_char = text[cursor] if cursor < len(text) else " "
    cursor_width = max(1, display_width(cursor_char))
    while display_width(before) + cursor_width > field_width and before:
        before = before[1:]
    after_width = max(0, field_width - display_width(before) - cursor_width)
    after = fit_raw(text[cursor + (1 if cursor < len(text) else 0):], after_width)
    return pad_ansi(prefix + before + reverse(cursor_char) + after, width)


def log_prompt_row_text_colored(text: str, cursor: int, width: int, prefix: str, colors: dict[str, str], cwd: Path) -> str:
    if width <= 0:
        return ""
    while display_width(prefix) > max(0, width - 1) and prefix:
        prefix = prefix[1:]
    field_width = max(1, width - display_width(prefix))
    cursor = min(max(0, cursor), len(text))
    visible_start = 0
    before = text[:cursor]
    while display_width(before) >= field_width and before:
        visible_start += 1
        before = before[1:]
    cursor_char = text[cursor] if cursor < len(text) else " "
    cursor_width = max(1, display_width(cursor_char))
    while display_width(before) + cursor_width > field_width and before:
        visible_start += 1
        before = before[1:]
    after_width = max(0, field_width - display_width(before) - cursor_width)
    cursor_end = cursor + (1 if cursor < len(text) else 0)
    after = fit_raw(text[cursor_end:], after_width)
    visible_text = before + cursor_char + after
    colored = color_log_input_segment(visible_text, visible_start, cursor - visible_start, colors, cwd)
    return pad_ansi(color_text(prefix, colors["log_prompt_color"]) + colored, width)


def color_log_input_segment(text: str, source_start: int, cursor_offset: int, colors: dict[str, str], cwd: Path) -> str:
    spans = shell_input_color_spans(text, source_start, colors, cwd)
    out = ""
    for index, ch in enumerate(text):
        color = spans[index] if index < len(spans) else colors["log_input_text_color"]
        cell = color_text(ch, color)
        out += reverse_ansi(cell) if index == cursor_offset else cell
    if cursor_offset >= len(text):
        out += reverse(" ")
    return out


def shell_input_color_spans(text: str, source_start: int, colors: dict[str, str], cwd: Path) -> list[str]:
    spans = [colors["log_input_text_color"] for _ in text]
    tokens = shell_input_tokens(text, source_start)
    for start, end, value, quoted, closed in tokens:
        if quoted:
            color = colors["log_input_text_color"] if closed else colors["log_input_unclosed_string_color"]
        else:
            color = shell_path_color(value, colors, cwd) or colors["log_input_text_color"]
        for index in range(max(0, start), min(len(spans), end)):
            spans[index] = color
    return spans


def shell_input_tokens(text: str, source_start: int) -> list[tuple[int, int, str, bool, bool]]:
    tokens: list[tuple[int, int, str, bool, bool]] = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        start = index
        if text[index] in ("'", '"'):
            quote = text[index]
            index += 1
            value_start = index
            while index < len(text) and text[index] != quote:
                if quote == '"' and text[index] == "\\" and index + 1 < len(text):
                    index += 2
                else:
                    index += 1
            closed = index < len(text) and text[index] == quote
            value = text[value_start:index]
            end = index + 1 if closed else index
            tokens.append((start, end, value, True, closed))
            index = end
            continue
        while index < len(text) and not text[index].isspace():
            index += 1
        value = text[start:index]
        tokens.append((start, index, value, False, True))
    return [(start, end, value, quoted, closed) for start, end, value, quoted, closed in tokens if end > start and source_start + end > source_start]


def shell_path_color(value: str, colors: dict[str, str], cwd: Path) -> str:
    raw = value.strip()
    if not raw or raw.startswith("-"):
        return ""
    if not any(mark in raw for mark in ("/", "\\", ".", "~")):
        return ""
    path_text = raw.rstrip(",;:")
    if not path_text:
        return ""
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return colors["log_input_existing_path_color"] if path.exists() else colors["log_input_missing_path_color"]


def editor_shell_init(state: EditorShellState) -> None:
    if state.input is None:
        state.input = []
    if state.lines is None:
        state.lines = []
    state.history_index = min(max(0, state.history_index), len(EDITOR_STATE.run_history))


def editor_shell_prompt_prefix(state: EditorShellState) -> str:
    path = stable_path_text(state.cwd)
    if path and not path.endswith(("/", "\\")):
        path += os.sep
    return f"{path} $ "


def editor_shell_command_shell() -> str | None:
    if IS_WINDOWS:
        return os.environ.get("COMSPEC") or None
    return os.environ.get("SHELL") or "/bin/sh"


def editor_shell_append(state: EditorShellState, text: str) -> None:
    editor_shell_init(state)
    assert state.lines is not None
    for line in text.splitlines() or [""]:
        state.lines.append(line)
    if len(state.lines) > 1000:
        del state.lines[:-1000]


def editor_shell_recall_history(state: EditorShellState, previous: bool) -> str:
    editor_shell_init(state)
    history = EDITOR_STATE.run_history
    if not history:
        return "run history empty"
    state.history_index += -1 if previous else 1
    state.history_index = min(len(history), max(0, state.history_index))
    value = "" if state.history_index == len(history) else history[state.history_index]
    state.input = list(value)
    state.cursor = len(state.input)
    return "run history"


def editor_shell_run_command(state: EditorShellState) -> str:
    editor_shell_init(state)
    assert state.input is not None
    command = "".join(state.input).strip()
    if not command:
        return "shell command empty"
    raw_command = command
    command = expand_prompt_vars(command)
    state.input = []
    state.cursor = 0
    if raw_command not in EDITOR_STATE.run_history:
        EDITOR_STATE.run_history.append(raw_command)
        save_run_history(EDITOR_STATE.run_history)
    state.history_index = len(EDITOR_STATE.run_history)
    editor_shell_append(state, editor_shell_prompt_prefix(state) + command)
    clear_git_cache()
    try:
        result = subprocess.run(
            command,
            shell=True,
            executable=editor_shell_command_shell(),
            cwd=str(state.cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            check=False,
        )
    except OSError as exc:
        editor_shell_append(state, f"failed to start: {exc}")
        return f"shell failed: {exc}"
    if result.stdout:
        editor_shell_append(state, result.stdout.rstrip("\n"))
    if result.stderr:
        editor_shell_append(state, "[stderr]")
        editor_shell_append(state, result.stderr.rstrip("\n"))
    if not result.stdout and not result.stderr:
        editor_shell_append(state, "(no output)")
    if result.returncode != 0:
        editor_shell_append(state, f"exit code: {result.returncode}")
        return f"shell exit: {result.returncode}"
    return ""


def handle_editor_shell_key(term: Terminal, state: EditorShellState, key: str, height: int) -> tuple[bool, str]:
    editor_shell_init(state)
    assert state.input is not None and state.lines is not None
    key = normalize_move_key(key)
    if key == KEY_ENTER:
        return True, editor_shell_run_command(state)
    if key == KEY_ESCAPE:
        if state.input:
            state.input = []
            state.cursor = 0
        return True, ""
    if key in (KEY_UP, KEY_DOWN, KEY_CTRL_UP, KEY_CTRL_DOWN):
        return True, editor_shell_recall_history(state, key in (KEY_UP, KEY_CTRL_UP))
    if key in (KEY_PGUP, KEY_PGDN):
        rows = max(1, height - 2)
        delta = -rows if key == KEY_PGUP else rows
        state.top = min(max(0, state.top + delta), max(0, len(state.lines) - rows))
        return True, f"shell: {min(state.top + 1, max(1, len(state.lines)))}/{max(1, len(state.lines))}"
    if key == KEY_LEFT:
        state.cursor = max(0, state.cursor - 1)
        return True, ""
    if key == KEY_RIGHT:
        state.cursor = min(len(state.input), state.cursor + 1)
        return True, ""
    if key == KEY_CTRL_LEFT or key == KEY_HOME:
        state.cursor = 0
        return True, ""
    if key == KEY_CTRL_RIGHT or key == KEY_END:
        state.cursor = len(state.input)
        return True, ""
    if key == KEY_BACKSPACE:
        if state.cursor > 0:
            del state.input[state.cursor - 1]
            state.cursor -= 1
        return True, ""
    if key == KEY_DELETE:
        if state.cursor < len(state.input):
            del state.input[state.cursor]
        return True, ""
    if is_text_input(key):
        state.input[state.cursor:state.cursor] = list(key)
        state.cursor += len(key)
        return True, ""
    return False, ""


def draw_editor_shell(term: Terminal, row: int, col: int, width: int, height: int, state: EditorShellState, active: bool, colors: dict[str, str] | None) -> tuple[int, int]:
    editor_shell_init(state)
    assert state.input is not None and state.lines is not None
    title = f" Shell  {editor_shell_prompt_prefix(state)} "
    term.move(row, col)
    term.write(reverse(fit(title, width)) if active else underline(fit(title, width)))
    log_rows = max(0, height - 2)
    state.top = min(max(0, state.top), max(0, len(state.lines) - max(1, log_rows)))
    for screen_row in range(log_rows):
        index = state.top + screen_row
        text = state.lines[index] if index < len(state.lines) else ""
        term.move(row + 1 + screen_row, col)
        term.write(fit(text, width))
    prompt = log_prompt_row_text("".join(state.input), state.cursor, width, editor_shell_prompt_prefix(state))
    term.move(row + height - 1, col)
    term.write(prompt)
    cursor_col = min(width, display_width(editor_shell_prompt_prefix(state)) + display_width("".join(state.input[:state.cursor])) + 1)
    return row + height - 1, col + max(0, cursor_col - 1)


def ruler_line(width: int, left: int = 0, cursor_col: int | None = None) -> str:
    if width <= 0:
        return ""
    chars: list[str] = []
    for col in range(width):
        value = left + col + 1
        if value % 10 == 0:
            chars.append(str((value // 10) % 10))
        elif value % 5 == 0:
            chars.append("+")
        else:
            chars.append("-")
    if cursor_col is not None and left <= cursor_col < left + width:
        index = cursor_col - left
        chars[index] = reverse(chars[index])
    return "".join(chars)


def wheel_scroll_position(cursor: int, top: int, count: int, body: int, delta: int) -> tuple[int, int]:
    if count <= 0:
        return 0, 0
    body = max(1, body)
    max_top = max(0, count - body)
    new_cursor = min(max(0, cursor + delta), count - 1)
    new_top = top
    if new_cursor < new_top:
        new_top = new_cursor
    elif new_cursor >= new_top + body:
        new_top = new_cursor - body + 1
    return new_cursor, min(max(0, new_top), max_top)


def clamp_scroll_position(cursor: int, top: int, count: int, body: int) -> tuple[int, int]:
    if count <= 0:
        return 0, 0
    body = max(1, body)
    cursor = min(max(0, cursor), count - 1)
    top = max(0, top)
    if cursor < top:
        top = cursor
    elif cursor >= top + body:
        top = cursor - body + 1
    return cursor, min(top, max(0, count - body))


def filer_max_log_height(lines: int) -> int:
    return max(1, lines - 6)


def filer_log_height(lines: int, requested: int) -> int:
    return min(max(1, requested), filer_max_log_height(lines))


def filer_body_height(lines: int, log_height: int) -> int:
    return max(1, lines - 5 - filer_log_height(lines, log_height))


def filer_log_display_height(lines: int, requested: int) -> int:
    return filer_log_height(lines, requested) + 1


def command_popup_item_height(count: int, lines: int, full_height: bool = False) -> int:
    limit = max(1, lines - 4)
    return min(count, limit)


def highlight_text(text: str, match_text: str, color: str, width: int) -> str:
    if not match_text:
        return fit(text, width)
    pos = text.find(match_text)
    if pos < 0:
        return fit(text, width)
    before = fit_raw(text[:pos], width)
    remain = max(0, width - display_width(before))
    match = fit_raw(match_text, remain)
    after = fit_raw(text[pos + len(match_text):], max(0, remain - display_width(match)))
    return pad_ansi(before + color_text(match, color) + after, width)


def fmt_size(size: int, is_dir: bool) -> str:
    if is_dir:
        return "<DIR>"
    units = ["B", "K", "M", "G", "T"]
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    if unit == "B":
        return f"{int(value)}B"
    return f"{value:.1f}{unit}"


def short_datetime(stamp: float) -> str:
    if stamp <= 0:
        return "00-00-00 00:00:00"
    try:
        return time.strftime("%y-%m-%d %H:%M:%S", time.localtime(stamp))
    except (OverflowError, ValueError):
        return "00-00-00 00:00:00"


class FilerApp:
    def __init__(self, start: Path, other: Path | None = None, mode: str = "dual", restore_stat: bool = False) -> None:
        self.config = load_config(Path.cwd())
        stat = FILER_STAT.get("filer") if restore_stat else None
        if isinstance(stat, dict):
            mode_value = stat.get("mode")
            if mode_value in ("preview", "dual"):
                mode = str(mode_value)
            start = stat_path(stat.get("left_cwd"), start)
            other = stat_path(stat.get("right_cwd"), other or start)
        resolved = start.resolve()
        other_resolved = other.resolve() if other is not None else resolved
        self.panes = [
            PaneState(resolved, "", [], 0, 0, preview_ratio=self.config.painwidth, marks=set()),
            PaneState(other_resolved, "", [], 0, 0, preview_ratio=self.config.painwidth, marks=set()),
        ]
        for pane in self.panes:
            pane.show_datetime = EDITOR_STATE.show_datetime
        self.active_pane = 0
        self.mode = mode
        self.status = "?:help"
        self.running = True
        self.root_pending = False
        self.editor_request: tuple[Path, bool, int | None] | None = None
        self.return_editor_requests = False
        self.resident_mode = False
        self.restart_requested = False
        self.shell_origin_cwd: Path | None = None
        self.shell_return_text = ""
        self.buffer_count = 0
        self.file_clipboard: tuple[list[Entry], bool] | None = None
        self.dual_ratio = 0.5
        self.log_lines: list[str] = []
        self.log_top = 0
        self.log_follow_bottom = True
        self.log_height = 3
        self.log_focus = False
        self.log_cwd = resolved
        self.log_input: list[str] = []
        self.log_input_cursor = 0
        self.log_history_index = len(EDITOR_STATE.run_history)
        self.log_tail: TailState | None = None
        self.log_busy = False
        self.compare_return_active = 0
        self.git_view_return_mode = ""
        self.git_view_return_active = 0
        self.restore_targets: list[str | None] = [None, None]
        self.restore_cursors: list[int] = [0, 0]
        self.dir_history: list[list[str]] = [[str(resolved)], [str(other_resolved)]]
        self.dir_history_pos: list[int] = [0, 0]
        self.next_watch_update = 0.0
        self.last_input_time = time.monotonic()
        if EDITOR_STATE.search_history is None:
            EDITOR_STATE.search_history = []
        if EDITOR_STATE.bookmarks is None:
            EDITOR_STATE.bookmarks = []
        if isinstance(stat, dict):
            self.apply_saved_stat(stat)

    @property
    def pane(self) -> PaneState:
        return self.panes[self.active_pane]

    @property
    def cwd(self) -> Path:
        return self.pane.cwd

    @cwd.setter
    def cwd(self, value: Path) -> None:
        self.pane.cwd = value

    def can_enter_dir(self, path: Path) -> bool:
        if is_guard_path(path, self.config.guards):
            self.status = f"guarded: {path}"
            return False
        return True

    def reload_def(self) -> None:
        try:
            config = load_config(Path.cwd())
        except ConfigError as exc:
            self.fail_status(f"DEF error: {exc}")
            return
        self.config = config
        for pane in self.panes:
            pane.preview_ratio = self.config.painwidth
        self.refresh_all()
        self.status = f"DEF reloaded: {self.config.def_name}"

    def restart_app(self, term: Terminal | None = None) -> None:
        save_stat(self.filer_stat())
        clear_git_cache()
        if term is not None:
            term.leave_app_mode()
            term.clear()
        if self.resident_mode:
            self.restart_requested = True
            self.running = False
            return
        os.execv(sys.executable, [sys.executable, *sys.argv])

    @property
    def filter_text(self) -> str:
        return self.pane.filter_text

    @filter_text.setter
    def filter_text(self, value: str) -> None:
        self.pane.filter_text = value

    @property
    def entries(self) -> list[Entry]:
        return self.pane.entries

    @entries.setter
    def entries(self, value: list[Entry]) -> None:
        self.pane.entries = value

    @property
    def cursor(self) -> int:
        return self.pane.cursor

    @cursor.setter
    def cursor(self, value: int) -> None:
        self.pane.cursor = value

    @property
    def top(self) -> int:
        return self.pane.top

    @top.setter
    def top(self, value: int) -> None:
        self.pane.top = value

    def run(self) -> None:
        with Terminal() as term:
            self.refresh_all(True)
            dirty = True
            while self.running:
                if dirty:
                    self.draw(term)
                    dirty = False
                key = read_key_timeout(0.1)
                if not key:
                    dirty = self.poll_log_tail(term) or dirty
                    dirty = self.idle_watch_tick() or dirty
                    continue
                self.note_input_activity()
                self.handle_key(term, key)
                dirty = True
            self.stop_watchers()
            save_stat(self.filer_stat())

    def help_text(self) -> str:
        if self.mode == "dual":
            return "1:preview  2:dual  Tab:log  Space:mark  a:all  F9:copy  S-F9:cut  F10:paste  []:hist  b/B:bookmark  Left/Right:pane  w:sync  Enter:open/exec  v:view  e:edit  x:launcher  g:git  s:sort  l:dir  c:copy  m:move  d:delete  q:quit"
        return "1:preview  2:dual  Tab:log  Space:mark  a:all  F9:copy  S-F9:cut  F10:paste  []:hist  b/B:bookmark  f:search  w:wrap  Enter:open/exec  BS:up  v:view  e:edit  x:launcher  g:git  s:sort  l:dir  c:copy  m:move  d:delete  q:quit"

    def menu_bar(self, columns: int) -> str:
        help_text = f"?:Help ({self.config.def_name}) "
        left_width = max(1, columns - display_width(help_text))
        left = fit(self.menu_bar_text(), left_width)
        return reverse(left + help_text)

    def menu_bar_text(self) -> str:
        return " F1:Files F2:Edit F3:View F4:Git F5:Reload F6:Launch F7:PainSize F9:Copy/Cut F10:Paste F12:Editor "

    def filer_menu_labels(self) -> list[str]:
        return ["F1:Files", "F2:Edit", "F3:View", "F4:Git", "F6:Launch"]

    def git_menu_items(self) -> list[CommandItem]:
        git_root_path = None if self.pane.zip_path is not None else git_root(self.cwd)
        git_available = self.pane.zip_path is None and git_root_path is not None
        git_init_available = self.pane.zip_path is None and git_root_path is None
        git_view_available = git_available
        git_add_available = git_available and self.git_add_target_available()
        git_ignore_available = self.pane.zip_path is None and (self.cwd / ".gitignore").is_file() and bool(self.git_ignore_targets())
        git_unmanage_available = git_available and self.git_unmanage_target_available()
        git_discard_available = git_available and self.git_discard_target_available()
        git_history_available = git_available and self.git_history_target_available()
        items: list[CommandItem] = []
        if self.pane.git_tree_mode:
            items.extend([
                CommandItem("Checkout Commit", "__git_tree_checkout__"),
                CommandItem(f"Tree Scope ({self.pane.git_tree_scope.title()})", "__git_tree_scope__"),
            ])
        if self.pane.git_commit_files_mode:
            items.extend([
                CommandItem("Checkout File", "__git_commit_checkout__"),
                CommandItem("Copy File", "__git_commit_copy__"),
            ])
        items.extend([
            CommandItem("Status", "__git_status__", not git_view_available),
            CommandItem("Commit Command", "__git_commit__", not git_available),
            CommandItem("Unmanaged Files", "__git_unmanaged__", not git_view_available),
            CommandItem("Managed Files", "__git_managed__", not git_view_available),
            CommandItem("Discard Changes", "__git_discard__", not git_discard_available),
            CommandItem("Manage File(s)", "__git_add__", not git_add_available),
            CommandItem("Add ignore", "__git_add_ignore__", not git_ignore_available),
            CommandItem("Unmanage File(s)", "__git_unmanage__", not git_unmanage_available),
            CommandItem("File History", "__git_history__", not git_history_available),
            CommandItem("Graph Tree", "__git_tree__", not git_view_available),
            CommandItem("Branch List", "__git_branch_list__", not git_available),
            CommandItem("New Branch", "__git_new_branch__", not git_available),
            CommandItem("Merge Branch", "__git_merge_branch__", not git_available),
            CommandItem("Show Command", "__git_show__", not git_available),
            CommandItem("Pull Command", "__git_pull__", not git_available),
            CommandItem("Push Command", "__git_push__", not git_available),
            CommandItem("Initialize", "__git_init__", not git_init_available),
        ])
        return items

    def filer_menu(self, term: Terminal, initial_menu: int) -> None:
        git_items = self.git_menu_items()
        file_shortcut_col = 18
        edit_shortcut_col = 18
        edit_items = [
            CommandItem(menu_text("Mark All", "a", edit_shortcut_col), "__mark_all__"),
            CommandItem("Clear Marks", "__clear_marks__"),
            CommandItem(menu_text("Copy/Cut", "F9/Shift+F9", edit_shortcut_col), "__clip_copy__"),
            CommandItem(menu_text("Paste", "F10", edit_shortcut_col), "__clip_paste__"),
            menu_separator(),
            CommandItem("Path Copy", "__path_copy__"),
            CommandItem("Filename Copy", "__filename_copy__"),
            CommandItem(menu_text("File Search", "f", edit_shortcut_col), "__search__"),
            CommandItem("Filename Search", "__filename_search__"),
            CommandItem("Bulk Name Replace", "__bulk_name_replace__"),
            CommandItem(menu_text("Name Filter", "/", edit_shortcut_col), "__filter__"),
        ]
        if self.file_clipboard is not None:
            edit_items.insert(4, CommandItem("Clip File Clear", "__clip_file_clear__"))
        view_items = self.view_menu_items()
        launch_items = [
            CommandItem(menu_text("Launcher", "x", 17), "__launcher__"),
            CommandItem("Setting Tool", "__setting_tool__"),
            menu_separator(),
        ]
        launch_items.extend(self.config.launchers)
        launch_items.extend([
            CommandItem("Full Screen Shell", "__full_shell__"),
            CommandItem("Run...", "__run__"),
            CommandItem("New Text File...", "__new_text__"),
            CommandItem("New Archive...", "__new_archive__"),
        ])
        menus = [
            ("Files", [
                CommandItem(menu_text("Open/Exec", "Enter", file_shortcut_col), "__open__"),
                CommandItem(menu_text("View", "v", file_shortcut_col), "__view__"),
                CommandItem(menu_text("Edit", "e", file_shortcut_col), "__edit__"),
                CommandItem(menu_text("Tail", "", file_shortcut_col), "__tail__"),
                CommandItem(menu_text("Information", "i", file_shortcut_col), "__information__"),
                CommandItem(menu_text("Copy...", "c", file_shortcut_col), "__copy__"),
                CommandItem(menu_text("Merge Copy", "", file_shortcut_col), "__merge_copy__"),
                CommandItem(menu_text("Move...", "m", file_shortcut_col), "__move__"),
                CommandItem(menu_text("Rename", "r", file_shortcut_col), "__rename__"),
                CommandItem(menu_text("Mkdir", "n", file_shortcut_col), "__mkdir__"),
                CommandItem(menu_text("Delete", "d", file_shortcut_col), "__delete__"),
                CommandItem(menu_text("Bookmark List", "b", file_shortcut_col), "__bookmark__"),
                CommandItem(menu_text("Bookmark Add", "B", file_shortcut_col), "__bookmark_add__"),
                CommandItem(menu_text("Reload DEF", "", file_shortcut_col), "__reload_def__"),
                CommandItem(menu_text("Restart", "", file_shortcut_col), "__restart__"),
                CommandItem(menu_text("Close/Quit", "q", file_shortcut_col), "__quit__"),
            ]),
            ("Edit", edit_items),
            ("View", view_items),
            ("Git", git_items),
            ("Launch", launch_items),
        ]
        action = self.select_menu_item(term, menus, initial_menu)
        if action is not None:
            self.run_menu_action(term, action)

    def select_menu_item(self, term: Terminal, menus: list[tuple[str, list[CommandItem]]], menu: int) -> str | None:
        cursor = first_enabled_command(menus[menu][1])
        labels = self.filer_menu_labels()
        while True:
            items = menus[menu][1]
            columns, lines = term.size()
            group = menus[menu][0]
            width = min(max(18, max(max(display_width(item.title) for item in items), display_width(group)) + 4), max(18, columns))
            height = min(len(items), max(1, lines - 4))
            top = min(max(0, cursor - height + 1), max(0, len(items) - height))
            start_col = menu_popup_col(self.menu_bar_text(), labels[menu], columns, width)
            start_row = 2
            self.draw(term)
            draw_menu_bar_highlight(term, self.menu_bar_text(), labels[menu])
            term.move(start_row, start_col)
            term.write(yellow("█" * width))
            for row, item in enumerate(items[top:top + height], start=top):
                line = fit("-" * (width - 2) if is_menu_separator(item) else item.title, width - 2)
                term.move(start_row + 1 + row - top, start_col)
                if is_menu_separator(item):
                    body = yellow_bg(line)
                elif item.disabled:
                    body = color_text(line, "90;43")
                elif row == cursor:
                    body = color_text(line, "31;43")
                else:
                    body = yellow_bg(line)
                term.write(yellow("█") + body + yellow("█"))
            term.move(start_row + height + 1, start_col)
            term.write(yellow("█" * width))
            term.flush()
            key = read_key()
            if key == KEY_ENTER:
                return None if items[cursor].disabled else items[cursor].command
            if key in (KEY_ESCAPE, KEY_BACKSPACE, "q", "Q"):
                return None
            if key in (KEY_F1, KEY_F2, KEY_F3, KEY_F4, KEY_F6):
                menu = {KEY_F1: 0, KEY_F2: 1, KEY_F3: 2, KEY_F4: 3, KEY_F6: 4}[key]
                cursor = first_enabled_command(menus[menu][1])
            if key == KEY_RIGHT:
                menu = (menu + 1) % len(menus)
                cursor = first_enabled_command(menus[menu][1])
            elif key == KEY_LEFT:
                menu = (menu - 1) % len(menus)
                cursor = first_enabled_command(menus[menu][1])
            elif key in (KEY_UP, "k", "K"):
                cursor = move_enabled_command(items, cursor, -1)
            elif key in (KEY_DOWN, "j", "J"):
                cursor = move_enabled_command(items, cursor, 1)

    def view_menu_items(self) -> list[CommandItem]:
        sort_text = self.sort_state_text()
        wrap_name = f"Preview Wrap ({'ON' if EDITOR_STATE.wrap else 'OFF'})" if self.mode == "preview" else "Sync Path"
        line_text = "Show" if self.pane.preview_numbers else "Hide"
        datetime_text = "Show" if EDITOR_STATE.show_datetime else "Hide"
        empty_dirs_text = "ON" if EDITOR_STATE.hide_empty_directories else "OFF"
        mouse_text = "ON" if EDITOR_STATE.mouse_cursor else "OFF"
        wheel_text = "ON" if EDITOR_STATE.wheel_scroll else "OFF"
        commit_text = "Show" if self.pane.git_tree_show_commit else "Hide"
        graph_time_text = "Relative" if self.pane.git_tree_relative_time else "DateTime"
        labels = [
            ("Preview Mode", "", self.mode == "preview"),
            ("Dual Mode", "", self.mode == "dual"),
            ("Sort", sort_text, False),
            ("Dir List", "", False),
            ("Compare", "", self.mode != "dual"),
            ("Duplexes", "", self.mode == "dual"),
            (wrap_name, "", False),
            ("Line Number", line_text, False),
            ("Datetime", datetime_text, False),
            ("Hide Empty Directories", empty_dirs_text, False),
            ("Mouse Cursor", mouse_text, False),
            ("Wheel Scroll", wheel_text, False),
        ]
        if self.pane.git_tree_mode:
            labels.extend([
                ("Commit Id", commit_text, False),
                ("Graph Time", graph_time_text, False),
            ])
        shortcut_col = max(display_width(name + (f" ({state})" if state else "")) for name, state, _ in labels) + 4
        items = [
            CommandItem(menu_text("Preview Mode", "1", shortcut_col), "__mode_preview__", self.mode == "preview"),
            CommandItem(menu_text("Dual Mode", "2", shortcut_col), "__mode_dual__", self.mode == "dual"),
            menu_separator(),
            CommandItem(menu_text(f"Sort ({sort_text})", "s", shortcut_col), "__sort__"),
            CommandItem(menu_text("Dir List", "l", shortcut_col), "__dir__"),
            CommandItem(menu_text("Compare", "", shortcut_col), "__compare__", self.mode != "dual"),
            CommandItem(menu_text("Duplexes", "", shortcut_col), "__duplexes__", self.mode == "dual"),
            CommandItem(menu_text(wrap_name, "w", shortcut_col), "__wrap_sync__"),
            CommandItem(menu_text(f"Line Number ({line_text})", "", shortcut_col), "__line__"),
            CommandItem(menu_text(f"Datetime ({datetime_text})", "", shortcut_col), "__datetime__"),
            CommandItem(menu_text(f"Hide Empty Directories ({empty_dirs_text})", "", shortcut_col), "__hide_empty_directories__"),
            CommandItem(menu_text(f"Mouse Cursor ({mouse_text})", "", shortcut_col), "__mouse_cursor__"),
            CommandItem(menu_text(f"Wheel Scroll ({wheel_text})", "", shortcut_col), "__wheel_scroll__"),
        ]
        if self.pane.git_tree_mode:
            items.extend([
                menu_separator(),
                CommandItem(menu_text(f"Commit Id ({commit_text})", "", shortcut_col), "__git_tree_commit_id__"),
                CommandItem(menu_text(f"Graph Time ({graph_time_text})", "", shortcut_col), "__git_tree_time__"),
            ])
        return items

    def sort_state_text(self) -> str:
        names = {"name": "Name", "natural": "Natural", "ext": "Ext", "size": "Size", "mtime": "DateTime"}
        return f"{names.get(self.pane.sort_key, self.pane.sort_key)} {'DESC' if self.pane.sort_reverse else 'ASC'}"

    def run_menu_action(self, term: Terminal, action: str) -> None:
        if action == "__open__":
            self.open_selected(term)
        elif action == "__view__":
            self.preview_selected(term)
        elif action == "__edit__":
            self.edit_selected(term)
        elif action == "__tail__":
            self.tail_selected(term)
        elif action == "__information__":
            self.information_selected(term)
        elif action == "__rename__":
            self.rename_selected(term)
        elif action == "__mkdir__":
            self.mkdir(term)
        elif action == "__delete__":
            self.delete_selected(term)
        elif action == "__bookmark__":
            self.bookmark_selected(term)
        elif action == "__bookmark_add__":
            self.bookmark_add(term)
        elif action == "__quit__":
            if not self.config.quit_prompt or self.confirm_quit(term):
                self.running = False
        elif action == "__reload_def__":
            self.reload_def()
        elif action == "__restart__":
            self.restart_app(term)
        elif action == "__mark_all__":
            self.mark_all()
        elif action == "__clear_marks__":
            self.clear_marks()
            self.status = "marks cleared"
        elif action == "__clip_copy__":
            self.clip_selected(False)
        elif action == "__clip_cut__":
            self.clip_selected(True)
        elif action == "__clip_paste__":
            self.paste_clipped(term)
        elif action == "__clip_file_clear__":
            self.clear_file_clipboard()
        elif action == "__path_copy__":
            self.copy_selected_text(True)
        elif action == "__filename_copy__":
            self.copy_selected_text(False)
        elif action == "__copy__":
            self.copy_selected(term)
        elif action == "__merge_copy__":
            self.merge_copy_selected(term)
        elif action == "__move__":
            self.move_selected(term)
        elif action == "__mode_preview__":
            self.mode = "preview"
        elif action == "__mode_dual__":
            self.mode = "dual"
        elif action == "__sort__":
            self.sort_selected(term)
        elif action == "__dir__":
            self.directory_selected(term)
        elif action == "__compare__":
            self.compare_dirs()
        elif action == "__duplexes__":
            self.duplexes()
        elif action == "__wrap_sync__":
            self.toggle_preview_wrap() if self.mode == "preview" else self.sync_other_pane()
        elif action == "__line__":
            self.toggle_preview_numbers() if self.mode == "preview" else self.preview_selected(term)
        elif action == "__datetime__":
            self.toggle_datetime()
        elif action == "__hide_empty_directories__":
            self.toggle_hide_empty_directories()
        elif action == "__mouse_cursor__":
            self.toggle_mouse_cursor(term)
        elif action == "__wheel_scroll__":
            self.toggle_wheel_scroll(term)
        elif action == "__git_tree_commit_id__":
            self.pane.git_tree_show_commit = not self.pane.git_tree_show_commit
            self.refresh()
            self.status = f"commit id: {'show' if self.pane.git_tree_show_commit else 'hide'}"
        elif action == "__git_tree_time__":
            self.pane.git_tree_relative_time = not self.pane.git_tree_relative_time
            self.refresh()
            self.status = f"graph time: {'relative' if self.pane.git_tree_relative_time else 'datetime'}"
        elif action == "__search__":
            self.search_files(term)
        elif action == "__filename_search__":
            self.search_filenames(term)
        elif action == "__bulk_name_replace__":
            self.bulk_name_replace(term)
        elif action == "__filter__":
            self.set_filter(term)
        elif action == "__git__":
            self.git_selected(term)
        elif action == "__git_init__":
            self.git_initialize(term)
        elif action == "__git_add__":
            self.git_add_selected(term)
        elif action == "__git_add_ignore__":
            self.git_add_ignore_selected()
        elif action == "__git_show__":
            self.confirm_and_run_git(term, "git show")
        elif action == "__git_history__":
            self.git_history_selected()
        elif action == "__git_status__":
            self.git_status_selected()
        elif action == "__git_unmanaged__":
            self.git_unmanaged_selected()
        elif action == "__git_managed__":
            self.git_managed_selected()
        elif action == "__git_unmanage__":
            self.git_unmanage_selected(term)
        elif action == "__git_discard__":
            self.git_discard_selected(term)
        elif action == "__git_tree__":
            self.git_tree_selected()
        elif action == "__git_tree_checkout__":
            self.git_tree_checkout(term)
        elif action == "__git_tree_scope__":
            self.git_tree_scope_selected(term)
        elif action == "__git_branch_list__":
            self.git_branch_list(term)
        elif action == "__git_new_branch__":
            self.git_new_branch(term)
        elif action == "__git_merge_branch__":
            self.git_merge_branch(term)
        elif action == "__git_commit_checkout__":
            self.git_commit_file_checkout(term)
        elif action == "__git_commit_copy__":
            self.git_commit_file_copy(term)
        elif action == "__git_commit__":
            self.git_commit(term)
        elif action == "__git_push__":
            self.confirm_and_run_git(term, "git push")
        elif action == "__git_pull__":
            self.confirm_and_run_git(term, "git pull")
        elif action == "__launcher__":
            self.launcher_selected(term)
        elif action == "__setting_tool__":
            self.run_setting_tool(term)
        elif action == "__full_shell__":
            self.full_screen_shell(term)
        elif action == "__run__":
            self.run_shell(term, self.selected())
        elif action == "__new_text__":
            self.new_text_file(term)
        elif action == "__new_archive__":
            self.new_archive(term)
        else:
            self.confirm_and_run_command(term, action, self.selected().path if self.selected() is not None else None)

    def confirm_and_run_git(self, term: Terminal, command: str) -> None:
        if self.pane.zip_path is not None or git_root(self.cwd) is None:
            self.status = "git repositoryではありません"
            return
        self.confirm_and_run_command(term, command, None)

    def refresh_all(self, restore_focus: bool = False) -> None:
        old_active = self.active_pane
        for index in range(len(self.panes)):
            self.active_pane = index
            self.ensure_pane_cwd_exists(self.pane)
            self.refresh()
        self.active_pane = old_active
        if restore_focus:
            self.restore_saved_focus()

    def ensure_all_pane_cwds_exist(self) -> bool:
        changed = False
        old_active = self.active_pane
        for index, pane in enumerate(self.panes):
            self.active_pane = index
            changed = self.ensure_pane_cwd_exists(pane) or changed
        self.active_pane = old_active
        return changed

    def ensure_pane_cwd_exists(self, pane: PaneState) -> bool:
        if pane.cwd.is_dir():
            return False
        fallback = nearest_existing_dir(pane.cwd, Path.cwd())
        pane.cwd = fallback
        self.reset_pane_location_state(pane)
        if pane is self.pane:
            self.status = f"directory fallback: {fallback}"
        return True

    def reset_pane_location_state(self, pane: PaneState) -> None:
        pane.zip_path = None
        pane.zip_dir = ""
        pane.search_mode = False
        pane.search_pattern = ""
        pane.search_kind = "content"
        pane.git_history_mode = False
        pane.git_history_file = None
        pane.git_status_mode = False
        pane.git_tree_mode = False
        pane.git_commit_files_mode = False
        pane.git_commit_hash = ""
        pane.git_commit_parent = ""
        pane.compare_mode = False
        pane.duplex_mode = False
        pane.duplex_root = None
        pane.thuru_return_path = None
        pane.thuru_preview_path = None
        pane.cursor = 0
        pane.top = 0
        if pane.marks is not None:
            pane.marks.clear()

    def retarget_panes_after_rename(self, old_path: Path, new_path: Path) -> None:
        for pane in self.panes:
            cwd = retarget_path_after_rename(pane.cwd, old_path, new_path)
            zip_path = retarget_path_after_rename(pane.zip_path, old_path, new_path) if pane.zip_path is not None else None
            changed = cwd != pane.cwd or zip_path != pane.zip_path
            if not changed:
                continue
            pane.cwd = cwd
            if zip_path is not None:
                pane.zip_path = zip_path
            pane.cursor = 0
            pane.top = 0
            if pane.marks is not None:
                pane.marks.clear()

    def fallback_panes_after_delete(self, deleted_paths: list[Path]) -> None:
        for pane in self.panes:
            for deleted in deleted_paths:
                if path_is_same_or_inside(pane.cwd, deleted):
                    pane.cwd = nearest_existing_dir(deleted.parent, Path.cwd())
                    self.reset_pane_location_state(pane)
                    break
                if pane.zip_path is not None and path_is_same_or_inside(pane.zip_path, deleted):
                    pane.cwd = nearest_existing_dir(deleted.parent, Path.cwd())
                    self.reset_pane_location_state(pane)
                    break

    def reload_current(self, term: Terminal | None = None) -> None:
        if is_thuru_path(self.cwd, self.config.thurupaths):
            if term is None or self.confirm_key(term, "get list? (N/y)"):
                self.pane.thuru_list_path = self.cwd
            else:
                self.status = "reload canceled"
                return
        self.refresh_all()
        self.status = "reloaded"

    def note_input_activity(self) -> None:
        self.last_input_time = time.monotonic()

    def idle_watch_due(self, interval: float = 0.75, idle_delay: float = 1.5) -> bool:
        now = time.monotonic()
        if now - self.last_input_time < idle_delay:
            return False
        if now < self.next_watch_update:
            return False
        self.next_watch_update = now + interval
        return True

    def idle_watch_tick(self) -> bool:
        if not self.idle_watch_due():
            return False
        if self.ensure_all_pane_cwds_exist():
            self.refresh_all()
            return True
        self.update_watchers()
        self.mark_snapshot_changes_dirty()
        return self.apply_auto_refresh()

    def mark_snapshot_changes_dirty(self) -> None:
        for pane in self.panes:
            if self.watch_target(pane) is None or pane.watch_snapshot is None:
                continue
            current = entry_watch_snapshot(pane.entries)
            if current != pane.watch_snapshot:
                pane.watch_dirty = True

    def update_watchers(self) -> None:
        for pane in self.panes:
            target = self.watch_target(pane)
            if same_watch_path(target, pane.watch_path):
                continue
            self.stop_watcher(pane)
            pane.watch_path = target
            if target is not None:
                self.start_watcher(pane, target)

    def watch_target(self, pane: PaneState) -> Path | None:
        if pane is not self.pane and self.mode != "dual":
            return None
        if pane.zip_path is not None or self.is_temporary_pane(pane) or self.is_thuru_blocked(pane):
            return None
        if not pane.cwd.is_dir() or is_network_like_path(pane.cwd):
            return None
        return pane.cwd

    def is_temporary_pane(self, pane: PaneState) -> bool:
        return pane.duplex_mode or pane.compare_mode or pane.search_mode or pane.git_history_mode or pane.git_status_mode or pane.git_tree_mode or pane.git_commit_files_mode

    def start_watcher(self, pane: PaneState, path: Path) -> None:
        pane.watch_token += 1
        pane.watch_dirty = False
        stop_event = threading.Event()
        pane.watch_stop = stop_event
        token = pane.watch_token
        worker = watch_directory_windows_poll if IS_WINDOWS else watch_directory_kqueue
        threading.Thread(target=worker, args=(path, stop_event, pane, token), daemon=True).start()

    def stop_watcher(self, pane: PaneState) -> None:
        if pane.watch_stop is not None:
            pane.watch_stop.set()
        pane.watch_stop = None
        pane.watch_path = None
        pane.watch_token += 1
        pane.watch_dirty = False

    def stop_watchers(self) -> None:
        for pane in self.panes:
            self.stop_watcher(pane)

    def apply_auto_refresh(self) -> bool:
        changed = False
        old_active = self.active_pane
        for index, pane in enumerate(self.panes):
            if not pane.watch_dirty:
                continue
            pane.watch_dirty = False
            if self.watch_target(pane) is None:
                if not self.ensure_pane_cwd_exists(pane):
                    continue
            self.active_pane = index
            self.refresh()
            changed = True
        self.active_pane = old_active
        if changed:
            self.status = "auto refreshed"
        return changed

    def apply_saved_stat(self, stat: dict[str, object]) -> None:
        active = stat.get("active_pane")
        if isinstance(active, int) and active in (0, 1):
            self.active_pane = active
        dual_ratio = stat.get("dual_ratio")
        if isinstance(dual_ratio, (int, float)):
            self.dual_ratio = min(0.8, max(0.2, float(dual_ratio)))
        log_height = stat.get("log_height")
        if isinstance(log_height, int):
            self.log_height = min(99, max(1, log_height))
        for index, pane in enumerate(self.panes):
            prefix = "left" if index == 0 else "right"
            preview_ratio = stat.get(f"{prefix}_preview_ratio")
            if isinstance(preview_ratio, (int, float)):
                pane.preview_ratio = min(0.8, max(0.3, float(preview_ratio)))
            sort_key = stat.get(f"{prefix}_sort_key")
            if sort_key in ("name", "natural", "ext", "size", "mtime"):
                pane.sort_key = str(sort_key)
            pane.sort_reverse = bool(stat.get(f"{prefix}_sort_reverse", pane.sort_reverse))
            cursor = stat.get(f"{prefix}_cursor")
            if isinstance(cursor, int) and cursor >= 0:
                self.restore_cursors[index] = cursor
            target = stat.get(f"{prefix}_selected")
            if isinstance(target, str):
                self.restore_targets[index] = target
            history = stat.get(f"{prefix}_history")
            pos = stat.get(f"{prefix}_history_pos")
            if isinstance(history, list):
                values = [item for item in history if isinstance(item, str) and Path(item).is_dir()]
                if values:
                    self.dir_history[index] = values[-100:]
                    self.dir_history_pos[index] = min(max(0, int(pos) if isinstance(pos, int) else len(values) - 1), len(self.dir_history[index]) - 1)

    def restore_saved_focus(self) -> None:
        for index, pane in enumerate(self.panes):
            target = self.restore_targets[index]
            if target:
                for entry_index, entry in enumerate(pane.entries):
                    if str(entry.path) == target:
                        pane.cursor = entry_index
                        break
                else:
                    pane.cursor = min(self.restore_cursors[index], max(0, len(pane.entries) - 1))
            else:
                pane.cursor = min(self.restore_cursors[index], max(0, len(pane.entries) - 1))
            if pane.cursor < pane.top:
                pane.top = pane.cursor
            self.restore_targets[index] = None

    def filer_stat(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "active_pane": self.active_pane,
            "dual_ratio": self.dual_ratio,
            "log_height": self.log_height,
            "left_cwd": str(self.panes[0].cwd),
            "right_cwd": str(self.panes[1].cwd),
            "left_preview_ratio": self.panes[0].preview_ratio,
            "right_preview_ratio": self.panes[1].preview_ratio,
            "left_sort_key": self.panes[0].sort_key,
            "right_sort_key": self.panes[1].sort_key,
            "left_sort_reverse": self.panes[0].sort_reverse,
            "right_sort_reverse": self.panes[1].sort_reverse,
            "left_cursor": self.panes[0].cursor,
            "right_cursor": self.panes[1].cursor,
            "left_selected": selected_path_text(self.panes[0]),
            "right_selected": selected_path_text(self.panes[1]),
            "preview_file": selected_path_text(self.pane) if self.mode == "preview" else "",
            "left_history": self.dir_history[0][-100:],
            "right_history": self.dir_history[1][-100:],
            "left_history_pos": self.dir_history_pos[0],
            "right_history_pos": self.dir_history_pos[1],
        }

    def push_dir_history(self, pane_index: int | None = None) -> None:
        index = self.active_pane if pane_index is None else pane_index
        pane = self.panes[index]
        if pane.zip_path is not None:
            return
        path = str(pane.cwd)
        history = self.dir_history[index]
        pos = self.dir_history_pos[index]
        if 0 <= pos < len(history) and history[pos] == path:
            return
        history[:] = history[: pos + 1]
        history.append(path)
        if len(history) > 100:
            del history[:-100]
        self.dir_history_pos[index] = len(history) - 1

    def move_dir_history(self, delta: int) -> None:
        history = self.dir_history[self.active_pane]
        if not history:
            self.status = "history empty"
            return
        pos = min(max(0, self.dir_history_pos[self.active_pane] + delta), len(history) - 1)
        if pos == self.dir_history_pos[self.active_pane]:
            self.status = "history edge"
            return
        path = Path(history[pos])
        if not path.is_dir():
            self.status = f"history not found: {path}"
            return
        path = path.resolve()
        if not self.can_enter_dir(path):
            return
        self.dir_history_pos[self.active_pane] = pos
        self.cwd = path
        self.pane.zip_path = None
        self.pane.zip_dir = ""
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.pane.git_status_mode = False
        self.pane.git_tree_mode = False
        self.pane.git_commit_files_mode = False
        self.pane.git_commit_hash = ""
        self.pane.git_commit_parent = ""
        self.pane.compare_mode = False
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"history: {path}"

    def refresh(self) -> None:
        self.ensure_pane_cwd_exists(self.pane)
        if self.pane.duplex_mode:
            self.entries = list_duplex_entries(self.pane.duplex_root or self.cwd)
        elif self.pane.compare_mode:
            self.entries = list_compare_entries(
                self.pane.compare_left,
                self.pane.compare_right,
                self.pane.compare_left_zip,
                self.pane.compare_left_zip_dir,
                self.pane.compare_right_zip,
                self.pane.compare_right_zip_dir,
            )
        elif self.pane.git_history_mode:
            self.entries = list_git_history_entries(self.cwd, self.pane.git_history_file)
        elif self.pane.git_status_mode:
            self.entries = list_git_managed_entries(self.cwd) if self.pane.git_status_kind == "managed" else list_git_status_entries(self.cwd, self.pane.git_status_kind == "unmanaged")
        elif self.pane.git_tree_mode:
            self.entries = list_git_tree_entries(self.cwd, self.pane.git_tree_scope, self.pane.git_tree_show_commit, self.pane.git_tree_relative_time)
        elif self.pane.git_commit_files_mode:
            self.entries = list_git_commit_file_entries(self.cwd, self.pane.git_commit_hash)
        elif self.pane.search_mode and self.is_thuru_blocked(self.pane):
            self.entries = []
        elif self.pane.search_mode:
            if self.pane.search_kind == "name":
                self.entries = list_filename_search_entries(self.cwd, self.pane.search_pattern)
            else:
                self.entries = list_search_entries(self.cwd, self.pane.search_pattern)
        elif self.pane.zip_path is not None:
            self.entries = list_zip_entries(self.pane.zip_path, self.pane.zip_dir, self.filter_text)
        elif self.is_thuru_blocked(self.pane):
            self.entries = self.thuru_return_entries(self.pane)
        else:
            self.entries = list_entries(self.cwd, self.filter_text, EDITOR_STATE.hide_empty_directories)
        if not self.pane.search_mode and not self.pane.git_history_mode and not self.pane.git_status_mode and not self.pane.git_tree_mode and not self.pane.git_commit_files_mode and not self.pane.compare_mode and not self.pane.duplex_mode and not self.is_thuru_blocked(self.pane):
            sort_entries(self.entries, self.pane.sort_key, self.pane.sort_reverse)
            if self.config.show_ownerpath:
                parent = zip_owner_entry(self.pane.zip_path, self.pane.zip_dir) if self.pane.zip_path is not None else owner_entry(self.cwd)
                if parent is not None:
                    self.entries.insert(0, parent)
        if self.cursor >= len(self.entries):
            self.cursor = max(0, len(self.entries) - 1)
        if self.cursor < self.top:
            self.top = self.cursor
        self.update_watch_snapshot(self.pane)

    def update_watch_snapshot(self, pane: PaneState) -> None:
        if self.watch_target(pane) is None:
            pane.watch_snapshot = None
            return
        pane.watch_snapshot = entry_watch_snapshot(pane.entries)

    def is_thuru_blocked(self, pane: PaneState) -> bool:
        if not is_thuru_path(pane.cwd, self.config.thurupaths):
            return False
        return not self.is_thuru_allowed(pane, pane.cwd)

    def is_thuru_allowed(self, pane: PaneState, path: Path) -> bool:
        allowed = pane.thuru_list_path
        if allowed is None:
            return False
        return same_existing_path(path, allowed) or is_path_inside(path, allowed)

    def thuru_return_entries(self, pane: PaneState) -> list[Entry]:
        parent = owner_entry(pane.cwd)
        return [parent] if parent is not None else []

    def selected(self) -> Entry | None:
        if not self.entries:
            return None
        return self.entries[self.cursor]

    def marked_entries(self) -> list[Entry]:
        marks = self.pane.marks or set()
        return [entry for entry in self.entries if not is_owner_entry(entry) and entry_key(entry) in marks]

    def selected_entries(self) -> list[Entry]:
        marked = self.marked_entries()
        if marked:
            if self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.compare_mode:
                return marked
            return self.unique_file_entries(marked) if self.pane.search_mode else marked
        entry = self.selected()
        if entry is not None and is_owner_entry(entry):
            return []
        if entry is not None and self.pane.search_mode:
            return self.unique_file_entries([entry])
        return [entry] if entry is not None else []

    def unique_file_entries(self, entries: list[Entry]) -> list[Entry]:
        seen: set[Path] = set()
        unique: list[Entry] = []
        for entry in entries:
            if entry.path in seen:
                continue
            seen.add(entry.path)
            try:
                stat = entry.path.stat()
                unique.append(Entry(entry.path, entry.path.name, entry.path.is_dir(), stat.st_size, mtime=stat.st_mtime))
            except OSError:
                unique.append(Entry(entry.path, entry.path.name, entry.path.is_dir(), entry.size, mtime=entry.mtime))
        return unique

    def git_history_target_available(self) -> bool:
        entry = self.selected()
        return entry is not None and not entry.is_dir and entry.zip_path is None

    def toggle_mark(self) -> None:
        entry = self.selected()
        if entry is None or is_owner_entry(entry):
            return
        if self.pane.marks is None:
            self.pane.marks = set()
        key = entry_key(entry)
        if key in self.pane.marks:
            self.pane.marks.remove(key)
        else:
            if self.pane.git_history_mode and len(self.pane.marks) >= 2:
                self.status = "history marks: max 2"
                return
            self.pane.marks.add(key)
        self.move_cursor(1)

    def mark_all(self) -> None:
        if self.pane.git_history_mode:
            self.status = "history marks: max 2"
            return
        if self.pane.marks is None:
            self.pane.marks = set()
        if self.pane.marks:
            self.pane.marks.clear()
            self.status = "marks cleared"
            return
        self.pane.marks = {entry_key(entry) for entry in self.entries if not is_owner_entry(entry)}
        self.status = f"marked: {len(self.pane.marks)} item(s)"

    def clear_marks(self) -> None:
        if self.pane.marks is not None:
            self.pane.marks.clear()

    def current_git_tree_commit(self) -> str:
        if not self.pane.git_tree_mode:
            return ""
        entry = self.selected()
        return entry.search_text if entry is not None else ""

    def sync_git_tree_preview_state(self) -> None:
        if not self.pane.git_tree_mode:
            return
        commit = self.current_git_tree_commit()
        if self.pane.git_tree_preview_commit != commit:
            self.pane.git_tree_preview_commit = commit
            self.pane.git_tree_preview_time = time.monotonic()
            self.pane.git_tree_detail_commit = commit if git_commit_detail_cached(self.cwd, commit) else ""

    def request_git_tree_detail(self, auto: bool = False) -> None:
        commit = self.current_git_tree_commit()
        if not commit:
            return
        self.pane.git_tree_preview_commit = commit
        self.pane.git_tree_detail_commit = commit
        self.status = "git show --stat" + (" auto" if auto else "")

    def git_tree_waiting_for_detail(self) -> bool:
        if not IS_WINDOWS or self.mode != "preview" or not self.pane.git_tree_mode:
            return False
        self.sync_git_tree_preview_state()
        commit = self.current_git_tree_commit()
        return bool(commit and self.pane.git_tree_detail_commit != commit)

    def git_tree_auto_detail_due(self) -> bool:
        if not self.git_tree_waiting_for_detail():
            return False
        return time.monotonic() - self.pane.git_tree_preview_time >= 1.0

    def shell_return_entry_text(self, entry: Entry) -> str:
        origin = self.shell_origin_cwd
        text = entry.name
        if origin is not None and not same_existing_path(entry.path.parent, origin):
            text = stable_path_text(entry.path)
        if entry.is_dir and not text.endswith("/"):
            text += "/"
        return quote_path(text)

    def is_temporary_view(self) -> bool:
        return self.pane.duplex_mode or self.pane.compare_mode or self.pane.search_mode or self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.git_commit_files_mode

    def close_temporary_view(self) -> None:
        if self.pane.duplex_mode:
            self.clear_duplexes()
        elif self.pane.compare_mode:
            self.clear_compare()
        elif self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.git_commit_files_mode:
            self.clear_git_view()
        elif self.pane.search_mode:
            self.clear_search()

    def enter_git_preview_view(self) -> None:
        if self.mode == "dual" and not self.git_view_return_mode:
            self.git_view_return_mode = "dual"
            self.git_view_return_active = self.active_pane
        self.mode = "preview"
        self.log_focus = False

    def handle_key(self, term: Terminal, key: str) -> None:
        if not key:
            return
        if key in (KEY_WHEEL_UP, KEY_WHEEL_DOWN):
            self.handle_wheel(term, key)
            return
        if key.startswith(KEY_MOUSE + ":"):
            self.handle_mouse(term, key)
            return
        key = normalize_move_key(key)
        if self.root_pending and key != "\\":
            self.root_pending = False
        if self.resident_mode and key == KEY_SHIFT_ENTER:
            entry = self.selected()
            if entry is not None and not is_owner_entry(entry):
                self.shell_return_text = self.shell_return_entry_text(entry)
                self.running = False
            return
        if key == "\t":
            self.cycle_focus()
        elif self.log_focus and self.handle_log_key(term, key):
            return
        elif key == KEY_ESCAPE and self.is_temporary_view():
            self.close_temporary_view()
        elif key in ("q", "Q", KEY_ESCAPE):
            if self.resident_mode and key == KEY_ESCAPE:
                self.running = False
                return
            if not self.config.quit_prompt or self.confirm_quit(term):
                self.running = False
        elif key == "1":
            self.log_focus = False
            self.mode = "preview"
            self.status = "mode: preview  ?:help"
        elif key == "2":
            self.log_focus = False
            if self.pane.compare_mode:
                self.clear_compare()
            else:
                self.mode = "dual"
                self.status = "mode: dual  ?:help"
        elif key == "?":
            self.show_help(term)
        elif key in (KEY_F1, KEY_F2, KEY_F3, KEY_F4, KEY_F6):
            self.filer_menu(term, {KEY_F1: 0, KEY_F2: 1, KEY_F3: 2, KEY_F4: 3, KEY_F6: 4}[key])
        elif key == KEY_F5:
            self.reload_current(term)
        elif self.mode == "preview" and self.pane.preview_focus and not self.log_focus and key in (KEY_UP, KEY_DOWN, KEY_PGUP, KEY_PGDN, "j", "J", "k", "K"):
            self.scroll_preview(term, key)
        elif self.mode == "preview" and self.pane.preview_focus and not self.log_focus and self.preview_jump_available() and key in ("n", "N", "b", "B"):
            if not self.jump_preview_diff(term, key in ("n", "N")):
                self.status = "diff not found"
        elif key in (KEY_UP, "k", "K"):
            self.move_cursor(-1)
            self.pane.preview_top = 0
            self.pane.thuru_preview_path = None
        elif key in (KEY_DOWN, "j", "J"):
            self.move_cursor(1)
            self.pane.preview_top = 0
            self.pane.thuru_preview_path = None
        elif key == KEY_HOME:
            self.cursor = 0
            self.top = 0
            self.pane.thuru_preview_path = None
        elif key == KEY_END:
            self.cursor = max(0, len(self.entries) - 1)
            self.pane.thuru_preview_path = None
        elif key == KEY_PGUP:
            self.move_cursor(-self.page_step(term))
            self.pane.thuru_preview_path = None
        elif key == KEY_PGDN:
            self.move_cursor(self.page_step(term))
            self.pane.thuru_preview_path = None
        elif key == KEY_F7:
            self.filer_pane_size_mode(term)
        elif key in (KEY_LEFT, KEY_RIGHT) and self.mode == "dual":
            if (self.active_pane == 0 and key == KEY_RIGHT) or (self.active_pane == 1 and key == KEY_LEFT):
                self.switch_pane(1 if key == KEY_RIGHT else -1)
        elif IS_WINDOWS and key == KEY_RIGHT and self.mode == "preview" and self.pane.git_tree_mode:
            self.request_git_tree_detail()
        elif key == KEY_RIGHT and self.mode == "preview":
            self.log_focus = False
            self.pane.preview_focus = True
        elif key == KEY_LEFT and self.mode == "preview":
            self.log_focus = False
            self.pane.preview_focus = False
        elif key == KEY_CTRL_ENTER:
            self.open_selected_os()
        elif key == KEY_ENTER:
            if not self.paste_selected_to_log_prompt():
                self.open_selected(term)
        elif key == KEY_BACKSPACE:
            if self.is_temporary_view():
                self.close_temporary_view()
            else:
                self.go_parent(term)
        elif key == "\\":
            if self.root_pending:
                self.root_pending = False
                self.go_root()
            else:
                self.root_pending = True
                self.status = "\\ again: root"
        elif key == "[":
            self.move_dir_history(-1)
        elif key == "]":
            self.move_dir_history(1)
        elif key == "b":
            self.bookmark_selected(term)
        elif key == "B":
            self.bookmark_add(term)
        elif key in ("e", "E"):
            self.edit_selected(term)
        elif key in ("i", "I"):
            self.information_selected(term)
        elif key in ("x", "X"):
            self.launcher_selected(term)
        elif key in ("g", "G"):
            self.git_selected(term)
        elif key in ("s", "S"):
            self.sort_selected(term)
        elif key in ("l", "L"):
            self.directory_selected(term)
        elif key in ("w", "W"):
            if self.mode == "preview":
                self.toggle_preview_wrap()
            else:
                self.sync_other_pane()
        elif key in ("y", "Y"):
            self.allow_thuru_preview()
        elif key in ("v", "V"):
            self.preview_selected(term)
        elif key == " ":
            self.toggle_mark()
        elif key in ("a", "A"):
            self.mark_all()
        elif key in ("r", "R"):
            self.rename_selected(term)
        elif key in ("n", "N"):
            self.mkdir(term)
        elif key in ("d", "D", KEY_DELETE):
            self.delete_selected(term)
        elif key in ("c", "C"):
            self.copy_selected(term)
        elif key in ("m", "M"):
            self.move_selected(term)
        elif key == KEY_F9:
            self.clip_selected(False)
        elif key == KEY_SHIFT_F9:
            self.clip_selected(True)
        elif key == KEY_F10:
            self.paste_clipped(term)
        elif key in ("f", "F"):
            self.search_files(term)
        elif key == "/":
            self.set_filter(term)

    def handle_wheel(self, term: Terminal, key: str) -> None:
        if not EDITOR_STATE.wheel_scroll:
            return
        if self.log_focus:
            self.scroll_log(term, KEY_UP if key == KEY_WHEEL_UP else KEY_DOWN)
            return
        if self.mode == "preview" and self.pane.preview_focus:
            self.scroll_preview(term, KEY_UP if key == KEY_WHEEL_UP else KEY_DOWN)
            return
        step = -3 if key == KEY_WHEEL_UP else 3
        body_height = self.current_body_height(term)
        self.cursor, self.top = wheel_scroll_position(self.cursor, self.top, len(self.entries), body_height, step)
        self.pane.preview_top = 0
        self.pane.thuru_preview_path = None

    def handle_mouse(self, term: Terminal, key: str) -> None:
        if not EDITOR_STATE.mouse_cursor:
            return
        event = mouse_event(key)
        if event is None:
            return
        button, col, row, press = event
        if not press or button != 0:
            return
        columns, lines = term.size()
        body_height = filer_body_height(lines, self.log_height)
        log_height = filer_log_display_height(lines, self.log_height)
        log_start = 4 + body_height
        if log_start <= row < log_start + log_height:
            self.log_focus = True
            self.log_cwd = self.cwd
            self.status = ""
            return
        first_row = 3
        if row < first_row or row >= first_row + body_height:
            return
        screen_row = row - first_row
        if self.mode == "preview":
            list_width = max(20, min(columns - 1, int(columns * self.pane.preview_ratio)))
            if col <= list_width:
                self.log_focus = False
                self.pane.preview_focus = False
                self.cursor = min(max(0, self.top + screen_row), max(0, len(self.entries) - 1))
                self.pane.preview_top = 0
                self.pane.thuru_preview_path = None
                self.status = "mouse"
            else:
                self.log_focus = False
                self.pane.preview_focus = True
                self.status = "preview pane"
            return
        left_width = max(20, min(columns - 21, int(columns * self.dual_ratio)))
        if col <= left_width:
            self.log_focus = False
            self.active_pane = 0
            pane = self.panes[0]
        elif col > left_width + 1:
            self.log_focus = False
            self.active_pane = 1
            pane = self.panes[1]
        else:
            return
        pane.cursor = min(max(0, pane.top + screen_row), max(0, len(pane.entries) - 1))
        pane.preview_top = 0
        pane.thuru_preview_path = None
        self.status = "mouse"

    def clear_search(self) -> None:
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.pane.search_kind = "content"
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = "search closed"

    def clear_git_view(self) -> None:
        if self.pane.git_commit_files_mode:
            commit = self.pane.git_commit_hash
            self.pane.git_commit_files_mode = False
            self.pane.git_commit_hash = ""
            self.pane.git_commit_parent = ""
            self.pane.git_tree_mode = True
            self.pane.git_status_mode = False
            self.pane.git_history_mode = False
            self.pane.git_history_file = None
            self.pane.git_tree_preview_commit = ""
            self.pane.git_tree_detail_commit = ""
            self.pane.git_tree_preview_time = 0.0
            self.cursor = 0
            self.top = 0
            self.clear_marks()
            self.refresh()
            for index, entry in enumerate(self.entries):
                if entry.search_text == commit:
                    self.cursor = index
                    break
            self.sync_git_tree_preview_state()
            self.status = f"tree: {len(self.entries)} commit(s)"
            return
        target = self.pane.git_history_file
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.pane.git_status_mode = False
        self.pane.git_tree_mode = False
        self.pane.git_commit_files_mode = False
        self.pane.git_commit_hash = ""
        self.pane.git_commit_parent = ""
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        if target is not None:
            self.focus_path_in_pane(self.active_pane, target)
        if self.git_view_return_mode == "dual":
            self.mode = "dual"
            self.active_pane = self.git_view_return_active
            self.git_view_return_mode = ""
            self.refresh_all()
        else:
            self.git_view_return_mode = ""
        self.status = "git view closed"

    def compare_dirs(self) -> None:
        if self.mode != "dual":
            self.status = "compare: dual mode only"
            self.append_log(self.status)
            return
        left_zip = self.panes[0].zip_path
        right_zip = self.panes[1].zip_path
        left = self.panes[0].cwd
        right = self.panes[1].cwd
        if left_zip is not None:
            left = left_zip
        if right_zip is not None:
            right = right_zip
        self.compare_return_active = self.active_pane
        self.mode = "preview"
        self.active_pane = 0
        pane = self.pane
        pane.compare_mode = True
        pane.compare_left = left
        pane.compare_right = right
        pane.compare_left_zip = left_zip
        pane.compare_left_zip_dir = self.panes[0].zip_dir
        pane.compare_right_zip = right_zip
        pane.compare_right_zip_dir = self.panes[1].zip_dir
        pane.search_mode = False
        pane.search_pattern = ""
        pane.git_history_mode = False
        pane.git_history_file = None
        pane.git_status_mode = False
        pane.git_tree_mode = False
        pane.git_commit_files_mode = False
        pane.git_commit_hash = ""
        pane.git_commit_parent = ""
        pane.preview_focus = False
        pane.preview_top = 0
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"compare: {len(self.entries)} diff item(s)"
        self.append_log(self.status)

    def clear_compare(self) -> None:
        self.pane.compare_mode = False
        self.pane.compare_left = None
        self.pane.compare_right = None
        self.pane.compare_left_zip = None
        self.pane.compare_left_zip_dir = ""
        self.pane.compare_right_zip = None
        self.pane.compare_right_zip_dir = ""
        self.mode = "dual"
        self.active_pane = self.compare_return_active
        self.refresh_all()
        self.status = "compare closed"

    def duplexes(self) -> None:
        if self.mode == "dual":
            self.status = "duplexes: one pane mode only"
            self.append_log(self.status)
            return
        if self.pane.zip_path is not None:
            self.status = "duplexes: zip unsupported"
            self.append_log(self.status)
            return
        pane = self.pane
        pane.duplex_mode = True
        pane.duplex_root = self.cwd
        pane.search_mode = False
        pane.search_pattern = ""
        pane.git_history_mode = False
        pane.git_history_file = None
        pane.git_status_mode = False
        pane.git_tree_mode = False
        pane.git_commit_files_mode = False
        pane.git_commit_hash = ""
        pane.git_commit_parent = ""
        pane.compare_mode = False
        pane.preview_focus = False
        pane.preview_top = 0
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"duplexes: {len(self.entries)} duplicate file(s)"
        self.append_log(self.status)

    def clear_duplexes(self) -> None:
        self.pane.duplex_mode = False
        self.pane.duplex_root = None
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = "duplexes closed"

    def allow_thuru_preview(self) -> None:
        entry = self.selected()
        if self.mode == "preview" and entry is not None and entry.is_dir and is_thuru_path(entry.path, self.config.thurupaths):
            self.pane.thuru_preview_path = entry.path
            self.pane.preview_top = 0
            self.status = f"preview list: {entry.name}"

    def switch_pane(self, delta: int) -> None:
        self.log_focus = False
        self.active_pane = (self.active_pane + delta) % len(self.panes)
        self.status = "?:help"

    def cycle_focus(self) -> None:
        if self.log_focus:
            self.log_focus = False
            self.status = ""
        else:
            if not self.log_input:
                self.log_cwd = self.cwd
            self.log_focus = True
            self.status = ""

    def append_log(self, text: str, term: Terminal | None = None) -> None:
        self.log_lines.append(text)
        if len(self.log_lines) > 1000:
            del self.log_lines[:-1000]
        height = self.current_log_scroll_height(term) if term is not None else max(1, self.log_height - 1)
        self.log_top = max(0, len(self.log_lines) - height)
        self.log_follow_bottom = True

    def append_tail_log(self, text: str, term: Terminal | None = None) -> None:
        follow = self.log_follow_bottom
        self.log_lines.append(text)
        if len(self.log_lines) > 1000:
            del self.log_lines[:-1000]
        if follow:
            height = self.current_log_scroll_height(term) if term is not None else max(1, self.log_height - 1)
            self.log_top = max(0, len(self.log_lines) - height)
        self.log_follow_bottom = follow

    def append_live_log(self, term: Terminal, text: str) -> None:
        self.append_log(text, term)
        self.draw(term)
        term.flush()

    def fail_status(self, message: str) -> None:
        self.status = message
        self.append_log(message)

    def handle_log_key(self, term: Terminal, key: str) -> bool:
        if key == KEY_ENTER:
            self.run_log_command(term)
            return True
        if key == KEY_ESCAPE:
            if self.log_tail is not None:
                self.log_tail.active = False
                self.log_tail = None
                self.status = "tail stopped"
            elif self.log_input:
                self.log_input = []
                self.log_input_cursor = 0
                self.status = ""
            else:
                self.log_focus = False
                self.status = ""
            return True
        if key in (KEY_UP, KEY_DOWN, KEY_CTRL_UP, KEY_CTRL_DOWN):
            self.recall_log_history(key in (KEY_UP, KEY_CTRL_UP))
            return True
        if key in (KEY_PGUP, KEY_PGDN):
            self.scroll_log(term, key)
            return True
        if key == KEY_LEFT:
            self.log_input_cursor = max(0, self.log_input_cursor - 1)
            return True
        if key == KEY_RIGHT:
            self.log_input_cursor = min(len(self.log_input), self.log_input_cursor + 1)
            return True
        if key == KEY_CTRL_LEFT or key == KEY_HOME:
            self.log_input_cursor = 0
            return True
        if key == KEY_CTRL_RIGHT or key == KEY_END:
            self.log_input_cursor = len(self.log_input)
            return True
        if key == KEY_BACKSPACE:
            if self.log_input_cursor > 0:
                del self.log_input[self.log_input_cursor - 1]
                self.log_input_cursor -= 1
            return True
        if key == KEY_DELETE:
            if self.log_input_cursor < len(self.log_input):
                del self.log_input[self.log_input_cursor]
            return True
        if is_text_input(key):
            self.log_input[self.log_input_cursor:self.log_input_cursor] = list(key)
            self.log_input_cursor += len(key)
            return True
        return False

    def paste_selected_to_log_prompt(self) -> bool:
        if not self.log_input:
            return False
        entry = self.selected()
        if entry is None or entry.is_dir:
            return False
        text = quote_path(entry_display_path(entry))
        before = "".join(self.log_input[:self.log_input_cursor])
        after = "".join(self.log_input[self.log_input_cursor:])
        if before and not before[-1].isspace():
            text = " " + text
        if after and not after[0].isspace():
            text += " "
        self.log_input[self.log_input_cursor:self.log_input_cursor] = list(text)
        self.log_input_cursor += len(text)
        self.log_focus = True
        self.status = ""
        return True

    def recall_log_history(self, previous: bool) -> None:
        history = EDITOR_STATE.run_history
        if not history:
            self.status = "run history empty"
            return
        self.log_history_index += -1 if previous else 1
        self.log_history_index = min(len(history), max(0, self.log_history_index))
        value = "" if self.log_history_index == len(history) else history[self.log_history_index]
        self.log_input = list(value)
        self.log_input_cursor = len(self.log_input)
        self.status = "run history"

    def run_log_command(self, term: Terminal) -> None:
        command = "".join(self.log_input).strip()
        if not command:
            self.status = "log command empty"
            return
        self.log_tail = None
        raw_command = command
        command = expand_prompt_vars(command)
        self.log_input = []
        self.log_input_cursor = 0
        self.add_run_history(raw_command)
        self.append_log(f"{self.log_prompt_prefix()}{command}", term)
        clear_git_cache()
        self.log_busy = True
        self.draw(term)
        term.flush()
        try:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    executable=self.command_shell(),
                    cwd=str(self.log_cwd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                    check=False,
                )
            except OSError as exc:
                self.append_log(f"failed to start: {exc}", term)
                self.fail_status(f"shell failed: {exc}")
                return
            self.append_log_command_output(result.stdout, result.stderr, result.returncode, term)
            clear_git_cache()
            self.refresh_all()
            self.status = "" if result.returncode == 0 else f"shell exit: {result.returncode}"
        finally:
            self.log_busy = False

    def append_log_command_output(self, stdout: str, stderr: str, returncode: int, term: Terminal | None = None) -> None:
        if stdout:
            for line in stdout.rstrip("\n").splitlines():
                self.append_log(line, term)
        if stderr:
            self.append_log("[stderr]", term)
            for line in stderr.rstrip("\n").splitlines():
                self.append_log(line, term)
        if not stdout and not stderr:
            self.append_log("(no output)", term)
        if returncode != 0:
            self.append_log(f"exit code: {returncode}", term)

    def scroll_log(self, term: Terminal, key: str) -> None:
        height = self.current_log_scroll_height(term)
        step = height if key in (KEY_PGUP, KEY_PGDN) else 1
        delta = -step if key in (KEY_UP, KEY_PGUP, "k", "K") else step
        max_top = max(0, len(self.log_lines) - height)
        self.log_top = min(max(0, self.log_top + delta), max_top)
        self.log_follow_bottom = self.log_top >= max_top
        self.status = f"log: {min(self.log_top + 1, max(1, len(self.log_lines)))}/{max(1, len(self.log_lines))}"

    def tail_selected(self, term: Terminal) -> None:
        entry = self.selected()
        if entry is None or entry.is_dir or entry.zip_path is not None:
            self.status = "tail unavailable"
            return
        if self.log_tail is not None:
            self.log_tail.active = False
            self.log_tail = None
        lines, offset = tail_initial_lines(entry.path)
        self.log_tail = TailState(entry.path, offset, "", True, tail_last_stamp_from_rows(lines))
        self.log_lines = [f"$ tail -f {entry.path}"] + lines
        self.log_focus = False
        self.log_follow_bottom = True
        self.log_input = []
        self.log_input_cursor = 0
        self.log_top = max(0, len(self.log_lines) - self.current_log_scroll_height(term))
        self.status = f"tail: {entry.name}"

    def poll_log_tail(self, term: Terminal | None = None) -> bool:
        if self.log_tail is None or not self.log_tail.active:
            return False
        rows = read_tail_lines(self.log_tail)
        if not rows:
            return False
        for row in rows:
            self.append_tail_log(row, term)
        return True

    def current_log_height(self, term: Terminal) -> int:
        _, lines = term.size()
        return filer_log_display_height(lines, self.log_height)

    def current_log_scroll_height(self, term: Terminal) -> int:
        return max(1, self.current_log_height(term) - (1 if self.log_prompt_visible() else 0))

    def log_tail_active(self) -> bool:
        return self.log_tail is not None and self.log_tail.active

    def log_prompt_visible(self) -> bool:
        if self.log_busy:
            return False
        if self.log_tail_active() and not self.log_focus:
            return False
        if not self.log_focus and not self.log_input:
            return False
        return self.log_follow_bottom

    def current_body_height(self, term: Terminal) -> int:
        _, lines = term.size()
        return filer_body_height(lines, self.log_height)

    def sync_other_pane(self) -> None:
        other_pane = self.panes[1 - self.active_pane]
        other_pane.cwd = self.cwd
        other_pane.filter_text = self.filter_text
        other_pane.cursor = self.cursor
        other_pane.top = self.top
        other_pane.sort_key = self.pane.sort_key
        other_pane.sort_reverse = self.pane.sort_reverse
        other_pane.preview_numbers = self.pane.preview_numbers
        other_pane.zip_path = self.pane.zip_path
        other_pane.zip_dir = self.pane.zip_dir
        other_pane.marks = set()
        old_active = self.active_pane
        self.active_pane = 1 - self.active_pane
        self.refresh()
        self.push_dir_history(self.active_pane)
        self.active_pane = old_active
        self.status = "synced other pane"

    def move_cursor(self, delta: int) -> None:
        self.cursor = min(max(0, self.cursor + delta), max(0, len(self.entries) - 1))

    def scroll_preview(self, term: Terminal, key: str) -> None:
        step = self.current_body_height(term)
        max_top = self.preview_scroll_max_top(term, step)
        if key in (KEY_UP, "k", "K"):
            self.pane.preview_top = max(0, self.pane.preview_top - 1)
        elif key in (KEY_DOWN, "j", "J"):
            self.pane.preview_top = self.pane.preview_top + 1 if max_top is None else min(max_top, self.pane.preview_top + 1)
        elif key == KEY_PGUP:
            self.pane.preview_top = max(0, self.pane.preview_top - step)
        elif key == KEY_PGDN:
            self.pane.preview_top = self.pane.preview_top + step if max_top is None else min(max_top, self.pane.preview_top + step)
        if max_top is not None:
            self.pane.preview_top = min(max(0, self.pane.preview_top), max_top)
        self.status = f"preview top: {self.pane.preview_top + 1}"

    def preview_scroll_max_top(self, term: Terminal, body_height: int) -> int | None:
        if not self.preview_jump_available():
            return None
        columns, _ = term.size()
        list_width = max(20, min(columns - 1, int(columns * self.pane.preview_ratio)))
        preview_width = max(0, columns - list_width - 1)
        return max(0, len(self.preview_source_rows(preview_width, body_height)) - body_height)

    def preview_jump_available(self) -> bool:
        return self.pane.compare_mode or self.pane.git_status_mode or self.pane.git_commit_files_mode or (self.pane.git_history_mode and len(self.marked_entries()) == 2)

    def preview_source_rows(self, width: int, height: int) -> list[str]:
        if width <= 0:
            return []
        entry = self.selected()
        if entry is None:
            return []
        rows: list[str] = []
        if self.pane.git_history_mode:
            rows = self.git_history_preview_rows(width, height)
        elif self.pane.git_status_mode:
            rows = self.git_status_preview_rows(width)
        elif self.pane.git_tree_mode:
            rows = self.git_tree_preview_rows(width)
        elif self.pane.git_commit_files_mode:
            rows = self.git_commit_file_preview_rows(width)
        elif self.pane.compare_mode:
            rows = self.compare_preview_rows(width)
        elif entry.zip_path is None and is_zip_archive_path(entry.path):
            rows = zip_listing_preview_rows(entry.path)
        elif entry.zip_path is not None and entry.zip_name is not None:
            if entry.is_dir:
                rows.append("[zip directory]")
            else:
                rows.extend(zip_preview_lines(entry.zip_path, entry.zip_name, self.pane.preview_numbers, width, EDITOR_STATE.wrap))
        elif entry.is_dir:
            if self.is_thuru_preview_blocked(entry):
                rows.append("[directory preview]")
                rows.append("y:get list")
            else:
                rows.append("[directory preview]")
                for child in directory_preview_children(entry.path, max(0, height - 1)):
                    rows.append(("[D] " if child.is_dir() else "    ") + child.name)
        else:
            if entry.search_line is not None:
                rows.extend(file_preview_lines_around(entry.path, entry.search_line, self.pane.preview_numbers, width, EDITOR_STATE.wrap, height + self.pane.preview_top, entry.search_match, self.config.colors["search_match_color"], syntax_for_path(entry.path)))
            else:
                rows.extend(file_preview_lines(entry.path, self.pane.preview_numbers, width, EDITOR_STATE.wrap, syntax_for_path(entry.path)))
        return rows

    def jump_preview_diff(self, term: Terminal, forward: bool) -> bool:
        columns, _ = term.size()
        list_width = max(20, min(columns - 1, int(columns * self.pane.preview_ratio)))
        preview_width = max(0, columns - list_width - 1)
        rows = self.preview_source_rows(preview_width, self.current_body_height(term))
        marks = diff_row_indices(rows)
        if not marks:
            return False
        context = self.config.diff_jump_before
        current = min(len(rows), self.pane.preview_top + context)
        target = -1
        if forward:
            for idx in marks:
                if idx > current:
                    target = idx
                    break
        else:
            for idx in reversed(marks):
                if idx < current:
                    target = idx
                    break
        if target < 0:
            return False
        self.pane.preview_top = max(0, target - context)
        self.status = f"diff: {target + 1}"
        return True

    def adjust_preview_width(self, delta: float) -> None:
        self.pane.preview_ratio = min(0.8, max(0.3, self.pane.preview_ratio + delta))
        self.status = f"preview width: {int(self.pane.preview_ratio * 100)}%"

    def filer_pane_size_mode(self, term: Terminal) -> None:
        self.status = "pane size: Left/Right pane  Up/Down log  Enter/F7 ok"
        while True:
            self.draw(term)
            key = read_key()
            if key in (KEY_ENTER, KEY_F7, KEY_ESCAPE):
                self.status = "pane size fixed"
                save_stat(self.filer_stat())
                return
            if key == KEY_UP:
                _, lines = term.size()
                self.log_height = min(filer_max_log_height(lines), self.log_height + 1)
                max_top = max(0, len(self.log_lines) - self.current_log_scroll_height(term))
                self.log_top = max_top if self.log_follow_bottom else min(self.log_top, max_top)
                self.status = f"log height: {self.current_log_height(term)}"
                continue
            if key == KEY_DOWN:
                self.log_height = max(1, self.log_height - 1)
                max_top = max(0, len(self.log_lines) - self.current_log_scroll_height(term))
                self.log_top = max_top if self.log_follow_bottom else min(self.log_top, max_top)
                self.status = f"log height: {self.current_log_height(term)}"
                continue
            if self.mode == "preview":
                if key == KEY_LEFT:
                    self.adjust_preview_width(-0.04)
                elif key == KEY_RIGHT:
                    self.adjust_preview_width(0.04)
            else:
                if key == KEY_LEFT:
                    self.dual_ratio = min(0.8, max(0.2, self.dual_ratio - 0.04))
                    self.status = f"pane size: {int(self.dual_ratio * 100)}%"
                elif key == KEY_RIGHT:
                    self.dual_ratio = min(0.8, max(0.2, self.dual_ratio + 0.04))
                    self.status = f"pane size: {int(self.dual_ratio * 100)}%"

    def toggle_preview_wrap(self) -> None:
        EDITOR_STATE.wrap = not EDITOR_STATE.wrap
        save_stat()
        self.status = "preview wrap: on" if EDITOR_STATE.wrap else "preview wrap: off"

    def toggle_preview_numbers(self) -> None:
        self.pane.preview_numbers = not self.pane.preview_numbers
        self.status = f"line number: {'on' if self.pane.preview_numbers else 'off'}"

    def page_step(self, term: Terminal) -> int:
        return self.current_body_height(term)

    def open_selected(self, term: Terminal) -> None:
        if self.pane.git_tree_mode:
            self.git_tree_commit_files_selected()
            return
        if self.pane.git_commit_files_mode:
            self.status = "preview"
            return
        if self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.compare_mode:
            self.status = "preview"
            return
        entry = self.selected()
        if entry is None:
            return
        if is_owner_entry(entry):
            self.go_parent(term)
            return
        if entry.zip_path is not None and entry.is_dir:
            self.pane.zip_dir = entry.zip_name or ""
            self.cursor = 0
            self.top = 0
            self.clear_marks()
            self.refresh()
        elif entry.is_dir:
            target = entry.path.resolve()
            if not self.can_enter_dir(target):
                return
            if is_thuru_path(target, self.config.thurupaths):
                if not self.confirm_thuru_list(term):
                    return
                if not self.is_thuru_allowed(self.pane, target):
                    self.pane.thuru_list_path = target
            elif not self.is_thuru_allowed(self.pane, target):
                self.pane.thuru_list_path = None
            self.cwd = target
            self.cursor = 0
            self.top = 0
            self.pane.zip_path = None
            self.pane.zip_dir = ""
            self.pane.search_mode = False
            self.pane.search_pattern = ""
            self.pane.search_kind = "content"
            self.pane.git_history_mode = False
            self.pane.git_history_file = None
            self.pane.git_status_mode = False
            self.pane.git_tree_mode = False
            self.pane.git_commit_files_mode = False
            self.pane.git_commit_hash = ""
            self.pane.git_commit_parent = ""
            self.pane.duplex_mode = False
            self.pane.duplex_root = None
            self.pane.thuru_return_path = None
            self.clear_marks()
            self.refresh()
            self.push_dir_history()
        elif entry.zip_path is not None:
            self.view_entry(term, entry)
        elif is_zip_archive_path(entry.path):
            self.pane.zip_path = entry.path
            self.pane.zip_dir = ""
            self.pane.search_mode = False
            self.pane.search_pattern = ""
            self.pane.search_kind = "content"
            self.pane.git_history_mode = False
            self.pane.git_history_file = None
            self.pane.git_status_mode = False
            self.pane.git_tree_mode = False
            self.pane.git_commit_files_mode = False
            self.pane.git_commit_hash = ""
            self.pane.git_commit_parent = ""
            self.pane.duplex_mode = False
            self.pane.duplex_root = None
            self.cursor = 0
            self.top = 0
            self.clear_marks()
            self.refresh()
        else:
            self.exec_selected_by_ext(term, entry)

    def open_path_os(self, path: Path) -> None:
        try:
            if IS_WINDOWS:
                os.startfile(str(path))
            else:
                subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            self.fail_status(f"os open failed: {exc}")
            return
        self.status = f"os open: {path.name}"

    def open_selected_os(self) -> None:
        entry = self.selected()
        if entry is None or is_owner_entry(entry):
            self.status = "os open: no file"
            return
        if entry.zip_path is not None:
            self.status = "archive内ファイルのos openは未対応です"
            return
        self.open_path_os(entry.path)

    def go_parent(self, term: Terminal | None = None) -> None:
        if self.pane.zip_path is not None:
            if self.pane.zip_dir:
                self.pane.zip_dir = parent_zip_dir(self.pane.zip_dir)
                self.cursor = 0
                self.top = 0
                self.clear_marks()
                self.refresh()
                return
            zip_path = self.pane.zip_path
            self.pane.zip_path = None
            self.pane.zip_dir = ""
            self.cwd = zip_path.parent
            self.pane.search_mode = False
            self.pane.search_pattern = ""
            self.pane.search_kind = "content"
            self.pane.git_history_mode = False
            self.pane.git_history_file = None
            self.pane.git_status_mode = False
            self.pane.git_tree_mode = False
            self.pane.git_commit_files_mode = False
            self.pane.git_commit_hash = ""
            self.pane.git_commit_parent = ""
            self.pane.duplex_mode = False
            self.pane.duplex_root = None
            self.clear_marks()
            self.refresh()
            self.push_dir_history()
            for index, entry in enumerate(self.entries):
                if entry.path == zip_path:
                    self.cursor = index
                    break
            return
        parent = self.cwd.parent
        if parent == self.cwd:
            return
        if not self.can_enter_dir(parent):
            return
        old = self.cwd
        if is_thuru_path(parent, self.config.thurupaths):
            if term is None or self.confirm_key(term, "get list? (N/y)"):
                self.pane.thuru_list_path = parent
            else:
                self.pane.thuru_list_path = None
        self.cwd = parent
        self.pane.thuru_return_path = None
        if not is_thuru_path(parent, self.config.thurupaths) and not self.is_thuru_allowed(self.pane, parent):
            self.pane.thuru_list_path = None
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.pane.git_status_mode = False
        self.pane.git_tree_mode = False
        self.pane.git_commit_files_mode = False
        self.pane.git_commit_hash = ""
        self.pane.git_commit_parent = ""
        self.pane.duplex_mode = False
        self.pane.duplex_root = None
        self.clear_marks()
        self.refresh()
        self.push_dir_history()
        for index, entry in enumerate(self.entries):
            if entry.path == old:
                self.cursor = index
                break

    def go_root(self) -> None:
        base = self.pane.zip_path.parent if self.pane.zip_path is not None else self.cwd
        root = Path(base.anchor) if IS_WINDOWS and base.anchor else Path("/")
        if not self.can_enter_dir(root):
            return
        self.cwd = root
        self.pane.zip_path = None
        self.pane.zip_dir = ""
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.pane.git_status_mode = False
        self.pane.git_tree_mode = False
        self.pane.git_commit_files_mode = False
        self.pane.git_commit_hash = ""
        self.pane.git_commit_parent = ""
        self.pane.duplex_mode = False
        self.pane.duplex_root = None
        self.pane.thuru_return_path = None
        self.pane.thuru_list_path = None
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.push_dir_history()
        self.status = f"root: {root}"

    def edit_selected(self, term: Terminal) -> None:
        if self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.git_commit_files_mode or self.pane.compare_mode:
            self.status = "edit unavailable"
            return
        entry = self.selected()
        if entry is None:
            return
        if entry.zip_path is not None:
            self.status = "archive内ファイルのeditは未対応です"
            return
        self.edit_file(term, entry.path, entry.search_line)

    def edit_file(self, term: Terminal, path: Path, line: int | None = None) -> None:
        if self.return_editor_requests:
            self.editor_request = (path, False, line)
            return
        saved = text_editor(term, path, False, self.config.colors, start_line=line)
        self.status = "saved" if saved else "edit canceled"
        self.refresh_all()

    def directory_selected(self, term: Terminal) -> None:
        items = system_directory_items() + self.config.directories
        index = self.select_command_item(term, items, full_height=True)
        if index is None:
            self.status = "directory canceled"
            return
        path = Path(items[index].command).expanduser()
        if not path.is_absolute():
            path = self.cwd / path
        if not path.is_dir():
            self.status = f"not directory: {path}"
            return
        path = path.resolve()
        if not self.can_enter_dir(path):
            return
        self.cwd = path
        self.pane.zip_path = None
        self.pane.zip_dir = ""
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.pane.git_status_mode = False
        self.pane.git_tree_mode = False
        self.pane.git_commit_files_mode = False
        self.pane.git_commit_hash = ""
        self.pane.git_commit_parent = ""
        self.pane.thuru_return_path = None
        self.pane.thuru_list_path = None
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.push_dir_history()
        self.status = f"jumped: {path}"

    def bookmark_add(self, term: Terminal) -> None:
        title = self.prompt(term, "bookmark title", self.cwd.name or str(self.cwd))
        if not title:
            self.status = "bookmark canceled"
            return
        bookmarks = EDITOR_STATE.bookmarks or []
        path = str(self.cwd)
        for item in bookmarks:
            if item.command == path:
                item.title = title
                break
        else:
            bookmarks.append(CommandItem(title, path))
        EDITOR_STATE.bookmarks = bookmarks
        self.status = f"bookmark added: {title}" if save_stat(self.filer_stat()) else "bookmark save failed"

    def bookmark_selected(self, term: Terminal) -> None:
        bookmarks = EDITOR_STATE.bookmarks or []
        if not bookmarks:
            self.status = "bookmark empty"
            return
        index = self.select_bookmark_item(term, bookmarks)
        if index is None:
            self.status = "bookmark canceled"
            return
        path = Path(bookmarks[index].command).expanduser()
        if not path.is_dir():
            self.status = f"bookmark not found: {path}"
            return
        path = path.resolve()
        if not self.can_enter_dir(path):
            return
        self.cwd = path
        self.pane.zip_path = None
        self.pane.zip_dir = ""
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.pane.git_status_mode = False
        self.pane.git_tree_mode = False
        self.pane.git_commit_files_mode = False
        self.pane.git_commit_hash = ""
        self.pane.git_commit_parent = ""
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.push_dir_history()
        self.status = f"bookmark: {bookmarks[index].title}"

    def select_bookmark_item(self, term: Terminal, bookmarks: list[CommandItem]) -> int | None:
        cursor = 0
        top = 0
        while True:
            if not bookmarks:
                return None
            columns, lines = term.size()
            height = min(len(bookmarks), max(1, min(10, lines - 6)))
            width = min(max(30, max(display_width(item.title) for item in bookmarks) + 8), max(30, columns - 4))
            popup_height = height + 3
            start_row, start_col = self.popup_origin(columns, lines, width, popup_height)
            if cursor < top:
                top = cursor
            elif cursor >= top + height:
                top = cursor - height + 1
            self.draw(term)
            self.draw_popup_border(term, start_row, start_col, width, popup_height)
            for row in range(height):
                index = top + row
                item = bookmarks[index]
                line = fit(f"> {item.title}" if index == cursor else f"  {item.title}", width - 2)
                term.move(start_row + 1 + row, start_col + 1)
                term.write(reverse(line) if index == cursor else line)
            term.move(start_row + popup_height - 1, start_col + 1)
            term.write(yellow_bg(fit(" Enter:OK  DEL:Delete  r:Rename ", width - 2)))
            term.flush()
            key = read_key()
            if key == KEY_ENTER:
                return cursor
            if key in (KEY_ESCAPE, KEY_BACKSPACE, "q", "Q"):
                return None
            if key in (KEY_UP, "k", "K"):
                cursor = max(0, cursor - 1)
            elif key in (KEY_DOWN, "j", "J"):
                cursor = min(len(bookmarks) - 1, cursor + 1)
            elif key == KEY_DELETE:
                del bookmarks[cursor]
                cursor = min(cursor, max(0, len(bookmarks) - 1))
                if not save_stat(self.filer_stat()):
                    self.status = "bookmark save failed"
            elif key in ("r", "R"):
                title = self.prompt(term, "bookmark title", bookmarks[cursor].title)
                if title:
                    bookmarks[cursor].title = title
                    if not save_stat(self.filer_stat()):
                        self.status = "bookmark save failed"

    def launcher_selected(self, term: Terminal) -> None:
        entry = self.selected()
        items = list(self.config.launchers)
        items.append(CommandItem("Setting Tool", "__setting_tool__"))
        items.append(CommandItem("Full Screen Shell", "__full_shell__"))
        items.append(CommandItem("Run...", "__run__"))
        entries = self.selected_entries()
        if entries:
            items.append(CommandItem(f"Archive {entries[0].name}", "__archive_selected__"))
            items.append(CommandItem(f"Archive DateTime {entries[0].name}", "__archive_datetime__"))
        items.append(CommandItem("New Text File...", "__new_text__"))
        items.append(CommandItem("New Archive...", "__new_archive__"))
        if entry is not None and is_zip_archive_path(entry.path) and entry.zip_path is None:
            items.append(CommandItem("Extract", "__extract_zip__"))
        index = self.select_command_item(term, items)
        if index is None:
            self.status = "launcher canceled"
            return
        command = items[index].command
        if command == "__setting_tool__":
            self.run_setting_tool(term)
            return
        if command == "__full_shell__":
            self.full_screen_shell(term)
            return
        if command == "__run__":
            self.run_shell(term, entry)
            return
        if command == "__archive_selected__":
            self.archive_selected(term, entries)
            return
        if command == "__archive_datetime__":
            self.archive_selected_datetime(term, entries)
            return
        if command == "__new_text__":
            self.new_text_file(term)
            return
        if command == "__new_archive__":
            self.new_archive(term)
            return
        if command == "__extract_zip__":
            self.extract_selected_zip(entry)
            return
        path = entry.path if entry is not None else None
        self.confirm_and_run_command(term, command, path, items[index].charset, items[index].screen)

    def add_run_history(self, command: str) -> None:
        if command and command not in EDITOR_STATE.run_history:
            EDITOR_STATE.run_history.append(command)
            save_run_history(EDITOR_STATE.run_history)
        self.log_history_index = len(EDITOR_STATE.run_history)

    def run_setting_tool(self, term: Terminal) -> None:
        tool = Path(__file__).resolve().with_name("vfiler_setting.py")
        if not tool.exists():
            self.status = "setting tool not found"
            return
        config_path = find_config(Path.cwd()) or Path(__file__).resolve().with_name(platform_config_name())
        command = f"{quote_path(Path(sys.executable))} {quote_path(tool)} {quote_path(config_path)}"
        returncode = self.spawn_external_fullscreen(term, command)
        self.reload_def()
        if returncode not in (0, None):
            self.status = f"setting tool failed: {returncode}"

    def run_shell(self, term: Terminal, entry: Entry | None) -> None:
        default = self.run_shell_default(entry)
        command = self.prompt_history(term, "run", default)
        if not command:
            self.status = "run canceled"
            return
        self.add_run_history(command)
        command = expand_prompt_vars(command)
        returncode = self.spawn_external(term, command)
        self.status = self.command_result_status(returncode)
        self.refresh_all()

    def run_shell_default(self, entry: Entry | None) -> str:
        entries = self.run_shell_entries(entry)
        return " ".join(quote_path(item.path) for item in entries)

    def run_shell_entries(self, entry: Entry | None) -> list[Entry]:
        result = self.marked_entries()
        if not result and entry is not None:
            result = [entry]
        if self.mode == "dual":
            other = self.panes[1 - self.active_pane]
            result.extend(self.marked_entries_for_pane(other))
        return result

    def marked_entries_for_pane(self, pane: PaneState) -> list[Entry]:
        marks = pane.marks or set()
        if not marks:
            return []
        return [entry for entry in pane.entries if entry_key(entry) in marks]

    def full_screen_shell(self, term: Terminal) -> None:
        command = self.full_screen_shell_command()
        if not command:
            self.status = "shell not found"
            return
        cwd = self.cwd
        term.clear()
        term.leave_app_mode()
        try:
            print(f"vfiler shell: {cwd}")
            try:
                subprocess.run(command, cwd=str(cwd))
            except OSError as exc:
                print(f"failed to start shell: {exc}")
                input("Enter:back")
        finally:
            term.enter_app_mode()
            term.clear()
        self.status = "shell closed"
        self.refresh_all()

    def full_screen_shell_command(self) -> list[str]:
        shell = self.config.shell.strip()
        if shell:
            try:
                command = shlex.split(shell, posix=not IS_WINDOWS)
            except ValueError:
                command = [shell]
        elif IS_WINDOWS:
            command = [os.environ.get("COMSPEC") or "cmd.exe"]
        else:
            command = [os.environ.get("SHELL") or "/bin/sh"]
        if not command:
            return []
        executable = command[0]
        path = Path(executable).expanduser()
        if path.is_absolute():
            return command if path.exists() else []
        found = shutil.which(executable)
        if found is None:
            return []
        command[0] = found
        return command

    def new_text_file(self, term: Terminal) -> None:
        text = self.prompt(term, "text file", str(self.cwd / "new.txt"))
        if not text:
            self.status = "new text canceled"
            return
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = self.cwd / path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=False)
            self.status = f"created: {path.name}"
            self.refresh_all()
            self.focus_path_in_pane(self.active_pane, path)
        except OSError as exc:
            self.fail_status(f"new text failed: {exc}")

    def git_selected(self, term: Terminal) -> None:
        if self.pane.zip_path is not None:
            self.status = "git repositoryではありません"
            return
        items = self.git_menu_items()
        index = self.select_command_item(term, items)
        if index is None:
            self.status = "git canceled"
            return
        command = items[index].command
        if command == "__git_init__":
            self.git_initialize(term)
            return
        if command == "__git_add__":
            self.git_add_selected(term)
            return
        if command == "__git_add_ignore__":
            self.git_add_ignore_selected()
            return
        if command == "__git_history__":
            self.git_history_selected()
            return
        if command == "__git_status__":
            self.git_status_selected()
            return
        if command == "__git_unmanaged__":
            self.git_unmanaged_selected()
            return
        if command == "__git_managed__":
            self.git_managed_selected()
            return
        if command == "__git_unmanage__":
            self.git_unmanage_selected(term)
            return
        if command == "__git_discard__":
            self.git_discard_selected(term)
            return
        if command == "__git_tree__":
            self.git_tree_selected()
            return
        if command == "__git_tree_checkout__":
            self.git_tree_checkout(term)
            return
        if command == "__git_tree_scope__":
            self.git_tree_scope_selected(term)
            return
        if command == "__git_branch_list__":
            self.git_branch_list(term)
            return
        if command == "__git_new_branch__":
            self.git_new_branch(term)
            return
        if command == "__git_merge_branch__":
            self.git_merge_branch(term)
            return
        if command == "__git_commit_checkout__":
            self.git_commit_file_checkout(term)
            return
        if command == "__git_commit_copy__":
            self.git_commit_file_copy(term)
            return
        if command == "__git_commit__":
            self.git_commit(term)
            return
        if command == "__git_show__":
            self.confirm_and_run_git(term, "git show")
            return
        if command == "__git_push__":
            self.confirm_and_run_git(term, "git push")
            return
        if command == "__git_pull__":
            self.confirm_and_run_git(term, "git pull")
            return
        self.confirm_and_run_command(term, command, None)

    def git_add_target_available(self) -> bool:
        if self.pane.git_history_mode or self.pane.git_tree_mode or self.pane.git_commit_files_mode or self.pane.compare_mode:
            return False
        if self.pane.git_status_mode and self.pane.git_status_kind == "managed":
            return False
        return any(entry.zip_path is None for entry in self.selected_entries())

    def git_ignore_targets(self) -> list[Entry]:
        if self.is_temporary_view():
            return []
        return [entry for entry in self.selected_entries() if entry.zip_path is None and entry.path.parent == self.cwd]

    def git_add_ignore_selected(self) -> None:
        target = self.cwd / ".gitignore"
        entries = self.git_ignore_targets()
        if self.pane.zip_path is not None or not target.is_file() or not entries:
            self.status = "add ignore unavailable"
            return
        try:
            original = target.read_bytes()
            newline = b"\r\n" if b"\r\n" in original else b"\n"
            existing = set(original.splitlines())
            patterns = []
            for entry in entries:
                name = re.sub(r"([\\*?\[ ])", r"\\\1", entry.path.name)
                pattern = ("/" + name + ("/" if entry.is_dir else "")).encode("utf-8")
                if pattern not in existing:
                    patterns.append(pattern)
                    existing.add(pattern)
            if not patterns:
                self.status = "add ignore: already listed"
                return
            with target.open("ab") as stream:
                if original and not original.endswith((b"\n", b"\r")):
                    stream.write(newline)
                stream.write(newline.join(patterns) + newline)
        except OSError as exc:
            self.fail_status(f"add ignore failed: {exc}")
            return
        self.status = f"add ignore: {len(patterns)} item(s)"
        self.clear_marks()
        self.refresh_all()

    def git_unmanage_target_available(self) -> bool:
        return self.pane.git_status_mode and self.pane.git_status_kind == "managed" and any(entry.zip_path is None for entry in self.selected_entries())

    def git_discard_target_available(self) -> bool:
        return self.pane.git_status_mode and any(entry.zip_path is None for entry in self.selected_entries())

    def git_initialize(self, term: Terminal) -> None:
        if self.pane.zip_path is not None:
            self.status = "git init unavailable"
            return
        if git_root(self.cwd) is not None:
            self.status = "git repository already exists"
            return
        template = self.select_gitignore_template(term)
        if template is None:
            self.status = "git init canceled"
            return
        self.spawn_external(term, "git init")
        clear_git_cache()
        ignore_status = self.create_gitignore_from_template(term, template)
        self.status = "git initialized" + (f"; {ignore_status}" if ignore_status else "")
        self.refresh_all()

    def select_gitignore_template(self, term: Terminal) -> str | None:
        items = [CommandItem(name, name, name != "none" and not gitignore_template_path(name).is_file()) for name in GITIGNORE_TEMPLATE_NAMES]
        index = self.select_command_item(term, items)
        return None if index is None else items[index].command

    def create_gitignore_from_template(self, term: Terminal, template: str) -> str:
        if template == "none":
            return "no .gitignore"
        source = gitignore_template_path(template)
        if not source.is_file():
            return f"{template}.gitignore not found"
        target = self.cwd / ".gitignore"
        if target.exists() and not self.confirm_key(term, "overwrite .gitignore? y/N"):
            return ".gitignore skipped"
        try:
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            return f".gitignore: {template}"
        except OSError as exc:
            return f".gitignore failed: {exc}"

    def git_add_selected(self, term: Terminal) -> None:
        root = git_root(self.cwd)
        if root is None:
            self.status = "git repositoryではありません"
            return
        entries = [entry for entry in self.selected_entries() if entry.zip_path is None]
        command, count = git_add_command(root, entries)
        if not command:
            self.status = "git add: no file"
            return
        self.spawn_external(term, command)
        self.status = f"git add: {count} item(s)"
        for entry in entries:
            self.append_log(f"GIT ADD {entry_display_path(entry)} (success)")
        self.clear_marks()
        self.refresh_all()

    def git_unmanage_selected(self, term: Terminal) -> None:
        root = git_root(self.cwd)
        if root is None:
            self.status = "git repositoryではありません"
            return
        entries = [entry for entry in self.selected_entries() if entry.zip_path is None]
        command, count = git_unmanage_command(root, entries)
        if not command:
            self.status = "unmanage: no file"
            return
        if not self.confirm_key(term, f"unmanage {count} file(s)? y/N"):
            self.status = "unmanage canceled"
            return
        self.spawn_external(term, command)
        self.status = f"unmanaged: {count} file(s)"
        for entry in entries:
            self.append_log(f"UNMANAGE {entry_display_path(entry)} (success)")
        self.clear_marks()
        self.refresh_all()

    def git_discard_selected(self, term: Terminal) -> None:
        root = git_root(self.cwd)
        if root is None:
            self.status = "git repositoryではありません"
            return
        if not self.pane.git_status_mode:
            self.status = "discard: status only"
            return
        entries = [entry for entry in self.selected_entries() if entry.zip_path is None]
        command, count, untracked = git_discard_plan(root, entries)
        if count == 0:
            self.status = "discard: no change"
            return
        if not self.confirm_key(term, f"discard changes {count} item(s)? y/N"):
            self.status = "discard canceled"
            return
        if command:
            returncode = self.spawn_external(term, command)
            if returncode != 0:
                self.status = self.command_result_status(returncode)
                self.refresh_all()
                return
        try:
            for path in untracked:
                if path.exists():
                    remove_file_target(path)
                    self.append_log(f"GIT DISCARD {path} (deleted)")
        except OSError as exc:
            self.fail_status(f"discard failed: {exc}")
            self.refresh_all()
            return
        clear_git_cache()
        self.status = f"discarded: {count} item(s)"
        self.append_log(self.status)
        self.clear_marks()
        self.refresh_all()

    def git_history_selected(self) -> None:
        entry = self.selected()
        if entry is None or entry.is_dir or entry.zip_path is not None:
            self.status = "history: file only"
            return
        if git_root(self.cwd) is None:
            self.status = "git repositoryではありません"
            return
        self.enter_git_preview_view()
        self.pane.git_history_mode = True
        self.pane.git_history_file = entry.path
        self.pane.git_status_mode = False
        self.pane.git_tree_mode = False
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"history: {entry.name}  {len(self.entries)} commit(s)"

    def git_status_selected(self) -> None:
        self.git_status_view_selected("all")

    def git_unmanaged_selected(self) -> None:
        self.git_status_view_selected("unmanaged")

    def git_managed_selected(self) -> None:
        self.git_status_view_selected("managed")

    def git_status_view_selected(self, kind: str) -> None:
        if git_root(self.cwd) is None:
            self.status = "git repositoryではありません"
            return
        self.enter_git_preview_view()
        self.pane.git_status_mode = True
        self.pane.git_status_kind = kind
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.pane.git_tree_mode = False
        self.pane.git_commit_files_mode = False
        self.pane.git_commit_hash = ""
        self.pane.git_commit_parent = ""
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        label = {"managed": "managed", "unmanaged": "unmanaged"}.get(kind, "status")
        self.status = f"{label}: {len(self.entries)} file(s)"

    def git_tree_selected(self) -> None:
        if git_root(self.cwd) is None:
            self.status = "git repositoryではありません"
            return
        self.enter_git_preview_view()
        self.pane.git_tree_mode = True
        self.pane.git_status_mode = False
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.pane.git_commit_files_mode = False
        self.pane.git_commit_hash = ""
        self.pane.git_commit_parent = ""
        self.pane.git_tree_preview_commit = ""
        self.pane.git_tree_detail_commit = ""
        self.pane.git_tree_preview_time = 0.0
        self.pane.search_mode = False
        self.pane.search_pattern = ""
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.sync_git_tree_preview_state()
        self.status = f"tree: {len(self.entries)} commit(s)"

    def git_tree_commit_files_selected(self) -> None:
        entry = self.selected()
        if entry is None or not entry.search_text:
            self.status = "commit unavailable"
            return
        self.pane.git_commit_files_mode = True
        self.pane.git_commit_hash = entry.search_text
        self.pane.git_commit_parent = git_first_parent(self.cwd, entry.search_text)
        self.pane.git_tree_mode = False
        self.pane.git_status_mode = False
        self.pane.git_history_mode = False
        self.pane.git_history_file = None
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"commit files: {entry.search_match or entry.search_text[:7]}  {len(self.entries)} file(s)"

    def git_commit(self, term: Terminal) -> None:
        message = self.prompt(term, "commit message", "")
        if not message:
            self.status = "commit canceled"
            return
        self.spawn_external(term, "git commit -a -m " + quote_path(message))
        self.status = "command finished"
        self.refresh_all()

    def git_tree_checkout(self, term: Terminal) -> None:
        entry = self.selected()
        commit = entry.search_text if entry is not None else ""
        root = git_root(self.cwd)
        if root is None or not self.pane.git_tree_mode or not commit:
            self.status = "checkout unavailable"
            return
        label = entry.search_match or commit[:7]
        if not self.confirm_key(term, f"checkout commit {label}? detached HEAD y/N"):
            self.status = "checkout canceled"
            return
        self.spawn_external(term, "git checkout " + quote_path(commit))
        self.status = f"checked out: {label}"
        self.refresh_all()

    def git_branch_list(self, term: Terminal) -> None:
        root = git_root(self.cwd)
        if root is None:
            self.status = "git repositoryではありません"
            return
        items = list_git_branch_items(root)
        if not items:
            self.status = "branch empty"
            return
        index = self.select_command_item(term, items)
        if index is None:
            self.status = "branch canceled"
            return
        command = items[index].command
        title = items[index].title.strip()
        if not command:
            self.status = "branch unavailable"
            return
        if not self.confirm_key(term, f"checkout {title.lstrip('* ')}? y/N"):
            self.status = "branch checkout canceled"
            return
        self.spawn_external(term, command)
        self.status = f"branch checkout: {title.lstrip('* ')}"
        self.refresh_all()

    def git_new_branch(self, term: Terminal) -> None:
        root = git_root(self.cwd)
        if root is None:
            self.status = "git repositoryではありません"
            return
        name = self.prompt(term, "new branch", "")
        if not name:
            self.status = "branch canceled"
            return
        base = ""
        if self.pane.git_tree_mode:
            entry = self.selected()
            base = entry.search_text if entry is not None else ""
        command = "git checkout -b " + quote_path(name) + ((" " + quote_path(base)) if base else "")
        if not self.confirm_key(term, f"create branch {name}? y/N"):
            self.status = "branch canceled"
            return
        self.spawn_external(term, command)
        self.status = f"branch created: {name}"
        self.refresh_all()

    def git_merge_branch(self, term: Terminal) -> None:
        root = git_root(self.cwd)
        if root is None:
            self.status = "git repositoryではありません"
            return
        items = list_git_branch_items(root, merge_mode=True)
        if not items:
            self.status = "branch empty"
            return
        index = self.select_command_item(term, items)
        if index is None:
            self.status = "merge canceled"
            return
        command = items[index].command
        title = items[index].title.strip()
        if not command:
            self.status = "merge unavailable"
            return
        if not self.confirm_key(term, f"merge {title.lstrip('* ')}? y/N"):
            self.status = "merge canceled"
            return
        self.spawn_external(term, command)
        self.status = f"merged: {title.lstrip('* ')}"
        self.refresh_all()

    def git_tree_scope_selected(self, term: Terminal) -> None:
        items = [
            CommandItem("Local", "local", self.pane.git_tree_scope == "local"),
            CommandItem("Remote", "remote", self.pane.git_tree_scope == "remote"),
            CommandItem("All", "all", self.pane.git_tree_scope == "all"),
        ]
        index = self.select_command_item(term, items)
        if index is None:
            self.status = "tree scope canceled"
            return
        self.pane.git_tree_scope = items[index].command
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"tree scope: {self.pane.git_tree_scope}  {len(self.entries)} commit(s)"

    def git_commit_file_checkout(self, term: Terminal) -> None:
        entry = self.selected()
        root = git_root(self.cwd)
        if entry is None or root is None or not self.pane.git_commit_files_mode:
            self.status = "checkout unavailable"
            return
        rel = git_rel_path(root, entry.path)
        if not self.confirm_key(term, f"checkout {rel}? y/N"):
            self.status = "checkout canceled"
            return
        try:
            result = subprocess.run(["git", "-C", str(root), "checkout", self.pane.git_commit_hash, "--", rel], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace", check=False)
        except OSError as exc:
            self.fail_status(f"checkout failed: {exc}")
            return
        if result.returncode == 0:
            self.status = "checkout done"
        else:
            self.fail_status(f"checkout failed: {result.stderr.strip()}")
        self.refresh_all()

    def git_commit_file_copy(self, term: Terminal) -> None:
        entry = self.selected()
        if entry is None or not self.pane.git_commit_files_mode:
            self.status = "copy unavailable"
            return
        data = git_blob_bytes_for_path(self.cwd, self.pane.git_commit_hash, entry.path)
        if data is None:
            self.fail_status("copy failed")
            return
        dst_text = self.prompt(term, "copy to", str(self.cwd / entry.path.name))
        if not dst_text:
            self.status = "copy canceled"
            return
        dst = Path(dst_text).expanduser()
        if not dst.is_absolute():
            dst = self.cwd / dst
        try:
            if dst.exists():
                if self.confirm_overwrite_action(term, dst) != "yes":
                    self.status = "copy canceled"
                    return
                remove_file_target(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        except OSError as exc:
            self.fail_status(f"copy failed: {exc}")
            return
        self.status = f"copied: {dst}"
        self.refresh_all()

    def sort_selected(self, term: Terminal) -> None:
        items = [
            CommandItem("Name ascending", "name:0"),
            CommandItem("Name descending", "name:1"),
            CommandItem("Natural name ascending", "natural:0"),
            CommandItem("Natural name descending", "natural:1"),
            CommandItem("Ext ascending", "ext:0"),
            CommandItem("Ext descending", "ext:1"),
            CommandItem("Size ascending", "size:0"),
            CommandItem("Size descending", "size:1"),
            CommandItem("Time ascending", "mtime:0"),
            CommandItem("Time descending", "mtime:1"),
        ]
        index = self.select_command_item(term, items)
        if index is None:
            self.status = "sort canceled"
            return
        key, reverse = items[index].command.split(":", 1)
        self.pane.sort_key = key
        self.pane.sort_reverse = reverse == "1"
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"sort: {key} {'desc' if self.pane.sort_reverse else 'asc'}"

    def extract_selected_zip(self, entry: Entry | None) -> None:
        if entry is None:
            return
        dst = self.other_cwd_for_file_ops()
        try:
            extract_zip(entry.path, dst)
            self.status = f"extracted: {entry.name} -> {dst}"
            self.clear_marks()
            self.refresh_all()
        except ARCHIVE_READ_ERRORS as exc:
            self.fail_status(f"extract failed: {exc}")

    def archive_selected(self, term: Terminal, entries: list[Entry]) -> None:
        if not entries:
            return
        default = self.default_archive_path(entries[0])
        text = self.prompt(term, "archive", str(default))
        if not text:
            self.status = "archive canceled"
            return
        text = expand_prompt_vars(text)
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = default.parent / path
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")
        try:
            create_empty_zip(path)
            add_entries_to_zip(path, entries, "")
            self.status = f"archived: {len(entries)} item(s) -> {path.name}"
            self.clear_marks()
            self.refresh_all()
            self.focus_path_in_pane(1 - self.active_pane if self.mode == "dual" else self.active_pane, path)
        except (OSError, zipfile.BadZipFile) as exc:
            self.fail_status(f"archive failed: {exc}")

    def archive_selected_datetime(self, term: Terminal, entries: list[Entry]) -> None:
        if not entries:
            return
        default = self.default_datetime_archive_path(entries[0])
        text = self.prompt(term, "archive", str(default))
        if not text:
            self.status = "archive canceled"
            return
        text = expand_prompt_vars(text)
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = default.parent / path
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")
        try:
            create_empty_zip(path)
            add_entries_to_zip(path, entries, "")
            self.status = f"archived: {len(entries)} item(s) -> {path.name}"
            self.clear_marks()
            self.refresh_all()
            self.focus_path_in_pane(1 - self.active_pane if self.mode == "dual" else self.active_pane, path)
        except (OSError, zipfile.BadZipFile) as exc:
            self.fail_status(f"archive failed: {exc}")

    def default_archive_path(self, entry: Entry) -> Path:
        if self.mode == "dual":
            other = self.panes[1 - self.active_pane]
            base = other.zip_path.parent if other.zip_path is not None else other.cwd
        else:
            base = self.pane.zip_path.parent if self.pane.zip_path is not None else self.cwd
        return base / (Path(entry.name).stem + ".zip")

    def default_datetime_archive_path(self, entry: Entry) -> Path:
        if self.mode == "dual":
            other = self.panes[1 - self.active_pane]
            base = other.zip_path.parent if other.zip_path is not None else other.cwd
        else:
            base = self.pane.zip_path.parent if self.pane.zip_path is not None else self.cwd
        stamp = expand_prompt_vars("${DATE}-${TIME}")
        return base / f"{Path(entry.name).stem}-{stamp}.zip"

    def new_archive(self, term: Terminal) -> None:
        text = self.prompt(term, "archive", str(self.default_new_archive_path()))
        if not text:
            self.status = "archive canceled"
            return
        text = expand_prompt_vars(text)
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = self.cwd / path
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")
        try:
            create_empty_zip(path)
            self.status = f"created archive: {path.name}"
            self.refresh_all()
            self.focus_path_in_pane(self.active_pane, path)
        except OSError as exc:
            self.fail_status(f"archive failed: {exc}")

    def default_new_archive_path(self) -> Path:
        return self.cwd / "new.zip"

    def focus_path_in_pane(self, pane_index: int, path: Path) -> None:
        pane = self.panes[pane_index]
        if pane.zip_path is not None:
            return
        if pane.cwd != path.parent:
            pane.cwd = path.parent
            old_active = self.active_pane
            self.active_pane = pane_index
            self.refresh()
            self.active_pane = old_active
        for index, entry in enumerate(pane.entries):
            if entry.path == path:
                pane.cursor = index
                pane.top = min(pane.top, pane.cursor)
                break

    def exec_selected_by_ext(self, term: Terminal, entry: Entry) -> None:
        if self.view_image_entry(term, entry):
            return
        ext = entry.path.suffix[1:].lower()
        item = self.config.execs.get(ext)
        if item is None:
            if is_binary_file(entry.path):
                self.open_path_os(entry.path)
                return
            self.view_file(term, entry.path, entry.search_line)
            return
        self.confirm_and_run_exec(term, item.command, entry)

    def confirm_and_run_exec(self, term: Terminal, template: str, entry: Entry) -> None:
        command = self.exec_command_default(template, entry)
        command = self.prompt(term, "command", command)
        if not command:
            self.status = "command canceled"
            return
        self.add_run_history(command)
        command = expand_prompt_vars(command)
        returncode = self.spawn_external(term, command)
        self.status = self.command_result_status(returncode)
        self.refresh_all()

    def exec_command_default(self, template: str, entry: Entry) -> str:
        current_entries = self.selected_entries()
        command = expand_command(template, entry.path, self.pane_command_path(self.pane), self.pane_command_path(self.panes[1 - self.active_pane]), current_entries)
        if "%f" not in template:
            return command
        extras: list[Entry] = []
        if self.mode == "dual":
            extras.extend(self.marked_entries_for_pane(self.panes[1 - self.active_pane]))
        if not extras:
            return command
        return command + " " + " ".join(quote_path(item.path) for item in extras)

    def preview_selected(self, term: Terminal) -> None:
        if self.pane.git_history_mode:
            self.preview_git_history_selected(term)
            return
        if self.pane.git_commit_files_mode:
            self.preview_git_commit_file_selected(term)
            return
        if self.pane.compare_mode:
            self.preview_compare_selected(term)
            return
        entry = self.selected()
        if entry is None:
            return
        if entry.is_dir:
            self.status = "ファイルを選択してください"
            return
        self.view_entry(term, entry)

    def preview_git_history_selected(self, term: Terminal) -> None:
        selected = self.marked_entries()
        if len(selected) == 2:
            newer, older = sorted(selected, key=lambda item: item.mtime, reverse=True)
            rows = git_file_diff_text_rows(self.cwd, self.pane.git_history_file, newer.search_text, older.search_text)
            name = "vfiler-history-diff.txt"
        else:
            entry = self.selected()
            if entry is None:
                return
            data = git_file_bytes(self.cwd, self.pane.git_history_file, entry.search_text)
            if data is None:
                self.fail_status("history view failed")
                return
            rows = data.decode("utf-8", errors="replace").splitlines()
            name = "vfiler-history.txt"
        path = Path(tempfile.gettempdir()) / name
        try:
            path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
        except OSError as exc:
            self.fail_status(f"history view failed: {exc}")
            return
        self.view_file(term, path)

    def preview_compare_selected(self, term: Terminal) -> None:
        entry = self.selected()
        if entry is None:
            return
        rows = strip_ansi_rows(compare_preview_rows(entry, 1000))
        path = Path(tempfile.gettempdir()) / "vfiler-compare.txt"
        try:
            path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
        except OSError as exc:
            self.fail_status(f"compare view failed: {exc}")
            return
        self.view_file(term, path)

    def view_entry(self, term: Terminal, entry: Entry) -> None:
        if self.view_image_entry(term, entry):
            return
        if entry.zip_path is not None and entry.zip_name is not None:
            self.view_zip_file(term, entry.zip_path, entry.zip_name)
        else:
            self.view_file(term, entry.path, entry.search_line)

    def view_image_entry(self, term: Terminal, entry: Entry) -> bool:
        if not is_iterm_terminal():
            return False
        if not entry_is_image(entry):
            return False
        image_entries = self.image_entries()
        try:
            index = next(index for index, item in enumerate(image_entries) if entry_key(item) == entry_key(entry))
        except StopIteration:
            index = 0
        shown = self.show_iterm_image(term, image_entries, index)
        if shown is None:
            return True
        self.status = f"image: {shown.name}"
        self.refresh_all()
        self.focus_entry_in_active_pane(shown)
        return True

    def image_entries(self) -> list[Entry]:
        return [entry for entry in self.entries if entry_is_image(entry)]

    def image_entry_data(self, entry: Entry) -> bytes:
        if entry.zip_path is not None and entry.zip_name is not None:
            return archive_read_bytes(entry.zip_path, entry.zip_name)
        return entry.path.read_bytes()

    def focus_entry_in_active_pane(self, entry: Entry) -> None:
        for index, item in enumerate(self.entries):
            if entry_key(item) == entry_key(entry):
                self.cursor = index
                if self.cursor < self.top:
                    self.top = self.cursor
                break

    def show_iterm_image(self, term: Terminal, entries: list[Entry], start_index: int) -> Entry | None:
        if not entries:
            return None
        index = min(max(0, start_index), len(entries) - 1)
        term.clear()
        term.leave_app_mode()
        try:
            while True:
                entry = entries[index]
                try:
                    data = self.image_entry_data(entry)
                except ARCHIVE_READ_ERRORS as exc:
                    self.fail_status(f"image view failed: {exc}")
                    return None
                sys.stdout.write("\x1b[2J\x1b[H")
                sys.stdout.write(iterm_image_sequence(entry.name, data))
                sys.stdout.write(f"\n\n{entry.name}  Up/Down: prev/next  d:delete  Enter/ESC/q: back")
                sys.stdout.flush()
                key = read_key_normal_mode()
                if key in (KEY_ENTER, KEY_ESCAPE, KEY_BACKSPACE, "q", "Q"):
                    return entry
                if key in ("d", "D"):
                    term.enter_app_mode()
                    term.clear()
                    try:
                        confirm = confirm_popup_key(term, f"delete {entry.name}? n/Y", hint="N/ESC:Cancel  Y:Delete")
                    finally:
                        term.leave_app_mode()
                    if confirm not in ("y", "Y"):
                        continue
                    try:
                        if entry.zip_path is not None:
                            delete_zip_entries([entry])
                        else:
                            remove_file_target(entry.path)
                    except ARCHIVE_READ_ERRORS as exc:
                        self.fail_status(f"delete failed: {exc}")
                        return None
                    self.status = f"deleted: {entry_display_path(entry)}"
                    del entries[index]
                    if not entries:
                        self.refresh_all()
                        return None
                    index = min(index, len(entries) - 1)
                    self.refresh_all()
                    continue
                if key in (KEY_UP, "k", "K"):
                    if index > 0:
                        index -= 1
                elif key in (KEY_DOWN, "j", "J"):
                    if index + 1 < len(entries):
                        index += 1
        finally:
            term.enter_app_mode()
            term.clear()

    def information_selected(self, term: Terminal) -> None:
        entries = self.selected_entries()
        if not entries:
            self.status = "no file"
            return
        sort_value = self.select_information_sort(term)
        if sort_value is None:
            self.status = "information canceled"
            return
        sort_key, reverse = sort_value
        rows = entry_information_rows(entries, sort_key, reverse)
        self.append_log(f"[Information] sort:{information_sort_title(sort_key, reverse)}")
        for row in rows:
            self.append_log(row.rstrip())
        self.status = f"information: {len(entries)} item(s)"

    def select_information_sort(self, term: Terminal) -> tuple[str, bool] | None:
        items = [
            CommandItem("File size ascending", "size:0"),
            CommandItem("File size descending", "size:1"),
            CommandItem("Created ascending", "created:0"),
            CommandItem("Created descending", "created:1"),
            CommandItem("Modified ascending", "modified:0"),
            CommandItem("Modified descending", "modified:1"),
            CommandItem("Filename ascending", "name:0"),
            CommandItem("Filename descending", "name:1"),
        ]
        index = self.select_command_item(term, items)
        if index is None:
            return None
        key, reverse = items[index].command.split(":", 1)
        return key, reverse == "1"

    def confirm_and_run_command(self, term: Terminal, template: str, path: Path | None, charset: str = "", screen: str = "") -> None:
        command = expand_command(template, path, self.pane_command_path(self.pane), self.pane_command_path(self.panes[1 - self.active_pane]), self.selected_entries())
        command = self.prompt(term, "command", command)
        if not command:
            self.status = "command canceled"
            return
        self.add_run_history(command)
        command = expand_prompt_vars(command)
        if screen.strip().lower() == "fullscreen":
            returncode = self.spawn_external_fullscreen(term, command, charset)
        else:
            returncode = self.spawn_external(term, command, charset)
        self.status = self.command_result_status(returncode)
        self.refresh_all()

    def pane_command_path(self, pane: PaneState) -> str:
        if pane.zip_path is None:
            return str(pane.cwd)
        suffix = ("/" + pane.zip_dir) if pane.zip_dir else ""
        return f"{pane.zip_path}{suffix}"

    def other_cwd_for_file_ops(self) -> Path:
        other = self.panes[1 - self.active_pane]
        if other.zip_path is not None:
            return other.zip_path.parent
        return other.cwd

    def select_command_item(self, term: Terminal, items: list[CommandItem], full_height: bool = False) -> int | None:
        if not items:
            return None
        cursor = first_enabled_command(items)
        top = 0
        while True:
            columns, lines = term.size()
            height = command_popup_item_height(len(items), lines, full_height)
            width = min(max(24, max(display_width(item.title) for item in items) + 6), max(24, columns - 4))
            popup_height = height + 3
            start_row, start_col = self.popup_origin(columns, lines, width, popup_height)
            if cursor < top:
                top = cursor
            elif cursor >= top + height:
                top = cursor - height + 1
            self.draw(term)
            self.draw_popup_border(term, start_row, start_col, width, popup_height)
            for row in range(height):
                index = top + row
                item = items[index]
                line = fit(f"  {item.title}", width - 2)
                term.move(start_row + 1 + row, start_col + 1)
                if item.disabled:
                    term.write(color_text(line, "90"))
                else:
                    term.write(reverse(line) if index == cursor else line)
            footer = fit(" Enter:OK  ESC:Cancel ", width - 2)
            term.move(start_row + popup_height - 1, start_col + 1)
            term.write(yellow_bg(footer))
            term.flush()
            key = read_key()
            if key in (KEY_ENTER,):
                return None if items[cursor].disabled else cursor
            if key in (KEY_ESCAPE, "q", "Q", KEY_BACKSPACE):
                return None
            if key in (KEY_UP, "k", "K"):
                cursor = move_enabled_command(items, cursor, -1)
            elif key in (KEY_DOWN, "j", "J"):
                cursor = move_enabled_command(items, cursor, 1)
            elif key == KEY_PGUP:
                cursor = move_enabled_command(items, cursor, -height)
            elif key == KEY_PGDN:
                cursor = move_enabled_command(items, cursor, height)

    def popup_origin(self, columns: int, lines: int, width: int, height: int) -> tuple[int, int]:
        row = max(2, (lines - height) // 2 + 1)
        if self.mode != "dual":
            return row, max(1, (columns - width) // 2 + 1)
        left_width = max(20, columns // 2)
        if self.active_pane == 0:
            pane_left = 1
            pane_width = left_width
        else:
            pane_left = left_width + 2
            pane_width = max(20, columns - left_width - 1)
        col = pane_left + max(0, (pane_width - width) // 2)
        return row, min(max(1, col), max(1, columns - width + 1))

    def draw_popup_border(self, term: Terminal, row: int, col: int, width: int, height: int) -> None:
        horizontal = "█" * (width - 2)
        term.move(row, col)
        term.write(yellow("█" + horizontal + "█"))
        for inner_row in range(1, height - 1):
            term.move(row + inner_row, col)
            term.write(yellow("█") + (" " * (width - 2)) + yellow("█"))
        term.move(row + height - 1, col)
        term.write(yellow("█" + horizontal + "█"))

    def rename_selected(self, term: Terminal) -> None:
        if self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.compare_mode:
            self.status = "rename unavailable"
            return
        entry = self.selected()
        if entry is None:
            return
        entries = self.marked_entries()
        if entries and self.pane.search_mode:
            entries = self.unique_file_entries(entries)
        if entries:
            if len(entries) == 1 and entries[0].zip_path is not None:
                self.rename_zip_selected(term, entries[0])
                return
            self.rename_marked(term, entries)
            return
        if self.pane.search_mode:
            entries = self.selected_entries()
            if entries:
                self.rename_one(term, entries[0])
            return
        if entry.zip_path is not None:
            self.rename_zip_selected(term, entry)
            return
        self.rename_one(term, entry)

    def rename_one(self, term: Terminal, entry: Entry) -> None:
        new_name = self.prompt(term, "rename", entry.path.name)
        new_name = expand_prompt_vars(new_name)
        if not new_name or new_name == entry.path.name:
            return
        dst = entry.path.with_name(new_name)
        try:
            entry.path.rename(dst)
            self.retarget_panes_after_rename(entry.path, dst)
            self.status = f"renamed: {entry.path.name} -> {new_name}"
            self.append_log(f"RENAME {entry.path} {dst} (success)")
        except OSError as exc:
            self.fail_status(f"rename failed: {exc}")
        self.refresh_all()

    def rename_zip_selected(self, term: Terminal, entry: Entry) -> None:
        if entry.zip_path is None or entry.zip_name is None:
            return
        new_name = self.prompt(term, "rename", entry.name)
        new_name = expand_prompt_vars(new_name)
        if not new_name or new_name == entry.name:
            return
        if "/" in new_name or "\\" in new_name:
            self.fail_status(f"rename failed: bad name {new_name}")
            return
        try:
            rename_zip_entry(entry, new_name)
            self.status = f"renamed: {entry.name} -> {new_name}"
            self.append_log(f"RENAME {entry_display_path(entry)} {new_name} (success)")
            self.clear_marks()
        except (OSError, zipfile.BadZipFile) as exc:
            self.fail_status(f"rename failed: {exc}")
        self.refresh_all()

    def rename_marked(self, term: Terminal, entries: list[Entry]) -> None:
        if any(entry.zip_path is not None for entry in entries):
            self.status = "zip内のrenameは未対応です"
            return
        template = self.prompt(term, "rename", "${file}.${ext}")
        if not template:
            self.status = "rename canceled"
            return
        template = expand_prompt_vars(template)
        width = len(str(len(entries))) if len(entries) < 10 else max(2, len(str(len(entries))))
        targets: list[tuple[Entry, Path]] = []
        seen: set[Path] = set()
        for index, entry in enumerate(entries, 1):
            name = rename_template(template, entry, index, width)
            if not name or "/" in name or "\\" in name:
                self.fail_status(f"rename failed: bad name {name}")
                return
            target = entry.path.with_name(name)
            if target in seen or (target.exists() and target != entry.path):
                self.fail_status(f"rename failed: exists {target.name}")
                return
            seen.add(target)
            targets.append((entry, target))
        try:
            for entry, target in targets:
                if entry.path != target:
                    entry.path.rename(target)
                    self.retarget_panes_after_rename(entry.path, target)
                    self.append_log(f"RENAME {entry.path} {target} (success)")
            self.status = f"renamed: {len(targets)} item(s)"
            self.clear_marks()
        except OSError as exc:
            self.fail_status(f"rename failed: {exc}")
        self.refresh_all()

    def bulk_name_replace(self, term: Terminal) -> None:
        if self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.compare_mode:
            self.status = "replace unavailable"
            return
        entries = self.marked_entries()
        if entries and self.pane.search_mode:
            entries = self.unique_file_entries(entries)
        if not entries:
            self.status = "replace: no marks"
            return
        if any(entry.zip_path is not None for entry in entries):
            self.status = "zip内のrenameは未対応です"
            return
        old = self.prompt(term, "replace from", "")
        if old == "":
            self.status = "replace canceled"
            return
        new = self.prompt(term, "replace to", "")
        new = expand_prompt_vars(new)
        targets: list[tuple[Entry, Path]] = []
        seen: set[Path] = set()
        for entry in entries:
            name = entry.name.replace(old, new)
            if name == entry.name:
                continue
            if not name or "/" in name or "\\" in name:
                self.fail_status(f"replace failed: bad name {name}")
                return
            target = entry.path.with_name(name)
            if target in seen or (target.exists() and target != entry.path):
                self.fail_status(f"replace failed: exists {target.name}")
                return
            seen.add(target)
            targets.append((entry, target))
        if not targets:
            self.status = "replace: no change"
            return
        try:
            for entry, target in targets:
                entry.path.rename(target)
                self.retarget_panes_after_rename(entry.path, target)
                self.append_log(f"RENAME {entry.path} {target} (success)")
            self.status = f"replaced: {len(targets)} item(s)"
            self.clear_marks()
        except OSError as exc:
            self.fail_status(f"replace failed: {exc}")
        self.refresh_all()

    def mkdir(self, term: Terminal) -> None:
        if self.pane.zip_path is not None:
            self.status = "zip内のmkdirは未対応です"
            return
        name = self.prompt(term, "mkdir", "")
        if not name:
            return
        try:
            (self.cwd / name).mkdir()
            self.status = f"created: {name}"
            self.append_log(f"MKDIR {self.cwd / name} (success)")
        except OSError as exc:
            self.fail_status(f"mkdir failed: {exc}")
        self.refresh_all()

    def delete_selected(self, term: Terminal) -> None:
        if self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.compare_mode:
            self.status = "delete unavailable"
            return
        entries = self.selected_entries()
        if not entries:
            return
        if not self.confirm_key(term, f"delete {len(entries)} item(s)? y/N"):
            self.status = "delete canceled"
            return
        self.log_busy = True
        try:
            try:
                self.append_live_log(term, f"DELETE start: {len(entries)} item(s)")
                if any(entry.zip_path is not None for entry in entries):
                    delete_zip_entries(entries)
                    for entry in entries:
                        self.append_live_log(term, f"DELETE {entry_display_path(entry)} (success)")
                else:
                    deleted_paths = [entry.path for entry in entries]
                    for entry in entries:
                        self.append_live_log(term, f"DELETE running: {entry.path}")
                        remove_file_target(entry.path)
                        self.append_live_log(term, f"DELETE {entry.path} (success)")
                    self.fallback_panes_after_delete(deleted_paths)
                self.status = f"deleted: {len(entries)} item(s)"
                self.append_live_log(term, self.status)
                self.clear_marks()
            except (OSError, zipfile.BadZipFile) as exc:
                self.fail_status(f"delete failed: {exc}")
        finally:
            self.log_busy = False
        self.refresh_all()

    def confirm_key(self, term: Terminal, message: str) -> bool:
        key = self.read_confirm_key(term, message)
        return key in ("y", "Y")

    def confirm_thuru_list(self, term: Terminal) -> bool:
        if term is None:
            return self.confirm_key(term, "get list? (N/y)")  # type: ignore[arg-type]
        key = confirm_popup_key(term, "get list? (N/y)", lambda: self.draw(term), hint="Y:get list  N/ESC:Cancel  Up/Down:move")
        if key in (KEY_UP, "k", "K"):
            self.move_cursor(-1)
            self.pane.preview_top = 0
            self.pane.thuru_preview_path = None
            self.status = "?:help"
            return False
        if key in (KEY_DOWN, "j", "J"):
            self.move_cursor(1)
            self.pane.preview_top = 0
            self.pane.thuru_preview_path = None
            self.status = "?:help"
            return False
        return key in ("y", "Y")

    def confirm_quit(self, term: Terminal) -> bool:
        items = ["Quit vfiler?", "Q/q/Y/y/Enter: quit", "Other key: cancel"]
        while True:
            columns, lines = term.size()
            width = min(max(28, max(display_width(item) for item in items) + 4), max(28, columns - 4))
            popup_height = len(items) + 2
            start_row, start_col = self.popup_origin(columns, lines, width, popup_height)
            self.draw(term)
            self.draw_popup_border(term, start_row, start_col, width, popup_height)
            for index, item in enumerate(items):
                term.move(start_row + 1 + index, start_col + 1)
                term.write(fit(item, width - 2))
            term.flush()
            key = read_key()
            if key in (KEY_ENTER, "q", "Q", "y", "Y"):
                return True
            if key:
                self.status = "quit canceled"
                return False

    def read_confirm_key(self, term: Terminal, message: str) -> str:
        return confirm_popup_key(term, message, lambda: self.draw(term))

    def copy_selected(self, term: Terminal) -> None:
        if self.pane.git_history_mode or self.pane.git_tree_mode or self.pane.compare_mode:
            self.status = "copy unavailable"
            return
        entries = self.selected_entries()
        if not entries:
            return
        zip_target = self.copy_target_zip()
        if zip_target is not None:
            try:
                add_entries_to_zip(zip_target[0], entries, zip_target[1])
                for entry in entries:
                    self.append_log(f"COPY {entry_display_path(entry)} {zip_target[0]} (success)")
                self.status = f"added to archive: {len(entries)} item(s)"
                self.clear_marks()
                self.refresh_all()
            except (OSError, zipfile.BadZipFile) as exc:
                self.fail_status(f"zip copy failed: {exc}")
            return
        dst_text = self.prompt(term, "copy to", str(self.default_target_path(entries)))
        if not dst_text:
            return
        dst = Path(dst_text).expanduser()
        if not dst.is_absolute():
            dst = self.cwd / dst
        self.log_busy = True
        try:
            try:
                overwrite_all = [False]
                copied = 0
                skipped = 0
                self.append_live_log(term, f"COPY start: {len(entries)} item(s) -> {dst}")
                for entry in entries:
                    target = self.copy_target_path(entry, dst, len(entries) > 1)
                    self.append_live_log(term, f"COPY running: {entry_display_path(entry)} -> {target}")
                    action = self.prepare_file_target(term, entry, target, "copy", overwrite_all)
                    if action == "cancel":
                        self.refresh_all()
                        return
                    if action == "skip":
                        skipped += 1
                        self.append_live_log(term, f"COPY {entry_display_path(entry)} {target} (skip)")
                        continue
                    self.copy_entry_to(entry, target, term)
                    self.append_live_log(term, f"COPY {entry_display_path(entry)} {target} (success)")
                    copied += 1
                self.status = f"copied: {copied} item(s)" + (f", skipped: {skipped}" if skipped else "")
                self.append_live_log(term, self.status)
                self.clear_marks()
            except OSError as exc:
                self.fail_status(f"copy failed: {exc}")
        finally:
            self.log_busy = False
        self.refresh_all()

    def copy_target_zip(self) -> tuple[Path, str] | None:
        if self.mode != "dual":
            return None
        other = self.panes[1 - self.active_pane]
        if other.zip_path is not None and is_real_zip_archive_path(other.zip_path):
            return other.zip_path, other.zip_dir
        return None

    def merge_copy_selected(self, term: Terminal) -> None:
        if self.pane.git_history_mode or self.pane.git_tree_mode or self.pane.compare_mode:
            self.status = "merge copy unavailable"
            return
        entries = self.selected_entries()
        if not entries:
            return
        if self.copy_target_zip() is not None:
            self.status = "zipへのmerge copyは未対応です"
            return
        default = self.other_cwd_for_file_ops() if self.mode == "dual" else self.cwd
        dst_text = self.prompt(term, "merge copy to", str(default))
        if not dst_text:
            self.status = "merge copy canceled"
            return
        dst = Path(dst_text).expanduser()
        if not dst.is_absolute():
            dst = self.cwd / dst
        self.log_busy = True
        try:
            try:
                overwrite_all = [False]
                copied = 0
                skipped = 0
                self.append_live_log(term, f"MERGE COPY start: {len(entries)} item(s) -> {dst}")
                for entry in entries:
                    target = self.merge_copy_target(dst, entry)
                    if target is None:
                        skipped += 1
                        continue
                    self.append_live_log(term, f"MERGE COPY running: {entry_display_path(entry)} -> {target}")
                    if entry.zip_path is not None:
                        done, skip = self.merge_copy_zip_entry(term, entry, target, overwrite_all)
                    else:
                        if self.pane.git_status_mode and not entry.path.exists():
                            skipped += 1
                            continue
                        done, skip = self.merge_copy_entry(term, entry.path, target, overwrite_all)
                    copied += done
                    skipped += skip
                self.status = f"merge copied: {copied} file(s)" + (f", skipped: {skipped}" if skipped else "")
                self.append_live_log(term, self.status)
                self.clear_marks()
            except ARCHIVE_READ_ERRORS as exc:
                if str(exc) == "canceled":
                    self.status = "merge copy canceled"
                else:
                    self.fail_status(f"merge copy failed: {exc}")
        finally:
            self.log_busy = False
        self.refresh_all()

    def merge_copy_target(self, dst: Path, entry: Entry) -> Path | None:
        if self.pane.git_status_mode and entry.zip_path is None:
            return safe_relative_target(dst, entry.name)
        return dst / entry.name

    def merge_copy_entry(self, term: Terminal, source: Path, target: Path, overwrite_all: list[bool]) -> tuple[int, int]:
        if target.exists() and same_existing_path(source, target):
            return 0, 1
        if source.is_dir():
            if is_path_inside(target, source):
                raise OSError("target inside source")
            if target.exists() and not target.is_dir():
                choice = self.confirm_overwrite_action(term, target, overwrite_all)
                if choice == "cancel":
                    raise OSError("canceled")
                if choice == "skip":
                    return 0, 1
                remove_file_target(target)
            target.mkdir(parents=True, exist_ok=True)
            copied = 0
            skipped = 0
            for child in source.iterdir():
                self.append_live_log(term, f"MERGE COPY running: {child} -> {target / child.name}")
                done, skip = self.merge_copy_entry(term, child, target / child.name, overwrite_all)
                copied += done
                skipped += skip
            return copied, skipped
        action = self.prepare_file_target(term, Entry(source, source.name, False, source.stat().st_size), target, "merge copy", overwrite_all)
        if action == "cancel":
            raise OSError("canceled")
        if action == "skip":
            return 0, 1
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        self.append_live_log(term, f"MERGE COPY {source} {target} (success)")
        return 1, 0

    def merge_copy_zip_entry(self, term: Terminal, entry: Entry, target: Path, overwrite_all: list[bool]) -> tuple[int, int]:
        if entry.zip_path is None or entry.zip_name is None:
            return 0, 0
        copied = 0
        skipped = 0
        if is_tar_archive_path(entry.zip_path):
            for name, data in archive_entry_file_data(entry):
                rel = Path(name[len(normalize_zip_dir(entry.zip_name)):] if entry.is_dir else entry.name)
                done, skip = self.merge_copy_zip_bytes(term, entry.zip_path, name, data, target / rel if entry.is_dir else target, overwrite_all)
                copied += done
                skipped += skip
            return copied, skipped
        with zipfile.ZipFile(entry.zip_path) as archive:
            if entry.is_dir:
                prefix = normalize_zip_dir(entry.zip_name)
                if target.exists() and not target.is_dir():
                    choice = self.confirm_overwrite_action(term, target, overwrite_all)
                    if choice == "cancel":
                        raise OSError("canceled")
                    if choice == "skip":
                        return 0, 1
                    remove_file_target(target)
                target.mkdir(parents=True, exist_ok=True)
                for info in archive.infolist():
                    if not info.filename.startswith(prefix) or info.is_dir():
                        continue
                    rel = Path(info.filename[len(prefix):])
                    done, skip = self.merge_copy_zip_file(term, archive, info, target / rel, overwrite_all)
                    copied += done
                    skipped += skip
                return copied, skipped
            info = archive.getinfo(entry.zip_name)
            return self.merge_copy_zip_file(term, archive, info, target, overwrite_all)

    def merge_copy_zip_bytes(self, term: Terminal, archive_path: Path, archive_name: str, data: bytes, target: Path, overwrite_all: list[bool]) -> tuple[int, int]:
        if target.exists():
            choice = self.confirm_overwrite_action(term, target, overwrite_all)
            if choice == "cancel":
                raise OSError("canceled")
            if choice == "skip":
                return 0, 1
            remove_file_target(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.append_live_log(term, f"MERGE COPY {archive_path}/{archive_name} {target} (success)")
        return 1, 0

    def merge_copy_zip_file(self, term: Terminal, archive: zipfile.ZipFile, info: zipfile.ZipInfo, target: Path, overwrite_all: list[bool]) -> tuple[int, int]:
        if target.exists():
            choice = self.confirm_overwrite_action(term, target, overwrite_all)
            if choice == "cancel":
                raise OSError("canceled")
            if choice == "skip":
                return 0, 1
            remove_file_target(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, target.open("wb") as out:
            shutil.copyfileobj(src, out)
        self.append_live_log(term, f"MERGE COPY {archive.filename}/{info.filename} {target} (success)")
        return 1, 0

    def move_selected(self, term: Terminal) -> None:
        if self.pane.git_history_mode or self.pane.git_status_mode or self.pane.git_tree_mode or self.pane.compare_mode:
            self.status = "move unavailable"
            return
        entries = self.selected_entries()
        if not entries:
            return
        if any(entry.zip_path is not None for entry in entries):
            self.status = "zip内のmoveは未対応です"
            return
        dst_text = self.prompt(term, "move to", str(self.default_target_path(entries)))
        if not dst_text:
            return
        dst = Path(dst_text).expanduser()
        if not dst.is_absolute():
            dst = self.cwd / dst
        self.log_busy = True
        try:
            try:
                overwrite_all = [False]
                moved = 0
                skipped = 0
                self.append_live_log(term, f"MOVE start: {len(entries)} item(s) -> {dst}")
                for entry in entries:
                    target = dst / entry.name if len(entries) > 1 or dst.is_dir() else dst
                    self.append_live_log(term, f"MOVE running: {entry.path} -> {target}")
                    action = self.prepare_file_target(term, entry, target, "move", overwrite_all)
                    if action == "cancel":
                        self.refresh_all()
                        return
                    if action == "skip":
                        skipped += 1
                        self.append_live_log(term, f"MOVE {entry.path} {target} (skip)")
                        continue
                    shutil.move(str(entry.path), str(target))
                    self.append_live_log(term, f"MOVE {entry.path} {target} (success)")
                    moved += 1
                self.status = f"moved: {moved} item(s)" + (f", skipped: {skipped}" if skipped else "")
                self.append_live_log(term, self.status)
                self.clear_marks()
            except OSError as exc:
                self.fail_status(f"move failed: {exc}")
        finally:
            self.log_busy = False
        self.refresh_all()

    def clip_selected(self, cut: bool) -> None:
        entries = self.selected_entries()
        if not entries:
            return
        if cut and any(entry.zip_path is not None for entry in entries):
            self.status = "zip内のcutは未対応です"
            return
        self.file_clipboard = (entries, cut)
        self.status = f"{'cut' if cut else 'copied'} to clipboard: {len(entries)} item(s)"
        self.clear_marks()
        self.refresh()

    def clear_file_clipboard(self) -> None:
        self.file_clipboard = None
        self.status = "file clip cleared"
        self.refresh()

    def preview_git_commit_file_selected(self, term: Terminal) -> None:
        entry = self.selected()
        if entry is None:
            return
        data = git_blob_bytes_for_path(self.cwd, self.pane.git_commit_hash, entry.path)
        if data is None:
            self.fail_status("commit view failed")
            return
        path = Path(tempfile.gettempdir()) / f"vfiler-commit-{self.pane.git_commit_hash[:7]}-{entry.path.name}"
        try:
            path.write_bytes(data)
        except OSError as exc:
            self.fail_status(f"commit view failed: {exc}")
            return
        saved = text_editor(term, path, True, self.config.colors)
        self.status = "view closed" if saved else "view canceled"
        self.refresh()

    def copy_selected_text(self, path_mode: bool) -> None:
        entries = self.selected_entries()
        if not entries:
            return
        values = [entry_display_path(entry) if path_mode else entry.name for entry in entries]
        text = "\n".join(values)
        editor_push_clip(text)
        label = values[0] if len(values) == 1 else f"{values[0]} ... {len(values)} item(s)"
        self.status = f"{label} copied."
        self.clear_marks()
        self.refresh()

    def paste_clipped(self, term: Terminal) -> None:
        if self.file_clipboard is None:
            self.status = "clipboard empty"
            return
        entries, cut = self.file_clipboard
        if self.pane.zip_path is not None:
            if is_tar_archive_path(self.pane.zip_path):
                self.status = "tarへのpasteは未対応です"
                return
            try:
                add_entries_to_zip(self.pane.zip_path, entries, self.pane.zip_dir)
                if cut:
                    self.delete_source_entries(entries)
                    self.file_clipboard = None
                for entry in entries:
                    self.append_log(f"PASTE {entry_display_path(entry)} {self.pane.zip_path} (success)")
                self.status = f"pasted to archive: {len(entries)} item(s)"
                self.clear_marks()
            except (OSError, zipfile.BadZipFile) as exc:
                self.fail_status(f"paste failed: {exc}")
            self.refresh_all()
            return
        dst = self.cwd
        self.log_busy = True
        try:
            try:
                overwrite_all = [False]
                pasted = 0
                skipped = 0
                skipped_entries: list[Entry] = []
                self.append_live_log(term, f"PASTE start: {len(entries)} item(s) -> {dst}")
                for entry in entries:
                    if cut and entry.zip_path is None:
                        target = dst / entry.name
                        self.append_live_log(term, f"PASTE running: {entry.path} -> {target}")
                        action = self.prepare_file_target(term, entry, target, "paste", overwrite_all)
                        if action == "cancel":
                            self.refresh_all()
                            return
                        if action == "skip":
                            skipped += 1
                            skipped_entries.append(entry)
                            self.append_live_log(term, f"PASTE {entry.path} {target} (skip)")
                            continue
                        shutil.move(str(entry.path), str(target))
                        self.append_live_log(term, f"PASTE {entry.path} {target} (success)")
                    else:
                        target = self.copy_target_path(entry, dst, True)
                        self.append_live_log(term, f"PASTE running: {entry_display_path(entry)} -> {target}")
                        action = self.prepare_file_target(term, entry, target, "paste", overwrite_all)
                        if action == "cancel":
                            self.refresh_all()
                            return
                        if action == "skip":
                            skipped += 1
                            if cut:
                                skipped_entries.append(entry)
                            self.append_live_log(term, f"PASTE {entry_display_path(entry)} {target} (skip)")
                            continue
                        self.copy_entry_to(entry, target, term)
                        self.append_live_log(term, f"PASTE {entry_display_path(entry)} {target} (success)")
                    pasted += 1
                if cut:
                    self.file_clipboard = (skipped_entries, True) if skipped_entries else None
                self.status = f"pasted: {pasted} item(s)" + (f", skipped: {skipped}" if skipped else "")
                self.append_live_log(term, self.status)
                self.clear_marks()
            except OSError as exc:
                self.fail_status(f"paste failed: {exc}")
        finally:
            self.log_busy = False
        self.refresh_all()

    def delete_source_entries(self, entries: list[Entry]) -> None:
        for entry in entries:
            if entry.zip_path is not None:
                continue
            remove_file_target(entry.path)

    def search_files(self, term: Terminal) -> None:
        if self.is_thuru_blocked(self.pane):
            self.pane.search_mode = True
            self.pane.search_pattern = ""
            self.pane.search_kind = "content"
            self.entries = []
            self.cursor = 0
            self.top = 0
            self.status = "search skipped: thurupath"
            return
        history = EDITOR_STATE.search_history or []
        pattern = self.prompt_search(term, "search", self.pane.search_pattern, history)
        if not pattern:
            self.pane.search_mode = False
            self.pane.search_pattern = ""
            self.pane.search_kind = "content"
            self.status = "search cleared"
            self.refresh()
            return
        try:
            re_compile(pattern)
        except ValueError as exc:
            self.fail_status(f"search error: {exc}")
            return
        if pattern not in history:
            history.append(pattern)
            EDITOR_STATE.search_history = history
        self.pane.search_mode = True
        self.pane.search_pattern = pattern
        self.pane.search_kind = "content"
        self.pane.duplex_mode = False
        self.pane.duplex_root = None
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"search: {pattern}  {len(self.entries)} hit row(s)"

    def search_filenames(self, term: Terminal) -> None:
        history = EDITOR_STATE.search_history or []
        pattern = self.prompt_search(term, "filename search", self.pane.search_pattern if self.pane.search_kind == "name" else "", history)
        if not pattern:
            self.pane.search_mode = False
            self.pane.search_pattern = ""
            self.pane.search_kind = "content"
            self.status = "filename search cleared"
            self.refresh()
            return
        try:
            re_compile(pattern)
        except ValueError as exc:
            self.fail_status(f"filename search error: {exc}")
            return
        if pattern not in history:
            history.append(pattern)
            EDITOR_STATE.search_history = history
        self.pane.search_mode = True
        self.pane.search_pattern = pattern
        self.pane.search_kind = "name"
        self.pane.duplex_mode = False
        self.pane.duplex_root = None
        self.cursor = 0
        self.top = 0
        self.clear_marks()
        self.refresh()
        self.status = f"filename search: {pattern}  {len(self.entries)} hit(s)"

    def prompt_search(self, term: Terminal, label: str, default: str, history: list[str]) -> str:
        term.show_cursor()
        try:
            value = popup_edit_line(term, label, default, lambda: self.draw(term), history)
            return value.strip()
        finally:
            term.hide_cursor()

    def copy_entry(self, entry: Entry, dst: Path, multi: bool) -> None:
        self.copy_entry_to(entry, self.copy_target_path(entry, dst, multi))

    def copy_target_path(self, entry: Entry, dst: Path, multi: bool) -> Path:
        return dst / entry.name if multi or dst.is_dir() else dst

    def copy_entry_to(self, entry: Entry, target: Path, term: Terminal | None = None) -> None:
        if entry.zip_path is not None and entry.zip_name is not None:
            copy_zip_entry(entry, target, False)
            return
        if entry.is_dir:
            self.copy_directory_live(entry.path, target, term)
        else:
            if term is not None:
                self.append_live_log(term, f"COPY file: {entry.path} -> {target}")
            shutil.copy2(entry.path, target)

    def copy_directory_live(self, source: Path, target: Path, term: Terminal | None = None) -> None:
        if is_path_inside(target, source):
            raise OSError("target inside source")
        target.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            child_target = target / child.name
            if child.is_dir():
                if term is not None:
                    self.append_live_log(term, f"COPY dir: {child} -> {child_target}")
                self.copy_directory_live(child, child_target, term)
            else:
                if term is not None:
                    self.append_live_log(term, f"COPY file: {child} -> {child_target}")
                shutil.copy2(child, child_target)

    def confirm_overwrite_action(self, term: Terminal, target: Path, overwrite_all: list[bool] | None = None) -> str:
        if overwrite_all is not None and overwrite_all[0]:
            return "yes"
        message = overwrite_prompt(target, overwrite_all is not None)
        key = self.read_confirm_key(term, message)
        if key in ("a", "A") and overwrite_all is not None:
            overwrite_all[0] = True
            return "yes"
        if key in ("y", "Y"):
            return "yes"
        if overwrite_all is not None and key in ("c", "C"):
            return "cancel"
        if overwrite_all is not None:
            return "skip"
        return "cancel"

    def prepare_file_target(self, term: Terminal, entry: Entry, target: Path, action: str, overwrite_all: list[bool] | None = None) -> str:
        if not target.exists():
            return "yes"
        if entry.zip_path is None and same_existing_path(entry.path, target):
            self.fail_status(f"{action} failed: same file")
            return "cancel"
        choice = self.confirm_overwrite_action(term, target, overwrite_all)
        if choice == "cancel":
            self.status = f"{action} canceled"
            return "cancel"
        if choice == "skip":
            self.status = f"{action} skipped: {target.name}"
            return "skip"
        remove_file_target(target)
        return "yes"

    def default_target_path(self, entries: list[Entry]) -> Path:
        if self.mode == "dual":
            other_pane = self.panes[1 - self.active_pane]
            if other_pane.zip_path is not None:
                return other_pane.zip_path
            base = other_pane.cwd
        else:
            base = self.cwd
        if len(entries) == 1:
            return base / entries[0].name
        return base

    def set_filter(self, term: Terminal) -> None:
        text = self.prompt(term, "filter", self.filter_text)
        self.filter_text = text
        self.cursor = 0
        self.top = 0
        self.refresh()

    def view_file(self, term: Terminal, path: Path, line: int | None = None) -> None:
        if self.return_editor_requests:
            self.editor_request = (path, True, line)
            return
        active = self.active_pane
        target = path
        text_editor(term, path, True, self.config.colors, start_line=line)
        self.refresh_all()
        if target:
            self.focus_path_in_pane(active, target)

    def view_zip_file(self, term: Terminal, zip_path: Path, zip_name: str) -> None:
        try:
            data = archive_read_bytes(zip_path, zip_name)
        except ARCHIVE_READ_ERRORS as exc:
            self.fail_status(f"archive view failed: {exc}")
            return
        temp_path = zip_view_temp_path(zip_path, zip_name)
        try:
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_bytes(data)
        except OSError as exc:
            self.fail_status(f"archive view failed: {exc}")
            return
        self.view_file(term, temp_path)

    def spawn_external(self, term: Terminal, command: str, charset: str = "") -> int | None:
        clear_git_cache()
        popen_kwargs = external_command_popen_kwargs(charset)
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                executable=self.command_shell(),
                cwd=str(self.cwd),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                errors="replace",
                bufsize=1,
                **popen_kwargs,
            )
        except OSError as exc:
            output = f"cwd: {self.cwd}\n$ {command}\n\nfailed to start: {exc}\n"
            self.append_command_log(output)
            self.show_command_output(term, command, output)
            return None
        returncode, output = self.show_live_command_output(term, command, process)
        self.append_command_log(output)
        clear_git_cache()
        return returncode

    def spawn_external_fullscreen(self, term: Terminal, command: str, charset: str = "") -> int | None:
        clear_git_cache()
        run_kwargs = external_command_run_kwargs(charset)
        term.clear()
        term.leave_app_mode()
        try:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    executable=self.command_shell(),
                    cwd=str(self.cwd),
                    **run_kwargs,
                )
                return result.returncode
            except OSError as exc:
                print(f"failed to start command: {exc}")
                try:
                    input("Enter:back")
                except EOFError:
                    pass
                return None
        finally:
            term.enter_app_mode()
            term.clear()
            clear_git_cache()

    def append_command_log(self, output: str) -> None:
        for line in output.rstrip("\n").splitlines():
            self.append_log(line)
        if not output.strip():
            self.append_log("(no output)")

    def command_result_status(self, returncode: int | None) -> str:
        if returncode == 0:
            return "command finished"
        if returncode is None:
            return "command failed"
        return f"command failed: {returncode}"

    def command_shell(self) -> str | None:
        shell = self.config.shell.strip()
        if not shell:
            return None
        path = Path(shell).expanduser()
        if path.is_absolute():
            return str(path) if path.exists() else None
        return shutil.which(shell)

    def show_live_command_output(self, term: Terminal, command: str, process: subprocess.Popen[str]) -> tuple[int | None, str]:
        events: queue.Queue[tuple[str, str | int]] = queue.Queue()
        stdout_done = process.stdout is None
        stderr_done = process.stderr is None
        if process.stdout is not None:
            threading.Thread(target=read_process_stream, args=(process.stdout, events, "out"), daemon=True).start()
        if process.stderr is not None:
            threading.Thread(target=read_process_stream, args=(process.stderr, events, "err"), daemon=True).start()

        output = f"cwd: {self.cwd}\n$ {command}\n"
        offset = 0
        follow = True
        returncode: int | None = None
        saved_path: Path | None = None
        dirty = True
        def drain_events(wait: float = 0.0) -> None:
            nonlocal output, dirty, stdout_done, stderr_done
            timeout = wait
            while True:
                try:
                    kind, value = events.get(timeout=timeout)
                except queue.Empty:
                    return
                timeout = 0.0
                if kind == "out":
                    output += str(value)
                    dirty = True
                elif kind == "err":
                    output += str(value)
                    dirty = True
                elif kind == "out_done":
                    stdout_done = True
                elif kind == "err_done":
                    stderr_done = True

        while True:
            drain_events()
            if returncode is None:
                returncode = process.poll()
                if returncode is not None:
                    drain_events(0.05)
                    output += f"\nexit code: {returncode}\n"
                    dirty = True
                    if self.config.autosave_runlog:
                        saved_path = self.save_run_log(output)
                        dirty = True

            columns, lines = term.size()
            body_height = max(1, lines - 3)
            rows = wrap_output_lines(output, columns)
            if follow:
                offset = max(0, len(rows) - body_height)
            if dirty:
                term.clear()
                term.write(reverse(fit(f" running: {command} ", columns)) + "\n")
                for row in rows[offset : offset + body_height]:
                    term.write(fit(row, columns) + "\n")
                pos = f" {min(offset + 1, len(rows))}/{len(rows)} "
                save_text = f" saved:{saved_path.name} " if saved_path is not None else " s:save "
                footer = " Enter:back  q:stop/back  Up/Down/PgUp/PgDn scroll " + save_text + pos
                if returncode is None:
                    footer = " running  " + footer
                term.write(reverse(fit(footer, columns)))
                term.flush()
                dirty = False

            key = read_key_timeout(0.08)
            if key:
                if key in (KEY_ENTER, KEY_ESCAPE, KEY_BACKSPACE):
                    if returncode is not None:
                        break
                elif key in ("q", "Q"):
                    if returncode is None:
                        process.terminate()
                        output += "\nterminated\n"
                        returncode = process.wait()
                        drain_events(0.05)
                        if self.config.autosave_runlog:
                            saved_path = self.save_run_log(output)
                    break
                elif key in ("s", "S"):
                    saved_path = self.save_run_log(output)
                    dirty = True
                elif key in (KEY_UP, "k", "K"):
                    follow = False
                    offset = max(0, offset - 1)
                    dirty = True
                elif key in (KEY_DOWN, "j", "J"):
                    follow = False
                    offset = min(max(0, len(rows) - body_height), offset + 1)
                    dirty = True
                elif key == KEY_PGUP:
                    follow = False
                    offset = max(0, offset - body_height)
                    dirty = True
                elif key == KEY_PGDN:
                    follow = False
                    offset = min(max(0, len(rows) - body_height), offset + body_height)
                    dirty = True
        return returncode, output

    def show_command_output(self, term: Terminal, command: str, output: str) -> None:
        offset = 0
        saved_path: Path | None = self.save_run_log(output) if self.config.autosave_runlog else None
        while True:
            columns, lines = term.size()
            body_height = max(1, lines - 3)
            rows = wrap_output_lines(output, columns)
            term.clear()
            term.write(reverse(fit(f" command result: {command} ", columns)) + "\n")
            for row in rows[offset : offset + body_height]:
                term.write(fit(row, columns) + "\n")
            pos = f" {min(offset + 1, len(rows))}/{len(rows)} "
            save_text = f" saved:{saved_path.name} " if saved_path is not None else " s:save "
            term.write(reverse(fit(" Enter:back  Up/Down/PgUp/PgDn scroll " + save_text + pos, columns)))
            term.flush()
            key = read_key()
            if key in (KEY_ENTER, KEY_ESCAPE, KEY_BACKSPACE, "q", "Q"):
                break
            if key in ("s", "S"):
                saved_path = self.save_run_log(output)
                continue
            if key in (KEY_UP, "k", "K"):
                offset = max(0, offset - 1)
            elif key in (KEY_DOWN, "j", "J"):
                offset = min(max(0, len(rows) - body_height), offset + 1)
            elif key == KEY_PGUP:
                offset = max(0, offset - body_height)
            elif key == KEY_PGDN:
                offset = min(max(0, len(rows) - body_height), offset + body_height)

    def save_run_log(self, output: str) -> Path | None:
        base = Path(self.config.autosave_runlog_path).expanduser() if self.config.autosave_runlog_path else self.cwd
        if not base.is_absolute():
            base = self.cwd / base
        try:
            base.mkdir(parents=True, exist_ok=True)
            path = base / (time.strftime("%Y%m%d-%H%M%S") + ".log")
            suffix = 1
            while path.exists():
                path = base / (time.strftime("%Y%m%d-%H%M%S") + f"-{suffix}.log")
                suffix += 1
            path.write_text(output, encoding="utf-8", errors="replace")
            return path
        except OSError:
            return None

    def prompt(self, term: Terminal, label: str, default: str) -> str:
        term.show_cursor()
        try:
            value = popup_edit_line(term, label, default, lambda: self.draw(term))
            return value.strip()
        finally:
            self.clear_prompt_line(term)
            term.hide_cursor()

    def prompt_history(self, term: Terminal, label: str, default: str) -> str:
        term.show_cursor()
        try:
            value = popup_edit_line(term, label, default, lambda: self.draw(term), EDITOR_STATE.run_history)
            return value.strip()
        finally:
            self.clear_prompt_line(term)
            term.hide_cursor()

    def clear_prompt_line(self, term: Terminal) -> None:
        _, lines = term.size()
        term.move(lines, 1)
        term.write("\x1b[2K")
        term.flush()

    def show_help(self, term: Terminal) -> None:
        rows = [
            "1 preview mode",
            "2 dual pane mode",
            "Up/Down/PgUp/PgDn move",
            "Tab focus current pane/log",
            "Log active: Enter shell, Up/Down history, PgUp/PgDn/k/j scroll",
            "Left/Right switch pane",
            "F7 pane/log size mode",
            "Enter open/exec",
            "Backspace parent",
            "\\\\ root",
            "Space mark",
            "a mark all",
            "F9 file copy to clipboard",
            "Shift+F9 file cut to clipboard",
            "F10 file paste from clipboard",
            "v preview file",
            "e edit",
            "i information",
            "x launcher",
            "g git menu",
            "s sort",
            "l directory list",
            "w sync other pane / wrap in preview mode",
            "c copy",
            "m move",
            "r rename",
            "n mkdir",
            "d delete",
            "f search file contents by regex",
            "  Up/Down in prompt recalls search history",
            "  result rows can delete / rename / copy",
            "/ filter names in active pane",
            "  match: contains typed text",
            "  wildcard: *.py, *@**.jpg",
            "  empty filter clears it",
            "  filter is per pane",
            "q quit",
        ]
        self.show_text_popup(term, "Help", rows)

    def show_text_popup(self, term: Terminal, title: str, rows: list[str]) -> None:
        if not rows:
            rows = [""]
        offset = 0
        while True:
            columns, lines = term.size()
            width = min(max(28, max(max(display_width(row) for row in rows), display_width(title)) + 4), max(28, columns - 4))
            height = min(len(rows), max(1, lines - 6))
            popup_height = height + 3
            start_row = max(2, (lines - popup_height) // 2 + 1)
            start_col = max(1, (columns - width) // 2 + 1)
            self.draw(term)
            self.draw_popup_border(term, start_row, start_col, width, popup_height)
            term.move(start_row, start_col + 2)
            term.write(yellow_bg(fit(f" {title} ", min(width - 4, display_width(title) + 2))))
            for index, row in enumerate(rows[offset : offset + height]):
                term.move(start_row + 1 + index, start_col + 1)
                term.write(fit(row, width - 2))
            term.move(start_row + popup_height - 1, start_col + 1)
            pos = f" {min(offset + 1, len(rows))}/{len(rows)} "
            term.write(yellow_bg(fit(" Enter:back  Up/Down scroll " + pos, width - 2)))
            term.flush()
            key = read_key()
            if key in (KEY_ENTER, KEY_ESCAPE, KEY_BACKSPACE, "q", "Q", "?"):
                break
            if key in (KEY_UP, "k", "K"):
                offset = max(0, offset - 1)
            elif key in (KEY_DOWN, "j", "J"):
                offset = min(max(0, len(rows) - height), offset + 1)
            elif key == KEY_PGUP:
                offset = max(0, offset - height)
            elif key == KEY_PGDN:
                offset = min(max(0, len(rows) - height), offset + height)

    def draw(self, term: Terminal) -> None:
        if self.mode == "dual":
            self.draw_dual(term)
        else:
            self.draw_preview(term)

    def draw_preview(self, term: Terminal) -> None:
        columns, lines = term.size()
        list_width = max(20, min(columns - 1, int(columns * self.pane.preview_ratio)))
        preview_width = max(0, columns - list_width - 1)
        body_height = filer_body_height(lines, self.log_height)
        log_height = filer_log_display_height(lines, self.log_height)
        self.ensure_visible(body_height)

        term.move(1, 1)
        term.write(self.menu_bar(columns) + "\n")
        title = f" {self.pane_display_path(self.pane)}"
        if self.filter_text:
            title += f" filter:{self.filter_text} "
        if self.pane.search_mode:
            title += f" search:{self.pane.search_pattern} "
        if self.pane.git_history_mode and self.pane.git_history_file is not None:
            title += f" history:{self.pane.git_history_file.name} "
        if self.pane.git_status_mode:
            title += f" git {git_status_title(self.pane.git_status_kind)} "
        if self.pane.git_tree_mode:
            title += " git tree "
        if self.pane.git_commit_files_mode:
            title += f" commit:{self.pane.git_commit_hash[:7]} "
        if self.pane.compare_mode:
            title = f" compare: {self.pane.compare_left} <-> {self.pane.compare_right} "
        if self.pane.duplex_mode:
            title = f" duplexes: {self.pane.duplex_root or self.cwd} "
        preview_title = entry_display_path(self.selected()) if self.selected() is not None else ""
        sep = reverse(" ")
        file_active = not self.pane.preview_focus and not self.log_focus
        preview_active = self.pane.preview_focus and not self.log_focus
        term.write(pad_ansi(self.filer_bar(title, list_width, file_active) + sep + self.filer_bar(preview_title, preview_width, preview_active), columns) + "\n")
        previews = self.preview_rows(preview_width, body_height)

        for screen_row in range(body_height):
            index = self.top + screen_row
            if index < len(self.entries):
                entry = self.entries[index]
                row = self.format_entry_row(entry, index == self.cursor, list_width)
                if index == self.cursor:
                    row = underline(row) if self.pane.preview_focus or self.log_focus else self.cursor_entry_row(entry, row, self.pane)
                elif self.pane.git_tree_mode:
                    row = color_git_graph_row(row)
                elif not self.pane.search_mode:
                    row = entry_color(entry, row, self.config.colors)
                if index != self.cursor and self.is_marked_entry(entry, self.pane):
                    row = reverse_ansi(row)
            else:
                row = fit(" NO FILES", list_width) if screen_row == 0 and not self.entries else " " * list_width
            preview = previews[screen_row] if screen_row < len(previews) else " " * preview_width
            term.write(pad_ansi(row + sep + preview, columns) + "\n")

        buffer_text = f"  BUF:{self.buffer_count}" if self.buffer_count else ""
        list_count = self.status_bar_text(f" {len(self.entries)} file(s){buffer_text} ", list_width)
        preview_count = " preview "
        term.write(pad_ansi(self.filer_bar(list_count, list_width, self.log_focus) + sep + self.filer_bar(preview_count, preview_width, self.log_focus), columns) + "\n")
        self.draw_log_pane(term, columns, log_height)
        term.flush()

    def draw_dual(self, term: Terminal) -> None:
        columns, lines = term.size()
        body_height = filer_body_height(lines, self.log_height)
        log_height = filer_log_display_height(lines, self.log_height)
        left_width = max(20, min(columns - 21, int(columns * self.dual_ratio)))
        right_width = max(20, columns - left_width - 1)

        for pane in self.panes:
            self.ensure_pane_visible(pane, body_height)

        term.move(1, 1)
        term.write(self.menu_bar(columns) + "\n")
        left_title = self.pane_title(0, left_width)
        right_title = self.pane_title(1, right_width)
        sep = reverse(" ")
        term.write(pad_ansi(left_title + sep + right_title, columns) + "\n")

        for screen_row in range(body_height):
            left = self.format_pane_row(0, screen_row, left_width)
            right = self.format_pane_row(1, screen_row, right_width)
            term.write(pad_ansi(left + sep + right, columns) + "\n")

        buffer_text = f" BUF:{self.buffer_count}" if self.buffer_count else ""
        left_count = f" {len(self.panes[0].entries)} file(s)"
        right_count = f" {len(self.panes[1].entries)} file(s)"
        if self.active_pane == 0:
            left_count = self.status_bar_text(left_count + f"{buffer_text} ", left_width)
        else:
            right_count = self.status_bar_text(right_count + f"{buffer_text} ", right_width)
        term.write(pad_ansi(self.filer_bar(left_count, left_width, self.log_focus) + sep + self.filer_bar(right_count, right_width, self.log_focus), columns) + "\n")
        self.draw_log_pane(term, columns, log_height)
        term.flush()

    def pane_title(self, pane_index: int, width: int) -> str:
        pane = self.panes[pane_index]
        title = f" {self.pane_display_path(pane)}"
        if pane.filter_text:
            title += f" filter:{pane.filter_text} "
        if pane.search_mode:
            title += f" search:{pane.search_pattern} "
        if pane.git_history_mode and pane.git_history_file is not None:
            title += f" history:{pane.git_history_file.name} "
        if pane.git_status_mode:
            title += f" git {git_status_title(pane.git_status_kind)} "
        if pane.git_tree_mode:
            title += f" git tree:{pane.git_tree_scope} "
        if pane.git_commit_files_mode:
            title += f" commit:{pane.git_commit_hash[:7]} "
        if pane.compare_mode:
            title = f" compare: {pane.compare_left} <-> {pane.compare_right} "
        if pane.duplex_mode:
            title = f" duplexes: {pane.duplex_root or pane.cwd} "
        return self.filer_bar(title, width, pane_index == self.active_pane and not self.log_focus)

    def draw_log_pane(self, term: Terminal, columns: int, height: int) -> None:
        show_prompt = self.log_prompt_visible()
        log_rows = max(0, height - (1 if show_prompt else 0))
        scroll_height = max(1, log_rows)
        max_top = max(0, len(self.log_lines) - scroll_height)
        self.log_top = max_top if self.log_follow_bottom else min(max(0, self.log_top), max_top)
        visible_count = min(log_rows, max(0, len(self.log_lines) - self.log_top))
        screen_rows: list[str] = []
        for row in range(visible_count):
            index = self.log_top + row
            text = self.log_lines[index] if index < len(self.log_lines) else ""
            screen_rows.append(fit(text, columns))
        if show_prompt and height > 0:
            screen_rows.append(self.log_prompt_row(columns))
        while len(screen_rows) < height:
            screen_rows.append(" " * columns)
        for row, text in enumerate(screen_rows[:height]):
            term.write(text)
            if row + 1 < height:
                term.write("\n")

    def log_prompt_row(self, columns: int) -> str:
        return log_prompt_row_text_colored("".join(self.log_input), self.log_input_cursor, columns, self.log_prompt_prefix(), self.config.colors, self.log_cwd)

    def log_prompt_prefix(self) -> str:
        if self.log_tail_active() and self.log_tail is not None:
            return f"[Tail] {stable_path_text(self.log_tail.path)} $ "
        path = stable_path_text(self.log_cwd)
        if path and not path.endswith(("/", "\\")):
            path += os.sep
        return f"{path} $ "

    def filer_bar(self, text: str, width: int, active: bool) -> str:
        fitted = pad_ansi(text, width) if "\x1b[" in text else fit(text, width)
        return color_text(fitted, self.config.colors["filer_active_bar_color"]) if active else reverse(fitted)

    def status_bar_text(self, text: str, width: int) -> str:
        if EDITOR_STATE.hide_empty_directories:
            label = "[EmpDir Hide] "
            return fit(text, max(0, width - display_width(label))) + color_text(label, "31")
        return text

    def format_pane_row(self, pane_index: int, screen_row: int, width: int) -> str:
        pane = self.panes[pane_index]
        index = pane.top + screen_row
        if index >= len(pane.entries):
            if screen_row == 0 and not pane.entries:
                return fit(" NO FILES", width)
            return " " * width
        entry = pane.entries[index]
        active = pane_index == self.active_pane and not self.log_focus
        row = self.format_entry_row(entry, active and index == pane.cursor, width, pane)
        if active and index == pane.cursor:
            return self.cursor_entry_row(entry, row, pane)
        if index == pane.cursor:
            return underline(row)
        if pane.git_tree_mode:
            row = color_git_graph_row(row)
        elif not pane.search_mode:
            row = entry_color(entry, row, self.config.colors)
        if self.is_marked_entry(entry, pane):
            row = reverse_ansi(row)
        return row

    def cursor_entry_row(self, entry: Entry, row: str, pane: PaneState) -> str:
        if pane.git_tree_mode:
            return reverse_ansi(color_git_graph_row(row))
        if pane.search_mode:
            return reverse(row)
        return entry_cursor_color(entry, row, self.config.colors)

    def format_entry_row(self, entry: Entry, active: bool, width: int, pane: PaneState | None = None) -> str:
        pane = pane or self.pane
        if pane.git_history_mode:
            return fit(f"{self.row_marker(entry, pane)} {entry.name}", width)
        if pane.git_status_mode:
            return fit(f"{self.row_marker(entry, pane)} {entry.search_text} {entry.name}", width)
        if pane.git_tree_mode:
            return fit(f"{self.row_marker(entry, pane)} {entry.name}", width)
        if pane.git_commit_files_mode:
            return fit(f"{self.row_marker(entry, pane)} {entry.search_text:<6} {entry.name}", width)
        if pane.compare_mode:
            return fit(f"{self.row_marker(entry, pane)} {entry.search_text:<6} {entry.name}", width)
        if pane.search_mode:
            if entry.search_line is not None:
                return self.fit_search_row(entry, width, active)
            return fit(entry.name, width)
        prefix = " "
        suffix = " "
        inner_width = max(1, width - display_width(prefix) - display_width(suffix))
        if pane.show_datetime:
            if self.config.change_file_datetime:
                size_text = f"{fmt_size(entry.size, entry.is_dir):>7}"
                datetime_text = f"{short_datetime(entry.mtime):>17}"
                meta_text = f"{size_text} {datetime_text}"
                name_width = inner_width - 1 - display_width(meta_text)
                if name_width > 0:
                    return prefix + fit(f"{fit(entry.name, name_width)} {meta_text}", inner_width) + suffix
            return prefix + fit(f"{fmt_size(entry.size, entry.is_dir):>7} {short_datetime(entry.mtime)} {entry.name}", inner_width) + suffix
        return prefix + fit(f"{fmt_size(entry.size, entry.is_dir):>7} {entry.name}", inner_width) + suffix

    def toggle_datetime(self) -> None:
        EDITOR_STATE.show_datetime = not EDITOR_STATE.show_datetime
        for pane in self.panes:
            pane.show_datetime = EDITOR_STATE.show_datetime
        save_stat()
        self.status = f"datetime: {'on' if EDITOR_STATE.show_datetime else 'off'}"

    def toggle_hide_empty_directories(self) -> None:
        EDITOR_STATE.hide_empty_directories = not EDITOR_STATE.hide_empty_directories
        self.refresh_all()
        save_stat(self.filer_stat())
        self.status = f"hide empty directories: {'on' if EDITOR_STATE.hide_empty_directories else 'off'}"

    def toggle_mouse_cursor(self, term: Terminal) -> None:
        EDITOR_STATE.mouse_cursor = not EDITOR_STATE.mouse_cursor
        term.set_mouse(True)
        save_stat()
        self.status = f"mouse cursor: {'on' if EDITOR_STATE.mouse_cursor else 'off'}"

    def toggle_wheel_scroll(self, term: Terminal) -> None:
        EDITOR_STATE.wheel_scroll = not EDITOR_STATE.wheel_scroll
        term.set_mouse(True)
        save_stat()
        self.status = f"wheel scroll: {'on' if EDITOR_STATE.wheel_scroll else 'off'}"

    def fit_search_row(self, entry: Entry, width: int, active: bool) -> str:
        text = entry.name
        if not entry.search_match or active:
            return fit(text, width)
        pos = text.find(entry.search_match)
        if pos < 0:
            return fit(text, width)
        before = fit_raw(text[:pos], width)
        remain = max(0, width - display_width(before))
        match = fit_raw(entry.search_match, remain)
        after = fit(text[pos + len(entry.search_match):], max(0, remain - display_width(match)))
        raw = before + color_text(match, self.config.colors["search_match_color"]) + after
        return pad_ansi(raw, width)

    def ensure_visible(self, body_height: int) -> None:
        self.ensure_pane_visible(self.pane, body_height)

    def ensure_pane_visible(self, pane: PaneState, body_height: int) -> None:
        pane.cursor, pane.top = clamp_scroll_position(pane.cursor, pane.top, len(pane.entries), body_height)

    def preview_line(self, line_index: int, width: int) -> str:
        if width <= 0:
            return ""
        entry = self.selected()
        if entry is None:
            return " " * width
        if line_index == 0:
            return fit(entry_display_path(entry), width)
        if entry.zip_path is not None and entry.zip_name is not None:
            if entry.is_dir:
                return fit("[zip directory]", width) if line_index == 1 else " " * width
            return fit_zip_preview_text(entry.zip_path, entry.zip_name, line_index - 2, width, self.pane.preview_numbers) if line_index > 1 else fit("[zip file preview]", width)
        if entry.is_dir:
            idx = line_index - 2
            if line_index == 1:
                return fit("[directory preview]", width)
            if self.is_thuru_preview_blocked(entry):
                return fit("y:get list", width) if line_index == 2 else " " * width
            children = directory_preview_children(entry.path, idx + 1)
            if 0 <= idx < len(children):
                prefix = "[D] " if children[idx].is_dir() else "    "
                return fit(prefix + children[idx].name, width)
            return " " * width
        if line_index == 1:
            return fit("[file preview]", width)
        return fit_preview_text(entry.path, line_index - 2, width, self.pane.preview_numbers)

    def preview_rows(self, width: int, height: int) -> list[str]:
        if width <= 0:
            return ["" for _ in range(height)]
        rows = self.preview_source_rows(width, height)
        if not rows and self.selected() is None:
            return [" " * width for _ in range(height)]
        if self.pane.preview_top:
            rows = rows[self.pane.preview_top:]
        fitted = [fit_ansi(row, width) if "\x1b[" in row else fit(row, width) for row in rows[:height]]
        while len(fitted) < height:
            fitted.append(" " * width)
        return fitted

    def is_thuru_preview_blocked(self, entry: Entry) -> bool:
        return entry.is_dir and is_thuru_path(entry.path, self.config.thurupaths) and self.pane.thuru_preview_path != entry.path

    def git_history_preview_rows(self, width: int, height: int) -> list[str]:
        selected = self.marked_entries()
        if len(selected) == 2:
            newer, older = sorted(selected, key=lambda item: item.mtime, reverse=True)
            return git_file_diff_rows(self.cwd, self.pane.git_history_file, newer.search_text, older.search_text, width)
        entry = self.selected()
        if entry is None:
            return []
        return git_file_at_rows(self.cwd, self.pane.git_history_file, entry.search_text, self.pane.preview_numbers, width, EDITOR_STATE.wrap, height + self.pane.preview_top)

    def git_status_preview_rows(self, width: int) -> list[str]:
        entry = self.selected()
        if entry is None:
            return []
        return git_status_diff_rows(self.cwd, entry.path, entry.search_text, width)

    def git_commit_file_preview_rows(self, width: int) -> list[str]:
        entry = self.selected()
        if entry is None:
            return []
        return git_commit_file_diff_rows(self.cwd, self.pane.git_commit_hash, entry.path, width)

    def git_tree_preview_rows(self, width: int) -> list[str]:
        entry = self.selected()
        if entry is None:
            return []
        if not IS_WINDOWS:
            return git_commit_detail_rows(self.cwd, entry.search_text, width)
        self.sync_git_tree_preview_state()
        if self.pane.git_tree_detail_commit == entry.search_text:
            return git_commit_detail_rows(self.cwd, entry.search_text, width)
        return git_tree_light_preview_rows(entry, width)

    def compare_preview_rows(self, width: int) -> list[str]:
        entry = self.selected()
        if entry is None:
            return []
        return compare_preview_rows(entry, width)

    def row_marker(self, entry: Entry, pane: PaneState) -> str:
        return "*" if pane.marks is not None and entry_key(entry) in pane.marks else " "

    def is_marked_entry(self, entry: Entry, pane: PaneState) -> bool:
        return pane.marks is not None and entry_key(entry) in pane.marks

    def pane_display_path(self, pane: PaneState) -> str:
        if pane.zip_path is None:
            return str(pane.cwd)
        suffix = ("/" + pane.zip_dir) if pane.zip_dir else ""
        return f"{pane.zip_path}{suffix}"


class EditorSession:
    def __init__(self, colors: dict[str, str], resident_mode: bool = False) -> None:
        self.colors = colors
        self.resident_mode = resident_mode
        self.active = False
        self.buffers: list[EditorBuffer] = []
        self.current = 0

    def open(self, term: Terminal, path: Path, readonly: bool, start_line: int | None = None) -> bool:
        self.active = True
        current_ref = [self.current]
        saved = text_editor(term, path, readonly, self.colors, self.buffers, current_ref, start_line, self.resident_mode)
        self.current = current_ref[0]
        self.active = False
        return saved

    def has_buffers(self) -> bool:
        return bool(self.buffers)

    def has_dirty_buffers(self) -> bool:
        return any(buffer.dirty for buffer in self.buffers)

    def reopen(self, term: Terminal) -> bool:
        if not self.buffers:
            return False
        self.active = True
        current_ref = [self.current]
        buffer = self.buffers[self.current]
        saved = text_editor(term, buffer.path, buffer.readonly, self.colors, self.buffers, current_ref, resident_mode=self.resident_mode)
        self.current = current_ref[0]
        self.active = False
        return saved


class App:
    def __init__(self, filer: FilerApp, editor: EditorSession | None = None, resident_mode: bool = False) -> None:
        self.filer = filer
        self.filer.return_editor_requests = True
        self.filer.resident_mode = resident_mode
        self.editor = editor if editor is not None else EditorSession(filer.config.colors, resident_mode)
        self.editor.resident_mode = resident_mode
        self.resident_mode = resident_mode
        self.view = "filer"

    def run(self) -> None:
        with Terminal() as term:
            self.filer.refresh_all(True)
            dirty = True
            while self.filer.running:
                if self.view == "filer":
                    self.filer.buffer_count = len(self.editor.buffers)
                    if dirty:
                        self.filer.draw(term)
                        dirty = False
                    key = read_key_timeout(0.1)
                    if not key and self.filer.git_tree_auto_detail_due():
                        self.filer.request_git_tree_detail(auto=True)
                        dirty = True
                        continue
                    if not key:
                        dirty = self.filer.poll_log_tail(term) or dirty
                        dirty = self.filer.idle_watch_tick() or dirty
                        continue
                    self.filer.note_input_activity()
                    if key == KEY_F12 and self.editor.has_buffers():
                        saved = self.editor.reopen(term)
                        term.clear()
                        self.filer.buffer_count = len(self.editor.buffers)
                        self.filer.status = "saved" if saved else "edit canceled"
                        self.filer.refresh_all()
                        dirty = True
                        continue
                    self.filer.handle_key(term, key)
                    dirty = True
                    if not self.resident_mode and not self.filer.running and self.editor.has_dirty_buffers():
                        if not self.filer.confirm_key(term, "Unsaved buffers. Quit? y/N"):
                            self.filer.running = True
                            self.filer.status = "quit canceled"
                            dirty = True
                            continue
                    if self.filer.editor_request is not None:
                        path, readonly, start_line = self.filer.editor_request
                        self.filer.editor_request = None
                        saved = self.editor.open(term, path, readonly, start_line)
                        term.clear()
                        self.filer.buffer_count = len(self.editor.buffers)
                        self.filer.status = "saved" if saved else "edit canceled"
                        self.filer.refresh_all()
                        dirty = True
            self.filer.stop_watchers()
            save_stat(self.filer.filer_stat())


def list_entries(cwd: Path, filter_text: str, hide_empty_directories: bool = False) -> list[Entry]:
    entries: list[Entry] = []
    directory_has_file_cache: dict[Path, bool] = {}
    for child in cwd.iterdir():
        if not match_filter(child.name, filter_text):
            continue
        try:
            stat = child.stat()
        except OSError:
            continue
        if hide_empty_directories and child.is_dir() and not directory_has_file(child, directory_has_file_cache):
            continue
        entries.append(Entry(child, child.name, child.is_dir(), stat.st_size, mtime=stat.st_mtime))
    return entries


def directory_has_file(path: Path, cache: dict[Path, bool], visiting: set[Path] | None = None) -> bool:
    cached = cache.get(path)
    if cached is not None:
        return cached
    if visiting is None:
        visiting = set()
    try:
        resolved = path.resolve()
    except OSError:
        return True
    if resolved in visiting:
        return False
    visiting.add(resolved)
    try:
        children = list(path.iterdir())
    except OSError:
        visiting.discard(resolved)
        return True
    for child in children:
        try:
            if child.is_file():
                cache[path] = True
                visiting.discard(resolved)
                return True
        except OSError:
            continue
    for child in children:
        try:
            if child.is_dir() and directory_has_file(child, cache, visiting):
                cache[path] = True
                visiting.discard(resolved)
                return True
        except OSError:
            continue
    cache[path] = False
    visiting.discard(resolved)
    return False


def list_compare_entries(left: Path | None, right: Path | None, left_zip: Path | None = None, left_zip_dir: str = "", right_zip: Path | None = None, right_zip_dir: str = "") -> list[Entry]:
    if left is None or right is None:
        return []
    left_items = zip_recursive_map(left_zip, left_zip_dir) if left_zip is not None else real_recursive_map(left)
    right_items = zip_recursive_map(right_zip, right_zip_dir) if right_zip is not None else real_recursive_map(right)
    rows: list[Entry] = []
    for rel in sorted(set(left_items) | set(right_items), key=str.lower):
        lp = left_items.get(rel)
        rp = right_items.get(rel)
        if lp is None and rp is not None:
            rows.append(compare_entry(rel, "R", None, rp))
            continue
        if rp is None and lp is not None:
            rows.append(compare_entry(rel, "L", lp, None))
            continue
        if lp is None or rp is None:
            continue
        if lp.is_dir or rp.is_dir:
            if lp.is_dir != rp.is_dir:
                rows.append(compare_entry(rel, "M type", lp, rp))
            continue
        if lp.size != rp.size:
            rows.append(compare_entry(rel, "M size", lp, rp))
            continue
        lhash = compare_source_sha256(lp)
        rhash = compare_source_sha256(rp)
        if lhash and rhash and lhash != rhash:
            rows.append(compare_entry(rel, "M hash", lp, rp))
            continue
        if int(lp.mtime) != int(rp.mtime):
            rows.append(compare_entry(rel, "M time", lp, rp))
    return rows


def list_duplex_entries(root: Path) -> list[Entry]:
    if not root.is_dir():
        return []
    by_size: dict[int, list[Path]] = {}
    for path in walk_duplex_files(root):
        try:
            stat_result = path.stat()
        except OSError:
            continue
        if stat_result.st_size <= 0:
            continue
        by_size.setdefault(stat_result.st_size, []).append(path)
    rows: list[Entry] = []
    for _size, paths in sorted(by_size.items(), key=lambda item: item[0]):
        if len(paths) < 2:
            continue
        by_hash: dict[str, list[Path]] = {}
        for path in sorted(paths, key=lambda item: str(item).lower()):
            digest = file_sha256(path)
            if digest:
                by_hash.setdefault(digest, []).append(path)
        for duplicates in by_hash.values():
            if len(duplicates) < 2:
                continue
            for path in duplicates[1:]:
                try:
                    stat_result = path.stat()
                    name = "/" + path.relative_to(root).as_posix()
                    rows.append(Entry(path, name, False, stat_result.st_size, mtime=stat_result.st_mtime, search_text="DUP"))
                except (OSError, ValueError):
                    continue
    return sorted(rows, key=lambda entry: entry.name.lower())


def walk_duplex_files(root: Path) -> Iterable[Path]:
    skip_dirs = {".git", "__pycache__"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in skip_dirs]
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                if path.is_file():
                    yield path
            except OSError:
                continue


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def real_recursive_map(base: Path) -> dict[str, Entry]:
    rows: dict[str, Entry] = {}
    try:
        iterator = os.walk(base)
    except OSError:
        return rows
    for root, dirs, files in iterator:
        dirs[:] = [name for name in dirs if name != ".git"]
        root_path = Path(root)
        for name in dirs:
            path = root_path / name
            add_real_compare_entry(rows, base, path)
        for name in files:
            path = root_path / name
            add_real_compare_entry(rows, base, path)
    return rows


def add_real_compare_entry(rows: dict[str, Entry], base: Path, path: Path) -> None:
    try:
        stat = path.stat()
        rel = path.relative_to(base).as_posix()
        rows[rel] = Entry(path, rel, path.is_dir(), stat.st_size, mtime=stat.st_mtime)
    except OSError:
        return


def zip_recursive_map(zip_path: Path, zip_dir: str) -> dict[str, Entry]:
    if is_tar_archive_path(zip_path):
        return tar_recursive_map(zip_path, zip_dir)
    rows: dict[str, Entry] = {}
    prefix = normalize_zip_dir(zip_dir)
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                raw_name = info.filename
                name = normalize_zip_name(raw_name)
                if not name or name == prefix or not name.startswith(prefix):
                    continue
                rest = name[len(prefix):].strip("/")
                if not rest:
                    continue
                parts = rest.split("/")
                for index in range(1, len(parts)):
                    rel = "/".join(parts[:index])
                    zip_name = zip_actual_prefix_for_logical(raw_name, prefix + rel + "/")
                    rows.setdefault(rel, Entry(zip_path, rel, True, 0, zip_path, zip_name, zip_info_mtime(info)))
                rel = "/".join(parts)
                is_dir = info.is_dir()
                zip_name = raw_name if not is_dir else zip_actual_prefix_for_logical(raw_name, name)
                size = 0 if is_dir else info.file_size
                old = rows.get(rel)
                if old is None or (old.is_dir and not is_dir):
                    rows[rel] = Entry(zip_path, rel, is_dir, size, zip_path, zip_name, zip_info_mtime(info))
    except (OSError, zipfile.BadZipFile):
        return {}
    return rows


def tar_recursive_map(tar_path: Path, tar_dir: str) -> dict[str, Entry]:
    rows: dict[str, Entry] = {}
    prefix = normalize_zip_dir(tar_dir)
    try:
        with tarfile.open(tar_path, "r:*") as archive:
            for info in archive.getmembers():
                raw_name = info.name
                name = normalize_tar_name(raw_name)
                if not name or name == prefix.rstrip("/") or not name.startswith(prefix):
                    continue
                rest = name[len(prefix):].strip("/")
                if not rest:
                    continue
                parts = rest.split("/")
                for index in range(1, len(parts)):
                    rel = "/".join(parts[:index])
                    rows.setdefault(rel, Entry(tar_path, rel, True, 0, tar_path, prefix + rel + "/", tar_info_mtime(info)))
                rel = "/".join(parts)
                is_dir = info.isdir()
                tar_name = raw_name if not is_dir else normalize_zip_dir(name)
                size = 0 if is_dir else info.size
                old = rows.get(rel)
                if old is None or (old.is_dir and not is_dir):
                    rows[rel] = Entry(tar_path, rel, is_dir, size, tar_path, tar_name, tar_info_mtime(info))
    except (OSError, tarfile.TarError):
        return {}
    return rows


def compare_entry(name: str, code: str, left: Entry | None, right: Entry | None) -> Entry:
    source = left or right
    if source is None:
        return Entry(Path("."), name, False, 0, search_text=code)
    return Entry(
        source.path,
        name,
        source.is_dir,
        source.size,
        source.zip_path,
        source.zip_name,
        source.mtime,
        search_text=code,
        compare_left_path=left.path if left is not None else None,
        compare_left_zip_name=(left.zip_name or "") if left is not None else "",
        compare_left_is_dir=left.is_dir if left is not None else False,
        compare_left_size=left.size if left is not None else 0,
        compare_left_mtime=left.mtime if left is not None else 0.0,
        compare_right_path=right.path if right is not None else None,
        compare_right_zip_name=(right.zip_name or "") if right is not None else "",
        compare_right_is_dir=right.is_dir if right is not None else False,
        compare_right_size=right.size if right is not None else 0,
        compare_right_mtime=right.mtime if right is not None else 0.0,
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def compare_source_bytes(entry: Entry) -> bytes | None:
    if entry.zip_path is not None and entry.zip_name:
        try:
            return archive_read_bytes(entry.zip_path, entry.zip_name)
        except ARCHIVE_READ_ERRORS:
            return None
    try:
        return entry.path.read_bytes()
    except OSError:
        return None


def compare_source_sha256(entry: Entry) -> str:
    data = compare_source_bytes(entry)
    return hashlib.sha256(data).hexdigest() if data is not None else ""


def re_compile(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ValueError(str(exc)) from exc


def list_search_entries(cwd: Path, pattern: str) -> list[Entry]:
    if not pattern:
        return []
    try:
        regex = re_compile(pattern)
    except ValueError:
        return []
    rows: list[Entry] = []
    for path in walk_search_files(cwd):
        try:
            stat = path.stat()
            with path.open("rb") as handle:
                sample = handle.read(4096)
                if b"\x00" in sample:
                    continue
                handle.seek(0)
                matched = False
                for line_no, raw in enumerate(handle, 1):
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    match = regex.search(line)
                    if match is None:
                        continue
                    if not matched:
                        rows.append(Entry(path, "/" + path.relative_to(cwd).as_posix(), False, stat.st_size, mtime=stat.st_mtime))
                        matched = True
                    line_display = line.lstrip(" \t")
                    shown_line = line_display[:SEARCH_LINE_LIMIT] + ("..." if len(line_display) > SEARCH_LINE_LIMIT else "")
                    rows.append(Entry(path, f"  {line_no}: {shown_line}", False, stat.st_size, mtime=stat.st_mtime, search_line=line_no, search_text=line, search_match=match.group(0)))
                    if len(rows) >= SEARCH_MAX_ROWS:
                        return rows
        except OSError:
            continue
    return rows


def list_filename_search_entries(cwd: Path, pattern: str) -> list[Entry]:
    if not pattern:
        return []
    try:
        regex = re_compile(pattern)
    except ValueError:
        return []
    rows: list[Entry] = []
    for path in walk_search_names(cwd):
        if regex.search(path.name) is None:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        name = "/" + path.relative_to(cwd).as_posix()
        rows.append(Entry(path, name, path.is_dir(), stat.st_size, mtime=stat.st_mtime, search_match=path.name))
    return rows


def git_root(cwd: Path) -> Path | None:
    key = stable_path_text(cwd)
    if key in GIT_ROOT_CACHE:
        return GIT_ROOT_CACHE[key]
    try:
        current = cwd.resolve()
    except OSError:
        current = cwd
    while True:
        git_marker = current / ".git"
        if git_marker.is_dir() or git_marker.is_file():
            GIT_ROOT_CACHE[key] = current
            return current
        if current.parent == current:
            break
        current = current.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        GIT_ROOT_CACHE[key] = None
        return None
    text = result.stdout.strip()
    root = Path(text) if text else None
    GIT_ROOT_CACHE[key] = root
    return root


def git_rel_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def git_add_command(root: Path, entries: list[Entry]) -> tuple[str, int]:
    rels: list[str] = []
    try:
        root_resolved = root.resolve()
    except OSError:
        root_resolved = root
    for entry in entries:
        if entry.zip_path is not None:
            continue
        try:
            rel = entry.path.resolve().relative_to(root_resolved).as_posix()
        except (OSError, ValueError):
            continue
        if rel and rel not in rels:
            rels.append(rel)
    if not rels:
        return "", 0
    command = "git -C " + quote_path(root) + " add -- " + " ".join(quote_path(rel) for rel in rels)
    return command, len(rels)


def git_unmanage_command(root: Path, entries: list[Entry]) -> tuple[str, int]:
    rels: list[str] = []
    try:
        root_resolved = root.resolve()
    except OSError:
        root_resolved = root
    for entry in entries:
        if entry.zip_path is not None:
            continue
        rel = entry.search_match
        if not rel:
            try:
                rel = entry.path.resolve().relative_to(root_resolved).as_posix()
            except (OSError, ValueError):
                continue
        if rel and rel not in rels:
            rels.append(rel)
    if not rels:
        return "", 0
    command = "git -C " + quote_path(root) + " rm --cached -f -- " + " ".join(quote_path(rel) for rel in rels)
    return command, len(rels)


def git_discard_plan(root: Path, entries: list[Entry]) -> tuple[str, int, list[Path]]:
    tracked: list[str] = []
    untracked: list[Path] = []
    for entry in entries:
        if entry.zip_path is not None:
            continue
        rel = git_entry_rel(root, entry)
        if not rel:
            continue
        if entry.search_text == "??":
            path = root / rel
            if path not in untracked:
                untracked.append(path)
        elif rel not in tracked:
            tracked.append(rel)
    command = ""
    if tracked:
        command = "git -C " + quote_path(root) + " restore --staged --worktree -- " + " ".join(quote_path(rel) for rel in tracked)
    return command, len(tracked) + len(untracked), untracked


def git_entry_rel(root: Path, entry: Entry) -> str:
    if entry.search_match:
        return entry.search_match
    try:
        return entry.path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return entry.name


def list_git_history_entries(cwd: Path, path: Path | None) -> list[Entry]:
    if path is None:
        return []
    root = git_root(cwd)
    if root is None:
        return []
    rel = git_rel_path(root, path)
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%H%x00%ct%x00%s", "--", rel],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    rows: list[Entry] = []
    try:
        stat = path.stat()
        current_time = stat.st_mtime
    except OSError:
        current_time = time.time()
    rows.append(Entry(path, "---------------------- 現在", False, 0, mtime=current_time, search_text="WORKTREE"))
    for line in decode_process_output(result.stdout).splitlines():
        parts = line.split("\0", 2)
        if len(parts) != 3:
            continue
        commit, stamp_text, subject = parts
        try:
            stamp = int(stamp_text)
        except ValueError:
            stamp = 0
        title = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stamp)) + " " + subject
        rows.append(Entry(path, title, False, 0, mtime=float(stamp), search_text=commit))
    return rows


def list_git_managed_entries(cwd: Path) -> list[Entry]:
    root = git_root(cwd)
    if root is None:
        return []
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return git_managed_entries_from_bytes(root, result.stdout)


def git_managed_entries_from_bytes(root: Path, data: bytes) -> list[Entry]:
    rows: list[Entry] = []
    for raw in data.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="replace")
        path = root / rel
        try:
            stat = path.stat()
            size = stat.st_size
            mtime = stat.st_mtime
            is_dir = path.is_dir()
        except OSError:
            size = 0
            mtime = 0.0
            is_dir = False
        rows.append(Entry(path, rel, is_dir, size, mtime=mtime, search_text="T ", search_match=rel))
    return rows


def list_git_status_entries(cwd: Path, unmanaged_only: bool = False) -> list[Entry]:
    root = git_root(cwd)
    if root is None:
        return []
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return git_status_entries_from_text(root, decode_process_output(result.stdout), unmanaged_only)


def git_status_entries_from_text(root: Path, text: str, unmanaged_only: bool = False) -> list[Entry]:
    rows: list[Entry] = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        if unmanaged_only and code != "??":
            continue
        name = line[3:]
        if " -> " in name:
            name = name.rsplit(" -> ", 1)[1]
        path = root / name
        try:
            stat = path.stat()
            size = stat.st_size
            mtime = stat.st_mtime
            is_dir = path.is_dir()
        except OSError:
            size = 0
            mtime = 0.0
            is_dir = False
        rows.append(Entry(path, name, is_dir, size, mtime=mtime, search_text=code, search_match=name))
    return rows


def list_git_branch_items(root: Path, merge_mode: bool = False) -> list[CommandItem]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "branch", "--all", "--format=%(HEAD)%00%(refname:short)%00%(upstream:short)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    items: list[CommandItem] = []
    seen: set[str] = set()
    for line in decode_process_output(result.stdout).splitlines():
        parts = line.split("\0")
        if len(parts) != 3:
            continue
        head, name, upstream = parts
        if not name or name.endswith("/HEAD") or name in seen:
            continue
        seen.add(name)
        current = head.strip() == "*"
        remote = name.startswith("remotes/")
        display = name[8:] if remote else name
        prefix = "* " if current else "  "
        suffix = "  remote" if remote else (f"  -> {upstream}" if upstream else "")
        command = "" if current else git_branch_command(name, remote, merge_mode)
        items.append(CommandItem(prefix + display + suffix, command, current))
    return items


def git_branch_command(name: str, remote: bool, merge_mode: bool = False) -> str:
    if remote:
        remote_name = name[8:]
        return "git merge " + quote_path(remote_name) if merge_mode else "git checkout --track " + quote_path(remote_name)
    if merge_mode:
        return "git merge " + quote_path(name)
    return "git checkout " + quote_path(name)


def list_git_commit_file_entries(cwd: Path, commit: str) -> list[Entry]:
    root = git_root(cwd)
    if root is None or not commit:
        return []
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff-tree", "--root", "--no-commit-id", "--name-status", "-r", commit],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    rows: list[Entry] = []
    for line in decode_process_output(result.stdout).splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0]
        name = parts[-1]
        path = root / name
        rows.append(Entry(path, name, False, 0, search_text=code, search_match=commit))
    return rows


def list_git_tree_entries(cwd: Path, scope: str = "all", show_commit: bool = True, relative_time: bool = False) -> list[Entry]:
    root = git_root(cwd)
    if root is None:
        return []
    refs = git_tree_ref_args(scope)
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--topo-order", "--parents", *refs, "--decorate=short", "--date=format:%y-%m-%d %H:%M", "--pretty=format:%H%x00%P%x00%h%x00%ad%x00%ct%x00%s%x00%d", "--max-count=500"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    commits = parse_git_tree_commits(decode_process_output(result.stdout))
    return render_git_tree_entries(root, commits, show_commit, relative_time)


def git_tree_ref_args(scope: str) -> list[str]:
    if scope == "local":
        return ["--branches", "--tags"]
    if scope == "remote":
        return ["--remotes"]
    return ["--branches", "--remotes", "--tags"]


def parse_git_tree_commits(text: str) -> list[GitTreeCommit]:
    commits: list[GitTreeCommit] = []
    for line in text.splitlines():
        parts = line.split("\0")
        if len(parts) == 7:
            commit, parents_text, short, stamp, epoch_text, subject, refs = parts
        elif len(parts) == 6:
            commit, parents_text, short, stamp, subject, refs = parts
            epoch_text = "0"
        else:
            continue
        parents = [part for part in parents_text.split() if part]
        try:
            epoch = int(epoch_text)
        except ValueError:
            epoch = 0
        commits.append(GitTreeCommit(commit, parents, short, stamp, epoch, subject, refs))
    return commits


def render_git_tree_entries(root: Path, commits: list[GitTreeCommit], show_commit: bool = True, relative_time: bool = False) -> list[Entry]:
    rows: list[Entry] = []
    lanes: list[str] = []
    for item in commits:
        if item.commit in lanes:
            lane = lanes.index(item.commit)
        else:
            lane = len(lanes)
            lanes.append(item.commit)
        duplicate_lanes = [index for index, value in enumerate(lanes) if index != lane and value == item.commit]
        graph = render_git_tree_graph(lanes, lane, item, duplicate_lanes)
        rows.append(Entry(root, graph + git_tree_commit_text(item, show_commit, relative_time), False, 0, search_text=item.commit, search_match=item.short))
        lanes[lane:lane + 1] = item.parents[:1] or []
        insert_at = lane + 1
        for parent in item.parents[1:]:
            if parent not in lanes:
                lanes.insert(insert_at, parent)
                insert_at += 1
        for index in sorted(duplicate_lanes, reverse=True):
            if 0 <= index < len(lanes):
                del lanes[index]
    return rows


def render_git_tree_graph(lanes: list[str], lane: int, item: GitTreeCommit, duplicate_lanes: list[int]) -> str:
    if not lanes:
        return ""
    head = "(HEAD" in item.refs
    bullet = "○" if head else "●"
    merge = len(item.parents) > 1
    collapse = bool(duplicate_lanes)
    crossing = collapse and any(index not in duplicate_lanes for index in range(lane + 1, len(lanes)))
    cells: list[str] = []
    for index, value in enumerate(lanes):
        if index in duplicate_lanes:
            continue
        if crossing and index > lane:
            continue
        if index == lane:
            if merge:
                cells.append(bullet + "─╮")
            elif crossing:
                cells.append(bullet + "─┼─╯")
            elif collapse:
                cells.append(bullet + "─╯")
            else:
                cells.append(bullet)
        else:
            cells.append("│")
    return " ".join(cells) + " "


def git_tree_commit_text(item: GitTreeCommit, show_commit: bool = True, relative_time: bool = False) -> str:
    suffix = f" {item.refs}" if item.refs else ""
    stamp = relative_time_text(item.epoch) if relative_time else item.stamp
    prefix = f"{item.short} " if show_commit else ""
    return f"{prefix}{stamp} {item.subject}{suffix}"


def relative_time_text(epoch: int) -> str:
    if epoch <= 0:
        return "0分前"
    seconds = max(0, int(time.time()) - epoch)
    if seconds < 3600:
        return f"{seconds // 60}分前"
    if seconds < 86400:
        return f"{seconds // 3600}時間前"
    return f"{seconds // 86400}日前"


def decode_process_output(data: bytes | str) -> str:
    if isinstance(data, str):
        return data
    candidates = ["utf-8", locale.getpreferredencoding(False)]
    if IS_WINDOWS:
        candidates.extend(["cp932", "mbcs"])
    seen: set[str] = set()
    for encoding in candidates:
        if not encoding or encoding.lower() in seen:
            continue
        seen.add(encoding.lower())
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def clear_git_cache() -> None:
    GIT_ROOT_CACHE.clear()
    GIT_BLOB_CACHE.clear()
    GIT_COMMIT_DETAIL_CACHE.clear()
    GIT_DIFF_TEXT_CACHE.clear()
    GIT_DIFF_RENDER_CACHE.clear()


def git_graph_commit_hash(line: str) -> str:
    for part in line.replace("\0", " ").split():
        if len(part) >= 7 and all(ch in "0123456789abcdefABCDEF" for ch in part):
            return part
    return ""


def git_graph_add_branch_start(text: str) -> str:
    for bullet in ("●", "○"):
        pos = text.rfind(bullet)
        if pos >= 0 and not text[pos:].startswith(bullet + "─"):
            return text[:pos] + bullet + "─╮" + text[pos + 1:]
    return text


def pretty_git_graph_line(line: str) -> str:
    line = line.replace("\0", " ")
    commit_at = git_graph_commit_pos(line)
    if commit_at < 0:
        return pretty_git_graph_part(line)
    graph = pretty_git_graph_part(line[:commit_at], "(HEAD" in line)
    return graph + line[commit_at:]


def git_graph_connector_line(line: str, extra_lane: bool) -> str:
    graph = line.replace("\0", " ").strip()
    bars = graph.count("|")
    lanes = bars + (1 if extra_lane else 0)
    if lanes <= 0:
        return ""
    return " ".join("│" for _ in range(lanes))


def git_graph_commit_pos(line: str) -> int:
    for index in range(max(0, len(line) - 6)):
        part = line[index:index + 7]
        if all(ch in "0123456789abcdefABCDEF" for ch in part):
            before = line[index - 1] if index else " "
            if before in " *|/\\_-.()":
                return index
    return -1


def pretty_git_graph_part(graph: str, head: bool = False) -> str:
    graph = graph.rstrip()
    if not graph:
        return ""
    chars = list(graph)
    out: list[str] = []
    for index, ch in enumerate(chars):
        if ch == "*":
            bullet = "○" if head else "●"
            tail = chars[index + 1:]
            if "/" in tail or "|" in tail:
                out.append(bullet + "─╯")
            elif any(item in tail for item in (".", "-")):
                out.append(bullet + "─")
            else:
                out.append(bullet)
        elif ch == "|":
            out.append("│")
        elif ch == "/":
            out.append("╯")
        elif ch == "\\":
            out.append("╯")
        elif ch == ".":
            out.append("╯")
        elif ch in "_-":
            if out and out[-1].endswith("─"):
                continue
            out.append("─")
        elif ch == " ":
            if out and out[-1].endswith("─"):
                continue
            out.append(" ")
        else:
            out.append(ch)
    rendered = "".join(out).rstrip()
    rendered = rendered.replace("│╯", "╯")
    rendered = rendered.replace("●─╯╯", "●─╯")
    rendered = rendered.replace("○─╯╯", "○─╯")
    rendered = rendered.replace("●─╯ ╯", "●─╯")
    rendered = rendered.replace("○─╯ ╯", "○─╯")
    rendered = rendered.replace("●─╯ │", "●─╯")
    rendered = rendered.replace("○─╯ │", "○─╯")
    rendered = rendered.replace("●─ ╯", "●─╯")
    rendered = rendered.replace("○─ ╯", "○─╯")
    return rendered + (" " if rendered else "")


def color_git_graph_row(row: str) -> str:
    out = []
    colors = ["94", "35", "33", "32", "36", "31"]
    graph = "●○│─╮╯┼ "
    lane = 0
    stop = 0
    in_cell = False
    for stop, ch in enumerate(row):
        if ch in "●○│─╮╯┼":
            out.append(color_text(ch, colors[lane % len(colors)]))
            in_cell = True
        elif ch in graph:
            out.append(ch)
            if in_cell and ch == " ":
                lane += 1
                in_cell = False
        else:
            break
    else:
        return "".join(out)
    out.append(row[stop:])
    return "".join(out)


def git_commit_detail_rows(cwd: Path, commit: str, width: int) -> list[str]:
    if not commit:
        return ["[commit not found]"]
    root = git_root(cwd)
    if root is None:
        return ["[git repository not found]"]
    key = (stable_path_text(root), commit)
    if key in GIT_COMMIT_DETAIL_CACHE:
        rows = GIT_COMMIT_DETAIL_CACHE[key]
        return ["[git show failed]"] if rows is None else [fit(row, width) for row in rows]
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", "--stat", "--decorate", "--date=short", "--format=fuller", commit],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return ["[git show failed]"]
    if result.returncode != 0:
        GIT_COMMIT_DETAIL_CACHE[key] = None
        return ["[git show failed]"]
    rows = decode_process_output(result.stdout).splitlines()
    GIT_COMMIT_DETAIL_CACHE[key] = rows
    return [fit(row, width) for row in rows]


def git_commit_detail_cached(cwd: Path, commit: str) -> bool:
    root = git_root(cwd)
    if root is None or not commit:
        return False
    return (stable_path_text(root), commit) in GIT_COMMIT_DETAIL_CACHE


def git_tree_light_preview_rows(entry: Entry, width: int) -> list[str]:
    row = re.sub("\x1b\\[[0-9;]*m", "", entry.name).strip()
    rows = [
        "git tree preview",
        "",
        f"commit: {entry.search_text}",
        f"short : {entry.search_match}",
        f"line  : {row}",
        "",
        "Right: git show --stat now",
        "Idle 1s: git show --stat auto",
    ]
    return [fit(item, width) for item in rows]


def git_file_bytes(cwd: Path, path: Path | None, commit: str) -> bytes | None:
    if path is None or not commit:
        return None
    if commit == "WORKTREE":
        try:
            return path.read_bytes()
        except OSError:
            return None
    root = git_root(cwd)
    if root is None:
        return None
    rel = git_rel_path(root, path)
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"{commit}:{rel}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def git_file_at_rows(cwd: Path, path: Path | None, commit: str, line_numbers: bool, width: int, wrap: bool, limit: int) -> list[str]:
    data = git_file_bytes(cwd, path, commit)
    if data is None:
        return ["[git show failed]"]
    if b"\x00" in data[:4096]:
        return ["[binary]"]
    rows = preview_body_lines(data.decode("utf-8", errors="replace").splitlines(), line_numbers, width, wrap)
    return rows[:limit]


def git_file_diff_rows(cwd: Path, path: Path | None, newer: str, older: str, width: int) -> list[str]:
    root = git_root(cwd)
    render_key = None
    if root is not None and path is not None:
        rel = git_rel_path(root, path)
        stat_key = file_stat_key(path) if newer == "WORKTREE" or older == "WORKTREE" else None
        render_key = ("history-file-render", stable_path_text(root), rel, newer, older, stat_key, width)
        cached = GIT_DIFF_RENDER_CACHE.get(render_key)
        if cached is not None:
            return cached[:]
    rows = git_file_diff_text_rows(cwd, path, newer, older)
    out = render_diff_rows(rows, width)
    if render_key is not None:
        GIT_DIFF_RENDER_CACHE[render_key] = out[:]
    return out


def git_status_diff_rows(cwd: Path, path: Path, code: str, width: int) -> list[str]:
    root = git_root(cwd)
    render_key = None
    if root is not None:
        rel = git_rel_path(root, path)
        render_key = ("status-render", stable_path_text(root), rel, code, file_stat_key(path), width)
        cached = GIT_DIFF_RENDER_CACHE.get(render_key)
        if cached is not None:
            return cached[:]
    rows = git_status_diff_text_rows(cwd, path, code)
    out = render_diff_rows(rows, width)
    if render_key is not None:
        GIT_DIFF_RENDER_CACHE[render_key] = out[:]
    return out


def git_commit_file_diff_rows(cwd: Path, commit: str, path: Path, width: int) -> list[str]:
    root = git_root(cwd)
    render_key = None
    if root is not None:
        rel = git_rel_path(root, path)
        parent = git_first_parent(cwd, commit)
        render_key = ("commit-file-render", stable_path_text(root), commit, parent, rel, width)
        cached = GIT_DIFF_RENDER_CACHE.get(render_key)
        if cached is not None:
            return cached[:]
    rows = git_commit_file_diff_text_rows(cwd, commit, path)
    out = render_diff_rows(rows, width)
    if render_key is not None:
        GIT_DIFF_RENDER_CACHE[render_key] = out[:]
    return out


def compare_preview_rows(entry: Entry, width: int) -> list[str]:
    code = entry.search_text
    left = compare_side_entry(entry, "left")
    right = compare_side_entry(entry, "right")
    if code == "L":
        return compare_single_side_rows(left, "left pane", width)
    if code == "R":
        return compare_single_side_rows(right, "right pane", width)
    if left is None or right is None:
        return ["[compare failed]"]
    if left.is_dir or right.is_dir:
        return compare_detail_rows(code, left, right, width)
    if code == "M time":
        return compare_detail_rows("same content / time differs", left, right, width)
    cache_key = compare_diff_cache_key(left, right)
    render_key = (*cache_key, width)
    if render_key in COMPARE_DIFF_RENDER_CACHE:
        return COMPARE_DIFF_RENDER_CACHE[render_key][:]
    if cache_key in COMPARE_DIFF_TEXT_CACHE:
        rendered = render_diff_rows(COMPARE_DIFF_TEXT_CACHE[cache_key], width)
        COMPARE_DIFF_RENDER_CACHE[render_key] = rendered[:]
        return rendered
    left_data = compare_source_bytes(left)
    right_data = compare_source_bytes(right)
    if left_data is None or right_data is None:
        return ["[compare failed]"]
    if b"\x00" in left_data[:4096] or b"\x00" in right_data[:4096]:
        rows = compare_detail_rows("[binary differs]", left, right, width)
        rows.append(fit(f"left sha256 : {compare_source_sha256(left)}", width))
        rows.append(fit(f"right sha256: {compare_source_sha256(right)}", width))
        return rows
    left_lines = left_data.decode("utf-8", errors="replace").splitlines()
    right_lines = right_data.decode("utf-8", errors="replace").splitlines()
    try:
        diff_rows = compare_diff_text_rows(left, right, left_lines, right_lines)
    except OperationCanceled:
        return [fit("[canceled]", width)]
    rows = ["diff: left -> right", ""] + (diff_rows or ["[no diff]"])
    COMPARE_DIFF_TEXT_CACHE[cache_key] = rows[:]
    rendered = render_diff_rows(rows, width)
    COMPARE_DIFF_RENDER_CACHE[render_key] = rendered[:]
    return rendered


def compare_single_side_rows(entry: Entry | None, side: str, width: int) -> list[str]:
    if entry is None:
        return ["[compare failed]"]
    return [
        fit("", width),
        fit(f"{compare_entry_path(entry)} exists only in {side}.", width),
    ]


def compare_side_entry(entry: Entry, side: str) -> Entry | None:
    if side == "left":
        path = entry.compare_left_path
        if path is None:
            return None
        zip_name = entry.compare_left_zip_name
        return Entry(path, entry.name, entry.compare_left_is_dir, entry.compare_left_size, path if zip_name else None, zip_name or None, entry.compare_left_mtime)
    path = entry.compare_right_path
    if path is None:
        return None
    zip_name = entry.compare_right_zip_name
    return Entry(path, entry.name, entry.compare_right_is_dir, entry.compare_right_size, path if zip_name else None, zip_name or None, entry.compare_right_mtime)


def compare_detail_rows(title: str, left: Entry | None, right: Entry | None, width: int) -> list[str]:
    rows = [title, ""]
    if left is not None:
        rows.append("left : " + compare_side_detail(left))
    if right is not None:
        rows.append("right: " + compare_side_detail(right))
    return [fit(row, width) for row in rows]


def compare_side_detail(entry: Entry) -> str:
    if entry.zip_path is not None and entry.zip_name:
        return f"{fmt_size(entry.size, entry.is_dir)} {short_datetime(entry.mtime)} {entry.zip_path}/{entry.zip_name}"
    return path_detail(entry.path)


def compare_entry_path(entry: Entry) -> str:
    if entry.zip_path is not None and entry.zip_name:
        return f"{entry.zip_path}/{entry.zip_name}"
    return str(entry.path)


def compare_diff_cache_key(left: Entry, right: Entry) -> tuple[object, ...]:
    return ("compare", compare_entry_identity(left), compare_entry_identity(right))


def compare_entry_identity(entry: Entry) -> tuple[object, ...]:
    if entry.zip_path is not None and entry.zip_name:
        return ("zip", stable_path_text(entry.zip_path), entry.zip_name, entry.size, int(entry.mtime * 1_000_000_000))
    return ("file", stable_path_text(entry.path), entry.size, int(entry.mtime * 1_000_000_000))


def compare_diff_text_rows(left: Entry, right: Entry, left_lines: list[str], right_lines: list[str]) -> list[str]:
    if not IS_WINDOWS and left.zip_path is None and right.zip_path is None:
        diff_lines = diff_command_output_lines_cancelable(left.path, right.path)
        if diff_lines is not None:
            return full_diff_rows_from_unified(right_lines, diff_lines)
    return side_diff_rows(left_lines, right_lines)


def diff_command_output_lines_cancelable(left: Path, right: Path) -> list[str] | None:
    try:
        process = subprocess.Popen(
            ["diff", "-U", str(GIT_DIFF_CONTEXT_LINES), "--", str(left), str(right)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    while process.poll() is None:
        if operation_cancel_requested():
            process.terminate()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise OperationCanceled()
        time.sleep(0.03)
    stdout, _ = process.communicate()
    if process.returncode not in (0, 1):
        return None
    return decode_process_output(stdout).splitlines()


def path_detail(path: Path) -> str:
    try:
        stat = path.stat()
        return f"{fmt_size(stat.st_size, path.is_dir())} {short_datetime(stat.st_mtime)} {path}"
    except OSError:
        return str(path)


def color_side_rows(rows: list[str], width: int) -> list[str]:
    return render_diff_rows(rows, width)


def render_diff_rows(rows: list[str], width: int) -> list[str]:
    out: list[str] = []
    for row in rows:
        if row.startswith("-"):
            out.append(color_diff_row(row, width, "37;41"))
        elif row.startswith("+"):
            out.append(color_diff_row(row, width, "30;42"))
        else:
            out.append(fit(row, width))
    return out


def color_diff_row(row: str, width: int, color: str) -> str:
    if width <= 0:
        return ""
    body_width = max(0, width - 1)
    return pad_ansi(color_text(fit(row, body_width), color), width)


def cached_git_diff_rows(key: tuple[object, ...]) -> list[str] | None:
    rows = GIT_DIFF_TEXT_CACHE.get(key)
    return rows[:] if rows is not None else None


def cache_git_diff_rows(key: tuple[object, ...], rows: list[str]) -> list[str]:
    GIT_DIFF_TEXT_CACHE[key] = rows[:]
    return rows


def file_stat_key(path: Path) -> tuple[int, int] | None:
    try:
        stat_result = path.stat()
        return stat_result.st_size, int(stat_result.st_mtime_ns)
    except OSError:
        return None


def git_diff_command_rows(root: Path, args: list[str]) -> list[str] | None:
    lines = git_diff_command_output_lines(root, args)
    return None if lines is None else parse_git_unified_diff(lines)


def git_diff_command_output_lines(root: Path, args: list[str]) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return None
    if result.returncode not in (0, 1):
        return None
    return decode_process_output(result.stdout).splitlines()


def full_diff_rows_from_unified(new_lines: list[str], diff_lines: list[str]) -> list[str]:
    additions: set[int] = set()
    deletions_before: dict[int, list[tuple[int, str]]] = {}
    old_line = 0
    new_line = 0
    changed = False
    for line in diff_lines:
        if line.startswith("@@"):
            parsed = parse_unified_hunk_header(line)
            if parsed is not None:
                old_line, new_line, _ = parsed
            continue
        if line.startswith(("diff --git ", "index ", "--- ", "+++ ", "new file mode ", "deleted file mode ", "similarity index ", "rename from ", "rename to ")):
            continue
        if line.startswith("\\"):
            continue
        if line.startswith("-"):
            changed = True
            deletions_before.setdefault(new_line, []).append((old_line, display_safe_text(line[1:])))
            old_line += 1
            continue
        if line.startswith("+"):
            changed = True
            additions.add(new_line)
            new_line += 1
            continue
        if line.startswith(" "):
            old_line += 1
            new_line += 1
    if not changed:
        return []
    rows: list[str] = []
    for index, text in enumerate(new_lines, 1):
        for old_no, deleted in deletions_before.pop(index, []):
            rows.append(f"- {old_no:>5}: {deleted}")
        prefix = "+" if index in additions else " "
        rows.append(f"{prefix} {index:>5}: {display_safe_text(text)}")
    for old_no, deleted in deletions_before.pop(len(new_lines) + 1, []):
        rows.append(f"- {old_no:>5}: {deleted}")
    for pending in sorted(deletions_before):
        for old_no, deleted in deletions_before[pending]:
            rows.append(f"- {old_no:>5}: {deleted}")
    return rows


def parse_git_unified_diff(lines: list[str]) -> list[str]:
    rows: list[str] = []
    old_line = 0
    new_line = 0
    for line in lines:
        if line.startswith(("diff --git ", "index ", "new file mode ", "deleted file mode ", "similarity index ", "rename from ", "rename to ")):
            continue
        if line.startswith("--- ") or line.startswith("+++ "):
            continue
        if line.startswith("@@"):
            parsed = parse_unified_hunk_header(line)
            if parsed is None:
                rows.append(line)
                continue
            old_line, new_line, title = parsed
            rows.append(title)
            continue
        if line.startswith("\\"):
            rows.append("  " + line)
            continue
        if line.startswith("-"):
            rows.append(f"- {old_line:>5}: {display_safe_text(line[1:])}")
            old_line += 1
            continue
        if line.startswith("+"):
            rows.append(f"+ {new_line:>5}: {display_safe_text(line[1:])}")
            new_line += 1
            continue
        if line.startswith(" "):
            rows.append(f"  {old_line:>5}: {display_safe_text(line[1:])}")
            old_line += 1
            new_line += 1
            continue
        if line:
            rows.append(line)
    return rows


def parse_unified_hunk_header(line: str) -> tuple[int, int, str] | None:
    match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)", line)
    if match is None:
        return None
    old_line = int(match.group(1))
    new_line = int(match.group(2))
    suffix = match.group(3).strip()
    title = f"@@ -{old_line} +{new_line} @@"
    if suffix:
        title += " " + display_safe_text(suffix)
    return old_line, new_line, title


def git_status_diff_text_rows(cwd: Path, path: Path, code: str) -> list[str]:
    if code == "??":
        try:
            data = path.read_bytes()
        except OSError:
            return ["[git diff failed]"]
        if b"\x00" in data[:4096]:
            return ["[binary]"]
        rows = ["diff: untracked -> working tree", ""]
        lines = data.decode("utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines[:SEARCH_MAX_ROWS], 1):
            rows.append(f"+ {index:>5}: {display_safe_text(line)}")
        if len(lines) > SEARCH_MAX_ROWS:
            rows.append(f"[truncated: {len(lines) - SEARCH_MAX_ROWS} more line(s)]")
        return rows
    root = git_root(cwd)
    if root is None:
        return ["[git diff failed]"]
    rel = git_rel_path(root, path)
    stat_key = file_stat_key(path)
    key = ("status", stable_path_text(root), rel, code, stat_key)
    cached = cached_git_diff_rows(key)
    if cached is not None:
        return cached
    old_data = git_blob_bytes(root, "HEAD", rel)
    try:
        new_data = path.read_bytes()
    except OSError:
        new_data = b""
    if old_data is None:
        return cache_git_diff_rows(key, ["[git diff failed]"])
    if b"\x00" in old_data[:4096] or b"\x00" in new_data[:4096]:
        return cache_git_diff_rows(key, ["[binary]"])
    diff_lines = git_diff_command_output_lines(root, ["diff", "--no-ext-diff", "--no-color", f"--unified={GIT_DIFF_CONTEXT_LINES}", "HEAD", "--", rel])
    if diff_lines is None:
        return cache_git_diff_rows(key, ["[git diff failed]"])
    rows = full_diff_rows_from_unified(new_data.decode("utf-8", errors="replace").splitlines(), diff_lines)
    if not rows:
        return ["[no diff]"]
    return cache_git_diff_rows(key, ["diff: HEAD -> working tree", ""] + rows)


def git_commit_file_diff_text_rows(cwd: Path, commit: str, path: Path) -> list[str]:
    root = git_root(cwd)
    if root is None:
        return ["[git diff failed]"]
    rel = git_rel_path(root, path)
    parent = git_first_parent(cwd, commit)
    key = ("commit-file", stable_path_text(root), commit, parent, rel)
    cached = cached_git_diff_rows(key)
    if cached is not None:
        return cached
    new_data = git_blob_bytes(root, commit, rel)
    if new_data is None:
        return cache_git_diff_rows(key, ["[git diff failed]"])
    old_data = git_blob_bytes(root, parent, rel) if parent else b""
    if old_data is None:
        old_data = b""
    if b"\x00" in old_data[:4096] or b"\x00" in new_data[:4096]:
        return cache_git_diff_rows(key, ["[binary]"])
    if parent:
        args = ["diff", "--no-ext-diff", "--no-color", f"--unified={GIT_DIFF_CONTEXT_LINES}", parent, commit, "--", rel]
    else:
        args = ["show", "--no-ext-diff", "--no-color", f"--unified={GIT_DIFF_CONTEXT_LINES}", "--format=", commit, "--", rel]
    diff_lines = git_diff_command_output_lines(root, args)
    if diff_lines is None:
        return cache_git_diff_rows(key, ["[git diff failed]"])
    rows = full_diff_rows_from_unified(new_data.decode("utf-8", errors="replace").splitlines(), diff_lines)
    if not rows:
        return ["[no diff]"]
    return cache_git_diff_rows(key, [f"diff: {parent[:7] if parent else 'EMPTY'} -> {commit[:7]}", ""] + rows)


def git_first_parent(cwd: Path, commit: str) -> str:
    root = git_root(cwd)
    if root is None or not commit:
        return ""
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-list", "--parents", "-n", "1", commit], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    parts = decode_process_output(result.stdout).strip().split()
    return parts[1] if len(parts) > 1 else ""


def git_blob_bytes_for_path(cwd: Path, commit: str, path: Path) -> bytes | None:
    root = git_root(cwd)
    if root is None:
        return None
    return git_blob_bytes(root, commit, git_rel_path(root, path))


def git_blob_bytes(root: Path, commit: str, rel: str) -> bytes | None:
    key = (stable_path_text(root), commit, rel)
    if key in GIT_BLOB_CACHE:
        return GIT_BLOB_CACHE[key]
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"{commit}:{rel}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        GIT_BLOB_CACHE[key] = None
        return None
    if result.returncode != 0:
        GIT_BLOB_CACHE[key] = None
        return None
    GIT_BLOB_CACHE[key] = result.stdout
    return result.stdout


def git_file_diff_text_rows(cwd: Path, path: Path | None, newer: str, older: str) -> list[str]:
    root = git_root(cwd)
    if root is not None and path is not None:
        rel = git_rel_path(root, path)
        stat_key = file_stat_key(path) if newer == "WORKTREE" or older == "WORKTREE" else None
        key = ("history-file", stable_path_text(root), rel, newer, older, stat_key)
        cached = cached_git_diff_rows(key)
        if cached is not None:
            return cached
        if newer == "WORKTREE":
            args = ["diff", "--no-ext-diff", "--no-color", f"--unified={GIT_DIFF_CONTEXT_LINES}", older, "--", rel]
        elif older == "WORKTREE":
            args = ["diff", "--no-ext-diff", "--no-color", "-R", f"--unified={GIT_DIFF_CONTEXT_LINES}", newer, "--", rel]
        else:
            args = ["diff", "--no-ext-diff", "--no-color", f"--unified={GIT_DIFF_CONTEXT_LINES}", older, newer, "--", rel]
        new_data_for_full = git_file_bytes(cwd, path, newer)
        old_data_for_full = git_file_bytes(cwd, path, older)
        diff_lines = git_diff_command_output_lines(root, args)
        if diff_lines is not None and new_data_for_full is not None and old_data_for_full is not None:
            if b"\x00" in new_data_for_full[:4096] or b"\x00" in old_data_for_full[:4096]:
                return cache_git_diff_rows(key, ["[binary]"])
            rows = full_diff_rows_from_unified(new_data_for_full.decode("utf-8", errors="replace").splitlines(), diff_lines)
            if not rows:
                return cache_git_diff_rows(key, ["[no diff]"])
            return cache_git_diff_rows(key, [f"diff: {git_label(older)} -> {git_label(newer)}", ""] + rows)
    new_data = git_file_bytes(cwd, path, newer)
    old_data = git_file_bytes(cwd, path, older)
    if new_data is None or old_data is None:
        return ["[git diff failed]"]
    if b"\x00" in new_data[:4096] or b"\x00" in old_data[:4096]:
        return ["[binary]"]
    old_lines = old_data.decode("utf-8", errors="replace").splitlines()
    new_lines = new_data.decode("utf-8", errors="replace").splitlines()
    rows = side_diff_rows(old_lines, new_lines)
    if not rows:
        return ["[no diff]"]
    return [f"diff: {git_label(older)} -> {git_label(newer)}", ""] + rows


def side_diff_rows(old_lines: list[str], new_lines: list[str]) -> list[str]:
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    rows: list[str] = []
    changed = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        raise_if_operation_canceled()
        if tag == "equal":
            rows.extend(f"  {line_no:>5}: {display_safe_text(text)}" for line_no, text in zip(range(i1 + 1, i2 + 1), old_lines[i1:i2]))
            continue
        changed = True
        if tag in ("replace", "delete"):
            rows.extend(f"- {line_no:>5}: {display_safe_text(text)}" for line_no, text in zip(range(i1 + 1, i2 + 1), old_lines[i1:i2]))
        if tag in ("replace", "insert"):
            rows.extend(f"+ {line_no:>5}: {display_safe_text(text)}" for line_no, text in zip(range(j1 + 1, j2 + 1), new_lines[j1:j2]))
    return rows if changed else []


def raise_if_operation_canceled() -> None:
    if operation_cancel_requested():
        raise OperationCanceled()


def operation_cancel_requested() -> bool:
    if IS_WINDOWS or not sys.stdin.isatty():
        return False
    try:
        if not select.select([sys.stdin.fileno()], [], [], 0)[0]:
            return False
        data = os.read(sys.stdin.fileno(), 1)
    except OSError:
        return False
    return data == b"\x03"


def diff_row_indices(rows: list[str]) -> list[int]:
    out: list[int] = []
    in_block = False
    for idx, row in enumerate(strip_ansi_rows(rows)):
        is_diff = row.startswith("+ ") or row.startswith("- ")
        if is_diff and not in_block:
            out.append(idx)
        in_block = is_diff
    return out


def git_label(commit: str) -> str:
    return "現在" if commit == "WORKTREE" else commit[:12]


def walk_search_files(cwd: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(cwd):
        dirs[:] = sorted((name for name in dirs if name not in (".git", "__pycache__")), key=str.lower)
        for name in sorted(files, key=str.lower):
            path = Path(root) / name
            if path.is_file():
                yield path


def walk_search_names(cwd: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(cwd):
        dirs[:] = sorted((name for name in dirs if name not in (".git", "__pycache__")), key=str.lower)
        for name in dirs:
            path = Path(root) / name
            if path.exists():
                yield path
        for name in sorted(files, key=str.lower):
            path = Path(root) / name
            if path.exists():
                yield path


def directory_preview_children(path: Path, limit: int) -> list[Path]:
    if limit <= 0:
        return []
    children: list[Path] = []
    try:
        for child in path.iterdir():
            children.append(child)
            if len(children) >= limit:
                break
    except OSError:
        return []
    return children


def list_zip_entries(zip_path: Path, zip_dir: str, filter_text: str) -> list[Entry]:
    if is_tar_archive_path(zip_path):
        return list_tar_entries(zip_path, zip_dir, filter_text)
    entries: dict[str, Entry] = {}
    prefix = normalize_zip_dir(zip_dir)
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                raw_name = info.filename
                name = normalize_zip_name(raw_name)
                if not name or name == prefix or not name.startswith(prefix):
                    continue
                rest = name[len(prefix):]
                if not rest:
                    continue
                part = rest.split("/", 1)[0]
                if not part:
                    continue
                is_dir = "/" in rest or info.is_dir()
                child_name = part
                child_zip_name = zip_actual_prefix_for_logical(raw_name, prefix + part + "/") if is_dir else raw_name
                if not match_filter(child_name, filter_text):
                    continue
                size = 0 if is_dir else info.file_size
                mtime = zip_info_mtime(info)
                old = entries.get(child_name)
                if old is None or (old.is_dir and not is_dir):
                    entries[child_name] = Entry(zip_path, child_name, is_dir, size, zip_path, child_zip_name, mtime)
    except (OSError, zipfile.BadZipFile):
        return []
    return list(entries.values())


def list_tar_entries(tar_path: Path, tar_dir: str, filter_text: str) -> list[Entry]:
    entries: dict[str, Entry] = {}
    prefix = normalize_zip_dir(tar_dir)
    try:
        with tarfile.open(tar_path, "r:*") as archive:
            for info in archive.getmembers():
                raw_name = info.name
                name = normalize_tar_name(raw_name)
                if not name or name == prefix.rstrip("/") or not name.startswith(prefix):
                    continue
                rest = name[len(prefix):]
                if not rest:
                    continue
                part = rest.split("/", 1)[0]
                if not part:
                    continue
                is_dir = "/" in rest or info.isdir()
                child_name = part
                child_tar_name = prefix + part + "/" if is_dir else raw_name
                if not match_filter(child_name, filter_text):
                    continue
                size = 0 if is_dir else info.size
                mtime = tar_info_mtime(info)
                old = entries.get(child_name)
                if old is None or (old.is_dir and not is_dir):
                    entries[child_name] = Entry(tar_path, child_name, is_dir, size, tar_path, child_tar_name, mtime)
    except (OSError, tarfile.TarError):
        return []
    return list(entries.values())


def match_filter(name: str, filter_text: str) -> bool:
    if not filter_text:
        return True
    pattern = filter_text.lower()
    target = name.lower()
    if any(ch in pattern for ch in "*?["):
        return fnmatch.fnmatchcase(target, pattern)
    return pattern in target


def zip_listing_preview_rows(zip_path: Path) -> list[str]:
    if is_tar_archive_path(zip_path):
        return tar_listing_preview_rows(zip_path)
    rows: list[str] = []
    try:
        with zipfile.ZipFile(zip_path) as archive:
            infos = sorted((info for info in archive.infolist() if not info.is_dir()), key=lambda info: info.filename.lower())
            rows = [f"{fmt_size(info.file_size, False):>7} {info.filename}" for info in infos]
    except (OSError, zipfile.BadZipFile):
        return ["[bad zip]"]
    return rows or ["[empty zip]"]


def tar_listing_preview_rows(tar_path: Path) -> list[str]:
    try:
        with tarfile.open(tar_path, "r:*") as archive:
            infos = sorted((info for info in archive.getmembers() if info.isfile()), key=lambda info: info.name.lower())
            rows = [f"{fmt_size(info.size, False):>7} {info.name}" for info in infos]
    except (OSError, tarfile.TarError):
        return ["[bad tar]"]
    return rows or ["[empty tar]"]


def sort_entries(entries: list[Entry], key: str, reverse: bool) -> None:
    def value(entry: Entry) -> object:
        if key == "ext":
            return ("", entry.name.lower()) if entry.is_dir else (Path(entry.name).suffix.lower(), entry.name.lower())
        if key == "size":
            return (entry.size, entry.name.lower())
        if key == "mtime":
            return (entry.mtime, entry.name.lower())
        if key == "natural":
            return natural_sort_key(entry.name)
        return entry.name.lower()

    dirs = sorted((entry for entry in entries if entry.is_dir), key=value, reverse=reverse)
    files = sorted((entry for entry in entries if not entry.is_dir), key=value, reverse=reverse)
    entries[:] = dirs + files


def natural_sort_key(text: str) -> tuple[object, ...]:
    parts = re.split(r"(\d+)", text.lower())
    key: list[object] = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part), len(part)))
        else:
            key.append((1, part))
    return tuple(key)


def zip_info_mtime(info: zipfile.ZipInfo) -> float:
    try:
        return time.mktime(info.date_time + (0, 0, -1))
    except (OverflowError, ValueError):
        return 0.0


def tar_info_mtime(info: tarfile.TarInfo) -> float:
    try:
        return float(info.mtime)
    except (TypeError, ValueError, OverflowError):
        return 0.0


def is_iterm_terminal() -> bool:
    return os.environ.get("TERM_PROGRAM") == "iTerm.app"


def is_image_path(path: Path) -> bool:
    return path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")


def is_zip_archive_path(path: Path) -> bool:
    return is_real_zip_archive_path(path) or is_tar_archive_path(path)


def is_real_zip_archive_path(path: Path) -> bool:
    return path.suffix.lower() in (".zip", ".jar")


def is_tar_archive_path(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith((".tar", ".tar.gz", ".tgz"))


ARCHIVE_READ_ERRORS = (OSError, KeyError, zipfile.BadZipFile, tarfile.TarError)


def archive_read_bytes(archive_path: Path, member_name: str) -> bytes:
    if is_tar_archive_path(archive_path):
        with tarfile.open(archive_path, "r:*") as archive:
            member = tar_member_for_name(archive, member_name)
            if member is None or not member.isfile():
                raise KeyError(member_name)
            stream = archive.extractfile(member)
            if stream is None:
                raise KeyError(member_name)
            with stream:
                return stream.read()
    with zipfile.ZipFile(archive_path) as archive:
        return archive.read(member_name)


def tar_member_for_name(archive: tarfile.TarFile, member_name: str) -> tarfile.TarInfo | None:
    target = normalize_tar_name(member_name).rstrip("/")
    for member in archive.getmembers():
        if normalize_tar_name(member.name).rstrip("/") == target:
            return member
    return None


def archive_entry_file_data(entry: Entry) -> Iterable[tuple[str, bytes]]:
    if entry.zip_path is None or entry.zip_name is None:
        return
    if is_tar_archive_path(entry.zip_path):
        prefix = normalize_zip_dir(entry.zip_name)
        with tarfile.open(entry.zip_path, "r:*") as archive:
            for member in archive.getmembers():
                name = normalize_tar_name(member.name)
                if entry.is_dir:
                    if not name.startswith(prefix) or not member.isfile():
                        continue
                elif name.rstrip("/") != normalize_tar_name(entry.zip_name).rstrip("/") or not member.isfile():
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    continue
                with stream:
                    yield name, stream.read()
        return
    with zipfile.ZipFile(entry.zip_path) as archive:
        if entry.is_dir:
            prefix = normalize_zip_dir(entry.zip_name)
            for info in archive.infolist():
                if not info.filename.startswith(prefix) or info.is_dir():
                    continue
                yield info.filename, archive.read(info.filename)
        else:
            yield entry.zip_name, archive.read(entry.zip_name)


def entry_is_image(entry: Entry) -> bool:
    if entry.zip_path is not None and entry.zip_name is not None:
        return is_image_path(Path(entry.zip_name))
    return is_image_path(entry.path)


def iterm_image_sequence(name: str, data: bytes) -> str:
    name_b64 = base64.b64encode(name.encode("utf-8", errors="replace")).decode("ascii")
    data_b64 = base64.b64encode(data).decode("ascii")
    return f"\x1b]1337;File=name={name_b64};size={len(data)};width=100%;height=100%;preserveAspectRatio=1;inline=1:{data_b64}\x07"


def read_key_normal_mode() -> str:
    if IS_WINDOWS:
        return read_key_windows()
    if not sys.stdin.isatty():
        ch = sys.stdin.read(1)
        return KEY_ENTER if ch in ("\n", "\r") else ch
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        attrs = termios.tcgetattr(fd)
        attrs[0] &= ~(termios.IXON | termios.IXOFF)
        attrs[3] &= ~(termios.ISIG | getattr(termios, "IEXTEN", 0))
        termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
        return read_key_posix()
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSAFLUSH, old)
        except termios.error:
            pass


def normalize_zip_dir(zip_dir: str) -> str:
    if not zip_dir:
        return ""
    name = normalize_zip_name(zip_dir)
    return name if name.endswith("/") else name + "/"


def normalize_zip_name(zip_name: str) -> str:
    if not zip_name:
        return ""
    parts = [decode_zip_member_name(part) for part in zip_name.replace("\\", "/").split("/") if part]
    if not parts:
        return ""
    name = "/".join(parts)
    return name + "/" if zip_name.endswith("/") else name


def normalize_tar_name(tar_name: str) -> str:
    if not tar_name:
        return ""
    parts = [part for part in tar_name.replace("\\", "/").split("/") if part]
    if not parts:
        return ""
    name = "/".join(parts)
    return name + "/" if tar_name.endswith("/") else name


def decode_zip_member_name(name: str) -> str:
    try:
        return name.encode("cp437").decode("utf-8")
    except UnicodeError:
        return name


def zip_actual_prefix_for_logical(raw_name: str, logical_prefix: str) -> str:
    target = normalize_zip_name(logical_prefix).rstrip("/").split("/")
    if not target:
        return ""
    raw_parts = raw_name.replace("\\", "/").split("/")
    actual = ""
    logical: list[str] = []
    for index, part in enumerate(raw_parts):
        if index:
            actual += "/"
        actual += part
        if not part:
            continue
        logical.append(decode_zip_member_name(part))
        if logical == target:
            return actual + "/"
    return normalize_zip_dir(logical_prefix)


def parent_zip_dir(zip_dir: str) -> str:
    value = normalize_zip_dir(zip_dir).rstrip("/")
    if "/" not in value:
        return ""
    return value.rsplit("/", 1)[0] + "/"


def read_preview_rows(path: Path) -> list[str]:
    data = path.read_bytes()[: min(path.stat().st_size, 64 * 1024)]
    return data.decode("utf-8", errors="replace").splitlines() or [""]


def file_preview_lines(path: Path, line_numbers: bool, width: int, wrap: bool, syntax: dict[str, object] | None = None) -> list[str]:
    try:
        with path.open("rb") as handle:
            data = handle.read(16384)
    except OSError:
        return []
    if editor_data_looks_binary(data):
        return ["[binary]"]
    return preview_body_lines(data.decode("utf-8", errors="replace").splitlines(), line_numbers, width, wrap, syntax)


def is_binary_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return editor_data_looks_binary(handle.read(16384))
    except OSError:
        return False


def file_preview_lines_around(path: Path, line_no: int, line_numbers: bool, width: int, wrap: bool, limit: int, match_text: str = "", match_color: str = "30;43", syntax: dict[str, object] | None = None) -> list[str]:
    start = max(1, line_no - 2)
    end = line_no + max(2, limit)
    rows: list[tuple[int, str]] = []
    try:
        with path.open("rb") as handle:
            sample = handle.read(4096)
            if editor_data_looks_binary(sample):
                return ["[binary]"]
            handle.seek(0)
            for index, raw in enumerate(handle, 1):
                if index < start:
                    continue
                if index > end:
                    break
                rows.append((index, raw.decode("utf-8", errors="replace").rstrip("\r\n")))
    except OSError:
        return []
    out: list[str] = []
    for index, line in rows:
        if match_text:
            plain = preview_text_line(line, index - 1, line_numbers, None)
            out.append(highlight_text(plain, match_text, match_color, width))
            continue
        text = preview_text_line(line, index - 1, line_numbers, syntax)
        if wrap:
            out.extend(wrap_display_text(text, width))
        else:
            out.append(text)
    return out


def zip_view_temp_path(zip_path: Path, zip_name: str) -> Path:
    try:
        stat_result = zip_path.stat()
        stamp = f"{stat_result.st_mtime_ns}:{stat_result.st_size}"
    except OSError:
        stamp = ""
    key = f"{zip_path.resolve()}!{zip_name}!{stamp}"
    digest = hashlib.sha1(key.encode("utf-8", errors="replace")).hexdigest()[:12]
    name = Path(zip_name).name or "zip-entry"
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "zip-entry"
    return Path(tempfile.gettempdir()) / "vfiler_zip_view" / f"{digest}_{safe_name}"


def zip_preview_lines(zip_path: Path, zip_name: str, line_numbers: bool, width: int, wrap: bool) -> list[str]:
    try:
        data = archive_read_bytes(zip_path, zip_name)[:16384]
    except ARCHIVE_READ_ERRORS:
        return []
    if editor_data_looks_binary(data):
        return ["[binary]"]
    return preview_body_lines(data.decode("utf-8", errors="replace").splitlines(), line_numbers, width, wrap)


def preview_body_lines(lines: list[str], line_numbers: bool, width: int, wrap: bool, syntax: dict[str, object] | None = None) -> list[str]:
    rows: list[str] = []
    for index, line in enumerate(lines):
        text = preview_text_line(line, index, line_numbers, syntax)
        if wrap:
            rows.extend(wrap_display_text(text, width))
        else:
            rows.append(text)
    return rows


def wrap_display_text(text: str, width: int) -> list[str]:
    if width <= 0:
        return [""]
    if "\x1b[" in text:
        return wrap_ansi_text(text, width)
    rows: list[str] = []
    line = text
    while display_width(line) > width:
        part = ""
        used = 0
        for ch in line:
            ch_width = char_width(ch)
            if used + ch_width > width:
                break
            part += ch
            used += ch_width
        rows.append(part)
        line = line[len(part):]
    rows.append(line)
    return rows


def editor_load(path: Path) -> tuple[list[str], str, str] | None:
    loaded = editor_load_detail(path)
    if loaded is None:
        return None
    lines, eol, encoding, binary = loaded
    if binary:
        return None
    return lines, eol, encoding


def editor_load_detail(path: Path) -> tuple[list[str], str, str, bool] | None:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        data = b""
    except OSError:
        return None
    eol = detect_eol(data)
    binary = editor_data_looks_binary(data)
    text, encoding = decode_editor_bytes(data)
    return text.splitlines() or [""], eol, encoding, binary


def editor_data_looks_binary(data: bytes) -> bool:
    if not data:
        return False
    return b"\x00" in data


def editor_save(path: Path, lines: list[str], eol: str = "LF", encoding: str = "UTF-8") -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        newline = eol_text(eol)
        path.write_text(newline.join(lines) + newline, encoding=encoding_name(encoding), newline="")
        return True
    except (OSError, UnicodeError):
        return False


def decode_editor_bytes(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace"), "UTF-8+BOM"
    for name, label in (("utf-8", "UTF-8"), ("cp932", "CP932")):
        try:
            return data.decode(name), label
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1", errors="replace"), "LATIN-1"


def encoding_name(label: str) -> str:
    return {
        "UTF-8": "utf-8",
        "UTF-8+BOM": "utf-8-sig",
        "CP932": "cp932",
        "LATIN-1": "latin-1",
    }.get(label, "utf-8")


def detect_eol(data: bytes) -> str:
    crlf = data.count(b"\r\n")
    rest = data.replace(b"\r\n", b"")
    lf = rest.count(b"\n")
    cr = rest.count(b"\r")
    kinds = sum(1 for count in (crlf, lf, cr) if count)
    if kinds > 1:
        return "MIXED"
    if crlf:
        return "CRLF"
    if cr:
        return "CR"
    if lf:
        return "LF"
    return "NONE"


def eol_text(eol: str) -> str:
    return {"CRLF": "\r\n", "CR": "\r", "LF": "\n"}.get(eol, "\r\n" if IS_WINDOWS else "\n")


def default_eol() -> str:
    return "CRLF" if IS_WINDOWS else "LF"


def confirm_popup_key(term: Terminal, message: str, redraw: Callable[[], None] | None = None, hint: str = "Y:OK  N/ESC:Cancel") -> str:
    if redraw is not None:
        redraw()
    columns, rows = term.size()
    content_width = max(ansi_width(message), display_width(hint))
    width = min(max(34, content_width + 4), max(20, columns - 4))
    height = 3
    start_row = max(2, (rows - height) // 2 + 1)
    start_col = max(1, (columns - width) // 2 + 1)
    term.move(start_row, start_col)
    term.write(yellow("█" * width))
    term.move(start_row + 1, start_col)
    term.write(yellow("█") + fit_ansi(message, width - 2) + yellow("█"))
    term.move(start_row + 2, start_col)
    term.write(yellow_bg(fit(hint, width)))
    term.flush()
    return read_key()


def editor_confirm(term: Terminal, message: str) -> bool:
    return confirm_popup_key(term, message) in ("y", "Y")


def editor_confirm_default_yes(term: Terminal, message: str) -> bool:
    key = confirm_popup_key(term, message, hint="Enter/Y:OK  N/ESC:Cancel")
    return key not in ("n", "N", KEY_ESCAPE, KEY_BACKSPACE)


def editor_menu_bar_text() -> str:
    return " F1:Files F2:Edit F3:Settings F4:Filer F5:Split F6:NextPain F7:PainSize F8:Select/Rect F9:Copy/Cut F10:Paste/Clips F11:Shell F12:NextBuf/Buffers "


def editor_menu_labels() -> list[str]:
    return ["F1:Files", "F2:Edit", "F3:Settings", "F12:NextBuf/Buffers"]


def editor_menu(term: Terminal, initial_menu: int, redraw, buffers: list[EditorBuffer] | None = None, current_buffer: int = 0, insert_mode: bool = True) -> str | None:  # type: ignore[no-untyped-def]
    buffer_items: list[CommandItem] = []
    if buffers is not None:
        for index, buffer in enumerate(buffers):
            mark = "*" if buffer.dirty else " "
            buffer_items.append(CommandItem(f"{index + 1}:{mark} {buffer.path.name}", f"buffer:{index}"))
    file_shortcut_col = 16
    edit_shortcut_col = 18
    settings_shortcut_col = 24
    current_readonly = bool(buffers and 0 <= current_buffer < len(buffers) and buffers[current_buffer].readonly)
    menus = [
        ("Files", [
            CommandItem(menu_text("Open", "", file_shortcut_col), "open"),
            CommandItem(menu_text("New", "", file_shortcut_col), "new"),
            CommandItem(menu_text("Save", "Ctrl+S", file_shortcut_col), "save"),
            CommandItem(menu_text("Save As", "", file_shortcut_col), "save_as"),
            CommandItem(menu_text("Tail", "", file_shortcut_col), "tail", not current_readonly),
            CommandItem(menu_text("Close", "Esc", file_shortcut_col), "close"),
        ]),
        ("Edit", [
            CommandItem(menu_text("Undo", "Ctrl+Z", edit_shortcut_col), "undo"),
            CommandItem(menu_text("Redo", "Ctrl+R", edit_shortcut_col), "redo"),
            menu_separator(),
            CommandItem(menu_text("Cut", "Shift+F9" if IS_WINDOWS else "Ctrl+X", edit_shortcut_col), "cut"),
            CommandItem(menu_text("Copy", "F9" if IS_WINDOWS else "Ctrl+C", edit_shortcut_col), "copy"),
            CommandItem(menu_text("Paste", "F10" if IS_WINDOWS else "Ctrl+V", edit_shortcut_col), "paste"),
            CommandItem(menu_text("Clip List", "Shift+F10", edit_shortcut_col), "clip_list"),
            CommandItem(menu_text("Select All", "Ctrl+A", edit_shortcut_col), "select_all"),
            menu_separator(),
            CommandItem(menu_text("Find", "Ctrl+F", edit_shortcut_col), "find"),
            CommandItem(menu_text("Find Next", "Ctrl+N", edit_shortcut_col), "find_next"),
            CommandItem(menu_text("Replace", "", edit_shortcut_col), "replace"),
            CommandItem(menu_text(f"VI Mode ({'ON' if EDITOR_STATE.vi_mode else 'OFF'})", "", edit_shortcut_col), "vi_mode"),
            CommandItem(menu_text("Normalize EOL", "", edit_shortcut_col), "normalize_eol"),
            CommandItem(menu_text("Delete Line", "Ctrl+Y", edit_shortcut_col), "delete_line"),
        ]),
        ("Settings", [
            CommandItem(menu_text(f"Tab Space ({EDITOR_STATE.tab_spaces})", "", settings_shortcut_col), "tab_space"),
            CommandItem(menu_text(f"Wrap Mode ({'Wrap' if EDITOR_STATE.wrap else 'Scroll'})", "", settings_shortcut_col), "wrap_mode"),
            CommandItem(menu_text(f"Line Number ({'Show' if EDITOR_STATE.line_numbers else 'Hide'})", "", settings_shortcut_col), "line_number"),
            CommandItem(menu_text(f"Mouse Cursor ({'ON' if EDITOR_STATE.mouse_cursor else 'OFF'})", "", settings_shortcut_col), "mouse_cursor"),
            CommandItem(menu_text(f"Wheel Scroll ({'ON' if EDITOR_STATE.wheel_scroll else 'OFF'})", "", settings_shortcut_col), "wheel_scroll"),
            CommandItem(menu_text(f"Ruler ({'ON' if EDITOR_STATE.ruler else 'OFF'})", "", settings_shortcut_col), "ruler"),
            CommandItem(menu_text(f"Cursor Underline ({'ON' if EDITOR_STATE.cursor_underline else 'OFF'})", "", settings_shortcut_col), "cursor_underline"),
            CommandItem(menu_text(f"Show Enter ({'ON' if EDITOR_STATE.show_enter else 'OFF'})", "", settings_shortcut_col), "show_enter"),
            CommandItem(menu_text(f"Show Tab ({'ON' if EDITOR_STATE.show_tab else 'OFF'})", "", settings_shortcut_col), "show_tab"),
            CommandItem(menu_text(f"Show Bin ({'ON' if EDITOR_STATE.show_bin else 'OFF'})", "", settings_shortcut_col), "show_bin"),
            CommandItem(menu_text(f"Insert/Overwrite ({'INS' if insert_mode else 'OVR'})", "", settings_shortcut_col), "insert_mode"),
            CommandItem(menu_text("Line Draw", "", settings_shortcut_col), "line_draw"),
        ]),
        ("Buffers", buffer_items or [CommandItem("Single Buffer", "", True)]),
    ]
    menu = initial_menu
    labels = editor_menu_labels()
    cursor = current_buffer if initial_menu == 3 and buffers else 0
    while True:
        redraw()
        items = menus[menu][1]
        columns, lines = term.size()
        group = menus[menu][0]
        width = min(max(18, max(max(display_width(item.title) for item in items), display_width(group)) + 4), max(18, columns))
        height = min(len(items), max(1, lines - 4))
        top = min(max(0, cursor - height + 1), max(0, len(items) - height))
        start_row = 2
        bar_text = editor_menu_bar_text()
        start_col = menu_popup_col(bar_text, labels[menu], columns, width)
        draw_menu_bar_highlight(term, bar_text, labels[menu])
        term.move(start_row, start_col)
        term.write(yellow("█" * width))
        for index, item in enumerate(items[top:top + height], start=top):
            line = fit("-" * (width - 2) if is_menu_separator(item) else item.title, width - 2)
            term.move(start_row + 1 + index - top, start_col)
            if is_menu_separator(item):
                body = yellow_bg(line)
            elif item.disabled:
                body = color_text(line, "90;43")
            elif index == cursor:
                body = color_text(line, "31;43")
            else:
                body = yellow_bg(line)
            term.write(yellow("█") + body + yellow("█"))
        term.move(start_row + height + 1, start_col)
        term.write(yellow("█" * width))
        term.flush()
        key = read_key()
        if key == KEY_ENTER:
            return None if items[cursor].disabled else items[cursor].command
        if key in (KEY_ESCAPE, KEY_BACKSPACE, "q", "Q"):
            return None
        if key in (KEY_F1, KEY_F2, KEY_F3, KEY_SHIFT_F12):
            menu = {KEY_F1: 0, KEY_F2: 1, KEY_F3: 2, KEY_SHIFT_F12: 3}[key]
            cursor = current_buffer if menu == 3 and buffers else first_enabled_command(menus[menu][1])
        if key in (KEY_LEFT, KEY_RIGHT):
            menu = (menu + (1 if key == KEY_RIGHT else -1)) % len(menus)
            cursor = current_buffer if menu == 3 and buffers else first_enabled_command(menus[menu][1])
        if key in (KEY_UP, "k", "K"):
            cursor = move_enabled_command(items, cursor, -1)
        elif key in (KEY_DOWN, "j", "J"):
            cursor = move_enabled_command(items, cursor, 1)


def menu_cursor(items: list[tuple[str, str]], cursor: int, delta: int) -> int:
    next_cursor = cursor
    for _ in range(len(items)):
        next_cursor = min(len(items) - 1, max(0, next_cursor + delta))
        if items[next_cursor][1]:
            return next_cursor
    return cursor


def menu_text(label: str, shortcut: str, shortcut_col: int) -> str:
    if not shortcut:
        return label
    spaces = max(1, shortcut_col - display_width(label))
    return label + (" " * spaces) + shortcut


def menu_separator() -> CommandItem:
    return CommandItem("", "", True)


def is_menu_separator(item: CommandItem) -> bool:
    return not item.title and not item.command


def first_enabled_command(items: list[CommandItem]) -> int:
    for index, item in enumerate(items):
        if not item.disabled:
            return index
    return 0


def move_enabled_command(items: list[CommandItem], cursor: int, delta: int) -> int:
    if not items:
        return 0
    step = 1 if delta >= 0 else -1
    count = max(1, abs(delta))
    index = cursor
    for _ in range(count):
        probe = index
        while True:
            next_index = min(len(items) - 1, max(0, probe + step))
            if next_index == probe:
                return index
            probe = next_index
            if not items[probe].disabled:
                index = probe
                break
    return index


def editor_buffer_list(term: Terminal, buffers: list[EditorBuffer], current: int, redraw, origin: tuple[int, int, int, int] | None = None) -> int | None:  # type: ignore[no-untyped-def]
    cursor = current
    top = 0
    while True:
        redraw()
        columns, lines = term.size()
        height = min(len(buffers), max(1, min(10, lines - 6)))
        width = min(max(30, max(display_width(buffer.path.name) for buffer in buffers) + 10), max(30, columns - 4))
        if origin is None:
            row = max(2, (lines - height - 3) // 2 + 1)
            col = max(1, (columns - width) // 2 + 1)
        else:
            pane_row, pane_col, pane_width, pane_height = origin
            row = pane_row + max(0, (pane_height - height - 3) // 2)
            col = pane_col + max(0, (pane_width - width) // 2)
            row = min(max(2, row), max(2, lines - height - 2))
            col = min(max(1, col), max(1, columns - width + 1))
        if cursor < top:
            top = cursor
        elif cursor >= top + height:
            top = cursor - height + 1
        for y in range(height + 3):
            term.move(row + y, col)
            if y == 0 or y == height + 2:
                term.write(yellow("█" * width))
            else:
                term.write(yellow("█") + " " * (width - 2) + yellow("█"))
        for screen_row in range(height):
            index = top + screen_row
            buffer = buffers[index]
            mark = "*" if buffer.dirty else " "
            title = f"{index + 1}:{mark} {buffer.path.name}"
            line = fit(("> " if index == cursor else "  ") + title, width - 2)
            term.move(row + 1 + screen_row, col + 1)
            term.write(reverse(line) if index == cursor else line)
        term.move(row + height + 2, col + 1)
        term.write(yellow_bg(fit(" Enter:OK  ESC:Cancel ", width - 2)))
        term.flush()
        key = read_key()
        if key == KEY_ENTER:
            return cursor
        if key in (KEY_ESCAPE, KEY_BACKSPACE, "q", "Q", KEY_SHIFT_F12):
            return None
        if key in (KEY_UP, "k", "K"):
            cursor = max(0, cursor - 1)
        elif key in (KEY_DOWN, "j", "J"):
            cursor = min(len(buffers) - 1, cursor + 1)
        elif key == KEY_PGUP:
            cursor = max(0, cursor - height)
        elif key == KEY_PGDN:
            cursor = min(len(buffers) - 1, cursor + height)


def text_editor(term: Terminal, path: Path, readonly: bool = False, colors: dict[str, str] | None = None, buffers: list[EditorBuffer] | None = None, current_ref: list[int] | None = None, start_line: int | None = None, resident_mode: bool = False) -> bool:
    def load_editor_buffer(load_path: Path) -> tuple[list[str], str, str, bool] | None:
        loaded_detail = editor_load_detail(load_path)
        if loaded_detail is None:
            return None
        loaded_lines, loaded_eol, loaded_encoding, binary = loaded_detail
        if binary and not editor_confirm_default_yes(term, "バイナリファイルの可能性がありますが開きますか？ Y/n"):
            return None
        return loaded_lines, loaded_eol, loaded_encoding, binary

    if buffers is None:
        loaded = load_editor_buffer(path)
        if loaded is None:
            return False
        loaded_lines, loaded_eol, loaded_encoding, loaded_binary = loaded
        buffer = EditorBuffer(path, loaded_lines, readonly, edit_mode=not readonly, undo=[], redo=[], encoding=loaded_encoding, eol=loaded_eol, show_bin=loaded_binary)
        buffers = [buffer]
        current_buffer = 0
    else:
        current_buffer = min(max(0, current_ref[0] if current_ref else 0), max(0, len(buffers) - 1))
        match = next((index for index, item in enumerate(buffers) if item.path == path), None)
        if match is None:
            loaded = load_editor_buffer(path)
            if loaded is None:
                return False
            loaded_lines, loaded_eol, loaded_encoding, loaded_binary = loaded
            buffers.append(EditorBuffer(path, loaded_lines, readonly, edit_mode=not readonly, undo=[], redo=[], encoding=loaded_encoding, eol=loaded_eol, show_bin=loaded_binary))
            current_buffer = len(buffers) - 1
        else:
            current_buffer = match
        buffer = buffers[current_buffer]
    if start_line is not None:
        buffer.cy = min(max(0, start_line - 1), max(0, len(buffer.lines) - 1))
        buffer.cx = 0
        buffer.top = max(0, buffer.cy - 2)
    lines = buffer.lines
    cy = buffer.cy
    cx = buffer.cx
    top = buffer.top
    left = buffer.left
    mark = buffer.mark
    select_mode = buffer.select_mode
    rect_select = buffer.rect_select
    find_text = buffer.find_text
    insert_mode = buffer.insert_mode
    edit_mode = buffer.edit_mode
    undo = buffer.undo or []
    redo = buffer.redo or []
    dirty = buffer.dirty
    saved = buffer.saved
    msg = buffer.msg
    encoding = buffer.encoding
    eol = buffer.eol
    show_bin = buffer.show_bin
    split_mode = "full"
    editor_pane = 0
    editor_pane_buffers = [current_buffer, current_buffer]
    editor_split_ratio = 0.5
    editor_shell_focus = False
    editor_shell = EditorShellState(path.parent, history_index=len(EDITOR_STATE.run_history))
    vi_command = EDITOR_STATE.vi_mode
    vi_count = ""
    vi_op = ""
    vi_op_count = ""
    vi_insert_undo_open = False
    editor_tail: TailState | None = None
    editor_tail_follow = True
    term.show_cursor()

    def sync_buffer() -> None:
        buffer.path = path
        buffer.lines = lines
        buffer.cy = cy
        buffer.cx = cx
        buffer.top = top
        buffer.left = left
        buffer.mark = mark
        buffer.select_mode = select_mode
        buffer.rect_select = rect_select
        buffer.find_text = find_text
        buffer.insert_mode = insert_mode
        buffer.edit_mode = edit_mode
        buffer.undo = undo
        buffer.redo = redo
        buffer.dirty = dirty
        buffer.saved = saved
        buffer.msg = msg
        buffer.encoding = encoding
        buffer.eol = eol
        buffer.show_bin = show_bin

    def finish(result: bool) -> bool:
        sync_buffer()
        if current_ref is not None:
            current_ref[0] = current_buffer
        return result

    def close_buffer(result: bool) -> bool:
        nonlocal current_buffer
        if buffers:
            del buffers[current_buffer]
        if buffers:
            current_buffer = min(current_buffer, len(buffers) - 1)
            for index, pane_buffer in enumerate(editor_pane_buffers):
                if pane_buffer >= len(buffers):
                    editor_pane_buffers[index] = len(buffers) - 1
        if current_ref is not None:
            current_ref[0] = current_buffer
        return result

    def use_buffer(new_buffer: EditorBuffer) -> tuple[Path, list[str], int, int, int, int, tuple[int, int] | None, bool, bool, str, bool, bool, list[tuple[list[str], int, int]], list[tuple[list[str], int, int]], bool, bool, str, str, str, bool]:
        return (
            new_buffer.path,
            new_buffer.lines,
            new_buffer.cy,
            new_buffer.cx,
            new_buffer.top,
            new_buffer.left,
            new_buffer.mark,
            new_buffer.select_mode,
            new_buffer.rect_select,
            new_buffer.find_text,
            new_buffer.insert_mode,
            new_buffer.edit_mode,
            new_buffer.undo or [],
            new_buffer.redo or [],
            new_buffer.dirty,
            new_buffer.saved,
            new_buffer.msg,
            new_buffer.encoding,
            new_buffer.eol,
            new_buffer.show_bin,
        )

    def switch_to_buffer(index: int, message: str = "") -> None:
        nonlocal current_buffer, buffer, path, lines, cy, cx, top, left, mark, select_mode, rect_select, find_text, insert_mode, edit_mode, undo, redo, dirty, saved, msg, encoding, eol, show_bin
        current_buffer = min(max(0, index), max(0, len(buffers) - 1))
        buffer = buffers[current_buffer]
        path, lines, cy, cx, top, left, mark, select_mode, rect_select, find_text, insert_mode, edit_mode, undo, redo, dirty, saved, msg, encoding, eol, show_bin = use_buffer(buffer)
        if message:
            msg = message

    def split_peer_buffer(index: int) -> int:
        buffers.append(clone_editor_buffer(buffers[index]))
        return len(buffers) - 1

    def close_split_peer() -> None:
        nonlocal current_buffer
        peer = editor_pane_buffers[1 - editor_pane]
        if peer == current_buffer or not (0 <= peer < len(buffers)):
            return
        if buffers[peer].path != buffers[current_buffer].path:
            return
        del buffers[peer]
        if current_buffer > peer:
            current_buffer -= 1
        for index, pane_buffer in enumerate(editor_pane_buffers):
            if pane_buffer > peer:
                editor_pane_buffers[index] = pane_buffer - 1
            elif pane_buffer == peer:
                editor_pane_buffers[index] = current_buffer

    def vi_status_text() -> str:
        if not EDITOR_STATE.vi_mode:
            return ""
        if select_mode and not rect_select and vi_command:
            return "VI:VIS"
        return "VI:CMD" if vi_command else "VI:INS"

    def enter_vi_insert(join_undo: bool = False) -> None:
        nonlocal vi_command, vi_insert_undo_open
        vi_command = False
        vi_insert_undo_open = join_undo

    def ensure_vi_insert_undo() -> bool:
        nonlocal vi_insert_undo_open
        if EDITOR_STATE.vi_mode and not vi_command:
            if not vi_insert_undo_open:
                push_undo(undo, lines, cy, cx)
                redo.clear()
                vi_insert_undo_open = True
            return True
        return False

    def redraw_editor() -> None:
        if split_mode == "full":
            editor_draw(term, path, lines, cy, cx, top, left, body, gutter, text_w, mark, rect_select, dirty, msg, insert_mode, edit_mode, colors, current_buffer, len(buffers), encoding, eol, vi_status_text(), show_bin)
        else:
            sync_buffer()
            sync_same_path_buffers(buffers, current_buffer)
            editor_draw_split(term, buffers, editor_pane_buffers, editor_pane, split_mode, editor_split_ratio, colors, msg, vi_status_text(), editor_shell if split_mode == "shell" else None, editor_shell_focus)

    try:
        while True:
            columns, rows = term.size()
            if split_mode == "full":
                pane_width = columns
                body = max(1, rows - 2 - editor_vi_command_rows() - (1 if EDITOR_STATE.ruler else 0))
            elif split_mode == "shell":
                pane_width, body = editor_active_pane_text_size(split_mode, 0, editor_split_ratio, columns, rows)
            else:
                pane_width, body = editor_active_pane_text_size(split_mode, editor_pane, editor_split_ratio, columns, rows)
            gutter = max(6, len(str(len(lines))) + 2) if EDITOR_STATE.line_numbers else 0
            cursor_w = editor_text_width(lines[cy][:cx], show_bin)
            text_w = max(1, pane_width - gutter)
            if EDITOR_STATE.wrap:
                left = 0
                top = editor_ensure_wrap_visible(lines, top, cy, cx, text_w, body, show_bin)
            else:
                if cy < top:
                    top = cy
                elif cy >= top + body:
                    top = cy - body + 1
            if editor_tail is not None and editor_tail.active and editor_at_bottom(top, body, len(lines)):
                editor_tail_follow = True
            if cursor_w < left:
                left = cursor_w
            elif cursor_w >= left + text_w:
                left = cursor_w - text_w + 1

            editor_pane_buffers[editor_pane] = current_buffer
            if editor_tail is not None and editor_tail.path != path:
                editor_tail = None
            redraw_editor()
            msg = ""

            key = read_key_timeout(0.2) if editor_tail is not None and editor_tail.active else read_key()
            if not key:
                if editor_tail is not None and editor_tail.active:
                    rows = read_tail_lines(editor_tail)
                    if rows:
                        append_tail_to_editor_lines(lines, rows)
                        if editor_tail_follow:
                            cy = max(0, len(lines) - 1)
                            cx = min(cx, len(lines[cy]))
                            top = max(0, len(lines) - body)
                        msg = f"tail: {path.name}"
                continue
            key = normalize_move_key(key)
            if editor_tail is not None and editor_tail.active and key in (KEY_UP, KEY_PGUP, KEY_HOME, KEY_WHEEL_UP, "k", "K", "\x15"):
                editor_tail_follow = False
            if split_mode == "shell" and editor_shell_focus:
                if key == KEY_F6:
                    editor_shell_focus = False
                    msg = "pane 1"
                    continue
                if key == KEY_F11:
                    editor_shell_focus = False
                    split_mode = "full"
                    msg = "shell closed"
                    continue
                handled, shell_msg = handle_editor_shell_key(term, editor_shell, key, editor_shell_height(editor_split_ratio, columns, rows))
                if handled:
                    msg = shell_msg
                    continue
            if key in (KEY_WHEEL_UP, KEY_WHEEL_DOWN):
                if not EDITOR_STATE.wheel_scroll:
                    continue
                delta = -3 if key == KEY_WHEEL_UP else 3
                cy, top = wheel_scroll_position(cy, top, len(lines), body, delta)
                cx = min(cx, len(lines[cy]))
                buffer.top = top
                buffer.cy = cy
                buffer.cx = cx
                msg = f"top:{top + 1}"
            elif key.startswith(KEY_MOUSE + ":"):
                event = mouse_event(key)
                if not EDITOR_STATE.mouse_cursor or event is None:
                    continue
                button, mcol, mrow, press = event
                if not press or button != 0:
                    continue
                if split_mode != "full":
                    sync_buffer()
                    if split_mode == "shell":
                        top_rect = editor_pane_rect(split_mode, 0, editor_split_ratio, columns, rows)
                        shell_rect = editor_pane_rect(split_mode, 1, editor_split_ratio, columns, rows)
                        if top_rect[0] <= mrow < top_rect[0] + top_rect[3]:
                            editor_shell_focus = False
                        elif shell_rect[0] <= mrow < shell_rect[0] + shell_rect[3]:
                            editor_shell_focus = True
                        continue
                    for pane_index in (0, 1):
                        r, c, w, h = editor_pane_rect(split_mode, pane_index, editor_split_ratio, columns, rows)
                        ruler_offset = 1 if EDITOR_STATE.ruler else 0
                        if r + 1 + ruler_offset <= mrow < r + h and c <= mcol < c + w:
                            editor_pane_buffers[editor_pane] = current_buffer
                            editor_pane = pane_index
                            current_buffer = editor_pane_buffers[editor_pane]
                            buffer = buffers[current_buffer]
                            path, lines, cy, cx, top, left, mark, select_mode, rect_select, find_text, insert_mode, edit_mode, undo, redo, dirty, saved, msg, encoding, eol, show_bin = use_buffer(buffer)
                            gutter = max(6, len(str(len(lines))) + 2) if EDITOR_STATE.line_numbers else 0
                            cy = min(max(0, top + (mrow - (r + 1 + ruler_offset))), max(0, len(lines) - 1))
                            target_col = max(0, left + (mcol - c + 1) - gutter - 1)
                            cx = display_col_to_index(lines[cy], target_col, show_bin)
                            msg = "mouse"
                            break
                    continue
                ruler_offset = 1 if EDITOR_STATE.ruler else 0
                if 2 + ruler_offset <= mrow < 2 + ruler_offset + body:
                    cy = min(max(0, top + (mrow - (2 + ruler_offset))), max(0, len(lines) - 1))
                    target_col = max(0, left + mcol - gutter - 1)
                    cx = display_col_to_index(lines[cy], target_col, show_bin)
                    msg = "mouse"
            elif key == "\x13":
                if not edit_mode:
                    msg = read_only_bell(term)
                    continue
                if editor_save(path, lines, eol, encoding):
                    dirty = False
                    saved = True
                    msg = "saved"
                else:
                    msg = "save failed"
            elif key == KEY_F4:
                return finish(False)
            elif key == KEY_F5:
                old_split_mode = split_mode
                editor_shell_focus = False
                split_mode = {"full": "h", "h": "v", "v": "full", "shell": "h"}[split_mode]
                if old_split_mode == "full" and split_mode != "full" and editor_pane_buffers[0] == editor_pane_buffers[1]:
                    sync_buffer()
                    editor_pane_buffers[1] = split_peer_buffer(current_buffer)
                elif old_split_mode != "full" and split_mode == "full":
                    sync_buffer()
                    close_split_peer()
                    switch_to_buffer(current_buffer)
                msg = f"split: {split_mode}"
            elif key == KEY_F6:
                if split_mode == "shell":
                    sync_buffer()
                    editor_shell.cwd = path.parent
                    editor_shell_focus = not editor_shell_focus
                    msg = "shell" if editor_shell_focus else "pane 1"
                    continue
                if split_mode == "full":
                    msg = "single pane"
                    continue
                sync_buffer()
                editor_pane_buffers[editor_pane] = current_buffer
                editor_pane = 1 - editor_pane
                switch_to_buffer(editor_pane_buffers[editor_pane], f"pane {editor_pane + 1}")
            elif resident_mode and key == KEY_F11:
                sync_buffer()
                return finish(False)
            elif key == KEY_SHIFT_F11 or (key == KEY_F11 and not resident_mode):
                sync_buffer()
                split_mode = "shell"
                editor_pane = 0
                editor_pane_buffers[0] = current_buffer
                editor_shell.cwd = path.parent
                editor_shell_focus = True
                msg = "shell"
            elif key == KEY_F7:
                editor_split_ratio = editor_pane_size_mode(term, buffers, editor_pane_buffers, editor_pane, split_mode, editor_split_ratio, colors, editor_shell if split_mode == "shell" else None, editor_shell_focus)
                msg = f"pane size: {int(editor_split_ratio * 100)}%"
            elif key == KEY_F12:
                if len(buffers) <= 1:
                    msg = "single buffer"
                    continue
                sync_buffer()
                current_buffer = (current_buffer + 1) % len(buffers)
                editor_pane_buffers[editor_pane] = current_buffer
                buffer = buffers[current_buffer]
                path, lines, cy, cx, top, left, mark, select_mode, rect_select, find_text, insert_mode, edit_mode, undo, redo, dirty, saved, msg, encoding, eol, show_bin = use_buffer(buffer)
                msg = f"buffer {current_buffer + 1}/{len(buffers)}"
            elif key == KEY_SHIFT_F12:
                if len(buffers) <= 1:
                    msg = "single buffer"
                    continue
                sync_buffer()
                selected_buffer = editor_buffer_list(
                    term,
                    buffers,
                    current_buffer,
                    lambda: editor_draw_split(term, buffers, editor_pane_buffers, editor_pane, split_mode, editor_split_ratio, colors, msg) if split_mode != "full" else editor_draw(term, path, lines, cy, cx, top, left, body, gutter, text_w, mark, rect_select, dirty, msg, insert_mode, edit_mode, colors, current_buffer, len(buffers), encoding, eol, show_bin=show_bin),
                    editor_pane_rect(split_mode, editor_pane, editor_split_ratio, columns, rows) if split_mode != "full" else None,
                )
                if selected_buffer is None:
                    msg = "buffer list canceled"
                    continue
                current_buffer = selected_buffer
                editor_pane_buffers[editor_pane] = current_buffer
                buffer = buffers[current_buffer]
                path, lines, cy, cx, top, left, mark, select_mode, rect_select, find_text, insert_mode, edit_mode, undo, redo, dirty, saved, msg, encoding, eol, show_bin = use_buffer(buffer)
                msg = f"buffer {current_buffer + 1}/{len(buffers)}"
            elif key in (KEY_F1, KEY_F2, KEY_F3):
                action = editor_menu(
                    term,
                    {KEY_F1: 0, KEY_F2: 1, KEY_F3: 2}[key],
                    lambda: editor_draw(term, path, lines, cy, cx, top, left, body, gutter, text_w, mark, rect_select, dirty, msg, insert_mode, edit_mode, colors, current_buffer, len(buffers), encoding, eol, show_bin=show_bin),
                    buffers,
                    current_buffer,
                    insert_mode,
                )
                if action and action.startswith("buffer:"):
                    sync_buffer()
                    current_buffer = int(action.split(":", 1)[1])
                    editor_pane_buffers[editor_pane] = current_buffer
                    buffer = buffers[current_buffer]
                    path, lines, cy, cx, top, left, mark, select_mode, rect_select, find_text, insert_mode, edit_mode, undo, redo, dirty, saved, msg, encoding, eol, show_bin = use_buffer(buffer)
                    msg = f"buffer {current_buffer + 1}/{len(buffers)}"
                    continue
                if action == "open":
                    if not edit_mode:
                        msg = read_only_bell(term)
                        continue
                    if dirty and not editor_confirm(term, "Unsaved. Open? y/N"):
                        msg = "open canceled"
                        continue
                    name = popup_edit_line(term, "open", str(path), redraw_editor)
                    if name:
                        new_path = Path(name).expanduser()
                        if not new_path.is_absolute():
                            new_path = path.parent / new_path
                        loaded = load_editor_buffer(new_path)
                        if loaded is None:
                            msg = "open failed"
                        else:
                            loaded_lines, loaded_eol, loaded_encoding, loaded_binary = loaded
                            buffer = EditorBuffer(new_path, loaded_lines, readonly, edit_mode=edit_mode, undo=[], redo=[], encoding=loaded_encoding, eol=loaded_eol, show_bin=loaded_binary)
                            buffers[current_buffer] = buffer
                            path, lines, cy, cx, top, left, mark, select_mode, rect_select, find_text, insert_mode, edit_mode, undo, redo, dirty, saved, msg, encoding, eol, show_bin = use_buffer(buffer)
                            msg = "opened"
                elif action == "new":
                    if not edit_mode:
                        msg = read_only_bell(term)
                        continue
                    if dirty and not editor_confirm(term, "Unsaved. New? y/N"):
                        msg = "new canceled"
                        continue
                    buffer = EditorBuffer(path.parent / "untitled.txt", [""], readonly, edit_mode=edit_mode, undo=[], redo=[], encoding="UTF-8", eol="LF")
                    buffers[current_buffer] = buffer
                    path, lines, cy, cx, top, left, mark, select_mode, rect_select, find_text, insert_mode, edit_mode, undo, redo, dirty, saved, msg, encoding, eol, show_bin = use_buffer(buffer)
                    msg = "new file"
                elif action == "save":
                    if not edit_mode:
                        msg = read_only_bell(term)
                        continue
                    if editor_save(path, lines, eol, encoding):
                        dirty = False
                        saved = True
                        msg = "saved"
                    else:
                        msg = "save failed"
                elif action == "save_as":
                    if not edit_mode:
                        msg = read_only_bell(term)
                        continue
                    name = popup_edit_line(term, "save as", str(path), redraw_editor)
                    if name:
                        new_path = Path(name).expanduser()
                        if not new_path.is_absolute():
                            new_path = path.parent / new_path
                        if editor_save(new_path, lines, eol, encoding):
                            path = new_path
                            dirty = False
                            saved = True
                            msg = "saved"
                        else:
                            msg = "save failed"
                elif action == "tail":
                    if not buffer.readonly:
                        msg = read_only_bell(term)
                        continue
                    try:
                        offset = path.stat().st_size
                    except OSError:
                        msg = "tail failed"
                        continue
                    stamp = tail_timestamp()
                    lines[:] = timestamp_tail_rows(lines, stamp)
                    buffer.lines = lines
                    editor_tail = TailState(path, offset, "", True, stamp)
                    editor_tail_follow = True
                    cy = max(0, len(lines) - 1)
                    cx = min(cx, len(lines[cy]))
                    top = max(0, len(lines) - body)
                    msg = f"tail: {path.name}"
                elif action == "close":
                    if not dirty or editor_confirm(term, "Close? y/N"):
                        return close_buffer(saved and not dirty)
                elif action:
                    if action == "replace":
                        if not edit_mode:
                            msg = read_only_bell(term)
                            continue
                        old = editor_input_popup(term, "Replace From", "", editor_find_history(), redraw_editor)
                        if not old:
                            msg = "replace canceled"
                            continue
                        new = editor_input_popup(term, "Replace To", "", editor_replace_history(), redraw_editor)
                        if new is None:
                            msg = "replace canceled"
                            continue
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                        count = editor_replace(lines, old, new)
                        dirty = count > 0
                        msg = f"replaced: {count}"
                        continue
                    if action == "vi_mode":
                        EDITOR_STATE.vi_mode = not EDITOR_STATE.vi_mode
                        vi_command = EDITOR_STATE.vi_mode
                        vi_count = ""
                        vi_op = ""
                        vi_op_count = ""
                        mark = None
                        select_mode = False
                        rect_select = False
                        save_stat()
                        msg = f"vi mode: {'on' if EDITOR_STATE.vi_mode else 'off'}"
                        continue
                    if action == "normalize_eol":
                        if not edit_mode:
                            msg = read_only_bell(term)
                            continue
                        target = default_eol()
                        if eol == target:
                            msg = f"eol already {target}"
                        else:
                            eol = target
                            dirty = True
                            saved = False
                            msg = f"eol: {target}"
                        continue
                    if action == "line_draw":
                        if not edit_mode:
                            msg = read_only_bell(term)
                            continue
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                        lines, cy, cx = editor_line_draw_mode(term, lines, cy, cx, insert_mode, colors)
                        dirty = True
                        msg = "line draw"
                        continue
                    if action == "insert_mode":
                        if not edit_mode:
                            msg = read_only_bell(term)
                            continue
                        mark = None
                        select_mode = False
                        rect_select = False
                        insert_mode = not insert_mode
                        msg = "INS" if insert_mode else "OVR"
                        continue
                    if action == "mouse_cursor":
                        EDITOR_STATE.mouse_cursor = not EDITOR_STATE.mouse_cursor
                        term.set_mouse(True)
                        save_stat()
                        msg = f"mouse cursor: {'on' if EDITOR_STATE.mouse_cursor else 'off'}"
                        continue
                    if action == "wheel_scroll":
                        EDITOR_STATE.wheel_scroll = not EDITOR_STATE.wheel_scroll
                        term.set_mouse(True)
                        save_stat()
                        msg = f"wheel scroll: {'on' if EDITOR_STATE.wheel_scroll else 'off'}"
                        continue
                    if action == "ruler":
                        EDITOR_STATE.ruler = not EDITOR_STATE.ruler
                        save_stat()
                        msg = f"ruler: {'on' if EDITOR_STATE.ruler else 'off'}"
                        continue
                    if action == "cursor_underline":
                        EDITOR_STATE.cursor_underline = not EDITOR_STATE.cursor_underline
                        save_stat()
                        msg = f"cursor underline: {'on' if EDITOR_STATE.cursor_underline else 'off'}"
                        continue
                    if action == "show_enter":
                        EDITOR_STATE.show_enter = not EDITOR_STATE.show_enter
                        save_stat()
                        msg = f"show enter: {'on' if EDITOR_STATE.show_enter else 'off'}"
                        continue
                    if action == "show_tab":
                        EDITOR_STATE.show_tab = not EDITOR_STATE.show_tab
                        save_stat()
                        msg = f"show tab: {'on' if EDITOR_STATE.show_tab else 'off'}"
                        continue
                    if action == "show_bin":
                        EDITOR_STATE.show_bin = not EDITOR_STATE.show_bin
                        save_stat()
                        msg = f"show bin: {'on' if EDITOR_STATE.show_bin else 'off'}"
                        continue
                    if action in ("undo", "redo"):
                        lines, cy, cx, undo, redo, msg = editor_undo_redo(action, lines, cy, cx, undo, redo)
                        mark = None
                        rect_select = False
                        dirty = True
                        continue
                    if action == "select_all":
                        cy, cx, mark, select_mode, rect_select, msg = editor_select_all(lines)
                        continue
                    if editor_action_changes(action, mark, (cy, cx), EDITOR_STATE.clips):
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines, cy, cx, mark, dirty, find_text, msg = editor_action(term, action, lines, cy, cx, mark, dirty, find_text, edit_mode, rect_select, redraw_editor)
                    if action in ("copy", "cut", "paste", "clip_list"):
                        select_mode = False
                        rect_select = False
            elif EDITOR_STATE.vi_mode and key == KEY_ESCAPE and (not edit_mode or not dirty):
                return close_buffer(saved and not dirty)
            elif EDITOR_STATE.vi_mode and not vi_command and key == KEY_ESCAPE:
                vi_command = True
                vi_insert_undo_open = False
                vi_count = ""
                vi_op = ""
                vi_op_count = ""
                msg = "vi command"
            elif EDITOR_STATE.vi_mode and vi_command:
                if key == KEY_ENTER and not edit_mode:
                    return close_buffer(saved and not dirty)
                if key == "\x01":
                    cy, cx, mark, select_mode, rect_select, msg = editor_select_all(lines)
                    vi_count = ""
                    vi_op = ""
                    vi_op_count = ""
                    continue
                if select_mode and not rect_select and key in ("y", "d"):
                    start, end = vi_visual_range(lines, mark or (cy, cx), (cy, cx))
                    if key == "y":
                        editor_push_clip(editor_selected_text(lines, start, end))
                        msg = "yanked"
                    elif not edit_mode:
                        msg = read_only_bell(term)
                    else:
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                        lines, cy, cx, text = editor_delete_selection(lines, start, end)
                        editor_push_clip(text)
                        dirty = True
                        msg = "deleted"
                    mark = None
                    select_mode = False
                    vi_count = ""
                    vi_op = ""
                    vi_op_count = ""
                    continue
                if key.isdigit() and (key != "0" or vi_count or vi_op):
                    if vi_op:
                        vi_op_count += key
                    else:
                        vi_count += key
                    msg = (vi_op or "") + (vi_op_count if vi_op else vi_count)
                    continue
                count = int(vi_count or "1")
                op_count = int(vi_op_count or vi_count or "1")
                if vi_op:
                    if key == vi_op and vi_op in ("d", "y"):
                        if vi_op == "y":
                            editor_push_clip(vi_yank_lines(lines, cy, op_count))
                            msg = f"yanked: {op_count} line(s)"
                        elif not edit_mode:
                            msg = read_only_bell(term)
                        else:
                            push_undo(undo, lines, cy, cx)
                            redo.clear()
                            lines, cy, cx, text = vi_delete_lines(lines, cy, op_count)
                            editor_push_clip(text)
                            dirty = True
                            msg = f"deleted: {op_count} line(s)"
                        vi_op = ""
                        vi_count = ""
                        vi_op_count = ""
                        continue
                    if vi_op == "c" and key == "e":
                        if not edit_mode:
                            msg = read_only_bell(term)
                        else:
                            push_undo(undo, lines, cy, cx)
                            redo.clear()
                            start = (cy, cx)
                            end = vi_range_end(lines, start, vi_motion(lines, cy, cx, "e", op_count, body), True)
                            lines, cy, cx, text = editor_delete_selection(lines, start, end)
                            editor_push_clip(text)
                            dirty = True
                            enter_vi_insert(True)
                            msg = "change"
                        vi_op = ""
                        vi_count = ""
                        vi_op_count = ""
                        continue
                    if key == "G":
                        target = int(vi_op_count or vi_count) - 1 if (vi_op_count or vi_count) else len(lines) - 1
                        target = min(max(0, target), len(lines) - 1)
                        first = min(cy, target)
                        last = max(cy, target)
                        line_count = last - first + 1
                        if vi_op == "y":
                            editor_push_clip("\n".join(lines[first:last + 1]) + "\n")
                            msg = f"yanked: {line_count} line(s)"
                        elif not edit_mode:
                            msg = read_only_bell(term)
                        else:
                            push_undo(undo, lines, cy, cx)
                            redo.clear()
                            text = "\n".join(lines[first:last + 1]) + "\n"
                            del lines[first:last + 1]
                            if not lines:
                                lines = [""]
                            cy = min(first, len(lines) - 1)
                            cx = 0
                            editor_push_clip(text)
                            dirty = True
                            msg = f"deleted: {line_count} line(s)"
                        vi_op = ""
                        vi_count = ""
                        vi_op_count = ""
                        continue
                    if key in ("h", "j", "k", "l", "w", "b", "e", KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_PGUP, KEY_PGDN, "\x15", "\x04"):
                        start = (cy, cx)
                        ny, nx = vi_motion(lines, cy, cx, key, op_count, body)
                        if vi_motion_linewise(key):
                            first = min(cy, ny)
                            last = max(cy, ny)
                            line_count = last - first + 1
                            if vi_op == "y":
                                editor_push_clip("\n".join(lines[first:last + 1]) + "\n")
                                msg = f"yanked: {line_count} line(s)"
                            elif not edit_mode:
                                msg = read_only_bell(term)
                            else:
                                push_undo(undo, lines, cy, cx)
                                redo.clear()
                                text = "\n".join(lines[first:last + 1]) + "\n"
                                del lines[first:last + 1]
                                if not lines:
                                    lines = [""]
                                cy = min(first, len(lines) - 1)
                                cx = 0
                                editor_push_clip(text)
                                dirty = True
                                msg = f"deleted: {line_count} line(s)"
                        else:
                            end = vi_range_end(lines, start, (ny, nx), key == "e")
                            if vi_op == "y":
                                editor_push_clip(editor_selected_text(lines, start, end))
                                cy, cx = ny, nx
                                msg = "yanked"
                            elif not edit_mode:
                                msg = read_only_bell(term)
                            else:
                                push_undo(undo, lines, cy, cx)
                                redo.clear()
                                lines, cy, cx, text = editor_delete_selection(lines, start, end)
                                editor_push_clip(text)
                                dirty = True
                                msg = "deleted"
                        vi_op = ""
                        vi_count = ""
                        vi_op_count = ""
                        continue
                    msg = f"vi {vi_op}?"
                    vi_op = ""
                    vi_count = ""
                    vi_op_count = ""
                    continue
                if key == "e" and not edit_mode:
                    edit_mode = True
                    msg = "edit mode"
                    vi_count = ""
                    continue
                if key in ("d", "y", "c"):
                    vi_op = key
                    vi_op_count = ""
                    msg = key
                    continue
                if key in ("h", "j", "k", "l", "w", "b", "e", KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_PGUP, KEY_PGDN, "\x15", "\x04"):
                    if select_mode and mark is None:
                        mark = (cy, cx)
                    cy, cx = vi_motion(lines, cy, cx, key, count, body)
                    if not select_mode:
                        mark = None
                    vi_count = ""
                    msg = "vi command"
                    continue
                if key == "G":
                    cy = min(max(0, int(vi_count) - 1), len(lines) - 1) if vi_count else len(lines) - 1
                    cx = min(cx, len(lines[cy]))
                    mark = None
                    vi_count = ""
                    msg = "vi command"
                    continue
                if key == "0":
                    cx = 0
                    vi_count = ""
                    msg = "vi command"
                    continue
                if key == "i":
                    if not edit_mode:
                        msg = read_only_bell(term)
                    else:
                        enter_vi_insert(False)
                        mark = None
                        select_mode = False
                        msg = "vi insert"
                    vi_count = ""
                    continue
                if key == "a":
                    if not edit_mode:
                        msg = read_only_bell(term)
                    else:
                        cx = min(len(lines[cy]), cx + 1)
                        enter_vi_insert(False)
                        mark = None
                        select_mode = False
                        msg = "vi append"
                    vi_count = ""
                    continue
                if key == "v":
                    if select_mode and not rect_select:
                        mark = None
                        select_mode = False
                        msg = "visual off"
                    else:
                        mark = (cy, cx)
                        select_mode = True
                        rect_select = False
                        msg = "visual"
                    vi_count = ""
                    continue
                if key == "x":
                    if not edit_mode:
                        msg = read_only_bell(term)
                    elif cx < len(lines[cy]):
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                        end = min(len(lines[cy]), cx + count)
                        editor_push_clip(lines[cy][cx:end])
                        lines[cy] = lines[cy][:cx] + lines[cy][end:]
                        dirty = True
                        msg = "deleted"
                    vi_count = ""
                    continue
                if key == "p":
                    clip = EDITOR_STATE.clips[-1] if EDITOR_STATE.clips else ""
                    if not edit_mode:
                        msg = read_only_bell(term)
                    elif clip:
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                        lines, cy, cx = vi_paste_after(lines, cy, cx, clip)
                        dirty = True
                        msg = "pasted"
                    else:
                        msg = "clipboard empty"
                    vi_count = ""
                    continue
                if key == "u":
                    lines, cy, cx, undo, redo, msg = editor_undo_redo("undo", lines, cy, cx, undo, redo)
                    mark = None
                    select_mode = False
                    rect_select = False
                    dirty = True
                    vi_count = ""
                    continue
                if key == "J":
                    if not edit_mode:
                        msg = read_only_bell(term)
                    elif cy + 1 < len(lines):
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                        lines, cy, cx = vi_join_lines(lines, cy, count)
                        dirty = True
                        msg = "joined"
                    else:
                        msg = "last line"
                    vi_count = ""
                    continue
                if key == "/":
                    text = editor_vi_line_input(term, "/", find_text, editor_find_history(), redraw_editor)
                    if text:
                        find_text = text
                        pos = editor_find(lines, find_text, cy, cx - 1)
                        if pos is not None:
                            cy, cx = pos
                            mark = (cy, cx + len(find_text))
                            msg = "found"
                        else:
                            msg = "not found"
                    else:
                        msg = "find canceled"
                    vi_count = ""
                    continue
                if key == "n":
                    pos = editor_find(lines, find_text, cy, cx)
                    if pos is not None:
                        cy, cx = pos
                        mark = (cy, cx + len(find_text))
                        msg = "found"
                    else:
                        msg = "not found"
                    vi_count = ""
                    continue
                if key == ":":
                    command = editor_vi_line_input(term, ":", "", [], redraw_editor)
                    vi_count = ""
                    if command is None:
                        msg = "command canceled"
                        continue
                    stripped = command.strip()
                    bare_command = vi_command_bare(stripped)
                    if bare_command == "w":
                        if not edit_mode:
                            msg = read_only_bell(term)
                        elif editor_save(path, lines, eol, encoding):
                            dirty = False
                            saved = True
                            msg = "saved"
                        else:
                            msg = "save failed"
                        continue
                    if bare_command == "q":
                        if not dirty or editor_confirm(term, "Close? y/N"):
                            return close_buffer(saved and not dirty)
                        msg = "close canceled"
                        continue
                    if bare_command == "q!":
                        return close_buffer(False)
                    if bare_command == "wq":
                        if not edit_mode:
                            msg = read_only_bell(term)
                            continue
                        if editor_save(path, lines, eol, encoding):
                            dirty = False
                            saved = True
                            return close_buffer(True)
                        msg = "save failed"
                        continue
                    if stripped.startswith(":s") or stripped.startswith("s"):
                        if not edit_mode:
                            msg = read_only_bell(term)
                            continue
                        try:
                            new_line, count = vi_substitute_line(lines[cy], stripped)
                        except ValueError as exc:
                            msg = f"substitute: {exc}"
                            continue
                        if count:
                            push_undo(undo, lines, cy, cx)
                            redo.clear()
                            lines[cy] = new_line
                            cx = min(cx, len(lines[cy]))
                            dirty = True
                        msg = f"substituted: {count}"
                        continue
                    msg = "unknown command"
                    continue
                vi_count = ""
                msg = "vi command"
            elif key in (KEY_ESCAPE, "\x11"):
                if dirty and not editor_confirm(term, "Close? y/N"):
                    msg = "close canceled"
                    continue
                return close_buffer(saved and not dirty)
            elif key == "\x0c":
                result = editor_calc_popup(term, lines, cy, cx, colors)
                if result:
                    if not edit_mode:
                        msg = read_only_bell(term)
                        continue
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines[cy] = editor_put_text(lines[cy], cx, result, insert_mode)
                    cx += len(result)
                    dirty = True
                    msg = "calc pasted"
            elif key in ("\x01", "\x18", "\x03", "\x16", "\x06", "\x0e", "\x19", "\x1a", "\x12", "\x17", "\x0b", KEY_CTRL_SHIFT_V, KEY_F9, KEY_SHIFT_F9, KEY_F10, KEY_SHIFT_F10):
                action = {"\x01": "select_all", "\x18": "cut", "\x03": "copy", "\x16": "paste", "\x06": "find", "\x0e": "find_next", "\x19": "delete_line", "\x1a": "undo", "\x12": "redo", "\x17": "delete_word", "\x0b": "delete_to_eol", KEY_CTRL_SHIFT_V: "clip_list", KEY_F9: "copy", KEY_SHIFT_F9: "cut", KEY_F10: "paste", KEY_SHIFT_F10: "clip_list"}[key]
                if action in ("undo", "redo"):
                    lines, cy, cx, undo, redo, msg = editor_undo_redo(action, lines, cy, cx, undo, redo)
                    mark = None
                    rect_select = False
                    dirty = True
                    continue
                if action == "select_all":
                    cy, cx, mark, select_mode, rect_select, msg = editor_select_all(lines)
                    continue
                if editor_action_changes(action, mark, (cy, cx), EDITOR_STATE.clips):
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                lines, cy, cx, mark, dirty, find_text, msg = editor_action(term, action, lines, cy, cx, mark, dirty, find_text, edit_mode, rect_select, redraw_editor)
                if action in ("copy", "cut", "paste", "clip_list"):
                    select_mode = False
                    rect_select = False
            elif key == KEY_F8:
                if select_mode:
                    select_mode = False
                    mark = None
                    rect_select = False
                    msg = "select off"
                else:
                    select_mode = True
                    rect_select = False
                    mark = (cy, cx)
                    msg = "select on"
            elif key == KEY_SHIFT_F8:
                if select_mode and rect_select:
                    select_mode = False
                    rect_select = False
                    mark = None
                    msg = "rect off"
                else:
                    select_mode = True
                    rect_select = True
                    mark = (cy, cx)
                    msg = "rect on"
            elif key in ("e", "E") and not edit_mode:
                edit_mode = True
                msg = "edit mode"
            elif key == KEY_INSERT:
                msg = "Settings: Insert/Overwrite"
            elif key in (KEY_SHIFT_UP, KEY_SHIFT_DOWN, KEY_SHIFT_LEFT, KEY_SHIFT_RIGHT):
                if mark is None:
                    mark = (cy, cx)
                cy, cx = editor_move(lines, cy, cx, {
                    KEY_SHIFT_UP: KEY_UP,
                    KEY_SHIFT_DOWN: KEY_DOWN,
                    KEY_SHIFT_LEFT: KEY_LEFT,
                    KEY_SHIFT_RIGHT: KEY_RIGHT,
                }[key], body)
            elif key == KEY_CTRL_LEFT:
                if select_mode and mark is None:
                    mark = (cy, cx)
                cx = 0
                if not select_mode:
                    mark = None
            elif key == KEY_CTRL_RIGHT:
                if select_mode and mark is None:
                    mark = (cy, cx)
                cx = len(lines[cy])
                if not select_mode:
                    mark = None
            elif key == KEY_CTRL_UP:
                if select_mode and mark is None:
                    mark = (cy, cx)
                cy = 0
                cx = min(cx, len(lines[cy]))
                top = 0
                if not select_mode:
                    mark = None
            elif key == KEY_CTRL_DOWN:
                if select_mode and mark is None:
                    mark = (cy, cx)
                cy = len(lines) - 1
                cx = min(cx, len(lines[cy]))
                if not select_mode:
                    mark = None
            elif key == KEY_UP:
                if select_mode and mark is None:
                    mark = (cy, cx)
                cy, cx = editor_move(lines, cy, cx, key, body)
                if not select_mode:
                    mark = None
            elif key == KEY_DOWN:
                if select_mode and mark is None:
                    mark = (cy, cx)
                cy, cx = editor_move(lines, cy, cx, key, body)
                if not select_mode:
                    mark = None
            elif key == KEY_LEFT:
                if select_mode and mark is None:
                    mark = (cy, cx)
                cy, cx = editor_move(lines, cy, cx, key, body)
                if not select_mode:
                    mark = None
            elif key == KEY_RIGHT:
                if select_mode and mark is None:
                    mark = (cy, cx)
                cy, cx = editor_move(lines, cy, cx, key, body)
                if not select_mode:
                    mark = None
            elif key == KEY_HOME:
                cx = 0
                mark = None
            elif key == KEY_END:
                cx = len(lines[cy])
                mark = None
            elif key == KEY_PGUP:
                cy, cx = editor_move(lines, cy, cx, key, body)
                mark = None
            elif key == KEY_PGDN:
                cy, cx = editor_move(lines, cy, cx, key, body)
                mark = None
            elif key == KEY_ENTER:
                if not edit_mode:
                    return close_buffer(saved and not dirty)
                if mark is not None and mark != (cy, cx):
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines, cy, cx, _ = editor_delete_rect(lines, mark, (cy, cx)) if rect_select else editor_delete_selection(lines, mark, (cy, cx))
                    mark = None
                else:
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                lines[cy:cy + 1] = [lines[cy][:cx], lines[cy][cx:]]
                cy += 1
                cx = 0
                dirty = True
            elif key == KEY_BACKSPACE:
                if not edit_mode:
                    msg = read_only_bell(term)
                    continue
                if mark is not None and mark != (cy, cx):
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines, cy, cx, _ = editor_delete_rect(lines, mark, (cy, cx)) if rect_select else editor_delete_selection(lines, mark, (cy, cx))
                    mark = None
                    dirty = True
                    continue
                if cx > 0:
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines[cy] = lines[cy][:cx - 1] + lines[cy][cx:]
                    cx -= 1
                    dirty = True
                elif cy > 0:
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    cx = len(lines[cy - 1])
                    lines[cy - 1] += lines[cy]
                    del lines[cy]
                    cy -= 1
                    dirty = True
            elif key == KEY_DELETE:
                if not edit_mode:
                    msg = read_only_bell(term)
                    continue
                if mark is not None and mark != (cy, cx):
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines, cy, cx, _ = editor_delete_rect(lines, mark, (cy, cx)) if rect_select else editor_delete_selection(lines, mark, (cy, cx))
                    mark = None
                    dirty = True
                    continue
                if cx < len(lines[cy]):
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines[cy] = lines[cy][:cx] + lines[cy][cx + 1:]
                    dirty = True
                elif cy + 1 < len(lines):
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines[cy] += lines[cy + 1]
                    del lines[cy + 1]
                    dirty = True
            elif key in ("\t", KEY_SHIFT_TAB):
                if not edit_mode:
                    msg = read_only_bell(term)
                    continue
                if not ensure_vi_insert_undo():
                    push_undo(undo, lines, cy, cx)
                    redo.clear()
                lines, cy, cx, mark, msg = editor_indent_lines(lines, cy, cx, mark, key != KEY_SHIFT_TAB)
                dirty = True
            elif is_text_input(key):
                if not edit_mode:
                    msg = read_only_bell(term)
                    continue
                if mark is not None and mark != (cy, cx):
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                    lines, cy, cx, _ = editor_delete_rect(lines, mark, (cy, cx)) if rect_select else editor_delete_selection(lines, mark, (cy, cx))
                    mark = None
                else:
                    if not ensure_vi_insert_undo():
                        push_undo(undo, lines, cy, cx)
                        redo.clear()
                lines[cy] = editor_put_text(lines[cy], cx, key, insert_mode)
                cx += len(key)
                dirty = True
    finally:
        term.hide_cursor()


def editor_pane_size_mode(term: Terminal, buffers: list[EditorBuffer], pane_buffers: list[int], active_pane: int, split_mode: str, ratio: float, colors: dict[str, str] | None, shell: EditorShellState | None = None, shell_focus: bool = False) -> float:
    if split_mode == "full":
        return ratio
    msg = "PainSize: arrows  Enter/F7 ok"
    while True:
        editor_draw_split(term, buffers, pane_buffers, active_pane, split_mode, ratio, colors, msg, shell=shell, shell_focus=shell_focus)
        key = normalize_move_key(read_key())
        if key in (KEY_ENTER, KEY_F7, KEY_ESCAPE):
            return ratio
        if split_mode == "v":
            if key == KEY_LEFT:
                ratio = max(0.25, ratio - 0.04)
            elif key == KEY_RIGHT:
                ratio = min(0.75, ratio + 0.04)
        elif split_mode in ("h", "shell"):
            if key == KEY_UP:
                ratio = max(0.25, ratio - 0.04)
            elif key == KEY_DOWN:
                ratio = min(0.75, ratio + 0.04)
        msg = f"PainSize: {int(ratio * 100)}%"


def sync_same_path_buffers(buffers: list[EditorBuffer], source_index: int) -> None:
    if not (0 <= source_index < len(buffers)):
        return
    source = buffers[source_index]
    if source.readonly or not source.edit_mode:
        return
    for index, buffer in enumerate(buffers):
        if index == source_index or buffer.path != source.path:
            continue
        if buffer.readonly or not buffer.edit_mode:
            continue
        buffer.lines = source.lines[:]
        buffer.dirty = source.dirty
        buffer.saved = source.saved
        buffer.edit_mode = source.edit_mode
        buffer.readonly = source.readonly
        buffer.encoding = source.encoding
        buffer.eol = source.eol
        buffer.show_bin = source.show_bin


def clone_editor_buffer(source: EditorBuffer) -> EditorBuffer:
    return EditorBuffer(
        source.path,
        source.lines[:],
        source.readonly,
        source.cy,
        source.cx,
        source.top,
        source.left,
        source.mark,
        source.select_mode,
        source.rect_select,
        source.find_text,
        source.insert_mode,
        source.edit_mode,
        list(source.undo or []),
        list(source.redo or []),
        source.dirty,
        source.saved,
        source.msg,
        source.encoding,
        source.eol,
        source.show_bin,
    )


def editor_draw_split(term: Terminal, buffers: list[EditorBuffer], pane_buffers: list[int], active_pane: int, split_mode: str, ratio: float, colors: dict[str, str] | None, msg: str, vi_status: str = "", shell: EditorShellState | None = None, shell_focus: bool = False) -> None:
    columns, rows = term.size()
    active_buffer = buffers[pane_buffers[active_pane]]
    bar = editor_bar_color(colors, active_buffer.edit_mode)
    command_rows = editor_vi_command_rows()
    term.move(1, 1)
    term.write(color_text(fit(editor_menu_bar_text(), columns), bar) + "\n")
    body_rows = max(1, rows - 3 - command_rows)
    shell_cursor: tuple[int, int] | None = None
    if split_mode == "v":
        left_w = max(20, min(columns - 21, int(columns * ratio)))
        right_w = max(20, columns - left_w - 1)
        height = body_rows
        editor_draw_pane(term, 2, 1, left_w, height, buffers[pane_buffers[0]], 0 == active_pane, colors)
        sep = reverse(" ")
        for y in range(body_rows):
            term.move(2 + y, left_w + 1)
            term.write(sep)
        editor_draw_pane(term, 2, left_w + 2, right_w, height, buffers[pane_buffers[1]], 1 == active_pane, colors)
    else:
        top_h = max(3, min(body_rows - 4, int(body_rows * ratio)))
        bottom_h = max(3, body_rows - top_h - 1)
        editor_draw_pane(term, 2, 1, columns, top_h, buffers[pane_buffers[0]], 0 == active_pane and not shell_focus, colors)
        term.move(2 + top_h, 1)
        term.write(reverse(" " * columns))
        if split_mode == "shell" and shell is not None:
            shell_cursor = draw_editor_shell(term, 3 + top_h, 1, columns, bottom_h, shell, shell_focus, colors)
        else:
            editor_draw_pane(term, 3 + top_h, 1, columns, bottom_h, buffers[pane_buffers[1]], 1 == active_pane, colors)
    vi = f" {vi_status} " if vi_status else ""
    focus = "SHELL" if shell_focus else f"PANE:{active_pane + 1}"
    status = f" SPLIT:{split_mode.upper()}  {focus}  {active_buffer.encoding} {active_buffer.eol} {vi} {msg} "
    term.move(rows - command_rows, 1)
    term.write(color_text(fit(status, columns), bar))
    if command_rows:
        term.move(rows, 1)
        term.write(" " * columns)
    if shell_cursor is not None and shell_focus:
        cur_row, cur_col = shell_cursor
    else:
        cur_row, cur_col = editor_split_cursor_position(buffers[pane_buffers[active_pane]], active_pane, split_mode, ratio, columns, rows)
    term.move(cur_row, cur_col)
    term.flush()


def editor_draw_pane(term: Terminal, row: int, col: int, width: int, height: int, buffer: EditorBuffer, active: bool, colors: dict[str, str] | None) -> None:
    bar = editor_bar_color(colors, buffer.edit_mode)
    title = f" {buffer.path.name}{'*' if buffer.dirty else ''}  {'EDIT' if buffer.edit_mode else 'READ'}  {buffer.encoding} {buffer.eol} "
    term.move(row, col)
    term.write((reverse(fit(title, width)) if active else underline(fit(title, width))))
    ruler_offset = 1 if EDITOR_STATE.ruler else 0
    body = max(0, height - 1 - ruler_offset)
    gutter = max(6, len(str(len(buffer.lines))) + 2) if EDITOR_STATE.line_numbers else 0
    text_w = max(1, width - gutter)
    if EDITOR_STATE.ruler:
        cursor_col = editor_text_width(buffer.lines[buffer.cy][:buffer.cx], buffer.show_bin) if active and 0 <= buffer.cy < len(buffer.lines) else None
        if cursor_col is not None and EDITOR_STATE.wrap:
            cursor_col %= max(1, text_w)
        term.move(row + 1, col)
        term.write(pad_ansi((" " * gutter) + ruler_line(text_w, 0 if EDITOR_STATE.wrap else buffer.left, cursor_col), width))
    visual_rows = editor_visual_rows(buffer.lines, buffer.top, body, text_w, buffer.show_bin) if EDITOR_STATE.wrap else [(buffer.top + screen_row, buffer.left) for screen_row in range(body)]
    for screen_row, (index, row_left) in enumerate(visual_rows):
        term.move(row + 1 + ruler_offset + screen_row, col)
        if index < len(buffer.lines):
            prefix = f"{index + 1:>{gutter - 2}}: " if gutter and row_left == 0 else (" " * gutter if gutter else "")
            cursor = (buffer.cy, buffer.cx) if active else (-1, -1)
            text = editor_row(buffer.lines[index], index, buffer.mark if active else None, cursor, row_left, text_w, buffer.rect_select if active else False, syntax_for_path(buffer.path), buffer.eol, colors, buffer.show_bin)
            line = pad_ansi(prefix + text, width)
            term.write(underline_ansi(line) if EDITOR_STATE.cursor_underline and index == buffer.cy else line)
        else:
            term.write(" " * width)


def editor_split_cursor_position(buffer: EditorBuffer, active_pane: int, split_mode: str, ratio: float, columns: int, rows: int) -> tuple[int, int]:
    body_rows = max(1, rows - 3 - editor_vi_command_rows())
    if split_mode == "v":
        left_w = max(20, min(columns - 21, int(columns * ratio)))
        width = left_w if active_pane == 0 else max(20, columns - left_w - 1)
        row = 2
        col = 1 if active_pane == 0 else left_w + 2
        height = body_rows
    else:
        top_h = max(3, min(body_rows - 4, int(body_rows * ratio)))
        row = 2 if active_pane == 0 else 3 + top_h
        col = 1
        width = columns
        height = top_h if active_pane == 0 or split_mode == "shell" else max(3, body_rows - top_h - 1)
    ruler_offset = 1 if EDITOR_STATE.ruler else 0
    body = max(0, height - 1 - ruler_offset)
    gutter = max(6, len(str(len(buffer.lines))) + 2) if EDITOR_STATE.line_numbers else 0
    text_w = max(1, width - gutter)
    if EDITOR_STATE.wrap:
        cursor_w = editor_text_width(buffer.lines[buffer.cy][:buffer.cx], buffer.show_bin)
        screen_row = editor_visual_cursor_row(buffer.lines, buffer.top, buffer.cy, buffer.cx, text_w, body, buffer.show_bin)
        screen_col = gutter + (cursor_w % max(1, text_w)) + 1
    else:
        screen_row = buffer.cy - buffer.top
        screen_col = gutter + editor_text_width(buffer.lines[buffer.cy][:buffer.cx], buffer.show_bin) - buffer.left + 1
    screen_row = min(max(0, screen_row), max(0, body - 1))
    screen_col = max(1, min(width, screen_col))
    return row + 1 + ruler_offset + screen_row, col + screen_col - 1


def editor_active_pane_text_size(split_mode: str, active_pane: int, ratio: float, columns: int, rows: int) -> tuple[int, int]:
    body_rows = max(1, rows - 3 - editor_vi_command_rows())
    if split_mode == "v":
        left_w = max(20, min(columns - 21, int(columns * ratio)))
        width = left_w if active_pane == 0 else max(20, columns - left_w - 1)
        height = body_rows
    elif split_mode in ("h", "shell"):
        top_h = max(3, min(body_rows - 4, int(body_rows * ratio)))
        width = columns
        height = top_h if active_pane == 0 or split_mode == "shell" else max(3, body_rows - top_h - 1)
    else:
        width = columns
        height = max(1, rows - 2)
    return width, max(1, height - 1 - (1 if EDITOR_STATE.ruler else 0))


def editor_pane_rect(split_mode: str, active_pane: int, ratio: float, columns: int, rows: int) -> tuple[int, int, int, int]:
    body_rows = max(1, rows - 3 - editor_vi_command_rows())
    if split_mode == "v":
        left_w = max(20, min(columns - 21, int(columns * ratio)))
        if active_pane == 0:
            return 2, 1, left_w, body_rows
        return 2, left_w + 2, max(20, columns - left_w - 1), body_rows
    if split_mode in ("h", "shell"):
        top_h = max(3, min(body_rows - 4, int(body_rows * ratio)))
        if active_pane == 0:
            return 2, 1, columns, top_h
        return 3 + top_h, 1, columns, max(3, body_rows - top_h - 1)
    return 2, 1, columns, max(1, rows - 2)


def editor_shell_height(ratio: float, columns: int, rows: int) -> int:
    body_rows = max(1, rows - 3 - editor_vi_command_rows())
    top_h = max(3, min(body_rows - 4, int(body_rows * ratio)))
    return max(3, body_rows - top_h - 1)


def editor_draw(term: Terminal, path: Path, lines: list[str], cy: int, cx: int, top: int, left: int, body: int, gutter: int, text_w: int, mark: tuple[int, int] | None, rect_select: bool, dirty: bool, msg: str, insert_mode: bool, edit_mode: bool, colors: dict[str, str] | None, buffer_index: int = 0, buffer_count: int = 1, encoding: str = "UTF-8", eol: str = "LF", vi_status: str = "", show_bin: bool = False) -> None:
    columns, rows = term.size()
    command_rows = editor_vi_command_rows()
    bar = editor_bar_color(colors, edit_mode)
    term.move(1, 1)
    term.write(color_text(fit(editor_menu_bar_text(), columns), bar) + "\n")
    if EDITOR_STATE.ruler:
        cursor_col = editor_text_width(lines[cy][:cx], show_bin)
        if EDITOR_STATE.wrap:
            cursor_col %= max(1, text_w)
        term.write((" " * gutter) + ruler_line(max(0, columns - gutter), 0 if EDITOR_STATE.wrap else left, cursor_col) + "\n")
    visual_rows = editor_visual_rows(lines, top, body, text_w, show_bin) if EDITOR_STATE.wrap else [(top + row, left) for row in range(body)]
    for screen_row, (index, row_left) in enumerate(visual_rows):
        if index < len(lines):
            prefix = f"{index + 1:>{gutter - 2}}: " if gutter and row_left == 0 else (" " * gutter if gutter else "")
            row = editor_row(lines[index], index, mark, (cy, cx), row_left, text_w, rect_select, syntax_for_path(path), eol, colors, show_bin)
            line = pad_ansi(prefix + row, columns)
            term.write((underline_ansi(line) if EDITOR_STATE.cursor_underline and index == cy else line) + "\n")
        else:
            term.write(" " * columns + "\n")
    vi = f" {vi_status} " if vi_status else ""
    status = f" {path} {'*' if dirty else ''}  BUF:{buffer_index + 1}/{buffer_count}  {'EDIT' if edit_mode else 'READ'}  {'INS' if insert_mode else 'OVR'} {vi} {encoding} {eol}  TAB:{EDITOR_STATE.tab_spaces}  {'WRAP' if EDITOR_STATE.wrap else 'SCROLL'} "
    if msg:
        status += f" {msg} "
    term.write(color_text(fit(status, columns), bar))
    if command_rows:
        term.move(rows, 1)
        term.write(" " * columns)
    if EDITOR_STATE.wrap:
        cursor_w = editor_text_width(lines[cy][:cx], show_bin)
        screen_row = editor_visual_cursor_row(lines, top, cy, cx, text_w, body, show_bin)
        screen_col = gutter + (cursor_w % max(1, text_w)) + 1
    else:
        screen_row = cy - top
        screen_col = gutter + editor_text_width(lines[cy][:cx], show_bin) - left + 1
    term.move(screen_row + 2 + (1 if EDITOR_STATE.ruler else 0), max(gutter + 1, min(columns, screen_col)))
    term.flush()


def editor_vi_command_rows() -> int:
    return 1 if EDITOR_STATE.vi_mode else 0


def editor_bar_color(colors: dict[str, str] | None, edit_mode: bool) -> str:
    if not colors:
        return "30;46" if edit_mode else "30;43"
    return colors["editor_edit_bar_color"] if edit_mode else colors["editor_readonly_bar_color"]


def editor_visual_rows(lines: list[str], top: int, body: int, width: int, show_bin: bool = False) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    for index in range(top, len(lines)):
        line_width = max(1, editor_text_width(lines[index], show_bin))
        parts = max(1, (line_width + width - 1) // width)
        for part in range(parts):
            rows.append((index, part * width))
            if len(rows) >= body:
                return rows
    while len(rows) < body:
        rows.append((len(lines), 0))
    return rows


def editor_visual_cursor_row(lines: list[str], top: int, cy: int, cx: int, width: int, body: int, show_bin: bool = False) -> int:
    row = editor_visual_cursor_offset(lines, top, cy, cx, width, show_bin)
    return min(body - 1, row)


def editor_visual_cursor_offset(lines: list[str], top: int, cy: int, cx: int, width: int, show_bin: bool = False) -> int:
    row = 0
    for index in range(top, cy):
        line_width = max(1, editor_text_width(lines[index], show_bin))
        row += max(1, (line_width + width - 1) // width)
    row += editor_text_width(lines[cy][:cx], show_bin) // max(1, width)
    return row


def editor_ensure_wrap_visible(lines: list[str], top: int, cy: int, cx: int, width: int, body: int, show_bin: bool = False) -> int:
    top = min(max(0, top), max(0, len(lines) - 1))
    if cy < top:
        return cy
    while top < cy and editor_visual_cursor_offset(lines, top, cy, cx, width, show_bin) >= body:
        top += 1
    return top


def editor_move(lines: list[str], cy: int, cx: int, key: str, page: int) -> tuple[int, int]:
    if key == KEY_UP:
        cy = max(0, cy - 1)
        cx = min(cx, len(lines[cy]))
    elif key == KEY_DOWN:
        cy = min(len(lines) - 1, cy + 1)
        cx = min(cx, len(lines[cy]))
    elif key == KEY_LEFT:
        if cx > 0:
            cx -= 1
        elif cy > 0:
            cy -= 1
            cx = len(lines[cy])
    elif key == KEY_RIGHT:
        if cx < len(lines[cy]):
            cx += 1
        elif cy + 1 < len(lines):
            cy += 1
            cx = 0
    elif key == KEY_PGUP:
        cy = max(0, cy - page)
        cx = min(cx, len(lines[cy]))
    elif key == KEY_PGDN:
        cy = min(len(lines) - 1, cy + page)
        cx = min(cx, len(lines[cy]))
    return cy, cx


def vi_motion(lines: list[str], cy: int, cx: int, key: str, count: int, page: int) -> tuple[int, int]:
    count = max(1, count)
    if key in ("h", KEY_LEFT):
        for _ in range(count):
            cy, cx = editor_move(lines, cy, cx, KEY_LEFT, page)
    elif key in ("l", KEY_RIGHT):
        for _ in range(count):
            cy, cx = editor_move(lines, cy, cx, KEY_RIGHT, page)
    elif key in ("k", KEY_UP):
        cy = max(0, cy - count)
        cx = min(cx, len(lines[cy]))
    elif key in ("j", KEY_DOWN):
        cy = min(len(lines) - 1, cy + count)
        cx = min(cx, len(lines[cy]))
    elif key == "w":
        for _ in range(count):
            cy, cx = vi_word_next(lines, cy, cx)
    elif key == "b":
        for _ in range(count):
            cy, cx = vi_word_prev(lines, cy, cx)
    elif key == "e":
        for _ in range(count):
            cy, cx = vi_word_end(lines, cy, cx)
    elif key == "\x15":
        cy = max(0, cy - max(1, page // 2) * count)
        cx = min(cx, len(lines[cy]))
    elif key == "\x04":
        cy = min(len(lines) - 1, cy + max(1, page // 2) * count)
        cx = min(cx, len(lines[cy]))
    elif key == KEY_PGUP:
        for _ in range(count):
            cy, cx = editor_move(lines, cy, cx, KEY_PGUP, page)
    elif key == KEY_PGDN:
        for _ in range(count):
            cy, cx = editor_move(lines, cy, cx, KEY_PGDN, page)
    return cy, cx


def vi_word_next(lines: list[str], cy: int, cx: int) -> tuple[int, int]:
    y, x = cy, cx
    while y < len(lines):
        line = lines[y]
        kind = vi_word_kind_at(line, x)
        if kind:
            while x < len(line) and vi_word_kind(line[x]) == kind:
                x += 1
        while x < len(line) and not vi_word_kind(line[x]):
            x += 1
        if x < len(line):
            return y, x
        y += 1
        x = 0
    return cy, cx


def vi_word_prev(lines: list[str], cy: int, cx: int) -> tuple[int, int]:
    y = cy
    x = cx - 1
    while y >= 0:
        line = lines[y]
        if not line or x < 0:
            y -= 1
            x = max(0, len(lines[y]) - 1) if y >= 0 else 0
            continue
        x = min(x, len(line) - 1)
        while x >= 0 and not vi_word_kind(line[x]):
            x -= 1
        if x >= 0:
            kind = vi_word_kind(line[x])
            while x > 0 and vi_word_kind(line[x - 1]) == kind:
                x -= 1
            return y, x
        y -= 1
        x = max(0, len(lines[y]) - 1) if y >= 0 else 0
    return 0, 0


def vi_word_end(lines: list[str], cy: int, cx: int) -> tuple[int, int]:
    y, x = cy, cx
    while y < len(lines):
        line = lines[y]
        if x >= len(line):
            y += 1
            x = 0
            continue
        while x < len(line) and not vi_word_kind(line[x]):
            x += 1
        if x < len(line):
            kind = vi_word_kind(line[x])
            while x + 1 < len(line) and vi_word_kind(line[x + 1]) == kind:
                x += 1
            return y, x
        y += 1
        x = 0
    return cy, cx


def vi_word_kind_at(line: str, index: int) -> str:
    return vi_word_kind(line[index]) if 0 <= index < len(line) else ""


def vi_word_kind(ch: str) -> str:
    if not ch or ch.isspace():
        return ""
    code = ord(ch)
    if code < 128:
        return "ascii_word" if (ch.isalnum() or ch == "_") else "ascii_symbol"
    name = unicodedata.name(ch, "")
    if "HIRAGANA" in name:
        return "hiragana"
    if "KATAKANA" in name:
        return "katakana"
    if is_cjk_kanji(code):
        return "kanji"
    category = unicodedata.category(ch)
    if category.startswith("P"):
        return "punct"
    if category.startswith("S"):
        return "symbol"
    if category.startswith(("L", "N")):
        return "word"
    return "symbol"


def is_cjk_kanji(code: int) -> bool:
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x20000 <= code <= 0x2A6DF
        or 0x2A700 <= code <= 0x2B73F
        or 0x2B740 <= code <= 0x2B81F
        or 0x2B820 <= code <= 0x2CEAF
        or 0x2CEB0 <= code <= 0x2EBEF
        or 0x30000 <= code <= 0x3134F
    )


def vi_motion_linewise(key: str) -> bool:
    return key in ("j", "k", KEY_UP, KEY_DOWN, KEY_PGUP, KEY_PGDN, "\x15", "\x04")


def vi_delete_lines(lines: list[str], cy: int, count: int) -> tuple[list[str], int, int, str]:
    count = max(1, count)
    end = min(len(lines), cy + count)
    text = "\n".join(lines[cy:end]) + "\n"
    del lines[cy:end]
    if not lines:
        lines = [""]
    cy = min(cy, len(lines) - 1)
    return lines, cy, 0, text


def vi_yank_lines(lines: list[str], cy: int, count: int) -> str:
    count = max(1, count)
    end = min(len(lines), cy + count)
    return "\n".join(lines[cy:end]) + "\n"


def vi_paste_after(lines: list[str], cy: int, cx: int, clip: str) -> tuple[list[str], int, int]:
    if clip.endswith("\n"):
        insert = clip.split("\n")[:-1]
        at = min(len(lines), cy + 1)
        lines[at:at] = insert
        return lines, at, 0
    at = min(len(lines[cy]), cx + 1)
    lines, cy, cx = editor_insert_text(lines, cy, at, clip)
    return lines, cy, cx


def vi_join_lines(lines: list[str], cy: int, count: int) -> tuple[list[str], int, int]:
    count = max(1, count)
    joins = min(count, max(0, len(lines) - cy - 1))
    cx = len(lines[cy])
    for _ in range(joins):
        right = lines.pop(cy + 1).lstrip()
        sep = "" if not lines[cy] or not right else " "
        lines[cy] += sep + right
    return lines, cy, cx


def vi_range_end(lines: list[str], start: tuple[int, int], end: tuple[int, int], include_end: bool = False) -> tuple[int, int]:
    ey, ex = end
    if include_end and 0 <= ey < len(lines):
        ex = min(len(lines[ey]), ex + 1)
    return ey, ex


def vi_visual_range(lines: list[str], mark: tuple[int, int], cur: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    if mark <= cur:
        return mark, vi_range_end(lines, mark, cur, True)
    return cur, vi_range_end(lines, cur, mark, True)


def vi_substitute_line(line: str, command: str) -> tuple[str, int]:
    text = command[1:] if command.startswith(":") else command
    if not text.startswith("s") or len(text) < 2:
        raise ValueError("bad substitute")
    sep = text[1]
    parts = text[2:].split(sep)
    if len(parts) < 2:
        raise ValueError("bad substitute")
    old, new = parts[0], parts[1]
    flags = parts[2] if len(parts) > 2 else ""
    if not old:
        raise ValueError("empty pattern")
    if "g" in flags:
        count = line.count(old)
        return line.replace(old, new), count
    if old not in line:
        return line, 0
    return line.replace(old, new, 1), 1


def vi_command_bare(command: str) -> str:
    text = command.strip()
    if text.startswith(":"):
        text = text[1:]
    return text.strip()


BOX_TO_BITS = {
    "─": 0b1010,
    "│": 0b0101,
    "┌": 0b0110,
    "┐": 0b1100,
    "└": 0b0011,
    "┘": 0b1001,
    "├": 0b0111,
    "┤": 0b1101,
    "┬": 0b1110,
    "┴": 0b1011,
    "┼": 0b1111,
}
BITS_TO_BOX = {value: key for key, value in BOX_TO_BITS.items()}
BITS_TO_BOX.update({
    0b0001: "│",
    0b0100: "│",
    0b0010: "─",
    0b1000: "─",
})
BOX_DIRS = {
    KEY_UP: (-1, 0, 0b0001, 0b0100),
    KEY_RIGHT: (0, 1, 0b0010, 0b1000),
    KEY_DOWN: (1, 0, 0b0100, 0b0001),
    KEY_LEFT: (0, -1, 0b1000, 0b0010),
}


def editor_line_draw_mode(term: Terminal, lines: list[str], cy: int, cx: int, insert_mode: bool, colors: dict[str, str] | None) -> tuple[list[str], int, int]:
    drawing = False
    prev_to_bit = 0
    msg = "line draw: move cursor  Enter start  Esc end"
    col = display_width(lines[cy][:cx]) if cy < len(lines) else cx
    while True:
        columns, rows = term.size()
        gutter = max(6, len(str(len(lines))) + 2) if EDITOR_STATE.line_numbers else 0
        body = max(1, rows - 3)
        top = max(0, min(cy, max(0, len(lines) - body)))
        left = 0
        text_w = max(1, columns - gutter)
        lines = editor_ensure_display_pos(lines, cy, col)
        draw_cx = display_col_to_index(lines[cy], col)
        editor_draw(term, Path("[line draw]"), lines, cy, draw_cx, top, left, body, gutter, text_w, None, False, True, msg, insert_mode, True, colors)
        term.move(cy - top + 2, max(gutter + 1, min(columns, gutter + col + 1)))
        term.flush()
        key = read_key()
        if key == KEY_ESCAPE:
            return lines, cy, draw_cx
        if key == KEY_ENTER:
            if drawing:
                return lines, cy, draw_cx
            drawing = True
            prev_to_bit = 0
            msg = "line draw: arrows draw  Space erase  Enter end"
            continue
        if key == " ":
            lines = box_put_char_at_col(lines, cy, col, " ", False)
            msg = "erase"
            continue
        if key not in BOX_DIRS:
            msg = "line draw: arrows draw  Space erase  Enter end" if drawing else "line draw: move cursor  Enter start  Esc end"
            continue
        dy, dx, from_bit, to_bit = BOX_DIRS[key]
        ny = max(0, cy + dy)
        ncol = max(0, col + dx)
        while ny >= len(lines):
            lines.append("")
        if drawing:
            if insert_mode and dy == 0:
                if box_char_at_col(lines, cy, col):
                    lines = box_add_bits_at_col(lines, cy, col, from_bit, False, prev_to_bit)
                    lines = box_add_bits_at_col(lines, ny, ncol, to_bit, True, 0)
                else:
                    lines = box_add_bits_at_col(lines, cy, min(col, ncol), 0b1010, True, 0)
            else:
                lines = box_add_bits_at_col(lines, cy, col, from_bit, False, prev_to_bit)
                lines = box_add_bits_at_col(lines, ny, ncol, to_bit, insert_mode, 0)
            prev_to_bit = to_bit
        cy, col = ny, ncol
        cx = display_col_to_index(lines[cy], col)
        msg = "line draw" if drawing else "line draw: move cursor  Enter start  Esc end"


def display_col_to_index(line: str, col: int, show_bin: bool = False) -> int:
    pos = 0
    for index, ch in enumerate(line):
        width = editor_char_width(ch, show_bin)
        if col <= pos or col < pos + width:
            return index
        pos += width
    return len(line)


def split_wide_char_at_col(line: str, col: int) -> tuple[str, int]:
    pos = 0
    for index, ch in enumerate(line):
        width = char_width(ch)
        if width > 1 and pos < col < pos + width:
            line = line[:index] + (" " * width) + line[index + 1:]
            return line, index + (col - pos)
        if col <= pos:
            return line, index
        pos += width
    return line, len(line)


def editor_ensure_display_pos(lines: list[str], y: int, col: int) -> list[str]:
    while y >= len(lines):
        lines.append("")
    width = display_width(lines[y])
    if col >= width:
        lines[y] += " " * (col - width + 1)
    return lines


def editor_ensure_pos(lines: list[str], y: int, x: int) -> list[str]:
    while y >= len(lines):
        lines.append("")
    if x >= len(lines[y]):
        lines[y] += " " * (x - len(lines[y]) + 1)
    return lines


def box_char_at_col(lines: list[str], y: int, col: int) -> bool:
    if y >= len(lines):
        return False
    lines[y], _ = split_wide_char_at_col(lines[y], col)
    x = display_col_to_index(lines[y], col)
    return x < len(lines[y]) and lines[y][x] in BOX_TO_BITS


def box_add_bits(lines: list[str], y: int, x: int, bits: int, insert_mode: bool = False, existing_bits: int = 0) -> list[str]:
    line = lines[y]
    if x >= len(line):
        line = line + (" " * (x - len(line) + 1))
    old = line[x]
    old_bits = BOX_TO_BITS.get(old, existing_bits if old in ("─", "│") else 0)
    if old in ("─", "│") and existing_bits:
        old_bits = existing_bits
    new_bits = old_bits | bits
    ch = BITS_TO_BOX.get(new_bits, old)
    if insert_mode and old not in BOX_TO_BITS and old != " ":
        lines[y] = line[:x] + ch + line[x:]
    else:
        lines[y] = line[:x] + ch + line[x + 1:]
    return lines


def box_add_bits_at_col(lines: list[str], y: int, col: int, bits: int, insert_mode: bool = False, existing_bits: int = 0) -> list[str]:
    lines = editor_ensure_display_pos(lines, y, col)
    line, x = split_wide_char_at_col(lines[y], col)
    lines[y] = line
    old = line[x] if x < len(line) else " "
    old_bits = BOX_TO_BITS.get(old, existing_bits if old in ("─", "│") else 0)
    if old in ("─", "│") and existing_bits:
        old_bits = existing_bits
    new_bits = old_bits | bits
    ch = BITS_TO_BOX.get(new_bits, old)
    if insert_mode and old not in BOX_TO_BITS and old != " ":
        lines[y] = line[:x] + ch + line[x:]
    else:
        lines[y] = line[:x] + ch + line[x + 1:]
    return lines


def box_put_char_at_col(lines: list[str], y: int, col: int, ch: str, insert_mode: bool = False) -> list[str]:
    lines = editor_ensure_display_pos(lines, y, col)
    line, x = split_wide_char_at_col(lines[y], col)
    lines[y] = line
    if insert_mode:
        lines[y] = line[:x] + ch + line[x:]
    else:
        lines[y] = line[:x] + ch + line[x + 1:]
    return lines


def box_put_char(lines: list[str], y: int, x: int, ch: str, insert_mode: bool = False) -> list[str]:
    line = lines[y]
    if x >= len(line):
        line = line + (" " * (x - len(line) + 1))
    if insert_mode:
        lines[y] = line[:x] + ch + line[x:]
    else:
        lines[y] = line[:x] + ch + line[x + 1:]
    return lines


def editor_put_text(line: str, cx: int, text: str, insert_mode: bool) -> str:
    if cx >= len(line):
        return line + (" " * (cx - len(line))) + text
    if insert_mode:
        return line[:cx] + text + line[cx:]
    return line[:cx] + text + line[min(len(line), cx + len(text)):]


def push_undo(stack: list[tuple[list[str], int, int]], lines: list[str], cy: int, cx: int) -> None:
    stack.append((lines[:], cy, cx))
    if len(stack) > 100:
        del stack[0]


def editor_undo_redo(action: str, lines: list[str], cy: int, cx: int, undo: list[tuple[list[str], int, int]], redo: list[tuple[list[str], int, int]]) -> tuple[list[str], int, int, list[tuple[list[str], int, int]], list[tuple[list[str], int, int]], str]:
    src = undo if action == "undo" else redo
    dst = redo if action == "undo" else undo
    if not src:
        return lines, cy, cx, undo, redo, "no undo" if action == "undo" else "no redo"
    dst.append((lines[:], cy, cx))
    lines, cy, cx = src.pop()
    return lines[:], cy, cx, undo, redo, action


def editor_action_changes(action: str, mark: tuple[int, int] | None, cur: tuple[int, int], clips: list[str]) -> bool:
    if action in ("cut",):
        return True
    if action in ("paste", "clip_list"):
        return bool(clips)
    if action in ("delete_line", "delete_word", "delete_to_eol"):
        return True
    return False


def editor_range(a: tuple[int, int], b: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    return (a, b) if a <= b else (b, a)


def editor_select_all(lines: list[str]) -> tuple[int, int, tuple[int, int], bool, bool, str]:
    last = max(0, len(lines) - 1)
    end = len(lines[last]) if lines else 0
    return last, end, (0, 0), True, False, "selected all"


def editor_indent_lines(lines: list[str], cy: int, cx: int, mark: tuple[int, int] | None, indent: bool) -> tuple[list[str], int, int, tuple[int, int] | None, str]:
    if mark is not None and mark != (cy, cx):
        start, end = editor_range(mark, (cy, cx))
        first, last = start[0], end[0]
        if end[1] == 0 and last > first:
            last -= 1
    else:
        first = last = cy
    width = EDITOR_STATE.tab_spaces
    shifts: dict[int, int] = {}
    if indent:
        prefix = " " * width
        for y in range(first, last + 1):
            lines[y] = prefix + lines[y]
            shifts[y] = width
        msg = f"indent: {last - first + 1}"
    else:
        for y in range(first, last + 1):
            count = min(len(lines[y]) - len(lines[y].lstrip(" ")), width)
            if count:
                lines[y] = lines[y][count:]
            shifts[y] = -count
        msg = f"unindent: {last - first + 1}"
    cx = shift_column(cy, cx, shifts)
    if mark is not None:
        mark = (mark[0], shift_column(mark[0], mark[1], shifts))
    return lines, cy, cx, mark, msg


def shift_column(row: int, col: int, shifts: dict[int, int]) -> int:
    shift = shifts.get(row, 0)
    if shift > 0:
        return col + shift
    if shift < 0:
        return max(0, col + shift)
    return col


def editor_selected_text(lines: list[str], mark: tuple[int, int], cur: tuple[int, int]) -> str:
    start, end = editor_range(mark, cur)
    sy, sx = start
    ey, ex = end
    if sy == ey:
        return lines[sy][sx:ex]
    parts = [lines[sy][sx:]]
    parts.extend(lines[sy + 1:ey])
    parts.append(lines[ey][:ex])
    return "\n".join(parts)


def editor_delete_selection(lines: list[str], mark: tuple[int, int], cur: tuple[int, int]) -> tuple[list[str], int, int, str]:
    text = editor_selected_text(lines, mark, cur)
    start, end = editor_range(mark, cur)
    sy, sx = start
    ey, ex = end
    if sy == ey:
        lines[sy] = lines[sy][:sx] + lines[sy][ex:]
    else:
        lines[sy:ey + 1] = [lines[sy][:sx] + lines[ey][ex:]]
    return lines, sy, sx, text


def editor_rect_text(lines: list[str], mark: tuple[int, int], cur: tuple[int, int]) -> str:
    sy, ey = sorted((mark[0], cur[0]))
    sx, ex = sorted((mark[1], cur[1]))
    return "\n".join((lines[y][sx:ex] if sx < len(lines[y]) else "") for y in range(sy, ey + 1))


def editor_delete_rect(lines: list[str], mark: tuple[int, int], cur: tuple[int, int]) -> tuple[list[str], int, int, str]:
    sy, ey = sorted((mark[0], cur[0]))
    sx, ex = sorted((mark[1], cur[1]))
    text = editor_rect_text(lines, mark, cur)
    for y in range(sy, ey + 1):
        line = lines[y]
        if sx < len(line):
            lines[y] = line[:sx] + line[min(ex, len(line)):]
    return lines, sy, sx, text


def editor_insert_text(lines: list[str], cy: int, cx: int, text: str) -> tuple[list[str], int, int]:
    parts = text.split("\n")
    if len(parts) == 1:
        lines[cy] = lines[cy][:cx] + text + lines[cy][cx:]
        return lines, cy, cx + len(text)
    tail = lines[cy][cx:]
    lines[cy] = lines[cy][:cx] + parts[0]
    insert = parts[1:]
    insert[-1] += tail
    lines[cy + 1:cy + 1] = insert
    return lines, cy + len(parts) - 1, len(parts[-1])


def editor_replace(lines: list[str], old: str, new: str) -> int:
    count = 0
    for index, line in enumerate(lines):
        line_count = line.count(old)
        if line_count:
            lines[index] = line.replace(old, new)
            count += line_count
    return count


def editor_find_history() -> list[str]:
    if EDITOR_STATE.find_history is None:
        EDITOR_STATE.find_history = []
    return EDITOR_STATE.find_history


def editor_replace_history() -> list[str]:
    if EDITOR_STATE.replace_history is None:
        EDITOR_STATE.replace_history = []
    return EDITOR_STATE.replace_history


def add_editor_history(history: list[str], text: str) -> None:
    if not text:
        return
    if text in history:
        history.remove(text)
    history.append(text)
    del history[:-50]
    save_stat()


def editor_input_popup(term: Terminal, label: str, default: str, history: list[str], redraw: Callable[[], None]) -> str | None:
    text = list(default)
    cursor = len(text)
    offset = 0
    hist = len(history)
    while True:
        redraw()
        columns, rows = term.size()
        width = min(max(40, (columns * 2) // 3), max(20, columns - 4))
        field_width = max(1, width - 2)
        while display_width("".join(text[offset:cursor])) > max(0, field_width - 1):
            offset += 1
        while cursor < offset:
            offset -= 1
        visible = ""
        for ch in text[offset:]:
            if display_width(visible + ch) > field_width:
                break
            visible += ch
        row = max(2, (rows - 4) // 2 + 1)
        col = max(1, (columns - width) // 2 + 1)
        title = f" {label} "
        title_row = yellow("█") + fit(title, width - 2) + yellow("█")
        body = yellow("█") + fit(visible, field_width) + yellow("█")
        hint = "Enter:OK  ESC:Cancel"
        term.move(row, col)
        term.write(yellow("█" * width))
        term.move(row + 1, col)
        term.write(title_row)
        term.move(row + 2, col)
        term.write(body)
        term.move(row + 3, col)
        term.write(yellow_bg(fit(hint, width)))
        cursor_col = col + 1 + min(field_width - 1, display_width("".join(text[offset:cursor])))
        term.move(row + 2, cursor_col)
        term.flush()

        key = read_key()
        if key == KEY_ENTER:
            value = "".join(text)
            add_editor_history(history, value)
            return value
        if key == KEY_ESCAPE:
            return None
        if key in (KEY_UP, KEY_DOWN) and history:
            hist += -1 if key == KEY_UP else 1
            hist = min(len(history), max(0, hist))
            value = default if hist == len(history) else history[hist]
            text = list(value)
            cursor = len(text)
            offset = 0
        elif key == KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == KEY_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif key == KEY_HOME:
            cursor = 0
            offset = 0
        elif key == KEY_END:
            cursor = len(text)
        elif key == KEY_BACKSPACE:
            if cursor > 0:
                del text[cursor - 1]
                cursor -= 1
        elif key == KEY_DELETE:
            if cursor < len(text):
                del text[cursor]
        elif key and is_text_input(key):
            text[cursor:cursor] = list(key)
            cursor += len(key)


def editor_vi_line_input(term: Terminal, prefix: str, default: str, history: list[str], redraw: Callable[[], None]) -> str | None:
    text = list(default)
    cursor = len(text)
    offset = 0
    hist = len(history)
    while True:
        redraw()
        columns, rows = term.size()
        field_width = max(1, columns - display_width(prefix))
        while display_width("".join(text[offset:cursor])) > max(0, field_width - 1):
            offset += 1
        while cursor < offset:
            offset -= 1
        visible = ""
        for ch in text[offset:]:
            if display_width(visible + ch) > field_width:
                break
            visible += ch
        term.move(rows, 1)
        term.write(fit(prefix + visible, columns))
        cursor_col = 1 + display_width(prefix + "".join(text[offset:cursor]))
        term.move(rows, max(1, min(columns, cursor_col)))
        term.flush()

        key = read_key()
        if key == KEY_ENTER:
            value = "".join(text)
            add_editor_history(history, value)
            return value
        if key == KEY_ESCAPE:
            return None
        if key in (KEY_UP, KEY_DOWN) and history:
            hist += -1 if key == KEY_UP else 1
            hist = min(len(history), max(0, hist))
            value = default if hist == len(history) else history[hist]
            text = list(value)
            cursor = len(text)
            offset = 0
        elif key == KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == KEY_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif key == KEY_HOME:
            cursor = 0
            offset = 0
        elif key == KEY_END:
            cursor = len(text)
        elif key == KEY_BACKSPACE:
            if cursor > 0:
                del text[cursor - 1]
                cursor -= 1
        elif key == KEY_DELETE:
            if cursor < len(text):
                del text[cursor]
        elif key and is_text_input(key):
            text[cursor:cursor] = list(key)
            cursor += len(key)


def editor_calc_popup(term: Terminal, lines: list[str], cy: int, cx: int, colors: dict[str, str] | None) -> str | None:
    history = EDITOR_STATE.calc_history
    if history is None:
        history = []
        EDITOR_STATE.calc_history = history
    expr: list[str] = []
    cursor = 0
    offset = 0
    hist = len(history)
    armed = False
    while True:
        columns, rows = term.size()
        text = "".join(expr)
        result = calc_text(text)
        width = min(max(36, columns // 2), max(36, columns - 2))
        result_width = min(18, max(10, width // 3))
        input_width = width - result_width - 2
        while display_width("".join(expr[offset:cursor])) > input_width:
            offset += 1
        while cursor < offset:
            offset -= 1
        visible = calc_visible_text("".join(expr[offset:]), input_width)
        row = cy + 4
        if row + 2 > rows:
            row = max(2, cy - 2)
        row = min(max(2, row), max(2, rows - 2))
        col = min(max(1, cx + 1), max(1, columns - width + 1))
        term.move(row, col)
        term.write(yellow("█" * width))
        term.move(row + 1, col)
        term.write(yellow("█") + fit(visible, input_width) + calc_result_cell(result, result_width) + yellow("█"))
        term.move(row + 2, col)
        term.write(yellow("█" * width))
        term.move(row + 1, col + 1 + min(input_width - 1, display_width("".join(expr[offset:cursor]))))
        term.flush()
        key = read_key()
        if key == KEY_ESCAPE:
            return None
        if key == KEY_ENTER:
            if armed and result:
                if text and text not in history:
                    history.append(text)
                    del history[:-50]
                return result
            armed = True
            continue
        armed = False
        if key == KEY_HOME:
            expr.clear()
            cursor = 0
            offset = 0
            hist = len(history)
        elif key == KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == KEY_RIGHT:
            cursor = min(len(expr), cursor + 1)
        elif key == KEY_BACKSPACE:
            if cursor > 0:
                del expr[cursor - 1]
                cursor -= 1
        elif key == KEY_DELETE:
            if cursor < len(expr):
                del expr[cursor]
        elif key == KEY_UP:
            if history:
                hist = max(0, hist - 1)
                expr = list(history[hist])
                cursor = len(expr)
                offset = max(0, cursor - input_width)
        elif key == KEY_DOWN:
            if history:
                hist = min(len(history), hist + 1)
                expr = [] if hist == len(history) else list(history[hist])
                cursor = len(expr)
                offset = max(0, cursor - input_width)
        elif key and is_text_input(key):
            expr[cursor:cursor] = list(key)
            cursor += len(key)


def calc_text(text: str) -> str:
    expr, fmt = split_calc_format(text)
    if not expr.strip():
        return ""
    try:
        value = eval_calc_expr(expr)
        return format_calc_value(value, fmt)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError, TypeError):
        return "ERR"


def calc_visible_text(text: str, width: int) -> str:
    if display_width(text) <= width:
        return text
    if width <= 3:
        return fit_raw(text, width)
    body = fit_raw(text, width - 3)
    return body + "..."


def calc_result_cell(result: str, width: int) -> str:
    text = fit_raw(result, width)
    pad = max(0, width - display_width(text))
    return color_text((" " * pad) + text, "30;43")


def split_calc_format(text: str) -> tuple[str, str]:
    if "=" not in text:
        return text, ""
    expr, fmt = text.rsplit("=", 1)
    fmt = fmt.strip()
    return expr, fmt if fmt.startswith("%") else ""


def eval_calc_expr(expr: str) -> float | int:
    expr = normalize_calc_expr(expr)
    tree = ast.parse(expr, mode="eval")
    return eval_calc_node(tree.body)


def normalize_calc_expr(expr: str) -> str:
    return re.sub(r"\b0([0-9]+)\b", lambda match: "0o" + match.group(1), expr)


def eval_calc_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp):
        value = eval_calc_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.USub):
            return -value
    if isinstance(node, ast.BinOp):
        left = eval_calc_node(node.left)
        right = eval_calc_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left ** right
    raise ValueError("bad expression")


def format_calc_value(value: float | int, fmt: str) -> str:
    if fmt:
        if fmt.endswith(("x", "X", "o", "d")):
            return fmt % int(value)
        return fmt % value
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.12g}"
    return str(int(value))


def editor_word_left(line: str, cx: int) -> int:
    pos = cx
    while pos > 0 and line[pos - 1].isspace():
        pos -= 1
    while pos > 0 and not line[pos - 1].isspace():
        pos -= 1
    return pos


def editor_find(lines: list[str], text: str, cy: int, cx: int) -> tuple[int, int] | None:
    if not text:
        return None
    for y in range(cy, len(lines)):
        start = cx + 1 if y == cy else 0
        x = lines[y].find(text, start)
        if x >= 0:
            return y, x
    for y in range(0, cy + 1):
        x = lines[y].find(text, 0)
        if x >= 0:
            return y, x
    return None


def editor_action(term: Terminal, action: str, lines: list[str], cy: int, cx: int, mark: tuple[int, int] | None, dirty: bool, find_text: str, edit_mode: bool, rect_select: bool = False, redraw: Callable[[], None] | None = None) -> tuple[list[str], int, int, tuple[int, int] | None, bool, str, str]:
    msg = ""
    cur = (cy, cx)
    if action == "copy":
        if mark is not None and mark != cur:
            editor_push_clip(editor_rect_text(lines, mark, cur) if rect_select else editor_selected_text(lines, mark, cur))
            mark = None
            msg = "copied"
        else:
            editor_push_clip(lines[cy] + "\n")
            msg = "line copied"
    elif action == "cut":
        if not edit_mode:
            return lines, cy, cx, mark, dirty, find_text, read_only_bell(term)
        if mark is not None and mark != cur:
            lines, cy, cx, text = editor_delete_rect(lines, mark, cur) if rect_select else editor_delete_selection(lines, mark, cur)
            editor_push_clip(text)
            mark = None
            dirty = True
            msg = "cut"
        else:
            editor_push_clip(lines[cy] + "\n")
            del lines[cy]
            if not lines:
                lines = [""]
            cy = min(cy, len(lines) - 1)
            cx = min(cx, len(lines[cy]))
            dirty = True
            msg = "line cut"
    elif action == "paste":
        if not edit_mode:
            return lines, cy, cx, mark, dirty, find_text, read_only_bell(term)
        clip = EDITOR_STATE.clips[-1] if EDITOR_STATE.clips else ""
        if clip:
            if mark is not None and mark != cur:
                lines, cy, cx, _ = editor_delete_selection(lines, mark, cur)
                mark = None
            lines, cy, cx = editor_insert_text(lines, cy, cx, clip)
            dirty = True
            msg = "pasted"
        else:
            msg = "clipboard empty"
    elif action == "clip_list":
        clip = editor_clip_list(term)
        if clip:
            if not edit_mode:
                return lines, cy, cx, mark, dirty, find_text, read_only_bell(term)
            if mark is not None and mark != cur:
                lines, cy, cx, _ = editor_delete_selection(lines, mark, cur)
                mark = None
            lines, cy, cx = editor_insert_text(lines, cy, cx, clip)
            dirty = True
            msg = "pasted"
        else:
            msg = "clipboard empty"
    elif action == "delete_line":
        if not edit_mode:
            return lines, cy, cx, mark, dirty, find_text, read_only_bell(term)
        editor_push_clip(lines[cy])
        del lines[cy]
        if not lines:
            lines = [""]
        cy = min(cy, len(lines) - 1)
        cx = min(cx, len(lines[cy]))
        mark = None
        dirty = True
        msg = "line deleted"
    elif action == "delete_word":
        if not edit_mode:
            return lines, cy, cx, mark, dirty, find_text, read_only_bell(term)
        if cx > 0:
            start = editor_word_left(lines[cy], cx)
            lines[cy] = lines[cy][:start] + lines[cy][cx:]
            cx = start
            dirty = True
            msg = "word deleted"
        elif cy > 0:
            cx = len(lines[cy - 1])
            lines[cy - 1] += lines[cy]
            del lines[cy]
            cy -= 1
            dirty = True
            msg = "word deleted"
        else:
            msg = "top"
    elif action == "delete_to_eol":
        if not edit_mode:
            return lines, cy, cx, mark, dirty, find_text, read_only_bell(term)
        if cx < len(lines[cy]):
            lines[cy] = lines[cy][:cx]
            dirty = True
            msg = "deleted to eol"
        elif cy + 1 < len(lines):
            lines[cy] += lines[cy + 1]
            del lines[cy + 1]
            dirty = True
            msg = "joined"
        else:
            msg = "eol"
    elif action == "find":
        text = editor_input_popup(term, "Find", find_text, editor_find_history(), redraw) if redraw is not None else edit_line(term, "find", find_text)
        if text is not None and text:
            find_text = text
            pos = editor_find(lines, find_text, cy, cx - 1)
            if pos is not None:
                cy, cx = pos
                mark = (cy, cx + len(find_text))
                msg = "found"
            else:
                msg = "not found"
    elif action == "find_next":
        pos = editor_find(lines, find_text, cy, cx)
        if pos is not None:
            cy, cx = pos
            mark = (cy, cx + len(find_text))
            msg = "found"
        else:
            msg = "not found"
    elif action == "tab_space":
        text = popup_edit_line(term, "tab space", str(EDITOR_STATE.tab_spaces), redraw)
        if text.isdigit() and 1 <= int(text) <= 16:
            EDITOR_STATE.tab_spaces = int(text)
            save_stat()
            msg = f"tab:{EDITOR_STATE.tab_spaces}"
        else:
            msg = "tab canceled"
    elif action == "wrap_mode":
        EDITOR_STATE.wrap = not EDITOR_STATE.wrap
        save_stat()
        msg = "wrap" if EDITOR_STATE.wrap else "horizontal scroll"
    elif action == "line_number":
        EDITOR_STATE.line_numbers = not EDITOR_STATE.line_numbers
        save_stat()
        msg = "line number on" if EDITOR_STATE.line_numbers else "line number off"
    return lines, cy, cx, mark, dirty, find_text, msg


def editor_push_clip(text: str) -> None:
    if text:
        EDITOR_STATE.clips.append(text)
        copy_to_os_clipboard(text)


def copy_to_os_clipboard(text: str) -> bool:
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
                input=text,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return True
        if sys.platform == "darwin":
            process = subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return process.returncode == 0
    except OSError:
        return False
    return False


def editor_clip_list(term: Terminal) -> str:
    if not EDITOR_STATE.clips:
        return ""
    cursor = len(EDITOR_STATE.clips) - 1
    top = 0
    while True:
        columns, rows = term.size()
        width = min(max(32, columns - 8), columns)
        height = min(len(EDITOR_STATE.clips), max(1, rows - 6))
        if cursor < top:
            top = cursor
        elif cursor >= top + height:
            top = cursor - height + 1
        start_row = max(2, (rows - height - 3) // 2 + 1)
        start_col = max(1, (columns - width) // 2 + 1)
        for y in range(height + 2):
            term.move(start_row + y, start_col)
            if y == 0 or y == height + 1:
                term.write(yellow("█" * width))
            else:
                term.write(yellow("█") + " " * (width - 2) + yellow("█"))
        for row in range(height):
            index = top + row
            sample = EDITOR_STATE.clips[index].replace("\n", "\\n")
            line = fit(("> " if index == cursor else "  ") + sample, width - 2)
            term.move(start_row + 1 + row, start_col + 1)
            term.write(reverse(line) if index == cursor else line)
        term.flush()
        key = read_key()
        if key == KEY_ENTER:
            return EDITOR_STATE.clips[cursor]
        if key in (KEY_ESCAPE, KEY_BACKSPACE, "q", "Q"):
            return ""
        if key in ("c", "C"):
            EDITOR_STATE.clips.clear()
            return ""
        if key == KEY_DELETE:
            del EDITOR_STATE.clips[cursor]
            if not EDITOR_STATE.clips:
                return ""
            cursor = min(cursor, len(EDITOR_STATE.clips) - 1)
        elif key in (KEY_UP, "k", "K"):
            cursor = max(0, cursor - 1)
        elif key in (KEY_DOWN, "j", "J"):
            cursor = min(len(EDITOR_STATE.clips) - 1, cursor + 1)


def editor_row(text: str, y: int, mark: tuple[int, int] | None, cur: tuple[int, int], left: int, width: int, rect_select: bool = False, syntax: dict[str, object] | None = None, eol: str = "LF", colors: dict[str, str] | None = None, show_bin: bool = False) -> str:
    spans = [] if len(text) > EDITOR_SYNTAX_MAX_LINE_CHARS else syntax_spans(text, syntax)
    if mark is None or mark == cur:
        return editor_slice_display(text, left, width, spans, eol, colors, show_bin)
    if rect_select:
        sy, ey = sorted((mark[0], cur[0]))
        sx, ex = sorted((mark[1], cur[1]))
    else:
        start, end = editor_range(mark, cur)
        sy, sx = start
        ey, ex = end
    out = ""
    used = pos = 0
    for x, ch in enumerate(text):
        cw = editor_char_width(ch, show_bin)
        next_pos = pos + cw
        if next_pos <= left:
            pos = next_pos
            continue
        if used + cw > width:
            break
        if rect_select:
            selected = sy <= y <= ey and sx <= x < ex
        else:
            selected = (sy < y < ey) or (y == sy and x >= sx and (y < ey or x < ex)) or (y == ey and sy < y and x < ex)
        cell = editor_char_display(ch, x, spans, colors, show_bin)
        if selected:
            out += reverse_ansi(cell)
        else:
            out += cell
        used += cw
        pos = next_pos
    return out


def editor_slice_display(text: str, start: int, width: int, spans: list[tuple[int, int, str]], eol: str, colors: dict[str, str] | None, show_bin: bool = False) -> str:
    out = ""
    used = 0
    pos = 0
    for index, ch in enumerate(text):
        cw = editor_char_width(ch, show_bin)
        next_pos = pos + cw
        if next_pos <= start:
            pos = next_pos
            continue
        if pos < start:
            pos = next_pos
            continue
        if used + cw > width:
            return out
        out += editor_char_display(ch, index, spans, colors, show_bin)
        used += cw
        pos = next_pos
    if EDITOR_STATE.show_enter and eol != "NONE":
        cw = 1
        next_pos = pos + cw
        if next_pos > start and pos >= start and used + cw <= width:
            out += color_text("↓", editor_enter_color(eol, colors))
    return out


def editor_char_display(ch: str, index: int, spans: list[tuple[int, int, str]], colors: dict[str, str] | None, show_bin: bool = False) -> str:
    if ch == "\t":
        spaces = max(1, EDITOR_STATE.tab_spaces)
        if EDITOR_STATE.show_tab:
            return color_text("→", editor_config_color(colors, "editor_tab_color", "cyan")) + (" " * (spaces - 1))
        return " " * spaces
    if (show_bin or EDITOR_STATE.show_bin) and is_editor_control_char(ch):
        return reverse_color_text(f"0x{ord(ch):02X}", editor_config_color(colors, "editor_bin_color", "7"))
    if is_editor_control_char(ch):
        return ""
    return color_text(ch, color_at(spans, index))


def editor_char_width(ch: str, show_bin: bool = False) -> int:
    if ch == "\t":
        return max(1, EDITOR_STATE.tab_spaces)
    if (show_bin or EDITOR_STATE.show_bin) and is_editor_control_char(ch):
        return len(f"0x{ord(ch):02X}")
    return char_width(ch)


def editor_text_width(text: str, show_bin: bool = False) -> int:
    return sum(editor_char_width(ch, show_bin) for ch in text)


def is_editor_control_char(ch: str) -> bool:
    return bool(ch) and unicodedata.category(ch)[0] == "C" and ch not in ("\t", "\n", "\r")


def editor_enter_color(eol: str, colors: dict[str, str] | None) -> str:
    if eol == "CRLF":
        return editor_config_color(colors, "editor_crlf_color", "cyan")
    if eol == "CR":
        return editor_config_color(colors, "editor_cr_color", "red")
    return editor_config_color(colors, "editor_lf_color", "yellow")


def editor_config_color(colors: dict[str, str] | None, key: str, fallback: str) -> str:
    if not colors:
        return fallback
    return colors.get(key, fallback)


def syntax_for_path(path: Path) -> dict[str, object] | None:
    syntax = EDITOR_STATE.syntax or default_syntax()
    return syntax.get(path.suffix.lower().lstrip("."))


def syntax_spans(text: str, rule: dict[str, object] | None) -> list[tuple[int, int, str]]:
    if not rule:
        return []
    spans: list[tuple[int, int, str]] = []
    protected_spans: list[tuple[int, int, str]] = []
    regex_rules = rule.get("regex")
    comment_color = str(rule.get("comment_color", ""))
    string_color = str(rule.get("string_color", ""))
    number_color = str(rule.get("number_color", ""))
    keyword_color = str(rule.get("keyword_color", ""))
    if isinstance(regex_rules, list):
        for item in regex_rules:
            if not isinstance(item, dict):
                continue
            pattern = item.get("pattern")
            color = item.get("color")
            if not isinstance(pattern, str) or not isinstance(color, str):
                continue
            try:
                for match in re.finditer(pattern, text):
                    span = (match.start(), match.end(), color)
                    spans.append(span)
                    protected_spans.append(span)
            except re.error:
                continue
    if comment_color and text.lstrip().startswith("#"):
        start = len(text) - len(text.lstrip())
        append_syntax_span(spans, protected_spans, start, len(text), comment_color)
    elif comment_color and "#" in text:
        start = text.find("#")
        append_syntax_span(spans, protected_spans, start, len(text), comment_color)
    if string_color:
        for match in re.finditer(r"(['\"])(?:\\.|(?!\1).)*\1", text):
            append_syntax_span(spans, protected_spans, match.start(), match.end(), string_color)
    if number_color:
        for match in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
            append_syntax_span(spans, protected_spans, match.start(), match.end(), number_color)
    keywords = rule.get("keywords")
    if keyword_color and isinstance(keywords, list):
        words = [re.escape(item) for item in keywords if isinstance(item, str) and item]
        if words:
            pattern = r"\b(?:" + "|".join(words) + r")\b"
            for match in re.finditer(pattern, text):
                append_syntax_span(spans, protected_spans, match.start(), match.end(), keyword_color)
    return spans


def append_syntax_span(spans: list[tuple[int, int, str]], protected_spans: list[tuple[int, int, str]], start: int, end: int, color: str) -> None:
    if not color or start >= end:
        return
    for protected_start, protected_end, _ in protected_spans:
        if start < protected_end and protected_start < end:
            return
    spans.append((start, end, color))


def color_at(spans: list[tuple[int, int, str]], index: int) -> str:
    for start, end, color in spans:
        if start <= index < end:
            return color
    return ""


def ansi_width(text: str) -> int:
    width = 0
    index = 0
    while index < len(text):
        if text.startswith("\x1b[", index):
            end = ansi_sequence_end(text, index)
            if end >= 0:
                index = end + 1
                continue
        width += char_width(text[index])
        index += 1
    return width


def strip_ansi_rows(rows: list[str]) -> list[str]:
    return [re.sub("\x1b\\[[0-9;]*[A-Za-z]", "", row).rstrip() for row in rows]


def ansi_sequence_end(text: str, start: int) -> int:
    if not text.startswith("\x1b[", start):
        return -1
    index = start + 2
    while index < len(text):
        if text[index].isalpha():
            return index
        index += 1
    return -1


def pad_ansi(text: str, width: int) -> str:
    return text + (" " * max(0, width - ansi_width(text)))


def fit_ansi(text: str, width: int) -> str:
    if width <= 0:
        return ""
    part, _ = take_ansi_width(text, width)
    return pad_ansi(part, width)


def wrap_ansi_text(text: str, width: int) -> list[str]:
    rows: list[str] = []
    rest = text
    while ansi_width(rest) > width:
        part, rest = take_ansi_width(rest, width)
        rows.append(pad_ansi(part, width))
        if not part and rest == text:
            break
    rows.append(rest)
    return rows


def take_ansi_width(text: str, width: int) -> tuple[str, str]:
    out = ""
    used = 0
    index = 0
    while index < len(text):
        if text.startswith("\x1b[", index):
            end = ansi_sequence_end(text, index)
            if end >= 0:
                out += text[index:end + 1]
                index = end + 1
                continue
        ch_width = char_width(text[index])
        if used + ch_width > width:
            break
        out += text[index]
        used += ch_width
        index += 1
    while index < len(text) and text.startswith("\x1b[", index):
        end = ansi_sequence_end(text, index)
        if end < 0:
            break
        out += text[index:end + 1]
        index = end + 1
    return out, text[index:]


def slice_display(text: str, start: int, width: int, spans: list[tuple[int, int, str]] | None = None) -> str:
    out = ""
    used = 0
    pos = 0
    spans = spans or []
    for index, ch in enumerate(text):
        cw = char_width(ch)
        next_pos = pos + cw
        if next_pos <= start:
            pos = next_pos
            continue
        if used + cw > width:
            break
        out += color_text(ch, color_at(spans, index))
        used += cw
        pos = next_pos
    return out


def fit_preview_text(path: Path, line_index: int, width: int, line_numbers: bool = False) -> str:
    if line_index < 0:
        return " " * width
    try:
        with path.open("rb") as handle:
            data = handle.read(16384)
    except OSError:
        return " " * width
    if b"\x00" in data:
        return fit("[binary]", width)
    text = data.decode("utf-8", errors="replace").splitlines()
    if line_index >= len(text):
        return " " * width
    return fit(preview_text_line(text[line_index], line_index, line_numbers), width)


def fit_zip_preview_text(zip_path: Path, zip_name: str, line_index: int, width: int, line_numbers: bool = False) -> str:
    if line_index < 0:
        return " " * width
    try:
        data = archive_read_bytes(zip_path, zip_name)[:16384]
    except ARCHIVE_READ_ERRORS:
        return " " * width
    if b"\x00" in data:
        return fit("[binary]", width)
    text = data.decode("utf-8", errors="replace").splitlines()
    if line_index >= len(text):
        return " " * width
    return fit(preview_text_line(text[line_index], line_index, line_numbers), width)


def preview_text_line(text: str, line_index: int, line_numbers: bool, syntax: dict[str, object] | None = None) -> str:
    body = display_safe_text(text)
    if syntax:
        body = syntax_color_line(body, syntax)
    if not line_numbers:
        return body
    return f"{line_index + 1:>5}: {body}"


def display_safe_text(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch == "\t":
            out.append("    ")
        elif ch == "\x1b":
            out.append("\\x1b")
        elif unicodedata.category(ch)[0] == "C":
            out.append(f"\\x{ord(ch):02x}")
        else:
            out.append(ch)
    return "".join(out)


def syntax_color_line(text: str, syntax: dict[str, object] | None) -> str:
    spans = syntax_spans(text, syntax)
    if not spans:
        return text
    out = ""
    for index, ch in enumerate(text):
        out += color_text(ch, color_at(spans, index))
    return out


def copy_zip_entry(entry: Entry, dst: Path, multi: bool) -> None:
    if entry.zip_path is None or entry.zip_name is None:
        return
    target_base = dst / entry.name if multi or dst.is_dir() else dst
    if is_tar_archive_path(entry.zip_path):
        for name, data in archive_entry_file_data(entry):
            if entry.is_dir:
                rel = Path(name[len(normalize_zip_dir(entry.zip_name)):])
                target = target_base / rel
            else:
                target = target_base
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return
    with zipfile.ZipFile(entry.zip_path) as archive:
        if entry.is_dir:
            prefix = normalize_zip_dir(entry.zip_name)
            for info in archive.infolist():
                if not info.filename.startswith(prefix) or info.is_dir():
                    continue
                rel = Path(info.filename[len(prefix):])
                target = target_base / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("wb") as out:
                    shutil.copyfileobj(src, out)
        else:
            target_base.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry.zip_name) as src, target_base.open("wb") as out:
                shutil.copyfileobj(src, out)


def create_empty_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w"):
        pass


def add_entries_to_zip(zip_path: Path, entries: list[Entry], zip_dir: str) -> None:
    prefix = normalize_zip_dir(zip_dir)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            if entry.zip_path is not None:
                add_zip_entry_from_zip(archive, entry, prefix)
            elif entry.is_dir:
                add_dir_to_zip(archive, entry.path, prefix + entry.name + "/")
            else:
                archive.write(entry.path, prefix + entry.name)


def add_dir_to_zip(archive: zipfile.ZipFile, path: Path, arc_prefix: str) -> None:
    archive.writestr(arc_prefix, b"")
    for child in path.rglob("*"):
        rel = child.relative_to(path).as_posix()
        arc_name = arc_prefix + rel + ("/" if child.is_dir() else "")
        if child.is_dir():
            archive.writestr(arc_name, b"")
        else:
            archive.write(child, arc_name)


def add_zip_entry_from_zip(dst_archive: zipfile.ZipFile, entry: Entry, prefix: str) -> None:
    if entry.zip_path is None or entry.zip_name is None:
        return
    with zipfile.ZipFile(entry.zip_path) as src_archive:
        if entry.is_dir:
            src_prefix = normalize_zip_dir(entry.zip_name)
            for info in src_archive.infolist():
                if not info.filename.startswith(src_prefix):
                    continue
                name = prefix + entry.name + "/" + info.filename[len(src_prefix):]
                if info.is_dir():
                    dst_archive.writestr(name, b"")
                else:
                    dst_archive.writestr(name, src_archive.read(info.filename))
        else:
            dst_archive.writestr(prefix + entry.name, src_archive.read(entry.zip_name))


def delete_zip_entries(entries: list[Entry]) -> None:
    by_zip: dict[Path, list[Entry]] = {}
    for entry in entries:
        if entry.zip_path is not None:
            if is_tar_archive_path(entry.zip_path):
                raise OSError("tar内のdeleteは未対応です")
            by_zip.setdefault(entry.zip_path, []).append(entry)
    if len(by_zip) != 1 or len(by_zip[next(iter(by_zip))]) != len(entries):
        raise OSError("zip内と通常ファイルの混在deleteは未対応です")
    zip_path, targets = next(iter(by_zip.items()))
    names = {entry.zip_name or "" for entry in targets}
    prefixes = {normalize_zip_dir(name) for name in names if name.endswith("/")}
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmp")
    with zipfile.ZipFile(zip_path) as src, zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename in names or any(info.filename.startswith(prefix) for prefix in prefixes):
                continue
            dst.writestr(info, src.read(info.filename))
    tmp.replace(zip_path)


def rename_zip_entry(entry: Entry, new_name: str) -> None:
    if entry.zip_path is None or entry.zip_name is None:
        return
    if is_tar_archive_path(entry.zip_path):
        raise OSError("tar内のrenameは未対応です")
    old_name = entry.zip_name
    parent = parent_zip_dir(old_name)
    new_zip_name = parent + new_name + ("/" if entry.is_dir else "")
    old_prefix = normalize_zip_dir(old_name) if entry.is_dir else old_name
    new_prefix = normalize_zip_dir(new_zip_name) if entry.is_dir else new_zip_name
    if old_name == new_zip_name:
        return
    tmp = entry.zip_path.with_suffix(entry.zip_path.suffix + ".tmp")
    changed = False
    with zipfile.ZipFile(entry.zip_path) as src:
        names = {info.filename for info in src.infolist()}
        if new_zip_name in names or any(name.startswith(new_prefix) for name in names):
            raise OSError(f"exists: {new_name}")
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                target_name = info.filename
                if entry.is_dir:
                    if target_name.startswith(old_prefix):
                        target_name = new_prefix + target_name[len(old_prefix):]
                        changed = True
                elif target_name == old_name:
                    target_name = new_zip_name
                    changed = True
                data = src.read(info.filename) if not info.is_dir() else b""
                new_info = zipfile.ZipInfo(target_name, info.date_time)
                new_info.comment = info.comment
                new_info.extra = info.extra
                new_info.internal_attr = info.internal_attr
                new_info.external_attr = info.external_attr
                new_info.compress_type = info.compress_type
                dst.writestr(new_info, data)
    if not changed:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise OSError(f"not found: {entry.name}")
    tmp.replace(entry.zip_path)


def extract_zip(zip_path: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    if is_tar_archive_path(zip_path):
        with tarfile.open(zip_path, "r:*") as archive:
            for info in archive.getmembers():
                target = safe_zip_target(dst, info.name)
                if target is None:
                    continue
                if info.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not info.isfile():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(info)
                if stream is None:
                    continue
                with stream, target.open("wb") as out:
                    shutil.copyfileobj(stream, out)
        return
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            target = safe_zip_target(dst, info.filename)
            if target is None:
                continue
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)


def safe_zip_target(dst: Path, name: str) -> Path | None:
    return safe_relative_target(dst, name)


def safe_relative_target(dst: Path, name: str) -> Path | None:
    target = (dst / name).resolve()
    root = dst.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def entry_key(entry: Entry) -> str:
    if entry.search_text and entry.search_line is None:
        return f"history:{entry.path}:{entry.search_text}"
    if entry.zip_path is not None:
        return f"zip:{entry.zip_path}!{entry.zip_name}"
    return str(entry.path)


def entry_display_path(entry: Entry) -> str:
    if entry.zip_path is not None:
        return f"{entry.zip_path}/{entry.zip_name or ''}"
    return str(entry.path)


def entry_information_rows(entries: list[Entry], sort_key: str = "name", reverse: bool = False) -> list[str]:
    infos = sorted((entry_information(entry) for entry in entries), key=entry_information_sort_value(sort_key), reverse=reverse)
    rows = ["Kind Size       Created             Modified            Name             Full Path"]
    rows.append("---- ---------- ------------------- ------------------- ---------------- ----------------")
    for info in infos:
        rows.append(f"{info.kind:<4} {fmt_size(info.size, False):>10} {long_datetime(info.created)} {long_datetime(info.modified)} {info.name:<16} {info.path}")
    return rows


def entry_information(entry: Entry) -> EntryInfo:
    created, modified, size = entry_stat_info(entry)
    kind = "DIR" if entry.is_dir else "FILE"
    return EntryInfo(kind, size, created, modified, entry.name, entry_display_path(entry))


def entry_information_sort_value(sort_key: str) -> Callable[[EntryInfo], object]:
    if sort_key == "size":
        return lambda info: (info.size, info.name.lower())
    if sort_key == "created":
        return lambda info: (info.created, info.name.lower())
    if sort_key == "modified":
        return lambda info: (info.modified, info.name.lower())
    return lambda info: info.name.lower()


def information_sort_title(sort_key: str, reverse: bool) -> str:
    names = {"size": "File size", "created": "Created", "modified": "Modified", "name": "Filename"}
    return f"{names.get(sort_key, sort_key)} {'DESC' if reverse else 'ASC'}"


def entry_stat_info(entry: Entry) -> tuple[float, float, int]:
    if entry.zip_path is not None:
        return zip_entry_stat_info(entry)
    try:
        stat_result = entry.path.stat()
        created = getattr(stat_result, "st_birthtime", stat_result.st_ctime)
        size = directory_total_size(entry.path) if entry.is_dir else stat_result.st_size
        return created, stat_result.st_mtime, size
    except OSError:
        return 0.0, entry.mtime, entry.size


def zip_entry_stat_info(entry: Entry) -> tuple[float, float, int]:
    if entry.zip_path is None or entry.zip_name is None:
        return 0.0, entry.mtime, entry.size
    if is_tar_archive_path(entry.zip_path):
        return tar_entry_stat_info(entry)
    try:
        with zipfile.ZipFile(entry.zip_path) as archive:
            if entry.is_dir:
                prefix = normalize_zip_dir(entry.zip_name)
                infos = [info for info in archive.infolist() if info.filename.startswith(prefix)]
                size = sum(info.file_size for info in infos if not info.is_dir())
                stamps = [zip_info_mtime(info) for info in infos]
                stamp = min(stamps) if stamps else entry.mtime
                return stamp, entry.mtime, size
            info = archive.getinfo(entry.zip_name)
            stamp = zip_info_mtime(info)
            return stamp, stamp, info.file_size
    except (OSError, KeyError, zipfile.BadZipFile):
        return 0.0, entry.mtime, entry.size


def tar_entry_stat_info(entry: Entry) -> tuple[float, float, int]:
    if entry.zip_path is None or entry.zip_name is None:
        return 0.0, entry.mtime, entry.size
    try:
        with tarfile.open(entry.zip_path, "r:*") as archive:
            if entry.is_dir:
                prefix = normalize_zip_dir(entry.zip_name)
                infos = [info for info in archive.getmembers() if normalize_tar_name(info.name).startswith(prefix)]
                size = sum(info.size for info in infos if info.isfile())
                stamps = [tar_info_mtime(info) for info in infos]
                stamp = min(stamps) if stamps else entry.mtime
                return stamp, entry.mtime, size
            info = tar_member_for_name(archive, entry.zip_name)
            if info is None:
                return 0.0, entry.mtime, entry.size
            stamp = tar_info_mtime(info)
            return stamp, stamp, info.size
    except (OSError, tarfile.TarError):
        return 0.0, entry.mtime, entry.size


def directory_total_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
    return total


def long_datetime(stamp: float) -> str:
    if stamp <= 0:
        return "0000-00-00 00:00:00"
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stamp))
    except (OverflowError, ValueError):
        return "0000-00-00 00:00:00"


def is_owner_entry(entry: Entry) -> bool:
    return entry.search_text == "__ownerpath__"


def owner_entry(cwd: Path) -> Entry | None:
    parent = cwd.parent
    if parent == cwd:
        return None
    try:
        mtime = parent.stat().st_mtime
    except OSError:
        mtime = 0.0
    return Entry(parent, "..", True, 0, mtime=mtime, search_text="__ownerpath__")


def zip_owner_entry(zip_path: Path, zip_dir: str) -> Entry | None:
    if not zip_dir:
        return None
    return Entry(zip_path, "..", True, 0, zip_path, zip_dir, zip_parent_mtime(zip_path, zip_dir), search_text="__ownerpath__")


def zip_parent_mtime(zip_path: Path, zip_dir: str) -> float:
    if is_tar_archive_path(zip_path):
        return tar_parent_mtime(zip_path, zip_dir)
    parent = parent_zip_dir(zip_dir)
    if not parent:
        try:
            return zip_path.stat().st_mtime
        except OSError:
            return 0.0
    target = normalize_zip_dir(parent)
    try:
        with zipfile.ZipFile(zip_path) as archive:
            exact = next((info for info in archive.infolist() if normalize_zip_dir(info.filename) == target), None)
            if exact is not None:
                return zip_info_mtime(exact)
            stamps = [zip_info_mtime(info) for info in archive.infolist() if info.filename.startswith(target)]
            if stamps:
                return min(stamps)
    except (OSError, zipfile.BadZipFile):
        pass
    try:
        return zip_path.stat().st_mtime
    except OSError:
        return 0.0


def tar_parent_mtime(tar_path: Path, tar_dir: str) -> float:
    parent = parent_zip_dir(tar_dir)
    if not parent:
        try:
            return tar_path.stat().st_mtime
        except OSError:
            return 0.0
    target = normalize_zip_dir(parent)
    try:
        with tarfile.open(tar_path, "r:*") as archive:
            exact = next((info for info in archive.getmembers() if normalize_tar_name(info.name).rstrip("/") == target.rstrip("/")), None)
            if exact is not None:
                return tar_info_mtime(exact)
            stamps = [tar_info_mtime(info) for info in archive.getmembers() if normalize_tar_name(info.name).startswith(target)]
            if stamps:
                return min(stamps)
    except (OSError, tarfile.TarError):
        pass
    try:
        return tar_path.stat().st_mtime
    except OSError:
        return 0.0


def rename_template(template: str, entry: Entry, index: int, width: int) -> str:
    try:
        stat_result = entry.path.stat()
        created = getattr(stat_result, "st_birthtime", stat_result.st_ctime)
        stamp = time.strftime("%Y%m%d%H%M%S", time.localtime(created))
    except OSError:
        stamp = time.strftime("%Y%m%d%H%M%S")
    values = {
        "${file}": entry.path.stem if not entry.is_dir else entry.name,
        "${ext}": entry.path.suffix[1:] if not entry.is_dir and entry.path.suffix else "",
        "${datetime}": stamp,
        "${index}": f"{index:0{width}d}",
    }
    name = template
    for key, value in values.items():
        name = name.replace(key, value)
    return name


def setting_true(value: object) -> bool:
    return isinstance(value, str) and value.strip().lower() in ("true", "enable", "1", "yes", "on")


def load_config(base_dir: Path) -> AppConfig:
    data: dict[str, object] = {}
    config_path = find_config(base_dir)
    if config_path is not None:
        try:
            raw = config_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except OSError as exc:
            raise ConfigError(f"{config_path.name}: read failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"{config_path.name}: JSON error at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc

    launchers = parse_command_items(data.get("launcher"))
    launchers.extend(parse_command_items(data.get("luncher")))
    execs = parse_exec_items(data.get("exec"))
    directories = parse_command_items(data.get("directory"))
    setting = data.get("setting")
    editor = ""
    shell = ""
    autosave_runlog = False
    autosave_runlog_path = ""
    quit_prompt = False
    show_ownerpath = False
    change_file_datetime = False
    diff_jump_before = 0
    if isinstance(setting, dict):
        value = setting.get("editor")
        if isinstance(value, str):
            editor = value
        value = setting.get("sh")
        if isinstance(value, str):
            shell = value
        value = setting.get("autosave_runlog")
        if isinstance(value, str):
            autosave_runlog = value.lower() == "enable"
        value = setting.get("autosave_runlog_path")
        if isinstance(value, str):
            autosave_runlog_path = value
        value = setting.get("quit_prompt")
        quit_prompt = setting_true(value)
        value = setting.get("show_ownerpath")
        show_ownerpath = setting_true(value)
        value = setting.get("change_file_datetime")
        change_file_datetime = setting_true(value)
        value = setting.get("diff_jump_before")
        if isinstance(value, (str, int, float)):
            try:
                diff_jump_before = max(0, int(float(value)))
            except ValueError:
                pass
    painwidth = load_painwidth(setting)
    thurupaths = load_thurupaths(data)
    guards = load_windows_guards(data)
    colors = load_colors(setting)
    syntax = load_syntax(data.get("syntax"))
    EDITOR_STATE.syntax = syntax
    if not editor:
        editor = default_editor()
    def_name = config_path.name if config_path is not None else "builtin"
    return AppConfig(launchers, execs, directories, editor, shell, autosave_runlog, autosave_runlog_path, quit_prompt, def_name, colors, painwidth, diff_jump_before, thurupaths, guards, show_ownerpath, change_file_datetime, syntax)


def find_config(base_dir: Path) -> Path | None:
    env_name = platform_config_name()
    candidates = [
        base_dir / env_name,
        base_dir / "vfiler.def",
        Path(__file__).resolve().with_name(env_name),
        Path(__file__).resolve().with_name("vfiler.def"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def platform_config_name() -> str:
    if IS_WINDOWS:
        if os.environ.get("TERM_PROGRAM") == "vscode":
            return "vfiler.win.vscode.def"
        return "vfiler.win.shell.def"
    return "vfiler.mac.def"


def current_os_key() -> str:
    if IS_WINDOWS:
        return "win"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def item_os_matches(raw_item: dict[object, object]) -> bool:
    value = raw_item.get("os")
    if value is None:
        return True
    if isinstance(value, str):
        return value.lower() == current_os_key()
    if isinstance(value, list):
        return any(isinstance(item, str) and item.lower() == current_os_key() for item in value)
    return False


def parse_command_items(value: object) -> list[CommandItem]:
    if not isinstance(value, list):
        return []
    items: list[CommandItem] = []
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue
        if not item_os_matches(raw_item):
            continue
        title = raw_item.get("title")
        command = raw_item.get("command")
        charset = raw_item.get("char")
        screen = raw_item.get("screen")
        if isinstance(title, str) and isinstance(command, str):
            items.append(CommandItem(title, command, False, charset if isinstance(charset, str) else "", screen if isinstance(screen, str) else ""))
    return items


def parse_exec_items(value: object) -> dict[str, CommandItem]:
    if not isinstance(value, list):
        return {}
    items: dict[str, CommandItem] = {}
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue
        if not item_os_matches(raw_item):
            continue
        ext = raw_item.get("ext")
        command = raw_item.get("command")
        if isinstance(ext, str) and isinstance(command, str):
            key = ext.lower().lstrip(".")
            items[key] = CommandItem(key, command)
    return items


def system_directory_items() -> list[CommandItem]:
    if IS_WINDOWS:
        return windows_drive_items()
    if sys.platform == "darwin":
        return mac_volume_items()
    return []


def windows_drive_items() -> list[CommandItem]:
    items: list[CommandItem] = []
    for letter in string.ascii_uppercase:
        path = f"{letter}:\\"
        if Path(path).exists():
            items.append(CommandItem(f"[{letter}:]", path))
    return items


def mac_volume_items() -> list[CommandItem]:
    items: list[CommandItem] = [CommandItem("[~]", "~")]
    root = Path("/Volumes")
    if not root.is_dir():
        return items
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if path.is_dir():
            items.append(CommandItem(f"[{path.name}]", str(path)))
    return items


def load_colors(setting: object) -> dict[str, str]:
    colors = {
        "dir_color": "blue",
        "dot_file_color": "red",
        "zip_file_color": "green",
        "file_color": "",
        "search_match_color": "30;43",
        "editor_readonly_bar_color": "30;43",
        "editor_edit_bar_color": "30;46",
        "editor_lf_color": "yellow",
        "editor_cr_color": "red",
        "editor_crlf_color": "cyan",
        "editor_tab_color": "cyan",
        "editor_bin_color": "7",
        "filer_active_bar_color": "30;46",
        "log_prompt_color": "yellow",
        "log_input_text_color": "cyan",
        "log_input_existing_path_color": "yellow",
        "log_input_missing_path_color": "magenta",
        "log_input_unclosed_string_color": "bright_red",
    }
    if isinstance(setting, dict):
        for key in colors:
            value = setting.get(key)
            if isinstance(value, str):
                colors[key] = value
    return colors


def default_syntax() -> dict[str, dict[str, object]]:
    py_keywords = "False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield".split()
    md_regex = [
        {"pattern": r"^# .*$", "color": "bright_cyan"},
        {"pattern": r"^## .*$", "color": "cyan"},
        {"pattern": r"^### .*$", "color": "bright_blue"},
        {"pattern": r"^#### .*$", "color": "blue"},
        {"pattern": r"^##### .*$", "color": "magenta"},
        {"pattern": r"^###### .*$", "color": "gray"},
    ]
    return {
        "py": {
            "keywords": py_keywords,
            "keyword_color": "cyan",
            "comment_color": "green",
            "string_color": "yellow",
            "number_color": "magenta",
        },
        "json": {
            "keywords": ["true", "false", "null"],
            "keyword_color": "magenta",
            "string_color": "green",
            "number_color": "cyan",
        },
        "md": {
            "regex": md_regex,
            "keywords": [],
            "keyword_color": "cyan",
            "comment_color": "gray",
            "string_color": "yellow",
        },
        "markdown": {
            "regex": md_regex,
            "keywords": [],
            "keyword_color": "cyan",
            "comment_color": "gray",
            "string_color": "yellow",
        },
    }


def load_syntax(value: object) -> dict[str, dict[str, object]]:
    rules = default_syntax()
    if not isinstance(value, dict):
        return rules
    for raw_ext, raw_rule in value.items():
        if not isinstance(raw_ext, str) or not isinstance(raw_rule, dict):
            continue
        ext = raw_ext.lower().lstrip(".")
        rule = dict(rules.get(ext, {}))
        keywords = raw_rule.get("keywords")
        if isinstance(keywords, list):
            rule["keywords"] = [item for item in keywords if isinstance(item, str)]
        regex_rules = raw_rule.get("regex")
        if isinstance(regex_rules, list):
            valid_regex = []
            for item in regex_rules:
                if not isinstance(item, dict):
                    continue
                pattern = item.get("pattern")
                color = item.get("color")
                if not isinstance(pattern, str) or not isinstance(color, str):
                    continue
                try:
                    re.compile(pattern)
                except re.error:
                    continue
                valid_regex.append({"pattern": pattern, "color": color})
            rule["regex"] = valid_regex
        for key in ("keyword_color", "comment_color", "string_color", "number_color"):
            item = raw_rule.get(key)
            if isinstance(item, str):
                rule[key] = item
        if rule:
            rules[ext] = rule
    return rules


def load_painwidth(setting: object) -> float:
    if isinstance(setting, dict):
        value = setting.get("painwidth")
        if isinstance(value, (str, int, float)):
            try:
                percent = float(value)
                return min(0.8, max(0.3, percent / 100.0))
            except ValueError:
                pass
    return 0.58


def load_thurupaths(setting: object) -> list[Path]:
    if not isinstance(setting, dict):
        return []
    value = setting.get("thurupaths")
    if not isinstance(value, list):
        return []
    paths: list[Path] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            paths.append(Path(item).expanduser())
        elif isinstance(item, dict) and item_os_matches(item):
            path = item.get("path")
            if isinstance(path, str) and path.strip():
                paths.append(Path(path).expanduser())
    return paths


def load_windows_guards(data: object) -> list[Path]:
    if not IS_WINDOWS or not isinstance(data, dict):
        return []
    windows = data.get("windows")
    if not isinstance(windows, dict):
        return []
    value = windows.get("guards")
    if not isinstance(value, list):
        return []
    paths: list[Path] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            paths.append(Path(item).expanduser())
    return paths


def is_thuru_path(path: Path, thurupaths: list[Path]) -> bool:
    if not thurupaths:
        return False
    target = normalize_compare_path(path)
    for base in thurupaths:
        base_text = normalize_compare_path(base)
        if target == base_text:
            return True
        if IS_WINDOWS and target.lower() == base_text.lower():
            return True
    return False


def is_guard_path(path: Path, guards: list[Path]) -> bool:
    if not guards:
        return False
    target = normalize_compare_path(path)
    for base in guards:
        base_text = normalize_compare_path(base)
        if target == base_text:
            return True
        if IS_WINDOWS and target.lower() == base_text.lower():
            return True
    return False


def external_command_stdio_kwargs(charset: str = "") -> dict[str, object]:
    if not IS_WINDOWS or not charset:
        return {}
    value = charset.strip().lower().replace("_", "-")
    if value == "utf-8":
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        return {"env": env, "encoding": "utf-8"}
    if value == "cp932":
        return {"encoding": "cp932"}
    return {}


def external_command_popen_kwargs(charset: str = "") -> dict[str, object]:
    return external_command_stdio_kwargs(charset)


def external_command_run_kwargs(charset: str = "") -> dict[str, object]:
    return external_command_stdio_kwargs(charset)


def normalize_compare_path(path: Path) -> str:
    try:
        return str(path.expanduser().resolve())
    except OSError:
        return str(path.expanduser())


def relative_command_path(path: Path, base: Path | str) -> str:
    if not isinstance(base, Path):
        return quote_path(path.name)
    try:
        rel = path.relative_to(base)
        text = rel.as_posix()
        return quote_path(text)
    except ValueError:
        return quote_path(path.name)


def expand_command(template: str, path: Path | None, pane_path: Path | str, other_path: Path | str, entries: list[Entry] | None = None) -> str:
    command = template.replace("%ps", quote_path(other_path)).replace("%p", quote_path(pane_path))
    if "%**" in command:
        rel_paths = [relative_command_path(item.path, pane_path) for item in (entries or [])]
        if not rel_paths and path is not None:
            rel_paths = [relative_command_path(path, pane_path)]
        command = command.replace("%**", " ".join(rel_paths))
    if "%*" in command:
        paths = [quote_path(item.path) for item in (entries or [])]
        if not paths and path is not None:
            paths = [quote_path(path)]
        command = command.replace("%*", " ".join(paths))
    if path is None:
        return command
    if "%b" in command:
        command = command.replace("%b", path.stem)
    file_path = quote_path(path)
    if "%f" in command:
        command = command.replace("%f", file_path)
    return command


def expand_prompt_vars(command: str) -> str:
    now = time.localtime()
    return command.replace("${DATE}", time.strftime("%Y%m%d", now)).replace("${TIME}", time.strftime("%H%M", now))


def read_only_bell(term: Terminal) -> str:
    term.write("\a")
    term.flush()
    return "read only"


def build_command_output(command: str, returncode: int, stdout: str, stderr: str) -> str:
    parts = [f"$ {command}", f"exit code: {returncode}"]
    if stdout:
        parts.extend(["", "[stdout]", stdout.rstrip("\n")])
    if stderr:
        parts.extend(["", "[stderr]", stderr.rstrip("\n")])
    if not stdout and not stderr:
        parts.extend(["", "(no output)"])
    return "\n".join(parts)


def load_run_history() -> list[str]:
    try:
        return [line.rstrip("\n") for line in RUN_HISTORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


def save_run_history(history: list[str]) -> None:
    try:
        RUN_HISTORY_PATH.write_text("\n".join(history[-200:]) + ("\n" if history else ""), encoding="utf-8")
    except OSError:
        pass


def load_stat() -> None:
    global FILER_STAT
    if NO_STAT:
        return
    data = read_stat_file()
    if data is None:
        return
    FILER_STAT = data
    EDITOR_STATE.wrap = bool(data.get("wrap", EDITOR_STATE.wrap))
    EDITOR_STATE.line_numbers = bool(data.get("line_numbers", EDITOR_STATE.line_numbers))
    EDITOR_STATE.show_datetime = bool(data.get("show_datetime", EDITOR_STATE.show_datetime))
    EDITOR_STATE.hide_empty_directories = bool(data.get("hide_empty_directories", EDITOR_STATE.hide_empty_directories))
    EDITOR_STATE.mouse_cursor = bool(data.get("mouse_cursor", EDITOR_STATE.mouse_cursor))
    EDITOR_STATE.wheel_scroll = bool(data.get("wheel_scroll", EDITOR_STATE.wheel_scroll))
    EDITOR_STATE.ruler = bool(data.get("ruler", EDITOR_STATE.ruler))
    EDITOR_STATE.cursor_underline = bool(data.get("cursor_underline", EDITOR_STATE.cursor_underline))
    EDITOR_STATE.vi_mode = bool(data.get("vi_mode", EDITOR_STATE.vi_mode))
    EDITOR_STATE.show_enter = bool(data.get("show_enter", EDITOR_STATE.show_enter))
    EDITOR_STATE.show_tab = bool(data.get("show_tab", EDITOR_STATE.show_tab))
    EDITOR_STATE.show_bin = bool(data.get("show_bin", EDITOR_STATE.show_bin))
    EDITOR_STATE.bookmarks = load_bookmarks(data.get("bookmarks"))
    EDITOR_STATE.find_history = load_string_list(data.get("find_history"))
    EDITOR_STATE.replace_history = load_string_list(data.get("replace_history"))
    tab_spaces = data.get("tab_spaces")
    if isinstance(tab_spaces, int) and 1 <= tab_spaces <= 16:
        EDITOR_STATE.tab_spaces = tab_spaces


def save_stat(filer: dict[str, object] | None = None) -> bool:
    global FILER_STAT
    if NO_STAT:
        return True
    if filer is None:
        old = FILER_STAT.get("filer")
        filer = old if isinstance(old, dict) else None
    local_data = {
        "wrap": EDITOR_STATE.wrap,
        "line_numbers": EDITOR_STATE.line_numbers,
        "show_datetime": EDITOR_STATE.show_datetime,
        "hide_empty_directories": EDITOR_STATE.hide_empty_directories,
        "mouse_cursor": EDITOR_STATE.mouse_cursor,
        "wheel_scroll": EDITOR_STATE.wheel_scroll,
        "ruler": EDITOR_STATE.ruler,
        "cursor_underline": EDITOR_STATE.cursor_underline,
        "vi_mode": EDITOR_STATE.vi_mode,
        "show_enter": EDITOR_STATE.show_enter,
        "show_tab": EDITOR_STATE.show_tab,
        "show_bin": EDITOR_STATE.show_bin,
        "tab_spaces": EDITOR_STATE.tab_spaces,
        "bookmarks": [{"title": item.title, "path": item.command} for item in (EDITOR_STATE.bookmarks or [])],
        "find_history": (EDITOR_STATE.find_history or [])[-50:],
        "replace_history": (EDITOR_STATE.replace_history or [])[-50:],
    }
    if filer is not None:
        local_data["filer"] = filer
    try:
        with StatWriteLock(STAT_LOCK_PATH):
            disk_data = read_stat_file() or {}
            data = merge_stat_data(FILER_STAT, disk_data, local_data)
            write_stat_file(data)
            FILER_STAT = data
            EDITOR_STATE.bookmarks = load_bookmarks(data.get("bookmarks"))
            return True
    except OSError:
        return False


def read_stat_file() -> dict[str, object] | None:
    try:
        data = json.loads(STAT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_stat_file(data: dict[str, object]) -> None:
    STAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=STAT_PATH.parent, prefix=STAT_PATH.name + ".", suffix=".tmp", delete=False) as handle:
        tmp_path = Path(handle.name)
        json.dump(data, handle, indent=2)
        handle.write("\n")
    try:
        tmp_path.replace(STAT_PATH)
    except OSError:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


class StatWriteLock:
    def __init__(self, path: Path, timeout: float = 1.0, stale_after: float = 10.0) -> None:
        self.path = path
        self.timeout = timeout
        self.stale_after = stale_after
        self.fd: int | None = None

    def __enter__(self) -> "StatWriteLock":
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(self.fd, f"{os.getpid()}\n{time.time()}\n".encode("ascii", errors="replace"))
                return self
            except FileExistsError:
                self.remove_stale_lock()
                if time.monotonic() >= deadline:
                    raise OSError(f"stat lock timeout: {self.path}")
                time.sleep(0.02)

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self.fd is not None:
            try:
                os.close(self.fd)
            finally:
                self.fd = None
        try:
            self.path.unlink()
        except OSError:
            pass

    def remove_stale_lock(self) -> None:
        try:
            stat_result = self.path.stat()
        except OSError:
            return
        if time.time() - stat_result.st_mtime <= self.stale_after:
            return
        try:
            self.path.unlink()
        except OSError:
            pass


def merge_stat_data(base: dict[str, object], remote: dict[str, object], local: dict[str, object]) -> dict[str, object]:
    data = dict(remote)
    for key, value in local.items():
        if key in ("bookmarks", "find_history", "replace_history"):
            continue
        data[key] = value
    data["bookmarks"] = dump_bookmarks(merge_bookmarks(load_bookmarks(base.get("bookmarks")), load_bookmarks(remote.get("bookmarks")), load_bookmarks(local.get("bookmarks"))))
    data["find_history"] = merge_string_history(load_string_list(remote.get("find_history")), load_string_list(local.get("find_history")), 50)
    data["replace_history"] = merge_string_history(load_string_list(remote.get("replace_history")), load_string_list(local.get("replace_history")), 50)
    return data


def dump_bookmarks(items: list[CommandItem]) -> list[dict[str, str]]:
    return [{"title": item.title, "path": item.command} for item in items]


def bookmark_key(item: CommandItem) -> tuple[str, str]:
    return item.title, item.command


def merge_bookmarks(base: list[CommandItem], remote: list[CommandItem], local: list[CommandItem]) -> list[CommandItem]:
    local_keys = {bookmark_key(item) for item in local}
    deleted_keys = {bookmark_key(item) for item in base if bookmark_key(item) not in local_keys}
    result: list[CommandItem] = []
    seen: set[tuple[str, str]] = set()
    for item in remote:
        key = bookmark_key(item)
        if key in deleted_keys or key in seen:
            continue
        result.append(item)
        seen.add(key)
    for item in local:
        key = bookmark_key(item)
        if key in seen:
            continue
        result.append(item)
        seen.add(key)
    return result


def merge_string_history(remote: list[str], local: list[str], limit: int) -> list[str]:
    values: list[str] = []
    for item in remote + local:
        if item in values:
            values.remove(item)
        values.append(item)
    return values[-limit:]


def load_bookmarks(value: object) -> list[CommandItem]:
    if not isinstance(value, list):
        return []
    items: list[CommandItem] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        title = raw.get("title")
        path = raw.get("path")
        if isinstance(title, str) and isinstance(path, str):
            items.append(CommandItem(title, path))
    return items


def load_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value[-50:] if isinstance(item, str)]


def read_process_stream(stream, events: queue.Queue[tuple[str, str | int]], kind: str) -> None:  # type: ignore[no-untyped-def]
    try:
        for line in stream:
            events.put((kind, line))
    finally:
        stream.close()
        events.put((kind + "_done", 1))


def wrap_output_lines(text: str, columns: int) -> list[str]:
    width = max(1, columns)
    rows: list[str] = []
    for raw in text.splitlines() or [""]:
        line = raw.replace("\t", "    ")
        if not line:
            rows.append("")
            continue
        while display_width(line) > width:
            part = ""
            for char in line:
                if display_width(part + char) > width:
                    break
                part += char
            rows.append(part)
            line = line[len(part):]
        rows.append(line)
    return rows


def quote_path(path: Path | str) -> str:
    text = str(path)
    if IS_WINDOWS:
        return '"' + text.replace('"', r"\"") + '"'
    return shlex.quote(text)


def same_existing_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def path_is_same_or_inside(path: Path, base: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(base.resolve(strict=False))
        return True
    except ValueError:
        return False


def retarget_path_after_rename(path: Path, old_path: Path, new_path: Path) -> Path:
    try:
        rel = path.resolve(strict=False).relative_to(old_path.resolve(strict=False))
    except ValueError:
        return path
    return new_path / rel


def nearest_existing_dir(path: Path, fallback: Path) -> Path:
    target = path.expanduser()
    while True:
        if target.is_dir():
            return target.resolve()
        parent = target.parent
        if parent == target:
            break
        target = parent
    if fallback.is_dir():
        return fallback.resolve()
    return Path.cwd().resolve()


def is_path_inside(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return path.resolve() != base.resolve()
    except (OSError, ValueError):
        return False


def remove_file_target(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, onerror=remove_readonly_error)
    else:
        try:
            path.unlink()
        except PermissionError:
            make_writable(path)
            path.unlink()


def remove_readonly_error(func, path: str, _exc_info) -> None:  # type: ignore[no-untyped-def]
    target = Path(path)
    make_writable(target)
    func(path)


def make_writable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def overwrite_prompt(target: Path, multi: bool) -> str:
    if not multi:
        return f"overwrite {target.name}? y/N"
    hot = "4;95"
    return (
        f"overwrite {target.name}? "
        f"{color_text('a', hot)}ll/"
        f"{color_text('y', hot)}es/"
        f"{color_text('c', hot)}ancel/"
        f"{color_text('N', hot)}o"
    )


def edit_line(term: Terminal, label: str, default: str) -> str:
    text = list(default)
    cursor = len(text)
    offset = 0

    while True:
        columns, lines = term.size()
        prefix = f"{label}: "
        field_width = max(1, columns - display_width(prefix))
        while display_width("".join(text[offset:cursor])) > field_width:
            offset += 1
        while cursor < offset:
            offset -= 1

        visible = ""
        for ch in text[offset:]:
            if display_width(visible + ch) > field_width:
                break
            visible += ch

        term.move(lines, 1)
        term.write("\x1b[2K")
        term.write(prefix + fit(visible, field_width))
        cursor_col = 1 + display_width(prefix) + display_width("".join(text[offset:cursor]))
        term.move(lines, cursor_col)
        term.flush()

        key = read_key()
        if key == KEY_ENTER:
            return "".join(text)
        if key == KEY_ESCAPE:
            return ""
        if key == KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == KEY_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif key == KEY_HOME:
            cursor = 0
            offset = 0
        elif key == KEY_END:
            cursor = len(text)
        elif key == KEY_BACKSPACE:
            if cursor > 0:
                del text[cursor - 1]
                cursor -= 1
        elif key == KEY_DELETE:
            if cursor < len(text):
                del text[cursor]
        elif key and is_text_input(key):
            text[cursor:cursor] = list(key)
            cursor += len(key)


def edit_line_history(term: Terminal, label: str, default: str, history: list[str]) -> str:
    text = list(default)
    cursor = len(text)
    offset = 0
    hist = len(history)

    while True:
        columns, lines = term.size()
        prefix = f"{label}: "
        field_width = max(1, columns - display_width(prefix))
        while display_width("".join(text[offset:cursor])) > field_width:
            offset += 1
        while cursor < offset:
            offset -= 1

        visible = ""
        for ch in text[offset:]:
            if display_width(visible + ch) > field_width:
                break
            visible += ch

        term.move(lines, 1)
        term.write("\x1b[2K")
        term.write(prefix + fit(visible, field_width))
        cursor_col = 1 + display_width(prefix) + display_width("".join(text[offset:cursor]))
        term.move(lines, cursor_col)
        term.flush()

        key = read_key()
        if key == KEY_ENTER:
            return "".join(text)
        if key == KEY_ESCAPE:
            return ""
        if key in (KEY_UP, KEY_DOWN) and history:
            hist += -1 if key == KEY_UP else 1
            hist = min(len(history), max(0, hist))
            value = default if hist == len(history) else history[hist]
            text = list(value)
            cursor = len(text)
            offset = 0
        elif key == KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == KEY_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif key == KEY_HOME:
            cursor = 0
            offset = 0
        elif key == KEY_END:
            cursor = len(text)
        elif key == KEY_BACKSPACE:
            if cursor > 0:
                del text[cursor - 1]
                cursor -= 1
        elif key == KEY_DELETE:
            if cursor < len(text):
                del text[cursor]
        elif key and is_text_input(key):
            text[cursor:cursor] = list(key)
            cursor += len(key)


def popup_edit_line(term: Terminal, label: str, default: str, redraw: Callable[[], None] | None = None, history: list[str] | None = None) -> str:
    flush_pending_input()
    text = list(default)
    cursor = len(text)
    offset = 0
    hist = len(history) if history is not None else 0

    while True:
        if redraw is not None:
            redraw()
        columns, lines = term.size()
        width = min(max(40, (columns * 2) // 3), max(20, columns - 4))
        field_width = max(1, width - 2)
        title = f" {label} "
        while display_width("".join(text[offset:cursor])) > max(0, field_width - 1):
            offset += 1
        while cursor < offset:
            offset -= 1

        visible = ""
        for ch in text[offset:]:
            if display_width(visible + ch) > field_width:
                break
            visible += ch

        row = max(2, (lines - 4) // 2 + 1)
        col = max(1, (columns - width) // 2 + 1)
        title_row = yellow("█") + fit(title, width - 2) + yellow("█")
        body = yellow("█") + fit(visible, field_width) + yellow("█")
        hint = "Enter:OK  ESC:Cancel"
        term.move(row, col)
        term.write(yellow("█" * width))
        term.move(row + 1, col)
        term.write(title_row)
        term.move(row + 2, col)
        term.write(body)
        term.move(row + 3, col)
        term.write(yellow_bg(fit(hint, width)))
        cursor_col = col + 1 + min(field_width - 1, display_width("".join(text[offset:cursor])))
        term.move(row + 2, max(col + 1, min(col + width - 2, cursor_col)))
        term.flush()

        key = read_key()
        if key == KEY_ENTER:
            return "".join(text)
        if key == KEY_ESCAPE:
            return ""
        if history is not None and key in (KEY_UP, KEY_DOWN) and history:
            hist += -1 if key == KEY_UP else 1
            hist = min(len(history), max(0, hist))
            value = default if hist == len(history) else history[hist]
            text = list(value)
            cursor = len(text)
            offset = 0
        elif key == KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == KEY_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif key == KEY_HOME:
            cursor = 0
            offset = 0
        elif key == KEY_END:
            cursor = len(text)
        elif key == KEY_BACKSPACE:
            if cursor > 0:
                del text[cursor - 1]
                cursor -= 1
        elif key == KEY_DELETE:
            if cursor < len(text):
                del text[cursor]
        elif key and is_text_input(key):
            text[cursor:cursor] = list(key)
            cursor += len(key)


def tty_write(fd: int, text: str) -> None:
    os.write(fd, text.encode("utf-8", errors="replace"))


def tty_read_key(fd: int) -> str:
    ch = os.read(fd, 1)
    if ch in (b"\n", b"\r"):
        return KEY_ENTER
    if ch in (b"\x7f", b"\b"):
        return KEY_BACKSPACE
    if ch != b"\x1b":
        return read_utf8_char(fd, ch)

    rest = b""
    while select.select([fd], [], [], 0.08)[0]:
        rest += os.read(fd, 1)
        if rest.endswith(b"~") or (rest.startswith(b"[") and rest[-1:] in b"ABCDMm"):
            break
        if len(rest) >= 16:
            break
    if rest == b"[D":
        return KEY_LEFT
    if rest == b"[C":
        return KEY_RIGHT
    if rest == b"[A":
        return KEY_UP
    if rest == b"[B":
        return KEY_DOWN
    if rest in (b"[H", b"[1~"):
        return KEY_HOME
    if rest in (b"[F", b"[4~"):
        return KEY_END
    if rest == b"[3~":
        return KEY_DELETE
    if rest:
        return ""
    return KEY_ESCAPE


def shell_popup_input(label: str, default: str = "") -> str | None:
    kind, value = shell_popup_choice(label, default, [])
    return value if kind == "text" else None


def shell_popup_choice(label: str, default: str = "", buffers: list[str] | None = None) -> tuple[str, str] | tuple[None, None]:
    if IS_WINDOWS:
        print("--shell-popup is only implemented for POSIX terminals", file=sys.stderr)
        return None, None
    buffers = buffers or []
    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
    except OSError as exc:
        if not sys.stdin.isatty():
            print(f"tty open failed: {exc}", file=sys.stderr)
            return None, None
        tty_fd = os.dup(sys.stdin.fileno())
    old = termios.tcgetattr(tty_fd)
    text = list(default)
    cursor = len(text)
    offset = 0
    selected_buffer = -1
    popup_height = 4 + min(len(buffers), 6)
    try:
        tty.setcbreak(tty_fd)
        attrs = termios.tcgetattr(tty_fd)
        attrs[0] &= ~(termios.IXON | termios.IXOFF)
        attrs[3] &= ~(termios.ISIG | getattr(termios, "IEXTEN", 0))
        termios.tcsetattr(tty_fd, termios.TCSADRAIN, attrs)
        tty_write(tty_fd, "\x1b[s\x1b[?25l")
        while True:
            size = shutil.get_terminal_size(fallback=(100, 28))
            columns, lines = size.columns, size.lines
            width = min(48, max(40, columns - 4))
            field_width = max(1, width - 2)
            row = max(2, (lines - popup_height) // 2 + 1)
            col = max(1, (columns - width) // 2 + 1)
            title = f" {label} "
            while display_width("".join(text[offset:cursor])) > max(0, field_width - 1):
                offset += 1
            while cursor < offset:
                offset -= 1
            visible = ""
            for ch in text[offset:]:
                if display_width(visible + ch) > field_width:
                    break
                visible += ch
            hint = "Enter:OK  ESC:Cancel"
            rows = [
                yellow("█" * width),
                yellow("█") + fit(title, field_width) + yellow("█"),
                yellow("█") + fit(visible, field_width) + yellow("█"),
            ]
            for index, item in enumerate(buffers[:6]):
                prefix = "> " if index == selected_buffer else "  "
                row_text = prefix + item
                rows.append(yellow("█") + fit(reverse(row_text) if index == selected_buffer else row_text, field_width) + yellow("█"))
            rows.append(yellow_bg(fit(hint, width)))
            for index, line in enumerate(rows):
                tty_write(tty_fd, f"\x1b[{row + index};{col}H\x1b[K{line}")
            cursor_col = col + 1 + min(field_width - 1, display_width("".join(text[offset:cursor])))
            tty_write(tty_fd, f"\x1b[{row + 2};{max(col + 1, min(col + width - 2, cursor_col))}H\x1b[?25h")
            key = tty_read_key(tty_fd)
            tty_write(tty_fd, "\x1b[?25l")
            if key == KEY_ENTER:
                if selected_buffer >= 0:
                    return "buffer", str(selected_buffer)
                return "text", "".join(text)
            if key == KEY_ESCAPE:
                return None, None
            if key == KEY_LEFT:
                selected_buffer = -1
                cursor = max(0, cursor - 1)
            elif key == KEY_RIGHT:
                selected_buffer = -1
                cursor = min(len(text), cursor + 1)
            elif key == KEY_UP and buffers:
                selected_buffer = len(buffers[:6]) - 1 if selected_buffer < 0 else max(0, selected_buffer - 1)
            elif key == KEY_DOWN and buffers:
                selected_buffer = 0 if selected_buffer < 0 else min(len(buffers[:6]) - 1, selected_buffer + 1)
            elif key == KEY_HOME:
                selected_buffer = -1
                cursor = 0
                offset = 0
            elif key == KEY_END:
                selected_buffer = -1
                cursor = len(text)
            elif key == KEY_BACKSPACE:
                selected_buffer = -1
                if cursor > 0:
                    del text[cursor - 1]
                    cursor -= 1
            elif key == KEY_DELETE:
                selected_buffer = -1
                if cursor < len(text):
                    del text[cursor]
            elif key and is_text_input(key):
                selected_buffer = -1
                text[cursor:cursor] = list(key)
                cursor += len(key)
    finally:
        size = shutil.get_terminal_size(fallback=(100, 28))
        columns, lines = size.columns, size.lines
        width = min(48, max(40, columns - 4))
        row = max(2, (lines - popup_height) // 2 + 1)
        col = max(1, (columns - width) // 2 + 1)
        for index in range(popup_height):
            tty_write(tty_fd, f"\x1b[{row + index};{col}H\x1b[K")
        tty_write(tty_fd, "\x1b[u\x1b[?25h\x1b[0m")
        termios.tcsetattr(tty_fd, termios.TCSAFLUSH, old)
        os.close(tty_fd)


def is_text_input(key: str) -> bool:
    return len(key) == 1 and ord(key) >= 32 and key != "\x7f"


def reverse(text: str) -> str:
    return "\x1b[7m" + text + "\x1b[0m"


def reverse_ansi(text: str) -> str:
    if "\x1b[" not in text:
        return reverse(text)
    return "\x1b[7m" + text.replace("\x1b[0m", "\x1b[0m\x1b[7m") + "\x1b[0m"


def underline(text: str) -> str:
    return "\x1b[4m" + text + "\x1b[0m"


def underline_ansi(text: str) -> str:
    if "\x1b[" not in text:
        return underline(text)
    return "\x1b[4m" + text.replace("\x1b[0m", "\x1b[0m\x1b[4m") + "\x1b[0m"


def yellow(text: str) -> str:
    return "\x1b[33m" + text + "\x1b[0m"


def yellow_bg(text: str) -> str:
    return "\x1b[30;43m" + text + "\x1b[0m"


def color_text(text: str, color: str) -> str:
    code = color_code(color)
    if not code:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def reverse_color_text(text: str, color: str) -> str:
    code = color_code(color)
    if not code:
        return reverse(text)
    return f"\x1b[7;{code}m{text}\x1b[0m"


def menu_popup_col(bar_text: str, label: str, columns: int, width: int) -> int:
    index = bar_text.find(label)
    col = max(1, index + 1) if index >= 0 else 1
    return min(col, max(1, columns - width + 1))


def draw_menu_bar_highlight(term: Terminal, bar_text: str, label: str) -> None:
    index = bar_text.find(label)
    if index < 0:
        return
    term.move(1, index + 1)
    term.write(yellow_bg(label))


def color_code(color: str) -> str:
    names = {
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "gray": "90",
        "bright_red": "91",
        "bright_green": "92",
        "bright_yellow": "93",
        "bright_blue": "94",
        "bright_magenta": "95",
        "bright_cyan": "96",
        "bright_white": "97",
    }
    value = color.strip().lower().replace("-", "_")
    if not value or value in ("none", "default"):
        return ""
    if all(part.isdigit() for part in value.split(";")):
        return value
    return names.get(value, "")


def entry_color_name(entry: Entry, colors: dict[str, str]) -> str:
    if entry.is_dir:
        return colors["dir_color"]
    if entry.name.startswith("."):
        return colors["dot_file_color"]
    if entry.zip_path is None and is_zip_archive_path(entry.path):
        return colors["zip_file_color"]
    return colors["file_color"]


def entry_color(entry: Entry, text: str, colors: dict[str, str]) -> str:
    return color_text(text, entry_color_name(entry, colors))


def entry_cursor_color(entry: Entry, text: str, colors: dict[str, str]) -> str:
    return reverse_color_text(text, entry_color_name(entry, colors))


def default_editor() -> str:
    if IS_WINDOWS:
        return "notepad %f"
    return "vi %f"


def run_self_test() -> None:
    global NO_STAT, FILER_STAT, EDITOR_STATE
    old_no_stat = NO_STAT
    old_filer_stat = dict(FILER_STAT)
    old_editor_state = EDITOR_STATE
    NO_STAT = True
    FILER_STAT = {}
    EDITOR_STATE = EditorState([], [])
    try:
        run_self_test_body()
    finally:
        EDITOR_STATE = old_editor_state
        FILER_STAT = old_filer_stat
        NO_STAT = old_no_stat


def run_self_test_body() -> None:
    assert fit("abc", 5) == "abc  "
    assert display_width("abc") == 3
    assert detect_eol(b"a\nb\n") == "LF"
    assert detect_eol(b"a\r\nb\r\n") == "CRLF"
    assert detect_eol(b"a\rb\r") == "CR"
    assert detect_eol(b"a\r\nb\n") == "MIXED"
    assert detect_eol(b"abc") == "NONE"
    assert decode_editor_bytes(b"\xef\xbb\xbfabc")[1] == "UTF-8+BOM"
    assert decode_editor_bytes("日本".encode("utf-8"))[1] == "UTF-8"
    assert decode_editor_bytes("日本".encode("cp932"))[1] == "CP932"
    assert decode_editor_bytes(b"\x81")[1] == "LATIN-1"
    assert pretty_git_graph_line("* 1234567 msg (HEAD -> main)") == "○ 1234567 msg (HEAD -> main)"
    assert pretty_git_graph_line("| * 1234567 msg") == "│ ● 1234567 msg"
    assert pretty_git_graph_line("* | 1234567 msg") == "●─╯ 1234567 msg"
    assert pretty_git_graph_line("* / 1234567 msg") == "●─╯ 1234567 msg"
    assert git_graph_connector_line("|\\  ", True) == "│ │"
    assert git_graph_connector_line("|/  ", False) == "│"
    assert git_graph_connector_line("| |/  ", False) == "│ │"
    sample_commits = [
        GitTreeCommit("a", ["b"], "aaaaaaa", "00", 0, "head", "(HEAD -> main)"),
        GitTreeCommit("b", ["f"], "bbbbbbb", "00", 0, "main", ""),
        GitTreeCommit("m", ["z", "c"], "mmmmmmm", "00", 0, "merge", "(origin/main)"),
        GitTreeCommit("c", ["d"], "ccccccc", "00", 0, "b1-2", "(b1)"),
        GitTreeCommit("d", ["f"], "ddddddd", "00", 0, "b1-1", ""),
        GitTreeCommit("f", ["z"], "fffffff", "00", 0, "t1", ""),
        GitTreeCommit("z", [], "zzzzzzz", "00", 0, "init", ""),
    ]
    sample_rows = [entry.name.split(" 00 ", 1)[0] for entry in render_git_tree_entries(Path("."), sample_commits)]
    assert sample_rows == ["○ aaaaaaa", "● bbbbbbb", "│ ●─╮ mmmmmmm", "│ │ ● ccccccc", "│ │ ● ddddddd", "●─┼─╯ fffffff", "●─╯ zzzzzzz"]
    colored_graph = color_git_graph_row("│ ●─╮ mmmmmmm")
    assert "\x1b[94m│\x1b[0m" in colored_graph and "\x1b[35m●\x1b[0m" in colored_graph
    assert "\x1b[0m\x1b[7m" in reverse_ansi(colored_graph)
    assert "\x1b[0m\x1b[4m" in underline_ansi("a\x1b[33m↓\x1b[0m ")
    assert parse_args(["--nostat"]).nostat is True
    assert setting_true("true") and setting_true("enable") and setting_true("YES")
    assert not setting_true("false") and not setting_true(None)
    old_windows = IS_WINDOWS
    try:
        globals()["IS_WINDOWS"] = False
        assert external_command_stdio_kwargs("utf-8") == {}
        globals()["IS_WINDOWS"] = True
        assert external_command_stdio_kwargs() == {}
        win_kwargs = external_command_stdio_kwargs("utf-8")
        assert win_kwargs["encoding"] == "utf-8"
        assert win_kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
        assert win_kwargs["env"]["PYTHONUTF8"] == "1"
        assert external_command_stdio_kwargs("cp932") == {"encoding": "cp932"}
        assert external_command_stdio_kwargs("sjis") == {}
    finally:
        globals()["IS_WINDOWS"] = old_windows
    owner = owner_entry(Path("/tmp/child"))
    assert owner is not None and owner.name == ".." and is_owner_entry(owner) and owner.mtime >= 0
    assert owner_entry(Path("/")) is None
    zip_owner = zip_owner_entry(Path("/tmp/test.zip"), "dir/sub/")
    assert zip_owner is not None and zip_owner.name == ".." and is_owner_entry(zip_owner) and zip_owner.mtime >= 0
    assert zip_owner_entry(Path("/tmp/test.zip"), "") is None
    assert is_image_path(Path("a.JPG")) and is_image_path(Path("b.webp"))
    assert entry_is_image(Entry(Path("a.jpg"), "a.jpg", False, 0))
    assert entry_is_image(Entry(Path("test.zip"), "a.png", False, 0, Path("test.zip"), "dir/a.png"))
    seq = iterm_image_sequence("a.png", b"\x89PNG")
    assert seq.startswith("\x1b]1337;File=") and "width=100%;height=100%" in seq and seq.endswith("\x07")
    old_stat_path = STAT_PATH
    old_stat_lock_path = STAT_LOCK_PATH
    old_no_stat = NO_STAT
    old_stat_data = dict(FILER_STAT)
    old_bookmarks = EDITOR_STATE.bookmarks
    try:
        with tempfile.TemporaryDirectory() as stat_temp:
            stat_root = Path(stat_temp)
            globals()["STAT_PATH"] = stat_root / "vfiler_stat.json"
            globals()["STAT_LOCK_PATH"] = stat_root / "vfiler_stat.json.lock"
            globals()["NO_STAT"] = False
            globals()["FILER_STAT"] = {}
            EDITOR_STATE.bookmarks = [CommandItem("one", "/one")]
            assert save_stat({"mode": "dual"})
            globals()["FILER_STAT"] = {}
            EDITOR_STATE.bookmarks = []
            assert save_stat({"mode": "preview"})
            saved = read_stat_file() or {}
            assert load_bookmarks(saved.get("bookmarks")) == [CommandItem("one", "/one")]
            one = {"title": "one", "path": "/one"}
            two = {"title": "two", "path": "/two"}
            three = {"title": "three", "path": "/three"}
            globals()["FILER_STAT"] = {"bookmarks": [one, two]}
            write_stat_file({"bookmarks": [one, two, three]})
            EDITOR_STATE.bookmarks = [CommandItem("two", "/two")]
            assert save_stat()
            saved = read_stat_file() or {}
            assert load_bookmarks(saved.get("bookmarks")) == [CommandItem("two", "/two"), CommandItem("three", "/three")]
    finally:
        globals()["STAT_PATH"] = old_stat_path
        globals()["STAT_LOCK_PATH"] = old_stat_lock_path
        globals()["NO_STAT"] = old_no_stat
        globals()["FILER_STAT"] = old_stat_data
        EDITOR_STATE.bookmarks = old_bookmarks
    parsed_commands = parse_command_items([{"title": "tool", "command": "run", "char": "cp932", "screen": "fullscreen"}])
    assert len(parsed_commands) == 1
    assert parsed_commands[0].charset == "cp932"
    assert parsed_commands[0].screen == "fullscreen"
    assert [gitignore_template_path(name).name for name in GITIGNORE_TEMPLATE_NAMES] == ["none.gitignore", "xcode.gitignore", "python.gitignore", "web.gitignore", "node.gitignore"]
    assert all(gitignore_template_path(name).exists() for name in GITIGNORE_TEMPLATE_NAMES)
    with tempfile.TemporaryDirectory() as nested_git_temp:
        nested_root = Path(nested_git_temp)
        nested_child = nested_root / "hoge"
        nested_subdir = nested_child / "subdir"
        (nested_root / ".git").mkdir()
        (nested_child / ".git").mkdir(parents=True)
        nested_subdir.mkdir()
        GIT_ROOT_CACHE.clear()
        assert git_root(nested_child) == nested_child.resolve()
        assert git_root(nested_subdir) == nested_child.resolve()
    unmanaged = git_status_entries_from_text(Path("."), " M tracked.py\n?? child/new.txt\n?? top.txt\n", True)
    assert [entry.name for entry in unmanaged] == ["child/new.txt", "top.txt"]
    status_entries = git_status_entries_from_text(Path("."), " M tracked.py\nA  added.txt\n?? child/new.txt\n", False)
    assert [(entry.search_text, entry.search_match) for entry in status_entries] == [(" M", "tracked.py"), ("A ", "added.txt"), ("??", "child/new.txt")]
    discard_command, discard_count, discard_untracked = git_discard_plan(Path("."), status_entries)
    assert discard_count == 3 and " restore --staged --worktree -- " in discard_command
    assert "tracked.py" in discard_command and "added.txt" in discard_command
    assert [path.as_posix() for path in discard_untracked] == ["child/new.txt"]
    managed = git_managed_entries_from_bytes(Path("."), b"a.txt\0dir/b.txt\0")
    assert [(entry.name, entry.search_match) for entry in managed] == [("a.txt", "a.txt"), ("dir/b.txt", "dir/b.txt")]
    unmanage_cmd, unmanage_count = git_unmanage_command(Path("."), managed)
    assert unmanage_count == 2 and " rm --cached -f -- " in unmanage_cmd
    assert display_width("日本") == 4
    assert display_width("ＡＢ") == 4
    assert display_width("e\u0301") == 1
    assert display_width("·") == 1
    assert ruler_line(12) == "----+----1--"
    assert "\x1b[7m+\x1b[0m" in ruler_line(12, 0, 4)
    assert filer_log_height(20, 3) == 3 and filer_body_height(20, 3) == 12
    assert filer_log_height(8, 99) == 2 and filer_body_height(8, 99) == 1
    assert filer_log_display_height(20, 3) == 4
    assert command_popup_item_height(50, 24, False) == 20
    assert command_popup_item_height(50, 24, True) == 20
    menu_app = FilerApp(Path("."), restore_stat=False)
    assert "F5:Reload" in menu_app.menu_bar_text() and "F6:Launch" in menu_app.menu_bar_text()
    assert menu_app.filer_menu_labels() == ["F1:Files", "F2:Edit", "F3:View", "F4:Git", "F6:Launch"]
    assert menu_app.watch_target(menu_app.pane) == menu_app.cwd
    menu_app.pane.search_mode = True
    assert menu_app.watch_target(menu_app.pane) is None
    menu_app.pane.search_mode = False
    menu_app.pane.watch_dirty = True
    assert menu_app.apply_auto_refresh() is True
    assert menu_app.status == "auto refreshed"
    menu_app.note_input_activity()
    resident_restart_app = FilerApp(Path("."), restore_stat=False)
    resident_restart_app.resident_mode = True
    resident_restart_app.restart_app(None)
    assert resident_restart_app.restart_requested is True
    assert resident_restart_app.running is False
    if not IS_WINDOWS:
        original_open = os.open
        original_close = os.close
        original_tcsetpgrp = os.tcsetpgrp
        os.open = lambda *_args, **_kwargs: 12345  # type: ignore[assignment]
        os.close = lambda _fd: None  # type: ignore[assignment]
        os.tcsetpgrp = lambda *_args: (_ for _ in ()).throw(termios.error(5, "Input/output error"))  # type: ignore[assignment]
        try:
            set_tty_foreground_pgrp(99999)
        finally:
            os.open = original_open  # type: ignore[assignment]
            os.close = original_close  # type: ignore[assignment]
            os.tcsetpgrp = original_tcsetpgrp  # type: ignore[assignment]
    assert resident_response_needs_restart({"ok": False, "error": "(5, 'Input/output error')"}) is True
    assert resident_response_needs_restart({"ok": False, "error": "[Errno 5] Input/output error"}) is True
    assert resident_response_needs_restart({"ok": False, "error": "buffer not found"}) is False
    assert resident_tty_path_from_id("dev_ttys000") == Path("/dev/ttys000")
    assert resident_terminal_alive("dev_vfiler_missing_tty_for_test") is False
    ps_text = " 123 python /Users/kds/Projects/2sfd/vfiler.py --z-server dev_ttys000\n 456 grep vfiler\n 789 python vfiler.py --z-server dev_ttys001\n"
    assert parse_resident_server_pids(ps_text, "dev_ttys000") == [123]
    with tempfile.TemporaryDirectory() as resident_temp:
        resident_root = Path(resident_temp)
        resident_other = resident_root / "other"
        resident_other.mkdir()
        resident_server = ResidentServer(resident_root / "resident.sock")
        resident_filer = resident_server.ensure_filer(resident_root)
        resident_filer.mode = "dual"
        resident_filer.active_pane = 1
        resident_filer.pane.search_mode = True
        resident_filer.pane.search_pattern = "needle"
        resident_filer.dual_ratio = 0.63
        resident_filer.log_lines.append("resident log")
        resident_filer.running = False
        resident_server.prepare_filer_for_resident(resident_filer, resident_other, True)
        assert resident_filer.running is True
        assert resident_filer.mode == "dual"
        assert resident_filer.active_pane == 1
        assert resident_filer.pane.search_mode is True
        assert resident_filer.pane.search_pattern == "needle"
        assert resident_filer.dual_ratio == 0.63
        assert resident_filer.log_lines == ["resident log"]
        resident_server.prepare_filer_for_resident(resident_filer, resident_other, False)
        assert resident_filer.mode == "preview"
        assert resident_filer.active_pane == 0
        assert same_existing_path(resident_filer.cwd, resident_other)
        assert resident_filer.pane.search_mode is False
        assert resident_filer.log_lines == ["resident log"]
    assert menu_app.idle_watch_tick() is False
    menu_app.last_input_time -= 2
    assert menu_app.idle_watch_due() is True
    assert menu_app.idle_watch_due() is False
    with tempfile.TemporaryDirectory() as watch_temp:
        watch_root = Path(watch_temp)
        watch_file = watch_root / "watch.txt"
        watch_file.write_text("old", encoding="utf-8")
        watch_app = FilerApp(watch_root, restore_stat=False)
        watch_app.refresh()
        assert watch_app.pane.watch_snapshot is not None
        time.sleep(0.001)
        watch_file.write_text("new data", encoding="utf-8")
        watch_app.mark_snapshot_changes_dirty()
        assert watch_app.pane.watch_dirty is True
        assert watch_app.apply_auto_refresh() is True
    with tempfile.TemporaryDirectory() as shell_temp:
        shell_root = Path(shell_temp)
        shell_child = shell_root / "child"
        shell_child.mkdir()
        shell_app = FilerApp(shell_child, restore_stat=False)
        shell_app.refresh()
        shutil.rmtree(shell_child)
        shell_app.last_input_time -= 2
        assert shell_app.idle_watch_tick() is True
        assert same_existing_path(shell_app.cwd, shell_root)
        shell_renamed = shell_root / "renamed"
        shell_renamed.mkdir()
        shell_app.cwd = shell_renamed
        shell_app.refresh()
        shell_renamed.rename(shell_root / "renamed2")
        shell_app.refresh()
        assert same_existing_path(shell_app.cwd, shell_root)
    old_windows = IS_WINDOWS
    try:
        globals()["IS_WINDOWS"] = True
        assert is_network_like_path(Path("//server/share"))
    finally:
        globals()["IS_WINDOWS"] = old_windows
    mount_rows = parse_mount_entries("dev on / (apfs, local, journaled)\n//u@srv/share on /Volumes/share (smbfs, nodev, nosuid)\n/dev/disk9s1 on /Volumes/RAID (apfs, local)\n")
    assert mount_rows == [("/", "apfs"), ("/Volumes/share", "smbfs"), ("/Volumes/RAID", "apfs")]
    old_cache = MAC_MOUNT_CACHE
    try:
        globals()["MAC_MOUNT_CACHE"] = (time.monotonic(), mount_rows)
        assert mac_mount_fs_type(Path("/Volumes/share/docs")) == "smbfs"
        assert mac_mount_fs_type(Path("/Volumes/RAID/work")) == "apfs"
    finally:
        globals()["MAC_MOUNT_CACHE"] = old_cache
    prompt_row = log_prompt_row_text("echo 123", 4, 20)
    assert ansi_width(prompt_row) == 20 and "\x1b[7m" in prompt_row
    assert ansi_width(log_prompt_row_text("1234567890", 10, 8)) == 8
    assert "/tmp/ $ \x1b[7m " in log_prompt_row_text("", 0, 20, "/tmp/ $ ")
    prompt_colors = load_colors({})
    colored_prompt = log_prompt_row_text_colored("./vfiler.py ./missing-file-for-test \"abc", 10, 80, "/tmp/ $ ", prompt_colors, Path.cwd())
    assert ansi_width(colored_prompt) == 80
    assert "\x1b[33m/tmp/ $ \x1b[0m" in colored_prompt
    assert "\x1b[33m" in colored_prompt and "\x1b[35m" in colored_prompt and "\x1b[91m" in colored_prompt
    size_app = FilerApp(Path("."), restore_stat=False)
    size_app.dual_ratio = 0.37
    size_app.log_height = 5
    size_app.panes[0].preview_ratio = 0.44
    size_app.panes[1].preview_ratio = 0.66
    size_app.panes[0].sort_key = "natural"
    size_stat = size_app.filer_stat()
    assert size_stat["dual_ratio"] == 0.37 and size_stat["log_height"] == 5
    restored_size_app = FilerApp(Path("."), restore_stat=False)
    restored_size_app.apply_saved_stat(size_stat)
    assert restored_size_app.dual_ratio == 0.37
    assert restored_size_app.log_height == 5
    assert restored_size_app.panes[0].preview_ratio == 0.44
    assert restored_size_app.panes[1].preview_ratio == 0.66
    assert restored_size_app.panes[0].sort_key == "natural"
    with tempfile.TemporaryDirectory() as pane_temp:
        pane_root = Path(pane_temp)
        left_dir = pane_root / "left"
        right_dir = pane_root / "right"
        right_child = right_dir / "child"
        left_dir.mkdir()
        right_child.mkdir(parents=True)
        pane_app = FilerApp(left_dir, right_child, restore_stat=False)
        pane_app.refresh_all()
        rename_entry = Entry(right_dir, "right", True, 0)
        original_prompt = pane_app.prompt
        pane_app.prompt = lambda *_args, **_kwargs: "renamed"  # type: ignore[method-assign]
        try:
            pane_app.rename_one(object(), rename_entry)  # type: ignore[arg-type]
        finally:
            pane_app.prompt = original_prompt  # type: ignore[method-assign]
        assert same_existing_path(pane_app.panes[1].cwd, pane_root / "renamed" / "child")
        delete_target = pane_root / "renamed"
        pane_app.fallback_panes_after_delete([delete_target])
        assert same_existing_path(pane_app.panes[1].cwd, pane_root)
        assert pane_app.panes[1].zip_path is None
        missing = pane_root / "missing" / "nested"
        assert same_existing_path(stat_path(str(missing), left_dir), pane_root)
    with tempfile.TemporaryDirectory() as os_open_temp:
        os_open_root = Path(os_open_temp)
        os_open_file = os_open_root / "open.txt"
        os_open_file.write_text("open", encoding="utf-8")
        os_open_app = FilerApp(os_open_root, restore_stat=False)
        os_open_app.refresh()
        os_open_app.cursor = next(index for index, entry in enumerate(os_open_app.entries) if entry.name == "open.txt")
        opened_paths: list[Path] = []
        original_open_path_os = os_open_app.open_path_os
        os_open_app.open_path_os = lambda path: opened_paths.append(path)  # type: ignore[method-assign]
        try:
            os_open_app.handle_key(object(), KEY_CTRL_ENTER)  # type: ignore[arg-type]
        finally:
            os_open_app.open_path_os = original_open_path_os  # type: ignore[method-assign]
        assert len(opened_paths) == 1 and same_existing_path(opened_paths[0], os_open_file)
        os_open_app.entries = [Entry(os_open_file, "inside.txt", False, 4, os_open_root / "archive.zip", "inside.txt")]
        os_open_app.pane.entries = os_open_app.entries
        os_open_app.cursor = 0
        os_open_app.open_selected_os()
        assert os_open_app.status == "archive内ファイルのos openは未対応です"
    mark_app = FilerApp(Path("."), restore_stat=False)
    mark_app.entries = [Entry(Path("a.txt"), "a.txt", False, 1), Entry(Path("b.txt"), "b.txt", False, 1)]
    mark_app.pane.entries = mark_app.entries
    mark_app.mark_all()
    assert mark_app.pane.marks == {"a.txt", "b.txt"}
    mark_app.mark_all()
    assert mark_app.pane.marks == set() and mark_app.status == "marks cleared"
    owner_mark_app = FilerApp(Path("."), restore_stat=False)
    owner_mark_app.entries = [Entry(Path(".."), "..", True, 0, search_text="__ownerpath__"), Entry(Path("a.txt"), "a.txt", False, 1)]
    owner_mark_app.pane.entries = owner_mark_app.entries
    owner_mark_app.mark_all()
    assert owner_mark_app.pane.marks == {"a.txt"}
    owner_mark_app.clear_marks()
    owner_mark_app.cursor = 0
    assert owner_mark_app.selected_entries() == []
    log_app = FilerApp(Path("."), restore_stat=False)
    log_app.append_command_log("cwd: /tmp\n$ false\nbad\nexit code: 1\n")
    assert log_app.log_lines[-4:] == ["cwd: /tmp", "$ false", "bad", "exit code: 1"]
    log_app.fail_status("delete failed: sample")
    assert log_app.status == "delete failed: sample" and log_app.log_lines[-1] == "delete failed: sample"
    old_run_history = EDITOR_STATE.run_history
    EDITOR_STATE.run_history = ["echo one", "echo two"]
    log_app.log_history_index = len(EDITOR_STATE.run_history)
    log_app.recall_log_history(True)
    assert "".join(log_app.log_input) == "echo two"
    log_app.recall_log_history(True)
    assert "".join(log_app.log_input) == "echo one"
    log_app.recall_log_history(False)
    assert "".join(log_app.log_input) == "echo two"
    EDITOR_STATE.run_history = old_run_history
    assert log_app.handle_log_key(None, "j") is True
    assert log_app.handle_log_key(None, "k") is True
    assert "".join(log_app.log_input).endswith("jk")
    log_app.log_focus = False
    assert log_app.log_prompt_visible()
    log_app.log_input = []
    log_app.log_input_cursor = 0
    assert not log_app.log_prompt_visible()
    log_app.log_tail = TailState(Path("tail.log"), 0, "", True)
    log_app.log_focus = True
    assert log_app.log_prompt_visible()
    assert log_app.log_prompt_prefix().startswith("[Tail] ")
    log_app.log_focus = False
    assert not log_app.log_prompt_visible()
    log_app.log_focus = True
    log_app.log_busy = True
    assert not log_app.log_prompt_visible()
    log_app.log_busy = False
    assert log_app.handle_log_key(None, KEY_ESCAPE) is True
    assert log_app.log_tail is None and log_app.status == "tail stopped"
    old_hide_empty = EDITOR_STATE.hide_empty_directories
    EDITOR_STATE.hide_empty_directories = True
    try:
        bar_text = log_app.status_bar_text(" 22 file(s) ", 38)
        assert ansi_width(bar_text) == 38
        assert "[EmpDir Hide] " in bar_text
    finally:
        EDITOR_STATE.hide_empty_directories = old_hide_empty
    shell_state = EditorShellState(Path.cwd())
    handled, shell_msg = handle_editor_shell_key(None, shell_state, "j", 5)
    assert handled and shell_msg == "" and shell_state.input == ["j"]
    handled, shell_msg = handle_editor_shell_key(None, shell_state, KEY_KP_LEFT, 5)
    assert handled and shell_msg == "" and shell_state.cursor == 0
    assert editor_at_bottom(8, 3, 10)
    assert not editor_at_bottom(6, 3, 10)
    with tempfile.TemporaryDirectory() as tail_temp:
        tail_path = Path(tail_temp) / "tail.log"
        tail_path.write_text("1\n2\n3\n", encoding="utf-8")
        tail_lines, tail_offset = tail_initial_lines(tail_path, 2)
        assert tail_offset == tail_path.stat().st_size
        assert len(tail_lines) == 2
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\|", tail_lines[0])
        assert tail_lines[1].startswith(" " * TAIL_STAMP_WIDTH + "|")
        assert [row.split("|", 1)[1] for row in tail_lines] == ["2", "3"]
        tail_state = TailState(tail_path, tail_offset, "", True, tail_last_stamp_from_rows(tail_lines))
        with tail_path.open("a", encoding="utf-8") as handle:
            handle.write("4\n5")
        tail_rows = read_tail_lines(tail_state)
        assert len(tail_rows) == 1 and tail_rows[0].endswith("|4") and tail_rows[0].startswith(" " * TAIL_STAMP_WIDTH + "|")
        with tail_path.open("a", encoding="utf-8") as handle:
            handle.write("\n")
        tail_rows = read_tail_lines(tail_state)
        assert len(tail_rows) == 1 and tail_rows[0].endswith("|5") and tail_rows[0].startswith(" " * TAIL_STAMP_WIDTH + "|")
        sample_rows, sample_stamp = format_tail_rows(["a", "b"], "2026-09-17 23:18:12")
        assert sample_rows == ["2026-09-17 23:18:12|a", "                   |b"]
        next_rows, _ = format_tail_rows(["c"], "2026-09-17 23:18:13", sample_stamp)
        assert next_rows == ["2026-09-17 23:18:13|c"]
    archive_app = FilerApp(Path("/tmp/out"), restore_stat=False)
    archive_default = archive_app.default_datetime_archive_path(Entry(Path("/tmp/out/foo.txt"), "foo.txt", False, 0))
    assert archive_default.parent == archive_app.cwd
    assert archive_default.name.startswith("foo-") and archive_default.suffix == ".zip"
    dual_archive_app = FilerApp(Path("/tmp/left"), restore_stat=False)
    dual_archive_app.mode = "dual"
    dual_archive_app.active_pane = 0
    dual_archive_app.panes[1].cwd = Path("/tmp/right")
    dual_archive_default = dual_archive_app.default_datetime_archive_path(Entry(Path("/tmp/left/foo.txt"), "foo.txt", False, 0))
    assert dual_archive_default.parent == Path("/tmp/right")
    assert dual_archive_default.name.startswith("foo-") and dual_archive_default.suffix == ".zip"
    with tempfile.TemporaryDirectory() as temp_name:
        base = Path(temp_name)
        real_dir = base / "real"
        real_dir.mkdir()
        (real_dir / "same.txt").write_text("same", encoding="utf-8")
        (real_dir / "real-only.txt").write_text("real", encoding="utf-8")
        (real_dir / "changed.txt").write_text("real", encoding="utf-8")
        zip_path = base / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("same.txt", "same")
            archive.writestr("zip-only.txt", "zip")
            archive.writestr("changed.txt", "zip")
        compare_names = {entry.name: entry.search_text for entry in list_compare_entries(real_dir, zip_path, None, "", zip_path, "")}
        assert compare_names["changed.txt"] == "M size"
        assert compare_names["real-only.txt"] == "L"
        assert compare_names["zip-only.txt"] == "R"
        assert compare_names.get("same.txt", "M time") == "M time"
        compare_entries = {entry.name: entry for entry in list_compare_entries(real_dir, zip_path, None, "", zip_path, "")}
        assert "exists only in left pane." in "".join(compare_preview_rows(compare_entries["real-only.txt"], 120))
        assert "exists only in right pane." in "".join(compare_preview_rows(compare_entries["zip-only.txt"], 120))
        changed_preview = "".join(compare_preview_rows(compare_entries["changed.txt"], 60))
        assert "\x1b[37;41m" in changed_preview and "\x1b[30;42m" in changed_preview
        dup_root = base / "dups"
        (dup_root / "a").mkdir(parents=True)
        (dup_root / "b").mkdir()
        (dup_root / "a" / "one.txt").write_text("same", encoding="utf-8")
        (dup_root / "b" / "two.txt").write_text("same", encoding="utf-8")
        (dup_root / "unique.txt").write_text("same size?", encoding="utf-8")
        duplex_rows = list_duplex_entries(dup_root)
        assert [entry.name for entry in duplex_rows] == ["/b/two.txt"]
        thuru_search = FilerApp(dup_root, restore_stat=False)
        thuru_search.config.thurupaths = [dup_root]
        thuru_search.refresh()
        assert not any(entry.name in ("a", "b", "unique.txt") for entry in thuru_search.entries)
        thuru_search.pane.search_mode = True
        thuru_search.pane.search_kind = "name"
        thuru_search.pane.search_pattern = r"one\.txt"
        thuru_search.refresh()
        assert thuru_search.entries == []
        thuru_search.pane.thuru_list_path = dup_root
        thuru_search.pane.search_mode = False
        thuru_search.pane.search_pattern = ""
        thuru_search.refresh()
        assert {entry.name for entry in thuru_search.entries} >= {"a", "b", "unique.txt"}
        thuru_search.pane.search_mode = True
        thuru_search.pane.search_kind = "name"
        thuru_search.pane.search_pattern = r"one\.txt"
        thuru_search.refresh()
        assert [entry.name for entry in thuru_search.entries] == ["/a/one.txt"]
        thuru_search.pane.search_kind = "content"
        thuru_search.pane.search_pattern = r"same"
        thuru_search.refresh()
        assert any(entry.name == "/a/one.txt" for entry in thuru_search.entries)
        thuru_search.cwd = dup_root / "a"
        thuru_search.pane.search_mode = False
        thuru_search.pane.search_pattern = ""
        thuru_search.refresh()
        assert any(entry.name == "one.txt" for entry in thuru_search.entries)
        thuru_search.cwd = dup_root
        thuru_search.refresh()
        thuru_search.cursor = next(index for index, entry in enumerate(thuru_search.entries) if entry.name == "a")
        thuru_search.open_selected(None)
        assert same_existing_path(thuru_search.cwd, dup_root / "a")
        assert thuru_search.pane.thuru_list_path is not None and same_existing_path(thuru_search.pane.thuru_list_path, dup_root)
        thuru_search.go_parent()
        assert same_existing_path(thuru_search.cwd, dup_root)
        assert thuru_search.pane.thuru_list_path is not None and same_existing_path(thuru_search.pane.thuru_list_path, dup_root)
        assert {entry.name for entry in thuru_search.entries} >= {"a", "b", "unique.txt"}
        thuru_back_cancel = FilerApp(dup_root / "a", restore_stat=False)
        thuru_back_cancel.config.thurupaths = [dup_root]
        thuru_back_cancel.pane.thuru_list_path = dup_root
        cancel_messages: list[str] = []
        original_cancel_confirm = thuru_back_cancel.confirm_key
        thuru_back_cancel.confirm_key = lambda _term, message: cancel_messages.append(message) and False  # type: ignore[method-assign]
        try:
            thuru_back_cancel.go_parent(object())  # type: ignore[arg-type]
        finally:
            thuru_back_cancel.confirm_key = original_cancel_confirm  # type: ignore[method-assign]
        assert cancel_messages == ["get list? (N/y)"]
        assert same_existing_path(thuru_back_cancel.cwd, dup_root)
        assert [entry.name for entry in thuru_back_cancel.entries] == [".."]
        thuru_reload = FilerApp(dup_root, restore_stat=False)
        thuru_reload.config.thurupaths = [dup_root]
        reload_messages: list[str] = []
        original_reload_confirm = thuru_reload.confirm_key
        thuru_reload.confirm_key = lambda _term, message: reload_messages.append(message) and False  # type: ignore[method-assign]
        try:
            thuru_reload.reload_current(object())  # type: ignore[arg-type]
        finally:
            thuru_reload.confirm_key = original_reload_confirm  # type: ignore[method-assign]
        assert reload_messages == ["get list? (N/y)"] and thuru_reload.status == "reload canceled"
        thuru_search.config.thurupaths = [dup_root, dup_root / "a"]
        thuru_search.refresh()
        thuru_search.cursor = next(index for index, entry in enumerate(thuru_search.entries) if entry.name == "a")
        thuru_search.mode = "preview"
        thuru_preview_rows = thuru_search.preview_source_rows(80, 10)
        assert thuru_preview_rows == ["[directory preview]", "y:get list"]
        thuru_search.allow_thuru_preview()
        thuru_preview_rows = thuru_search.preview_source_rows(80, 10)
        assert "    one.txt" in thuru_preview_rows
        thuru_search.move_cursor(1)
        assert thuru_search.pane.thuru_preview_path is not None
        thuru_search.handle_key(object(), KEY_UP)  # type: ignore[arg-type]
        assert thuru_search.pane.thuru_preview_path is None
        thuru_search.cursor = next(index for index, entry in enumerate(thuru_search.entries) if entry.name == "a")
        original_confirm_popup_key = globals()["confirm_popup_key"]
        globals()["confirm_popup_key"] = lambda *_args, **_kwargs: KEY_DOWN
        try:
            assert not thuru_search.confirm_thuru_list(object())  # type: ignore[arg-type]
            assert thuru_search.entries[thuru_search.cursor].name == "b"
        finally:
            globals()["confirm_popup_key"] = original_confirm_popup_key
        thuru_search.cursor = next(index for index, entry in enumerate(thuru_search.entries) if entry.name == "a")
        confirm_messages: list[str] = []
        original_confirm_key = thuru_search.confirm_key
        thuru_search.confirm_key = lambda _term, message: confirm_messages.append(message) or True  # type: ignore[method-assign]
        try:
            thuru_search.open_selected(None)
        finally:
            thuru_search.confirm_key = original_confirm_key  # type: ignore[method-assign]
        assert confirm_messages == ["get list? (N/y)"]
        assert same_existing_path(thuru_search.cwd, dup_root / "a")
        assert thuru_search.pane.thuru_list_path is not None and same_existing_path(thuru_search.pane.thuru_list_path, dup_root)
        many_root = base / "many"
        many_root.mkdir()
        for index in range(5205):
            (many_root / f"many_{index:04d}.txt").touch()
        many_rows = list_filename_search_entries(many_root, r"many_.*\.txt")
        assert len(many_rows) == 5205
        assert many_rows[0].name == "/many_0000.txt"
        assert many_rows[-1].name == "/many_5204.txt"
        zip_temp = zip_view_temp_path(zip_path, "dir/sample.py")
        assert zip_temp.parent.name == "vfiler_zip_view"
        assert zip_temp.name.endswith("_sample.py")
        assert zip_temp == zip_view_temp_path(zip_path, "dir/sample.py")
        info_dir = base / "info"
        info_dir.mkdir()
        (info_dir / "a.bin").write_bytes(b"abc")
        (info_dir / "b.bin").write_bytes(b"de")
        info_rows = entry_information_rows([Entry(info_dir, "info", True, 0, mtime=info_dir.stat().st_mtime)])
        assert any("5B" in row and "info" in row for row in info_rows)
        small = base / "small.txt"
        large = base / "large.txt"
        small.write_bytes(b"1")
        large.write_bytes(b"123")
        sorted_info = entry_information_rows([Entry(small, "small.txt", False, 0), Entry(large, "large.txt", False, 0)], "size", True)
        assert "large.txt" in sorted_info[2] and "small.txt" in sorted_info[3]
        assert information_sort_title("created", False) == "Created ASC"
        with zipfile.ZipFile(zip_path, "a") as archive:
            archive.writestr("dir/a.txt", "1234")
            archive.writestr("dir/b.txt", "56")
        zip_info_rows = entry_information_rows([Entry(zip_path, "dir", True, 0, zip_path, "dir/", 0)])
        assert any("6B" in row and "dir" in row for row in zip_info_rows)
        raw_utf8_name = "日本語".encode("utf-8").decode("cp437")
        bad_name_zip = base / "bad-name.zip"
        with zipfile.ZipFile(bad_name_zip, "w") as archive:
            archive.writestr(f"root//{raw_utf8_name}/a.txt", "ok")
        assert decode_zip_member_name(raw_utf8_name) == "日本語"
        bad_name_rows = list_zip_entries(bad_name_zip, "root/", "")
        assert [(entry.name, entry.is_dir) for entry in bad_name_rows] == [("日本語", True)]
        bad_name_leaf = list_zip_entries(bad_name_zip, "root/日本語/", "")
        assert [(entry.name, entry.zip_name) for entry in bad_name_leaf] == [("a.txt", f"root//{raw_utf8_name}/a.txt")]
        bad_name_map = zip_recursive_map(bad_name_zip, "")
        assert "root/日本語/a.txt" in bad_name_map
        tar_path = base / "test.tar"
        tar_src = base / "tar-src"
        (tar_src / "dir").mkdir(parents=True)
        (tar_src / "dir" / "a.txt").write_text("tar text", encoding="utf-8")
        (tar_src / "top.txt").write_text("top", encoding="utf-8")
        with tarfile.open(tar_path, "w") as archive:
            archive.add(tar_src / "dir" / "a.txt", "dir/a.txt")
            archive.add(tar_src / "top.txt", "top.txt")
        tar_rows = list_zip_entries(tar_path, "", "")
        assert [(entry.name, entry.is_dir) for entry in tar_rows] == [("dir", True), ("top.txt", False)]
        tar_leaf = list_zip_entries(tar_path, "dir/", "")
        assert [(entry.name, entry.zip_name) for entry in tar_leaf] == [("a.txt", "dir/a.txt")]
        assert zip_preview_lines(tar_path, "dir/a.txt", False, 80, False) == ["tar text"]
        tar_copy_dir = base / "tar-copy"
        copy_zip_entry(tar_rows[0], tar_copy_dir, True)
        assert (tar_copy_dir / "dir" / "a.txt").read_text(encoding="utf-8") == "tar text"
        assert any("8B" in row and "dir" in row for row in entry_information_rows([tar_rows[0]]))
        tar_gz_path = base / "test.tar.gz"
        with tarfile.open(tar_gz_path, "w:gz") as archive:
            archive.add(tar_src / "top.txt", "top.txt")
        assert is_zip_archive_path(tar_gz_path)
        assert zip_listing_preview_rows(tar_gz_path) == ["     3B top.txt"]
    assert wheel_scroll_position(0, 0, 100, 20, 3) == (3, 0)
    assert wheel_scroll_position(10, 0, 100, 20, -3) == (7, 0)
    assert wheel_scroll_position(19, 0, 100, 20, 3) == (22, 3)
    assert wheel_scroll_position(95, 80, 100, 20, 3) == (98, 80)
    assert clamp_scroll_position(9, 80, 10, 20) == (9, 0)
    assert clamp_scroll_position(9, 80, 10, 6) == (9, 4)
    assert clamp_scroll_position(20, 0, 10, 6) == (9, 4)
    assert clamp_scroll_position(0, 5, 0, 6) == (0, 0)
    vi_lines = ["abc def", "", "ghi jkl"]
    assert vi_motion(vi_lines, 0, 0, "w", 1, 10) == (0, 4)
    assert vi_motion(vi_lines, 2, 4, "b", 1, 10) == (2, 0)
    assert vi_motion(vi_lines, 2, 0, "b", 1, 10) == (0, 4)
    assert vi_motion(vi_lines, 0, 0, "e", 1, 10) == (0, 2)
    vi_mixed = ["abc日本語、def ++カナかな漢字"]
    assert vi_motion(vi_mixed, 0, 0, "w", 1, 10) == (0, 3)
    assert vi_motion(vi_mixed, 0, 3, "w", 1, 10) == (0, 6)
    assert vi_motion(vi_mixed, 0, 6, "w", 1, 10) == (0, 7)
    assert vi_motion(vi_mixed, 0, 7, "w", 1, 10) == (0, 11)
    assert vi_motion(vi_mixed, 0, 11, "w", 1, 10) == (0, 13)
    assert vi_motion(vi_mixed, 0, 13, "w", 1, 10) == (0, 15)
    assert vi_motion(vi_mixed, 0, 15, "w", 1, 10) == (0, 17)
    assert vi_motion(vi_mixed, 0, 17, "b", 1, 10) == (0, 15)
    assert vi_motion(vi_mixed, 0, 6, "b", 1, 10) == (0, 3)
    assert vi_motion(vi_mixed, 0, 3, "b", 1, 10) == (0, 0)
    assert vi_motion(vi_mixed, 0, 3, "e", 1, 10) == (0, 5)
    assert vi_motion(vi_lines, 0, 0, KEY_PGDN, 1, 2) == (2, 0)
    assert vi_motion(vi_lines, 2, 0, KEY_PGUP, 1, 2) == (0, 0)
    sel_y, sel_x, sel_mark, sel_mode, sel_rect, sel_msg = editor_select_all(["abc", "de"])
    assert (sel_y, sel_x, sel_mark, sel_mode, sel_rect, sel_msg) == (1, 2, (0, 0), True, False, "selected all")
    assert editor_selected_text(["abc", "de"], sel_mark, (sel_y, sel_x)) == "abc\nde"
    assert vi_yank_lines(vi_lines, 0, 2) == "abc def\n\n"
    deleted_lines, deleted_y, deleted_x, deleted_text = vi_delete_lines(vi_lines[:], 0, 2)
    assert deleted_lines == ["ghi jkl"] and (deleted_y, deleted_x) == (0, 0) and deleted_text == "abc def\n\n"
    pasted_lines, pasted_y, pasted_x = vi_paste_after(["top", "bottom"], 0, 0, "a\n\n")
    assert pasted_lines == ["top", "a", "", "bottom"] and (pasted_y, pasted_x) == (1, 0)
    joined_lines, joined_y, joined_x = vi_join_lines(["one ", " two", "three"], 0, 1)
    assert joined_lines == ["one  two", "three"] and (joined_y, joined_x) == (0, 4)
    assert vi_substitute_line("foo foo", ":s/foo/bar/") == ("bar foo", 1)
    assert vi_substitute_line("foo foo", ":s/foo/bar/g") == ("bar bar", 2)
    assert vi_command_bare(":q!") == "q!"
    assert vi_command_bare(" wq ") == "wq"
    old_vi_mode = EDITOR_STATE.vi_mode
    EDITOR_STATE.vi_mode = False
    assert editor_vi_command_rows() == 0
    EDITOR_STATE.vi_mode = True
    assert editor_vi_command_rows() == 1
    EDITOR_STATE.vi_mode = old_vi_mode
    insert_undo: list[tuple[list[str], int, int]] = []
    insert_redo: list[tuple[list[str], int, int]] = []
    insert_lines = ["abc"]
    push_undo(insert_undo, insert_lines, 0, 3)
    insert_lines[0] = editor_put_text(insert_lines[0], 3, "XYZ", True)
    insert_lines[0] = editor_put_text(insert_lines[0], 6, "123", True)
    insert_lines, insert_y, insert_x, insert_undo, insert_redo, insert_msg = editor_undo_redo("undo", insert_lines, 0, 9, insert_undo, insert_redo)
    assert insert_lines == ["abc"] and (insert_y, insert_x, insert_msg) == (0, 3, "undo")
    assert parse_mouse_sequence(b"[<0;12;5M") == "MOUSE:0:12:5:1"
    assert parse_mouse_sequence(b"[<64;1;2M") == KEY_WHEEL_UP
    assert parse_mouse_sequence(b"[<65;1;2M") == KEY_WHEEL_DOWN
    assert fmt_size(0, True) == "<DIR>"
    assert fmt_size(1024, False) == "1.0K"
    natural_entries = [Entry(Path(name), name, False, 0) for name in ["1", "10", "11", "12", "2", "3"]]
    sort_entries(natural_entries, "natural", False)
    assert [entry.name for entry in natural_entries] == ["1", "2", "3", "10", "11", "12"]
    sort_entries(natural_entries, "natural", True)
    assert [entry.name for entry in natural_entries] == ["12", "11", "10", "3", "2", "1"]
    prefixed_entries = [Entry(Path(name), name, False, 0) for name in ["file1.txt", "file10.txt", "file2.txt", "file02.txt", "fileA.txt"]]
    sort_entries(prefixed_entries, "natural", False)
    assert [entry.name for entry in prefixed_entries] == ["file1.txt", "file2.txt", "file02.txt", "file10.txt", "fileA.txt"]
    assert parse_exec_items([{"ext": "py", "command": "python %f"}])["py"].command == "python %f"
    syntax = load_syntax({"foo": {"keywords": ["hello"], "keyword_color": "red"}})
    assert syntax["foo"]["keywords"] == ["hello"]
    assert "\x1b[36m" in editor_row("def f():", 0, None, (0, 0), 0, 20, False, syntax["py"])
    assert "\x1b[31m" in editor_row("hello", 0, None, (0, 0), 0, 20, False, syntax["foo"])
    syntax = load_syntax({"md": {"regex": [{"pattern": r"^# .*$", "color": "bright_red"}, {"pattern": "[", "color": "cyan"}], "comment_color": "green"}})
    assert syntax["md"]["regex"] == [{"pattern": r"^# .*$", "color": "bright_red"}]
    assert syntax_spans("# title", syntax["md"]) == [(0, 7, "bright_red")]
    assert "\x1b[91m" in preview_text_line("# title", 0, False, syntax["md"])
    assert editor_row("a" * 10000, 0, None, (0, 0), 0, 20, False, syntax["md"]) == "a" * 20
    assert display_safe_text("a\tb\x1b[31m") == "a    b\\x1b[31m"
    unsafe_diff_rows = side_diff_rows(["a\tb"], ["a\x1b[31mb"])
    assert "\t" not in "".join(unsafe_diff_rows)
    assert "\\x1b[31m" in "".join(unsafe_diff_rows)
    parsed_diff = parse_git_unified_diff(["diff --git a/a b/a", "--- a/a", "+++ b/a", "@@ -10,2 +10,3 @@ func", " old", "-bad\tline", "+good\x1b[31m", "+next"])
    assert parsed_diff == ["@@ -10 +10 @@ func", "     10: old", "-    11: bad    line", "+    11: good\\x1b[31m", "+    12: next"]
    assert diff_row_indices(parsed_diff) == [2]
    full_diff = full_diff_rows_from_unified(["old", "good", "next"], ["diff --git a/a b/a", "--- a/a", "+++ b/a", "@@ -1,2 +1,3 @@", " old", "-bad\tline", "+good", "+next"])
    assert full_diff == ["      1: old", "-     2: bad    line", "+     2: good", "+     3: next"]
    wrapped_guard = color_diff_row("- " + ("x" * 20), 10, "37;41")
    assert ansi_width(wrapped_guard) == 10 and wrapped_guard.endswith(" ")
    wrap_lines = ["short", "x" * 80, "tail"]
    assert editor_ensure_wrap_visible(wrap_lines, 0, 2, 0, 20, 3) == 2
    readonly_source = EditorBuffer(Path("same.txt"), ["1", "2"], True, cy=4, top=3, edit_mode=False)
    readonly_clone = clone_editor_buffer(readonly_source)
    readonly_source.cy = 9
    readonly_source.top = 8
    readonly_source.lines = ["changed"]
    sync_same_path_buffers([readonly_source, readonly_clone], 0)
    assert (readonly_clone.cy, readonly_clone.top, readonly_clone.lines) == (4, 3, ["1", "2"])
    edit_source = EditorBuffer(Path("same.txt"), ["a"], False, cy=5, top=4, edit_mode=True)
    edit_clone = clone_editor_buffer(edit_source)
    edit_source.lines = ["b"]
    edit_source.cy = 7
    edit_source.top = 6
    sync_same_path_buffers([edit_source, edit_clone], 0)
    assert edit_clone.lines == ["b"] and (edit_clone.cy, edit_clone.top) == (5, 4)
    old_show_enter = EDITOR_STATE.show_enter
    old_show_tab = EDITOR_STATE.show_tab
    old_show_bin = EDITOR_STATE.show_bin
    EDITOR_STATE.show_enter = True
    EDITOR_STATE.show_tab = True
    EDITOR_STATE.show_bin = True
    editor_colors = load_colors({})
    assert "\x1b[33m↓\x1b[0m" in editor_row("abc", 0, None, (0, 0), 0, 20, False, None, "LF", editor_colors)
    assert "\x1b[31m↓\x1b[0m" in editor_row("abc", 0, None, (0, 0), 0, 20, False, None, "CR", editor_colors)
    assert "\x1b[36m↓\x1b[0m" in editor_row("abc", 0, None, (0, 0), 0, 20, False, None, "CRLF", editor_colors)
    assert "\x1b[36m→\x1b[0m" in editor_row("a\tb", 0, None, (0, 0), 0, 20, False, None, "NONE", editor_colors)
    bin_row = editor_row("a\x01b", 0, None, (0, 0), 0, 20, False, None, "NONE", editor_colors)
    assert "0x01" in bin_row and "\x1b[7" in bin_row
    old_show_bin_state = EDITOR_STATE.show_bin
    EDITOR_STATE.show_bin = False
    forced_bin_row = editor_row("a\x00b", 0, None, (0, 0), 0, 20, False, None, "NONE", editor_colors, True)
    assert "0x00" in forced_bin_row and "\x1b[7" in forced_bin_row and editor_text_width("a\x00b", True) == 6
    EDITOR_STATE.show_bin = old_show_bin_state
    assert editor_data_looks_binary(b"a\x00b")
    assert editor_data_looks_binary((b"a" * 5000) + b"\x00" + (b"b" * 5000))
    EDITOR_STATE.show_enter = old_show_enter
    EDITOR_STATE.show_tab = old_show_tab
    EDITOR_STATE.show_bin = old_show_bin
    assert "\x1b[36m" in preview_text_line("def f():", 0, False, syntax["py"])
    old_tab = EDITOR_STATE.tab_spaces
    EDITOR_STATE.tab_spaces = 2
    rows, cy, cx, mark, _ = editor_indent_lines(["a", " b"], 0, 1, None, True)
    assert rows == ["  a", " b"] and (cy, cx, mark) == (0, 3, None)
    rows, cy, cx, mark, _ = editor_indent_lines(["  a", "  b"], 1, 1, (0, 0), False)
    assert rows == ["a", "b"] and (cy, cx, mark) == (1, 0, (0, 0))
    EDITOR_STATE.tab_spaces = old_tab
    assert calc_text("1+2*3") == "7"
    assert calc_text("0xa0+012=%x") == "aa"
    assert calc_text("0o12+0O12") == "20"
    assert calc_text("1/3=%0.3f") == "0.333"
    assert calc_text("123*") == "ERR"
    assert calc_text("123=%q") == "ERR"
    assert normalize_move_key(KEY_KP_LEFT) == KEY_LEFT
    assert normalize_move_key(KEY_KP_UP) == KEY_UP
    assert normalize_move_key(KEY_KP_RIGHT) == KEY_RIGHT
    assert normalize_move_key(KEY_KP_DOWN) == KEY_DOWN
    assert normalize_move_key("4") == "4"
    assert calc_visible_text("1234567890", 6) == "123..."
    cell = calc_result_cell("249.476", 10)
    assert ansi_width(cell) == 10 and cell.endswith("249.476\x1b[0m")
    calc_width = 36
    calc_result_width = min(18, max(10, calc_width // 3))
    calc_input_width = calc_width - calc_result_width - 2
    assert ansi_width(yellow("█") + fit("123", calc_input_width) + calc_result_cell("123", calc_result_width) + yellow("█")) == calc_width
    assert "%f" not in expand_command("vi %f", Path("a b.txt"), Path("."), Path(".."))
    assert "%p" not in expand_command("echo %p %ps", None, Path("."), Path(".."))
    assert expand_command("echo", Path("a.txt"), Path("."), Path("..")) == "echo"
    sample_entries = [Entry(Path("/tmp/out/a 1.txt"), "a 1.txt", False, 0, 0), Entry(Path("/tmp/out/sub/b.txt"), "b.txt", False, 0, 0)]
    expanded = expand_command('zip "%p/%b-${DATE}-${TIME}.zip" %*', Path("src.tar.gz"), Path("/tmp/out"), Path(".."), sample_entries)
    assert expanded == 'zip "/tmp/out/src.tar-${DATE}-${TIME}.zip" \'/tmp/out/a 1.txt\' /tmp/out/sub/b.txt'
    expanded = expand_command('zip "%p/%b-${DATE}-${TIME}.zip" %**', Path("/tmp/out/src.tar.gz"), Path("/tmp/out"), Path(".."), sample_entries)
    assert expanded == 'zip "/tmp/out/src.tar-${DATE}-${TIME}.zip" \'a 1.txt\' sub/b.txt'
    assert safe_zip_target(Path("/tmp/vfiler"), "../bad.txt") is None
    colors = load_colors({"dir_color": "34", "dot_file_color": "31"})
    assert "\x1b[34m" in entry_color(Entry(Path(".git"), ".git", True, 0), ".git", colors)
    assert "\x1b[31m" in entry_color(Entry(Path(".env"), ".env", False, 0), ".env", colors)
    assert "\x1b[7;34m" in entry_cursor_color(Entry(Path(".git"), ".git", True, 0), ".git", colors)
    assert "\x1b[7;31m" in entry_cursor_color(Entry(Path(".env"), ".env", False, 0), ".env", colors)
    entries = list_entries(Path.cwd(), "")
    assert isinstance(entries, list)
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "empty").mkdir()
        (root / "empty-tree").mkdir()
        (root / "empty-tree" / "nested").mkdir()
        (root / "with-file").mkdir()
        (root / "with-file" / "item.txt").write_text("x", encoding="utf-8")
        assert [entry.name for entry in list_entries(root, "", True)] == ["with-file"]
    print("self-test ok")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standard-library terminal file manager")
    parser.add_argument("path", nargs="?", default=None, help="start directory or edit file")
    parser.add_argument("--1", dest="one", metavar="PATH", help="start in preview mode")
    parser.add_argument("--2", dest="two", nargs=2, metavar=("LEFT", "RIGHT"), help="start in dual pane mode")
    parser.add_argument("--e", dest="edit_file", metavar="FILE", help="open internal editor")
    parser.add_argument("--v", dest="view_file", metavar="FILE", help="open internal viewer")
    parser.add_argument("--nostat", action="store_true", help="disable vfiler_stat.json load/save")
    parser.add_argument("--no-resident", action="store_true", help="disable resident forwarding")
    parser.add_argument("--self-test", action="store_true", help="run non-interactive checks")
    parser.add_argument("--shell-popup", nargs="?", const="file", metavar="LABEL", help="experimental readline popup input")
    parser.add_argument("--shell-popup-default", default="", metavar="TEXT", help="default text for --shell-popup")
    parser.add_argument("-z", "--resident", action="store_true", help="start resident shell integration")
    parser.add_argument("--z-client", nargs="?", const="", metavar="SOCKET", help=argparse.SUPPRESS)
    parser.add_argument("--z-server", nargs="?", const="", metavar="TTY", help=argparse.SUPPRESS)
    return parser.parse_args(list(argv))


def start_dir(path_text: str) -> Path | None:
    path = Path(path_text).expanduser()
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr)
        return None
    return path if path.is_dir() else path.parent


def stat_path(value: object, fallback: Path) -> Path:
    if isinstance(value, str) and value:
        path = Path(value).expanduser()
        if path.is_dir():
            return path
        parent = nearest_existing_dir(path.parent, fallback)
        if parent.is_dir():
            return parent
    return fallback


def selected_path_text(pane: PaneState) -> str:
    if 0 <= pane.cursor < len(pane.entries):
        return str(pane.entries[pane.cursor].path)
    return ""


def stable_path_text(path: Path) -> str:
    try:
        return str(path.expanduser().resolve())
    except OSError:
        return str(path.expanduser())


def gitignore_template_path(name: str) -> Path:
    return TEMPLATE_DIR / f"{name}.gitignore"


def git_status_title(kind: str) -> str:
    return {"managed": "managed", "unmanaged": "unmanaged"}.get(kind, "status")


class ResidentServer:
    def __init__(self, socket_path: Path, tty_id: str | None = None) -> None:
        self.socket_path = socket_path
        self.tty_id = tty_id
        self.stop_event = threading.Event()
        self.editor: EditorSession | None = None
        self.filer: FilerApp | None = None
        self.restart_requested = False

    def serve(self) -> None:
        try:
            self.socket_path.unlink(missing_ok=True)
        except OSError:
            pass
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.socket_path))
        server.listen(1)
        server.settimeout(0.2)
        try:
            while not self.stop_event.is_set():
                if not resident_terminal_alive(self.tty_id):
                    self.stop_event.set()
                    break
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self.stop_event.is_set():
                        break
                    continue
                with conn:
                    response = {"ok": True}
                    try:
                        data = conn.recv(65536)
                        if not data:
                            continue
                        request = json.loads(data.decode("utf-8"))
                        response.update(self.handle_request(request))
                    except Exception as exc:
                        response = {"ok": False, "error": str(exc)}
                    try:
                        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                    except BrokenPipeError:
                        pass
                    if response.get("restart"):
                        self.restart_requested = True
                        self.stop_event.set()
        finally:
            server.close()
            try:
                self.socket_path.unlink(missing_ok=True)
            except OSError:
                pass
        if self.restart_requested:
            os.execv(sys.executable, [sys.executable, *sys.argv])

    def stop(self) -> None:
        self.stop_event.set()

    def ensure_editor(self, colors: dict[str, str]) -> EditorSession:
        if self.editor is None:
            self.editor = EditorSession(colors, resident_mode=True)
        self.editor.resident_mode = True
        return self.editor

    def ensure_filer(self, cwd: Path) -> FilerApp:
        if self.filer is None:
            self.filer = FilerApp(cwd, mode="preview", restore_stat=True)
        self.filer.config = load_config(cwd)
        self.filer.resident_mode = True
        self.filer.return_editor_requests = True
        return self.filer

    def prepare_filer_for_resident(self, filer: FilerApp, cwd: Path, restore_state: bool) -> None:
        filer.running = True
        filer.restart_requested = False
        filer.shell_return_text = ""
        filer.shell_origin_cwd = cwd
        filer.root_pending = False
        filer.log_focus = False
        if restore_state:
            return
        filer.mode = "preview"
        filer.active_pane = 0
        filer.cwd = cwd
        filer.pane.zip_path = None
        filer.pane.zip_dir = ""
        filer.pane.search_mode = False
        filer.pane.search_pattern = ""
        filer.pane.search_kind = "content"
        filer.pane.git_history_mode = False
        filer.pane.git_history_file = None
        filer.pane.git_status_mode = False
        filer.pane.git_tree_mode = False
        filer.pane.git_commit_files_mode = False
        filer.pane.git_commit_hash = ""
        filer.pane.git_commit_parent = ""
        filer.pane.compare_mode = False
        filer.pane.duplex_mode = False
        filer.pane.duplex_root = None
        filer.pane.thuru_return_path = None
        filer.pane.thuru_preview_path = None
        filer.pane.preview_focus = False
        filer.pane.preview_top = 0
        filer.cursor = 0
        filer.top = 0
        filer.clear_marks()
        filer.push_dir_history()

    def buffer_labels(self) -> list[str]:
        if self.editor is None:
            return []
        labels = []
        for index, buffer in enumerate(self.editor.buffers):
            dirty = "*" if buffer.dirty else " "
            labels.append(f"{index + 1}{dirty} {buffer.path.name}")
        return labels

    def handle_request(self, request: dict[str, object]) -> dict[str, object]:
        action = str(request.get("action") or "open")
        if action == "buffers":
            return {"buffers": self.buffer_labels(), "protocol": RESIDENT_PROTOCOL, "pid": os.getpid()}
        cwd = Path(str(request.get("cwd") or ".")).expanduser().resolve()
        value = str(request.get("value") or "")
        buffer_index = request.get("buffer_index")
        restore_filer_state = bool(request.get("restore_filer_state"))
        return_pgrp = int(request.get("return_pgrp") or 0)
        response: dict[str, object] = {}
        old_cwd = Path.cwd()
        os.chdir(cwd)
        try:
            load_stat()
            config = load_config(cwd)
            editor = self.ensure_editor(config.colors)
            if isinstance(buffer_index, int):
                if 0 <= buffer_index < len(editor.buffers):
                    editor.current = buffer_index
                    with Terminal() as term:
                        editor.reopen(term)
                else:
                    response["ok"] = False
                    response["error"] = "buffer not found"
            elif value:
                path = Path(value).expanduser()
                if not path.is_absolute():
                    path = cwd / path
                with Terminal() as term:
                    editor.open(term, path, False)
            else:
                filer = self.ensure_filer(cwd)
                self.prepare_filer_for_resident(filer, cwd, restore_filer_state)
                App(filer, editor, resident_mode=True).run()
                if filer.shell_return_text:
                    response["append"] = filer.shell_return_text
                if filer.restart_requested:
                    response["restart"] = True
        finally:
            os.chdir(old_cwd)
            if return_pgrp and not IS_WINDOWS:
                set_tty_foreground_pgrp(return_pgrp)
        return response


def resident_tty_id() -> str:
    try:
        tty_name = os.ttyname(sys.stdin.fileno())
    except OSError:
        tty_name = os.environ.get("TTY") or "notty"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", tty_name.strip("/")) or "notty"


def resident_socket_path(tty_id: str | None = None) -> Path:
    return Path(tempfile.gettempdir()) / f"vfiler-z-{os.getuid()}-{tty_id or resident_tty_id()}.sock"


def resident_pid_path(tty_id: str | None = None) -> Path:
    return Path(tempfile.gettempdir()) / f"vfiler-z-{os.getuid()}-{tty_id or resident_tty_id()}.pid"


def resident_tty_path_from_id(tty_id: str | None) -> Path | None:
    if not tty_id or tty_id == "notty":
        return None
    if tty_id.startswith("dev_"):
        return Path("/" + tty_id.replace("_", "/", 1))
    return None


def resident_terminal_alive(tty_id: str | None) -> bool:
    if IS_WINDOWS or not tty_id:
        return True
    tty_path = resident_tty_path_from_id(tty_id)
    if tty_path is not None and not tty_path.exists():
        return False
    try:
        os.tcgetpgrp(sys.stdin.fileno())
    except (OSError, termios.error):
        return False
    return True


def resident_server_alive(socket_path: Path) -> bool:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(0.1)
    try:
        client.connect(str(socket_path))
        return True
    except OSError:
        return False
    finally:
        client.close()


def cleanup_resident_files(tty_id: str | None = None) -> None:
    for path in (resident_socket_path(tty_id), resident_pid_path(tty_id)):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def resident_pid(tty_id: str | None = None) -> int | None:
    try:
        return int(resident_pid_path(tty_id).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def resident_server_pids(tty_id: str | None = None) -> list[int]:
    target = tty_id or resident_tty_id()
    pids: set[int] = set()
    pid = resident_pid(target)
    if pid is not None:
        pids.add(pid)
    try:
        result = subprocess.run(["ps", "-axo", "pid=,args="], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace", check=False)
    except OSError:
        return sorted(pid for pid in pids if pid != os.getpid())
    if result.returncode == 0:
        pids.update(parse_resident_server_pids(result.stdout, target))
    return sorted(pid for pid in pids if pid != os.getpid())


def parse_resident_server_pids(text: str, tty_id: str) -> list[int]:
    pids: list[int] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, args = stripped.partition(" ")
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if "vfiler.py" not in args or "--z-server" not in args:
            continue
        parts = shlex.split(args)
        for index, part in enumerate(parts):
            if part == "--z-server" and index + 1 < len(parts) and parts[index + 1] == tty_id:
                pids.append(pid)
                break
    return pids


def stop_resident_server(tty_id: str | None = None) -> None:
    pids = resident_server_pids(tty_id)
    if not pids:
        cleanup_resident_files(tty_id)
        return
    for sig, deadline in ((signal.SIGTERM, 1.0), (signal.SIGKILL, 0.5)):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                continue
            except OSError:
                continue
        end = time.monotonic() + deadline
        while time.monotonic() < end:
            if all(resident_pid_dead(pid) for pid in pids):
                cleanup_resident_files(tty_id)
                return
            time.sleep(0.05)
    cleanup_resident_files(tty_id)


def resident_pid_dead(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return False
    except ProcessLookupError:
        return True
    except OSError:
        return False


def run_resident_server(tty_id: str | None = None) -> int:
    if IS_WINDOWS:
        print("resident mode is only implemented for POSIX terminals", file=sys.stderr)
        return 2
    tty_id = tty_id or resident_tty_id()
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    signal.signal(signal.SIGTTIN, signal.SIG_IGN)
    pid_path = resident_pid_path(tty_id)
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    try:
        ResidentServer(resident_socket_path(tty_id), tty_id).serve()
    finally:
        try:
            pid_path.unlink(missing_ok=True)
        except OSError:
            pass
    return 0


def run_resident_mode() -> int:
    tty_id = resident_tty_id()
    socket_path = resident_socket_path(tty_id)
    if resident_server_alive(socket_path):
        response = resident_request(socket_path, {"action": "buffers"})
        if response.get("ok") and response.get("protocol") == RESIDENT_PROTOCOL:
            return 0
        stop_resident_server(tty_id)
    elif resident_server_pids(tty_id):
        stop_resident_server(tty_id)
    else:
        cleanup_resident_files(tty_id)
    try:
        tty_in = open("/dev/tty", "rb", buffering=0)
        tty_out = open("/dev/tty", "wb", buffering=0)
        tty_err = open("/dev/tty", "wb", buffering=0)
    except OSError as exc:
        print(f"tty open failed: {exc}", file=sys.stderr)
        return 1
    with tty_in, tty_out, tty_err:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--z-server", tty_id],
            stdin=tty_in,
            stdout=tty_out,
            stderr=tty_err,
            preexec_fn=os.setpgrp,
            close_fds=True,
        )
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if resident_server_alive(socket_path):
            return 0
        time.sleep(0.05)
    print("vfiler resident start timeout", file=sys.stderr)
    return 1


def resident_server_pgrp(tty_id: str | None = None) -> int | None:
    pid = resident_pid(tty_id)
    if pid is None:
        return None
    try:
        return os.getpgid(pid)
    except OSError:
        return None


def set_tty_foreground_pgrp(pgrp: int) -> None:
    if IS_WINDOWS:
        return
    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
    except OSError:
        return
    try:
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        os.tcsetpgrp(tty_fd, pgrp)
    except (OSError, termios.error):
        pass
    finally:
        os.close(tty_fd)


def run_resident_client(socket_text: str | None = None) -> int:
    tty_id = resident_tty_id()
    socket_path = Path(socket_text) if socket_text else resident_socket_path(tty_id)
    if not resident_server_alive(socket_path):
        if socket_text or run_resident_mode() != 0:
            print("vfiler resident is not running", file=sys.stderr)
            return 1
    buffers_response = resident_request(socket_path, {"action": "buffers"})
    if not buffers_response.get("ok"):
        cleanup_resident_files(tty_id)
        if socket_text or run_resident_mode() != 0:
            print(buffers_response.get("error", "resident error"), file=sys.stderr)
            return 1
        buffers_response = resident_request(socket_path, {"action": "buffers"})
    buffers = buffers_response.get("buffers", [])
    buffer_labels = [str(item) for item in buffers] if isinstance(buffers, list) else []
    kind, value = shell_popup_choice("入力ファイル", "", buffer_labels)
    if kind is None:
        return 0
    request: dict[str, object] = {"cwd": os.environ.get("PWD") or str(Path.cwd()), "value": value or "", "return_pgrp": os.getpgrp()}
    if kind == "buffer":
        request["buffer_index"] = int(value or "0")
        request["value"] = ""
    hand_terminal_to_resident(tty_id)
    response = resident_request(socket_path, request)
    if resident_response_needs_restart(response) and not socket_text:
        stop_resident_server(tty_id)
        if run_resident_mode() != 0:
            print(response.get("error", "resident error"), file=sys.stderr)
            return 1
        hand_terminal_to_resident(tty_id)
        response = resident_request(socket_path, request)
    if not response.get("ok"):
        print(response.get("error", "resident error"), file=sys.stderr)
        return 1
    append = str(response.get("append") or "")
    if append:
        print(append)
    return 0


def hand_terminal_to_resident(tty_id: str) -> None:
    server_pgrp = resident_server_pgrp(tty_id)
    if server_pgrp is not None:
        set_tty_foreground_pgrp(server_pgrp)


def forward_to_resident_if_running(args: argparse.Namespace) -> int | None:
    if args.no_resident or args.nostat or args.one or args.two or args.view_file:
        return None
    tty_id = resident_tty_id()
    socket_path = resident_socket_path(tty_id)
    if not resident_server_alive(socket_path):
        return None
    value = ""
    if args.edit_file:
        value = str(args.edit_file)
    elif args.path is not None:
        path = Path(args.path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        value = "" if path.is_dir() else str(args.path)
    request: dict[str, object] = {"cwd": os.environ.get("PWD") or str(Path.cwd()), "value": value, "return_pgrp": os.getpgrp()}
    if args.path is not None and not value:
        request["restore_filer_state"] = True
    hand_terminal_to_resident(tty_id)
    response = resident_request(socket_path, request)
    if resident_response_needs_restart(response):
        stop_resident_server(tty_id)
        if run_resident_mode() != 0:
            print(response.get("error", "resident error"), file=sys.stderr)
            return 1
        hand_terminal_to_resident(tty_id)
        response = resident_request(socket_path, request)
    if not response.get("ok"):
        print(response.get("error", "resident error"), file=sys.stderr)
        return 1
    append = str(response.get("append") or "")
    if append:
        print(append)
    return 0


def resident_request(socket_path: Path, request: dict[str, object]) -> dict[str, object]:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(str(socket_path))
        client.sendall(json.dumps(request).encode("utf-8"))
        data = client.recv(65536)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        client.close()
    return json.loads(data.decode("utf-8")) if data else {"ok": False, "error": "empty response"}


def resident_response_needs_restart(response: dict[str, object]) -> bool:
    if response.get("ok"):
        return False
    error = str(response.get("error") or "")
    return "Input/output error" in error or "[Errno 5]" in error


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    global NO_STAT
    args = parse_args(argv)
    NO_STAT = bool(args.nostat)
    if args.z_server is not None:
        return run_resident_server(args.z_server or None)
    if args.z_client is not None:
        return run_resident_client(args.z_client or None)
    if args.resident:
        return run_resident_mode()
    if args.self_test:
        run_self_test()
        return 0
    if args.shell_popup is not None:
        value = shell_popup_input(args.shell_popup, args.shell_popup_default)
        if value is None:
            return 130
        print(value)
        return 0
    forwarded = forward_to_resident_if_running(args)
    if forwarded is not None:
        return forwarded

    EDITOR_STATE.run_history = load_run_history()
    load_stat()
    try:
        config = load_config(Path.cwd())
        if args.edit_file or args.view_file:
            path = Path(args.edit_file or args.view_file).expanduser()
            with Terminal() as term:
                text_editor(term, path, readonly=bool(args.view_file), colors=config.colors)
            return 0
        if args.two:
            left = start_dir(args.two[0])
            right = start_dir(args.two[1])
            if left is None or right is None:
                return 2
            App(FilerApp(left, other=right, mode="dual")).run()
            return 0
        if args.one:
            start = start_dir(args.one)
            if start is None:
                return 2
            App(FilerApp(start, mode="preview")).run()
            return 0
        restore_stat = args.path is None and not args.nostat
        if args.path is not None:
            path = Path(args.path).expanduser()
            if not path.is_dir():
                with Terminal() as term:
                    text_editor(term, path, readonly=False, colors=config.colors)
                return 0
            start = path
        else:
            start = Path(".")
        App(FilerApp(start, restore_stat=restore_stat)).run()
    except ConfigError as exc:
        print(f"DEF error: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
