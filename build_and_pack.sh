#!/usr/bin/env bash
# build_and_pack.sh – Build & Pack in einem Rutsch (venv-first)
# --------------------------------------------------------------
# Automatischer Build für PRisM-RAC:
#  1. Aktualisiert das venv und installiert Requirements
#  2. Ruft PyInstaller mit .spec auf
#  3. Holt Version aus prism_version.py
#  4. Führt prepare_app_for_distribution.sh mit Versions-Tag aus

set -euo pipefail
cd "$(dirname "$0")"

# === Pfade ===
VENV="$PWD/.venv"
PIP="$VENV/bin/pip"
PYI="$VENV/bin/pyinstaller"
PYTHON="$VENV/bin/python"

# === Schritt 0: Check auf venv ===
if [[ ! -x "$PIP" ]]; then
  echo "❌ Kein venv unter .venv gefunden."
  echo "Bitte zuerst einrichten:"
  echo "    python3 -m venv .venv && ./.venv/bin/pip install -U pip"
  exit 1
fi

# === Schritt 1: Requirements aktualisieren ===
echo "🧩 Installiere/aktualisiere Requirements…"
if [[ -f "requirements.txt" ]]; then
  "$PIP" install -U -r requirements.txt
else
  echo "⚠️  Keine requirements.txt gefunden – installiere Minimalpakete."
  "$PIP" install -U pyinstaller certifi
fi

# === Schritt 2: Sicherstellen, dass PyInstaller existiert ===
if [[ ! -x "$PYI" ]]; then
  echo "🧰 Installiere PyInstaller ins venv…"
  "$PIP" install -U pyinstaller
fi

# === Schritt 3: Versionsnummer aus prism_version.py lesen ===
APP_VERSION="unknown"
if [[ -f "prism_version.py" ]]; then
  APP_VERSION=$("$PYTHON" -c 'from prism_version import __version__; print(__version__)')
else
  echo "⚠️  Keine prism_version.py gefunden – nutze Default-Version 0.0.0"
  APP_VERSION="0.0.0"
fi

echo "🏷  Version erkannt: ${APP_VERSION}"

# === Schritt 4: PyInstaller-Build starten ===
echo "🔧 Schritt 1: Baue App mit PyInstaller (venv)"
"$PYI" PRisM-RAC_arm64.spec --noconfirm

# === Schritt 5: Distribution vorbereiten ===
echo "📦 Schritt 2: Bereite Distribution vor"
chmod +x ./prepare_app_for_distribution.sh
./prepare_app_for_distribution.sh -a "dist/PRisM-RAC.app" -o "PRisM-RAC_${APP_VERSION}.zip"

# === Schritt 6: Abschlussmeldung ===
echo "✅ Fertig: App v${APP_VERSION} gebaut & gepackt."