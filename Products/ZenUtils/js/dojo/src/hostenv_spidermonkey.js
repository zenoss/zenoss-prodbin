/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above *//*
 * SpiderMonkey host environment
 */

dojo.hostenv.name_ = 'spidermonkey';

// version() returns 0, sigh. and build() returns nothing but just prints.
dojo.hostenv.getVersion = function(){ return version(); }

// make jsc shut up (so we can use jsc for sanity checking) 
/*@cc_on
@if (@_jscript_version >= 7)
var line2pc; var print; var load; var quit;
@end
@*/

if(typeof line2pc == 'undefined'){
	dj_throw("attempt to use SpiderMonkey host environment when no 'line2pc' global");
}

/*
 * This is a hack that determines the current script file by parsing a generated
 * stack trace (relying on the non-standard "stack" member variable of the
 * SpiderMonkey Error object).
 * If param depth is passed in, it'll return the script file which is that far down
 * the stack, but that does require that you know how deep your stack is when you are
 * calling.
 */
function dj_spidermonkey_current_file(depth){
    var s = '';
    try{
		throw Error("whatever");
	}catch(e){
		s = e.stack;
	}
    // lines are like: bu_getCurrentScriptURI_spidermonkey("ScriptLoader.js")@burst/Runtime.js:101
    var matches = s.match(/[^@]*\.js/gi);
    if(!matches){ 
		dj_throw("could not parse stack string: '" + s + "'");
	}
    var fname = (typeof depth != 'undefined' && depth) ? matches[depth + 1] : matches[matches.length - 1];
    if(!fname){ 
		dj_throw("could not find file name in stack string '" + s + "'");
	}
    //print("SpiderMonkeyRuntime got fname '" + fname + "' from stack string '" + s + "'");
    return fname;
}

// call this now because later we may not be on the top of the stack
//dojo.hostenv.getLibraryScriptUri = dj_spidermonkey_current_file;
if(!dojo.hostenv.library_script_uri_){ 
	dojo.hostenv.library_script_uri_ = dj_spidermonkey_current_file(0); 
}

dojo.hostenv.loadUri = function(uri){
    // spidermonkey load() evaluates the contents into the global scope (which is what we want).
    // TODO: sigh, load() does not return a useful value. 
    // Perhaps it is returning the value of the last thing evaluated?

	// FIXME: this is TOTALLY BORKEN on a stock spidermoneky. Instead of
	// returning a fail code, the interpreter halts, and without passing
	// JS_HAS_FILE_OBJECT=1 in the build (which I've not gotten to work yet)
	// there's no way to stat() the file to determine if it even exists before
	// attempting to load(). As per MDA, we should look at xpcshell as a
	// replacement for spidermonkey.
    var ok = load(uri);
    dj_debug("spidermonkey load(", uri, ") returned ", ok);
    return 1;
}

dojo.hostenv.println = function(line){
	print(line);
}

dojo.hostenv.exit = function(exitcode){ 
	quit(exitcode); 
}

