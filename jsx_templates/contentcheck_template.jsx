// contentcheck_template.jsx
// Erwartung: Python injiziert VOR diesem Template einen Header mit:
//   var DEBUG_OUTPUT
//   var required_layers, required_metadata
//   var keyword_layers,  keyword_metadata
//   var keywordCheckEnabled, keywordCheckWord
//   var keywordLogic           // NEU: "AUTO" | "ANY" | "ALL"
//   var logFolderPath

// ---------------- Polyfills & Utils ----------------
if (typeof String.prototype.trim !== "function") {
    String.prototype.trim = function() { return this.replace(/^\s+|\s+$/g, ""); };
}
if (ExternalObject.AdobeXMPScript == undefined) {
    ExternalObject.AdobeXMPScript = new ExternalObject("lib:AdobeXMPScript");
}
if (typeof Array.isArray !== "function") {
    Array.isArray = function(arg) { return Object.prototype.toString.call(arg) === "[object Array]"; };
}
if (typeof JSON === "undefined") {
    JSON = {};
    JSON.stringify = function(obj) {
        function ser(o){
            if (typeof o === "object" && o !== null){
                if (o instanceof Array){ var a=[]; for (var i=0;i<o.length;i++) a.push(ser(o[i])); return "["+a.join(",")+"]"; }
                var s="{"; for (var k in o) if (o.hasOwnProperty(k)){
                    var v=o[k];
                    if (typeof v === "object" && v !== null){ s+='"'+k+'":'+ser(v)+","; }
                    else if (typeof v === "string"){ s+='"'+k+'":"'+v.replace(/"/g,'\\"')+'",'; }
                    else { s+='"'+k+'":'+v+","; }
                }
                s=s.replace(/,$/,"")+"}"; return s;
            }
            if (typeof o === "string") return '"'+o.replace(/"/g,'\\"')+'"';
            return String(o);
        }
        return ser(obj);
    };
}
function serializeToJsonPretty(obj, indent) {
    indent = indent || "";
    if (typeof obj !== "object" || obj === null) { return (typeof obj === "string") ? '"' + obj.replace(/"/g, '\\"') + '"' : String(obj); }
    var isArray = Array.isArray(obj), out = isArray ? "[\n" : "{\n", indentNext = indent + "    ", first = true;
    if (isArray) { for (var i=0;i<obj.length;i++){ if(!first) out+=",\n"; first=false; out+=indentNext+serializeToJsonPretty(obj[i], indentNext);} }
    else { for (var key in obj) if (obj.hasOwnProperty(key)){ if(!first) out+=",\n"; first=false; out+=indentNext + '"' + key + '": ' + serializeToJsonPretty(obj[key], indentNext);} }
    out += "\n" + indent + (isArray ? "]" : "}"); return out;
}
if (typeof DEBUG_OUTPUT === "undefined") { var DEBUG_OUTPUT = false; }
function debug_print(msg) { if (DEBUG_OUTPUT) { $.writeln("[DEBUG] " + msg); } }
function removeSurroundingQuotes(str) {
    if (!str || str.length < 2) return str;
    if (str.charAt(0) === '"' && str.charAt(str.length - 1) === '"') return str.substring(1, str.length - 1);
    return str;
}

// ---------------- Defaults für injizierte Variablen ----------------
if (typeof required_layers === "undefined" || !required_layers) required_layers = [];
if (typeof required_metadata === "undefined" || !required_metadata) required_metadata = [];
if (typeof keyword_layers === "undefined" || !keyword_layers) keyword_layers = [];
if (typeof keyword_metadata === "undefined" || !keyword_metadata) keyword_metadata = [];
if (typeof keywordCheckEnabled === "undefined") keywordCheckEnabled = false;
if (typeof keywordCheckWord === "undefined")  keywordCheckWord = "";
if (typeof keywordLogic === "undefined" || !keywordLogic) keywordLogic = "AUTO";
keywordLogic = String(keywordLogic).toUpperCase(); // "AUTO" | "ANY" | "ALL"
if (typeof logFolderPath === "undefined" || !logFolderPath) { logFolderPath = Folder.desktop.fsName; }

var requiredLayers   = Array.isArray(required_layers)   ? required_layers   : [];
var requiredMetadata = Array.isArray(required_metadata) ? required_metadata : [];

// ---------------- Field-Mapping ----------------
var fieldMapping = {
    "documentTitle":    { ns: XMPConst.NS_DC,        prop: "title",                 altText: true,  isArray: false },
    "author":           { ns: XMPConst.NS_DC,        prop: "creator",               altText: false, isArray: true  },
    "authorPosition":   { ns: XMPConst.NS_PHOTOSHOP, prop: "AuthorsPosition",       altText: false, isArray: false },
    "description":      { ns: XMPConst.NS_DC,        prop: "description",           altText: true,  isArray: false },
    "descriptionWriter":{ ns: XMPConst.NS_PHOTOSHOP, prop: "CaptionWriter",         altText: false, isArray: false },
    "keywords":         { ns: XMPConst.NS_DC,        prop: "subject",               altText: false, isArray: true  },
    "copyrightNotice":  { ns: XMPConst.NS_DC,        prop: "rights",                altText: true,  isArray: false },
    "copyrightURL":     { ns: "http://ns.adobe.com/xap/1.0/rights/", prop: "WebStatement", altText: false, isArray: false },
    "city":             { ns: XMPConst.NS_PHOTOSHOP, prop: "City",                  altText: false, isArray: false },
    "stateProvince":    { ns: XMPConst.NS_PHOTOSHOP, prop: "State",                 altText: false, isArray: false },
    "country":          { ns: XMPConst.NS_PHOTOSHOP, prop: "Country",               altText: false, isArray: false },
    "creditLine":       { ns: XMPConst.NS_PHOTOSHOP, prop: "Credit",                altText: false, isArray: false },
    "source":           { ns: XMPConst.NS_PHOTOSHOP, prop: "Source",                altText: false, isArray: false },
    "headline":         { ns: XMPConst.NS_PHOTOSHOP, prop: "Headline",              altText: false, isArray: false },
    "instructions":     { ns: XMPConst.NS_PHOTOSHOP, prop: "Instructions",          altText: false, isArray: false },
    "transmissionRef":  { ns: XMPConst.NS_PHOTOSHOP, prop: "TransmissionReference", altText: false, isArray: false }
};
var userFriendlyLabels = {
    "documentTitle":"Title","author":"Author","description":"Description","keywords":"Keywords","headline":"Headline",
    "authorPosition":"Author Position","descriptionWriter":"Description Writer","copyrightNotice":"Copyright Notice",
    "copyrightURL":"Copyright URL","city":"City","stateProvince":"State/Province","country":"Country",
    "creditLine":"Credit Line","source":"Source","instructions":"Instructions","transmissionRef":"Transmission Ref"
};

// ---------------- XMP lesen ----------------
if (!app.documents || app.documents.length === 0) { alert("Keine Datei geöffnet. Bitte öffne eine Datei und starte das Skript erneut."); throw new Error("Kein Dokument geöffnet"); }
var doc = app.activeDocument;
var xmpData = doc.xmpMetadata.rawData;
var xmp = new XMPMeta(xmpData);

// XMP Value Helper
function getXMPValue(fieldKey) {
    var mapping = fieldMapping[fieldKey]; if (!mapping) return "undefined";
    var val = "";
    if (mapping.isArray) {
        try { var count = xmp.countArrayItems(mapping.ns, mapping.prop), items = [];
            for (var i = 1; i <= count; i++) { try { var item = xmp.getArrayItem(mapping.ns, mapping.prop, i); if (item && item.value) items.push(String(item.value)); } catch(e) {} }
            if (items.length > 0) val = items.join("; ");
        } catch(e) { val = "undefined"; }
    } else {
        if (mapping.altText) { try { var loc = xmp.getLocalizedText(mapping.ns, mapping.prop, "", "x-default"); if (loc && loc.value) val = String(loc.value); } catch(e) {} }
        if (!val) { try { var raw = xmp.getProperty(mapping.ns, mapping.prop); if (raw) val = String(raw); } catch(e) {} }
    }
    if (!val) val = "undefined"; return removeSurroundingQuotes(val);
}

// Alle Metadaten auslesen
var metadataOutput = {}; for (var k in fieldMapping) { metadataOutput[k] = getXMPValue(k); }

// ---------------- Keyword-Entscheidung (mit ANY/ALL/AUTO + NOT) ----------------
var checkType = "Standard", decidedKW = "Standard";
var kwEnabled = (keywordCheckEnabled === true);
var kwWord = String(keywordCheckWord || "");

// XMP-Keywords -> Set (lowercased, getrimmt)
function buildKeywordSet(kwString) {
    var set = {};
    if (!kwString) return set;
    var parts = String(kwString).split(";");
    for (var i = 0; i < parts.length; i++) {
        var t = String(parts[i]).trim().toLowerCase();
        if (t) set[t] = true;
    }
    return set;
}
var xmpKwSet = buildKeywordSet(String(metadataOutput["keywords"] || ""));

function splitByAny(s, seps) {
    var re = new RegExp("[" + seps.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') + "]", "g");
    var raw = s.split(re);
    var out = [];
    for (var i = 0; i < raw.length; i++) {
        var v = String(raw[i]).trim();
        if (v) out.push(v);
    }
    return out;
}

// parse Tokens -> {pos:[], neg:[]}  (leading "!" => neg)
function parseTokens(expr, separators) {
    var raw = splitByAny(expr, separators);
    var res = { pos: [], neg: [] };
    for (var i = 0; i < raw.length; i++) {
        var tok = raw[i];
        var isNeg = false;
        if (tok.indexOf("!") === 0) { isNeg = true; tok = tok.substring(1); }
        tok = tok.trim().toLowerCase();
        if (!tok) continue;
        (isNeg ? res.neg : res.pos).push(tok);
    }
    return res;
}

// Evaluation
// - ANY  : mindestens 1 positives vorhanden, kein negatives vorhanden
// - ALL  : alle positiven vorhanden, kein negatives vorhanden
// - AUTO : enthält '&'/'+' und keine ODER-Trenner → ALL, sonst ANY
function evalKW(expr, kwSet, mode) {
    expr = String(expr || "");
    if (!expr) return false;

    var hasAnd = expr.indexOf("&") >= 0 || expr.indexOf("+") >= 0;
    var hasOr  = expr.indexOf(";") >= 0 || expr.indexOf(",") >= 0 || expr.indexOf("|") >= 0;

    var effMode = (mode === "ANY" || mode === "ALL") ? mode : (hasAnd && !hasOr ? "ALL" : "ANY");
    var seps = (effMode === "ALL") ? "&+" : ";,|";
    var tk = parseTokens(expr, seps);

    for (var i = 0; i < tk.neg.length; i++) { if (kwSet[tk.neg[i]]) return false; }
    if (tk.pos.length === 0) return true; // nur Negationen

    if (effMode === "ALL") {
        for (var j = 0; j < tk.pos.length; j++) { if (!kwSet[tk.pos[j]]) return false; }
        return true;
    } else {
        for (var k = 0; k < tk.pos.length; k++) { if (kwSet[tk.pos[k]]) return true; }
        return false;
    }
}

if (kwEnabled && kwWord !== "") {
    var found = evalKW(kwWord, xmpKwSet, keywordLogic);
    decidedKW = found ? "Keyword-based" : "Standard";
}
checkType = decidedKW;

// Effektive Kriterien
var effectiveLayers, effectiveMetadata;
if (checkType === "Keyword-based") {
    effectiveLayers   = Array.isArray(keyword_layers)    ? keyword_layers    : [];
    effectiveMetadata = Array.isArray(keyword_metadata)  ? keyword_metadata  : [];
} else {
    effectiveLayers   = Array.isArray(requiredLayers)    ? requiredLayers    : [];
    effectiveMetadata = Array.isArray(requiredMetadata)  ? requiredMetadata  : [];
}

// ---------------- Ergebnisobjekt ----------------
var resultObj = {
    metadata: metadataOutput,
    details: {
        layers: {},
        missingLayers: [],
        missingMetadata: [],
        layerStatus: "OK",
        metaStatus: "OK",
        checkType: checkType,
        received: {
            required_layers: requiredLayers.slice ? requiredLayers.slice(0) : requiredLayers,
            required_metadata: requiredMetadata.slice ? requiredMetadata.slice(0) : requiredMetadata,
            keyword_layers: (Array.isArray(keyword_layers) ? keyword_layers.slice(0) : keyword_layers),
            keyword_metadata: (Array.isArray(keyword_metadata) ? keyword_metadata.slice(0) : keyword_metadata)
        },
        effective: {
            layers: effectiveLayers.slice ? effectiveLayers.slice(0) : effectiveLayers,
            metadata: effectiveMetadata.slice ? effectiveMetadata.slice(0) : effectiveMetadata
        },
        keywordCheck: { enabled: kwEnabled, keyword: kwWord, logic: keywordLogic },
        keywordDebug: { enabled: kwEnabled, word: kwWord, parsedKeywords: String(metadataOutput["keywords"] || "undefined"), decided: checkType }
    }
};

// Ebenen prüfen
for (var li=0; li<effectiveLayers.length; li++){
    var lname2 = effectiveLayers[li];
    var present = (function layerExists(doc, layerName) {
        function searchLayers(layers, name) {
            for (var i=0;i<layers.length;i++){
                var layer = layers[i];
                if (layer.name === name) return true;
                if (layer.typename === "LayerSet") { if (searchLayers(layer.layers, name)) return true; }
            }
            return false;
        }
        return searchLayers(doc.layers, layerName);
    })(doc, lname2);
    resultObj.details.layers[lname2] = present ? "yes" : "no";
    if (!present) { resultObj.details.missingLayers.push(lname2); resultObj.details.layerStatus = "FAIL"; }
}

// Metadaten prüfen
for (var mj=0; mj<effectiveMetadata.length; mj++){
    var field = effectiveMetadata[mj];
    if (metadataOutput[field] === "undefined") { resultObj.details.missingMetadata.push(field); resultObj.details.metaStatus = "FAIL"; }
}

// ---------------- Logging ----------------
var baseName = (function(){ try { return doc.name.replace(/\.[^\.]+$/, ""); } catch(e){ return "unknown"; } })();

var contentLogFile = new File(logFolderPath + "/" + baseName + "_01_log_contentcheck.json");
contentLogFile.encoding = "UTF8";
if (contentLogFile.open("w")) { contentLogFile.write(serializeToJsonPretty(resultObj, "")); contentLogFile.close(); debug_print("Contentcheck-Log gespeichert: " + contentLogFile.fullName); }

// Fail-Log nur bei FAIL
if (resultObj.details.layerStatus === "FAIL" || resultObj.details.metaStatus === "FAIL") {
    var missingLayersObj = {}; for (var i2=0;i2<resultObj.details.missingLayers.length;i2++){ missingLayersObj[resultObj.details.missingLayers[i2]] = "fehlt"; }
    var missingMetadataObj = {}; for (var j2=0;j2<resultObj.details.missingMetadata.length;j2++){ missingMetadataObj[resultObj.details.missingMetadata[j2]] = "fehlt"; }
    var failObj = {
        missingLayers: missingLayersObj,
        missingMetadata: missingMetadataObj,
        layerStatus: resultObj.details.layerStatus,
        metaStatus: resultObj.details.metaStatus,
        checkType: checkType,
        keywordCheck: { enabled: kwEnabled, keyword: kwWord, logic: keywordLogic },
        received: resultObj.details.received,
        effective: resultObj.details.effective
    };
    var failLogFile = new File(logFolderPath + "/" + baseName + "_01_log_fail.json");
    failLogFile.encoding = "UTF8";
    if (failLogFile.open("w")) { failLogFile.write(serializeToJsonPretty(failObj, "")); failLogFile.close(); debug_print("Contentcheck-Fail Log gespeichert: " + failLogFile.fullName); }
}