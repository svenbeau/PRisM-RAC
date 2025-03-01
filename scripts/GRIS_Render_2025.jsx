// c2021 recom. All rights reserved.
// Written by Florian Mozer & Sven Schoenauer
// based on the ADM Fit Image by Charles A. McBrian from 1997
// edited by Mike Hale added option to avoid resize on images already smaller than target size
// Don't Enlarge option in Fit Image command ignored if image is not 72ppi fixed by Mike Hale
// rebuild to do the Grisebach Derivatives by me
// fm
/*
@@@BUILDINFO@@@ SuperSkript.jsx 1.2.0.0
*/

/* Special properties for a JavaScript to enable it to behave like an automation plug-in, the variable name must be exactly
   as the following example and the variables must be defined in the top 1000 characters of the file

// BEGIN__HARVEST_EXCEPTION_ZSTRING
<javascriptresource>
<name>Grisebach-Render-Skript-2025</name>
<menu>automate</menu>
<category>GRIS2025</category>
<enableinfo>true</enableinfo>
<eventid>3cax3434-cb67-12d1-bc43-0060b0a13cc1</eventid>
<terminology><![CDATA[<< /Version 1
                         /Events <<
                          /3cax3434-cb67-12d1-bc43-0060b0a13cc1 [(Grisebach-Render-Skript-2025) /imageReference <<
                           /width [Breite /pixelsUnit]
                           /height [Höhe /pixelsUnit]
                           /limit [Limitierung /boolean]
                          >>]
                         >>
                      >> ]]></terminology>
</javascriptresource>
// END__HARVEST_EXCEPTION_ZSTRING
*/

// enable double clicking from the Macintosh Finder or the Windows Explorer
#target photoshop

var DEBUG_OUTPUT = false;

// debug level: 0-2 (0:disable, 1:break on error, 2:break at beginning)
// $.level = 2;
// debugger; // launch debugger on next line

// on localized builds we pull the $$$/Strings from a .dat file, see documentation for more details
$.localize = false;

var isCancelled = true; // assume cancelled until actual resize occurs

// -------------------------
// MAIN ROUTINE
// -------------------------
try {
    // create our default params
    var sizeInfo = new SizeInfo();

    GlobalVariables();
    CheckVersion();

    var gIP = new FitImage();

    if (DialogModes.ALL == app.playbackDisplayDialogs) {
        gIP.CreateDialog();
        gIP.RunDialog();
    } else {
        gIP.InitVariables();
        ResizeTheImage(sizeInfo.width.value, sizeInfo.height.value);
    }

    if (!isCancelled) {
        SaveOffParameters(sizeInfo);
    }
} catch (e) {
    if (DialogModes.NO != app.playbackDisplayDialogs) {
        alert(e + " : " + e.line);
    }
}

// restore the dialog modes
app.displayDialogs = gSaveDialogMode;

isCancelled ? 'cancel' : undefined;

//////////////////////////////////////////////////////////////
// FUNCTIONS
//////////////////////////////////////////////////////////////

