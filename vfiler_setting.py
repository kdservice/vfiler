#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import select
import shutil
import sys
import termios
import tty
import unicodedata
from pathlib import Path
from typing import Any


COLOR_NAMES = [
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
    "gray",
    "bright_red",
    "bright_green",
    "bright_yellow",
    "bright_blue",
    "bright_magenta",
    "bright_cyan",
    "bright_white",
    "default",
    "none",
]
REVERSIBLE_COLOR_KEYS = {
    "dir_color",
    "dot_file_color",
    "zip_file_color",
    "file_color",
    "search_match_color",
    "editor_readonly_bar_color",
    "editor_edit_bar_color",
    "editor_lf_color",
    "editor_cr_color",
    "editor_crlf_color",
    "editor_tab_color",
    "editor_bin_color",
    "filer_active_bar_color",
    "log_prompt_color",
    "log_input_text_color",
    "log_input_existing_path_color",
    "log_input_missing_path_color",
    "log_input_unclosed_string_color",
    "keyword_color",
    "comment_color",
    "string_color",
    "number_color",
    "regex_color",
}
REVERSE_COLOR_CHOICES = [
    ("7", "reverse"),
    ("7;30", "reverse black"),
    ("7;31", "reverse red"),
    ("7;32", "reverse green"),
    ("7;33", "reverse yellow"),
    ("7;34", "reverse blue"),
    ("7;35", "reverse magenta"),
    ("7;36", "reverse cyan"),
    ("7;37", "reverse white"),
    ("7;90", "reverse gray"),
    ("7;91", "reverse bright red"),
    ("7;92", "reverse bright green"),
    ("7;93", "reverse bright yellow"),
    ("7;94", "reverse bright blue"),
    ("7;95", "reverse bright magenta"),
    ("7;96", "reverse bright cyan"),
    ("7;97", "reverse bright white"),
]

SETTING_GROUPS = [
    (
        "基本設定",
        [
            ("editor", "string", "エディタコマンド"),
            ("sh", "string", "シェル"),
            ("autosave_runlog", "enable", "実行ログ自動保存"),
            ("autosave_runlog_path", "string", "実行ログ保存先"),
            ("quit_prompt", "bool", "終了確認"),
            ("show_ownerpath", "bool", "親ディレクトリ行表示"),
            ("change_file_datetime", "bool", "日時表示時の列順変更"),
            ("diff_jump_before", "number", "diff ジャンプ前行数"),
            ("painwidth", "number", "プレビュー幅パーセント"),
        ],
    ),
    (
        "色設定",
        [
            ("dir_color", "color", "ディレクトリ色"),
            ("dot_file_color", "color", "ドットファイル色"),
            ("zip_file_color", "color", "zip ファイル色"),
            ("file_color", "color", "通常ファイル色"),
            ("search_match_color", "color", "検索一致色"),
            ("editor_readonly_bar_color", "color", "閲覧バー色"),
            ("editor_edit_bar_color", "color", "編集バー色"),
            ("editor_lf_color", "color", "LF 表示色"),
            ("editor_cr_color", "color", "CR 表示色"),
            ("editor_crlf_color", "color", "CRLF 表示色"),
            ("editor_tab_color", "color", "タブ表示色"),
            ("editor_bin_color", "color", "バイナリ表示色"),
            ("filer_active_bar_color", "color", "アクティブペインバー色"),
            ("log_prompt_color", "color", "シェルプロンプト色"),
            ("log_input_text_color", "color", "シェル入力文字色"),
            ("log_input_existing_path_color", "color", "存在するパス色"),
            ("log_input_missing_path_color", "color", "存在しないパス色"),
            ("log_input_unclosed_string_color", "color", "閉じ忘れ文字列色"),
        ],
    ),
]

SYNTAX_COLOR_KEYS = [
    ("keyword_color", "キーワード色"),
    ("comment_color", "コメント色"),
    ("string_color", "文字列色"),
    ("number_color", "数値色"),
]

BOOL_TRUE = {"true", "enable", "1", "yes", "on"}
BOOL_FALSE = {"false", "disable", "0", "no", "off"}
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


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


def color_text(text: str, color: str) -> str:
    code = color_code(color)
    return f"\x1b[{code}m{text}\x1b[0m" if code else text


def yellow(text: str) -> str:
    return "\x1b[33m" + text + "\x1b[0m"


def yellow_bg(text: str) -> str:
    return "\x1b[30;43m" + text + "\x1b[0m"


def reverse_ansi(text: str) -> str:
    return "\x1b[7m" + text.replace("\x1b[0m", "\x1b[0m\x1b[7m") + "\x1b[0m"


def reverse(text: str) -> str:
    return "\x1b[7m" + text + "\x1b[0m"


def display_width(text: str) -> int:
    return sum(char_width(ch) for ch in ANSI_RE.sub("", text))


def char_width(ch: str) -> int:
    if not ch:
        return 0
    category = unicodedata.category(ch)
    if category[0] == "C" or category in ("Mn", "Me") or unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1


def pad_ansi(text: str, width: int) -> str:
    return text + (" " * max(0, width - display_width(text)))


def fit(text: str, width: int) -> str:
    if width <= 0:
        return ""
    out = ""
    used = 0
    for ch in text:
        ch_width = char_width(ch)
        if used + ch_width > width:
            break
        out += ch
        used += ch_width
    if display_width(text) > width and width >= 1:
        while display_width(out + "...") > width and out:
            out = out[:-1]
        out += "." if width < 3 else "..."
    return out + (" " * max(0, width - display_width(out)))


