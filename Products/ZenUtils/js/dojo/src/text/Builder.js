/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.text.Builder");
dojo.require("dojo.text");

dojo.text.Builder = function(str){
	var a = [];
	var b = str || "";
	var length = this.length = b.length;
	if (!dojo.text.isBlank(b)) a.push(b);
	b = "";
	this.toString = this.valueOf = function(){ 
		return a.join(""); 
	};
	this.append = function(s){
		a.push(s);
		length += s.length;
		this.length = length;
	};
	this.clear = function(){
		a=[];
		length = this.length = 0;
	};
	this.remove = function(f,l){
		var s = ""; 
		b = a.join(""); 
		a=[];
		if (f >0) s = b.substring(0, (f-1));
		b = s + b.substring(f + l); 
		a.push(b);
		length = this.length = b.length; 
		b="";
	};
	this.replace = function(o,n){
		b = a.join(""); 
		a = []; 
		b.replace(o,n); 
		a.push(b);
		length = this.length = b.length; 
		b="";
	};
	this.insert = function(idx,s){
		b = a.join(""); 
		a=[];
		if (idx == 0) b = s + b;
		else {
			var start = b.substring(0, idx-1);
			var end = b.substring(idx);
			b = start + s + end;
		}
		length = this.length = b.length; 
		a.push(b); 
		b="";
	};
};
