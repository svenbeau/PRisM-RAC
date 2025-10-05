#target photoshop

// Sicherstellen, dass das XMP-Script-Modul verfügbar ist
if (ExternalObject.AdobeXMPScript == undefined) {
    ExternalObject.AdobeXMPScript = new ExternalObject("lib:AdobeXMPScript");
}

// Hilfsfunktion: Liest ein XMP-Feld aus.
// Für "subject" wird das RDF-Bag manuell ausgelesen.
// Für "creator" (dc:creator, als RDF-Seq) wird das erste Element ausgelesen.
function getXMPProperty(xmp, schemaNS, prop) {
    var val = "";
    try {
        if (prop === "subject") {
            // dc:subject ist ein RDF-Bag.
            var count = xmp.countArrayItems(schemaNS, prop);
            var arr = [];
            for (var i = 1; i <= count; i++) {
                try {
                    var item = xmp.getArrayItem(schemaNS, prop, i);
                    if (item && item.value) {
                        arr.push(String(item.value));
                    }
                } catch(e) {
                    arr.push("[Fehler bei Array-Item " + i + ": " + e + "]");
                }
            }
            val = arr.join(", ");
        } else if (prop === "creator") {
            // dc:creator ist in der Regel als RDF-Seq gespeichert.
            var count = xmp.countArrayItems(schemaNS, prop);
            if (count > 0) {
                try {
                    var item = xmp.getArrayItem(schemaNS, prop, 1);
                    if (item && item.value) {
                        val = String(item.value);
                    }
                } catch(e) {
                    val = "[Fehler beim Auslesen des ersten Elementes von creator: " + e + "]";
                }
            }
        } else {
            // Versuche, den lokalisierten Text zu holen
            var localized = xmp.getLocalizedText(schemaNS, prop, "", "x-default");
            if (localized && localized.value) {
                val = String(localized.value);
            } else {
                // Fallback: getProperty
                var plain = xmp.getProperty(schemaNS, prop);
                if (plain != null) {
                    val = String(plain);
                }
            }
        }
    } catch(e) {
        try {
            var plain2 = xmp.getProperty(schemaNS, prop);
            if (plain2 != null) {
                val = String(plain2);
            }
        } catch(e2) {
            val = "[Fehler: " + e2 + "]";
        }
    }
    return val;
}

function debugPhotoshopMappings() {
    // Prüfen, ob ein Dokument geöffnet ist
    if (app.documents.length < 1) {
        alert("Kein Dokument geöffnet. Bitte ein Dokument öffnen und das Skript erneut ausführen.");
        return;
    }
    
    var doc = app.activeDocument;
    var rawData = "";
    try {
        rawData = doc.xmpMetadata.rawData;
    } catch (e) {
        alert("Fehler beim Auslesen der XMP-Daten: " + e);
        return;
    }
    if (!rawData || rawData === "") {
        alert("Dieses Dokument enthält keine XMP-Daten.");
        return;
    }
    
    var xmp = new XMPMeta(rawData);
    
    // Definiere die Felder, die du auslesen möchtest
    var fields = [
       { label: "DC Title (dc:title)", ns: XMPConst.NS_DC, prop: "title" },
       { label: "DC Description (dc:description) → 'Caption'", ns: XMPConst.NS_DC, prop: "description" },
       { label: "DC Creator (dc:creator) → 'Author'", ns: XMPConst.NS_DC, prop: "creator" },
       { label: "DC Subject (dc:subject) → 'Keywords'", ns: XMPConst.NS_DC, prop: "subject" },
       { label: "DC Rights (dc:rights)", ns: XMPConst.NS_DC, prop: "rights" },
       { label: "Photoshop Headline (photoshop:Headline) → 'Titel'", ns: XMPConst.NS_PHOTOSHOP, prop: "Headline" },
       { label: "Photoshop AuthorsPosition", ns: XMPConst.NS_PHOTOSHOP, prop: "AuthorsPosition" },
       { label: "Photoshop CaptionWriter", ns: XMPConst.NS_PHOTOSHOP, prop: "CaptionWriter" },
       { label: "Photoshop City", ns: XMPConst.NS_PHOTOSHOP, prop: "City" },
       { label: "Photoshop State", ns: XMPConst.NS_PHOTOSHOP, prop: "State" },
       { label: "Photoshop Country", ns: XMPConst.NS_PHOTOSHOP, prop: "Country" },
       { label: "Photoshop Credit", ns: XMPConst.NS_PHOTOSHOP, prop: "Credit" },
       { label: "Photoshop Source", ns: XMPConst.NS_PHOTOSHOP, prop: "Source" },
       { label: "Photoshop Instructions", ns: XMPConst.NS_PHOTOSHOP, prop: "Instructions" },
       { label: "Photoshop TransmissionReference", ns: XMPConst.NS_PHOTOSHOP, prop: "TransmissionReference" },
       { label: "xmpRights:WebStatement", ns: "http://ns.adobe.com/xap/1.0/rights/", prop: "WebStatement" }
    ];
    
    var output = "Photoshop <-> XMP Mapping Debug\n\n";
    for (var i = 0; i < fields.length; i++) {
        var f = fields[i];
        var value = getXMPProperty(xmp, f.ns, f.prop);
        if (value === "") {
            value = "(leer oder nicht vorhanden)";
        }
        output += f.label + ":\n   " + value + "\n\n";
    }
    
    alert(output);
}

// Funktion aufrufen
debugPhotoshopMappings();