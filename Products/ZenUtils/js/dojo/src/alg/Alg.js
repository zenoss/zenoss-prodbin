/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.alg.Alg");

dojo.alg.find = function(arr, val){
	for(var i=0;i<arr.length;++i){
		if(arr[i] == val){ return i; }
	}
	return -1;
}

dojo.alg.inArray = function(arr, val){
	// support both (arr, val) and (val, arr)
	if( (!arr || arr.constructor != Array) && (val && val.constructor == Array) ) {
		var a = arr;
		arr = val;
		val = a;
	}
	return dojo.alg.find(arr, val) > -1;
}
dojo.alg.inArr = dojo.alg.inArray; // for backwards compatibility

dojo.alg.getNameInObj = function(ns, item){
	if(!ns){ ns = dj_global; }

	for(var x in ns){
		if(ns[x] === item){
			return new String(x);
		}
	}
	return null;
}

// is this the right place for this?
dojo.alg.has = function(obj, name){
	return (typeof obj[name] !== 'undefined');
}

dojo.alg.forEach = function(arr, unary_func, fix_length){
	var il = arr.length;
	for(var i=0; i< ((fix_length) ? il : arr.length); i++){
		if(unary_func(arr[i]) == "break"){
			break;
		}
	}
}

dojo.alg.for_each = dojo.alg.forEach; // burst compat

dojo.alg.map = function(arr, obj, unary_func){
	for(var i=0;i<arr.length;++i){
		unary_func.call(obj, arr[i]);
	}
}

dojo.alg.tryThese = function(){
	for(var x=0; x<arguments.length; x++){
		try{
			if(typeof arguments[x] == "function"){
				var ret = (arguments[x]());
				if(ret){
					return ret;
				}
			}
		}catch(e){
			dj_debug(e);
		}
	}
}

dojo.alg.delayThese = function(farr, cb, delay, onend){
	/**
	 * alternate: (array funcArray, function callback, function onend)
	 * alternate: (array funcArray, function callback)
	 * alternate: (array funcArray)
	 */
	if(!farr.length){ 
		if(typeof onend == "function"){
			onend();
		}
		return;
	}
	if((typeof delay == "undefined")&&(typeof cb == "number")){
		delay = cb;
		cb = function(){};
	}else if(!cb){
		cb = function(){};
	}
	setTimeout(function(){
		(farr.shift())();
		cb();
		dojo.alg.delayThese(farr, cb, delay, onend);
	}, delay);
}

dojo.alg.for_each_call = dojo.alg.map; // burst compat
