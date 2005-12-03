/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above *//**
* @file bootstrap1.js
*
* bootstrap file that runs before hostenv_*.js file.
*
* @author Copyright 2004 Mark D. Anderson (mda@discerning.com)
* @author Licensed under the Academic Free License 2.1 http://www.opensource.org/licenses/afl-2.1.php
*
* $Id: bootstrap1.js 1321 2005-08-29 23:04:48Z alex $
*/

/**
 * The global djConfig can be set prior to loading the library, to override certain settings.
 * It does not exist under dojo.* so that it can be set before the dojo variable exists.
 * Setting any of these variables *after* the library has loaded does nothing at all.
 * The variables that can be set are as follows:
 *
 * <dl>
 * <dt>baseScriptUri
 *  <dd>The value that getBaseScriptUri() will return. It is the base URI for loading modules.
 *  If not set in config, we find it using libraryScriptUri (stripping out the name part).
 *
 * <dt>baseRelativePath
 *  <dd>How to get from the parent URI of the URI defining the bootstrap code (libraryScriptUri)
 *  to the base URI. Defaults to '' (meaning that the bootstrap code sits in the top).
 *  If it is non-empty, it has to have a trailing '/'.
 *
 * <dt>libraryScriptUri
 *  <dd>Unless set in config, in a browser environment, this is the full
 *  value of the 'src' attribute of our script element.
 *  In a command line, this is the argument specifying the library file.
 *  If you set baseScriptUri, this is ignored.
 *  Setting it saves us the effort of trying to figure it out, but you
 *  might as well just set baseScriptUri instead.
 *
 * <dt>isDebug
 *  <dd>whether debug output is enabled.
 * </dl>
 */
/**
 * dj_global is an alias for the top-level global object in the host environment (the "window" object in a browser).
 */
//:GLVAR Object dj_global
var dj_global = this; //typeof window == 'undefined' ? this : window;


function dj_undef(name, obj){
	if(!obj){ obj = dj_global; }
	return (typeof obj[name] == "undefined");
}

/*
 * private utility to  evaluate a string like "A.B" without using eval.
 */
function dj_eval_object_path(objpath, create){
	// fast path for no periods
	if(typeof objpath != "string"){ return dj_global; }
	if(objpath.indexOf('.') == -1){
		// dj_debug("typeof this[",objpath,"]=",typeof(this[objpath]), " and typeof dj_global[]=", typeof(dj_global[objpath])); 
		// dojo.hostenv.println(typeof dj_global[objpath]);
		// return (typeof dj_global[objpath] == 'undefined') ? undefined : dj_global[objpath];
		return dj_undef(objpath) ? undefined : dj_global[objpath];
	}

	var syms = objpath.split(/\./);
	var obj = dj_global;
	for(var i=0;i<syms.length;++i){
		if(!create){
			obj = obj[syms[i]];
			if((typeof obj == 'undefined')||(!obj)){
				return obj;
			}
		}else{
			if(dj_undef(syms[i], obj)){
				obj[syms[i]] = {};
			}
			obj = obj[syms[i]];
		}
	}
	return obj;
}


//:GLVAR Object djConfig
if(dj_undef("djConfig")){
	var djConfig = {};
}

/**
 * dojo is the root variable of (almost all) our public symbols.
 */
var dojo;
if(dj_undef("dojo")){ dojo = {}; }

dojo.version = {
	major: 0, minor: 1, patch: 0,
	revision: Number("$Rev: 1321 $".match(/[0-9]+/)[0]),
	toString: function() {
		var v = dojo.version;
		return v.major + "." + v.minor + "." + v.patch + " (" + v.revision + ")";
	}
};

// ****************************************************************
// global public utils
// ****************************************************************

/*
 * utility to print an Error. 
 * TODO: overriding Error.prototype.toString won't accomplish this?
 * ... since natively generated Error objects do not always reflect such things?
 */
