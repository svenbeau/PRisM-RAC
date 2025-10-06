#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Falls per ENV schon gesetzt, direkt nutzen
if [[ -n "${ARCH:-}" ]]; then
  exec ./build_and_pack.sh --arch "$ARCH"
  exit
fi

# macOS-Dialog zur Auswahl (osascript)
choice="$(/usr/bin/osascript <<'OSA'
set opts to {"arm64","x86_64","both"}
set sel to choose from list opts with title "PRisM-RAC Build" with prompt "Welche Architektur bauen?" default items {"arm64"} OK button name "Build" cancel button name "Abbrechen"
if sel is false then
  return "CANCEL"
else
  return item 1 of sel
end if
OSA
)"

if [[ "$choice" == "CANCEL" ]]; then
  echo "Abgebrochen."
  exit 1
fi

echo "🔧 Auswahl: $choice"
exec ./build_and_pack.sh --arch "$choice"