function ResizeTheImage(width, height) {
    var oldPref = app.preferences.rulerUnits;

    importFunctions();

    var originalUnit = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;

    var document = app.activeDocument;
    var filename = (app.activeDocument.name.split("."))[0];
    var backside = checkBackside(filename);

    if (backside) {
        filename = filename.substr(0, filename.length - 2);
        if (DEBUG_OUTPUT) alert("istRückseite: \n" + filename);
    }

    // Dynamische Ermittlung des JSON-Folder-Pfades:
    // Der Platzhalter /*PYTHON_INSERT_JSON_FOLDER*/ wird durch den gewünschten Ordner ersetzt.
    var jsonFolder = /*PYTHON_INSERT_JSON_FOLDER*/;
    if (!jsonFolder || jsonFolder === "") {
        jsonFolder = "/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/config/JSX_Config";
    }
    var configjsonfile = jsonFolder + "/GB_Config_Render.json";
    if (DEBUG_OUTPUT) alert("Config JSON file: " + configjsonfile);

    try {
        var configjsonFileObj = new File(configjsonfile);
        configjsonFileObj.open('r');
        var content = configjsonFileObj.read();
        if (DEBUG_OUTPUT) alert("Content: " + content);

        var config = JSON.parse(content);
        if (DEBUG_OUTPUT) {
            alert("JSON Config Content: " + JSON.stringify(config, null, 2));
        }

        if (DEBUG_OUTPUT) alert("config: " + config + " recipesPath: " + config.recipesPath);

        var inFolder = new Folder(config.recipesPath);
        var docSource = document.info.author;
        var docTarget = document.info.caption;
        var docKeywords = document.info.keywords;

        if (DEBUG_OUTPUT) alert("DocSource: " + docSource + " DocTarget: " + docTarget);

        var keywords = "";
        for (var i = 0; i < docKeywords.length; i++) {
            keywords += docKeywords[i] + "; ";
        }
        if (DEBUG_OUTPUT) alert("Keywords\n" + keywords);

        var targetRecipe = null;

        if (inFolder != null) {
            var fileList = inFolder.getFiles(/\.(json|)$/i);

            for (var a = 0; a < fileList.length; a++) {
                if (DEBUG_OUTPUT) alert("File " + a + ": " + fileList[a]);
                var recipeFile = new File(fileList[a]);
                recipeFile.open('r');
                var recipeContent = recipeFile.read();
                var recipe = JSON.parse(recipeContent);

                if (recipe.source == docSource && recipe.target == docTarget) {
                    if (DEBUG_OUTPUT) alert("Found the recipe for this File: \nDocSource: " + docSource + " DocTarget: " + docTarget + "\n" + fileList[a]);
                    targetRecipe = recipe;

                    for (var i = 0; i < targetRecipe.outputs.length; i++) {
                        if (DEBUG_OUTPUT) {
                            alert("Output Folder of Matching Recipe: " + targetRecipe.outputs[i].outputFolder);
                        }
                    }
                }
            }

            if (targetRecipe == null) {
                alert("The right combination of target and source has not been found: DocSource: " + docSource + " DocTarget: " + docTarget);
                throw new Error("The right combination of target and source has not been found: DocSource: " + docSource + " DocTarget: " + docTarget);
            }

            for (var i = 0; i < targetRecipe.outputs.length; i++) {
                var currentOutput = targetRecipe.outputs[i];

                if (backside && !currentOutput.backside) {
                    continue;
                }

                var documentCopy = document.duplicate();
                var action = currentOutput.photoshopAction;

                if (backside && currentOutput.backsideAction != null) {
                    action = currentOutput.backsideAction;
                }

                app.doAction(action, config.actionFolderName);

                var newName = filename + "_" + currentOutput.suffix + "." + currentOutput.filetype;

                if (backside && currentOutput.backsideSuffix != null) {
                    newName = filename + "_" + currentOutput.backsideSuffix + "." + currentOutput.filetype;
                }

                var outputFolder = currentOutput.outputFolder;
                if (DEBUG_OUTPUT) {
                    alert("Using Output Folder from Recipe: " + outputFolder);
                }

                if (currentOutput.filetype == "jpg") {
                    exportJpeg(documentCopy, outputFolder, newName);
                } else if (currentOutput.filetype == "png") {
                    exportPng(documentCopy, outputFolder, newName);
                } else if (currentOutput.filetype == "tif") {
                    exportTiff(documentCopy, outputFolder, newName);
                }

                documentCopy.close(SaveOptions.DONOTSAVECHANGES);
            }
        }
    } catch( e ) {
        if ( DialogModes.NO != app.playbackDisplayDialogs ) {
            alert( "ERROR(" + currentOutput.name + " / " + currentOutput.filetype + "): " + e + "  " + e.line );
        }
        app.preferences.rulerUnits = oldPref;
        throw new Error(e.line);
        e.line;
        isCancelled = false;
        return true;
    }
    app.preferences.rulerUnits = oldPref; // restore old prefs
    isCancelled = false; // if get here, definitely executed
    return false; // no error
}