function dj_error_to_string(excep){
	return ((!dj_undef("message", excep)) ? excep.message : (dj_undef("description", excep) ? excep : excep.description ));
}

/**
 * Produce a line of debug output. 
 * Does nothing unless dojo.hostenv.is_debug_ is true.
 * varargs, joined with ''.
 * Caller should not supply a trailing "\n".
 *
 * TODO: dj_debug() is a convenience for dojo.hostenv.debug()?
 */
// We have a workaround here for the "arguments" object not being legal when using "jsc -fast+".
/*@cc_on @*/
/*@if (@_jscript_version >= 7)
function dj_debug(... args : Object[]) {
@else @*/
function dj_debug(){
	var args = arguments;
/*@end @*/
	if(dj_undef("println", dojo.hostenv)){
		// dj_throw("attempt to call dj_debug when there is no dojo.hostenv println implementation (yet?)");
		dj_throw("dj_debug not available (yet?)");
	}
	if(!dojo.hostenv.is_debug_){ return; }
	var isJUM = dj_global["jum"];
	var s = isJUM ? "": "DEBUG: ";
	for(var i=0;i<args.length;++i){
		if(!false && args[i] instanceof Error){
			var msg = "[" + args[i].name + ": " + dj_error_to_string(args[i]) +
				(args[i].fileName ? ", file: " + args[i].fileName : "") +
				(args[i].lineNumber ? ", line: " + args[i].lineNumber : "") + "]";
		}else{ 
			var msg = args[i];
		}
		s += msg + " ";
	}
	if(isJUM){ // this seems to be the only way to get JUM to "play nice"
		jum.debug(s);
	}else{
		dojo.hostenv.println(s);
	}
}

/**
* Throws an Error object given the string err. For now, will also do a println to the user first.
*/
function dj_throw(message){
	var he = dojo.hostenv;
	if(dj_undef("hostenv", dojo)&&dj_undef("println", dojo)){ 
		dojo.hostenv.println("FATAL: " + message);
	}
	throw Error(message);
}

/**
 * Rethrows the provided Error object excep, with the additional message given by message.
 */
function dj_rethrow(message, excep){
	var emess = dj_error_to_string(excep);
	dj_throw(message + ": " + emess);
}

/**
 * We put eval() in this separate function to keep down the size of the trapped
 * evaluation context.
 *
 * Note that:
 * - JSC eval() takes an optional second argument which can be 'unsafe'.
 * - Mozilla/SpiderMonkey eval() takes an optional second argument which is the scope object for new symbols.
*/
function dj_eval(s){ return dj_global.eval ? dj_global.eval(s) : eval(s); }


/**
 * Convenience for throwing an exception because some function is not implemented.
 */
function dj_unimplemented(funcname, extra){
	var mess = "'" + funcname + "' not implemented";
	if((typeof extra != 'undefined')&&(extra)){ mess += " " + extra; }
	// mess += " (host environment '" + dojo.hostenv.getName() + "')";
	dj_throw(mess);
}

/**
 * Convenience for informing of deprecated behaviour.
 */
function dj_deprecated(behaviour, extra){
	var mess = "DEPRECATED: " + behaviour;
	if((typeof extra != 'undefined')&&(extra)){ mess += " " + extra; }
	// mess += " (host environment '" + dojo.hostenv.getName() + "')";
	dj_debug(mess);
}

/**
 * Does inheritance
 */
function dj_inherits(subclass, superclass){
	if(typeof superclass != 'function'){ 
		// dj_throw("eek: superclass not a function: " + superclass + "\nsubclass is: " + subclass);
		dj_throw("superclass: "+superclass+" borken");
	}
	subclass.prototype = new superclass();
	subclass.prototype.constructor = subclass;
	subclass.superclass = superclass.prototype;
	// DEPRICATED: super is a reserved word, use 'superclass'
	subclass['super'] = superclass.prototype;
}


