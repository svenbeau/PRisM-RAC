// GRIS_Wandabbildungen_2024.jsx
// c2025 Sven Schönauer. All rights reserved.
// Written by Florian Mozer 2021 + Sven Schönauer 2024
// Bilder an die Wand für Grisebach, angepasst um als Aktion über alle zu laufen.

#target photoshop

$.localize = false;
var DEBUG_OUTPUT = false;
var isCancelled = true;

// === Konfiguration laden ====================================================
var config = loadScriptConfigForThisScript();
function loadScriptConfigForThisScript() {
    var scriptFile = new File($.fileName);
    var configPath = new File(scriptFile.parent.parent + "/config/script_config.json");
    if (!configPath.exists) {
        alert("Script config not found: " + configPath.fsName);
        return {};
    }
    configPath.open("r");
    var configStr = configPath.read();
    configPath.close();
    try {
        var fullConfig = JSON.parse(configStr);
        var scripts = fullConfig.scripts;
        var currentScriptPath = scriptFile.fsName;
        for (var i = 0; i < scripts.length; i++) {
            if (currentScriptPath.indexOf(scripts[i].script_path) !== -1) {
                return scripts[i];
            }
        }
        return {};
    } catch (e) {
        alert("Error parsing script_config.json: " + e);
        return {};
    }
}

var config_json_folder = config.json_folder || "";
var config_actionFolderName = config.actionFolderName || "";
var config_basicWandFiles = config.basicWandFiles || "";
var config_csvWandFile = config.csvWandFile || "";
var config_wandFileSavePath = config.wandFileSavePath || "";

// === Rest des Skripts ======================================================
// (Hier folgt der restliche Code von GRIS_Wandabbildungen_2024.jsx, der unverändert bleibt)
// … (Restlicher Originalcode) …
// the main routine
// the FitImage object does most of the work
try {

	// create our default params
	var sizeInfo = new SizeInfo();

	GlobalVariables();
	CheckVersion();

	var gIP = new FitImage();

	if ( DialogModes.ALL == app.playbackDisplayDialogs ) {
        gIP.CreateDialog();
        gIP.RunDialog();
	}
	else {
		gIP.InitVariables();
		SaveImages(sizeInfo.width.value, sizeInfo.height.value);
	}

	if (!isCancelled) {
		SaveOffParameters(sizeInfo);
	}

}


// Lot's of things can go wrong
// Give a generic alert and see if they want the details
catch( e ) {
	if ( DialogModes.NO != app.playbackDisplayDialogs ) {
		alert( e + " : " + e.line );
	}
}



// restore the dialog modes
app.displayDialogs = gSaveDialogMode;

isCancelled ? 'cancel' : undefined;

//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////

