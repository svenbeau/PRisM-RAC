# wrapper.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

def main():
    """
    Diese Funktion ruft das eigentliche 'main.py' auf
    oder eine andere Hauptfunktion deines Programms.
    """
    # Ermitteln, wo sich das entpackte Verzeichnis befindet,
    # wenn wir in einer gefrorenen PyInstaller-Umgebung sind.
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Füge base_path zum sys.path hinzu, damit Python Module aus dem entpackten Verzeichnis findet
    if base_path not in sys.path:
        sys.path.insert(0, base_path)

    # Beispiel: main.py importieren und starten
    try:
        import main
        main.run()  # Falls deine main.py eine Funktion run() o.Ä. hat
    except ImportError as e:
        print("Konnte 'main.py' nicht finden oder importieren.", e)
        sys.exit(1)
    except Exception as ex:
        print("Fehler beim Ausführen von main:", ex)
        sys.exit(2)


if __name__ == '__main__':
    main()