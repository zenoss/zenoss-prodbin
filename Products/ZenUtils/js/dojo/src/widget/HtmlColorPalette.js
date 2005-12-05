/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.HtmlColorPalette");
dojo.require("dojo.widget.*");
dojo.require("dojo.widget.Toolbar");


dojo.widget.tags.addParseTreeHandler("dojo:ToolbarColorDialog");

dojo.widget.HtmlToolbarColorDialog = function () {
	dojo.widget.HTMLToolbarDialog.call(this);
	
	for (var method in this.constructor.prototype) {
		this[method] = this.constructor.prototype[method];
	}
}

dj_inherits(dojo.widget.HtmlToolbarColorDialog, dojo.widget.HTMLToolbarDialog);

dojo.lang.extend(dojo.widget.HtmlToolbarColorDialog, {

	widgetType: "ToolbarColorDialog",
	
	fillInTemplate: function (args, frag) {
		dojo.widget.HtmlToolbarColorDialog.superclass.fillInTemplate.call(this, args, frag);
		this.dialog = dojo.widget.fromScript("ColorPalette");

		dojo.event.connect(this.dialog, "onColorSelect", this, "_setValue");
	},

	_setValue: function(color) {
		this._value = color;
		this._fireEvent("onSetValue", color);
	},
	
	showDialog: function (e) {
		dojo.widget.HtmlToolbarColorDialog.superclass.showDialog.call(this, e);
		with (dojo.xml.htmlUtil) {
			var x = getAbsoluteX(this.domNode);
			var y = getAbsoluteY(this.domNode) + getInnerHeight(this.domNode);
		}
		this.dialog.showAt(x, y);
	},
	
	hideDialog: function (e) {
		dojo.widget.HtmlToolbarColorDialog.superclass.hideDialog.call(this, e);
		this.dialog.hide();
	}
});



dojo.widget.tags.addParseTreeHandler("dojo:colorpalette");

dojo.widget.HtmlColorPalette = function () {
	dojo.widget.HtmlWidget.call(this);
}

dj_inherits(dojo.widget.HtmlColorPalette, dojo.widget.HtmlWidget);

dojo.lang.extend(dojo.widget.HtmlColorPalette, {

	widgetType: "colorpalette",

	buildRendering: function () {
	
		var colors = [["fff", "fcc", "fc9", "ff9", "ffc", "9f9", "9ff", "cff", "ccf", "fcf"],
			["ccc", "f66", "f96", "ff6", "ff3", "6f9", "3ff", "6ff", "99f", "f9f"],
			["c0c0c0", "f00", "f90", "fc6", "ff0", "3f3", "6cc", "3cf", "66c", "c6c"],
			["999", "c00", "f60", "fc3", "fc0", "3c0", "0cc", "36f", "63f", "c3c"],
			["666", "900", "c60", "c93", "990", "090", "399", "33f", "60c", "939"],
			["333", "600", "930", "963", "660", "060", "366", "009", "339", "636"],
			["000", "300", "630", "633", "330", "030", "033", "006", "309", "303"]];
	
		this.domNode = document.createElement("table");
		this.domNode.unselectable = "on";
		with (this.domNode) { // set the table's properties
			cellPadding = "0"; cellSpacing = "1"; border = "1";
			style.backgroundColor = "white"; style.position = "absolute";
		}
		var tbody = document.createElement("tbody");
		this.domNode.appendChild(tbody);
		for (var i = 0; i < colors.length; i++) {
			var tr = document.createElement("tr");
			for (var j = 0; j < colors[i].length; j++) {
				if (colors[i][j].length == 3) {
					colors[i][j] = colors[i][j].replace(/(.)(.)(.)/, "$1$1$2$2$3$3");
				}
	
				var td = document.createElement("td");
				with (td.style) {
					backgroundColor = "#" + colors[i][j];
					border = "1px solid gray";
					width = height = "15px";
					fontSize = "1px";
				}
	
				td.color = "#" + colors[i][j];
	
				td.onmouseover = function (e) { this.style.borderColor = "white"; }
				td.onmouseout = function (e) { this.style.borderColor = "gray"; }
				dojo.event.connect(td, "onmousedown", this, "click");
	
				td.innerHTML = "&nbsp;";
				tr.appendChild(td);
			}
			tbody.appendChild(tr);
		}
	},

	click: function (e) {
		this.onColorSelect(e.currentTarget.color);
		e.currentTarget.style.borderColor = "gray";
	},

	onColorSelect: function (color) { },

	hide: function () { this.domNode.parentNode.removeChild(this.domNode); },
	
	showAt: function (x, y) {
		with (this.domNode.style) { top = y + "px"; left = x + "px"; }
		document.body.appendChild(this.domNode);
	}

});
