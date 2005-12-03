/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.Menu");
dojo.provide("dojo.widget.DomMenu");
dojo.provide("dojo.widget.HtmlMenu");

dojo.require("dojo.widget.Widget");
dojo.require("dojo.widget.DomWidget");
dojo.require("dojo.widget.HtmlWidget");


dojo.widget.tags.addParseTreeHandler("dojo:menu");

/* Menu
 *******/

dojo.widget.Menu = function () {
	dojo.widget.Menu.superclass.constructor.call(this);
}
dj_inherits(dojo.widget.Menu, dojo.widget.Widget);

dojo.lang.extend(dojo.widget.Menu, {
	widgetType: "Menu",
	
	items: [],

	push: function (item) {
		dojo.connect.event(item, "onSelect", this, "onSelect");
		this.items.push(item);
	}

});


/* DomMenu
 **********/

dojo.widget.DomMenu = function(){
	dojo.widget.DomMenu.superclass.constructor.call(this);
}
dj_inherits(dojo.widget.DomMenu, dojo.widget.DomWidget);

dojo.lang.extend(dojo.widget.DomMenu, {
	widgetType: "Menu",

	push: function (item) {
		dojo.widget.Menu.call(this, item);
		this.domNode.appendChild(item.domNode);
	}
});


/* HtmlMenu
 ***********/
 
dojo.widget.HtmlMenu = function(){
	dojo.widget.HtmlMenu.superclass.constructor.call(this);
}
dj_inherits(dojo.widget.HtmlMenu, dojo.widget.HtmlWidget);

dojo.lang.extend(dojo.widget.HtmlMenu, {
	widgetType: "Menu",

	templateString: '<ul style="list-style: none; padding: 0; margin: 0;"></ul>',
	templateCssPath: dojo.uri.dojoUri("src/widget/templates/Menu.css"),
	
	fillInTemplate: function () {
		//dojo.widget.HtmlMenu.superclass.fillInTemplate.apply(this, arguments);
		this.domNode.className = "Menu";
	},
	
	push: dojo.widget.DomMenu.prototype.push

});
