/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.widget.Tabs");
dojo.provide("dojo.widget.HtmlTabs");

dojo.require("dojo.io.*");
dojo.require("dojo.widget.*");
dojo.require("dojo.graphics.*");

dojo.widget.HtmlTabs = function() {
	dojo.widget.HtmlWidget.call(this);

	this.widgetType = "Tabs";
	this.isContainer = true;

	this.templatePath = null; // prolly not
	this.templateCssPath = null; // maybe

	this.domNode = null;
	this.containerNode = null;

	this.tabs = [];
	this.panels = [];
	this.selected = -1;

	this.tabTarget = "";
	this.extractContent = false; // find the bits inside <body>
	this.parseContent = false; // parse externally loaded pages for widgets

	this.buildRendering = function(args, frag) {
		this.domNode = frag["dojo:"+this.widgetType.toLowerCase()]["nodeRef"];
		if(!this.domNode) { dj_error("HTMLTabs: No node reference"); }

		if(args["tabtarget"]) {
			this.tabtarget = args["tabtarget"];
			this.containerNode = document.getElementById(args["tabtarget"]);
		} else {
			this.containerNode = document.createElement("div");
			var next = this.domNode.nextSibling;
			if(next) {
				this.domNode.parentNode.insertBefore(this.containerNode, next);
			} else {
				this.domNode.parentNode.appendChild(this.containerNode);
			}
		}
		dojo.xml.htmlUtil.addClass(this.containerNode, "dojoTabPanelContainer");

		var li = dojo.xml.domUtil.getFirstChildTag(this.domNode);
		while(li) {
			var a = li.getElementsByTagName("a").item(0);
			this.addTab(a);
			li = dojo.xml.domUtil.getNextSiblingTag(li);
		}

		if(this.selected == -1) { this.selected = 0; }
		this.selectTab(null, this.tabs[this.selected]);
	}

	this.addTab = function(title, url) {
		if(title && title.tagName && title.tagName.toLowerCase() == "a") {
			// init case
			var a = title;
			var li = a.parentNode;
			title = a.innerHTML;
			url = a.getAttribute("href");
			if(url.indexOf("#") > 0 && location.href.split("#")[0] == url.split("#")[0]) {
				url = "#" + url.split("#")[1];
			}
		} else {
			// programmatically adding
			var li = document.createElement("li");
			var a = document.createElement("a");
			a.innerHTML = title;
			a.href = url;
			li.appendChild(a);
			this.domNode.appendChild(li);
		}

		dojo.event.connect(a, "onclick", this, "selectTab");

		this.tabs.push(li);
		var panel = {url: url, loaded: false, id: null};
		this.panels.push(panel);
		if(panel.url.charAt(0) == "#") { this.getPanel(panel); }

		if(this.selected == -1 && dojo.xml.htmlUtil.hasClass(li, "current")) {
			this.selected = this.tabs.length-1;
		}
	}

	this.selectTab = function(e, target) {
		if(e) {
			if(e.target) {
				target = e.target;
				while(target && (target.tagName||"").toLowerCase() != "li") {
					target = target.parentNode;
				}
			}
			if(e.preventDefault) { e.preventDefault(); }
		}

		dojo.xml.htmlUtil.removeClass(this.tabs[this.selected], "current");

		for(var i = 0; i < this.tabs.length; i++) {
			if(this.tabs[i] == target) {
				dojo.xml.htmlUtil.addClass(this.tabs[i], "current");
				this.selected = i;
				break;
			}
		}

		var panel = this.panels[this.selected];
		if(panel) {
			this.getPanel(panel);
			this.hidePanels(panel);
			document.getElementById(panel.id).style.display = "";
		}
	}

	this.getPanel = function(panel) {
		if(!panel || panel.loaded) { return; }

		if(panel.url.charAt(0) == "#") {
			var id = panel.url.substring(1);
			var node = document.getElementById(id);
			node.style.display = "none";
			this.containerNode.appendChild(node);
		} else {
			var node = document.createElement("div");
			node.innerHTML = "Loading...";
			node.style.display = "none";
			node.id = dojo.xml.domUtil.getUniqueId();
			this.containerNode.appendChild(node);

			var extract = this.extractContent;
			var parse = this.parseContent;
			dojo.io.bind({
				url: panel.url,
				useCache: true,
				mimetype: "text/html",
				handler: function(type, data, e) {
					if(type == "load") {
						if(extract) {
							var matches = data.match(/<body[^>]*>\s*([\s\S]+)\s*<\/body>/im);
							if(matches) { data = matches[1]; }
						}
						node.innerHTML = data;
						if(parse) {
							var parser = new dojo.xml.Parse();
							var frag = parser.parseElement(node, null, true);
							dojo.widget.getParser().createComponents(frag);
						}
					} else {
						node.innerHTML = "Error loading '" + panel.url + "' (" + e.status + " " + e.statusText + ")";
					}
				}
			});
		}

		panel.id = node.id;
		panel.loaded = true;
	}

	this.hidePanels = function(except) {
		for(var i = 0; i < this.panels.length; i++) {
			if(this.panels[i] != except && this.panels[i].id) {
				var p = document.getElementById(this.panels[i].id);
				if(p) {
					p.style.display = "none";
				}
			}
		}
	}
}
dj_inherits(dojo.widget.HtmlTabs, dojo.widget.HtmlWidget);

dojo.widget.tags.addParseTreeHandler("dojo:tabs");
