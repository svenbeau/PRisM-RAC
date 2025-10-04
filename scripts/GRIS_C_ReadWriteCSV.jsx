// GRIS_C_ReadWriteCSV.jsx
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

$.localize = false;
var DEBUG_OUTPUT = false;
var isCancelled = true; // assume cancelled until actual resize occurs

// === Konfiguration laden ====================================================
// Wir laden hier die Script-Konfiguration aus script_config.json.
// Dabei prüfen wir, ob die globale Variable SCRIPT_CONFIG_PATH definiert ist.
// Diese Variable kann in den allgemeinen Einstellungen gesetzt werden, sodass der Nutzer
// einen individuellen Pfad angeben kann. Falls nicht gesetzt, greifen wir auf den relativen Pfad zurück.
var scriptFile = new File($.fileName);
var defaultConfigPath = new File(scriptFile.parent.parent + "/config/script_config.json");
var configPath = (typeof SCRIPT_CONFIG_PATH !== "undefined" && SCRIPT_CONFIG_PATH)
    ? new File(SCRIPT_CONFIG_PATH)
    : defaultConfigPath;

if (!configPath.exists) {
    alert("Script config not found: " + configPath.fsName);
    var config = {};
} else {
    configPath.open("r");
    var configStr = configPath.read();
    configPath.close();
    try {
        // Entferne eventuelle trailing commas
        configStr = configStr.replace(/,\s*}/g, "}").replace(/,\s*\]/g, "]");
        var fullConfig = JSON.parse(configStr);
        var scripts = (fullConfig.scripts && Array.isArray(fullConfig.scripts)) ? fullConfig.scripts : [];
        var currentScriptPath = scriptFile.fsName;
        var config = {};
        for (var i = 0; i < scripts.length; i++) {
            if (currentScriptPath.indexOf(scripts[i].script_path) !== -1) {
                config = scripts[i];
                break;
            }
        }
    } catch (e) {
        alert("Error parsing script_config.json: " + e);
        var config = {};
    }
}

// Konfigurationswerte (Falls in script_config.json nicht vorhanden, werden leere Strings verwendet)
var config_json_folder = config.json_folder || "";
var config_actionFolderName = config.actionFolderName || "";
var config_basicWandFiles = config.basicWandFiles || "";
var config_csvWandFile = config.csvWandFile || "";
var config_wandFileSavePath = config.wandFileSavePath || "";

// === Rest des Skripts ======================================================
// ... (Der restliche Originalcode von GRIS_C_ReadWriteCSV.jsx bleibt unverändert) ...

try {
    var sizeInfo = new SizeInfo();
    GlobalVariables();
    CheckVersion();
    var gIP = new FitImage();
    if (DialogModes.ALL == app.playbackDisplayDialogs) {
        gIP.CreateDialog();
        gIP.RunDialog();
    } else {
        gIP.InitVariables();
        SaveImages(sizeInfo.width.value, sizeInfo.height.value);
    }
    if (!isCancelled) {
        SaveOffParameters(sizeInfo);
    }
} catch (e) {
    if (DialogModes.NO != app.playbackDisplayDialogs) {
        alert(e + " : " + e.line);
    }
}
app.displayDialogs = gSaveDialogMode;
isCancelled ? 'cancel' : undefined;

//////////////////////////////////////////////////////////////
// Funktionen zum Speichern der Bilder und weitere Hilfsfunktionen
//////////////////////////////////////////////////////////////

