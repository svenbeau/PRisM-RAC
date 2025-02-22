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

// Globaler Debug-Schalter
// Wichtig: Wir setzen DEBUG_OUTPUT _nicht_ neu, wenn er bereits definiert ist (z. B. von Python).
// Dadurch wird der von außen injizierte Wert (true oder false) beibehalten.
if (typeof DEBUG_OUTPUT === "undefined") {
    var DEBUG_OUTPUT = true; // Standardwert, falls nichts von außen übergeben wird
}

function debug_print(msg) {
    if (DEBUG_OUTPUT) {
        $.writeln("[DEBUG] " + msg);
    }
}

// Platzhalter – diese Werte werden von Python ersetzt:
var requiredLayers = /*PYTHON_INSERT_LAYERS*/;
var requiredMetadata = /*PYTHON_INSERT_METADATA*/;
var logFolderPath = "/*PYTHON_INSERT_LOGFOLDER*/";

// Funktion zum Entfernen umgebender Anführungszeichen
function removeSurroundingQuotes(str) {
    if (!str || str.length < 2) return str;
    if (str.charAt(0) === '"' && str.charAt(str.length - 1) === '"') {
        return str.substring(1, str.length - 1);
    }
    return str;
}

// Feld-Mapping – Keys entsprechen der gewünschten Zuordnung. Wichtig: "headline" statt "psHeadline".
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
            var item = xmp.getArrayItem(mapping.ns, mapping.prop, 1);
            if (item && item.value) {
                val = String(item.value);
            }
        } catch(e) {}
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

// Erzeuge die Ausgabe nur für die in requiredMetadata ausgewählten Felder
var output = "";
for (var i = 0; i < requiredMetadata.length; i++) {
    var key = requiredMetadata[i];
    var label = userFriendlyLabels[key] || key;
    output += label + ": " + metadataOutput[key] + "\n";
}

// Erzeuge formatierten Output für alle benutzerfreundlichen Metadatenfelder
var formattedMeta = "Metadata Output:\n";
for (var key in userFriendlyLabels) {
    var label = userFriendlyLabels[key];
    var value = (metadataOutput[key] !== undefined) ? metadataOutput[key] : "undefined";
    formattedMeta += label + ": " + value + "\n";
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

// Erzeuge formatierten Output für die Ebenen, basierend auf requiredLayers
var formattedLayers = "Layer Output:\n";
for (var i = 0; i < requiredLayers.length; i++) {
    var lname = requiredLayers[i];
    formattedLayers += lname + ": " + (layerExists(doc, lname) ? "yes" : "no") + "\n";
}

// Debug-Ausgaben: Immer in die Konsole schreiben und Alert-Dialog nur, wenn DEBUG_OUTPUT exakt true ist.
debug_print(formattedMeta);
debug_print(formattedLayers);
if (DEBUG_OUTPUT === true) {
    alert(formattedMeta + "\n\n" + formattedLayers);
}

var resultObj = {
    metadata: metadataOutput,
    details: { layers: {} }
};
for (var i = 0; i < requiredLayers.length; i++) {
    var lname = requiredLayers[i];
    resultObj.details.layers[lname] = layerExists(doc, lname) ? "yes" : "no";
}

// Funktion zur Serialisierung in JSON-Format
function serializeToJson(obj) {
    var s = "{";
    for (var key in obj) {
        if (obj.hasOwnProperty(key)) {
            var val = obj[key];
            if (typeof val === "object" && val !== null) {
                s += '"' + key + '":' + serializeToJson(val) + ",";
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

var jsonString = serializeToJson({ metadata: metadataOutput });
var logFile = new File(logFolderPath + "/" + doc.name.replace(/\.[^\.]+$/, "") + "_log_contentcheck.json");
logFile.encoding = "UTF8";
logFile.open("w");
logFile.write(jsonString);
logFile.close();

debug_print("Contentcheck-Log gespeichert: " + logFile.fullName);