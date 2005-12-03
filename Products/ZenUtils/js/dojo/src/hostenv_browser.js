/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above *//**
* @file hostenv_browser.js
*
* Implements the hostenv interface for a browser environment. 
*
* Perhaps it could be called a "dom" or "useragent" environment.
*
* @author Copyright 2004 Mark D. Anderson (mda@discerning.com)
* @author Licensed under the Academic Free License 2.1 http://www.opensource.org/licenses/afl-2.1.php
*/

// make jsc shut up (so we can use jsc to sanity check the code even if it will never run it).
/*@cc_on
@if (@_jscript_version >= 7)
var window; var XMLHttpRequest;
@end
@*/

dj_addNodeEvtHdlr = function(node, evtName, fp, capture){
	if(node.attachEvent){
		node.attachEvent("on"+evtName, fp);
	}else if(node.addEventListener){ // FIXME: test w/ Safari!
		node.addEventListener(evtName, fp, capture);
	}else{
		// node["on"+evtName]=fp;
		var oldHandler = node["on"+evtName];
		if(typeof oldHandler != "undefined"){
			node["on"+evtName]=function(){
				fp.apply(node, arguments);
				oldHandler.apply(node, arguments);
			}
		}else{
			node["on"+evtName]=fp;
		}
	}
	return true;
}

if(typeof window == 'undefined'){
	dj_throw("no window object");
}

// attempt to figure out the path to dojo if it isn't set in the config
(function() {
	if((dojo.hostenv["base_script_uri_"] == "" || dojo.hostenv["base_relative_path_"] == "")
		&& document && document.getElementsByTagName) {
		var scripts = document.getElementsByTagName("script");
		var rePkg = /(__package__|dojo)\.js$/i;
		for(var i = 0; i < scripts.length; i++) {
			var src = scripts[i].getAttribute("src");
			if( rePkg.test(src) ) {
				var root = src.replace(rePkg, "");
				if(dojo.hostenv["base_script_uri_"] == "") { dojo.hostenv["base_script_uri_"] = root; }
				if(dojo.hostenv["base_relative_path_"] == "") { dojo.hostenv["base_relative_path_"] = root; }
				break;
			}
		}
	}
})();

with(dojo.render){
	html.UA = navigator.userAgent;
	html.AV = navigator.appVersion;
	html.capable = true;
	html.support.builtin = true;

	ver = parseFloat(html.AV);
	os.mac = html.AV.indexOf("Macintosh") == -1 ? false : true; 
	os.win = html.AV.indexOf("Windows") == -1 ? false : true; 

	html.opera = html.UA.indexOf("Opera") == -1 ? false : true; 
	html.khtml = ((html.AV.indexOf("Konqueror") >= 0)||(html.AV.indexOf("Safari") >= 0)) ? true : false; 
	html.safari = (html.AV.indexOf("Safari") >= 0) ? true : false; 
	html.mozilla = html.moz = ((html.UA.indexOf("Gecko") >= 0)&&(!html.khtml)) ? true : false; 
	html.ie = ((document.all)&&(!html.opera)) ? true : false;
	html.ie50 = html.ie && html.AV.indexOf("MSIE 5.0")>=0;
	html.ie55 = html.ie && html.AV.indexOf("MSIE 5.5")>=0;
	html.ie60 = html.ie && html.AV.indexOf("MSIE 6.0")>=0;

	/*
	// FIXME: need to check for the various SVG plugins and builtin
	// capabilities (as w/ Moz+SVG)
	svg.capable = false;
	// svg.support.plugin = true;
	// svg.support.builtin = false;
	// svg.adobe = true;
	*/
};

dojo.hostenv.startPackage("dojo.hostenv");

dojo.hostenv.name_ = 'browser';
dojo.hostenv.searchIds = [];

// These are in order of decreasing likelihood; this will change in time.
var DJ_XMLHTTP_PROGIDS = ['Msxml2.XMLHTTP', 'Microsoft.XMLHTTP', 'Msxml2.XMLHTTP.4.0'];

dojo.hostenv.getXmlhttpObject = function(){
    var http = null;
	var last_e = null;
	try{ http = new XMLHttpRequest(); }catch(e){}
    if(!http){
		for(var i=0; i<3; ++i){
			var progid = DJ_XMLHTTP_PROGIDS[i];
			try{
				http = new ActiveXObject(progid);
			}catch(e){
				last_e = e;
			}

			if(http){
				DJ_XMLHTTP_PROGIDS = [progid];  // so faster next time
				break;
			}
		}
	}

	if((last_e)&&(!http)){
		dj_rethrow("Could not create a new ActiveXObject using any of the progids " + DJ_XMLHTTP_PROGIDS.join(', '), last_e);
	}else if(!http){
		return dj_throw("No XMLHTTP implementation available, for uri " + uri);
	}

	return http;
}

