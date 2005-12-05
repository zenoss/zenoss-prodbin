/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.collections.ArrayList");
dojo.require("dojo.collections.Collections");

dojo.collections.ArrayList = function(arr){
	var items = [];
	if (arr) items = items.concat(arr);
	this.count = items.length;
	this.add = function(o){
		items.push(o);
		this.count = items.length;
	};
	this.addRange = function(a){
		if (a.getIterator) {
			var e = new dojo.collections.Iterator(a);
			while (e.moveNext()) {
				this.add(e.current);
			}
			this.count = items.length;
		} else {
			items.concat(a);
			this.count = items.length;
		}
	};
	this.binarySearch = function(key, fn){
		var arr = ([].concat(items)).sort((fn?fn:'')) ;
		var low = -1 ;
		var high = arr.length ;
		var i ;
		while ((high - low) > 1) {
			i = ((low + high) >>> 1) ;
			if (key <= arr[i]) high = i ;
			else low = i ;
		}
		if (key == arr[high]) return high ;
		return -1 ;
	};
	this.clear = function(){
		items.splice(0, items.length);
		this.count = 0;
	};
	this.clone = function(){
		return new dojo.collections.ArrayList(items);
	};
	this.contains = function(o){
		for (var i = 0; i < items.length; i++){
			if (items[i] == o) return true;
		}
		return false;
	};
	this.getIterator = function(){
		return new dojo.collections.Iterator(items);
	};
	this.indexOf = function(o){
		for (var i = 0; i < items.length; i++){
			if (items[i] == o) return i;
		}
		return -1;
	};
	this.insert = function(i, o){
		items.splice(i,0,o);
		this.count = items.length;
	};
	this.item = function(k){
		return items[k];
	};
	this.remove = function(o){
		var i = this.indexOf(o);
		if (i >=0) items.splice(i,1);
		this.count = items.length;
	};
	this.removeAt = function(i){
		items.splice(i,1);
		this.count = items.length;
	};
	this.reverse = function(){
		items.reverse();
	};
	this.sort = function(fn){
		items.sort(fn);
	};
	this.toArray = function(){
		return [].concat(items);
	}
	this.toString = function(){
		return items.join(",");
	};
};
