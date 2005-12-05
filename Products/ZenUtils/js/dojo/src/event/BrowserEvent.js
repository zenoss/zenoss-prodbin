/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.event.BrowserEvent");
dojo.event.browser = {};

dojo.require("dojo.event.Event");

dojo_ie_clobber = new function(){
	this.clobberArr = ['data', 
		'onload', 'onmousedown', 'onmouseup', 
		'onmouseover', 'onmouseout', 'onmousemove', 
		'onclick', 'ondblclick', 'onfocus', 
		'onblur', 'onkeypress', 'onkeydown', 
		'onkeyup', 'onsubmit', 'onreset',
		'onselect', 'onchange', 'onselectstart', 
		'ondragstart', 'oncontextmenu'];

	this.exclusions = [];
	
	this.clobberList = {};
	this.clobberNodes = [];

	this.addClobberAttr = function(type){
		if(dojo.render.html.ie){
			if(this.clobberList[type]!="set"){
				this.clobberArr.push(type);
				this.clobberList[type] = "set"; 
			}
		}
	}

	this.addExclusionID = function(id){
		this.exclusions.push(id);
	}

	if(dojo.render.html.ie){
		for(var x=0; x<this.clobberArr.length; x++){
			this.clobberList[this.clobberArr[x]] = "set";
		}
	}

	this.clobber = function(nodeRef){
		for(var x=0; x< this.exclusions.length; x++){
			try{
				var tn = document.getElementById(this.exclusions[x]);
				tn.parentNode.removeChild(tn);
			}catch(e){
				// this is fired on unload, so squelch
			}
		}

		var na;
		if(nodeRef){
			var tna = nodeRef.getElementsByTagName("*");
			na = [nodeRef];
			for(var x=0; x<tna.length; x++){
				na.push(tna[x]);
			}
		}else{
			na = (this.clobberNodes.length) ? this.clobberNodes : document.all;
		}
		for(var i = na.length-1; i>=0; i=i-1){
			var el = na[i];
			for(var p = this.clobberArr.length-1; p>=0; p=p-1){
				var ta = this.clobberArr[p];
				try{
					el[ta] = null;
					el.removeAttribute(ta);
					delete el[ta];
				}catch(e){ /* squelch */ }
			}
		}
	}
}

if((dojo.render.html.ie)&&((!dojo.hostenv.ie_prevent_clobber_)||(dojo.hostenv.ie_clobber_minimal_))){
	window.onunload = function(){
		dojo_ie_clobber.clobber();
		if((dojo["widget"])&&(dojo.widget["manager"])){
			dojo.widget.manager.destroyAll();
		}
		CollectGarbage();
	}
}

dojo.event.browser = new function(){

	this.clean = function(node){
		if(dojo.render.html.ie){ 
			dojo_ie_clobber.clobber(node);
		}
	}

	this.addClobberAttr = function(type){
		dojo_ie_clobber.addClobberAttr(type);
	}

	this.addClobberAttrs = function(){
		for(var x=0; x<arguments.length; x++){
			this.addClobberAttr(arguments[x]);
		}
	}

	this.addClobberNode = function(node){
		if(dojo.hostenv.ie_clobber_minimal_){
			if(!node.__doClobber__) {
				dojo_ie_clobber.clobberNodes.push(node);
				node.__doClobber__ = true;
			}
		}
	}

	/*
	this.eventAroundAdvice = function(methodInvocation){
		var evt = this.fixEvent(methodInvocation.args[0]);
		return methodInvocation.proceed();
	}
	*/

	this.addListener = function(node, evtName, fp, capture){
		if(!capture){ var capture = false; }
		evtName = evtName.toLowerCase();
		if(evtName.substr(0,2)=="on"){ evtName = evtName.substr(2); }
		if(!node){ return; } // FIXME: log and/or bail?

		// build yet another closure around fp in order to inject fixEvent
		// around the resulting event
		var newfp = function(evt){
			if(!evt){ evt = window.event; }
			var ret = fp(dojo.event.browser.fixEvent(evt));
			if(capture){
				dojo.event.browser.stopEvent(evt);
			}
			return ret;
		}

		var onEvtName = "on"+evtName;
		if(node.addEventListener){ 
			node.addEventListener(evtName, newfp, capture);
			return true;
		}else{
			if(typeof node[onEvtName] == "function" ){
				var oldEvt = node[onEvtName];
				node[onEvtName] = function(e){
					oldEvt(e);
					newfp(e);
				}
			}else{
				node[onEvtName]=newfp;
			}
			if(dojo.render.html.ie){
				this.addClobberAttr(onEvtName);
				this.addClobberNode(node);
			}
			return true;
		}
	}

	this.fixEvent = function(evt){
		
		if (evt.type && evt.type.indexOf("key") == 0) { // key events
			var keys = {
				KEY_BACKSPACE: 8,
				KEY_TAB: 9,
				KEY_ENTER: 13,
				KEY_SHIFT: 16,
				KEY_CTRL: 17,
				KEY_ALT: 18,
				KEY_PAUSE: 19,
				KEY_CAPS_LOCK: 20,
				KEY_ESCAPE: 27,
				KEY_PAGE_UP: 33,
				KEY_PAGE_DOWN: 34,
				KEY_END: 35,
				KEY_HOME: 36,
				KEY_LEFT_ARROW: 37,
				KEY_UP_ARROW: 38,
				KEY_RIGHT_ARROW: 39,
				KEY_DOWN_ARROW: 40,
				KEY_INSERT: 45,
				KEY_DELETE: 46,
				KEY_LEFT_WINDOW: 91,
				KEY_RIGHT_WINDOW: 92,
				KEY_SELECT: 93,
				KEY_F1: 112,
				KEY_F2: 113,
				KEY_F3: 114,
				KEY_F4: 115,
				KEY_F5: 116,
				KEY_F6: 117,
				KEY_F7: 118,
				KEY_F8: 119,
				KEY_F9: 120,
				KEY_F10: 121,
				KEY_F11: 122,
				KEY_F12: 123,
				KEY_NUM_LOCK: 144,
				KEY_SCROLL_LOCK: 145
			}
	
			evt.keys = [];
			// add to evt object
			for (var key in keys) {
				evt[key] = keys[key];
				evt.keys[keys[key]] = key; // allow reverse lookup
			}
			if (dojo.render.html.ie && evt.type == "keypress") {
				evt.charCode = evt.keyCode;
			}
		}
	
		if(dojo.render.html.ie){
			if(!evt.target){ evt.target = evt.srcElement; }
			if(!evt.currentTarget){ evt.currentTarget = evt.srcElement; }
			if(!evt.layerX){ evt.layerX = evt.offsetX; }
			if(!evt.layerY){ evt.layerY = evt.offsetY; }
			// mouseover
			if(evt.fromElement){ evt.relatedTarget = evt.fromElement; }
			// mouseout
			if(evt.toElement){ evt.relatedTarget = evt.toElement; }
			evt.callListener = function(listener, curTarget){
				if(typeof listener != 'function'){
					dj_throw("listener not a function: " + listener);
				}
				evt.currentTarget = curTarget;
				var ret = listener.call(curTarget, evt);
				return ret;
			}

			evt.stopPropagation = function(){
				evt.cancelBubble = true;
			}

			evt.preventDefault = function(){
			  evt.returnValue = false;
			}
		}
		return evt;
	}

	this.stopEvent = function(ev) {
		if(window.event){
			ev.returnValue = false;
			ev.cancelBubble = true;
		}else{
			ev.preventDefault();
			ev.stopPropagation();
		}
	}
}
