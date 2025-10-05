// In AnalyseLayersAndMetadata.jsx
var DEBUG_OUTPUT = __DEBUG__; // This will be replaced by "true" or "false" from Python

if (DEBUG_OUTPUT) {
    $.writeln("Debug: AnalyseLayersAndMetadata gestartet.");
}

(function(){
    try {
        if (app.documents.length === 0) {
            if (DEBUG_OUTPUT) { alert("Kein Dokument geöffnet."); }
            return JSON.stringify({ error: "No document open" });
        }
        var doc = app.activeDocument;
        if (DEBUG_OUTPUT) { alert("Dokument: " + doc.name); }

        // Initialisiere Ergebnisobjekt (Standard: "no")
        var result = {
            "layers": {
                "Freisteller": "no",
                "Messwerte": "no",
                "Korrektur": "no",
                "Freisteller_Wand": "no",
                "Bildausschnitt": "no"
            },
            "metadata": {
                "author": "no",
                "description": "no",
                "keywords": "no",
                "headline": "no"
            }
        };

        // Funktion zum rekursiven Durchsuchen der Ebenen
        function searchLayers(layers) {
            for (var i = 0; i < layers.length; i++) {
                var layer = layers[i];
                var lname = layer.name.toLowerCase();
                if (layer.typename === "ArtLayer") {
                    if (lname.indexOf("freisteller") !== -1) { result.layers["Freisteller"] = "yes"; }
                    if (lname.indexOf("messwerte") !== -1) { result.layers["Messwerte"] = "yes"; }
                    if (lname.indexOf("korrektur") !== -1) { result.layers["Korrektur"] = "yes"; }
                    if (lname.indexOf("freisteller_wand") !== -1) { result.layers["Freisteller_Wand"] = "yes"; }
                    if (lname.indexOf("bildausschnitt") !== -1) { result.layers["Bildausschnitt"] = "yes"; }
                } else if (layer.typename === "LayerSet") {
                    // Ebenen in Gruppen durchsuchen
                    if (lname.indexOf("freisteller") !== -1) { result.layers["Freisteller"] = "yes"; }
                    if (lname.indexOf("messwerte") !== -1) { result.layers["Messwerte"] = "yes"; }
                    if (lname.indexOf("korrektur") !== -1) { result.layers["Korrektur"] = "yes"; }
                    if (lname.indexOf("freisteller_wand") !== -1) { result.layers["Freisteller_Wand"] = "yes"; }
                    if (lname.indexOf("bildausschnitt") !== -1) { result.layers["Bildausschnitt"] = "yes"; }
                    searchLayers(layer.layers);
                }
            }
        }
        searchLayers(doc.layers);

        // Metadaten prüfen (bei "description" wird zuerst caption geprüft)
        var info = doc.info;
        if (info.author && info.author.toString().length > 0) {
            result.metadata["author"] = "yes";
        }
        if (info.caption && info.caption.toString().length > 0) {
            result.metadata["description"] = "yes";
        } else if (info.description && info.description.toString().length > 0) {
            result.metadata["description"] = "yes";
        }
        if (info.keywords && info.keywords.toString().length > 0) {
            result.metadata["keywords"] = "yes";
        }
        if (info.headline && info.headline.toString().length > 0) {
            result.metadata["headline"] = "yes";
        }

        // Debug-Ausgabe: Zeige gefundene Ebenen und Metadaten
        if (DEBUG_OUTPUT) {
            var debugMsg = "Gefundene Ebenen:\n" +
                           "Freisteller: " + result.layers["Freisteller"] + "\n" +
                           "Messwerte: " + result.layers["Messwerte"] + "\n" +
                           "Korrektur: " + result.layers["Korrektur"] + "\n" +
                           "Freisteller_Wand: " + result.layers["Freisteller_Wand"] + "\n" +
                           "Bildausschnitt: " + result.layers["Bildausschnitt"] + "\n\n" +
                           "Gefundene Metadaten:\n" +
                           "Author: " + result.metadata["author"] + "\n" +
                           "Description: " + result.metadata["description"] + "\n" +
                           "Keywords: " + result.metadata["keywords"] + "\n" +
                           "Headline: " + result.metadata["headline"];
            alert(debugMsg);
        }
        return JSON.stringify(result);
    } catch(e) {
        if (DEBUG_OUTPUT) { alert("Fehler: " + e.message); }
        return JSON.stringify({ error: e.toString() });
    }
})();