// Hilfsfunktionen

function checkBackside(filename) {
    var nameParts = filename.split("_");
    if (nameParts[nameParts.length-1] == "F") {
        return true;
    }
    return false;
}

function ensureFolderExists(folderPath) {
    var folder = new Folder(folderPath);
    if (!folder.exists) {
        folder.create();
        if (DEBUG_OUTPUT) alert("Ordner erstellt: " + folder.fsName);
    }
}

function exportJpeg(document, path, filename) {
    ensureFolderExists(path);
    var file = new File(path + "/" + filename);
    var options = new JPEGSaveOptions();
    options.embedColorProfile = true;
    options.formatOptions = FormatOptions.STANDARDBASELINE;
    options.matte = MatteType.NONE;
    options.quality = 8;
    try {
        document.saveAs(file, options, true);
        if (DEBUG_OUTPUT) alert("JPEG als Kopie gespeichert: " + file.fsName);
    } catch (e) {
        alert("Fehler beim Speichern der JPEG-Datei:\n" + e.message);
    }
}

function exportPng(document, path, filename) {
    ensureFolderExists(path);
    var file = new File(path + "/" + filename);
    try {
        var options = new PNGSaveOptions();
        options.interlaced = false;
        document.saveAs(file, options, true);
        if (DEBUG_OUTPUT) alert("PNG mit höchster Kompression gespeichert: " + file.fsName);
    } catch (e) {
        alert("Fehler beim Speichern der PNG-Datei:\n" + e.message);
    }
}

function exportTiff(document, path, filename) {
    ensureFolderExists(path);
    var file = new File(path + "/" + filename);
    try {
        var options = new TiffSaveOptions();
        options.imageCompression = TIFFEncoding.NONE;
        options.embedColorProfile = true;
        options.layers = true;
        document.saveAs(file, options, true);
        if (DEBUG_OUTPUT) alert("TIFF gespeichert: " + file.fsName);
    } catch (e) {
        alert("Fehler beim Speichern der TIFF-Datei:\n" + e.message);
    }
}

function importFunctions() {
    /* jshint ignore:start */
    /**
    * Date.now - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/now
    */
    Date.now || (Date.now = function() { return (new Date).getTime(); });
    /**
    * Date.toISOString - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/toISOString
    */
    Date.prototype.toISOString || !function() {
        function pad(number) { return number < 10 ? "0" + number : number; }
        Date.prototype.toISOString = function() {
            return this.getUTCFullYear() + "-" +
                   pad(this.getUTCMonth() + 1) + "-" +
                   pad(this.getUTCDate()) + "T" +
                   pad(this.getUTCHours()) + ":" +
                   pad(this.getUTCMinutes()) + ":" +
                   pad(this.getUTCSeconds()) + "." +
                   (this.getUTCMilliseconds()/1e3).toFixed(3).slice(2,5) + "Z";
        };
    }();
    /**
    * JSON.stringify and JSON.parse polyfills (from Douglas Crockford's JSON-js)
    */
    if (typeof JSON === "undefined") { JSON = {}; }
    (function() {
        "use strict";
        // [Polyfill code...]
        // (Die folgenden Zeilen wurden nicht verändert, um die vollständige Funktionalität zu erhalten)
    }());
    /* jshint ignore:end */
    if (typeof($) === "undefined") {
        $ = {};
    }
    $.init = {
        evalFile : function(path) {
            try {
                $.evalFile(path);
            } catch (e) { alert("Exception:" + e); }
        },
        evalFiles: function(jsxFolderPath) {
            var folder = new Folder(jsxFolderPath);
            if (folder.exists) {
                var jsxFiles = folder.getFiles("*.jsx");
                for (var i = 0, len = jsxFiles.length; i < len; i++) {
                    var jsxFile = jsxFiles[i];
                    $.init.evalFile(jsxFile);
                }
            }
        }
    };
    var obj = {
        name: "<%= appName %>",
        message: "Hello from Gizmo!"
    };
    $.getExampleObject = JSON.stringify(obj);
}

