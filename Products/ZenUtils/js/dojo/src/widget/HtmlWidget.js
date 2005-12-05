/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.require("dojo.widget.DomWidget");
dojo.provide("dojo.widget.HtmlWidget");

dojo.widget.HtmlWidget = function(args){
	// mixin inheritance
	dojo.widget.DomWidget.call(this);
}

dj_inherits(dojo.widget.HtmlWidget, dojo.widget.DomWidget);

dojo.lang.extend(dojo.widget.HtmlWidget, {
	templateCssPath: null,
	templatePath: null,
	allowResizeX: true,
	allowResizeY: true,

	resizeGhost: null,
	initialResizeCoords: null,
	// this.templateString = null;

	getContainerHeight: function(){
		// NOTE: container height must be returned as the INNER height
		dj_unimplemented("dojo.widget.HtmlWidget.getContainerHeight");
	},

	getContainerWidth: function(){
		return this.parent.domNode.offsetWidth;
	},

	setNativeHeight: function(height){
		var ch = this.getContainerHeight();
	},

	startResize: function(coords){
		// get the left and top offset of our dom node
		var hu = dojo.xml.htmlUtil;
		
		coords.offsetLeft = hu.totalOffsetLeft(this.domNode);
		coords.offsetTop = hu.totalOffsetTop(this.domNode);
		coords.innerWidth = hu.getInnerWidth(this.domNode);
		coords.innerHeight = hu.getInnerHeight(this.domNode);
		if(!this.resizeGhost){
			this.resizeGhost = document.createElement("div");
			var rg = this.resizeGhost;
			rg.style.position = "absolute";
			rg.style.backgroundColor = "white";
			rg.style.border = "1px solid black";
			dojo.xml.htmlUtil.setOpacity(rg, 0.3);
			document.body.appendChild(rg);
		}
		with(this.resizeGhost.style){
			left = coords.offsetLeft + "px";
			top = coords.offsetTop + "px";
		}
		this.initialResizeCoords = coords;
		this.resizeGhost.style.display = "";
		this.updateResize(coords, true);
	},

	updateResize: function(coords, override){
		var dx = coords.x-this.initialResizeCoords.x;
		var dy = coords.y-this.initialResizeCoords.y;
		with(this.resizeGhost.style){
			if((this.allowResizeX)||(override)){
				width = this.initialResizeCoords.innerWidth + dx + "px";
			}
			if((this.allowResizeY)||(override)){
				height = this.initialResizeCoords.innerHeight + dy + "px";
			}
		}
	},

	endResize: function(coords){
		// FIXME: need to actually change the size of the widget!
		var dx = coords.x-this.initialResizeCoords.x;
		var dy = coords.y-this.initialResizeCoords.y;
		with(this.domNode.style){
			if(this.allowResizeX){
				width = this.initialResizeCoords.innerWidth + dx + "px";
			}
			if(this.allowResizeY){
				height = this.initialResizeCoords.innerHeight + dy + "px";
			}
		}
		this.resizeGhost.style.display = "none";
	},


	createNodesFromText: function(txt, wrap){
		return dojo.xml.domUtil.createNodesFromText(txt, wrap);
	},

	_old_buildFromTemplate: dojo.widget.DomWidget.prototype.buildFromTemplate,

	buildFromTemplate: function(){
		dojo.widget.buildFromTemplate(this);
		this._old_buildFromTemplate();
	},

	destroyRendering: function(finalize){
		try{
			var tempNode = this.domNode.parentNode.removeChild(this.domNode);
			if(!finalize){
				dojo.event.browser.clean(tempNode);
			}
			delete tempNode;
		}catch(e){ /* squelch! */ }
	}
});
