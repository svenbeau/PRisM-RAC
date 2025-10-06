#!/usr/bin/env bash
# prepare_app_for_distribution.sh
# Zweck: App-Bundle für interne Verteilung vorbereiten (ohne Developer-ID).
#  - Quarantäne-Attribute entfernen (xattr -cr)
#  - ZIP mit ditto erstellen
#  - Basistests/Checks ausgeben (spctl Assess, codesign-Infos falls vorhanden)
#  - SHA256-Prüfsumme erzeugen

set -euo pipefail

# -----------------------------
# Einstellungen (anpassbar)
# -----------------------------
APP_DEFAULT="dist/PRisM-RAC.app"    # Standardpfad zu deiner App
OUT_DEFAULT="PRisM-RAC.zip"          # Standardname des ZIP-Archivs
KEEP_PARENT="1"                      # 1 => keepParent bei ditto (App bleibt in ZIP als Ordner enthalten)

# -----------------------------
# Farben (nur Kosmetik)
# -----------------------------
RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
BLUE=$'\033[34m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

log()  { echo "${BLUE}[*]${RESET} $*"; }
ok()   { echo "${GREEN}[ok]${RESET} $*"; }
warn() { echo "${YELLOW}[! ]${RESET} $*"; }
err()  { echo "${RED}[xx]${RESET} $*"; }

# -----------------------------
# Usage
# -----------------------------
usage() {
  cat <<EOF
${BOLD}Usage:${RESET} $0 [-a /pfad/zur/App.app] [-o /pfad/zur/Datei.zip] [--no-keep-parent]

Optionen:
  -a, --app PATH        Pfad zum .app-Bundle (Default: ${APP_DEFAULT})
  -o, --out PATH        Ausgabedatei ZIP (Default: ${OUT_DEFAULT})
      --no-keep-parent  ZIP ohne übergeordneten Ordner (ohne --keepParent)

Beispiele:
  $0
  $0 -a "dist/PRisM-CC.app" -o "builds/PRisM-CC_$(date +%Y%m%d).zip"
EOF
}

APP_PATH="${APP_DEFAULT}"
OUT_ZIP="${OUT_DEFAULT}"
KEEP_PARENT_FLAG="--keepParent"

# -----------------------------
# Args parsen
# -----------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -a|--app)
      APP_PATH="${2:-}"; shift 2;;
    -o|--out)
      OUT_ZIP="${2:-}"; shift 2;;
    --no-keep-parent)
      KEEP_PARENT="0"; shift 1;;
    -h|--help)
      usage; exit 0;;
    *)
      err "Unbekannte Option: $1"
      usage; exit 1;;
  esac
done

if [[ "${KEEP_PARENT}" == "0" ]]; then
  KEEP_PARENT_FLAG=""
fi

# -----------------------------
# Vorab-Prüfungen
# -----------------------------
if [[ ! -d "${APP_PATH}" ]]; then
  err "App-Bundle nicht gefunden: ${APP_PATH}"
  exit 1
fi

# ditto vorhanden?
if ! command -v ditto >/dev/null 2>&1; then
  err "ditto nicht gefunden (macOS-Tool). Xcode Command Line Tools installieren: xcode-select --install"
  exit 1
fi

# spctl vorhanden? (normalerweise ja)
if ! command -v spctl >/dev/null 2>&1; then
  warn "spctl nicht gefunden – Überspringe Gatekeeper-Assessment."
fi

# -----------------------------
# Schritt 1: Quarantäne entfernen
# -----------------------------
log "Entferne Quarantäne-Attribute (xattr -cr) von: ${APP_PATH}"
if xattr -lr "${APP_PATH}" >/dev/null 2>&1; then
  xattr -cr "${APP_PATH}" || true
fi
ok "Quarantäne entfernt."

# -----------------------------
# Schritt 2: Basis-Check (optional)
# -----------------------------
if command -v spctl >/dev/null 2>&1; then
  log "Gatekeeper-Assessment (spctl) ausführen…"
  if spctl --assess --type execute --verbose "${APP_PATH}"; then
    ok "spctl Assessment: bestanden (Hinweis: ohne Notarisierung kann beim ersten Start dennoch ein Dialog erscheinen)."
  else
    warn "spctl Assessment hat Bedenken gemeldet (erwartbar ohne Signierung/Notarisierung). Rechtsklick→Öffnen löst das auf Zielsystemen."
  fi
fi

# codesign-Infos (falls signiert oder Teilkomponenten signiert)
if command -v codesign >/dev/null 2>&1; then
  log "Codesign-Infos (nur informativ):"
  if ! codesign --display --verbose=4 "${APP_PATH}" 2>/dev/null; then
    warn "App scheint nicht signiert (ist okay für interne Verteilung)."
  fi
fi

# -----------------------------
# Schritt 3: ZIP erstellen
# -----------------------------
# Zielordner vorbereiten
OUT_DIR="$(dirname "${OUT_ZIP}")"
mkdir -p "${OUT_DIR}"

# Falls ZIP existiert -> überschreiben
if [[ -f "${OUT_ZIP}" ]]; then
  warn "Bestehende ZIP wird überschrieben: ${OUT_ZIP}"
  rm -f "${OUT_ZIP}"
fi

log "Erstelle ZIP mit ditto: ${OUT_ZIP}"
if [[ -n "${KEEP_PARENT_FLAG}" ]]; then
  ditto -c -k ${KEEP_PARENT_FLAG} "${APP_PATH}" "${OUT_ZIP}"
else
  ditto -c -k "${APP_PATH}" "${OUT_ZIP}"
fi
ok "ZIP erstellt: ${OUT_ZIP}"

# -----------------------------
# Schritt 4: Prüfsummen ausgeben
# -----------------------------
if command -v shasum >/dev/null 2>&1; then
  log "SHA256 für ZIP:"
  shasum -a 256 "${OUT_ZIP}" | awk '{print "  "$1"  "$2}'
fi

# -----------------------------
# Schritt 5: Kurzanleitung für Zielsystem
# -----------------------------
cat <<EOT

${BOLD}Distribution-Hinweise (ohne Developer-ID):${RESET}

1) ZIP an Ziel-Mac übertragen und entpacken.
2) Beim ersten Start eventuell:
   - Rechtsklick auf die App → "Öffnen" → Hinweis bestätigen.
   - Oder in Terminal:   xattr -cr "/Pfad/zu/$(basename "${APP_PATH}")"
3) Netzwerkzugriffe (FTP/SMTP) werden ggf. von der Firewall einmalig nachgefragt → "Zulassen".

Fertig. Viel Erfolg!
EOT

ok "Fertig."