#!/usr/bin/env python3
import os
import shutil
import sys


def post_build():
    # Basis-Verzeichnis des Projekts
    base_dir = os.getcwd()

    # Ziel-App-Bundle
    app_bundle = os.path.join(base_dir, "dist", "PRisM-RAC.app")
    resources_dir = os.path.join(app_bundle, "Contents", "Resources")

    # Stelle sicher, dass das Resources-Verzeichnis existiert
    if not os.path.exists(resources_dir):
        print(f"Fehler: Resources-Verzeichnis nicht gefunden: {resources_dir}")
        return False

    # Stelle sicher, dass das Assets-Verzeichnis im Bundle existiert
    assets_target_dir = os.path.join(resources_dir, "assets")
    os.makedirs(assets_target_dir, exist_ok=True)
    print(f"Assets-Verzeichnis sichergestellt: {assets_target_dir}")

    # Kopiere main.py in das Resources-Verzeichnis
    main_py_source = os.path.join(base_dir, "main.py")
    main_py_target = os.path.join(resources_dir, "main.py")
    if os.path.exists(main_py_source):
        print(f"Kopiere {main_py_source} nach {main_py_target}")
        shutil.copy2(main_py_source, main_py_target)
    else:
        print(f"Warnung: main.py nicht gefunden: {main_py_source}")

    # Kopiere Splash-Screen (Dateiname angepasst)
    splash_source = os.path.join(base_dir, "assets", "CC_PRisM_SplashScreen_600px.png")
    splash_target = os.path.join(assets_target_dir, "CC_PRisM_SplashScreen_600px.png")
    if os.path.exists(splash_source):
        print(f"Kopiere {splash_source} nach {splash_target}")
        shutil.copy2(splash_source, splash_target)
    else:
        print(f"Warnung: Splash-Screen nicht gefunden: {splash_source}")

    # Verschiebe den jsx_templates-Ordner aus Resources in Contents/Frameworks/jsx_templates
    source_jsx_templates = os.path.join(resources_dir, "jsx_templates")
    target_frameworks_dir = os.path.join(app_bundle, "Contents", "Frameworks")
    target_jsx_templates = os.path.join(target_frameworks_dir, "jsx_templates")
    if os.path.exists(source_jsx_templates):
        os.makedirs(target_frameworks_dir, exist_ok=True)
        # Falls der Zielordner schon existiert, entfernen wir ihn (bei symlink: unlink)
        if os.path.exists(target_jsx_templates):
            if os.path.islink(target_jsx_templates):
                os.unlink(target_jsx_templates)
            else:
                shutil.rmtree(target_jsx_templates)
        try:
            shutil.move(source_jsx_templates, target_jsx_templates)
            print(f"jsx_templates wurde erfolgreich nach {target_jsx_templates} verschoben.")
        except Exception as e:
            print(f"Fehler beim Verschieben von jsx_templates: {e}")
            return False
    else:
        print(f"Warnung: jsx_templates-Ordner nicht gefunden in {resources_dir}")

    return True


if __name__ == "__main__":
    if post_build():
        print("Post-Build-Prozess erfolgreich ausgeführt.")
    else:
        print("Post-Build-Prozess fehlgeschlagen.")
        sys.exit(1)