// an object that authors use determine what host we are running under
dojo.render = {
	name: "",
	ver: dojo.version,
	os: { win: false, linux: false, osx: false },
	html: {
		capable: false,
		support: {
			builtin: false,
			plugin: false
		},
		ie: false,
		opera: false,
		khtml: false,
		safari: false,
		moz: false,
		prefixes: ["html"]
	},
	svg: {
		capable: false,
		support: {
			builtin: false,
			plugin: false
		},
		corel: false,
		adobe: false,
		batik: false,
		prefixes: ["svg"]
	},
	swf: {
		capable: false,
		support: {
			builtin: false,
			plugin: false
		},
		mm: false,
		prefixes: ["Swf", "Flash", "Mm"]
	},
	swt: {
		capable: false,
		support: {
			builtin: false,
			plugin: false
		},
		ibm: false,
		prefixes: ["Swt"]
	}
};


// ****************************************************************
// dojo.hostenv methods that must be defined in hostenv_*.js
// ****************************************************************

/**
 * The interface definining the interaction with the EcmaScript host environment.
*/

/*
 * None of these methods should ever be called directly by library users.
 * Instead public methods such as loadModule should be called instead.
 */
dojo.hostenv = (function(){
	var djc = djConfig;

	function _def(obj, name, def){
		return (dj_undef(name, obj) ? def : obj[name]);
	}

	return {
		is_debug_: _def(djc, "isDebug", false),
		base_script_uri_: _def(djc, "baseScriptUri", undefined),
		base_relative_path_: _def(djc, "baseRelativePath", ""),
		library_script_uri_: _def(djc, "libraryScriptUri", ""),
		auto_build_widgets_: _def(djc, "parseWidgets", true),
		ie_prevent_clobber_: _def(djc, "iePreventClobber", false),
		ie_clobber_minimal_: _def(djc, "ieClobberMinimal", false),
		name_: '(unset)',
		version_: '(unset)',
		pkgFileName: "__package__",

		// for recursion protection
		loading_modules_: {},
		loaded_modules_: {},
		addedToLoadingCount: [],
		removedFromLoadingCount: [],
		inFlightCount: 0,
		modulePrefixes_: {
			dojo: {name: "dojo", value: "src"}
		},


		setModulePrefix: function(module, prefix){
			this.modulePrefixes_[module] = {name: module, value: prefix};
		},

		getModulePrefix: function(module){
			var mp = this.modulePrefixes_;
			if((mp[module])&&(mp[module]["name"])){
				return mp[module].value;
			}
			return module;
		},

		getTextStack: [],
		loadUriStack: [],
		loadedUris: [],
		// lookup cache for modules.
		// NOTE: this is partially redundant a private variable in the jsdown implementation, but we don't want to couple the two.
		modules_ : {},
		modulesLoadedFired: false,
		modulesLoadedListeners: [],
		/**
		 * Return the name of the hostenv.
		 */
		getName: function(){ return this.name_; },

		/**
		* Return the version of the hostenv.
		*/
		getVersion: function(){ return this.version_; },

		/**
		 * Read the plain/text contents at the specified uri.
		 * If getText() is not implemented, then it is necessary to override loadUri()
		 * with an implementation that doesn't rely on it.
		 */
		getText: function(uri){
			dj_unimplemented('getText', "uri=" + uri);
		},

		/**
		 * return the uri of the script that defined this function
		 * private method that must be implemented by the hostenv.
		 */
		getLibraryScriptUri: function(){
			// FIXME: need to implement!!!
			dj_unimplemented('getLibraryScriptUri','');
		}
	};
})();

/*
dojo.hostenv.makeUnimpl = function(ns, funcname){
	return new Function("dj_unimplemented('"+funcname+" unimplemented');");
}
*/

/**
 * Display a line of text to the user.
 * The line argument should not contain a trailing "\n"; that is added by the implementation.
 */
//dojo.hostenv.println = function(line) {}

