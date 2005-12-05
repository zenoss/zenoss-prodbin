/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.lang.Lang");

dojo.lang.mixin = function(obj, props){
	var tobj = {};
	for(var x in props){
		if(typeof tobj[x] == "undefined"){
			obj[x] = props[x];
		}
	}
	return obj;
}

dojo.lang.extend = function(ctor, props){
	this.mixin(ctor.prototype, props);
}

dojo.lang.extendPrototype = function(obj, props){
	this.extend(obj.constructor, props);
}


/**
 * Sets a timeout in milliseconds to execute a function in a given context
 * with optional arguments.
 *
 * setTimeout (Object context, function func, number delay[, arg1[, ...]]);
 * setTimeout (function func, number delay[, arg1[, ...]]);
 */
dojo.lang.setTimeout = function (func, delay) {
	var context = window, argsStart = 2;
	if (typeof delay == "function") {
		context = func;
		func = delay;
		delay = arguments[2];
		argsStart++;
	}
	
	var args = [];
	for (var i = argsStart; i < arguments.length; i++) {
		args.push(arguments[i]);
	}
	return setTimeout(function () { func.apply(context, args); }, delay);
}

// Partial implmentation of is* functions from
// http://www.crockford.com/javascript/recommend.html
dojo.lang.mixin(dojo.lang, {
	isObject : function(wh) {
		return typeof wh == "object" || dojo.lang.isArray(wh) || dojo.lang.isFunction(wh);
	},

	isArray : function(wh) {
		return (wh instanceof Array || typeof wh == "array");
	},

	isFunction : function(wh) {
		return (wh instanceof Function || typeof wh == "function");
	},

	isString : function(wh) {
		return (wh instanceof String || typeof wh == "string");
	},

	isNumber : function(wh) {
		return (wh instanceof Number || typeof wh == "number");
	},

	isBoolean : function(wh) {
		return (wh instanceof Boolean || typeof wh == "boolean");
	},

	isUndefined : function(wh) {
		return wh == undefined;
	}
});
