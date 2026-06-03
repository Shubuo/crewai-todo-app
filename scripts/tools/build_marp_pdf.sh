#!/bin/zsh

set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/TeX/texbin:$PATH"

if [ "$#" -eq 0 ]; then
  exit 0
fi

normalize_input_path() {
  local raw="$1"

  if [[ "$raw" == file://* ]]; then
    python3 -c 'import sys, urllib.parse; print(urllib.parse.unquote(sys.argv[1][7:]))' "$raw"
    return 0
  fi

  printf '%s\n' "$raw"
}

resolve_browser_path() {
  local candidate

  for candidate in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    "/Users/$USER/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell"
  do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  local glob_candidate
  for glob_candidate in "/Users/$USER/Library/Caches/ms-playwright"/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell; do
    if [ -x "$glob_candidate" ]; then
      printf '%s\n' "$glob_candidate"
      return 0
    fi
  done

  return 1
}

ensure_browser() {
  if resolve_browser_path >/dev/null 2>&1; then
    return 0
  fi

  printf 'Uyumlu tarayici bulunamadi, Playwright Chromium indiriliyor...\n' >&2
  npx playwright@latest install chromium >/dev/null

  if ! resolve_browser_path >/dev/null 2>&1; then
    printf 'Chromium kurulumu sonrasi tarayici yolu tespit edilemedi.\n' >&2
    exit 1
  fi
}

ensure_browser
browser_path="$(resolve_browser_path)"

processed_any=0

for f in "$@"; do
  f="$(normalize_input_path "$f")"

  if [ ! -f "$f" ]; then
    continue
  fi

  if [[ "$f" != *.md ]]; then
    continue
  fi

  processed_any=1

  (
    file_dir="$(dirname "$f")"
    file_name="$(basename "$f")"
    file_base="${file_name%.*}"
    if [[ "$file_name" == *.marp.md ]]; then
      file_base="${file_name%.marp.md}"
    fi

    cd "$file_dir"

    marp_args=(
      "$file_name"
      --pdf
      --pdf-notes
      --html
      --allow-local-files
      --browser chrome
      --browser-path "$browser_path"
      -o "$file_base.pdf"
    )

    if [ -f "metropolis-ege.css" ]; then
      marp_args+=(--theme-set "./metropolis-ege.css")
    fi

    npx @marp-team/marp-cli@latest "${marp_args[@]}"
  )
done

if [ "$processed_any" -eq 0 ]; then
  exit 0
fi
