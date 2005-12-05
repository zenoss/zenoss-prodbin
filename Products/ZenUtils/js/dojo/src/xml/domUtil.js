/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.xml.domUtil");
dojo.require("dojo.graphics.color");
dojo.require("dojo.text.String");

// for loading script:
dojo.xml.domUtil = new function(){
	this.nodeTypes = {
		ELEMENT_NODE                  : 1,
		ATTRIBUTE_NODE                : 2,
		TEXT_NODE                     : 3,
		CDATA_SECTION_NODE            : 4,
		ENTITY_REFERENCE_NODE         : 5,
		ENTITY_NODE                   : 6,
		PROCESSING_INSTRUCTION_NODE   : 7,
		COMMENT_NODE                  : 8,
		DOCUMENT_NODE                 : 9,
		DOCUMENT_TYPE_NODE            : 10,
		DOCUMENT_FRAGMENT_NODE        : 11,
		NOTATION_NODE                 : 12
	}
	
	this.dojoml = "http://www.dojotoolkit.org/2004/dojoml";
	this.idIncrement = 0;
	
	this.getTagName = function(node){
		var tagName = node.tagName;
		if(tagName.substr(0,5).toLowerCase()!="dojo:"){
			
			if(tagName.substr(0,4).toLowerCase()=="dojo"){
				// FIXME: this assuumes tag names are always lower case
				return "dojo:" + tagName.substring(4).toLowerCase();
			}

			// allow lower-casing
			var djt = node.getAttribute("dojoType")||node.getAttribute("dojotype");
			if(djt){
				return "dojo:"+djt.toLowerCase();
			}
			
			if((node.getAttributeNS)&&(node.getAttributeNS(this.dojoml,"type"))){
				return "dojo:" + node.getAttributeNS(this.dojoml,"type").toLowerCase();
			}
			try{
				// FIXME: IE really really doesn't like this, so we squelch
				// errors for it
				djt = node.getAttribute("dojo:type");
			}catch(e){ /* FIXME: log? */ }
			if(djt){
				return "dojo:"+djt.toLowerCase();
			}

			if((!dj_global["djConfig"])||(!djConfig["ignoreClassNames"])){
				// FIXME: should we make this optionally enabled via djConfig?
				var classes = node.className||node.getAttribute("class");
				if((classes)&&(classes.indexOf("dojo-") != -1)){
					var aclasses = classes.split(" ");
					for(var x=0; x<aclasses.length; x++){
						if((aclasses[x].length>5)&&(aclasses[x].indexOf("dojo-")>=0)){
							return "dojo:"+aclasses[x].substr(5);
						}
					}
				}
			}

		}
		return tagName.toLowerCase();
	}

	this.getUniqueId = function(){
		var base = "dj_unique_";
		this.idIncrement++;
		while(document.getElementById(base+this.idIncrement)){
			this.idIncrement++;
		}
		return base+this.idIncrement;
	}

	this.getFirstChildTag = function(parentNode) {
		var node = parentNode.firstChild;
		while(node && node.nodeType != 1) {
			node = node.nextSibling;
		}
		return node;
	}

	this.getLastChildTag = function(parentNode) {
		if(!node) { return null; }
		var node = parentNode.lastChild;
		while(node && node.nodeType != 1) {
			node = node.previousSibling;
		}
		return node;
	}

	this.getNextSiblingTag = function(node) {
		if(!node) { return null; }
		do {
			node = node.nextSibling;
		} while(node && node.nodeType != 1);
		return node;
	}

	this.getPreviousSiblingTag = function(node) {
		if(!node) { return null; }
		do {
			node = node.previousSibling;
		} while(node && node.nodeType != 1);
		return node;
	}

	this.forEachChildTag = function(node, unaryFunc) {
		var child = this.getFirstChildTag(node);
		while(child) {
			if(unaryFunc(child) == "break") { break; }
			child = this.getNextSiblingTag(child);
		}
	}

	this.moveChildren = function(srcNode, destNode, trim) {
		var count = 0;
		if(trim) {
			while(srcNode.hasChildNodes() && srcNode.firstChild.nodeType == 3) {
				srcNode.removeChild(srcNode.firstChild);
			}
			while(srcNode.hasChildNodes() && srcNode.lastChild.nodeType == 3) {
				srcNode.removeChild(srcNode.lastChild);
			}
		}
		while(srcNode.hasChildNodes()) {
			destNode.appendChild(srcNode.firstChild);
			count++;
		}
		return count;
	}

	this.copyChildren = function(srcNode, destNode, trim) {
		var cp = srcNode.cloneNode(true);
		return this.moveChildren(cp, destNode, trim);
	}

	this.clearChildren = function(node) {
		var count = 0;
		while(node.hasChildNodes()) {
			node.removeChild(node.firstChild);
			count++;
		}
		return count;
	}

	this.replaceChildren = function(node, newChild) {
		this.clearChildren(node);
		node.appendChild(newChild);
	}

	this.getStyle = function(element, cssSelector) {
		var value = undefined, camelCased = dojo.xml.domUtil.toCamelCase(cssSelector);
		value = element.style[camelCased]; // dom-ish
		if(!value) {
			if(document.defaultView) { // gecko
				value = document.defaultView.getComputedStyle(element, "")
					.getPropertyValue(cssSelector);
			} else if(element.currentStyle) { // ie
				value = element.currentStyle[camelCased];
			} else if(element.style.getPropertyValue) { // dom spec
				value = element.style.getPropertyValue(cssSelector);
			}
		}
		return value;
	}

	this.toCamelCase = function(selector) {
		var arr = selector.split('-'), cc = arr[0];
		for(var i = 1; i < arr.length; i++) {
			cc += arr[i].charAt(0).toUpperCase() + arr[i].substring(1);
		}
		return cc;		
	}

	this.toSelectorCase = function(selector) {
		return selector.replace(/([A-Z])/g, "-$1" ).toLowerCase() ;
	}

	this.getAncestors = function(node){
		var ancestors = [];
		while(node){
			ancestors.push(node);
			node = node.parentNode;
		}
		return ancestors;
	}

	this.isChildOf = function(node, ancestor, noSame) {
		if(noSame && node) { node = node.parentNode; }
		while(node) {
			if(node == ancestor) {
				return true;
			}
			node = node.parentNode;
		}
		return false;
	}

	// FIXME: this won't work in Safari
	this.createDocumentFromText = function(str, mimetype) {
		if(!mimetype) { mimetype = "text/xml"; }
		if(typeof DOMParser != "undefined") {
			var parser = new DOMParser();
			return parser.parseFromString(str, mimetype);
		}else if(typeof ActiveXObject != "undefined"){
			var domDoc = new ActiveXObject("Microsoft.XMLDOM");
			if(domDoc) {
				domDoc.async = false;
				domDoc.loadXML(str);
				return domDoc;
			}else{
				dj_debug("toXml didn't work?");
			}
		/*
		}else if((dojo.render.html.capable)&&(dojo.render.html.safari)){
			// FIXME: this doesn't appear to work!
			// from: http://web-graphics.com/mtarchive/001606.php
			// var xml = '<?xml version="1.0"?>'+str;
			var mtype = "text/xml";
			var xml = '<?xml version="1.0"?>'+str;
			var url = "data:"+mtype+";charset=utf-8,"+encodeURIComponent(xml);
			var req = new XMLHttpRequest();
			req.open("GET", url, false);
			req.overrideMimeType(mtype);
			req.send(null);
			return req.responseXML;
		*/
		}else if(document.createElement){
			// FIXME: this may change all tags to uppercase!
			var tmp = document.createElement("xml");
			tmp.innerHTML = str;
			if(document.implementation && document.implementation.createDocument) {
				var xmlDoc = document.implementation.createDocument("foo", "", null);
				for(var i = 0; i < tmp.childNodes.length; i++) {
					xmlDoc.importNode(tmp.childNodes.item(i), true);
				}
				return xmlDoc;
			}
			// FIXME: probably not a good idea to have to return an HTML fragment
			// FIXME: the tmp.doc.firstChild is as tested from IE, so it may not
			// work that way across the board
			return tmp.document && tmp.document.firstChild ?
				tmp.document.firstChild : tmp;
		}
		return null;
	}

	// FIXME: how do we account for mixed environments?
	if(dojo.render.html.capable) {
		this.createNodesFromText = function(txt, wrap){
			var tn = document.createElement("div");
			// tn.style.display = "none";
			tn.style.visibility= "hidden";
			document.body.appendChild(tn);
			tn.innerHTML = txt;
			tn.normalize();
			if(wrap){ 
				var ret = [];
				// start hack
				var fc = tn.firstChild;
				ret[0] = ((fc.nodeValue == " ")||(fc.nodeValue == "\t")) ? fc.nextSibling : fc;
				// end hack
				// tn.style.display = "none";
				document.body.removeChild(tn);
				return ret;
			}
			var nodes = [];
			for(var x=0; x<tn.childNodes.length; x++){
				nodes.push(tn.childNodes[x].cloneNode(true));
			}
			tn.style.display = "none";
			document.body.removeChild(tn);
			return nodes;
		}
	}else if(dojo.render.svg.capable){
		this.createNodesFromText = function(txt, wrap){
			// from http://wiki.svg.org/index.php/ParseXml
			var docFrag = parseXML(txt, window.document);
			docFrag.normalize();
			if(wrap){ 
				var ret = [docFrag.firstChild.cloneNode(true)];
				return ret;
			}
			var nodes = [];
			for(var x=0; x<docFrag.childNodes.length; x++){
				nodes.push(docFrag.childNodes.item(x).cloneNode(true));
			}
			// tn.style.display = "none";
			return nodes;
		}
	}

	// referenced for backwards compatibility
	this.extractRGB = function() { return dojo.graphics.color.extractRGB.call(dojo.graphics.color, arguments); }
	this.hex2rgb = function() { return dojo.graphics.color.hex2rgb.call(dojo.graphics.color, arguments); }
	this.rgb2hex = function() { return dojo.graphics.color.rgb2hex.call(dojo.graphics.color, arguments); }

	this.insertBefore = function(node, ref){
		var pn = ref.parentNode;
		pn.insertBefore(node, ref);
	}

	this.before = this.insertBefore;

	this.insertAfter = function(node, ref){
		var pn = ref.parentNode;
		if(ref == pn.lastChild){
			pn.appendChild(node);
		}else{
			pn.insertBefore(node, ref.nextSibling);
		}
	}

	this.after = this.insertAfter;

	this.insert = function(node, ref, position){
		switch(position.toLowerCase()){
			case "before":
				this.before(node, ref);
				break;
			case "after":
				this.after(node, ref);
				break;
			case "first":
				if(ref.firstChild){
					this.before(node, ref.firstChild);
				}else{
					ref.appendChild(node);
				}
				break;
			default: // aka: last
				ref.appendChild(node);
				break;
		}
	}

	this.insertAtIndex = function(node, ref, insertionIndex){
		var pn = ref.parentNode;
		var siblingNodes = pn.childNodes;
		var placed = false;
		for(var i=0; i<siblingNodes.length; i++) {
			if(	(siblingNodes.item(i)["getAttribute"])&&
				(parseInt(siblingNodes.item(i).getAttribute("dojoinsertionindex")) > insertionIndex)){
				this.before(node, siblingNodes.item(i));
				placed = true;
				break;
			}
		}
		if(!placed){
			this.before(node, ref);
		}
	}
	
	/**
	 * implementation of the DOM Level 3 attribute.
	 * 
	 * @param node The node to scan for text
	 * @param text Optional, set the text to this value.
	 */
	this.textContent = function (node, text) {
		if (text) {
			this.replaceChildren(node, document.createTextNode(text));
			return text;
		} else {
			var _result = "";
			if (node == null) { return _result; }
			for (var i = 0; i < node.childNodes.length; i++) {
				switch (node.childNodes[i].nodeType) {
					case 1: // ELEMENT_NODE
					case 5: // ENTITY_REFERENCE_NODE
						_result += dojo.xml.domUtil.textContent(node.childNodes[i]);
						break;
					case 3: // TEXT_NODE
					case 2: // ATTRIBUTE_NODE
					case 4: // CDATA_SECTION_NODE
						_result += node.childNodes[i].nodeValue;
						break;
					default:
						break;
				}
			}
			return _result;
		}
	}
	
	/**
	 * Attempts to return the text as it would be rendered, with the line breaks
	 * sorted out nicely. Unfinished.
	 */
	this.renderedTextContent = function (node) {
		var result = "";
		if (node == null) { return result; }
		for (var i = 0; i < node.childNodes.length; i++) {
			switch (node.childNodes[i].nodeType) {
				case 1: // ELEMENT_NODE
				case 5: // ENTITY_REFERENCE_NODE
					switch (dojo.xml.domUtil.getStyle(node.childNodes[i], "display")) {
						case "block": case "list-item": case "run-in":
						case "table": case "table-row-group": case "table-header-group":
						case "table-footer-group": case "table-row": case "table-column-group":
						case "table-column": case "table-cell": case "table-caption":
							// TODO: this shouldn't insert double spaces on aligning blocks
							result += "\n";
							result += dojo.xml.domUtil.renderedTextContent(node.childNodes[i]);
							result += "\n";
							break;
						
						case "none": break;
						
						default:
							result += dojo.xml.domUtil.renderedTextContent(node.childNodes[i]);
							break;
					}
					break;
				case 3: // TEXT_NODE
				case 2: // ATTRIBUTE_NODE
				case 4: // CDATA_SECTION_NODE
					var text = node.childNodes[i].nodeValue;
					switch (dojo.xml.domUtil.getStyle(node, "text-transform")) {
						case "capitalize": text = dojo.text.capitalize(text); break;
						case "uppercase": text = text.toUpperCase(); break;
						case "lowercase": text = text.toLowerCase(); break;
						default: break; // leave as is
					}
					// TODO: implement
					switch (dojo.xml.domUtil.getStyle(node, "text-transform")) {
						case "nowrap": break;
						case "pre-wrap": break;
						case "pre-line": break;
						case "pre": break; // leave as is
						default:
							// remove whitespace and collapse first space
							text = text.replace(/\s+/, " ");
							if (/\s$/.test(result)) { text.replace(/^\s/, ""); }
							break;
					}
					result += text;
					break;
				default:
					break;
			}
		}
		return result;
	}
	
	this.remove = function (node) {
		if (node && node.parentNode) { node.parentNode.removeChild(node); }
	}
}

