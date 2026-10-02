#!/usr/bin/env bash

case $- in
  *i*) ;;
  *) return 0 2>/dev/null || exit 0 ;;
esac

__vfiler_popup_file() {
  local script_dir
  local vfiler_py
  local append

  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  vfiler_py="$script_dir/vfiler.py"

  append="$(python3 "$vfiler_py" --z-client)"
  __vfiler_insert_readline "$append"
}

__vfiler_insert_readline() {
  local append
  local before
  local after

  append="$1"
  if [[ -n $append ]]; then
    before="${READLINE_LINE:0:READLINE_POINT}"
    after="${READLINE_LINE:READLINE_POINT}"
    if [[ -n $before && $before != *[[:space:]] && $append != [[:space:]]* ]]; then
      append=" $append"
    fi
    READLINE_LINE="${before}${append}${after}"
    READLINE_POINT=$((READLINE_POINT + ${#append}))
  fi
}

__vfiler_open_filer() {
  local script_dir
  local vfiler_py
  local append

  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  vfiler_py="$script_dir/vfiler.py"

  append="$(python3 "$vfiler_py" "$PWD")"
  __vfiler_insert_readline "$append"
}

__vfiler_popup_start_resident() {
  local script_dir
  local vfiler_py

  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  vfiler_py="$script_dir/vfiler.py"

  python3 "$vfiler_py" -z
}

__vfiler_popup_start_resident

bind 'set keyseq-timeout 10'
bind -x '"\e": __vfiler_popup_file'
bind -x '"\e?": __vfiler_popup_file'
bind -x '"\e[13;2u": __vfiler_open_filer'
