/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.Dialog");
dojo.provide("dojo.widget.HtmlDialog");

dojo.require("dojo.widget.*");
dojo.require("dojo.graphics.*");

dojo.widget.tags.addParseTreeHandler("dojo:dialog");

dojo.widget.HtmlDialog = function() {
	dojo.widget.HtmlDialog.superclass.constructor.call(this);

	this.widgetType = "Dialog";

	this.templateString = '<div class="dialog">'
		+ '<span dojoAttachPoint="tabStart" dojoOnFocus="trapTabs" dojoOnBlur="clearTrap" tabindex="0"></span>'
		+ '<div dojoAttachPoint="content"></div>'
		+ '<span dojoAttachPoint="tabEnd" dojoOnFocus="trapTabs" dojoOnBlur="clearTrap" tabindex="0"></span>'
		+ '</div>';

	// Only supports fade right now
	this.effect = "fade";
	this.effectDuration = 250;

	this.bg;
	this.bgColor = "black";
	this.bgOpacity = 0.4;

	var fromTrap = false;
	this.trapTabs = function(e) {
		if(e.target == this.tabStart) {
			if(fromTrap) {
				fromTrag = false;
			} else {
				fromTrap = true;
				this.tabEnd.focus();
			}
		} else if(e.target == this.tabEnd) {
			if(fromTrap) {
				fromTrag = false;
			} else {
				fromTrap = true;
				this.tabStart.focus();
			}
		}
	}

	this.clearTrap = function(e) {
		setTimeout(function() {
			fromTrap = false;
		}, 100);
	}

	this.postInitialize = function(args, frag, parentComp) {
		document.body.appendChild(this.domNode);
		this.nodeRef = frag["dojo:"+this.widgetType.toLowerCase()]["nodeRef"];
		if(this.nodeRef) {
			this.setContent(this.nodeRef);
		}
		this.bg = document.createElement("div");
		this.bg.className = "dialogUnderlay";
		with(this.bg.style) {
			position = "absolute";
			left = top = "0px";
			width = "100%";
			zIndex = 998;
			display = "none";
		}
		this.setBackgroundColor(this.bgColor);
		document.body.appendChild(this.bg);
		with(this.domNode.style) {
			position = "absolute";
			zIndex = 999;
			display = "none";
		}
	}

	this.setContent = function(content) {
		if(typeof content == "string") {
			this.content.innerHTML = content;
		} else if(content.nodeType != undefined) {
			while(this.content.hasChildNodes()) {
				this.content.removeChild(this.content.firstChild);
			}
			this.content.appendChild(content);
		} else {
			dj_throw("Tried to setContent with unknownn content (" + content + ")");
		}
	}

	this.setBackgroundColor = function(color) {
		if(arguments.length >= 3) {
			color = dojo.graphics.color.rgb2hex(arguments[0], arguments[1], arguments[2]);
		}
		this.bg.style.backgroundColor = color;
		return this.bgColor = color;
	}

	this.setBackgroundOpacity = function(op) {
		if(arguments.length == 0) { op = this.bgOpacity; }
		dojo.xml.htmlUtil.setOpacity(this.bg, op);
		return this.bgOpacity = dojo.xml.htmlUtil.getOpacity(this.bg);
	}

	this.sizeBackground = function() {
		var h = document.documentElement.scrollHeight || document.body.scrollHeight;
		this.bg.style.height = h + "px";
	}

	this.placeDialog = function() {
		var scrollTop = document.documentElement.scrollTop;
		var scrollLeft = document.documentElement.scrollLeft;
		var W = document.documentElement.clientWidth || document.body.clientWidth || 0;
		var H = document.documentElement.clientHeight || document.body.clientHeight || 0;
		this.domNode.style.display = "block";
		var w = this.domNode.offsetWidth;
		var h = this.domNode.offsetHeight;
		this.domNode.style.display = "none";
		var L = scrollLeft + (W - w)/2;
		var T = scrollTop + (H - h)/2;
		with(this.domNode.style) {
			left = L + "px";
			top = T + "px";
		}
	}

	this.show = function() {
		this.setBackgroundOpacity();
		this.sizeBackground();
		this.placeDialog();
		switch((this.effect||"").toLowerCase()) {
			case "fade":
				this.bg.style.display = "block";
				this.domNode.style.display = "block";
				dojo.graphics.htmlEffects.fade(this.domNode, this.effectDuration, 0, 1);
				break;
			default:
				this.bg.style.display = "block";
				this.domNode.style.display = "block";
				break;
		}
	}

	this.hide = function() {
		switch((this.effect||"").toLowerCase()) {
			case "fade":
				this.bg.style.display = "none";
				dojo.graphics.htmlEffects.fadeOut(this.domNode, this.effectDuration, function(node) { node.style.display = "none"; });
				break;
			default:
				this.bg.style.display = "none";
				this.domNode.style.display = "none";
				break;
		}
	}

	this.setCloseControl = function(node) {
		dojo.event.connect(node, "onclick", this, "hide");
	}
}
dj_inherits(dojo.widget.HtmlDialog, dojo.widget.HtmlWidget);
