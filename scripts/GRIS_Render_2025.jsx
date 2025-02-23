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

// the main routine
// the FitImage object does most of the work
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
//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////

function ResizeTheImage(width, height) {
    var oldPref = app.preferences.rulerUnits;

    importFunctions();

    var originalUnit = preferences.rulerUnits;
    preferences.rulerUnits = Units.PIXELS;

    var document = app.activeDocument;
    var filename = (app.activeDocument.name.split("."))[0];
    var backside = checkBackside(filename);

    if (backside) {
        filename = filename.substr(0, filename.length - 2);
        if (DEBUG_OUTPUT) alert("istRückseite: \n" + filename);
    }

    var configjsonfile = '/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/config/JSX_Config/GB_Config_Render.json';
    if (DEBUG_OUTPUT) alert(configjsonfile);

    try {
        var configjsonfile = new File(configjsonfile);
        configjsonfile.open('r');
        var content = configjsonfile.read();
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
			alert( "ERROR("+currentOutput.name+" / "+currentOutput.filetype+"): "+e + "  " + e.line );
		}
		app.preferences.rulerUnits = oldPref;
		throw new Error(e.line)
		e.line;
		isCancelled = false
		return true
	}
    app.preferences.rulerUnits = oldPref; // restore old prefs
	isCancelled = false; // if get here, definitely executed
	return false; // no error
}

//Hilfsfunktionen


function checkBackside(filename){
    var nameParts = filename.split("_")
    if(nameParts[nameParts.length-1]=="F"){
        return true
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
    options.quality = 8; // Qualität von 0 bis 12, hier 8 als Beispiel

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
        options.interlaced = false; // Kein Interlacing
        // Die höchste Kompression erfolgt standardmäßig, da keine direkte API für den gezeigten Dialog existiert.

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

// created in
function SaveOffParameters(sizeInfo) {

	// save off our last run parameters
	var d = objectToDescriptor(sizeInfo, strMessage);
	app.putCustomOptions("3cax3434-cb67-12d1-bc43-0060b0a13cc1", d);
	app.playbackDisplayDialogs = DialogModes.ALL;

	// save off another copy so Photoshop can track them corectly
	var dd = objectToDescriptor(sizeInfo, strMessage);
	app.playbackParameters = dd;
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
	strTitle = "Grisebach Render Skript";
	strConstrainWithin =  "Beschränken" ;
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
	strMustUse =  "You must use Photoshop CS 2 or later to run this script!" ;
	strLimitResize = "nicht vergrößern";
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
							e: EditNumber { preferredSize: [70, 20] }, \
							p: StaticText { text:'" + strTextPixels + "'} \
						}, \
						h: Group { orientation: 'row', alignment: 'right', \
							s: StaticText { text:'" + strTextHeight + "' }, \
							e: EditNumber { preferredSize: [70, 20] }, \
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
		d.pAndB.info.w.e.minvalue = 1;
		d.pAndB.info.w.e.maxvalue = gMaxResize;
		d.pAndB.info.h.e.minvalue = 1;
		d.pAndB.info.h.e.maxvalue = gMaxResize;
	} // end of CreateDialog

	// initialize variables of dialog
	this.InitVariables = function() {

		var oldPref = app.preferences.rulerUnits;
		app.preferences.rulerUnits = Units.PIXELS;

		// look for last used params via Photoshop registry, getCustomOptions will throw if none exist
		try {
			var desc = app.getCustomOptions("3cax3434-cb67-12d1-bc43-0060b0a13cc1");
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
			d.pAndB.info.w.e.value = Number(w);
			d.pAndB.info.h.e.value = Number(h);
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

            var lValue = d.pAndB.info.l.c.value;
            var w = d.pAndB.info.w.e.value;
            var h = d.pAndB.info.h.e.value;
            sizeInfo.limit = Boolean(lValue);
            var inputErr = false;

            if ( isNaN( w ) || isNaN( h ) ) {
                if ( DialogModes.NO != app.playbackDisplayDialogs ) {
                    alert( strTextInvalidType );
                }
                if (isNaN( w )) {
                    sizeInfo.width = new UnitValue( 1, "px" );
                    d.pAndB.info.w.e.value = 1;
                } else {
                    sizeInfo.height = new UnitValue( 1, "px" );
                    d.pAndB.info.h.e.value = 1;
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
				d.pAndB.info.w.e.value = 1;
			}


            if ( w > gMaxResize) {
				inputErr = true;
				sizeInfo.width = new UnitValue( gMaxResize, "px" );
				d.pAndB.info.w.e.value = gMaxResize;
            }

            if ( h < 1) {
				inputErr = true;
				sizeInfo.height = new UnitValue( 1, "px" );
				d.pAndB.info.h.e.value = 1;
            }

            if ( h > gMaxResize) {
				inputErr = true;
				sizeInfo.height = new UnitValue( gMaxResize, "px" );
				d.pAndB.info.h.e.value = gMaxResize;
            }

            if (inputErr == false)  {
                sizeInfo.width = new UnitValue( w, "px" );
                sizeInfo.height = new UnitValue( h, "px" );
                if (ResizeTheImage(w, h)) { // the whole point
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

///////////////////////////////////////////////////////////////////////////////
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
///////////////////////////////////////////////////////////////////////////////
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

///////////////////////////////////////////////////////////////////////////////
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
///////////////////////////////////////////////////////////////////////////////

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

///////////////////////////////////////////////////////////////////////////////
// Function: SizeInfo
// Usage: object for holding the dialog parameters
// Input: <none>
// Return: object holding the size info
///////////////////////////////////////////////////////////////////////////////
function SizeInfo() {
    this.height = new UnitValue( 0, "px" );
    this.width = new UnitValue( 0, "px" );
    this.limit = false;
}

///////////////////////////////////////////////////////////////////////////////
// Function: NumericEditKeyboardHandler
// Usage: Do not allow anything except for numbers 0-9
// Input: ScriptUI keydown event
// Return: <nothing> key is rejected and beep is sounded if invalid
///////////////////////////////////////////////////////////////////////////////
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
// End Fit Image.jsx

