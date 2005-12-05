/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.graphics.color");

dojo.graphics.color = new function() {
	// blend colors a and b (both as RGB array or hex strings) with weight from -1 to +1, 0 being a 50/50 blend
	this.blend = function(a, b, weight) {
		if(typeof a == "string") { return this.blendHex(a, b, weight); }
		if(!weight) { weight = 0; }
		else if(weight > 1) { weight = 1; }
		else if(weight < -1) { weight = -1; }
		var c = new Array(3);
		for(var i = 0; i < 3; i++) {
			var half = Math.abs(a[i] - b[i])/2;
			c[i] = Math.floor(Math.min(a[i], b[i]) + half + (half * weight));
		}
		return c;
	}

	// very convenient blend that takes and returns hex values
	// (will get called automatically by blend when blend gets strings)
	this.blendHex = function(a, b, weight) {
		return this.rgb2hex(this.blend(this.hex2rgb(a), this.hex2rgb(b), weight));
	}

	// get RGB array from css-style color declarations
	this.extractRGB = function(color) {
		var hex = "0123456789abcdef";
		color = color.toLowerCase();
		if( color.indexOf("rgb") == 0 ) {
			var matches = color.match(/rgba*\((\d+), *(\d+), *(\d+)/i);
			var ret = matches.splice(1, 3);
			return ret;
		} else if( color.indexOf("#") == 0 ) {
			var colors = [];
			color = color.substring(1);
			if( color.length == 3 ) {
				colors[0] = color.charAt(0) + color.charAt(0);
				colors[1] = color.charAt(1) + color.charAt(1);
				colors[2] = color.charAt(2) + color.charAt(2);
			} else {
				colors[0] = color.substring(0, 2);
				colors[1] = color.substring(2, 4);
				colors[2] = color.substring(4, 6);
			}

			for(var i = 0; i < colors.length; i++) {
				var c = colors[i];
				colors[i] = hex.indexOf(c.charAt(0))*16 + hex.indexOf(c.charAt(1));
			}
			return colors;
		} else {
			// named color (how many do we support?)
			switch(color) {
				case "white": return [255,255,255];
				case "black": return [0,0,0];
				case "red": return[255,0,0];
				case "green": return [0,255,0];
				case "blue": return [0,0,255];
				case "navy": return [0,0,128];
				case "gray": return [128,128,128];
				case "silver": return [192,192,192];
			}
		}
		return [255,255,255]; // assume white if all else fails
	}

	this.hex2rgb = function(hex) {
		var hexNum = "0123456789ABCDEF";
		var rgb = new Array(3);
		if( hex.indexOf("#") == 0 ) { hex = hex.substring(1); }
		hex = hex.toUpperCase();
		if( hex.length == 3 ) {
			rgb[0] = hex.charAt(0) + hex.charAt(0)
			rgb[1] = hex.charAt(1) + hex.charAt(1)
			rgb[2] = hex.charAt(2) + hex.charAt(2);
		} else {
			rgb[0] = hex.substring(0, 2);
			rgb[1] = hex.substring(2, 4);
			rgb[2] = hex.substring(4);
		}
		for(var i = 0; i < rgb.length; i++) {
			rgb[i] = hexNum.indexOf(rgb[i].charAt(0)) * 16 + hexNum.indexOf(rgb[i].charAt(1));
		}
		return rgb;
	}

	this.rgb2hex = function(r, g, b) {
		if(r.constructor == Array) {
			g = r[1] || 0;
			b = r[2] || 0;
			r = r[0] || 0;
		}
		return ["#", r.toString(16), g.toString(16), b.toString(16)].join("");
	}
}
