/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.io.IO");

/******************************************************************************
 *	Notes about dojo.io design:
 *	
 *	The dojo.io.* package has the unenviable task of making a lot of different
 *	types of I/O feel natural, despite a universal lack of good (or even
 *	reasonable!) I/O capability in the host environment. So lets pin this down
 *	a little bit further.
 *
 *	Rhino:
 *		perhaps the best situation anywhere. Access to Java classes allows you
 *		to do anything one might want in terms of I/O, both synchronously and
 *		async. Can open TCP sockets and perform low-latency client/server
 *		interactions. HTTP transport is available through Java HTTP client and
 *		server classes. Wish it were always this easy.
 *
 *	xpcshell:
 *		XPCOM for I/O. A cluster-fuck to be sure.
 *
 *	spidermonkey:
 *		S.O.L.
 *
 *	Browsers:
 *		Browsers generally do not provide any useable filesystem access. We are
 *		therefore limited to HTTP for moving information to and from Dojo
 *		instances living in a browser.
 *
 *		XMLHTTP:
 *			Sync or async, allows reading of arbitrary text files (including
 *			JS, which can then be eval()'d), writing requires server
 *			cooperation and is limited to HTTP mechanisms (POST and GET).
 *
 *		<iframe> hacks:
 *			iframe document hacks allow browsers to communicate asynchronously
 *			with a server via HTTP POST and GET operations. With significant
 *			effort and server cooperation, low-latency data transit between
 *			client and server can be acheived via iframe mechanisms (repubsub).
 *
 *		SVG:
 *			Adobe's SVG viewer implements helpful primitives for XML-based
 *			requests, but receipt of arbitrary text data seems unlikely w/o
 *			<![CDATA[]]> sections.
 *
 *
 *	A discussion between Dylan, Mark, Tom, and Alex helped to lay down a lot
 *	the IO API interface. A transcript of it can be found at:
 *		http://dojotoolkit.org/viewcvs/viewcvs.py/documents/irc/irc_io_api_log.txt?rev=307&view=auto
 *	
 *	Also referenced in the design of the API was the DOM 3 L&S spec:
 *		http://www.w3.org/TR/2004/REC-DOM-Level-3-LS-20040407/load-save.html
 ******************************************************************************/

// a map of the available transport options. Transports should add themselves
// by calling add(name)
dojo.io.transports = [];
dojo.io.hdlrFuncNames = [ "load", "error" ]; // we're omitting a progress() event for now

dojo.io.Request = function(url, mt, trans, curl){
	this.url = url;
	this.mimetype = mt;
	this.transport = trans;
	this.changeUrl = curl;
	this.formNode = null;
	
	// events stuff
	this.events_ = {};
	
	var Request = this;
	
	this.error = function (type, error) {
		
		switch (type) {
			case "io":
				var errorCode = dojo.io.IOEvent.IO_ERROR;
				var errorMessage = "IOError: error during IO";
				break;
			case "parse":
				var errorCode = dojo.io.IOEvent.PARSE_ERROR;
				var errorMessage = "IOError: error during parsing";
			default:
				var errorCode = dojo.io.IOEvent.UNKOWN_ERROR;
				var errorMessage = "IOError: cause unkown";
		}
		
		var event = new dojo.io.IOEvent("error", null, Request, errorMessage, this.url, errorCode);
		Request.dispatchEvent(event);
		if (Request.onerror) { Request.onerror(errorMessage, Request.url, event); }
	}
	
	this.load = function (type, data, evt) {
		var event = new dojo.io.IOEvent("load", data, Request, null, null, null);
		Request.dispatchEvent(event);
		if (Request.onload) { Request.onload(event); }
	}
	
	this.backButton = function () {
		var event = new dojo.io.IOEvent("backbutton", null, Request, null, null, null);
		Request.dispatchEvent(event);
		if (Request.onbackbutton) { Request.onbackbutton(event); }
	}
	
	this.forwardButton = function () {
		var event = new dojo.io.IOEvent("forwardbutton", null, Request, null, null, null);
		Request.dispatchEvent(event);
		if (Request.onforwardbutton) { Request.onforwardbutton(event); }
	}
	
}

// EventTarget interface
dojo.io.Request.prototype.addEventListener = function (type, func) {
	if (!this.events_[type]) { this.events_[type] = []; }
	
	for (var i = 0; i < this.events_[type].length; i++) {
		if (this.events_[type][i] == func) { return; }
	}
	this.events_[type].push(func);
}

dojo.io.Request.prototype.removeEventListener = function (type, func) {
	if (!this.events_[type]) { return; }
	
	for (var i = 0; i < this.events_[type].length; i++) {
		if (this.events_[type][i] == func) { this.events_[type].splice(i,1); }
	}
}

dojo.io.Request.prototype.dispatchEvent = function (evt) {
	if (!this.events_[evt.type]) { return; }
	for (var i = 0; i < this.events_[evt.type].length; i++) {
		this.events_[evt.type][i](evt);
	}
	return false; // FIXME: implement return value
}

dojo.io.IOEvent = function(type, data, request, errorMessage, errorUrl, errorCode) {	
	// properties
	this.type =  type;
	this.data = data;
	this.request = request;
	this.errorMessage = errorMessage;
	this.errorUrl = errorUrl;
	this.errorCode = errorCode;
}

