/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.text.String");

dojo.text = {
	trim: function(iString){
		if(arguments.length == 0){ // allow String.prototyp-ing
			iString = this; 
		}
		if(typeof iString != "string"){ return iString; }
		if(!iString.length){ return iString; }
		return iString.replace(/^\s*/, "").replace(/\s*$/, "");
	},

	// Parameterized string function
	//  str - formatted string with %{values} to be replaces
	//  pairs - object of name: "value" value pairs
	//  killExtra - remove all remaining %{values} after pairs are inserted
	paramString: function(str, pairs, killExtra) {
		if(typeof str != "string") { // allow String.prototype-ing
			pairs = str;
			killExtra = pairs;
			str = this;
		}

		for(var name in pairs) {
			var re = new RegExp("\\%\\{" + name + "\\}", "g");
			str = str.replace(re, pairs[name]);
		}

		if(killExtra) { str = str.replace(/%\{([^\}\s]+)\}/g, ""); }
		return str;
	},
	
	/** Uppercases the first letter of each word */
	capitalize: function (str) {
		if (typeof str != "string" || str == null)
			return "";
		if (arguments.length == 0) { str = this; }
		var words = str.split(' ');
		var retval = "";
		var len = words.length;
		for (var i=0; i<len; i++) {
			var word = words[i];
			word = word.charAt(0).toUpperCase() + word.substring(1, word.length);
			retval += word;
			if (i < len-1)
				retval += " ";
		}
		
		return new String(retval);
	},
	
	isBlank: function (str) {
		if (typeof str != "string" || str == null)
			return true;
		return (dojo.text.trim(str).length == 0);
	}
}

/*
 * We need to make sure that the dojo.text.Text Object exists, the
 * above assignment causes it to be clobbered so we redefine it here.
 */
dojo.text.String = {};