def fit_ansi(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return pad_ansi(text, width)
    plain = ANSI_RE.sub("", text)
    return fit(plain, width)


class ConfigTool:
    def __init__(self, path: Path, dry_run: bool = False) -> None:
        self.path = path
        self.dry_run = dry_run
        self.data = self.load_json(path)
        self.dirty = False
        self.menu_depth = 0

    def run(self) -> int:
        while True:
            choice = self.menu(
                "メインメニュー",
                [
                    "setting を編集",
                    "luncher/launcher を編集",
                    "exec を編集",
                    "syntax を編集",
                    "directory を編集",
                    "thurupaths を編集",
                    "windows.guards を編集",
                    "保存",
                    "保存して終了",
                    "終了",
                ],
            )
            if choice == 1:
                self.edit_settings()
            elif choice == 2:
                self.edit_launchers()
            elif choice == 3:
                self.edit_execs()
            elif choice == 4:
                self.edit_syntax()
            elif choice == 5:
                self.edit_command_list("directory", "directory")
            elif choice == 6:
                self.edit_string_list("thurupaths", "thurupaths")
            elif choice == 7:
                self.edit_windows_guards()
            elif choice == 8:
                self.save()
            elif choice == 9:
                self.save()
                return 0
            elif choice == 10:
                if self.confirm_exit():
                    return 0

    def edit_settings(self) -> None:
        setting = self.ensure_dict("setting")
        while True:
            self.clear()
            rows, targets = self.setting_rows(setting)
            rows.append("未定義 setting キーを追加/編集")
            targets.append(("__custom__", "string", "未定義 setting キーを追加/編集"))
            rows.append("戻る")
            targets.append(("__back__", "string", "戻る"))
            choice = self.menu("setting", rows)
            key, kind, label = targets[choice - 1]
            if key == "__back__":
                return
            if key == "__separator__":
                continue
            if key == "__custom__":
                self.add_missing_setting(setting)
                continue
            current = setting.get(key, "")
            if kind == "enable":
                new_value = self.ask_enable(label, current)
                if new_value is not None:
                    setting[key] = new_value
                    self.mark_dirty()
            elif kind == "bool":
                new_value = self.ask_bool(label, current)
                if new_value is not None:
                    setting[key] = "true" if new_value else "false"
                    self.mark_dirty()
            elif kind == "number":
                new_value = self.ask_number(label, current)
                if new_value is not None:
                    setting[key] = new_value
                    self.mark_dirty()
            elif kind == "color":
                new_value = self.ask_color(label, str(current), key)
                if new_value is not None:
                    setting[key] = new_value
                    self.mark_dirty()
            else:
                value = self.ask(label, str(current))
                if value is not None:
                    setting[key] = value
                    self.mark_dirty()

    def add_missing_setting(self, setting: dict[str, Any]) -> None:
        known = [item for _, group_items in SETTING_GROUPS for item in group_items]
        missing = [(key, kind, label) for key, kind, label in known if key not in setting]
        rows = [self.setting_missing_row(key, kind, label) for key, kind, label in missing]
        rows.append("戻る")
        if not missing:
            self.pause("追加できる未定義 setting キーはありません。")
            return
        choice = self.menu("未定義 setting キーを追加", rows)
        if choice == len(rows):
            return
        key, kind, label = missing[choice - 1]
        value = self.prompt_setting_value(label, kind, "", key)
        if value is None:
            return
        setting[key] = value
        self.mark_dirty()

    def prompt_setting_value(self, label: str, kind: str, current: Any, key: str = "") -> str | None:
        if kind == "enable":
            value = self.ask_enable(label, current)
            if value is None:
                return None
            return value
        if kind == "bool":
            value = self.ask_bool(label, current)
            if value is None:
                return None
            return "true" if value else "false"
        if kind == "number":
            return self.ask_number(label, current)
        if kind == "color":
            return self.ask_color(label, str(current), key)
        return self.ask(label, str(current))

    def edit_launchers(self) -> None:
        key = self.launcher_key()
        self.edit_command_list(key, "luncher/launcher", include_extra=True)

    def edit_command_list(self, key: str, title: str, include_extra: bool = False) -> None:
        items = self.ensure_list(key)
        while True:
            self.clear()
            labels = [self.command_label(item, include_extra) for item in items]
            labels.extend(["追加", "戻る"])
            choice = self.menu(title, labels)
            if choice == len(labels):
                return
            if choice == len(labels) - 1:
                item = self.prompt_directory_item() if key == "directory" else self.prompt_command_item(include_extra=include_extra)
                if item:
                    items.append(item)
                    self.mark_dirty()
                continue
            self.edit_command_item(items, choice - 1, include_extra)

    def edit_command_item(self, items: list[Any], index: int, include_extra: bool) -> None:
        item = self.ensure_item_dict(items, index)
        while True:
            self.clear()
            rows = [
                f"title: {item.get('title', '')!r}",
                f"command: {item.get('command', '')!r}",
                f"os: {self.os_label(item.get('os'))}",
            ]
            if include_extra:
                rows.extend(
                    [
                        f"char: {item.get('char', '')!r}",
                        f"screen: {item.get('screen', '')!r}",
                    ]
                )
            rows.extend(["削除", "戻る"])
            choice = self.menu("項目編集", rows)
            if choice == 1:
                value = self.ask("title", str(item.get("title", "")))
                if value is not None:
                    item["title"] = value
                    self.mark_dirty()
            elif choice == 2:
                value = self.ask_path("command", str(item.get("command", ""))) if not include_extra else self.ask("command", str(item.get("command", "")))
                if value is not None:
                    item["command"] = value
                    self.mark_dirty()
            elif choice == 3:
                self.edit_os(item)
            elif include_extra and choice == 4:
                self.set_or_delete(item, "char", "char")
            elif include_extra and choice == 5:
                self.set_or_delete(item, "screen", "screen")
            elif choice == len(rows) - 1:
                if self.ask_yes_no("この項目を削除しますか", False):
                    del items[index]
                    self.mark_dirty()
                    return
            elif choice == len(rows):
                return

    def prompt_command_item(self, include_extra: bool = False) -> dict[str, Any] | None:
        title = self.ask("title")
        if not title:
            return None
        command = self.ask("command") if include_extra else self.ask_path("command")
        if not command:
            return None
        item: dict[str, Any] = {"title": title, "command": command}
        if self.ask_yes_no("OS 条件を設定しますか", False):
            self.edit_os(item)
        if include_extra:
            char = self.ask("char (空で未設定)")
            if char:
                item["char"] = char
            screen = self.ask("screen (空で未設定)")
            if screen:
                item["screen"] = screen
        return item

    def prompt_directory_item(self) -> dict[str, Any] | None:
        command = self.ask_path("directory")
        if not command:
            return None
        default_title = Path(command).expanduser().name or command
        title = self.ask("title", default_title)
        if not title:
            return None
        return {"title": title, "command": command}

    def edit_execs(self) -> None:
        items = self.ensure_list("exec")
        while True:
            self.clear()
            labels = [self.exec_label(item) for item in items]
            labels.extend(["追加", "戻る"])
            choice = self.menu("exec", labels)
            if choice == len(labels):
                return
            if choice == len(labels) - 1:
                item = self.prompt_exec_item()
                if item:
                    items.append(item)
                    self.mark_dirty()
                continue
            self.edit_exec_item(items, choice - 1)

    def edit_exec_item(self, items: list[Any], index: int) -> None:
        item = self.ensure_item_dict(items, index)
        while True:
            self.clear()
            rows = [
                f"ext: {item.get('ext', '')!r}",
                f"command: {item.get('command', '')!r}",
                f"os: {self.os_label(item.get('os'))}",
                "削除",
                "戻る",
            ]
            choice = self.menu("exec 項目編集", rows)
            if choice == 1:
                value = self.ask("ext", str(item.get("ext", "")))
                if value is not None:
                    item["ext"] = value.lstrip(".")
                    self.mark_dirty()
            elif choice == 2:
                value = self.ask("command", str(item.get("command", "")))
                if value is not None:
                    item["command"] = value
                    self.mark_dirty()
            elif choice == 3:
                self.edit_os(item)
            elif choice == 4:
                if self.ask_yes_no("この exec を削除しますか", False):
                    del items[index]
                    self.mark_dirty()
                    return
            elif choice == 5:
                return

    def prompt_exec_item(self) -> dict[str, Any] | None:
        ext_value = self.ask("ext")
        if ext_value is None:
            return None
        ext = ext_value.lstrip(".")
        if not ext:
            return None
        command = self.ask("command")
        if not command:
            return None
        item: dict[str, Any] = {"ext": ext, "command": command}
        if self.ask_yes_no("OS 条件を設定しますか", False):
            self.edit_os(item)
        return item

    def edit_syntax(self) -> None:
        syntax = self.ensure_dict("syntax")
        while True:
            self.clear()
            names = sorted(str(key) for key in syntax.keys())
            rows = [self.syntax_label(name, syntax.get(name)) for name in names]
            rows.extend(["タイプ追加", "戻る"])
            choice = self.menu("syntax", rows)
            if choice == len(rows):
                return
            if choice == len(rows) - 1:
                name = self.ask_key("タイプ名/ext")
                if name:
                    syntax[name.lower().lstrip(".")] = {
                        "keywords": [],
                        "keyword_color": "cyan",
                        "comment_color": "green",
                        "string_color": "yellow",
                        "number_color": "magenta",
                    }
                    self.mark_dirty()
                continue
            self.edit_syntax_type(syntax, names[choice - 1])

    def edit_syntax_type(self, syntax: dict[str, Any], name: str) -> None:
        rule = syntax.get(name)
        if not isinstance(rule, dict):
            rule = {}
            syntax[name] = rule
        while True:
            self.clear()
            rows = [
                f"keywords: {self.keywords_summary(rule)}",
                "キーワード群を追加",
                "keywords を全置換",
                "keywords から削除",
                "regex ルール編集",
            ]
            for key, label in SYNTAX_COLOR_KEYS:
                rows.append(f"{label} [{key}]: {self.inline_color_sample(str(rule.get(key, '')))}")
            rows.extend(["タイプ名変更", "タイプ削除", "戻る"])
            choice = self.menu(f"syntax: {name}", rows)
            if choice == 1:
                self.pause("キーワード一覧: " + ", ".join(self.keyword_list(rule)))
            elif choice == 2:
                self.add_keyword_group(rule)
            elif choice == 3:
                keywords = self.ask("keywords (空白/カンマ区切り)", ", ".join(self.keyword_list(rule)))
                if keywords is not None:
                    rule["keywords"] = split_words(keywords)
                    self.mark_dirty()
            elif choice == 4:
                self.remove_keywords(rule)
            elif choice == 5:
                self.edit_regex_rules(rule)
            elif 6 <= choice <= 9:
                key, label = SYNTAX_COLOR_KEYS[choice - 6]
                value = self.ask_color(label, str(rule.get(key, "")), key)
                if value is not None:
                    rule[key] = value
                    self.mark_dirty()
            elif choice == 10:
                new_name = self.ask_key("新しいタイプ名", name)
                if new_name and new_name != name:
                    syntax[new_name] = syntax.pop(name)
                    self.mark_dirty()
                    name = new_name
            elif choice == 11:
                if self.ask_yes_no(f"{name} を削除しますか", False):
                    syntax.pop(name, None)
                    self.mark_dirty()
                    return
            elif choice == 12:
                return

    def add_keyword_group(self, rule: dict[str, Any]) -> None:
        current = self.keyword_list(rule)
        text = self.ask("追加するキーワード群 (空白/カンマ区切り)")
        if text is None:
            return
        additions = split_words(text)
        if not additions:
            return
        seen = set(current)
        merged = current[:]
        for keyword in additions:
            if keyword not in seen:
                merged.append(keyword)
                seen.add(keyword)
        rule["keywords"] = merged
        self.mark_dirty()

    def remove_keywords(self, rule: dict[str, Any]) -> None:
        current = self.keyword_list(rule)
        if not current:
            self.pause("削除できるキーワードがありません。")
            return
        rows = current + ["戻る"]
        choice = self.menu("削除するキーワード", rows)
        if choice == len(rows):
            return
        target = current[choice - 1]
        rule["keywords"] = [keyword for keyword in current if keyword != target]
        self.mark_dirty()

    def edit_regex_rules(self, rule: dict[str, Any]) -> None:
        regex_rules = rule.get("regex")
        if not isinstance(regex_rules, list):
            regex_rules = []
            rule["regex"] = regex_rules
        while True:
            self.clear()
            rows = [self.regex_label(item) for item in regex_rules]
            rows.extend(["追加", "戻る"])
            choice = self.menu("regex ルール", rows)
            if choice == len(rows):
                return
            if choice == len(rows) - 1:
                item = self.prompt_regex_item()
                if item:
                    regex_rules.append(item)
                    self.mark_dirty()
                continue
            self.edit_regex_item(regex_rules, choice - 1)

    def edit_regex_item(self, items: list[Any], index: int) -> None:
        item = self.ensure_item_dict(items, index)
        while True:
            self.clear()
            rows = [
                f"pattern: {item.get('pattern', '')!r}",
                f"color: {item.get('color', '')!r}",
                "削除",
                "戻る",
            ]
            choice = self.menu("regex 項目編集", rows)
            if choice == 1:
                pattern = self.ask_regex(str(item.get("pattern", "")))
                if pattern is not None:
                    item["pattern"] = pattern
                    self.mark_dirty()
            elif choice == 2:
                color = self.ask_color("regex color", str(item.get("color", "")), "regex_color")
                if color is not None:
                    item["color"] = color
                    self.mark_dirty()
            elif choice == 3:
                if self.ask_yes_no("この regex を削除しますか", False):
                    del items[index]
                    self.mark_dirty()
                    return
            elif choice == 4:
                return

    def prompt_regex_item(self) -> dict[str, str] | None:
        pattern = self.ask_regex("")
        if not pattern:
            return None
        color = self.ask_color("regex color", "cyan", "regex_color")
        if not color:
            return None
        return {"pattern": pattern, "color": color}

    def edit_string_list(self, key: str, title: str) -> None:
        items = self.ensure_list(key)
        while True:
            self.clear()
            rows = [repr(item) for item in items]
            rows.extend(["追加", "戻る"])
            choice = self.menu(title, rows)
            if choice == len(rows):
                return
            if choice == len(rows) - 1:
                value = self.ask_path("追加する値") if title in ("thurupaths", "windows.guards") else self.ask("追加する値")
                if value:
                    items.append(value)
                    self.mark_dirty()
                continue
            current = "" if not isinstance(items[choice - 1], str) else items[choice - 1]
            rows2 = ["編集", "削除", "戻る"]
            sub = self.menu(f"{title}: {current}", rows2)
            if sub == 1:
                value = self.ask_path("値", current) if title in ("thurupaths", "windows.guards") else self.ask("値", current)
                if value is not None:
                    items[choice - 1] = value
                    self.mark_dirty()
            elif sub == 2:
                if self.ask_yes_no("削除しますか", False):
                    del items[choice - 1]
                    self.mark_dirty()

    def edit_windows_guards(self) -> None:
        windows = self.ensure_dict("windows")
        guards = windows.get("guards")
        if not isinstance(guards, list):
            guards = []
            windows["guards"] = guards
        self.edit_string_list_in_place(guards, "windows.guards")

    def edit_string_list_in_place(self, items: list[Any], title: str) -> None:
        while True:
            self.clear()
            rows = [repr(item) for item in items]
            rows.extend(["追加", "戻る"])
            choice = self.menu(title, rows)
            if choice == len(rows):
                return
            if choice == len(rows) - 1:
                value = self.ask_path("追加する値")
                if value:
                    items.append(value)
                    self.mark_dirty()
                continue
            current = "" if not isinstance(items[choice - 1], str) else items[choice - 1]
            sub = self.menu(f"{title}: {current}", ["編集", "削除", "戻る"])
            if sub == 1:
                value = self.ask_path("値", current)
                if value is not None:
                    items[choice - 1] = value
                    self.mark_dirty()
            elif sub == 2 and self.ask_yes_no("削除しますか", False):
                del items[choice - 1]
                self.mark_dirty()

    def edit_os(self, item: dict[str, Any]) -> None:
        choices = ["未設定", "mac", "win", "linux", "複数指定", "直接入力"]
        choice = self.menu("OS 条件", choices)
        if choice == 1:
            item.pop("os", None)
        elif choice in (2, 3, 4):
            item["os"] = choices[choice - 1]
        elif choice == 5:
            raw = self.ask("OS 名をカンマ区切りで入力", self.os_label(item.get("os")))
            if raw is None:
                return
            values = [part.strip().lower() for part in raw.split(",") if part.strip()]
            if values:
                item["os"] = values
            else:
                item.pop("os", None)
        elif choice == 6:
            raw = self.ask("os 値", self.os_label(item.get("os")))
            if raw is None:
                return
            if raw:
                item["os"] = raw
            else:
                item.pop("os", None)
        self.mark_dirty()

    def ask_color(self, label: str, current: str = "", key: str = "") -> str | None:
        samples = self.data.get("sample_colors")
        normal_colors = [item for item in samples if isinstance(item, str)] if isinstance(samples, list) else COLOR_NAMES
        choices = [(color, color) for color in normal_colors]
        if key in REVERSIBLE_COLOR_KEYS:
            known = {value for value, _ in choices}
            choices.extend((value, label) for value, label in REVERSE_COLOR_CHOICES if value not in known)
        rows = [self.color_row(value, current, name) for value, name in choices]
        rows.extend(["ANSI コード/任意名を直接入力", "空にする", "キャンセル"])
        choice = self.menu(f"{label}: 色選択", rows)
        if choice <= len(choices):
            return choices[choice - 1][0]
        if choice == len(choices) + 1:
            return self.ask("色名または ANSI コード", current)
        if choice == len(choices) + 2:
            return ""
        return None

    @staticmethod
    def color_row(color: str, current: str = "", name: str | None = None) -> str:
        swatch = color_text("  SAMPLE  ", color)
        code = color_code(color) or "default"
        suffix = color_text(" current", "yellow") if color == current else ""
        title = name if name is not None else color
        return f"{swatch}  {title:<22} ansi={code:<8}{suffix}"

    def ask_bool(self, label: str, current: Any) -> bool | None:
        current_bool = str(current).strip().lower() in BOOL_TRUE
        choice = self.menu(f"{label}: 真偽", [f"true{' (current)' if current_bool else ''}", f"false{' (current)' if not current_bool else ''}", "キャンセル"])
        if choice == 1:
            return True
        if choice == 2:
            return False
        return None

    def ask_enable(self, label: str, current: Any) -> str | None:
        current_text = str(current).strip().lower()
        choice = self.menu(
            f"{label}: enable",
            [
                f"enable{' (current)' if current_text == 'enable' else ''}",
                f"disable{' (current)' if current_text in ('disable', 'false', '0', 'off', 'no') else ''}",
                "キャンセル",
            ],
        )
        if choice == 1:
            return "enable"
        if choice == 2:
            return "disable"
        return None

    def ask_path(self, label: str, current: str = "") -> str | None:
        base = Path(current).expanduser() if current else Path.cwd()
        if not base.is_dir():
            base = base.parent if base.parent.exists() else Path.cwd()
        cwd = base.resolve()
        while True:
            choices = self.path_choices(cwd, current)
            labels = [row for row, _ in choices] + ["直接入力", "キャンセル"]
            choice = self.menu(f"{label}: path", labels)
            if choice <= len(choices):
                row, path = choices[choice - 1]
                if row.startswith("[select this directory]"):
                    return str(path)
                if row.startswith("[..]") and path != cwd:
                    cwd = path
                    continue
                if path.is_dir():
                    subdirs = self.child_directories(path)
                    if subdirs:
                        cwd = path
                        continue
                    return str(path)
                return str(path)
            if choice == len(choices) + 1:
                return self.ask(label, current)
            return None

    def path_choices(self, cwd: Path, current: str) -> list[tuple[str, Path]]:
        rows: list[tuple[str, Path]] = []
        if current:
            rows.append((f"[current] {current}", Path(current).expanduser()))
        rows.append(("[select this directory] " + str(cwd), cwd))
        parent = cwd.parent
        if parent != cwd:
            rows.append(("[..] " + str(parent), parent))
        home = Path.home()
        rows.append(("[~] " + str(home), home))
        for path in self.child_directories(cwd)[:40]:
            rows.append((path.name + "/", path))
        return rows

    @staticmethod
    def child_directories(path: Path) -> list[Path]:
        try:
            return sorted([child for child in path.iterdir() if child.is_dir()], key=lambda item: item.name.lower())
        except OSError:
            return []

    def ask_number(self, label: str, current: Any) -> str | None:
        while True:
            value = self.ask(label, str(current))
            if value is None:
                return None
            if value == "":
                return None
            try:
                float(value)
            except ValueError:
                self.pause("数値を入力してください。")
                continue
            return value

    def ask_regex(self, current: str = "") -> str | None:
        while True:
            pattern = self.ask("regex pattern", current)
            if pattern is None:
                return None
            if not pattern:
                return None
            try:
                re.compile(pattern)
            except re.error as exc:
                self.pause(f"regex エラー: {exc}")
                continue
            return pattern

    def ask_key(self, label: str, current: str = "") -> str:
        while True:
            value = self.ask(label, current)
            if value is None:
                return ""
            value = value.strip().lower().lstrip(".")
            if not value:
                return ""
            if all(ch.isalnum() or ch in "_-" for ch in value):
                return value
            self.pause("英数字、_、- のみ使えます。")

    def set_or_delete(self, item: dict[str, Any], key: str, label: str) -> None:
        value = self.ask(f"{label} (空で削除)", str(item.get(key, "")))
        if value is None:
            return
        if value:
            item[key] = value
        else:
            item.pop(key, None)
        self.mark_dirty()

    def save(self) -> None:
        if self.dry_run:
            print(json.dumps(self.data, ensure_ascii=False, indent=2))
            self.pause("dry-run のため保存していません。")
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self.data, ensure_ascii=False, indent=2) + "\n"
        self.path.write_text(text, encoding="utf-8")
        self.dirty = False
        self.pause("保存しました。")

    def confirm_exit(self) -> bool:
        if not self.dirty:
            return True
        return self.ask_yes_no("未保存の変更を破棄して終了しますか", False)

    def launcher_key(self) -> str:
        if isinstance(self.data.get("luncher"), list):
            return "luncher"
        if isinstance(self.data.get("launcher"), list):
            return "launcher"
        self.data["luncher"] = []
        return "luncher"

    def ensure_dict(self, key: str) -> dict[str, Any]:
        value = self.data.get(key)
        if not isinstance(value, dict):
            value = {}
            self.data[key] = value
            self.mark_dirty()
        return value

    def ensure_list(self, key: str) -> list[Any]:
        value = self.data.get(key)
        if not isinstance(value, list):
            value = []
            self.data[key] = value
            self.mark_dirty()
        return value

    def ensure_item_dict(self, items: list[Any], index: int) -> dict[str, Any]:
        item = items[index]
        if not isinstance(item, dict):
            item = {}
            items[index] = item
            self.mark_dirty()
        return item

    def mark_dirty(self) -> None:
        self.dirty = True

    def menu(self, title: str, items: list[str]) -> int:
        selected = 0
        top = 0
        self.menu_depth += 1
        try:
            while True:
                top, visible = self.draw_menu(title, items, selected, top)
                key = self.read_key()
                if key in ("UP", "LEFT"):
                    selected = (selected - 1) % len(items)
                elif key in ("DOWN", "RIGHT"):
                    selected = (selected + 1) % len(items)
                elif key == "HOME":
                    selected = 0
                elif key == "END":
                    selected = len(items) - 1
                elif key == "PGUP":
                    selected = max(0, selected - visible)
                elif key == "PGDN":
                    selected = min(len(items) - 1, selected + visible)
                elif key == "ENTER":
                    return selected + 1
                elif key == "ESC":
                    fallback = self.menu_escape_choice(items)
                    if fallback is not None:
                        return fallback
                if selected < top:
                    top = selected
                elif selected >= top + visible:
                    top = selected - visible + 1
        finally:
            self.menu_depth -= 1

    def draw_menu(self, title: str, items: list[str], selected: int, top: int) -> tuple[int, int]:
        self.clear()
        columns, lines = shutil.get_terminal_size(fallback=(100, 28))
        depth = self.visual_menu_depth(title)
        row = min(lines, 3 + depth * 2)
        col = min(columns, 4 + depth * 2)
        max_width = max(20, columns - col + 1)
        max_height = max(6, lines - row + 1)
        content_width = min(max_width - 2, max(24, max([display_width(item) for item in items] + [display_width(title)]) + 4))
        width = min(max_width, content_width + 2)
        height = min(max_height, max(4, min(len(items) + 3, lines - row + 1)))
        visible = max(1, height - 3)
        top = min(max(0, top), max(0, len(items) - visible))
        if selected < top:
            top = selected
        elif selected >= top + visible:
            top = selected - visible + 1

        self.draw_popup_border(row, col, width, height)
        for screen_index in range(visible):
            index = top + screen_index
            self.move(row + 1 + screen_index, col + 1)
            if index >= len(items):
                print(" " * (width - 2), end="")
                continue
            marker = ">" if index == selected else " "
            text = fit_ansi(f" {marker} {items[index]}", width - 2)
            if index == selected:
                print(reverse_ansi(text), end="")
            else:
                print(text, end="")
        self.move(row + height - 1, col + 1)
        footer = " Enter:OK  ESC:Cancel "
        if len(items) > visible:
            footer += f" {selected + 1}/{len(items)} "
        print(yellow_bg(fit(footer, width - 2)), end="")
        sys.stdout.flush()
        return top, visible

    @staticmethod
    def move(row: int, col: int) -> None:
        print(f"\033[{max(1, row)};{max(1, col)}H", end="")

    @staticmethod
    def draw_popup_border(row: int, col: int, width: int, height: int) -> None:
        horizontal = "█" * (width - 2)
        ConfigTool.move(row, col)
        print(yellow("█" + horizontal + "█"), end="")
        for inner_row in range(1, height - 1):
            ConfigTool.move(row + inner_row, col)
            print(yellow("█") + (" " * (width - 2)) + yellow("█"), end="")
        ConfigTool.move(row + height - 1, col)
        print(yellow("█" + horizontal + "█"), end="")

    @staticmethod
    def visual_menu_depth(title: str) -> int:
        if title == "メインメニュー":
            return 0
        depth = 1
        if ":" in title:
            depth += 1
        if any(token in title for token in ("色選択", "項目編集", "regex 項目編集", "OS 条件", "削除するキーワード", "未定義 setting", "path")):
            depth += 1
        return min(depth, 5)

    def read_key(self) -> str:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = os.read(fd, 1).decode("utf-8", errors="ignore")
            if ch in ("\r", "\n"):
                return "ENTER"
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\x7f":
                return "BACKSPACE"
            if ch == "\x04":
                return "DELETE"
            if ch != "\x1b":
                return {
                    "k": "UP",
                    "j": "DOWN",
                    "h": "LEFT",
                    "l": "RIGHT",
                    "g": "HOME",
                    "G": "END",
                }.get(ch, ch)
            seq = self.read_escape_sequence(fd)
            return {
                "\x1b[A": "UP",
                "\x1b[B": "DOWN",
                "\x1b[C": "RIGHT",
                "\x1b[D": "LEFT",
                "\x1b[H": "HOME",
                "\x1b[F": "END",
                "\x1bOH": "HOME",
                "\x1bOF": "END",
                "\x1b[5~": "PGUP",
                "\x1b[6~": "PGDN",
            }.get(seq, "ESC")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    @staticmethod
    def read_escape_sequence(fd: int) -> str:
        seq = "\x1b"
        if not select.select([fd], [], [], 0.1)[0]:
            return seq
        seq += os.read(fd, 1).decode("utf-8", errors="ignore")
        if seq not in ("\x1b[", "\x1bO"):
            return seq
        if not select.select([fd], [], [], 0.1)[0]:
            return seq
        seq += os.read(fd, 1).decode("utf-8", errors="ignore")
        if len(seq) >= 3 and not seq[-1].isdigit():
            return seq
        while select.select([fd], [], [], 0.1)[0]:
            seq += os.read(fd, 1).decode("utf-8", errors="ignore")
            if seq[-1].isalpha() or seq[-1] == "~" or len(seq) >= 8:
                break
        return seq

    @staticmethod
    def menu_escape_choice(items: list[str]) -> int | None:
        for label in ("戻る", "キャンセル", "終了"):
            if label in items:
                return items.index(label) + 1
        return None

    def ask(self, label: str, current: str = "") -> str | None:
        return self.input_popup(label, current)

    def ask_yes_no(self, label: str, default: bool) -> bool:
        rows = [f"はい{' (default)' if default else ''}", f"いいえ{' (default)' if not default else ''}", "キャンセル"]
        choice = self.menu(label, rows)
        if choice == 1:
            return True
        if choice == 2:
            return False
        return default

    def pause(self, message: str = "") -> None:
        self.menu(message or "続行", ["OK"])

    def input_popup(self, label: str, current: str = "") -> str | None:
        text = list(current)
        cursor = len(text)
        offset = 0
        while True:
            columns, lines = shutil.get_terminal_size(fallback=(100, 28))
            title_width = display_width(label) + 8
            value_width = max(20, min(max(20, columns - 18), max(title_width, display_width(current) + 8)))
            width = min(columns - 8, value_width + 2)
            height = 5
            depth = 3
            row = min(lines - height + 1, 3 + depth * 2)
            col = min(columns - width + 1, 4 + depth * 2)
            field_width = max(1, width - 2)
            while display_width("".join(text[offset:cursor])) > max(0, field_width - 1):
                offset += 1
            while cursor < offset:
                offset = max(0, offset - 1)
            visible = ""
            for ch in text[offset:]:
                if display_width(visible + ch) > field_width:
                    break
                visible += ch
            self.clear()
            self.draw_popup_border(row, col, width, height)
            self.move(row + 1, col + 1)
            print(fit(label, field_width), end="")
            self.move(row + 2, col + 1)
            print(fit(visible, field_width), end="")
            self.move(row + height - 1, col + 1)
            print(yellow_bg(fit(" Enter:OK  ESC:Cancel ", field_width)), end="")
            cursor_col = col + 1 + min(field_width - 1, display_width("".join(text[offset:cursor])))
            self.move(row + 2, cursor_col)
            sys.stdout.flush()
            key = self.read_key()
            if key == "ENTER":
                return "".join(text)
            if key == "ESC":
                return None
            if key == "LEFT":
                cursor = max(0, cursor - 1)
            elif key == "RIGHT":
                cursor = min(len(text), cursor + 1)
            elif key == "HOME":
                cursor = 0
                offset = 0
            elif key == "END":
                cursor = len(text)
            elif key == "BACKSPACE":
                if cursor > 0:
                    del text[cursor - 1]
                    cursor -= 1
            elif key == "DELETE":
                if cursor < len(text):
                    del text[cursor]
            elif len(key) == 1 and ord(key) >= 32:
                text[cursor:cursor] = list(key)
                cursor += len(key)

    def clear(self) -> None:
        if sys.stdout.isatty():
            print("\033[2J\033[H", end="")

    @staticmethod
    def load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: JSON エラー line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
        except OSError as exc:
            raise SystemExit(f"{path}: 読み込み失敗: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"{path}: ルートは JSON object である必要があります。")
        return value

    @staticmethod
    def command_label(item: Any, include_extra: bool = False) -> str:
        if not isinstance(item, dict):
            return repr(item)
        extra = []
        if item.get("os") is not None:
            extra.append(f"os={ConfigTool.os_label(item.get('os'))}")
        if include_extra and item.get("char"):
            extra.append(f"char={item.get('char')}")
        if include_extra and item.get("screen"):
            extra.append(f"screen={item.get('screen')}")
        suffix = f" ({', '.join(extra)})" if extra else ""
        return f"{item.get('title', '')}: {item.get('command', '')}{suffix}"

    @staticmethod
    def exec_label(item: Any) -> str:
        if not isinstance(item, dict):
            return repr(item)
        suffix = f" (os={ConfigTool.os_label(item.get('os'))})" if item.get("os") is not None else ""
        return f".{item.get('ext', '')}: {item.get('command', '')}{suffix}"

    @staticmethod
    def syntax_label(name: str, rule: Any) -> str:
        if not isinstance(rule, dict):
            return name
        keyword_count = len(rule.get("keywords")) if isinstance(rule.get("keywords"), list) else 0
        regex_count = len(rule.get("regex")) if isinstance(rule.get("regex"), list) else 0
        return f"{name}: keywords={keyword_count}, regex={regex_count}"

    @staticmethod
    def regex_label(item: Any) -> str:
        if not isinstance(item, dict):
            return repr(item)
        return f"{item.get('pattern', '')!r} -> {item.get('color', '')!r}"

    @staticmethod
    def os_label(value: Any) -> str:
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        if value is None:
            return "未設定"
        return str(value)

    def setting_rows(self, setting: dict[str, Any]) -> tuple[list[str], list[tuple[str, str, str]]]:
        items = [item for _, group_items in SETTING_GROUPS for item in group_items]
        label_width = max(display_width(label) for _, _, label in items)
        spec_width = max(display_width(f"[{key}:{kind}]") for key, kind, _ in items)
        rows: list[str] = []
        targets: list[tuple[str, str, str]] = []
        for group_index, (group, group_items) in enumerate(SETTING_GROUPS):
            if group_index > 0:
                rows.append(self.setting_separator(group))
                targets.append(("__separator__", "separator", group))
            for key, kind, label in group_items:
                value = setting.get(key, "")
                rows.append(self.setting_row(label, key, kind, value, label_width, spec_width))
                targets.append((key, kind, label))
        return rows, targets

    @staticmethod
    def setting_row(label: str, key: str, kind: str, value: Any, label_width: int, spec_width: int) -> str:
        left = fit(label, label_width)
        spec = fit(f"[{key}:{kind}]", spec_width)
        shown = ConfigTool.setting_value_text(kind, value)
        return f"{left}  {spec}  {shown}"

    @staticmethod
    def setting_missing_row(key: str, kind: str, label: str) -> str:
        return f"{fit(label, 24)}  [{key}:{kind}]"

    @staticmethod
    def setting_value_text(kind: str, value: Any) -> str:
        text = "" if value is None else str(value)
        if kind == "bool":
            lowered = text.strip().lower()
            if lowered in BOOL_TRUE or lowered == "enable":
                return "true"
            if lowered in BOOL_FALSE or lowered == "disable":
                return "false"
            return text
        if kind == "enable":
            return "enable" if text.strip().lower() == "enable" else "disable"
        if kind == "number":
            return text
        if kind == "color":
            return ConfigTool.inline_color_sample(text)
        return repr(text)

    @staticmethod
    def setting_separator(title: str) -> str:
        return f"--- {title} " + ("-" * 36)

    @staticmethod
    def keyword_list(rule: dict[str, Any]) -> list[str]:
        keywords = rule.get("keywords")
        if not isinstance(keywords, list):
            return []
        return [item for item in keywords if isinstance(item, str)]

    @staticmethod
    def keywords_summary(rule: dict[str, Any]) -> str:
        keywords = ConfigTool.keyword_list(rule)
        if not keywords:
            return "(none)"
        preview = ", ".join(keywords[:8])
        if len(keywords) > 8:
            preview += f", ... +{len(keywords) - 8}"
        return preview

    @staticmethod
    def inline_color_sample(color: str) -> str:
        if not color:
            return "''"
        return f"{color!r} {color_text(' SAMPLE ', color)}"


def split_words(text: str) -> list[str]:
    return [part for part in re.split(r"[\s,]+", text.strip()) if part]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="vfiler.def CUI settings editor")
    parser.add_argument("def_file", nargs="?", default="vfiler.def", help="編集する DEF ファイル")
    parser.add_argument("--dry-run", action="store_true", help="保存せず、保存時に JSON を表示する")
    parser.add_argument("--check", action="store_true", help="DEF を読み込めるかだけ確認する")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    path = Path(args.def_file).expanduser()
    tool = ConfigTool(path, dry_run=bool(args.dry_run))
    if args.check:
        print(f"ok: {path}")
        return 0
    if not sys.stdin.isatty():
        raise SystemExit("CUI 操作には端末が必要です。")
    if not shutil.get_terminal_size(fallback=(80, 24)).columns:
        raise SystemExit("端末サイズを取得できません。")
    return tool.run()


if __name__ == "__main__":
    raise SystemExit(main())