// constants
dojo.io.IOEvent.UNKOWN_ERROR = 0;
dojo.io.IOEvent.IO_ERROR = 1;
dojo.io.IOEvent.PARSE_ERROR = 2;


dojo.io.Error = function(msg, type, num){
	this.message = msg;
	this.type =  type || "unknown"; // must be one of "io", "parse", "unknown"
	this.number = num || 0; // per-substrate error number, not normalized
}

dojo.io.transports.addTransport = function(name){
	this.push(name);
	// FIXME: do we need to handle things that aren't direct children of the
	// dojo.io namespace? (say, dojo.io.foo.fooTransport?)
	this[name] = dojo.io[name];
}

// binding interface, the various implementations register their capabilities
// and the bind() method dispatches
dojo.io.bind = function(kwArgs){
	// if the request asks for a particular implementation, use it

	// normalize args
	if(!kwArgs["url"]){ kwArgs.url = ""; } else { kwArgs.url = kwArgs.url.toString(); }
	if(!kwArgs["mimetype"]){ kwArgs.mimetype = "text/plain"; }
	if(!kwArgs["method"] && !kwArgs["formNode"]){
		kwArgs.method = "get";
	} else if(kwArgs["formNode"]) {
		kwArgs.method = kwArgs["method"] || kwArgs["formNode"].method || "get";
	}
	if(kwArgs["handler"]){ kwArgs.handle = kwArgs.handler; }
	if(!kwArgs["handle"]){ kwArgs.handle = function(){}; }
	if(kwArgs["loaded"]){ kwArgs.load = kwArgs.loaded; }
	if(kwArgs["changeUrl"]) { kwArgs.changeURL = kwArgs.changeUrl; }
	for(var x=0; x<this.hdlrFuncNames.length; x++){
		var fn = this.hdlrFuncNames[x];
		if(typeof kwArgs[fn] == "function"){ continue; }
		if(typeof kwArgs.handler == "object"){
			if(typeof kwArgs.handler[fn] == "function"){
				kwArgs[fn] = kwArgs.handler[fn]||kwArgs.handler["handle"]||function(){};
			}
		}else if(typeof kwArgs["handler"] == "function"){
			kwArgs[fn] = kwArgs.handler;
		}else if(typeof kwArgs["handle"] == "function"){
			kwArgs[fn] = kwArgs.handle;
		}
	}

	var tsName = "";
	if(kwArgs["transport"]){
		tsName = kwArgs["transport"];
		if(!this[tsName]){ return false; /* throw exception? */ }
	}else{
		// otherwise we do our best to auto-detect what available transports
		// will handle 

		// FIXME: should we normalize or set defaults for the kwArgs here?
		for(var x=0; x<dojo.io.transports.length; x++){
			var tmp = dojo.io.transports[x];
			if((this[tmp])&&(this[tmp].canHandle(kwArgs))){
				tsName = tmp;
			}
		}
		if(tsName == ""){ return false; /* throw exception? */ }
	}
	this[tsName].bind(kwArgs);
	return true;
}

dojo.io.argsFromMap = function(map){
	var control = new Object();
	var mapStr = "";
	for(var x in map){
		if(!control[x]){
			mapStr+= encodeURIComponent(x)+"="+encodeURIComponent(map[x])+"&";
		}
	}

	return mapStr;
}

/*
dojo.io.sampleTranport = new function(){
	this.canHandle = function(kwArgs){
		// canHandle just tells dojo.io.bind() if this is a good transport to
		// use for the particular type of request.
		if(	
			(
				(kwArgs["mimetype"] == "text/plain") ||
				(kwArgs["mimetype"] == "text/html") ||
				(kwArgs["mimetype"] == "text/javascript")
			)&&(
				(kwArgs["method"] == "get") ||
				( (kwArgs["method"] == "post") && (!kwArgs["formNode"]) )
			)
		){
			return true;
		}

		return false;
	}

	this.bind = function(kwArgs){
		var hdlrObj = {};

		// set up a handler object
		for(var x=0; x<dojo.io.hdlrFuncNames.length; x++){
			var fn = dojo.io.hdlrFuncNames[x];
			if(typeof kwArgs.handler == "object"){
				if(typeof kwArgs.handler[fn] == "function"){
					hdlrObj[fn] = kwArgs.handler[fn]||kwArgs.handler["handle"];
				}
			}else if(typeof kwArgs[fn] == "function"){
				hdlrObj[fn] = kwArgs[fn];
			}else{
				hdlrObj[fn] = kwArgs["handle"]||function(){};
			}
		}

		// build a handler function that calls back to the handler obj
		var hdlrFunc = function(evt){
			if(evt.type == "onload"){
				hdlrObj.load("load", evt.data, evt);
			}else if(evt.type == "onerr"){
				var errObj = new dojo.io.Error("sampleTransport Error: "+evt.msg);
				hdlrObj.error("error", errObj);
			}
		}

		// the sample transport would attach the hdlrFunc() when sending the
		// request down the pipe at this point
		var tgtURL = kwArgs.url+"?"+dojo.io.argsFromMap(kwArgs.content);
		// sampleTransport.sendRequest(tgtURL, hdlrFunc);
	}

	dojo.io.transports.addTransport("sampleTranport");
}
*/
