/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.DomWidget");

dojo.require("dojo.event.*");
dojo.require("dojo.text.*");
dojo.require("dojo.widget.Widget");
dojo.require("dojo.xml.*");
dojo.require("dojo.math.curves");
dojo.require("dojo.animation.Animation");
dojo.require("dojo.uri.*");

dojo.widget._cssFiles = {};

// static method to build from a template w/ or w/o a real widget in place
dojo.widget.buildFromTemplate = function(obj, templatePath, templateCssPath, templateString) {
	var tpath = templatePath || obj.templatePath;
	var cpath = templateCssPath || obj.templateCssPath;

	if (!cpath && obj.templateCSSPath) {
		obj.templateCssPath = cpath = obj.templateCSSPath;
		obj.templateCSSPath = null;
		dj_deprecated("templateCSSPath is deprecated, use templateCssPath");
	}

	// DEPRECATED: use Uri objects, not strings
	if (tpath && !(tpath instanceof dojo.uri.Uri)) {
		tpath = dojo.uri.dojoUri(tpath);
		dj_deprecated("templatePath should be of type dojo.uri.Uri");
	}
	if (cpath && !(cpath instanceof dojo.uri.Uri)) {
		cpath = dojo.uri.dojoUri(cpath);
		dj_deprecated("templateCssPath should be of type dojo.uri.Uri");
	}
	
	var tmplts = dojo.widget.DomWidget.templates;
	if(!obj["widgetType"]) { // don't have a real template here
		do {
			var dummyName = "__dummyTemplate__" + dojo.widget.buildFromTemplate.dummyCount++;
		} while(tmplts[dummyName]);
		obj.widgetType = dummyName;
	}

	if((cpath)&&(!dojo.widget._cssFiles[cpath])){
		dojo.xml.htmlUtil.insertCssFile(cpath);
		obj.templateCssPath = null;
		dojo.widget._cssFiles[cpath] = true;
	}

	var ts = tmplts[obj.widgetType];
	if(!ts){
		tmplts[obj.widgetType] = {};
		ts = tmplts[obj.widgetType];
	}
	if(!obj.templateString){
		obj.templateString = templateString || ts["string"];
	}
	if(!obj.templateNode){
		obj.templateNode = ts["node"];
	}
	if((!obj.templateNode)&&(!obj.templateString)&&(tpath)){
		// fetch a text fragment and assign it to templateString
		// NOTE: we rely on blocking IO here!
		var tstring = dojo.hostenv.getText(tpath);
		if(tstring){
			var matches = tstring.match(/<body[^>]*>\s*([\s\S]+)\s*<\/body>/im);
			if(matches){
				tstring = matches[1];
			}
		}else{
			tstring = "";
		}
		obj.templateString = tstring;
		ts.string = tstring;
	}
	if(!ts["string"]) {
		ts.string = obj.templateString;
	}
}
dojo.widget.buildFromTemplate.dummyCount = 0;

dojo.widget.attachProperty = "dojoAttachPoint";
dojo.widget.eventAttachProperty = "dojoAttachEvent";
dojo.widget.subTemplateProperty = "dojoSubTemplate";
dojo.widget.onBuildProperty = "dojoOnBuild";

