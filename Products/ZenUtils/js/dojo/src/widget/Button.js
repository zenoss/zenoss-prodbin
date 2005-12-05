/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.Button");
dojo.require("dojo.widget.Widget");

dojo.widget.tags.addParseTreeHandler("dojo:button");

dojo.widget.Button = function(){
	dojo.widget.Widget.call(this);

	this.widgetType = "Button";
	this.onClick = function(){ return; }
	this.isContainer = false;
}
dj_inherits(dojo.widget.Button, dojo.widget.Widget);
