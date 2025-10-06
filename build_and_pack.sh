#!/usr/bin/env bash
# build_and_pack.sh – Build & Pack in einem Rutsch (venv-first)

set -euo pipefail
cd "$(dirname "$0")"

VENV="$PWD/.venv"
PIP="$VENV/bin/pip"
PYI="$VENV/bin/pyinstaller"

if [[ ! -x "$PIP" ]]; then
  echo "❌ Kein venv unter .venv gefunden."
  echo "Bitte zuerst einrichten:  python3 -m venv .venv && ./.venv/bin/pip install -U pip"
  exit 1
fi

echo "🧩 Installiere/aktualisiere Requirements…"
if [[ -f "requirements.txt" ]]; then
  "$PIP" install -U -r requirements.txt
else
  # Fallback: minimal nötige Pakete, falls keine requirements.txt existiert
  "$PIP" install -U pyinstaller certifi
fi

if [[ ! -x "$PYI" ]]; then
  echo "🧰 Installiere PyInstaller ins venv…"
  "$PIP" install -U pyinstaller
fi

echo "🔧 Schritt 1: Baue App mit PyInstaller (venv)"
"$PYI" PRisM-RAC_arm64.spec --noconfirm

echo "📦 Schritt 2: Bereite Distribution vor"
chmod +x ./prepare_app_for_distribution.sh
./prepare_app_for_distribution.sh -a "dist/PRisM-RAC.app" -o "PRisM-RAC.zip"

echo "✅ Fertig: App gebaut & gepackt."