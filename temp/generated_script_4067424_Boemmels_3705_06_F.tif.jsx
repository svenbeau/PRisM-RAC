// Template für Content-Check JSX Script
// DEBUG_OUTPUT wird vom Generator gesetzt
var DEBUG_OUTPUT = false;

// Hilfsfunktionen für Logging
function debugLog(message) {
    if (DEBUG_OUTPUT) {
        $.writeln("[DEBUG] " + message);
    }
}

function errorLog(message) {
    $.writeln("[ERROR] " + message);
}

function infoLog(message) {
    $.writeln("[INFO] " + message);
}

// Hauptfunktion
function main() {
    try {
        debugLog("Starting content check script");

        // Hier kommt der Rest deines Template-Codes...
        var imagePath = "4067424_Boemmels_3705_06_F.tif";
        var checkSettings = ${CHECK_SETTINGS};
        var outputPath = "${OUTPUT_PATH}";

        debugLog("Image path: " + imagePath);
        debugLog("Check settings: " + JSON.stringify(checkSettings));
        debugLog("Output path: " + outputPath);

        // Weitere Template-Logik...

    } catch(e) {
        errorLog("Error in main function: " + e);
    }
}

// Skript ausführen
main();