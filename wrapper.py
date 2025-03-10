# wrapper.py
import os
import sys
import importlib
import importlib.util


def main():
    # Debug-Ausgabe hinzufügen
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"[DEBUG] BASE_DIR: {base_dir}")

    config_path = os.path.join(base_dir, "config", "script_config.json")
    print(f"[DEBUG] Script Config File (UNUSED) would be: {config_path}")

    try:
        # Versuche, das main-Modul zu importieren und die run-Funktion auszuführen
        import main
        main.run()
    except Exception as e:
        print(f"Fehler beim Ausführen von main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()