// ****************************************************************
// dojo.hostenv methods not defined in hostenv_*.js
// ****************************************************************

/**
 * Return the base script uri that other scripts are found relative to.
 * It is either the empty string, or a non-empty string ending in '/'.
 */
dojo.hostenv.getBaseScriptUri = function(){
	// if(typeof this.base_script_uri_ != 'undefined'){ return this.base_script_uri_; }
	if(!dj_undef("base_script_uri_", this)){ return this.base_script_uri_; }
	var uri = this.library_script_uri_;
	if(!uri){
		uri = this.library_script_uri_ = this.getLibraryScriptUri();
		if(!uri){
			dj_throw("Nothing returned by getLibraryScriptUri(): " + uri);
		}
	}

	var lastslash = uri.lastIndexOf('/');
	// inclusive of slash
	// this.base_script_uri_ = this.normPath((lastslash == -1 ? '' : uri.substring(0,lastslash + 1)) + this.base_relative_path_);
	this.base_script_uri_ = this.base_relative_path_;
	return this.base_script_uri_;
}

// FIXME: we should move this into a different namespace
/*
dojo.hostenv.normPath = function(path){
	// FIXME: need to convert or handle windows-style path separators

	// posix says we can have one and two slashes next to each other, but 3 or
	// more should be compressed to a single slash
	path = path.replace(/(\/\/)(\/)+/, "\/");
	// if we've got a "..." sequence, we can should attempt to normalize it
	path = path.replace(/(\.\.)(\.)+/, "..");
	// likewise, we need to clobber "../" sequences at the beginning of our
	// string since they don't mean anything in this context
	path = path.replace(/^(\.)+(\/)/, "");
	// return path;

	// FIXME: we need to fix this for non-rhino clients (say, IE)
	// we need to strip out ".." sequences since rhino can't handle 'em
	if(path.indexOf("..") >= 0){
		var oparts = path.split("/");
		var nparts = [];
		for(var x=0; x<oparts.length; x++){
			if(oparts[x]==".."){
				// FIXME: what about if this is at the front? do we care?
				if(nparts.length){
					nparts.pop();
				}else{
					nparts.push("..");
				}
			}else{
				nparts.push(oparts[x]);
			}
		}
		return nparts.join("/");
	}
}
*/

/**
* Set the base script uri.
*/
// In JScript .NET, see interface System._AppDomain implemented by System.AppDomain.CurrentDomain. Members include AppendPrivatePath, RelativeSearchPath, BaseDirectory.
dojo.hostenv.setBaseScriptUri = function(uri){ this.base_script_uri_ = uri }

/**
 * Loads and interprets the script located at relpath, which is relative to the script root directory.
 * If the script is found but its interpretation causes a runtime exception, that exception is not caught
 * by us, so the caller will see it.
 * We return a true value if and only if the script is found.
 *
 * For now, we do not have an implementation of a true search path.
 * We consider only the single base script uri, as returned by getBaseScriptUri().
 *
 * @param relpath A relative path to a script (no leading '/', and typically ending in '.js').
 * @param module A module whose existance to check for after loading a path. Can be used to determine success or failure of the load.
 */
dojo.hostenv.loadPath = function(relpath, module /*optional*/, cb /*optional*/){
	if(!relpath){
		dj_throw("Missing relpath argument");
	}
	if((relpath.charAt(0) == '/')||(relpath.match(/^\w+:/))){
		dj_throw("relpath '" + relpath + "'; must be relative");
	}
	var uri = this.getBaseScriptUri() + relpath;
	try{
		return ((!module) ? this.loadUri(uri) : this.loadUriAndCheck(uri, module));
	}catch(e){
		if(dojo.hostenv.is_debug_){
			dj_debug(e);
		}
		return false;
	}
}

/**
 * Reads the contents of the URI, and evaluates the contents.
 * Returns true if it succeeded. Returns false if the URI reading failed. Throws if the evaluation throws.
 * The result of the eval is not available to the caller.
 */
