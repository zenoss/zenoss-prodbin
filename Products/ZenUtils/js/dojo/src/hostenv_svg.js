/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above *///	hostenv_svg
if(typeof window == 'undefined'){
	dj_throw("attempt to use adobe svg hostenv when no window object");
}
dj_debug = function(){ 
	var args = arguments;
	if(!dojo.hostenv.is_debug_){ return; }
	var isJUM = dj_global["jum"];
	var s = isJUM ? "": "DEBUG: ";
	for (var i = 0; i < args.length; ++i){ s += args[i]; }
	if (isJUM){ // this seems to be the only way to get JUM to "play nice"
		jum.debug(s);
	} else{ 
		dojo.hostenv.println(s);
	}
};

//	set up dojo.render.
dojo.render.name = navigator.appName;
dojo.render.ver = parseFloat(navigator.appVersion, 10);
switch(navigator.platform){
	case "MacOS":
		dojo.render.os.osx =  true;
		break;
	case "Linux":
		dojo.render.os.linux =  true;
		break;
	case "Windows":
		dojo.render.os.win =  true;
		break;
	default:
		dojo.render.os.linux = true;
		break;
};
dojo.render.svg.capable = true;
dojo.render.svg.support.builtin = true;
//	FIXME the following two is a big-ass hack for now.
dojo.render.svg.moz = ((navigator.userAgent.indexOf("Gecko") >= 0) && (!((navigator.appVersion.indexOf("Konqueror") >= 0) || (navigator.appVersion.indexOf("Safari") >= 0))));
dojo.render.svg.adobe = !dojo.render.svg.moz;

//	agent-specific implementations.

//	from old hostenv_adobesvg.
dojo.hostenv.startPackage("dojo.hostenv");
dojo.hostenv.println = function(s){ 
	try {
		var ti = document.createElement("text");
		ti.setAttribute("x","50");
		ti.setAttribute("y", (25 + 15 * document.getElementsByTagName("text").length));
		ti.appendChild(document.createTextNode(s));
		document.documentElement.appendChild(ti);
	} catch(e){ }
};
dojo.hostenv.name_ = "svg";

//	expected/defined by bootstrap1.js
dojo.hostenv.setModulePrefix = function(module, prefix){ };
dojo.hostenv.getModulePrefix = function(module){ };
dojo.hostenv.getTextStack = [];
dojo.hostenv.loadUriStack = [];
dojo.hostenv.loadedUris = [];
dojo.hostenv.modules_ = {};
dojo.hostenv.modulesLoadedFired = false;
dojo.hostenv.modulesLoadedListeners = [];
dojo.hostenv.getText = function(uri, cb, data){ 
	if (!cb) var cb = function(result){ window.alert(result); };
	if (!data) {
		window.getUrl(uri, cb);
	} else {
		window.postUrl(uri, data, cb);
	}
};
dojo.hostenv.getLibaryScriptUri = function(){ };

dojo.hostenv.loadUri = function(uri){ };
dojo.hostenv.loadUriAndCheck = function(uri, module){ };

//	aliased in bootstrap2, don't ignore
//	we are going to kill loadModule for the first round of SVG stuff, and include shit manually.
dojo.hostenv.loadModule = function(moduleName){
	//	just like startPackage, but this time we're just checking to make sure it exists already.
	var a = moduleName.split(".");
	var currentObj = window;
	var s = [];
	for (var i = 0; i < a.length; i++){
		if (a[i] == "*") continue;
		s.push(a[i]);
		if (!currentObj[a[i]]){
			dj_throw("dojo.require('" + moduleName + "'): module does not exist.");
		} else currentObj = currentObj[a[i]];
	}
	return; 
};
dojo.hostenv.startPackage = function(moduleName){
	var a = moduleName.split(".");
	var currentObj = window;
	var s = [];
	for (var i = 0; i < a.length; i++){
		if (a[i] == "*") continue;
		s.push(a[i]);
		if (!currentObj[a[i]]) currentObj[a[i]] = {};
		currentObj = currentObj[a[i]];
	}
	return; 
};
