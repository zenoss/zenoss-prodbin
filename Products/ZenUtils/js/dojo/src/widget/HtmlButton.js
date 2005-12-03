/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.HtmlButton");
dojo.require("dojo.widget.HtmlWidget");
dojo.require("dojo.widget.Button");

dojo.widget.HtmlButton = function(){
	// mix in the button properties
	dojo.widget.Button.call(this);
	dojo.widget.HtmlWidget.call(this);

	this.templatePath = dojo.uri.dojoUri("src/widget/templates/HtmlButtonTemplate.html");
	this.templateCssPath = dojo.uri.dojoUri("src/widget/templates/HtmlButtonTemplate.css");

	// FIXME: freaking implement this already!
	this.foo = function(){ alert("bar"); }

	this.label = "huzzah!";
	this.labelNode = null;

	this.setLabel = function(){
		this.labelNode.innerHTML = this.label;
		// this.domNode.label = this.label;
	}

	this.fillInTemplate = function(){
		this.setLabel();
	}

	this.onFoo = function(){ }
}
dj_inherits(dojo.widget.HtmlButton, dojo.widget.HtmlWidget);
