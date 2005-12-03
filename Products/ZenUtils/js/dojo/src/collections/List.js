/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.collections.List");
dojo.require("dojo.collections.Collections");

dojo.collections.List = function(dictionary){
	var items = {};
	var q = [];
	
	if (dictionary){
		var e = dictionary.getIterator();
		while (e.moveNext()){
			items[e.key] = q[q.length] = new dojo.collections.DictionaryEntry(e.key, e.value);
		}
	}
	this.count = q.length;

	this.add = function(k, v){
		items[k] = q[q.length] = new dojo.collections.DictionaryEntry(k,v);
		this.count = q.length;
	};
	this.clear = function(){
		items = {};
		q = [];
		this.count = q.length;
	};
	this.clone = function(){
		return new dojo.collections.List(this);
	};
	this.contains = this.containsKey = function(k){
		return (items[k] != null);
	};
	this.containsValue = function(o){
		var e = this.getIterator();
		while (e.moveNext()){
			if (e.value == o) return true;
		}
		return false;
	};
	this.copyTo = function(arr,i){
		var e = this.getIterator();
		var idx = i;
		while (e.moveNext()){
			arr.splice(idx, 0, e.entry);
			idx++;
		}
	};
	this.getByIndex = function(i){
		return q[i].value;
	};
	this.getIterator = function(){
		return new dojo.collections.DictionaryIterator(items);
	};
	this.getKey = function(i){
		return q[i].key;
	};
	this.getKeyList = function(){
		var arr = [];
		var e = this.getIterator();
		while (e.moveNext()) arr.push(e.key);
		return arr;
	};
	this.getValueList = function(){
		var arr = [];
		var e = this.getIterator();
		while (e.moveNext()) arr.push(e.value);
		return arr;
	};
	this.indexOfKey = function(k){
		for (var i = 0; i < q.length; i++){
			if (q[i].key == k) return i;
		}
		return -1;
	};
	this.indexOfValue = function(o){
		for (var i = 0; i < q.length; i++){
			if (q[i].value == o) return i;
		}
		return -1;
	};
	this.item = function(k){
		return items[k];
	};
	this.remove = function(k){
		delete items[k];
		var arr = [];
		for (var i = 0; i < q.length; i++){
			if (q[i].key != k) arr.push(q[i]);
		}
		q = arr;
		this.count = q.length;
	};
	this.removeAt = function(i){
		delete items[q[i].key];
		q.splice(i,1);
		this.count = q.length;
	};
}
