/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.math");

/* Math utils from Dan's 13th lib stuff. See: http://pupius.co.uk/js/Toolkit.Drawing.js */

dojo.math = new function() {
	this.degToRad = function(x) { return (x*Math.PI) / 180; }
	this.radToDeg = function(x) { return (x*180) / Math.PI; }

	this.factorial = function(n) {
		if(n<1){ return 0; }
		var retVal = 1;
		for(var i=1;i<=n;i++){ retVal *= i; }
		return retVal;
	}

	//The number of ways of obtaining an ordered subset of k elements from a set of n elements
	this.permutations = function(n,k) {
		if(n==0 || k==0) return 1;
		return (this.factorial(n) / this.factorial(n-k));
	}

	//The number of ways of picking n unordered outcomes from r possibilities
	this.combinations = function(n,r) {
		if(n==0 || r==0) return 1;
		return (this.factorial(n) / (this.factorial(n-r) * this.factorial(r)));
	}

	this.bernstein = function (t,n,i) {
		return ( this.combinations(n,i) * Math.pow(t,i) * Math.pow(1-t,n-i) );
	}
};

dojo.provide("dojo.math.Math");