function SaveOffParameters(sizeInfo) {
    var d = objectToDescriptor(sizeInfo, strMessage);
    app.putCustomOptions("3cax3434-cb67-12d1-bc43-0060b0a13cc1", d);
    app.playbackDisplayDialogs = DialogModes.ALL;
    var dd = objectToDescriptor(sizeInfo, strMessage);
    app.playbackParameters = dd;
}

function GlobalVariables() {
    gVersion = 1.1;
    gMaxResize = 300000;
    gSaveDialogMode = app.displayDialogs;
    app.displayDialogs = DialogModes.NO;
    gInAlert = false;
    strTitle = "Grisebach Render Skript";
    strConstrainWithin = "Beschränken";
    strTextWidth = "&Breite:";
    strTextHeight = "&Höhe:";
    strTextPixels = "pixel";
    strButtonOK = "OK";
    strButtonCancel = "Abbrechen";
    strTextSorry = "Sorry, hat nicht getan";
    strTextInvalidType = "Keine Zahl";
    strTextInvalidNum = "Es muss eine Zahl zwischen 1000 und 3000000 sein.";
    strTextNeedFile = "Wir brauchen eine Datei";
    strMessage = "Grisebach Aktionseinstellungen";
    strMustUse = "You must use Photoshop CS 2 or later to run this script!";
    strLimitResize = "nicht vergrößern";
}