dojo.widget.attachTemplateNodes = function(rootNode, targetObj, subTemplateParent, events){
	// FIXME: this method is still taking WAAAY too long. We need ways of optimizing:
	//	a.) what we are looking for on each node
	//	b.) the nodes that are subject to interrogation (use xpath instead?)
	//	c.) how expensive event assignment is (less eval(), more connect())
	// var start = new Date();
	var elementNodeType = dojo.xml.domUtil.nodeTypes.ELEMENT_NODE;

	if(!rootNode){ 
		rootNode = targetObj.domNode;
	}

	if(rootNode.nodeType != elementNodeType){
		return;
	}
	// alert(events.length);

	var nodes = rootNode.getElementsByTagName("*");
	var _this = targetObj;
	for(var x=-1; x<nodes.length; x++){
		var baseNode = (x == -1) ? rootNode : nodes[x];
		// FIXME: is this going to have capitalization problems?
		var attachPoint = baseNode.getAttribute(this.attachProperty);
		if(attachPoint){
			targetObj[attachPoint]=baseNode;
		}

		// FIXME: we need to put this into some kind of lookup structure
		// instead of direct assignment
		var tmpltPoint = baseNode.getAttribute(this.templateProperty);
		if(tmpltPoint){
			targetObj[tmpltPoint]=baseNode;
		}

		// subtemplates are always collected "flatly" by the widget class
		var tmpltPoint = baseNode.getAttribute(this.subTemplateProperty);
		if(tmpltPoint){
			// we assign by removal in this case, mainly because we assume that
			// this will get proccessed later when the sub-template is filled
			// in (usually by this method, and usually repetitively)
			subTemplateParent.subTemplates[tmpltPoint]=baseNode.parentNode.removeChild(baseNode);
			// make sure we don't get stopped here the next time we try to process
			subTemplateParent.subTemplates[tmpltPoint].removeAttribute(this.subTemplateProperty);
			// return;
		}

		var attachEvent = baseNode.getAttribute(this.eventAttachProperty);
		if(attachEvent){
			// NOTE: we want to support attributes that have the form
			// "domEvent: nativeEvent; ..."
			var evts = attachEvent.split(";");
			for(var y=0; y<evts.length; y++){
				if(!evts[y]){ continue; }
				if(!evts[y].length){ continue; }
				var tevt = null;
				var thisFunc = null;
				tevt = dojo.text.trim(evts[y]);
				if(tevt.indexOf(":") >= 0){
					// oh, if only JS had tuple assignment
					var funcNameArr = tevt.split(":");
					tevt = dojo.text.trim(funcNameArr[0]);
					thisFunc = dojo.text.trim(funcNameArr[1]);
				}
				if(!thisFunc){
					thisFunc = tevt;
				}
				//if(dojo.hostenv.name_ == "browser"){
				var tf = function(){ 
					var ntf = new String(thisFunc);
					return function(evt){
						if(_this[ntf]){
							_this[ntf](evt);
						}
					}
				}();
				dojo.event.browser.addListener(baseNode, tevt.substr(2), tf);
			}
		}

		for(var y=0; y<events.length; y++){
			//alert(events[x]);
			var evtVal = baseNode.getAttribute(events[y]);
			if((evtVal)&&(evtVal.length)){
				var thisFunc = null;
				var domEvt = events[y].substr(4).toLowerCase(); // clober the "dojo" prefix
				thisFunc = dojo.text.trim(evtVal);
				var tf = function(){ 
					var ntf = new String(thisFunc);
					return function(evt){
						if(_this[ntf]){
							_this[ntf](evt);
						}
					}
				}();
				// dojo.event.connect(baseNode, domEvt, tf);
				dojo.event.browser.addListener(baseNode, domEvt.substr(2), tf);
			}
		}

		var onBuild = baseNode.getAttribute(this.onBuildProperty);
		if(onBuild){
			eval("var node = baseNode; var widget = targetObj; "+onBuild);
		}
	}

	// dj_debug("attachTemplateNodes toc: ", new Date()-start, "ms");
}

dojo.widget.getDojoEventsFromStr = function(str){
	// var lstr = str.toLowerCase();
	var re = /(dojoOn([a-z]+)(\s?))=/gi;
	var evts = str ? str.match(re)||[] : [];
	var ret = [];
	var lem = {};
	for(var x=0; x<evts.length; x++){
		if(evts[x].legth < 1){ continue; }
		var cm = evts[x].replace(/\s/, "");
		cm = (cm.slice(0, cm.length-1));
		if(!lem[cm]){
			lem[cm] = true;
			ret.push(cm);
		}
	}
	return ret;
}


