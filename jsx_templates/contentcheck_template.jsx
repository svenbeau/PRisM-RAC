// contentcheck_template.jsx

// Lade die Adobe XMPScript Library, falls noch nicht geladen
if (ExternalObject.AdobeXMPScript == undefined) {
    ExternalObject.AdobeXMPScript = new ExternalObject("lib:AdobeXMPScript");
}

// Polyfill für Array.isArray
if (typeof Array.isArray !== "function") {
    Array.isArray = function(arg) {
        return Object.prototype.toString.call(arg) === "[object Array]";
    };
}

// Polyfill für JSON.stringify, falls nicht definiert
if (typeof JSON === "undefined") {
    JSON = {};
    JSON.stringify = function(obj) {
        function serialize(obj) {
            if (typeof obj === "object") {
                var s = "{";
                for (var key in obj) {
                    if (obj.hasOwnProperty(key)) {
                        var val = obj[key];
                        if (typeof val === "object" && val !== null) {
                            s += '"' + key + '":' + serialize(val) + ",";
                        } else if (typeof val === "string") {
                            s += '"' + key + '":"' + val.replace(/"/g, '\\"') + '",';
                        } else {
                            s += '"' + key + '":' + val + ",";
                        }
                    }
                }
                s = s.replace(/,$/, "") + "}";
                return s;
            }
            return obj.toString();
        }
        return serialize(obj);
    };
}

// Pretty Print Funktion für JSON
function serializeToJsonPretty(obj, indent) {
    indent = indent || "";
    if (typeof obj !== "object" || obj === null) {
        if (typeof obj === "string") {
            return '"' + obj.replace(/"/g, '\\"') + '"';
        } else {
            return String(obj);
        }
    }
    var isArray = Array.isArray(obj);
    var result = isArray ? "[\n" : "{\n";
    var indentNext = indent + "    ";
    var first = true;
    for (var key in obj) {
        if (obj.hasOwnProperty(key)) {
            if (!first) {
                result += ",\n";
            }
            first = false;
            if (!isArray) {
                result += indentNext + '"' + key + '": ';
            } else {
                result += indentNext;
            }
            result += serializeToJsonPretty(obj[key], indentNext);
        }
    }
    result += "\n" + indent + (isArray ? "]" : "}");
    return result;
}

// Globaler Debug-Schalter – wird von außen injiziert, falls vorhanden.
if (typeof DEBUG_OUTPUT === "undefined") {
    var DEBUG_OUTPUT = true;
}

function debug_print(msg) {
    if (DEBUG_OUTPUT) {
        $.writeln("[DEBUG] " + msg);
    }
}

// Platzhalter – diese Werte werden von Python ersetzt:
var requiredLayers = ["Freisteller", "Messwerte", "Korrektur", "Freisteller_Wand", "Bildausschnitt"];
var requiredMetadata = ["author", "description", "keywords", "headline"];
var logFolderPath = "/Users/sschonauer/Documents/Jobs/Grisebach/Entwicklung_Workflow/04_Logfiles";

// NEUE PLACEHOLDER für den Check-Typ:
var keywordCheckEnabled = false;  // Wird von Python ersetzt, z.B. true
var keywordCheckWord = "";        // Wird von Python ersetzt, z.B. "Rueckseite"

// Zunächst setzen wir checkType standardmäßig auf "Standard"
var checkType = "Standard";

// Funktion zum Entfernen umgebender Anführungszeichen
function removeSurroundingQuotes(str) {
    if (!str || str.length < 2) return str;
    if (str.charAt(0) === '"' && str.charAt(str.length - 1) === '"') {
        return str.substring(1, str.length - 1);
    }
    return str;
}

// Feld-Mapping – Keys entsprechen der gewünschten Zuordnung.
var fieldMapping = {
    "documentTitle":    { ns: XMPConst.NS_DC, prop: "title", altText: true,  isArray: false },
    "author":           { ns: XMPConst.NS_DC, prop: "creator", altText: false, isArray: true  },
    "authorPosition":   { ns: XMPConst.NS_PHOTOSHOP, prop: "AuthorsPosition", altText: false, isArray: false },
    "description":      { ns: XMPConst.NS_DC, prop: "description", altText: true,  isArray: false },
    "descriptionWriter":{ ns: XMPConst.NS_PHOTOSHOP, prop: "CaptionWriter", altText: false, isArray: false },
    "keywords":         { ns: XMPConst.NS_DC, prop: "subject", altText: false, isArray: true  },
    "copyrightNotice":  { ns: XMPConst.NS_DC, prop: "rights", altText: true,  isArray: false },
    "copyrightURL":     { ns: "http://ns.adobe.com/xap/1.0/rights/", prop: "WebStatement", altText: false, isArray: false },
    "city":             { ns: XMPConst.NS_PHOTOSHOP, prop: "City", altText: false, isArray: false },
    "stateProvince":    { ns: XMPConst.NS_PHOTOSHOP, prop: "State", altText: false, isArray: false },
    "country":          { ns: XMPConst.NS_PHOTOSHOP, prop: "Country", altText: false, isArray: false },
    "creditLine":       { ns: XMPConst.NS_PHOTOSHOP, prop: "Credit", altText: false, isArray: false },
    "source":           { ns: XMPConst.NS_PHOTOSHOP, prop: "Source", altText: false, isArray: false },
    "headline":         { ns: XMPConst.NS_PHOTOSHOP, prop: "Headline", altText: false, isArray: false },
    "instructions":     { ns: XMPConst.NS_PHOTOSHOP, prop: "Instructions", altText: false, isArray: false },
    "transmissionRef":  { ns: XMPConst.NS_PHOTOSHOP, prop: "TransmissionReference", altText: false, isArray: false }
};

// Benutzerfreundliche Labels für die Anzeige
var userFriendlyLabels = {
    "documentTitle":    "Title",
    "author":           "Author",
    "description":      "Description",
    "keywords":         "Keywords",
    "headline":         "Headline",
    "authorPosition":   "Author Position",
    "descriptionWriter":"Description Writer",
    "copyrightNotice":  "Copyright Notice",
    "copyrightURL":     "Copyright URL",
    "city":             "City",
    "stateProvince":    "State/Province",
    "country":          "Country",
    "creditLine":       "Credit Line",
    "source":           "Source",
    "instructions":     "Instructions",
    "transmissionRef":  "Transmission Ref"
};

// Funktion zum Auslesen eines Feldes gemäß Mapping
function getXMPValue(fieldKey) {
    var mapping = fieldMapping[fieldKey];
    if (!mapping) {
        return "undefined";
    }
    var val = "";
    if (mapping.isArray) {
        try {
            var count = 1;
            try {
                count = xmp.countArrayItems(mapping.ns, mapping.prop);
            } catch(e) {
                count = 1;
            }
            var items = [];
            for (var i = 1; i <= count; i++) {
                try {
                    var item = xmp.getArrayItem(mapping.ns, mapping.prop, i);
                    if (item && item.value) {
                        items.push(String(item.value));
                    }
                } catch(e) {}
            }
            if (items.length > 0) {
                // Verbinde alle Einträge mit Semikolon
                val = items.join("; ");
            }
        } catch(e) {
            val = "undefined";
        }
    } else {
        if (mapping.altText) {
            try {
                var loc = xmp.getLocalizedText(mapping.ns, mapping.prop, "", "x-default");
                if (loc && loc.value) {
                    val = String(loc.value);
                }
            } catch(e) {}
        }
        if (!val) {
            try {
                var raw = xmp.getProperty(mapping.ns, mapping.prop);
                if (raw) {
                    val = String(raw);
                }
            } catch(e) {}
        }
    }
    if (!val) {
        val = "undefined";
    }
    return removeSurroundingQuotes(val);
}

// Sicherstellen, dass ein Dokument geöffnet ist
if (app.documents.length === 0) {
    alert("Keine Datei geöffnet. Bitte öffne eine Datei und starte das Skript erneut.");
    throw new Error("Kein Dokument geöffnet");
}
var doc = app.activeDocument;
var xmpData = doc.xmpMetadata.rawData;
var xmp = new XMPMeta(xmpData);

// Erzeuge ein Objekt, das alle Felder enthält (basierend auf fieldMapping)
var metadataOutput = {};
for (var key in fieldMapping) {
    metadataOutput[key] = getXMPValue(key);
}

// Keyword-Check: Falls keywordCheckEnabled true ist und ein Suchbegriff definiert,
if (keywordCheckEnabled && keywordCheckWord !== "") {
    // Teile den keywords-String anhand des Semikolons auf.
    var tags = metadataOutput["keywords"].split(";");
    var found = false;
    for (var i = 0; i < tags.length; i++) {
        if (tags[i].trim().toLowerCase() === keywordCheckWord.toLowerCase()) {
            found = true;
            break;
        }
    }
    if (found) {
        checkType = "Keyword-based";
    } else {
        checkType = "Standard";
    }
} else {
    checkType = "Standard";
}

// Erzeuge formatierten Output für die ausgewählten Metadaten
var formattedMeta = "Metadata Output:\n";
for (var i = 0; i < requiredMetadata.length; i++) {
    var key = requiredMetadata[i];
    var label = userFriendlyLabels[key] || key;
    formattedMeta += label + ": " + metadataOutput[key] + "\n";
}

// Erzeuge formatierten Output für die Ebenen
var formattedLayers = "Layer Output:\n";
for (var i = 0; i < requiredLayers.length; i++) {
    var lname = requiredLayers[i];
    formattedLayers += lname + ": " + (layerExists(doc, lname) ? "yes" : "NO") + "\n";
}

// Funktion, um zu prüfen, ob eine Ebene im Dokument existiert
function layerExists(doc, layerName) {
    function searchLayers(layers, name) {
        for (var i = 0; i < layers.length; i++) {
            var layer = layers[i];
            if (layer.name === name) {
                return true;
            }
            if (layer.typename === "LayerSet") {
                if (searchLayers(layer.layers, name)) {
                    return true;
                }
            }
        }
        return false;
    }
    return searchLayers(doc.layers, layerName);
}

// Ausgabe des Alerts im alten Layout (nur Metadaten und Ebenen)
if (DEBUG_OUTPUT === true) {
    alert(formattedMeta + "\n\n" + formattedLayers);
}

// Erstelle das finale Objekt für die JSON-Ausgabe
var resultObj = {
    metadata: metadataOutput,
    details: {
        layers: {},
        missingLayers: [],
        missingMetadata: [],
        layerStatus: "OK",
        metaStatus: "OK",
        checkType: checkType
    }
};

// Prüfe fehlende Ebenen
for (var i = 0; i < requiredLayers.length; i++) {
    var lname = requiredLayers[i];
    var present = layerExists(doc, lname);
    resultObj.details.layers[lname] = present ? "yes" : "no";
    if (!present) {
        resultObj.details.missingLayers.push(lname);
        resultObj.details.layerStatus = "FAIL";
    }
}

// Prüfe fehlende Metadaten
for (var j = 0; j < requiredMetadata.length; j++) {
    var field = requiredMetadata[j];
    if (metadataOutput[field] === "undefined") {
        resultObj.details.missingMetadata.push(field);
        resultObj.details.metaStatus = "FAIL";
    }
}

// Erzeuge den kompletten Contentcheck-Log (Pretty Print)
var jsonString = serializeToJsonPretty(resultObj, "");
var baseName = doc.name.replace(/\.[^\.]+$/, "");
var contentLogFile = new File(logFolderPath + "/" + baseName + "_01_log_contentcheck.json");
contentLogFile.encoding = "UTF8";
contentLogFile.open("w");
contentLogFile.write(jsonString);
contentLogFile.close();

debug_print("Contentcheck-Log gespeichert: " + contentLogFile.fullName);

// Falls layerStatus oder metaStatus FAIL, zusätzlich einen Fail-Log erzeugen,
// der nur die fehlenden Kriterien enthält.
if (resultObj.details.layerStatus === "FAIL" || resultObj.details.metaStatus === "FAIL") {
    var missingLayersObj = {};
    for (var i = 0; i < resultObj.details.missingLayers.length; i++) {
        var layer = resultObj.details.missingLayers[i];
        missingLayersObj[layer] = "fehlt";
    }
    var missingMetadataObj = {};
    for (var j = 0; j < resultObj.details.missingMetadata.length; j++) {
        var field = resultObj.details.missingMetadata[j];
        missingMetadataObj[field] = "fehlt";
    }
    var failObj = {
        missingLayers: missingLayersObj,
        missingMetadata: missingMetadataObj,
        layerStatus: resultObj.details.layerStatus,
        metaStatus: resultObj.details.metaStatus,
        checkType: checkType
    };
    var failJsonString = serializeToJsonPretty(failObj, "");
    var failLogFile = new File(logFolderPath + "/" + baseName + "_01_log_fail.json");
    failLogFile.encoding = "UTF8";
    failLogFile.open("w");
    failLogFile.write(failJsonString);
    failLogFile.close();
    debug_print("Contentcheck-Fail Log gespeichert: " + failLogFile.fullName);
}