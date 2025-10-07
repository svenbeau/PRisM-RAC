#!/usr/bin/env bash
# choose_arch_and_build.sh
# Robust: findet das erzeugte .app dynamisch und bricht mit klarer Fehlermeldung ab, wenn nichts da ist.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# ── Auswahl Architektur (Default: arm64) ────────────────────────────────────────
ARCH="${1:-arm64}"   # optionaler 1. Parameter: arm64 | x86_64
case "$ARCH" in
  arm64)   DIST_DIR="dist_arm64"; SPEC_FILE="PRisM-RAC_arm64.spec"; ARCH_LABEL="arm64" ;;
  x86_64)  DIST_DIR="dist_x86_64"; SPEC_FILE="PRisM-RAC_x86_64.spec"; ARCH_LABEL="x86_64" ;;
  *)
    echo "❌ Unbekannte Architektur: $ARCH (erlaubt: arm64 | x86_64)"
    exit 2
    ;;
esac

echo "🔧 Auswahl: ${ARCH_LABEL}"

# ── Requirements installieren/aktualisieren ────────────────────────────────────
echo "🧩 Installiere/aktualisiere Requirements…"
if [[ -f "requirements.txt" ]]; then
  pip install -r requirements.txt
else
  echo "⚠️  Keine requirements.txt gefunden – überspringe."
fi

# Version aus VERSION-Datei oder fallback
APP_VERSION="0.0.0"
if [[ -f VERSION ]]; then
  APP_VERSION="$(cat VERSION | tr -d '\n' || true)"
fi
echo "🏷  Version erkannt: ${APP_VERSION}"

# ── Schritt 1: Build mit PyInstaller ───────────────────────────────────────────
echo "🔧 Schritt 1 (${ARCH_LABEL}): Baue App mit PyInstaller"
if [[ ! -f "$SPEC_FILE" ]]; then
  echo "❌ Spec-Datei nicht gefunden: $SPEC_FILE"
  exit 3
fi

# Sauber neu bauen
pyinstaller --clean --distpath "$DIST_DIR" --workpath "build_${ARCH_LABEL}" "$SPEC_FILE"

echo "📦 PyInstaller-Build abgeschlossen."

# ── App-Bundle im DIST-Verzeichnis robust finden ───────────────────────────────
echo "📂 Scanne ${DIST_DIR} nach .app…"
if [[ ! -d "$DIST_DIR" ]]; then
  echo "❌ Dist-Verzeichnis nicht gefunden: ${DIST_DIR}"
  exit 4
fi

# Finde das erste .app, das mit PRisM-RAC beginnt (deckt PRisM-RAC.app, PRisM-RAC-arm64.app, PRisM-RAC-x86_64.app ab)
APP_PATH="$(ls -1d "${DIST_DIR}"/PRisM-RAC*.app 2>/dev/null | head -n 1 || true)"

if [[ -z "${APP_PATH}" ]]; then
  echo "❌ Kein App-Bundle gefunden. Inhalt von ${DIST_DIR}:"
  ls -la "${DIST_DIR}" || true
  exit 5
fi

echo "✅ Gefundenes App-Bundle: ${APP_PATH}"

# Optional: Kompatibilitäts-Symlink auf PRisM-RAC.app anlegen,
# falls nachfolgende Schritte hart auf diesen Namen zeigen.
TARGET_LINK="${DIST_DIR}/PRisM-RAC.app"
if [[ "$(basename "$APP_PATH")" != "PRisM-RAC.app" ]]; then
  echo "🔗 Erzeuge Symlink ${TARGET_LINK} → $(basename "$APP_PATH")"
  ( cd "$DIST_DIR" && ln -sfn "$(basename "$APP_PATH")" "PRisM-RAC.app" )
fi

# ── Schritt 2: Distribution vorbereiten (arbeite ab jetzt mit APP_PATH) ───────
echo "📦 Schritt 2 (${ARCH_LABEL}): Bereite Distribution vor"
# Beispiel: hier könntest du Assets sammeln, Readme kopieren, Zip erstellen etc.
# Nutze immer ${APP_PATH} (oder ${TARGET_LINK}) statt eines fixen Namens!

# Beispiel-Zip (optional, auskommentiert lassen wenn du was anderes machst):
# ZIP_NAME="PRisM-RAC_${APP_VERSION}_${ARCH_LABEL}.zip"
# echo "🗜  Erzeuge ${ZIP_NAME}…"
# (cd "${DIST_DIR}" && /usr/bin/zip -qry "${ZIP_NAME}" "$(basename "${APP_PATH}")")

echo "🎉 Fertig. App liegt unter: ${APP_PATH}"