function SaveImages(width, height) {
    const saveFTP = false;
    importFunctions();

    // Feste Pfadangabe für die JSON-Datei:
    var configjsonpath = '/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/config/JSX_Config/GB_Config_Render.json';
    if (DEBUG_OUTPUT)
        alert(configjsonpath);
    try {
        // Get file object
        var configjsonfile = new File(configjsonpath);
        // open it before reading.
        configjsonfile.open('r');
        // Read and get the content
        var content = configjsonfile.read();
        if (DEBUG_OUTPUT)
            alert("Content: " + content);
        // Parse the configuration into an Object 
        var config = JSON.parse(content);
        if (DEBUG_OUTPUT)
            alert("config: " + config + " recipesPath: " + config.recipesPath);
    } catch (e) {
        alert("Wall error saving " + e + " line: " + e.line);
    }

    /* THE PATH WHERE THE WALLFILES ARE
     *  AND WHERE THE FILES ARE SAVED!
     *  @ SVEN this is to change!!!
     */
    var pathtofiles = config.basicWandFiles;

    var mainPathDwgWall = "//Volumes/rcm_GB/__Render/Wand/";
    var oldPref = app.preferences.rulerUnits;
    var doc = app.activeDocument;
    var filename = (app.activeDocument.name.split("."))[0];

    var wid = doc.width;
    var hei = doc.height;

    const wall1dpi = 23.863;
    const wall2dpi = 23.863;
    const wall3dpi = 23.863;
    const wall4dpi = 23.863;
    const wall5dpi = 25.3992672;
    const wall6dpi = 60.35;

    const dpis = [23.863, 23.863, 23.863, 23.863, 25.3992672, 60.35];
    const files = ["Waende01.psb", "Waende02.psb", "Waende03.psb", "Waende04.psb", "Waende05.psb", "Waende06.psb"];
    const xValues = [2592, 2509, 2509, 2362, 2194, 2362];
    const yValues = [1341, 1604, 1508, 1543, 1498, 1397];

    const afterActions = [
        "06_WeiterverarbeitungWand_Wand01",
        "06_WeiterverarbeitungWand_Wand02",
        "06_WeiterverarbeitungWand_Wand03",
        "06_WeiterverarbeitungWand_Wand04",
        "06_WeiterverarbeitungWand_Wand05",
        "06_WeiterverarbeitungWand_Wand06"
    ];

    const wallSizeLimits = [
        { minHeight: 40, minWidth: 40, maxHeight: 400, maxWidth: 500 },
        { minHeight: 40, minWidth: 40, maxHeight: 400, maxWidth: 500 },
        { minHeight: 40, minWidth: 40, maxHeight: 400, maxWidth: 500 },
        { minHeight: 40, minWidth: 40, maxHeight: 400, maxWidth: 500 },
        { minHeight: 40, minWidth: 40, maxHeight: 400, maxWidth: 500 },
        { minHeight: 0, minWidth: 0, maxHeight: 50, maxWidth: 50 }
    ];

    // Read the Size from the EXIF Headline Field. 
    var s = doc.info.headline;
    if (s != "") {
        if (DEBUG_OUTPUT)
            alert("headline " + s);
        var size = s.split("x");
        var h = parseFloat(size[0]);
        var b = parseFloat(size[1]);

        // Select a random Image of the WallImages based on size
        var validOptions = [];
        for (var i = 0; i < wallSizeLimits.length; i++) {
            var limit = wallSizeLimits[i];
            if ((h >= limit.minHeight && h <= limit.maxHeight) || (b >= limit.minWidth && b <= limit.maxWidth)) {
                validOptions.push(i);
            }
        }
        if (validOptions.length > 0) {
            var randomIndex = Math.floor(Math.random() * validOptions.length);
            var random = validOptions[randomIndex];
        } else {
            alert("No suitable wall image found for the given dimensions.");
            return;
        }
        var randomField = activeDocument.info.instructions;
        if (randomField != "") {
            random = randomField;
        }
        var s = "Random: " + random;
        if (DEBUG_OUTPUT)
            alert(s + " dpi: " + dpis[random] + " file:" + files[random]);
        var image = activeDocument;
        app.preferences.rulerUnits = Units.PIXELS;

        // prepare the PSD
        var layers = doc.artLayers;
        try {
            var freisteller = activeDocument.layers.getByName("Freisteller");
        } catch (e) {
            app.doAction("H011 Wand Alles Freistellen", "Grisebach DOM 2021");
        }
        var freisteller = activeDocument.layers.getByName("Freisteller");
        try {
            var freistellerWand = activeDocument.layers.getByName("Freisteller_Wand");
        } catch (e) {
            freisteller.name = "Freisteller_Wand";
        }
        app.doAction("70 DOM Color 2 Wand (WA)", "Grisebach 2025");
        if (DEBUG_OUTPUT)
            alert("vorbereitet");
        // Resize to the Right dpi and Scale Values; 
        image.resizeImage(new UnitValue(b, "cm"), new UnitValue(h, "cm"), dpis[random]);

        // open the Randomly selected WALL image
        var pathtoWallFile = pathtofiles + files[random];
        var fileRef = new File(pathtoWallFile);
        if (DEBUG_OUTPUT)
            alert("Wandpfad:" + pathtoWallFile);
        var wallImage = app.open(fileRef);

        app.activeDocument = image;
        image.activeLayer.duplicate(wallImage, ElementPlacement.PLACEATBEGINNING);
        app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
        app.activeDocument = wallImage;
        app.activeDocument.activeLayer = activeDocument.artLayers.getByName("insertedImage");
        var imageLayer = app.activeDocument.activeLayer;
        MoveLayerTo(imageLayer, xValues[random], yValues[random]);

        app.doAction(afterActions[random], "Grisebach DOM 2021");

        //#Filename for the websave
        var newName = filename + "_W.psd";
        var outputFile = config.wandFileSavePath + newName;

        var webFile = new File(outputFile);
        if (DEBUG_OUTPUT)
            alert("save as:" + outputFile);

        var psdSaveOptions = new PhotoshopSaveOptions();
        psdSaveOptions.embedColorProfile = true;
        psdSaveOptions.alphaChannels = true;
        // Pfad prüfen und Verzeichnis bei Bedarf erstellen
        if (!webFile.parent.exists) {
            webFile.parent.create();
        }

        // Speichern mit psdSaveOptions
        try {
            wallImage.saveAs(webFile, psdSaveOptions, true, Extension.LOWERCASE);
        } catch (e) {
            alert("Fehler beim Speichern: " + e.message + " line: " + e.line);
        }
    }
    app.preferences.rulerUnits = oldPref; // restore old prefs
    isCancelled = false;
    app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
    return false; // no error
}