dojo.widget.buildAndAttachTemplate = function(obj, templatePath, templateCssPath, templateString, targetObj) {
	this.buildFromTemplate(obj, templatePath, templateCssPath, templateString);
	var node = dojo.xml.domUtil.createNodesFromText(obj.templateString, true)[0];
	this.attachTemplateNodes(node, targetObj||obj, obj, dojo.widget.getDojoEventsFromStr(templateString));
	return node;
}

dojo.widget.DomWidget = function(){
	dojo.widget.Widget.call(this);
	if((arguments.length>0)&&(typeof arguments[0] == "object")){
		this.create(arguments[0]);
	}
}
dj_inherits(dojo.widget.DomWidget, dojo.widget.Widget);

dojo.lang.extend(dojo.widget.DomWidget, {
	templateNode: null,
	templateString: null,
	subTemplates: {},
	domNode: null, // this is our visible representation of the widget!
	containerNode: null, // holds child elements

	// FIXME: should we support addition at an index in the children arr and
	// order the display accordingly? Right now we always append.
	addChild: function(widget, overrideContainerNode, pos, ref, insertIndex){ 
		// var start = new Date();
		if(!this.isContainer){ // we aren't allowed to contain other widgets, it seems
			dj_debug("dojo.widget.DomWidget.addChild() attempted on non-container widget");
			return false;
		}else{
			if((!this.containerNode)&&(!overrideContainerNode)){
				this.containerNode = this.domNode;
			}
			var cn = (overrideContainerNode) ? overrideContainerNode : this.containerNode;
			if(!pos){ pos = "after"; }
			if(!ref){ ref = cn.lastChild; }
			if(!insertIndex) { insertIndex = 0; }
			widget.domNode.setAttribute("dojoinsertionindex", insertIndex);
			if(!ref){
				cn.appendChild(widget.domNode);
			}else{
				dojo.xml.domUtil[pos](widget.domNode, ref, insertIndex);
			}
			// dj_debug(this.widgetId, "added", widget.widgetId, "as a child");
			this.children.push(widget);
			widget.parent = this;
			widget.addedTo(this);
		}
		// dj_debug("add child took: ", new Date()-start, "ms");
		return widget;
	},

	// FIXME: we really need to normalize how we do things WRT "destroy" vs. "remove"
	removeChild: function(widget){
		for(var x=0; x<this.children.length; x++){
			if(this.children[x] === widget){
				this.children.splice(x, 1);
				break;
			}
		}
		return widget;
	},
	
	postInitialize: function(args, frag, parentComp){
		if(parentComp){
			parentComp.addChild(this, "", "insertAtIndex", "",  args["dojoinsertionindex"]);
		}else{
			if(!frag){ return; }
			var sourceNodeRef = frag["dojo:"+this.widgetType.toLowerCase()]["nodeRef"];
			if(!sourceNodeRef){ return; } // fail safely if we weren't instantiated from a fragment
			// FIXME: this will probably break later for more complex nesting of widgets
			// FIXME: this will likely break something else, and has performance issues
			// FIXME: it also seems to be breaking mixins
			// FIXME: this breaks when the template for the container widget has child
			// nodes

			this.parent = dojo.widget.manager.root;
			// insert our domNode into the DOM in place of where we started
			if((this.domNode)&&(this.domNode !== sourceNodeRef)){
				var oldNode = sourceNodeRef.parentNode.replaceChild(this.domNode, sourceNodeRef);
			}
		}

		if(this.isContainer){
			var elementNodeType = dojo.xml.domUtil.nodeTypes.ELEMENT_NODE;
			// FIXME: this is borken!!!

			var fragParser = dojo.widget.getParser();
			// build any sub-components with us as the parent
			fragParser.createComponents(frag, this);
		}
	},

	startResize: function(coords){
		dj_unimplemented("dojo.widget.DomWidget.startResize");
	},

	updateResize: function(coords){
		dj_unimplemented("dojo.widget.DomWidget.updateResize");
	},

	endResize: function(coords){
		dj_unimplemented("dojo.widget.DomWidget.endResize");
	},

	// method over-ride
	buildRendering: function(args, frag){
		// DOM widgets construct themselves from a template
		var ts = dojo.widget.DomWidget.templates[this.widgetType];
		if(	
			(this.templatePath)||
			(this.templateNode)||
			(
				(this["templateString"])&&(this.templateString.length) 
			)||
			(
				(typeof ts != "undefined")&&( (ts["string"])||(ts["node"]) )
			)
		){
			// if it looks like we can build the thing from a template, do it!
			this.buildFromTemplate(args, frag);
		}else{
			// otherwise, assign the DOM node that was the source of the widget
			// parsing to be the root node
			this.domNode = frag["dojo:"+this.widgetType.toLowerCase()]["nodeRef"];
		}
		this.fillInTemplate(args, frag); 	// this is where individual widgets
											// will handle population of data
											// from properties, remote data
											// sets, etc.
	},

	buildFromTemplate: function(args, frag){
		// var start = new Date();
		// copy template properties if they're already set in the templates object
		var ts = dojo.widget.DomWidget.templates[this.widgetType];
		if(ts){
			if(!this.templateString.length){
				this.templateString = ts["string"];
			}
			if(!this.templateNode){
				this.templateNode = ts["node"];
			}
		}
		var node = null;
		// attempt to clone a template node, if there is one
		if((!this.templateNode)&&(this.templateString)){
			// do root conversion on the template string if required
			this.templateString = this.templateString.replace(/\$\{baseScriptUri\}/mg, dojo.hostenv.getBaseScriptUri());
			this.templateString = this.templateString.replace(/\$\{dojoRoot\}/mg, dojo.hostenv.getBaseScriptUri());
			// FIXME: what other replacement productions do we want to make available? Arbitrary eval's?

			// otherwise, we are required to instantiate a copy of the template
			// string if one is provided.
			
			// FIXME: need to be able to distinguish here what should be done
			// or provide a generic interface across all DOM implementations
			// FIMXE: this breaks if the template has whitespace as its first 
			// characters
			// node = this.createNodesFromText(this.templateString, true);
			// this.templateNode = node[0].cloneNode(true); // we're optimistic here
			this.templateNode = this.createNodesFromText(this.templateString, true)[0];
			ts.node = this.templateNode;
		}
		if(!this.templateNode){ 
			dj_debug("weren't able to create template!");
			return false;
		}

		// dj_debug("toc0: ", new Date()-start, "ms");
		var node = this.templateNode.cloneNode(true);
		if(!node){ return false; }

		// recurse through the node, looking for, and attaching to, our
		// attachment points which should be defined on the template node.

		this.domNode = node;
		// dj_debug("toc1: ", new Date()-start, "ms");
		this.attachTemplateNodes(this.domNode, this);
		// dj_debug("toc2: ", new Date()-start, "ms");
	},

	attachTemplateNodes: function(baseNode, targetObj){
		if(!targetObj){ targetObj = this; }
		return dojo.widget.attachTemplateNodes(baseNode, targetObj, this, 
					dojo.widget.getDojoEventsFromStr(this.templateString));
	},

	fillInTemplate: function(){
		// dj_unimplemented("dojo.widget.DomWidget.fillInTemplate");
	},
	
	// method over-ride
	destroyRendering: function(){
		try{
			var tempNode = this.domNode.parentNode.removeChild(this.domNode);
			delete tempNode;
		}catch(e){ /* squelch! */ }
	},

	// FIXME: method over-ride
	cleanUp: function(){},
	
	getContainerHeight: function(){
		// FIXME: the generic DOM widget shouldn't be using HTML utils!
		return dojo.xml.htmlUtil.getInnerHeight(this.domNode.parentNode);
	},

	getContainerWidth: function(){
		// FIXME: the generic DOM widget shouldn't be using HTML utils!
		return dojo.xml.htmlUtil.getInnerWidth(this.domNode.parentNode);
	},

	createNodesFromText: function(){
		dj_unimplemented("dojo.widget.DomWidget.createNodesFromText");
	}
});
dojo.widget.DomWidget.templates = {};
