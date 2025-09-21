// contentcheck_template.jsx

// Polyfill für String.prototype.trim
if (typeof String.prototype.trim !== "function") {
    String.prototype.trim = function() {
        return this.replace(/^\s+|\s+$/g, "");
    };
}

// Adobe XMPScript laden
if (ExternalObject.AdobeXMPScript == undefined) {
    ExternalObject.AdobeXMPScript = new ExternalObject("lib:AdobeXMPScript");
}

// --- Von Python zu injizierende Variablen (Platzhalter!) ---
var required_layers = /*PYTHON_INSERT_REQUIRED_LAYERS*/;
if (!required_layers || required_layers === "") { required_layers = []; }

var required_metadata = /*PYTHON_INSERT_REQUIRED_METADATA*/;
if (!required_metadata || required_metadata === "") { required_metadata = []; }

var keyword_layers = /*PYTHON_INSERT_KEYWORD_LAYERS*/;
if (!keyword_layers || keyword_layers === "") { keyword_layers = []; }

var keyword_metadata = /*PYTHON_INSERT_KEYWORD_METADATA*/;
if (!keyword_metadata || keyword_metadata === "") { keyword_metadata = []; }

var logFolderPath = /*PYTHON_INSERT_LOGFOLDER*/;
if (!logFolderPath || logFolderPath === "") {
    logFolderPath = Folder.desktop.fsName; // defensiver Fallback
}

