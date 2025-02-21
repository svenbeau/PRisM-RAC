// contentcheck_template.jsx

// Lade die Adobe XMPScript Library, falls noch nicht geladen
if (ExternalObject.AdobeXMPScript == undefined) {
    ExternalObject.AdobeXMPScript = new ExternalObject("lib:AdobeXMPScript");
}

if (typeof Array.isArray !== "function") {
    Array.isArray = function(arg) {
        return Object.prototype.toString.call(arg) === "[object Array]";
    };
}

var DEBUG_OUTPUT = true;

function debug_print(msg) {
    if (DEBUG_OUTPUT) {
        $.writeln("[DEBUG] " + msg);
    }
}

// Platzhalter – diese Werte werden von Python ersetzt:
var requiredLayers = /*PYTHON_INSERT_LAYERS*/;
var requiredMetadata = /*PYTHON_INSERT_METADATA*/;
var logFolderPath = "/*PYTHON_INSERT_LOGFOLDER*/";

// Entfernt ggf. umgebende Anführungszeichen
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
    "documentTitle":  "Title",
    "author":         "Author",
    "description":    "Description",
    "keywords":       "Keywords",
    "headline":       "Headline",
    "authorPosition": "Author Position",
    "descriptionWriter": "Description Writer",
    "copyrightNotice": "Copyright Notice",
    "copyrightURL":   "Copyright URL",
    "city":           "City",
    "stateProvince":  "State/Province",
    "country":        "Country",
    "creditLine":     "Credit Line",
    "source":         "Source",
    "instructions":   "Instructions",
    "transmissionRef": "Transmission Ref"
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
    val = removeSurroundingQuotes(val);
    return val;
}

// Hole die XMP-Daten des aktiven Dokuments
if (app.documents.length === 0) {
    alert("Keine Datei geöffnet. Bitte öffne eine Datei und starte das Skript erneut.");
    throw new Error("Kein Dokument geöffnet");
}
var doc = app.activeDocument;
var xmpData = doc.xmpMetadata.rawData;
var xmp = new XMPMeta(xmpData);

// Erzeuge ein Objekt, das alle Felder enthält:
var metadataOutput = {};
for (var key in fieldMapping) {
    metadataOutput[key] = getXMPValue(key);
}

// Erzeuge die Ausgabe nur für die in requiredMetadata ausgewählten Felder:
var output = "";
for (var i = 0; i < requiredMetadata.length; i++) {
    var key = requiredMetadata[i];
    var label = userFriendlyLabels[key] || key;
    output += label + ": " + metadataOutput[key] + "\n";
}

alert(output);
debug_print("Ausgabe:\n" + output);

// Erzeuge JSON-Log
function serializeToJson(obj) {
    var json = "{";
    for (var key in obj) {
        if (obj.hasOwnProperty(key)) {
            var value = obj[key];
            if (typeof value === "object" && value !== null) {
                json += '"' + key + '":' + serializeToJson(value) + ",";
            } else if (typeof value === "string") {
                json += '"' + key + '":"' + value.replace(/"/g, '\\"') + '",';
            } else {
                json += '"' + key + '":' + value + ",";
            }
        }
    }
    json = json.replace(/,$/, "") + "}";
    return json;
}

var jsonLog = serializeToJson({ metadata: metadataOutput });
var logFile = new File(logFolderPath + "/" + doc.name.replace(/\.[^\.]+$/, "") + "_log_contentcheck.json");
logFile.encoding = "UTF8";
logFile.open("w");
logFile.write(jsonLog);
logFile.close();
debug_print("Contentcheck-Log gespeichert: " + logFile.fullName);