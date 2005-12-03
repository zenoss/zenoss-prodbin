/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.HtmlContextMenu");
dojo.require("dojo.widget.HtmlWidget");
dojo.require("dojo.widget.ContextMenu");

dojo.widget.HtmlContextMenu = function(){
	dojo.widget.ContextMenu.call(this);
	dojo.widget.HtmlWidget.call(this);

	this.templatePath = dojo.uri.dojoUri("src/widget/templates/HtmlContextMenuTemplate.html");
	this.templateCssPath = dojo.uri.dojoUri("src/widget/templates/HtmlContextMenuTemplate.css");

	this.fillInTemplate = function(){
		// this.setLabel();
	}

	this.onShow = function(evt){
		evt.preventDefault();
		evt.stopPropagation();

		// FIXME: use whatever we use to do more general style setting?
		// FIXME: FIX this into something useful
		this.domNode.style.left = evt.clientX + "px";
		this.domNode.style.top = evt.clientY + "px";
		this.domNode.style.display = "block";
		dojo.event.connect(doc, "onclick", this, "onHide");
		return false;
	}
	
	this.onHide = function(){
		// FIXME: use whatever we use to do more general style setting?
		this.domNode.style.display = "none";
		dojo.event.disconnect(doc, "onclick", this, "onHide");
	}
	
	// FIXME: short term hack to show a single context menu in HTML
	// FIXME: need to prevent the default context menu...
	
	var doc = document.documentElement  || document.body;
	dojo.event.connect(doc, "oncontextmenu", this, "onShow");
}

dj_inherits(dojo.widget.HtmlContextMenu, dojo.widget.HtmlWidget);