// Polyfills
if (typeof Array.isArray !== "function") {
    Array.isArray = function(arg) { return Object.prototype.toString.call(arg) === "[object Array]"; };
}
if (typeof JSON === "undefined") {
    JSON = {};
    JSON.stringify = function(obj) {
        function serialize(o) {
            if (typeof o === "object") {
                var s = "{";
                for (var k in o) if (o.hasOwnProperty(k)) {
                    var v = o[k];
                    if (typeof v === "object" && v !== null) {
                        s += '"' + k + '":' + serialize(v) + ",";
                    } else if (typeof v === "string") {
                        s += '"' + k + '":"' + v.replace(/"/g, '\\"') + '",';
                    } else {
                        s += '"' + k + '":' + v + ",";
                    }
                }
                s = s.replace(/,$/, "") + "}";
                return s;
            }
            return o.toString();
        }
        return serialize(obj);
    };
}

// Pretty JSON
function serializeToJsonPretty(obj, indent) {
    indent = indent || "";
    if (typeof obj !== "object" || obj === null) {
        return (typeof obj === "string") ? '"' + obj.replace(/"/g, '\\"') + '"' : String(obj);
    }
    var isArray = Array.isArray(obj);
    var out = isArray ? "[\n" : "{\n";
    var indentNext = indent + "    ";
    var first = true;
    for (var key in obj) if (obj.hasOwnProperty(key)) {
        if (!first) out += ",\n";
        first = false;
        if (!isArray) out += indentNext + '"' + key + '": ';
        else out += indentNext;
        out += serializeToJsonPretty(obj[key], indentNext);
    }
    out += "\n" + indent + (isArray ? "]" : "}");
    return out;
}

// Debug
if (typeof DEBUG_OUTPUT === "undefined") { var DEBUG_OUTPUT = false; }
function debug_print(msg) { if (DEBUG_OUTPUT) { $.writeln("[DEBUG] " + msg); } }

// Standardwerte nur falls NICHT injiziert
var requiredLayers = required_layers;
var requiredMetadata = required_metadata;

// Check-Typ
var checkType = "Standard";

function removeSurroundingQuotes(str) {
    if (!str || str.length < 2) return str;
    if (str.charAt(0) === '"' && str.charAt(str.length - 1) === '"') {
        return str.substring(1, str.length - 1);
    }
    return str;
}

// Feld-Mapping
var fieldMapping = {
    "documentTitle":    { ns: XMPConst.NS_DC, prop: "title", altText: true, isArray: false },
    "author":           { ns: XMPConst.NS_DC, prop: "creator", altText: false, isArray: true },
    "authorPosition":   { ns: XMPConst.NS_PHOTOSHOP, prop: "AuthorsPosition", altText: false, isArray: false },
    "description":      { ns: XMPConst.NS_DC, prop: "description", altText: true, isArray: false },
    "descriptionWriter":{ ns: XMPConst.NS_PHOTOSHOP, prop: "CaptionWriter", altText: false, isArray: false },
    "keywords":         { ns: XMPConst.NS_DC, prop: "subject", altText: false, isArray: true },
    "copyrightNotice":  { ns: XMPConst.NS_DC, prop: "rights", altText: true, isArray: false },
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

// Labels
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

// XMP lesen
if (app.documents.length === 0) {
    alert("Keine Datei geöffnet. Bitte öffne eine Datei und starte das Skript erneut.");
    throw new Error("Kein Dokument geöffnet");
}
var doc = app.activeDocument;
var xmpData = doc.xmpMetadata.rawData;
var xmp = new XMPMeta(xmpData);

// XMP Value Helper
function getXMPValue(fieldKey) {
    var mapping = fieldMapping[fieldKey];
    if (!mapping) return "undefined";
    var val = "";
    if (mapping.isArray) {
        try {
            var count = 1;
            try { count = xmp.countArrayItems(mapping.ns, mapping.prop); } catch(e) { count = 1; }
            var items = [];
            for (var i = 1; i <= count; i++) {
                try {
                    var item = xmp.getArrayItem(mapping.ns, mapping.prop, i);
                    if (item && item.value) { items.push(String(item.value)); }
                } catch(e) {}
            }
            if (items.length > 0) { val = items.join("; "); }
        } catch(e) { val = "undefined"; }
    } else {
        if (mapping.altText) {
            try {
                var loc = xmp.getLocalizedText(mapping.ns, mapping.prop, "", "x-default");
                if (loc && loc.value) { val = String(loc.value); }
            } catch(e) {}
        }
        if (!val) {
            try {
                var raw = xmp.getProperty(mapping.ns, mapping.prop);
                if (raw) { val = String(raw); }
            } catch(e) {}
        }
    }
    if (!val) val = "undefined";
    return removeSurroundingQuotes(val);
}

// Alle Metadaten auslesen
var metadataOutput = {};
for (var k in fieldMapping) {
    metadataOutput[k] = getXMPValue(k);
}

// --- Keyword-Entscheidung ---
var keywordCheckEnabled = /*PYTHON_INSERT_KW_ENABLED*/;    // true/false
var keywordCheckWord    = /*PYTHON_INSERT_KW_WORD*/;       // "Rueckseite" o.ä.

var decidedKW = "Standard";
if (keywordCheckEnabled && keywordCheckWord && keywordCheckWord !== "") {
    var kwStr = String(metadataOutput["keywords"]);
    var tags = kwStr.split(";");
    var found = false;
    for (var i = 0; i < tags.length; i++) {
        if (String(tags[i]).trim().toLowerCase() === String(keywordCheckWord).toLowerCase()) { found = true; break; }
    }
    decidedKW = found ? "Keyword-based" : "Standard";
}
checkType = decidedKW;

// Effektive Kriterien wählen (nur HIER!)
var effectiveLayers, effectiveMetadata;
if (checkType === "Keyword-based") {
    effectiveLayers = Array.isArray(keyword_layers) ? keyword_layers : [];
    effectiveMetadata = Array.isArray(keyword_metadata) ? keyword_metadata : [];
} else {
    effectiveLayers = Array.isArray(requiredLayers) ? requiredLayers : [];
    effectiveMetadata = Array.isArray(requiredMetadata) ? requiredMetadata : [];
}

// Optionale UI-Preview
if (DEBUG_OUTPUT === true) {
    var formattedMeta = "Metadata Output:\n";
    for (var m = 0; m < effectiveMetadata.length; m++) {
        var mk = effectiveMetadata[m];
        var label = userFriendlyLabels[mk] || mk;
        formattedMeta += label + ": " + metadataOutput[mk] + "\n";
    }
    var formattedLayers = "Layer Output:\n";
    for (var n = 0; n < effectiveLayers.length; n++) {
        var lname = effectiveLayers[n];
        formattedLayers += lname + ": " + (layerExists(doc, lname) ? "yes" : "NO") + "\n";
    }
    alert(formattedMeta + "\n\n" + formattedLayers);
}

// Layer-Existenz
function layerExists(doc, layerName) {
    function searchLayers(layers, name) {
        for (var i = 0; i < layers.length; i++) {
            var layer = layers[i];
            if (layer.name === name) return true;
            if (layer.typename === "LayerSet") {
                if (searchLayers(layer.layers, name)) return true;
            }
        }
        return false;
    }
    return searchLayers(doc.layers, layerName);
}

// Ergebnis-Grundgerüst
var resultObj = {
    metadata: metadataOutput,
    details: {
        layers: {},
        missingLayers: [],
        missingMetadata: [],
        layerStatus: "OK",
        metaStatus: "OK",
        checkType: checkType,
        keywordCheck: { enabled: keywordCheckEnabled, keyword: keywordCheckWord },
        keywordDebug: {
            enabled: keywordCheckEnabled,
            word: String(keywordCheckWord || ""),
            parsedKeywords: String(metadataOutput["keywords"] || "undefined"),
            decided: checkType
        }
    }
};

// Ebenen prüfen
for (var li = 0; li < effectiveLayers.length; li++) {
    var lname2 = effectiveLayers[li];
    var present = layerExists(doc, lname2);
    resultObj.details.layers[lname2] = present ? "yes" : "no";
    if (!present) {
        resultObj.details.missingLayers.push(lname2);
        resultObj.details.layerStatus = "FAIL";
    }
}

// Metadaten prüfen
for (var mj = 0; mj < effectiveMetadata.length; mj++) {
    var field = effectiveMetadata[mj];
    if (metadataOutput[field] === "undefined") {
        resultObj.details.missingMetadata.push(field);
        resultObj.details.metaStatus = "FAIL";
    }
}

// --- Logging (wie gehabt) ---
var baseName = doc.name.replace(/\.[^\.]+$/, "");

var contentLogFile = new File(logFolderPath + "/" + baseName + "_01_log_contentcheck.json");
contentLogFile.encoding = "UTF8";
contentLogFile.open("w");
contentLogFile.write(serializeToJsonPretty(resultObj, ""));
contentLogFile.close();
debug_print("Contentcheck-Log gespeichert: " + contentLogFile.fullName);

// Fail-Log nur bei FAIL
if (resultObj.details.layerStatus === "FAIL" || resultObj.details.metaStatus === "FAIL") {
    var missingLayersObj = {};
    for (var i2 = 0; i2 < resultObj.details.missingLayers.length; i2++) {
        missingLayersObj[resultObj.details.missingLayers[i2]] = "fehlt";
    }
    var missingMetadataObj = {};
    for (var j2 = 0; j2 < resultObj.details.missingMetadata.length; j2++) {
        missingMetadataObj[resultObj.details.missingMetadata[j2]] = "fehlt";
    }
    var failObj = {
        missingLayers: missingLayersObj,
        missingMetadata: missingMetadataObj,
        layerStatus: resultObj.details.layerStatus,
        metaStatus: resultObj.details.metaStatus,
        checkType: checkType,
        keywordCheck: { enabled: keywordCheckEnabled, keyword: keywordCheckWord }
    };
    var failLogFile = new File(logFolderPath + "/" + baseName + "_01_log_fail.json");
    failLogFile.encoding = "UTF8";
    failLogFile.open("w");
    failLogFile.write(serializeToJsonPretty(failObj, ""));
    failLogFile.close();
    debug_print("Contentcheck-Fail Log gespeichert: " + failLogFile.fullName);
}