/**
 * Read the contents of the specified uri and return those contents.
 *
 * @param uri A relative or absolute uri. If absolute, it still must be in the same "domain" as we are.
 * @param async_cb If not specified, load synchronously. If specified, load asynchronously, and use async_cb as the progress handler which takes the xmlhttp object as its argument. If async_cb, this function returns null.
 * @param fail_ok Default false. If fail_ok and !async_cb and loading fails, return null instead of throwing.
 */ 
dojo.hostenv.getText = function(uri, async_cb, fail_ok){
	
	var http = this.getXmlhttpObject();

	if(async_cb){
		http.onreadystatechange = function(){ 
			if((4==http.readyState)&&(http["status"])){
				if(http.status==200){
					dj_debug("LOADED URI: "+uri);
					async_cb(http.responseText);
				}
			}
		}
	}

	http.open('GET', uri, async_cb ? true : false);
	http.send(null);
	if(async_cb){
		return null;
	}
	
	return http.responseText;
}

/*
 * It turns out that if we check *right now*, as this script file is being loaded,
 * then the last script element in the window DOM is ourselves.
 * That is because any subsequent script elements haven't shown up in the document
 * object yet.
 */
function dj_last_script_src() {
    var scripts = window.document.getElementsByTagName('script');
    if(scripts.length < 1){ 
		dj_throw("No script elements in window.document, so can't figure out my script src"); 
	}
    var script = scripts[scripts.length - 1];
    var src = script.src;
    if(!src){
		dj_throw("Last script element (out of " + scripts.length + ") has no src");
	}
    return src;
}

if(!dojo.hostenv["library_script_uri_"]){
	dojo.hostenv.library_script_uri_ = dj_last_script_src();
}

dojo.hostenv.println = function(s){
	var ti = null;
	var dis = "<div>"+s+"</div>";
	try{
		ti = document.createElement("div");
		document.body.appendChild(ti);
		ti.innerHTML = s;
	}catch(e){
		try{
			// safari needs the output wrapped in an element for some reason
			document.write(dis);
		}catch(e2){
			window.status = s;
		}
	}
	delete ti;
	delete dis;
	delete s;
}

dj_addNodeEvtHdlr(window, "load", function(){
	if(dojo.render.html.ie) {
		dojo.hostenv.makeWidgets();
	}
	dojo.hostenv.modulesLoaded();
});


dojo.hostenv.makeWidgets = function(){
	if((dojo.hostenv.auto_build_widgets_)||(dojo.hostenv.searchIds.length > 0)){
		if(dj_eval_object_path("dojo.widget.Parse")){
			// we must do this on a delay to avoid:
			//	http://www.shaftek.org/blog/archives/000212.html
			// IE is such a tremendous peice of shit.
			try{
				var parser = new dojo.xml.Parse();
				var sids = dojo.hostenv.searchIds;
				if(sids.length > 0){
					for(var x=0; x<sids.length; x++){
						if (!document.getElementById(sids[x])) { continue; }
						var frag = parser.parseElement(document.getElementById(sids[x]), null, true);
						dojo.widget.getParser().createComponents(frag);
					}
				}else if(dojo.hostenv.auto_build_widgets_){
					var frag  = parser.parseElement(document.body, null, true);
					dojo.widget.getParser().createComponents(frag);
				}
			}catch(e){
				dj_debug("auto-build-widgets error:", e);
			}
		}
	}
}

dojo.hostenv.modulesLoadedListeners.push(function(){
	if(!dojo.render.html.ie) {
		dojo.hostenv.makeWidgets();
	}
});

// we assume that we haven't hit onload yet. Lord help us.
if((!window["djConfig"])||(!window["djConfig"]["preventBackButtonFix"])){
	document.write("<iframe style='border: 0px; width: 1px; height: 1px; position: absolute; bottom: 0px; right: 0px; visibility: visible;' name='djhistory' id='djhistory' src='"+(dojo.hostenv.getBaseScriptUri()+'iframe_history.html')+"'></iframe>");
}

// stub, over-ridden by debugging code. This will at least keep us from
// breaking when it's not included
dojo.hostenv.writeIncludes = function(){} 
