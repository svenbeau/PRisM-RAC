#!/usr/bin/env bash
# build_and_pack.sh – Build & Pack mit wählbarer Architektur
# Nutzung:
#   ./build_and_pack.sh                  # default: --arch arm64
#   ./build_and_pack.sh --arch x86_64
#   ./build_and_pack.sh --arch both

set -euo pipefail
cd "$(dirname "$0")"

# --- CLI-Args -----------------------------------------------------------------
ARCH="${1:-}"
if [[ "$ARCH" == "--arch" ]]; then
  ARCH="${2:-}"
elif [[ -z "$ARCH" ]]; then
  ARCH="arm64"
elif [[ "$ARCH" == "--help" || "$ARCH" == "-h" ]]; then
  echo "Usage: $0 [--arch arm64|x86_64|both]"
  exit 0
fi

# --- Pfade/Tools --------------------------------------------------------------
VENV="$PWD/.venv"
PIP="$VENV/bin/pip"
PYI="$VENV/bin/pyinstaller"
PY="$VENV/bin/python"

# --- Checks -------------------------------------------------------------------
if [[ ! -x "$PIP" ]]; then
  echo "❌ Kein venv gefunden (.venv). Bitte zuerst:"
  echo "   python3 -m venv .venv && ./.venv/bin/pip install -U pip"
  exit 1
fi

# --- Requirements sicherstellen -----------------------------------------------
echo "🧩 Installiere/aktualisiere Requirements…"
if [[ -f "requirements.txt" ]]; then
  "$PIP" install -U -r requirements.txt
else
  "$PIP" install -U pyinstaller certifi
fi

if [[ ! -x "$PYI" ]]; then
  echo "🧰 Installiere PyInstaller ins venv…"
  "$PIP" install -U pyinstaller
fi

# --- Version aus prism_version.py lesen ---------------------------------------
APP_VERSION="$("$PY" - <<'PY'
import importlib, sys
try:
    v = importlib.import_module("prism_version").__version__
    print(v)
except Exception as e:
    print("0.0.0")
PY
)"
echo "🏷  Version erkannt: ${APP_VERSION}"

# --- Hilfsfunktionen ----------------------------------------------------------
build_one() {
  local arch="$1"
  local spec
  local dist_dir
  local app_in_dist
  local app_labeled
  local zip_name

  if [[ "$arch" == "arm64" ]]; then
    spec="PRisM-RAC_arm64.spec"
  elif [[ "$arch" == "x86_64" ]]; then
    spec="PRisM-RAC_x86_64.spec"
  else
    echo "⚠️  Unbekannte Architektur: $arch"; return 1
  fi

  if [[ ! -f "$spec" ]]; then
    echo "❌ Spec-Datei fehlt: $spec"
    exit 1
  fi

  dist_dir="dist_${arch}"
  app_in_dist="${dist_dir}/PRisM-RAC.app"
  app_labeled="PRisM-RAC_${arch}.app"
  zip_name="PRisM-RAC_${arch}.zip"

  echo "🔧 Schritt 1 ($arch): Baue App mit PyInstaller"
  "$PYI" "$spec" --noconfirm --distpath "$dist_dir" --workpath "build_${arch}"

  echo "📦 Schritt 2 ($arch): Bereite Distribution vor"
  chmod +x ./prepare_app_for_distribution.sh

  # prepare_app_for_distribution erwartet einen App-Pfad und Zieldateinamen
  ./prepare_app_for_distribution.sh -a "$app_in_dist" -o "$zip_name"

  # Für Kombi-Zip: beschriftete Kopie ablegen
  rm -rf "$app_labeled"
  cp -R "$app_in_dist" "$app_labeled"

  echo "✅ Fertig ($arch): $zip_name"
}

make_dual_zip() {
  local dual_dir="PRisM-RAC_${APP_VERSION}"
  local dual_zip="PRisM-RAC_both.zip"

  rm -rf "$dual_dir"
  mkdir -p "$dual_dir"

  # Die zuvor abgelegten, beschrifteten Kopien einsammeln
  if [[ -d "PRisM-RAC_arm64.app" ]]; then
    cp -R "PRisM-RAC_arm64.app" "$dual_dir/"
  fi
  if [[ -d "PRisM-RAC_x86_64.app" ]]; then
    cp -R "PRisM-RAC_x86_64.app" "$dual_dir/"
  fi

  if [[ ! -d "$dual_dir/PRisM-RAC_arm64.app" || ! -d "$dual_dir/PRisM-RAC_x86_64.app" ]]; then
    echo "⚠️  Für das Kombi-Zip werden beide Apps benötigt. Überspringe."
    rm -rf "$dual_dir"
    return 0
  fi

  echo "[*] Erzeuge Kombi-ZIP mit beiden Apps → $dual_zip"
  /usr/bin/ditto -c -k --sequesterRsrc --keepParent "$dual_dir" "$dual_zip"
  shasum -a 256 "$dual_zip" | awk '{print "  " $1, " ", $2}'
  rm -rf "$dual_dir"
  echo "[ok] Kombi-ZIP erstellt."
}

# --- Build-Flow ---------------------------------------------------------------
case "$ARCH" in
  arm64)
    build_one arm64
    ;;
  x86_64)
    build_one x86_64
    ;;
  both)
    build_one arm64
    build_one x86_64
    make_dual_zip
    ;;
  *)
    echo "❌ Ungültiger Wert für --arch: $ARCH"
    echo "   Erlaubt: arm64 | x86_64 | both"
    exit 2
    ;;
esac

echo "🎉 All done."