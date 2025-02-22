# PRisM-RAC
PRisM-RAC ist eine integrierte Workflow-Lösung, die einen automatisierten Prozess zur Verarbeitung von Bilddateien mithilfe von Adobe Photoshop realisiert. Im Kern überwacht das System spezifizierte “Hotfolder” auf neu eingehende Dateien. Sobald eine Datei in einem dieser Ordner erkannt wird, führt das Projekt mehrere Schritte durch:
	1.	Überwachung und Stabilitätsprüfung:
Das System überwacht den definierten Hotfolder kontinuierlich (unter Verwendung von Watchdog oder ähnlichen Mechanismen) und wartet, bis eine Datei vollständig kopiert wurde – also ihre Größe über mehrere Messungen stabil ist.
	2.	Öffnen in Photoshop und Ausführen von JSX-Skripten:
Nach der Stabilitätsprüfung wird die Datei in Photoshop geöffnet. Anschließend wird ein dynamisch generiertes JSX-Skript ausgeführt, das einen sogenannten Contentcheck durchführt. Dieses Skript liest die Metadaten (wie Autor, Beschreibung, Keywords, etc.) sowie die Struktur der Ebenen des Dokuments aus und vergleicht diese mit vordefinierten Kriterien.
	3.	Inhaltliche Überprüfung:
Mithilfe eines umfangreichen Feldmappings werden sowohl die erforderlichen Ebenen als auch spezifische Metadatenfelder (und bei Bedarf auch keyword-basierte Prüfungen) kontrolliert. Das Skript erzeugt eine JSON-Struktur, in der alle gefundenen Metadaten und Ebenen festgehalten werden. Anhand dieser Ergebnisse entscheidet das System, ob die Datei alle Anforderungen erfüllt.
	4.	Logfile-Generierung und Dateiverwaltung:
Je nach Ergebnis des Contentchecks wird die Datei entweder in einen Success-Ordner verschoben oder, falls Kriterien nicht erfüllt sind, in einen Fault-Ordner. Gleichzeitig wird ein detailliertes Logfile im JSON-Format erstellt, das sämtliche Ergebnisse der Metadaten- und Ebenenprüfung enthält. Diese Logfiles ermöglichen es, die Verarbeitung nachvollziehbar zu dokumentieren und bei Bedarf Fehler zu analysieren.
	5.	Konfigurierbare Benutzeroberfläche:
Eine grafische Benutzeroberfläche (UI) erlaubt es dem Anwender, alle relevanten Einstellungen – etwa die Pfade der Hotfolder, die zu prüfenden Ebenen und Metadaten sowie Optionen für zusätzliche JSX-Skripte – anzupassen. Diese Konfiguration wird persistent in einer JSON-Datei (settings.json) gespeichert, sodass Einstellungen auch über Neustarts hinweg erhalten bleiben. Außerdem können Debug-Optionen ein- und ausgeschaltet werden, um den Prozess zu überwachen und Probleme zu diagnostizieren.
	6.	Dynamische Skriptgenerierung und Debugging:
Das System beinhaltet einen Mechanismus, der dynamisch JSX-Skripte generiert, die in Photoshop ausgeführt werden. Dabei wird darauf geachtet, dass der Debug-Modus (via globalem DEBUG_OUTPUT-Schalter) korrekt funktioniert – das heißt, es werden Debug-Ausgaben in die Konsole geschrieben und, falls aktiviert, auch Alert-Dialoge angezeigt. So wird sichergestellt, dass während der automatisierten Verarbeitung keine ungewollten Dialoge erscheinen, wenn der Debug-Modus ausgeschaltet ist.

Kurz zusammengefasst:
	•	Automatisierte Überwachung: Das System erkennt neue Dateien in definierten Ordnern und startet die Verarbeitung automatisch.
	•	Inhaltliche Prüfung: Über JSX-Skripte in Photoshop werden Metadaten und Ebenen der Datei kontrolliert.
	•	Fehlerbehandlung und Logging: Je nach Prüfungsergebnis wird die Datei in Success oder Fault verschoben und ein detailliertes Logfile erstellt.
	•	Benutzerkonfiguration: Eine UI ermöglicht es, alle relevanten Einstellungen und Prüfparameter individuell anzupassen und zu speichern.
	•	Dynamische Skriptgenerierung und Debugging: Durch dynamische Generierung der JSX-Skripte und einen konfigurierbaren Debug-Modus wird ein flexibler und nachvollziehbarer Prozess sichergestellt.

Diese Lösung zielt darauf ab, den Arbeitsablauf im Grafikbereich zu automatisieren, indem sie Photoshop in den Prozess integriert, um eine zuverlässige Prüfung und Verarbeitung von Bilddateien zu gewährleisten.