function SaveImages(width, height) {
    importFunctions();

    // Verwende einen absoluten Pfad zur JSON-Konfigurationsdatei (z.B. GB_Config_Render.json).
    var configjsonpath = '/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/config/JSX_Config/GB_Config_Render.json';
    if (DEBUG_OUTPUT)
        alert(configjsonpath);
    try {
        var configjsonfile = new File(configjsonpath);
        configjsonfile.open('r');
        var content = configjsonfile.read();
        if (DEBUG_OUTPUT)
            alert("Content: " + content);
        var config = JSON.parse(content);
        if (DEBUG_OUTPUT)
            alert("config: " + config + " recipesPath: " + config.recipesPath);

        var inFolder = new Folder(config.recipesPath);
        var docSource = app.activeDocument.info.author;
        var docTarget = app.activeDocument.info.caption;
        var docKeywords = app.activeDocument.info.keywords;

        if (DEBUG_OUTPUT)
            alert("DocSource: " + docSource + " DocTarget: " + docTarget);

        var keywords = "";
        for (var i = 0; i < docKeywords.length; i++) {
            keywords += docKeywords[i] + "; ";
        }
        if (DEBUG_OUTPUT)
            alert("Keywords\n" + keywords);

        var targetRecipe = null;

        if (inFolder != null) {
            var fileList = inFolder.getFiles(/\.(json|)$/i);

            for (var a = 0; a < fileList.length; a++) {
                if (DEBUG_OUTPUT)
                    alert("File " + a + ": " + fileList[a]);
                var recipeFile = new File(fileList[a]);
                recipeFile.open('r');
                var recipeContent = recipeFile.read();
                var recipe = JSON.parse(recipeContent);

                if (recipe.source == docSource && recipe.target == docTarget) {
                    if (DEBUG_OUTPUT)
                        alert("Found the recipe for this File: \nDocSource: " + docSource + " DocTarget: " + docTarget + "\n" + fileList[a]);
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

                var documentCopy = app.activeDocument.duplicate();
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
    } catch (e) {
        if (DialogModes.NO != app.playbackDisplayDialogs) {
            alert("ERROR(" + currentOutput.name + " / " + currentOutput.filetype + "): " + e + "  " + e.line);
        }
        app.preferences.rulerUnits = oldPref;
        throw new Error(e.line);
        isCancelled = false;
        return true;
    }
    app.preferences.rulerUnits = oldPref;
    isCancelled = false;
    return false;
}

function SaveOffParameters(sizeInfo) {
    var d = objectToDescriptor(sizeInfo, strMessage);
    app.putCustomOptions("3caa3434-cb67-11d1-bc43-0060b0c2021C", d);
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

    strTitle = localize("$$$/JavaScript/FitImage3/Title=GRIS_C_ReadWriteCSV");
    strConstrainWithin = localize("$$$/JavaScript/FitImage/ConstrainWithin=Constrain Within");
    strTextWidth = localize("$$$/JavaScripts/FitImage/Width=&Width:");
    strTextHeight = localize("$$$/JavaScripts/FitImage/Height=&Height:");
    strTextPixels = localize("$$$/JavaScripts/FitImage/Pixels=pixels");
    strButtonOK = localize("$$$/JavaScripts/FitImage/OK=OK");
    strButtonCancel = localize("$$$/JavaScripts/FitImage/Cancel=Cancel");
    strTextSorry = localize("$$$/JavaScripts/FitImage/Sorry=Sorry, Dialog failed");
    strTextInvalidType = localize("$$$/JavaScripts/FitImage/InvalidType=Invalid numeric value");
    strTextInvalidNum = localize("$$$/JavaScripts/FitImage/InvalidNum=A number between 1 and 300000 is required. Closest value inserted.");
    strTextNeedFile = localize("$$$/JavaScripts/FitImage/NeedFile=You must have a file selected before using Fit Image");
    strMessage = localize("$$$/JavaScripts/FitImage/Message=Fit Image action settings");
    strMustUse = localize("$$$/JavaScripts/ImageProcessor/MustUse=You must use Photoshop CS 2 or later to run this script!");
    strLimitResize = localize("$$$/JavaScripts/FitImage/Limit=Don^}t Enlarge");
}

function FitImage() {
    this.CreateDialog = function () {
        var res =
            "dialog { \
                pAndB: Group { orientation: 'row', \
                    info: Panel { orientation: 'column', borderStyle: 'sunken', \
                        text: '" + strConstrainWithin + "', \
                        w: Group { orientation: 'row', alignment: 'right',\
                            s: StaticText { text:'" + strTextWidth + "' }, \
                            e: EditText { preferredSize: [70, 20] }, \
                            p: StaticText { text:'" + strTextPixels + "'} \
                        }, \
                        h: Group { orientation: 'row', alignment: 'right', \
                            s: StaticText { text:'" + strTextHeight + "' }, \
                            e: EditText { preferredSize: [70, 20] }, \
                            p: StaticText { text:'" + strTextPixels + "'} \
                        }, \
                        l: Group { orientation: 'row', alignment: 'left', \
                            c:Checkbox { text:'" + strLimitResize + "', value:false } \
                        } \
                    }, \
                    buttons: Group { orientation:'column', alignment:'top', \
                        okBtn: Button { text:'" + strButtonOK + "', alignment:'fill', properties:{name:'ok'} }, \
                        cancelBtn: Button { text:'" + strButtonCancel + "', alignment:'fill', properties:{name:'cancel'} } \
                    } \
                } \
            }";
        this.dlgMain = new Window(res, strTitle);
        var d = this.dlgMain;
        d.defaultElement = d.pAndB.buttons.okBtn;
        d.cancelElement = d.pAndB.buttons.cancelBtn;
    };

    this.InitVariables = function () {
        var oldPref = app.preferences.rulerUnits;
        app.preferences.rulerUnits = Units.PIXELS;
        try {
            var desc = app.getCustomOptions("3caa3434-cb67-11d1-bc43-0060b0c2021C");
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
            d.pAndB.info.w.e.text = Number(w);
            d.pAndB.info.h.e.text = Number(h);
            d.pAndB.info.l.c.value = sizeInfo.limit;
        }
        return true;
    };

    this.RunDialog = function () {
        var d = this.dlgMain;
        d.pAndB.buttons.cancelBtn.onClick = function () {
            var dToCancel = FindDialog(this);
            dToCancel.close(false);
        };
        d.onShow = function () { };
        d.pAndB.buttons.okBtn.onClick = function () {
            if (gInAlert == true) {
                gInAlert = false;
                return;
            }
            var wText = d.pAndB.info.w.e.text;
            var hText = d.pAndB.info.h.e.text;
            var lValue = d.pAndB.info.l.c.value;
            var w = Number(wText);
            var h = Number(hText);
            sizeInfo.limit = Boolean(lValue);
            var inputErr = false;
            if (isNaN(w) || isNaN(h)) {
                if (DialogModes.NO != app.playbackDisplayDialogs) {
                    alert(strTextInvalidType);
                }
                if (isNaN(w)) {
                    sizeInfo.width = new UnitValue(1, "px");
                    d.pAndB.info.w.e.text = 1;
                } else {
                    sizeInfo.height = new UnitValue(1, "px");
                    d.pAndB.info.h.e.text = 1;
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
                d.pAndB.info.w.e.text = 1;
            }
            if (w > gMaxResize) {
                inputErr = true;
                sizeInfo.width = new UnitValue(gMaxResize, "px");
                d.pAndB.info.w.e.text = gMaxResize;
            }
            if (h < 1) {
                inputErr = true;
                sizeInfo.height = new UnitValue(1, "px");
                d.pAndB.info.h.e.text = 1;
            }
            if (h > gMaxResize) {
                inputErr = true;
                sizeInfo.height = new UnitValue(gMaxResize, "px");
                d.pAndB.info.h.e.text = gMaxResize;
            }
            if (inputErr == false) {
                sizeInfo.width = new UnitValue(w, "px");
                sizeInfo.height = new UnitValue(h, "px");
                if (SaveImages(w, h)) {
                    // error, input or output size too small
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
    return d;
}

///////////////////////////////////////////////////////////////////////////////
// Function: descriptorToObject
///////////////////////////////////////////////////////////////////////////////
function descriptorToObject(o, d, s, f) {
    var l = d.count;
    if (l) {
        var keyMessage = app.charIDToTypeID('Msge');
        if (d.hasKey(keyMessage) && (s != d.getString(keyMessage)))
            return;
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
    } catch (e) {
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

function SaveTIFF(saveFile, doc) {
    var tiffSaveOptions = new TiffSaveOptions();
    tiffSaveOptions.embedColorProfile = true;
    tiffSaveOptions.alphaChannels = false;
    tiffSaveOptions.layers = false;
    tiffSaveOptions.imageCompression = TIFFEncoding.NONE;
    doc.saveAs(saveFile, tiffSaveOptions, true, Extension.LOWERCASE);
}

function SaveJPEG(saveFile, jpegQuality, doc) {
    if (doc.bitsPerChannel != BitsPerChannelType.EIGHT)
        doc.bitsPerChannel = BitsPerChannelType.EIGHT;
    var jpgSaveOptions = new JPEGSaveOptions();
    jpgSaveOptions.embedColorProfile = true;
    jpgSaveOptions.formatOptions = FormatOptions.STANDARDBASELINE;
    jpgSaveOptions.matte = MatteType.NONE;
    jpgSaveOptions.quality = jpegQuality;
    doc.saveAs(saveFile, jpgSaveOptions, true, Extension.LOWERCASE);
}

function CheckUmlaut(testString) {
    var str = testString;
    str = str.replace(/\u00e4/g, "ae");
    str = str.replace(/\u00c4/g, "Ae");
    str = str.replace(/\u00d6/g, "Oe");
    str = str.replace(/\u00f6/g, "oe");
    str = str.replace(/\u00dc/g, "Ue");
    str = str.replace(/\u00fc/g, "ue");
    str = str.replace(/\u00df/g, "ss");
    return str;
}

function CheckNumbers(testString) {
    var str = testString.split("_");
    var retStr = testString;
    if (str[0].length != 4) {
        retStr = "!" + retStr;
    }
    if (str[1].length != 2) {
        retStr = "!" + retStr;
    }
    return retStr;
}

function MoveLayerTo(fLayer, fX, fY) {
    var Position = fLayer.bounds;
    Position[0] = fX - Position[2] / 2;
    Position[1] = fY - Position[3] / 2;
    fLayer.translate(-Position[0], -Position[1]);
}

function trim(strIn) {
    var str1 = strIn.replace(/^\s+/, '');
    return str1.replace(/\s+$/, '');
}