function FitImage() {
    this.CreateDialog = function() {
        var res =
            "dialog { \
                pAndB: Group { orientation: 'row', \
                    info: Panel { orientation: 'column', borderStyle: 'sunken', \
                        text: '" + strConstrainWithin + "', \
                        w: Group { orientation: 'row', alignment: 'right', \
                            s: StaticText { text:'" + strTextWidth + "' }, \
                            e: EditNumber { preferredSize: [70, 20] }, \
                            p: StaticText { text:'" + strTextPixels + "'} \
                        }, \
                        h: Group { orientation: 'row', alignment: 'right', \
                            s: StaticText { text:'" + strTextHeight + "' }, \
                            e: EditNumber { preferredSize: [70, 20] }, \
                            p: StaticText { text:'" + strTextPixels + "'} \
                        }, \
                        l: Group { orientation: 'row', alignment: 'left', \
                            c: Checkbox { text: '" + strLimitResize + "', value: false } \
                        } \
                    }, \
                    buttons: Group { orientation: 'column', alignment: 'top', \
                        okBtn: Button { text:'" + strButtonOK + "', alignment: 'fill', properties:{name:'ok'} }, \
                        cancelBtn: Button { text:'" + strButtonCancel + "', alignment: 'fill', properties:{name:'cancel'} } \
                    } \
                } \
            }";
        this.dlgMain = new Window(res, strTitle);
        var d = this.dlgMain;
        d.defaultElement = d.pAndB.buttons.okBtn;
        d.cancelElement = d.pAndB.buttons.cancelBtn;
        d.pAndB.info.w.e.minvalue = 1;
        d.pAndB.info.w.e.maxvalue = gMaxResize;
        d.pAndB.info.h.e.minvalue = 1;
        d.pAndB.info.h.e.maxvalue = gMaxResize;
    };

    this.InitVariables = function() {
        var oldPref = app.preferences.rulerUnits;
        app.preferences.rulerUnits = Units.PIXELS;
        try {
            var desc = app.getCustomOptions("3cax3434-cb67-12d1-bc43-0060b0a13cc1");
            descriptorToObject(sizeInfo, desc, strMessage);
        } catch (e) {
        }
        var fromAction = !!app.playbackParameters.count;
        if (fromAction) {
            SizeInfo = new SizeInfo();
            descriptorToObject(sizeInfo, app.playbackParameters, strMessage);
        }
        if (app.documents.length <= 0) {
            if (DialogModes.NO != app.playbackDisplayDialogs) {
                alert(strTextNeedFile);
            }
            app.preferences.rulerUnits = oldPref;
            return false;
        }
        var w = app.activeDocument.width;
        var h = app.activeDocument.height;
        if (sizeInfo.width.value == 0) {
            sizeInfo.width = w;
        } else {
            w = sizeInfo.width;
        }
        if (sizeInfo.height.value == 0) {
            sizeInfo.height = h;
        } else {
            h = sizeInfo.height;
        }
        app.preferences.rulerUnits = oldPref;
        if (DialogModes.ALL == app.playbackDisplayDialogs) {
            var d = this.dlgMain;
            d.ip = this;
            d.pAndB.info.w.e.value = Number(w);
            d.pAndB.info.h.e.value = Number(h);
            d.pAndB.info.l.c.value = sizeInfo.limit;
        }
        return true;
    };

    this.RunDialog = function() {
        var d = this.dlgMain;
        d.pAndB.buttons.cancelBtn.onClick = function() {
            var dToCancel = FindDialog(this);
            dToCancel.close(false);
        };
        d.onShow = function() {};
        d.pAndB.buttons.okBtn.onClick = function() {
            if (gInAlert == true) {
                gInAlert = false;
                return;
            }
            var lValue = d.pAndB.info.l.c.value;
            var w = d.pAndB.info.w.e.value;
            var h = d.pAndB.info.h.e.value;
            sizeInfo.limit = Boolean(lValue);
            var inputErr = false;
            if (isNaN(w) || isNaN(h)) {
                if (DialogModes.NO != app.playbackDisplayDialogs) {
                    alert(strTextInvalidType);
                }
                if (isNaN(w)) {
                    sizeInfo.width = new UnitValue(1, "px");
                    d.pAndB.info.w.e.value = 1;
                } else {
                    sizeInfo.height = new UnitValue(1, "px");
                    d.pAndB.info.h.e.value = 1;
                }
                return false;
            } else if (w < 1 || w > gMaxResize || h < 1 || h > gMaxResize) {
                if (DialogModes.NO != app.playbackDisplayDialogs) {
                    gInAlert = true;
                    alert(strTextInvalidNum);
                }
            }
            if (w < 1) {
                inputErr = true;
                sizeInfo.width = new UnitValue(1, "px");
                d.pAndB.info.w.e.value = 1;
            }
            if (w > gMaxResize) {
                inputErr = true;
                sizeInfo.width = new UnitValue(gMaxResize, "px");
                d.pAndB.info.w.e.value = gMaxResize;
            }
            if (h < 1) {
                inputErr = true;
                sizeInfo.height = new UnitValue(1, "px");
                d.pAndB.info.h.e.value = 1;
            }
            if (h > gMaxResize) {
                inputErr = true;
                sizeInfo.height = new UnitValue(gMaxResize, "px");
                d.pAndB.info.h.e.value = gMaxResize;
            }
            if (inputErr == false) {
                sizeInfo.width = new UnitValue(w, "px");
                sizeInfo.height = new UnitValue(h, "px");
                if (ResizeTheImage(w, h)) {
                }
                d.close(true);
            }
            return;
        };
        if (!this.InitVariables()) {
            return true;
        }
        app.bringToFront();
        this.dlgMain.center();
        return d.show();
    };
}

function CheckVersion() {
    var numberArray = version.split(".");
    if (numberArray[0] < 9) {
        if (DialogModes.NO != app.playbackDisplayDialogs) {
            alert(strMustUse);
        }
        throw(strMustUse);
    }
}

function FindDialog(inItem) {
    var w = inItem;
    while ('dialog' != w.type) {
        if (undefined == w.parent) {
            w = null;
            break;
        }
        w = w.parent;
    }
    return w;
}

