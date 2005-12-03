/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above *///	dojo.require("dojo.alg.*");
dojo.provide("dojo.collections.Collections");

dojo.collections = {Collections:true};
dojo.collections.DictionaryEntry = function(k,v){
	this.key = k;
	this.value = v;
}

dojo.collections.Iterator = function(a){
	var o = a;
	var position = 0;
	this.current = null;
	this.atEnd = false;
	this.moveNext = function(){
		if (this.atEnd) return !this.atEnd;
		this.current = o[position];
		if (position == o.length) this.atEnd = true;
		position++;
		return !this.atEnd;
	}
	this.reset = function(){
		position = 0;
		this.atEnd = false;
	}
}

dojo.collections.DictionaryIterator = function(obj){
	var o = [] ;	//	Create an indexing array
	for (var p in obj) o[o.length] = obj[p] ;	//	fill it up
	var position = 0 ;
	this.current = null ;
	this.entry = null ;
	this.key = null ;
	this.value = null ;
	this.atEnd = false ;
	this.moveNext = function() { 
		if (this.atEnd) return !this.atEnd ;
		this.entry = this.current = o[position] ;
		if (this.entry) {
			this.key = this.entry.key ;
			this.value = this.entry.value ;
		}
		if (position == o.length) this.atEnd = true ;
		position++ ;
		return !this.atEnd ;
	} ;
	this.reset = function() { 
		position = 0 ; 
		this.atEnd = false ;
	} ;
};
