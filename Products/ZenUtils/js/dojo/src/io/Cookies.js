/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.io.Cookies");

dojo.io.cookies = new function() {
	this.setCookie = function(name, value, days, path) {
		var expires = -1;
		if(typeof days == "number" && days >= 0) {
			var d = new Date();
			d.setTime(d.getTime()+(days*24*60*60*1000));
			expires = d.toGMTString();
		}
		value = escape(value);
		document.cookie = name + "=" + value + ";"
			+ (expires != -1 ? " expires=" + expires + ";" : "")
			+ "path=" + (path || "/");
	}

	this.getCookie = function(name) {
		var idx = document.cookie.indexOf(name+'=');
		if(idx == -1) { return null; }
		value = document.cookie.substring(idx+name.length+1);
		var end = value.indexOf(';');
		if(end == -1) { end = value.length; }
		value = value.substring(0, end);
		value = unescape(value);
		return value;
	}

	this.deleteCookie = function(name) {
		this.setCookie(name, "-", 0);
	}

	this.setObjectCookie = function(name, obj, days, path, clearCurrent) {
		var pairs = [], cookie, value = "";
		if(!clearCurrent) { cookie = this.getObjectCookie(name); }
		if(days >= 0) {
			if(!cookie) { cookie = {}; }
			for(var prop in obj) {
				if(prop == null) {
					delete cookie[prop];
				} else if(typeof obj[prop] == "string" || typeof obj[prop] == "number") {
					cookie[prop] = obj[prop];
				}
			}
			prop = null;
			for(var prop in cookie) {
				pairs.push(escape(prop) + "=" + escape(cookie[prop]));
			}
			value = pairs.join("&");
		}
		this.setCookie(name, value, days, path);
	}

	this.getObjectCookie = function(name) {
		var values = null, cookie = this.getCookie(name);
		if(cookie) {
			values = {};
			var pairs = cookie.split("&");
			for(var i = 0; i < pairs.length; i++) {
				var pair = pairs[i].split("=");
				var value = pair[1];
				if( isNaN(value) ) { value = unescape(pair[1]); }
				values[ unescape(pair[0]) ] = value;
			}
		}
		return values;
	}

	this.isSupported = function() {
		if(typeof navigator.cookieEnabled != "boolean") {
			this.setCookie("__TestingYourBrowserForCookieSupport__", "CookiesAllowed", 90, null);
			var cookieVal = this.getCookie("__TestingYourBrowserForCookieSupport__");
			navigator.cookieEnabled = (cookieVal == "CookiesAllowed");
			if(navigator.cookieEnabled) {
				// FIXME: should we leave this around?
				this.deleteCookie("__TestingYourBrowserForCookieSupport__");
			}
		}
		return navigator.cookieEnabled;
	}
};