// created in
function SaveOffParameters(sizeInfo) {

	// save off our last run parameters
	var d = objectToDescriptor(sizeInfo, strMessage);
	app.putCustomOptions("3cxa3474-ca67-14d1-bc43-0060b1c2024Q", d);
	app.playbackDisplayDialogs = DialogModes.ALL;

	// save off another copy so Photoshop can track them corectly
	var dd = objectToDescriptor(sizeInfo, strMessage);
	app.playbackParameters = dd;
}

function importFunctions(){
    /* jshint ignore:start */
    /**
    * Date.now - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/now
    */
    Date.now||(Date.now=function(){return(new Date).getTime()});
    /**
    * Date.toISOString - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/toISOString
    */
    Date.prototype.toISOString||!function(){function pad(number){return number<10?"0"+number:number}Date.prototype.toISOString=function(){return this.getUTCFullYear()+"-"+pad(this.getUTCMonth()+1)+"-"+pad(this.getUTCDate())+"T"+pad(this.getUTCHours())+":"+pad(this.getUTCMinutes())+":"+pad(this.getUTCSeconds())+"."+(this.getUTCMilliseconds()/1e3).toFixed(3).slice(2,5)+"Z"}}();
    /**
    * JSON - from: https://github.com/douglascrockford/JSON-js
    */
    if(typeof JSON!=='object'){JSON={};}(function(){'use strict';function f(n){return n<10?'0'+n:n;}function this_value(){return this.valueOf();}if(typeof Date.prototype.toJSON!=='function'){Date.prototype.toJSON=function(){return isFinite(this.valueOf())?this.getUTCFullYear()+'-'+f(this.getUTCMonth()+1)+'-'+f(this.getUTCDate())+'T'+f(this.getUTCHours())+':'+f(this.getUTCMinutes())+':'+f(this.getUTCSeconds())+'Z':null;};Boolean.prototype.toJSON=this_value;Number.prototype.toJSON=this_value;String.prototype.toJSON=this_value;}var cx,escapable,gap,indent,meta,rep;function quote(string){escapable.lastIndex=0;return escapable.test(string)?'"'+string.replace(escapable,function(a){var c=meta[a];return typeof c==='string'?c:'\\u'+('0000'+a.charCodeAt(0).toString(16)).slice(-4);})+'"':'"'+string+'"';}function str(key,holder){var i,k,v,length,mind=gap,partial,value=holder[key];if(value&&typeof value==='object'&&typeof value.toJSON==='function'){value=value.toJSON(key);}if(typeof rep==='function'){value=rep.call(holder,key,value);}switch(typeof value){case'string':return quote(value);case'number':return isFinite(value)?String(value):'null';case'boolean':case'null':return String(value);case'object':if(!value){return'null';}gap+=indent;partial=[];if(Object.prototype.toString.apply(value)==='[object Array]'){length=value.length;for(i=0;i<length;i+=1){partial[i]=str(i,value)||'null';}v=partial.length===0?'[]':gap?'[\n'+gap+partial.join(',\n'+gap)+'\n'+mind+']':'['+partial.join(',')+']';gap=mind;return v;}if(rep&&typeof rep==='object'){length=rep.length;for(i=0;i<length;i+=1){if(typeof rep[i]==='string'){k=rep[i];v=str(k,value);if(v){partial.push(quote(k)+(gap?': ':':')+v);}}}}else{for(k in value){if(Object.prototype.hasOwnProperty.call(value,k)){v=str(k,value);if(v){partial.push(quote(k)+(gap?': ':':')+v);}}}}v=partial.length===0?'{}':gap?'{\n'+gap+partial.join(',\n'+gap)+'\n'+mind+'}':'{'+partial.join(',')+'}';gap=mind;return v;}}if(typeof JSON.stringify!=='function'){escapable=/[\\\"\u0000-\u001f\u007f-\u009f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g;meta={'\b':'\\b','\t':'\\t','\n':'\\n','\f':'\\f','\r':'\\r','"':'\\"','\\':'\\\\'};JSON.stringify=function(value,replacer,space){var i;gap='';indent='';if(typeof space==='number'){for(i=0;i<space;i+=1){indent+=' ';}}else if(typeof space==='string'){indent=space;}rep=replacer;if(replacer&&typeof replacer!=='function'&&(typeof replacer!=='object'||typeof replacer.length!=='number')){throw new Error('JSON.stringify');}return str('',{'':value});};}if(typeof JSON.parse!=='function'){cx=/[\u0000\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g;JSON.parse=function(text,reviver){var j;function walk(holder,key){var k,v,value=holder[key];if(value&&typeof value==='object'){for(k in value){if(Object.prototype.hasOwnProperty.call(value,k)){v=walk(value,k);if(v!==undefined){value[k]=v;}else{delete value[k];}}}}return reviver.call(holder,key,value);}text=String(text);cx.lastIndex=0;if(cx.test(text)){text=text.replace(cx,function(a){return'\\u'+('0000'+a.charCodeAt(0).toString(16)).slice(-4);});}if(/^[\],:{}\s]*$/.test(text.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g,'@').replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g,']').replace(/(?:^|:|,)(?:\s*\[)+/g,''))){j=eval('('+text+')');return typeof reviver==='function'?walk({'':j},''):j;}throw new SyntaxError('JSON.parse');};}}());
    /**
    * Object.create - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/create
    */
    "function"!=typeof Object.create&&(Object.create=function(undefined){var Temp=function(){};return function(prototype,propertiesObject){if(prototype!==Object(prototype)&&null!==prototype)throw TypeError("Argument must be an object, or null");Temp.prototype=prototype||{},propertiesObject!==undefined&&Object.defineProperties(Temp.prototype,propertiesObject);var result=new Temp;return Temp.prototype=null,null===prototype&&(result.__proto__=null),result}}());
    /**
    * Array.forEach - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/forEach
    */
    Array.prototype.forEach||(Array.prototype.forEach=function(r,t){var o,n;if(null==this)throw new TypeError(" this is null or not defined");var e=Object(this),i=e.length>>>0;if("function"!=typeof r)throw new TypeError(r+" is not a function");for(arguments.length>1&&(o=t),n=0;i>n;){var a;n in e&&(a=e[n],r.call(o,a,n,e)),n++}});
    /**
    * Array.isArray - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/isArray
    */
    Array.isArray||(Array.isArray=function(arg){return"[object Array]"===Object.prototype.toString.call(arg)});
    /**
    * Array.every - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/every
    */
    Array.prototype.every||(Array.prototype.every=function(callbackfn,thisArg){"use strict";var T,k;if(null==this)throw new TypeError("this is null or not defined");var O=Object(this),len=O.length>>>0;if("function"!=typeof callbackfn)throw new TypeError;for(arguments.length>1&&(T=thisArg),k=0;k<len;){var kValue;if(k in O){kValue=O[k];var testResult=callbackfn.call(T,kValue,k,O);if(!testResult)return!1}k++}return!0});
    /**
    * Array.filter - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/filter
    */
    Array.prototype.filter||(Array.prototype.filter=function(fun){"use strict";if(void 0===this||null===this)throw new TypeError;var t=Object(this),len=t.length>>>0;if("function"!=typeof fun)throw new TypeError;for(var res=[],thisArg=arguments.length>=2?arguments[1]:void 0,i=0;i<len;i++)if(i in t){var val=t[i];fun.call(thisArg,val,i,t)&&res.push(val)}return res});
    /**
    * Array.indexOf - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/indexOf
    */
    Array.prototype.indexOf||(Array.prototype.indexOf=function(searchElement,fromIndex){var k;if(null==this)throw new TypeError('"this" is null or not defined');var o=Object(this),len=o.length>>>0;if(0===len)return-1;var n=+fromIndex||0;if(Math.abs(n)===1/0&&(n=0),n>=len)return-1;for(k=Math.max(n>=0?n:len-Math.abs(n),0);k<len;){if(k in o&&o[k]===searchElement)return k;k++}return-1});
    /**
    * Array.lastIndexOf - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/lastIndexOf
    */
    Array.prototype.lastIndexOf||(Array.prototype.lastIndexOf=function(searchElement){"use strict";if(void 0===this||null===this)throw new TypeError;var n,k,t=Object(this),len=t.length>>>0;if(0===len)return-1;for(n=len-1,arguments.length>1&&(n=Number(arguments[1]),n!=n?n=0:0!=n&&n!=1/0&&n!=-(1/0)&&(n=(n>0||-1)*Math.floor(Math.abs(n)))),k=n>=0?Math.min(n,len-1):len-Math.abs(n);k>=0;k--)if(k in t&&t[k]===searchElement)return k;return-1});
    /**
    * Array.map - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map
    */
    Array.prototype.map||(Array.prototype.map=function(callback,thisArg){var T,A,k;if(null==this)throw new TypeError(" this is null or not defined");var O=Object(this),len=O.length>>>0;if("function"!=typeof callback)throw new TypeError(callback+" is not a function");for(arguments.length>1&&(T=thisArg),A=new Array(len),k=0;k<len;){var kValue,mappedValue;k in O&&(kValue=O[k],mappedValue=callback.call(T,kValue,k,O),A[k]=mappedValue),k++}return A});
    /**
    * Array.reduce - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/Reduce
    */
    Array.prototype.reduce||(Array.prototype.reduce=function(callback){"use strict";if(null==this)throw new TypeError("Array.prototype.reduce called on null or undefined");if("function"!=typeof callback)throw new TypeError(callback+" is not a function");var value,t=Object(this),len=t.length>>>0,k=0;if(2==arguments.length)value=arguments[1];else{for(;k<len&&!(k in t);)k++;if(k>=len)throw new TypeError("Reduce of empty array with no initial value");value=t[k++]}for(;k<len;k++)k in t&&(value=callback(value,t[k],k,t));return value});
    /**
    * Array.some - from: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/some
    */
    Array.prototype.some||(Array.prototype.some=function(fun){"use strict";if(null==this)throw new TypeError("Array.prototype.some called on null or undefined");if("function"!=typeof fun)throw new TypeError;for(var t=Object(this),len=t.length>>>0,thisArg=arguments.length>=2?arguments[1]:void 0,i=0;i<len;i++)if(i in t&&fun.call(thisArg,t[i],i,t))return!0;return!1});
    /* jshint ignore:end */
    if (typeof($) === 'undefined') {
    $ = {};
    }

    $.init = {
        // Evaluate a file and catch the exception.
        evalFile : function (path) {
            try {
                $.evalFile(path);
            } catch (e) {alert('Exception:' + e);}
        },
        // Evaluate all the files in the given folder
        evalFiles: function (jsxFolderPath) {
            var folder = new Folder(jsxFolderPath);
            if (folder.exists) {
                var jsxFiles = folder.getFiles('*.jsx');
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
    //alert("Demo Obj: "+obj);

}

function GlobalVariables() {

	// a version for possible expansion issues
	gVersion = 1.1;

	gMaxResize = 300000;

	// remember the dialog modes
	gSaveDialogMode = app.displayDialogs;
	app.displayDialogs = DialogModes.NO;
    gInAlert = false;

	// all the strings that need to be localized
	strTitle = localize("$$$/JavaScript/FitImage3/Title=GRIS C Wand 2021");
	//strTitle = localize( "$$$/JavaScript/FitImage/Title=Fit Image" );
	strConstrainWithin = localize( "$$$/JavaScript/FitImage/ConstrainWithin=Constrain Within" );
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
	strMustUse = localize( "$$$/JavaScripts/ImageProcessor/MustUse=You must use Photoshop CS 2 or later to run this script!" );
	strLimitResize = localize("$$$/JavaScripts/FitImage/Limit=Don^}t Enlarge");
}

// the main class
function FitImage() {

	this.CreateDialog = function() {

		// I will keep most of the important dialog items at the same level
		// and use auto layout
		// use overriding group so OK/Cancel buttons placed to right of panel

		var res =
			"dialog { \
				pAndB: Group { orientation: 'row', \
					info: Panel { orientation: 'column', borderStyle: 'sunken', \
						text: '" + strConstrainWithin +"', \
						w: Group { orientation: 'row', alignment: 'right',\
							s: StaticText { text:'" + strTextWidth +"' }, \
							e: EditText { preferredSize: [70, 20] }, \
							p: StaticText { text:'" + strTextPixels + "'} \
						}, \
						h: Group { orientation: 'row', alignment: 'right', \
							s: StaticText { text:'" + strTextHeight + "' }, \
							e: EditText { preferredSize: [70, 20] }, \
							p: StaticText { text:'" + strTextPixels + "'} \
						}, \
						l: Group { orientation: 'row', alignment: 'left', \
								c:Checkbox { text: '" + strLimitResize + "', value: false }, \
						} \
					}, \
					buttons: Group { orientation: 'column', alignment: 'top',  \
                          okBtn: Button { text:'" + strButtonOK +"', alignment: 'fill', properties:{name:'ok'} }, \
                          cancelBtn: Button { text:'" + strButtonCancel + "', alignment: 'fill', properties:{name:'cancel'} } \
					} \
				} \
			}";

		// the following, when placed after e: in w and h doesn't show up
		// this seems to be OK since px is put inside the dialog box
		//p: StaticText { text:'" + strTextPixels + "'}

		// create the main dialog window, this holds all our data
		this.dlgMain = new Window(res,strTitle);

		// create a shortcut for easier typing
		var d = this.dlgMain;

		d.defaultElement = d.pAndB.buttons.okBtn;
		d.cancelElement = d.pAndB.buttons.cancelBtn;
	} // end of CreateDialog

	// initialize variables of dialog
	this.InitVariables = function() {

		var oldPref = app.preferences.rulerUnits;
		app.preferences.rulerUnits = Units.PIXELS;

		// look for last used params via Photoshop registry, getCustomOptions will throw if none exist
		try {
			var desc = app.getCustomOptions("3cxa3474-ca67-14d1-bc43-0060b1c2024Q");
			descriptorToObject(sizeInfo, desc, strMessage);
		}

		catch(e) {
			// it's ok if we don't have any options, continue with defaults
		}

		// see if I am getting descriptor parameters
		var fromAction = !!app.playbackParameters.count;
		if( fromAction ){
			// reset sizeInfo to defaults
			SizeInfo = new SizeInfo();
			// set the playback options to sizeInfo
			descriptorToObject(sizeInfo, app.playbackParameters, strMessage);
		}

		// make sure got parameters before this
		if (app.documents.length <= 0) // count of documents viewed
		{
			if ( DialogModes.NO != app.playbackDisplayDialogs ) {
				alert(strTextNeedFile); // only put up dialog if permitted
			}
			app.preferences.rulerUnits = oldPref;
			return false; // if no docs, always return
		}

		var w = app.activeDocument.width;
		var h = app.activeDocument.height;
		var l = true;
		if (sizeInfo.width.value == 0) {
			sizeInfo.width = w;
		}
		else {
			w = sizeInfo.width;
		}
		if (sizeInfo.height.value == 0) {
			sizeInfo.height = h;
		}
		else {
			h = sizeInfo.height;
		}

		app.preferences.rulerUnits = oldPref;
		if ( DialogModes.ALL == app.playbackDisplayDialogs ) {
			var d = this.dlgMain;
			d.ip = this;
			d.pAndB.info.w.e.text = Number(w);
			d.pAndB.info.h.e.text = Number(h);
			d.pAndB.info.l.c.value = sizeInfo.limit;
		}
		return true;
	}

	// routine for running the dialog and it's interactions
	this.RunDialog = function () {
		var d = this.dlgMain;

		// in case hit cancel button, don't close
		d.pAndB.buttons.cancelBtn.onClick = function() {
			var dToCancel = FindDialog( this );
			dToCancel.close( false );
		}

		// nothing for now
		d.onShow = function() {
		}

		// do not allow anything except for numbers 0-9
		//d.pAndB.info.w.e.addEventListener ('keydown', NumericEditKeyboardHandler);

		// do not allow anything except for numbers 0-9
		//d.pAndB.info.h.e.addEventListener ('keydown', NumericEditKeyboardHandler);

		// hit OK, do resize
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

            if ( isNaN( w ) || isNaN( h ) ) {
                if ( DialogModes.NO != app.playbackDisplayDialogs ) {
                    alert( strTextInvalidType );
                }
                if (isNaN( w )) {
                    sizeInfo.width = new UnitValue( 1, "px" );
                    d.pAndB.info.w.e.text = 1;
                } else {
                    sizeInfo.height = new UnitValue( 1, "px" );
                    d.pAndB.info.h.e.text = 1;
                }
                    return false;
            }
            else if (w < 1 || w > gMaxResize || h < 1 || h > gMaxResize) {
                if ( DialogModes.NO != app.playbackDisplayDialogs ) {
                    gInAlert = true;
                    alert( strTextInvalidNum );
                }
            }

            if ( w < 1) {
				inputErr = true;
				sizeInfo.width = new UnitValue( 1, "px" );
				d.pAndB.info.w.e.text = 1;
			}


            if ( w > gMaxResize) {
				inputErr = true;
				sizeInfo.width = new UnitValue( gMaxResize, "px" );
				d.pAndB.info.w.e.text = gMaxResize;
            }

            if ( h < 1) {
				inputErr = true;
				sizeInfo.height = new UnitValue( 1, "px" );
				d.pAndB.info.h.e.text = 1;
            }

            if ( h > gMaxResize) {
				inputErr = true;
				sizeInfo.height = new UnitValue( gMaxResize, "px" );
				d.pAndB.info.h.e.text = gMaxResize;
            }

            if (inputErr == false)  {
                sizeInfo.width = new UnitValue( w, "px" );
                sizeInfo.height = new UnitValue( h, "px" );
                if (SaveImages(w, h)) { // the whole point
                    // error, input or output size too small
                }
                d.close(true);
            }
			return;
		}

		if (!this.InitVariables())
		{
			return true; // handled it
		}

		// give the hosting app the focus before showing the dialog
		app.bringToFront();
		this.dlgMain.center();

		return d.show();
	}
}

function CheckVersion() {
	var numberArray = version.split(".");
	if ( numberArray[0] < 9 ) {
		if ( DialogModes.NO != app.playbackDisplayDialogs ) {
			alert( strMustUse );
		}
		throw( strMustUse );
	}
}

function FindDialog( inItem ) {
	var w = inItem;
	while ( 'dialog' != w.type ) {
		if ( undefined == w.parent ) {
			w = null;
			break;
		}
		w = w.parent;
	}
	return w;
}

///////////////////////////////////////////////////////////////////////////////////
// Function: objectToDescriptor
// Usage: create an ActionDescriptor from a JavaScript Object
// Input: JavaScript Object (o)
//        object unique string (s)
//        Pre process converter (f)
// Return: ActionDescriptor
// NOTE: Only boolean, string, number and UnitValue are supported, use a pre processor
//       to convert (f) other types to one of these forms.
// REUSE: This routine is used in other scripts. Please update those if you
//        modify. I am not using include or eval statements as I want these
//        scripts self contained.
///////////////////////////////////////////////////////////////////////////////////
function objectToDescriptor (o, s, f) {
	if (undefined != f) {
		o = f(o);
	}

	var d = new ActionDescriptor;
	var l = o.reflect.properties.length;
	d.putString( app.charIDToTypeID( 'Msge' ), s );
	for (var i = 0; i < l; i++ ) {
		var k = o.reflect.properties[i].toString();
		if (k == "__proto__" || k == "__count__" || k == "__class__" || k == "reflect")
			continue;
		var v = o[ k ];
		k = app.stringIDToTypeID(k);
		switch ( typeof(v) ) {
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
				if ( v instanceof UnitValue ) {
					var uc = new Object;
					uc["px"] = charIDToTypeID("#Pxl"); // pixelsUnit
					uc["%"] = charIDToTypeID("#Prc"); // unitPercent
					d.putUnitDouble(k, uc[v.type], v.value);
				} else {
					throw( new Error("Unsupported type in objectToDescriptor " + typeof(v) ) );
				}
			}
		}
	}
    return d;
}

///////////////////////////////////////////////////////////////////////////////////
// Function: descriptorToObject
// Usage: update a JavaScript Object from an ActionDescriptor
// Input: JavaScript Object (o), current object to update (output)
//        Photoshop ActionDescriptor (d), descriptor to pull new params for object from
//        object unique string (s)
//        JavaScript Function (f), post process converter utility to convert
// Return: Nothing, update is applied to passed in JavaScript Object (o)
// NOTE: Only boolean, string, number and UnitValue are supported, use a post processor
//       to convert (f) other types to one of these forms.
// REUSE: This routine is used in other scripts. Please update those if you
//        modify. I am not using include or eval statements as I want these
//        scripts self contained.
///////////////////////////////////////////////////////////////////////////////////

function descriptorToObject (o, d, s, f) {
	var l = d.count;
	if (l) {
	    var keyMessage = app.charIDToTypeID( 'Msge' );
        if ( d.hasKey(keyMessage) && ( s != d.getString(keyMessage) )) return;
	}
	for (var i = 0; i < l; i++ ) {
		var k = d.getKey(i); // i + 1 ?
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
				uc[charIDToTypeID("#Rlt")] = "px"; // unitDistance
				uc[charIDToTypeID("#Prc")] = "%"; // unitPercent
				uc[charIDToTypeID("#Pxl")] = "px"; // unitPixels
				var ut = d.getUnitDoubleType(k);
				var uv = d.getUnitDoubleValue(k);
				o[strk] = new UnitValue( uv, uc[ut] );
				}
				break;
			case DescValueType.INTEGERTYPE:
			case DescValueType.ALIASTYPE:
			case DescValueType.CLASSTYPE:
			case DescValueType.ENUMERATEDTYPE:
			case DescValueType.LISTTYPE:
			case DescValueType.OBJECTTYPE:
			case DescValueType.RAWTYPE:
			case DescValueType.REFERENCETYPE:
			default:
				throw( new Error("Unsupported type in descriptorToObject " + t ) );
		}
	}
	if (undefined != f) {
		o = f(o);
	}
}

///////////////////////////////////////////////////////////////////////////////////
// Function: SizeInfo
// Usage: object for holding the dialog parameters
// Input: <none>
// Return: object holding the size info
///////////////////////////////////////////////////////////////////////////////////
function SizeInfo() {
    this.height = new UnitValue( 0, "px" );
    this.width = new UnitValue( 0, "px" );
    this.limit = false;
}

///////////////////////////////////////////////////////////////////////////////////
// Function: NumericEditKeyboardHandler
// Usage: Do not allow anything except for numbers 0-9
// Input: ScriptUI keydown event
// Return: <nothing> key is rejected and beep is sounded if invalid
///////////////////////////////////////////////////////////////////////////////////
function NumericEditKeyboardHandler (event) {

    try {

        var keyIsOK = KeyIsNumeric (event) ||
					  KeyIsDelete (event) ||
					  KeyIsLRArrow (event) ||
					  KeyIsTabEnterEscape (event);



        if (! keyIsOK) {
            //    Bad input: tell ScriptUI not to accept the keydown event
            event.preventDefault();

            /*    Notify user of invalid input: make sure NOT
			       to put up an alert dialog or do anything which
		                 requires user interaction, because that
		                 interferes with preventing the 'default'
		                 action for the keydown event */
            app.beep();
        }
    }
    catch (e) {
        ; // alert ("Ack! bug in NumericEditKeyboardHandler: " + e);
    }
}

//    key identifier functions
function KeyHasModifier (event) {
    return event.shiftKey || event.ctrlKey || event.altKey || event.metaKey;
}

function KeyIsNumeric (event) {
    return  (event.keyName >= '0') && (event.keyName <= '9') && ! KeyHasModifier (event);
}

function KeyIsDelete (event) {
    //    Shift-delete is ok
    return ((event.keyName == 'Backspace') || (event.keyName == 'Delete')) && ! (event.ctrlKey);
}

function KeyIsLRArrow (event) {
    return ((event.keyName == 'Left') || (event.keyName == 'Right')) && ! (event.altKey || event.metaKey);
}

function KeyIsTabEnterEscape (event) {
	return event.keyName == 'Tab' || event.keyName == 'Enter' || event.keyName == 'Escape';
}

function SaveTIFF(saveFile, doc){  
tiffSaveOptions = new TiffSaveOptions();   
tiffSaveOptions.embedColorProfile = true;   
tiffSaveOptions.alphaChannels = false;   
tiffSaveOptions.layers = false;  
tiffSaveOptions.imageCompression = TIFFEncoding.NONE;  
doc.saveAs(saveFile, tiffSaveOptions, true,Extension.LOWERCASE);  
}
function SaveJPEG(saveFile, jpegQuality, doc){  

if (doc.bitsPerChannel != BitsPerChannelType.EIGHT) doc.bitsPerChannel = BitsPerChannelType.EIGHT;  
jpgSaveOptions = new JPEGSaveOptions();  
jpgSaveOptions.embedColorProfile = true;  
jpgSaveOptions.formatOptions = FormatOptions.STANDARDBASELINE;  
jpgSaveOptions.matte = MatteType.NONE;  
jpgSaveOptions.quality = jpegQuality;   
doc.saveAs(saveFile, jpgSaveOptions, true,Extension.LOWERCASE);  
} 
function CheckUmlaut(testString) {
        // Ü, ü     \u00dc, \u00fc
        // Ä, ä     \u00c4, \u00e4
        // Ö, ö     \u00d6, \u00f6
        // ß        \u00df
        var str = testString;
        str = str.replace(/\u00e4/g, "ae")
        str = str.replace(/\u00c4/g, "Ae")
        str = str.replace(/\u00d6/g, "Oe")
        str = str.replace(/\u00f6/g, "oe")
        str = str.replace(/\u00dc/g, "Ue")
        str = str.replace(/\u00fc/g, "ue")
        str = str.replace(/\u00df/g, "ss")
        return str;

}
function CheckNumbers(testString) {
    var str = testString.split("_");
    var retStr = testString;
    if(str[0].length != 4){
        retStr = "!"+retStr;
        }
    if(str[1].length != 2) {
        retStr = "!"+retStr;
        }
    return retStr;
    }

//******************************************
// MOVE LAYER TO
// Author: Max Kielland
//
// Moves layer fLayer to the absolute
// position fX,fY. The unit of fX and fY are
// the same as the ruler setting. 
function MoveLayerTo(fLayer,fX,fY) {

  var Position = fLayer.bounds;
  Position[0] = fX - Position[2]/2;
  Position[1] = fY - Position[3]/2;

  fLayer.translate(-Position[0],-Position[1]);
}

// End Fit Image.jsx