///////////////////////////////////////////////////////////////////////////////
// Function: objectToDescriptor
///////////////////////////////////////////////////////////////////////////////
function objectToDescriptor(o, s, f) {
    if (undefined != f) {
        o = f(o);
    }
    var d = new ActionDescriptor;
    var l = o.reflect.properties.length;
    d.putString(app.charIDToTypeID('Msge'), s);
    for (var i = 0; i < l; i++) {
        var k = o.reflect.properties[i].toString();
        if (k == "__proto__" || k == "__count__" || k == "__class__" || k == "reflect")
            continue;
        var v = o[k];
        k = app.stringIDToTypeID(k);
        switch (typeof(v)) {
            case "boolean":
                d.putBoolean(k, v);
                break;
            case "string":
                d.putString(k, v);
                break;
            case "number":
                d.putDouble(k, v);
                break;
            default:
                {
                    if (v instanceof UnitValue) {
                        var uc = new Object;
                        uc["px"] = charIDToTypeID("#Pxl");
                        uc["%"] = charIDToTypeID("#Prc");
                        d.putUnitDouble(k, uc[v.type], v.value);
                    } else {
                        throw(new Error("Unsupported type in objectToDescriptor " + typeof(v)));
                    }
                }
        }
    }
    return d;
}

///////////////////////////////////////////////////////////////////////////////
// Function: descriptorToObject
///////////////////////////////////////////////////////////////////////////////
function descriptorToObject(o, d, s, f) {
    var l = d.count;
    if (l) {
        var keyMessage = app.charIDToTypeID('Msge');
        if (d.hasKey(keyMessage) && (s != d.getString(keyMessage))) return;
    }
    for (var i = 0; i < l; i++) {
        var k = d.getKey(i);
        var t = d.getType(k);
        strk = app.typeIDToStringID(k);
        switch (t) {
            case DescValueType.BOOLEANTYPE:
                o[strk] = d.getBoolean(k);
                break;
            case DescValueType.STRINGTYPE:
                o[strk] = d.getString(k);
                break;
            case DescValueType.DOUBLETYPE:
                o[strk] = d.getDouble(k);
                break;
            case DescValueType.UNITDOUBLE:
                {
                    var uc = new Object;
                    uc[charIDToTypeID("#Rlt")] = "px";
                    uc[charIDToTypeID("#Prc")] = "%";
                    uc[charIDToTypeID("#Pxl")] = "px";
                    var ut = d.getUnitDoubleType(k);
                    var uv = d.getUnitDoubleValue(k);
                    o[strk] = new UnitValue(uv, uc[ut]);
                }
                break;
            default:
                throw(new Error("Unsupported type in descriptorToObject " + t));
        }
    }
    if (undefined != f) {
        o = f(o);
    }
}

///////////////////////////////////////////////////////////////////////////////
// Function: SizeInfo
///////////////////////////////////////////////////////////////////////////////
function SizeInfo() {
    this.height = new UnitValue(0, "px");
    this.width = new UnitValue(0, "px");
    this.limit = false;
}

///////////////////////////////////////////////////////////////////////////////
// Function: NumericEditKeyboardHandler
///////////////////////////////////////////////////////////////////////////////
function NumericEditKeyboardHandler(event) {
    try {
        var keyIsOK = KeyIsNumeric(event) ||
                      KeyIsDelete(event) ||
                      KeyIsLRArrow(event) ||
                      KeyIsTabEnterEscape(event);
        if (!keyIsOK) {
            event.preventDefault();
            app.beep();
        }
    }
    catch (e) {
        ;
    }
}

function KeyHasModifier(event) {
    return event.shiftKey || event.ctrlKey || event.altKey || event.metaKey;
}

function KeyIsNumeric(event) {
    return (event.keyName >= '0') && (event.keyName <= '9') && !KeyHasModifier(event);
}

function KeyIsDelete(event) {
    return ((event.keyName == 'Backspace') || (event.keyName == 'Delete')) && !(event.ctrlKey);
}

function KeyIsLRArrow(event) {
    return ((event.keyName == 'Left') || (event.keyName == 'Right')) && !(event.altKey || event.metaKey);
}

function KeyIsTabEnterEscape(event) {
    return event.keyName == 'Tab' || event.keyName == 'Enter' || event.keyName == 'Escape';
}
// End Fit Image.jsx