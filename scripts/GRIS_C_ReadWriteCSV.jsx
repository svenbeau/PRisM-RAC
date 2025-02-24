// c2008 recom, Inc. All rights reserved.
// Written by Florian Mozer 2021
//Lesen der CSV Infos - angepasst um über alle laufen zu können

/*
@@@BUILDINFO@@@ GRIS_C_ReadWriteCSV.jsx 1.0.0.2
*/

/* Special properties for a JavaScript to enable it to behave like an automation plug-in, the variable name must be exactly
   as the following example and the variables must be defined in the top 1000 characters of the file

// BEGIN__HARVEST_EXCEPTION_ZSTRING
<javascriptresource>
<name>GRIS_C_ReadWriteCSV</name>
<category>GRIS2021_W</category>
<menu>automate</menu>
<enableinfo>true</enableinfo>
<eventid>3caa3434-cb67-11d1-bc43-0060b0c2021C</eventid>
<terminology><![CDATA[<< /Version 1
                         /Events <<
                          /3caa3434-cb67-11d1-bc43-0060b0c2021C [($$$/AdobePlugin/FitImageCSV/Name=GRIS_C_ReadWriteCSV) /imageReference <<
	                       /width [($$$/AdobePlugin/FitImage/Width=width) /pixelsUnit]
	                       /height [($$$/AdobePlugin/FitImage/Height=height) /pixelsUnit]
	                       /limit [($$$/AdobePlugin/FitImage/limit=Don't Enlarge) /boolean]
                          >>]
                         >>
                      >> ]]></terminology>
</javascriptresource>
// END__HARVEST_EXCEPTION_ZSTRING
*/

// enable double clicking from the Macintosh Finder or the Windows Explorer
#target photoshop

// debug level: 0-2 (0:disable, 1:break on error, 2:break at beginning)
// $.level = 1;
// debugger; // launch debugger on next line

// on localized builds we pull the $$$/Strings from a .dat file, see documentation for more details
$.localize = true;

var isCancelled = true; // assume cancelled until actual resize occurs

var DEBUG_OUTPUT = false;

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

	importFunctions();

	// Use absolute path for the JSON file.
	// Fester Pfad zur Konfigurationsdatei:
	var configjsonpath = '/Users/sschonauer/Documents/PycharmProjects/PRisM-RAC/config/JSX_Config/GB_Config_Render.json';
	if(DEBUG_OUTPUT)
		alert(configjsonpath);
	try{
		// Get file object
		var configjsonfile = new File(configjsonpath);

		// open it before reading.
		configjsonfile.open('r');
		

		// Read and get the content
		var content = configjsonfile.read();
		if(DEBUG_OUTPUT)
			alert("Content: " + content);
		//Parse the configuration into an Object 
		var config = JSON.parse(content);


		if(DEBUG_OUTPUT)
			alert ("config: " + config + " recipesPath: " + config.recipesPath);

	//Der Pfad zur CSV Datei steht jetzt in der GrisConfig datei.  
    var csvPath = config.csvWandFile; 
	// var csvPath = "/Users/fmozer/Desktop/Wandskript_ueberarbeitete/fuer_Flo/2020_10_28_13Uhr_OO_704_Recom_bearb_fs.csv"; 
	
	// Das ist das #Dateiobjekt für die csv
	var csvFile = new File(csvPath);
	
	//der Dateiname wird getrennt. 
	//4058933_Kuenstler_3021_03_abg // Demodateiname mit allem 
	// ohne 
	var filename = (app.activeDocument.name.split ("."))[0];
	var doc = app.activeDocument;
	var nameparts  = filename.split("_");
	var kdID =  nameparts[0];
	var kdVariant = nameparts[(nameparts.length - 1)];
	

	if(DEBUG_OUTPUT)
			alert ("filename: " + filename + " kdID: " + kdID + " kdVariant: " + kdVariant);

	if(!(isNaN(kdVariant))){
		kdVariant = "";
		//alert("noVariant")
	} else {
		//alert("VARIANT: "+kdVariant)
	}

    var oldPref = app.preferences.rulerUnits;
   
    doc.info.headline = "";
	doc.info.instructions = "";
    
    var h = 0;
    var w = 0;
	var rand = 0;
	
	// there was the try

	csvFile.open('r');
	var line1 = csvFile.readln();
	if(DEBUG_OUTPUT)
			alert ("line1: " + line1 + " from csv: " + csvPath);
	
    var found = false;
	while(!csvFile.eof){
		var line = csvFile.readln();
		//alert(line);
		
			var splittedLine = line.split(";");

			if(splittedLine[0] != ""){
				var kdIDCsV = splittedLine[0];
				var kdVariantCSV = splittedLine[1];
				//This is the searching and checking
				if(kdID == kdIDCsV){
					if(kdVariantCSV == "" && kdVariant == ""){
						if(DEBUG_OUTPUT)
							alert ("found in line: " + line);
	
						//	alert("found"+line);
						h = splittedLine[2];
						b = splittedLine[3];
						rand = splittedLine[6];
						found = true;
						//alert("h: "+ h + " b: "+ b + "rand: " + rand + ";");
					}
					if(kdVariantCSV != ""){
						//alert("kdVariant: "+kdVariant+ " kdVarCSV: "+kdVariantCSV);
						if(kdVariant == kdVariantCSV){
							if(DEBUG_OUTPUT)
								alert ("found with variant in line: " + line);
	
							//	alert("found"+line);
							h = splittedLine[2];
							b = splittedLine[3];
							rand = splittedLine[6];
							found = true;
							//alert("h: "+ h + " b: "+ b + "rand: " + rand + ";");
						}
					}
				}
			}
	}
    if(!found){
        if(DEBUG_OUTPUT)
			alert("Keine CSV_Info für Datei " + filename);
	
    }
	
	csvFile.close();
	} catch (e){
		alert ("closingError: " + e.strMessage + " line: " + e.line);
	}

	//write the info to the headline.  	
	if(found){
		try {
		
		doc.info.headline = h + "x" + b;
		doc.info.instructions = rand;
		//alert("written the doc info");
		} catch (e) {
			alert("error writing in the file " + e);
		}
	}	
    app.preferences.rulerUnits = oldPref; // restore old prefs
	isCancelled = false; // if get here, definitely executed
	return false; // no error

}


// created in
function SaveOffParameters(sizeInfo) {

	// save off our last run parameters
	var d = objectToDescriptor(sizeInfo, strMessage);
	app.putCustomOptions("3caa3434-cb67-11d1-bc43-0060b0c2021C", d);
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
	strTitle = localize("$$$/JavaScript/FitImage3/Title=GRIS_C_ReadWriteCSV");
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
			var desc = app.getCustomOptions("3caa3434-cb67-11d1-bc43-0060b0c2021C");
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
function trim (strIn) {
	var str1 = strIn.replace(/^\s+/,'')
	return str1.replace(/\s+$/,'');
}
// End Fit Image.jsx