dojo.hostenv.loadUri = function(uri, cb){
	if(dojo.hostenv.loadedUris[uri]){
		return;
	}
	var contents = this.getText(uri, null, true);
	if(contents == null){ return 0; }
	var value = dj_eval(contents);
	return 1;
}

dojo.hostenv.getDepsForEval = function(contents){
	// FIXME: should probably memoize this!
	if(!contents){ contents = ""; }
	// check to see if we need to load anything else first. Ugg.
	var deps = [];
	var tmp = contents.match( /dojo.hostenv.loadModule\(.*?\)/mg );
	if(tmp){
		for(var x=0; x<tmp.length; x++){ deps.push(tmp[x]); }
	}
	tmp = contents.match( /dojo.hostenv.require\(.*?\)/mg );
	if(tmp){
		for(var x=0; x<tmp.length; x++){ deps.push(tmp[x]); }
	}
	tmp = contents.match( /dojo.require\(.*?\)/mg );
	if(tmp){
		for(var x=0; x<tmp.length; x++){ deps.push(tmp[x]); }
	}
	// FIXME: this seems to be borken on Rhino in some situations. ???
	tmp = contents.match( /dojo.hostenv.conditionalLoadModule\([\w\W]*?\)/gm );
	if(tmp){
		for(var x=0; x<tmp.length; x++){ deps.push(tmp[x]); }
	}

	return deps;
}

// FIXME: probably need to add logging to this method
dojo.hostenv.loadUriAndCheck = function(uri, module, cb){
	// dj_debug("loadUriAndCheck: "+uri+", "+module);
	var ok = true;
	try{
		ok = this.loadUri(uri, cb);
	}catch(e){
		dj_debug("failed loading ", uri, " with error: ", e);
	}
	return ((ok)&&(this.findModule(module, false))) ? true : false;
}

dojo.loaded = function(){}

dojo.hostenv.loaded = function(){
	this.modulesLoadedFired = true;
	var mll = this.modulesLoadedListeners;
	for(var x=0; x<mll.length; x++){
		mll[x]();
	}
	dojo.loaded();
}

/*
Call styles:
	dojo.addOnLoad(functionPointer)
	dojo.addOnLoad(object, "functionName")
*/
dojo.addOnLoad = function(obj, fcnName) {
	if(arguments.length == 1) {
		dojo.hostenv.modulesLoadedListeners.push(obj);
	} else if(arguments.length > 1) {
		dojo.hostenv.modulesLoadedListeners.push(function() {
			obj[fcnName]();
		});
	}
};

dojo.hostenv.modulesLoaded = function(){
	if(this.modulesLoadedFired){ return; }
	if((this.loadUriStack.length==0)&&(this.getTextStack.length==0)){
		if(this.inFlightCount > 0){ 
			dj_debug("couldn't initialize, there are files still in flight");
			return;
		}
		this.loaded();
	}
}

dojo.hostenv.moduleLoaded = function(modulename){
	var modref = dj_eval_object_path((modulename.split(".").slice(0, -1)).join('.'));
	this.loaded_modules_[(new String(modulename)).toLowerCase()] = modref;
}

