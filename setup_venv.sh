#!/usr/bin/env bash
# setup_venv.sh — Erstellt und aktualisiert die virtuelle Umgebung für PRiSM-RAC
# Ausführen mit:
#   bash setup_venv.sh
# oder (nach chmod +x setup_venv.sh):
#   ./setup_venv.sh

set -euo pipefail
cd "$(dirname "$0")"

VENV_DIR=".venv"
REQ_FILE="requirements.txt"

echo "⚙️  PRiSM-RAC Virtual Environment Setup"
echo "--------------------------------------"

# Prüfen, ob Python verfügbar ist
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 ist nicht installiert oder nicht im PATH."
  exit 1
fi

# VENV anlegen, falls nicht vorhanden
if [[ ! -d "$VENV_DIR" ]]; then
  echo "📦 Erstelle virtuelle Umgebung unter $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
else
  echo "✅ Virtuelle Umgebung existiert bereits."
fi

# Aktivieren
source "$VENV_DIR/bin/activate"

# pip & tools aktualisieren
echo "🔄 Aktualisiere pip, setuptools und wheel ..."
pip install --upgrade pip setuptools wheel

# Requirements prüfen und installieren
if [[ -f "$REQ_FILE" ]]; then
  echo "📚 Installiere Requirements aus $REQ_FILE ..."
  pip install --upgrade -r "$REQ_FILE"
else
  echo "⚠️  Keine requirements.txt gefunden. Installiere Basis-Pakete ..."
  pip install --upgrade PySide6 watchdog paramiko certifi keyring pyinstaller
fi

# Abschlussinfo
PYTHON_VER=$(python --version)
PIP_VER=$(pip --version | awk '{print $2}')
echo "✅ Setup abgeschlossen."
echo "   Python: $PYTHON_VER"
echo "   pip: $PIP_VER"
echo "   Umgebungspfad: $VENV_DIR"

echo ""
echo "💡 Hinweis:"
echo "   Um die Umgebung künftig zu aktivieren:"
echo "      source $VENV_DIR/bin/activate"
echo "   oder in PyCharm als Interpreter:"
echo "      $(pwd)/$VENV_DIR/bin/python"