#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
from datetime import datetime


def export_log_as_csv(log_entries, output_csv_path):
    """
    Exportiert eine Liste von Log-Einträgen als CSV-Datei.

    Jeder Log-Eintrag ist ein Dictionary mit folgenden Feldern:
      - id: Siebenstellige ID (String, z. B. "0000001")
      - timestamp: Zeitstempel (ISO-Format)
      - filename: Name der Datei (ohne Pfad)
      - metadata: Dictionary mit Schlüsseln wie "author", "description", "keywords", "headline"
      - checkType: z. B. "Standard" oder "Keyword-based"
      - status: z. B. "Success" oder "Fail"
      - applied_script: Name oder Pfad des angewendeten .jsx-Skripts (oder "(none)")
      - details: Ein Dictionary, das z. B. "missingLayers" und "missingMetadata" enthält (als Liste oder String)

    Die CSV-Datei wird mit Semikolon als Delimiter erstellt.
    """
    fieldnames = [
        "ID",
        "Timestamp",
        "Filename",
        "Author",
        "Description",
        "Keywords",
        "Headline",
        "CheckType",
        "Status",
        "AppliedScript",
        "MissingLayers",
        "MissingMetadata"
    ]

    with open(output_csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for entry in log_entries:
            metadata = entry.get("metadata", {})
            details = entry.get("details", {})
            # Falls missingLayers/MissingMetadata Listen sind, in String umwandeln
            missing_layers = details.get("missingLayers", [])
            if isinstance(missing_layers, list):
                missing_layers = ", ".join(missing_layers)
            missing_meta = details.get("missingMetadata", [])
            if isinstance(missing_meta, list):
                missing_meta = ", ".join(missing_meta)
            row = {
                "ID": entry.get("id", ""),
                "Timestamp": entry.get("timestamp", ""),
                "Filename": entry.get("filename", ""),
                "Author": metadata.get("author", ""),
                "Description": metadata.get("description", ""),
                "Keywords": metadata.get("keywords", ""),
                "Headline": metadata.get("headline", ""),
                "CheckType": entry.get("checkType", ""),
                "Status": entry.get("status", ""),
                "AppliedScript": entry.get("applied_script", ""),
                "MissingLayers": missing_layers,
                "MissingMetadata": missing_meta
            }
            writer.writerow(row)


if __name__ == "__main__":
    # Beispiel-Dummy-Daten für den Export
    dummy_log = [
        {
            "id": "0000001",
            "timestamp": datetime.now().isoformat(),
            "filename": "Beispiel.tif",
            "metadata": {
                "author": "Max Mustermann",
                "description": "Testdatei",
                "keywords": "Test, Beispiel",
                "headline": "Testheadline"
            },
            "checkType": "Standard",
            "status": "Success",
            "applied_script": "GRIS_Render_2025.jsx",
            "details": {
                "missingLayers": [],
                "missingMetadata": []
            }
        },
        {
            "id": "0000002",
            "timestamp": datetime.now().isoformat(),
            "filename": "Fehlerdatei.tif",
            "metadata": {
                "author": "RecomArt",
                "description": "Keine Headline",
                "keywords": "742; Rueckseite",
                "headline": "undefined"
            },
            "checkType": "Keyword-based",
            "status": "Fail",
            "applied_script": "(none)",
            "details": {
                "missingLayers": ["Freisteller"],
                "missingMetadata": ["headline"]
            }
        }
    ]
    export_log_as_csv(dummy_log, "global_log_export.csv")