/**
* loadModule("A.B") first checks to see if symbol A.B is defined. 
* If it is, it is simply returned (nothing to do).
* If it is not defined, it will look for "A/B.js" in the script root directory, followed
* by "A.js".
* It throws if it cannot find a file to load, or if the symbol A.B is not defined after loading.
* It returns the object A.B.
*
* This does nothing about importing symbols into the current package.
* It is presumed that the caller will take care of that. For example, to import
* all symbols:
*
*    with (dojo.hostenv.loadModule("A.B")) {
*       ...
*    }
*
* And to import just the leaf symbol:
*
*    var B = dojo.hostenv.loadModule("A.B");
*    ...
*
* dj_load is an alias for dojo.hostenv.loadModule
*/
dojo.hostenv.loadModule = function(modulename, exact_only, omit_module_check){
	var module = this.findModule(modulename, false);
	if(module){
		return module;
	}

	// protect against infinite recursion from mutual dependencies
	if(dj_undef(modulename, this.loading_modules_)){
		this.addedToLoadingCount.push(modulename);
	}
	this.loading_modules_[modulename] = 1;

	// convert periods to slashes
	var relpath = modulename.replace(/\./g, '/') + '.js';

	var syms = modulename.split(".");
	var nsyms = modulename.split(".");
	for (var i = syms.length - 1; i > 0; i--) {
		var parentModule = syms.slice(0, i).join(".");
		var parentModulePath = this.getModulePrefix(parentModule);
		if (parentModulePath != parentModule) {
			syms.splice(0, i, parentModulePath);
			break;
		}
	}
	var last = syms[syms.length - 1];
	// figure out if we're looking for a full package, if so, we want to do
	// things slightly diffrently
	if(last=="*"){
		modulename = (nsyms.slice(0, -1)).join('.');

		while(syms.length){
			syms.pop();
			syms.push(this.pkgFileName);
			relpath = syms.join("/") + '.js';
			if(relpath.charAt(0)=="/"){
				relpath = relpath.slice(1);
			}
			ok = this.loadPath(relpath, ((!omit_module_check) ? modulename : null));
			if(ok){ break; }
			syms.pop();
		}
	}else{
		relpath = syms.join("/") + '.js';
		modulename = nsyms.join('.');
		var ok = this.loadPath(relpath, ((!omit_module_check) ? modulename : null));
		if((!ok)&&(!exact_only)){
			syms.pop();
			while(syms.length){
				relpath = syms.join('/') + '.js';
				ok = this.loadPath(relpath, ((!omit_module_check) ? modulename : null));
				if(ok){ break; }
				syms.pop();
				relpath = syms.join('/') + '/'+this.pkgFileName+'.js';
				if(relpath.charAt(0)=="/"){
					relpath = relpath.slice(1);
				}
				ok = this.loadPath(relpath, ((!omit_module_check) ? modulename : null));
				if(ok){ break; }
			}
		}

		if((!ok)&&(!omit_module_check)){
			dj_throw("Could not load '" + modulename + "'; last tried '" + relpath + "'");
		}
	}

	// check that the symbol was defined
	if(!omit_module_check){
		module = this.findModule(modulename, false); // pass in false so we can give better error
		if(!module){
			dj_throw("symbol '" + modulename + "' is not defined after loading '" + relpath + "'"); 
		}
	}

	return module;
}


function dj_load(modulename, exact_only){
	return dojo.hostenv.loadModule(modulename, exact_only); 
}

/**
* startPackage("A.B") follows the path, and at each level creates a new empty object
* or uses what already exists. It returns the result.
*/
dojo.hostenv.startPackage = function(packname){
	var syms = packname.split(/\./);
	if(syms[syms.length-1]=="*"){
		syms.pop();
	}
	return dj_eval_object_path(syms.join("."), true);
}



/**
 * findModule("A.B") returns the object A.B if it exists, otherwise null.
 * @param modulename A string like 'A.B'.
 * @param must_exist Optional, defualt false. throw instead of returning null if the module does not currently exist.
 */
dojo.hostenv.findModule = function(modulename, must_exist) {
	// check cache
	if(!dj_undef(modulename, this.modules_)){
		return this.modules_[modulename];
	}

	if(this.loaded_modules_[(new String(modulename)).toLowerCase()]){
		// dj_debug(modulename);
		return this.loaded_modules_[modulename];
	}

	// see if symbol is defined anyway
	var module = dj_eval_object_path(modulename);
	if((typeof module !== 'undefined')&&(module)){
		return this.modules_[modulename] = module;
	}

	if(must_exist){
		dj_throw("no loaded module named '" + modulename + "'");
	}
	return null;
}
