on run argv
    if (count of argv) < 2 then
        return "Error: Nicht genügend Parameter. Usage: ProcessFile.applescript <filePath> <configPath>"
    end if

    set filePath to item 1 of argv
    set configPath to item 2 of argv

    -- Hier könntest Du den Inhalt der Konfigurationsdatei einlesen, falls benötigt.
    -- Für diesen Beispielansatz nehmen wir an, dass alle nötigen Einstellungen fest im Skript stehen.

    -- Konfigurationen (bitte anpassen)
    set preActionName to "PreAction" -- z. B. den Namen der Photoshop-Aktion, oder leer, falls nicht verwendet
    set preActionFolder to "PreActionFolder" -- Name des Ordners, in dem die Aktion liegt
    set postActionName to "PostAction" -- wie oben für Post-Aktion
    set postActionFolder to "PostActionFolder"
    set processedFolder to "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/02_Succes"
    set errorFolder to "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/03_Fault"
    set jsxScriptPath to "/Users/sschonauer/Documents/PycharmProjects/RACPRiSM/scripts/AnalyseLayersAndMetadata.jsx"

    tell application id "com.adobe.Photoshop"
        activate
        try
            -- Datei öffnen (als alias, da dies in Deinem funktionierenden Code so verwendet wurde)
            set myDoc to open alias filePath
        on error errOpen
            return "Error opening file: " & errOpen
        end try

        delay 4 -- Wartezeit, damit die Datei vollständig geladen wird

        -- Pre-Aktion nur ausführen, wenn definiert
        if preActionName is not "" and preActionFolder is not "" then
            try
                do action preActionName from preActionFolder
            on error errPre
                -- Falls die Aktion nicht verfügbar ist, überspringen
            end try
        end if

        delay 1

        try
            set jsxResult to do javascript file jsxScriptPath in myDoc
        on error errJSX
            set jsxResult to "error: " & errJSX
        end try

        delay 1

        -- Post-Aktion nur ausführen, wenn definiert
        if postActionName is not "" and postActionFolder is not "" then
            try
                do action postActionName from postActionFolder
            on error errPost
                -- Falls nicht verfügbar, überspringen
            end try
        end if

        delay 1
        try
            close myDoc saving no
        end try
    end tell

    -- Evaluation: Wenn das JSX-Ergebnis "error:" enthält, dann verschiebe in Error, ansonsten in Processed
    if jsxResult starts with "error:" then
        do shell script "mv " & quoted form of filePath & " " & quoted form of errorFolder
    else
        do shell script "mv " & quoted form of filePath & " " & quoted form of processedFolder
    end if

    return jsxResult
end run