/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.require("dojo.alg.*");
dojo.provide("dojo.event.Event");

dojo.event = new function(){

	var anonCtr = 0;
	this.anon = {};

	this.nameAnonFunc = function(anonFuncPtr, namespaceObj){
		var nso = (namespaceObj || this.anon);
		if((dj_global["djConfig"])&&(djConfig["slowAnonFuncLookups"] == true)){
			for(var x in nso){
				if(nso[x] === anonFuncPtr){
						dj_debug(x);
						return x;
				}
			}
		}
		var ret = "_"+anonCtr++;
		while(typeof nso[ret] != "undefined"){
			ret = "_"+anonCtr++;
		}
		nso[ret] = anonFuncPtr;
		return ret;
	}

	this.createFunctionPair = function(obj, cb) {
		var ret = [];
		if(typeof obj == "function"){
			ret[1] = dojo.event.nameAnonFunc(obj, dj_global);
			ret[0] = dj_global;
			return ret;
		}else if((typeof obj == "object")&&(typeof cb == "string")){
			return [obj, cb];
		}else if((typeof obj == "object")&&(typeof cb == "function")){
			ret[1] = dojo.event.nameAnonFunc(cb, obj);
			ret[0] = obj;
			return ret;
		}
		return null;
	}

	// FIXME: where should we put this method (not here!)?
	this.matchSignature = function(args, signatureArr){

		var end = Math.min(args.length, signatureArr.length);

		for(var x=0; x<end; x++){
			// FIXME: this is naive comparison, can we do better?
			if(compareTypes){
				if((typeof args[x]).toLowerCase() != (typeof signatureArr[x])){
					return false;
				}
			}else{
				if((typeof args[x]).toLowerCase() != signatureArr[x].toLowerCase()){
					return false;
				}
			}
		}

		return true;
	}

	// FIXME: where should we put this method (not here!)?
	this.matchSignatureSets = function(args){
		for(var x=1; x<arguments.length; x++){
			if(this.matchSignature(args, arguments[x])){
				return true;
			}
		}
		return false;
	}

	function interpolateArgs(args){
		var ao = {
			srcObj: dj_global,
			srcFunc: null,
			adviceObj: dj_global,
			adviceFunc: null,
			aroundObj: null,
			aroundFunc: null,
			adviceType: (args.length>2) ? args[0] : "after",
			precedence: "last",
			once: false,
			delay: null
		};

		switch(args.length){
			case 0: return;
			case 1: return;
			case 2:
				ao.srcFunc = args[0];
				ao.adviceFunc = args[1];
				break;
			case 3:
				if((typeof args[0] == "object")&&(typeof args[1] == "string")&&(typeof args[2] == "string")){
					ao.adviceType = "after";
					ao.srcObj = args[0];
					ao.srcFunc = args[1];
					ao.adviceFunc = args[2];
				}else if((typeof args[1] == "string")&&(typeof args[2] == "string")){
					ao.srcFunc = args[1];
					ao.adviceFunc = args[2];
				}else if((typeof args[0] == "object")&&(typeof args[1] == "string")&&(typeof args[2] == "function")){
					ao.adviceType = "after";
					ao.srcObj = args[0];
					ao.srcFunc = args[1];
					var tmpName  = dojo.event.nameAnonFunc(args[2], ao.adviceObj);
					ao.adviceObj[tmpName] = args[2];
					ao.adviceFunc = tmpName;
				}else if((typeof args[0] == "function")&&(typeof args[1] == "object")&&(typeof args[2] == "string")){
					ao.adviceType = "after";
					ao.srcObj = dj_global;
					var tmpName  = dojo.event.nameAnonFunc(args[0], ao.srcObj);
					ao.srcObj[tmpName] = args[0];
					ao.srcFunc = tmpName;
					ao.adviceObj = args[1];
					ao.adviceFunc = args[2];
				}
				break;
			case 4:
				if((typeof args[0] == "object")&&(typeof args[2] == "object")){
					// we can assume that we've got an old-style "connect" from
					// the sigslot school of event attachment. We therefore
					// assume after-advice.
					ao.adviceType = "after";
					ao.srcObj = args[0];
					ao.srcFunc = args[1];
					ao.adviceObj = args[2];
					ao.adviceFunc = args[3];
				}else if((typeof args[1]).toLowerCase() == "object"){
					ao.srcObj = args[1];
					ao.srcFunc = args[2];
					ao.adviceObj = dj_global;
					ao.adviceFunc = args[3];
				}else if((typeof args[2]).toLowerCase() == "object"){
					ao.srcObj = dj_global;
					ao.srcFunc = args[1];
					ao.adviceObj = args[2];
					ao.adviceFunc = args[3];
				}else{
					ao.srcObj = ao.adviceObj = ao.aroundObj = dj_global;
					ao.srcFunc = args[1];
					ao.adviceFunc = args[2];
					ao.aroundFunc = args[3];
				}
				break;
			case 6:
				ao.srcObj = args[1];
				ao.srcFunc = args[2];
				ao.adviceObj = args[3]
				ao.adviceFunc = args[4];
				ao.aroundFunc = args[5];
				ao.aroundObj = dj_global;
				break;
			default:
				ao.srcObj = args[1];
				ao.srcFunc = args[2];
				ao.adviceObj = args[3]
				ao.adviceFunc = args[4];
				ao.aroundObj = args[5];
				ao.aroundFunc = args[6];
				ao.once = args[7];
				ao.delay = args[8];
				break;
		}

		if((typeof ao.srcFunc).toLowerCase() != "string"){
			ao.srcFunc = dojo.alg.getNameInObj(ao.srcObj, ao.srcFunc);
		}

		if((typeof ao.adviceFunc).toLowerCase() != "string"){
			ao.adviceFunc = dojo.alg.getNameInObj(ao.adviceObj, ao.adviceFunc);
		}

		if((ao.aroundObj)&&((typeof ao.aroundFunc).toLowerCase() != "string")){
			ao.aroundFunc = dojo.alg.getNameInObj(ao.aroundObj, ao.aroundFunc);
		}

		if(!ao.srcObj){
			dj_throw("bad srcObj for srcFunc: "+ao.srcFunc);
		}
		if(!ao.adviceObj){
			dj_throw("bad srcObj for srcFunc: "+ao.adviceFunc);
		}
		return ao;
	}

	this.connect = function(){
		var ao = interpolateArgs(arguments);

		// FIXME: just doing a "getForMethod()" seems to be enough to put this into infinite recursion!!
		var mjp = dojo.event.MethodJoinPoint.getForMethod(ao.srcObj, ao.srcFunc);
		if(ao.adviceFunc){
			var mjp2 = dojo.event.MethodJoinPoint.getForMethod(ao.adviceObj, ao.adviceFunc);
		}

		mjp.kwAddAdvice(ao);

		return mjp;	// advanced users might want to fsck w/ the join point
					// manually
	}

	this.connectBefore = function() {
		var args = ["before"];
		for(var i = 0; i < arguments.length; i++) { args.push(arguments[i]); }
		return this.connect.apply(this, args);
	}

	this.connectAround = function() {
		var args = ["around"];
		for(var i = 0; i < arguments.length; i++) { args.push(arguments[i]); }
		return this.connect.apply(this, args);
	}

	this.kwConnectImpl_ = function(kwArgs, disconnect){
		var fn = (disconnect) ? "disconnect" : "connect";
		if(typeof kwArgs["srcFunc"] == "function"){
			kwArgs.srcObj = kwArgs["srcObj"]||dj_global;
			var tmpName  = dojo.event.nameAnonFunc(kwArgs.srcFunc, kwArgs.srcObj);
			kwArgs.srcFunc = tmpName;
		}
		if(typeof kwArgs["adviceFunc"] == "function"){
			kwArgs.adviceObj = kwArgs["adviceObj"]||dj_global;
			var tmpName  = dojo.event.nameAnonFunc(kwArgs.adviceFunc, kwArgs.adviceObj);
			kwArgs.adviceFunc = tmpName;
		}
		return dojo.event[fn](	(kwArgs["type"]||kwArgs["adviceType"]||"after"),
									kwArgs["srcObj"],
									kwArgs["srcFunc"],
									kwArgs["adviceObj"]||kwArgs["targetObj"],
									kwArgs["adviceFunc"]||kwArgs["targetFunc"],
									kwArgs["aroundObj"],
									kwArgs["aroundFunc"],
									kwArgs["once"],
									kwArgs["delay"]);
	}

	this.kwConnect = function(kwArgs){
		return this.kwConnectImpl_(kwArgs, false);

	}

	this.disconnect = function(){
		var ao = interpolateArgs(arguments);
		if(!ao.adviceFunc){ return; } // nothing to disconnect
		var mjp = dojo.event.MethodJoinPoint.getForMethod(ao.srcObj, ao.srcFunc);
		return mjp.removeAdvice(ao.adviceObj, ao.adviceFunc, ao.adviceType, ao.once);
	}

	this.kwDisconnect = function(kwArgs){
		return this.kwConnectImpl_(kwArgs, true);
	}
}

// exactly one of these is created whenever a method with a joint point is run,
// if there is at least one 'around' advice.
dojo.event.MethodInvocation = function(join_point, obj, args) {
	this.jp_ = join_point;
	this.object = obj;
	this.args = [];
	for(var x=0; x<args.length; x++){
		this.args[x] = args[x];
	}
	// the index of the 'around' that is currently being executed.
	this.around_index = -1;
}

dojo.event.MethodInvocation.prototype.proceed = function() {
	// dojo.hostenv.println("in MethodInvocation.proceed()");
	this.around_index++;
	if(this.around_index >= this.jp_.around.length){
		return this.jp_.object[this.jp_.methodname].apply(this.jp_.object, this.args);
		// return this.jp_.run_before_after(this.object, this.args);
	}else{
		var ti = this.jp_.around[this.around_index];
		var mobj = ti[0]||dj_global;
		var meth = ti[1];
		return mobj[meth].call(mobj, this);
	}
} 


dojo.event.MethodJoinPoint = function(obj, methname){
	this.object = obj||dj_global;
	this.methodname = methname;
	this.methodfunc = this.object[methname];
	this.before = [];
	this.after = [];
	this.around = [];
}

dojo.event.MethodJoinPoint.getForMethod = function(obj, methname) {
	// if(!(methname in obj)){
	if(!obj){ obj = dj_global; }
	if(!obj[methname]){
		// supply a do-nothing method implementation
		obj[methname] = function(){};
	}else if(typeof obj[methname] != "function"){
		return null; // FIXME: should we throw an exception here instead?
	}
	// we hide our joinpoint instance in obj[methname + '$joinpoint']
	var jpname = methname + "$joinpoint";
	var jpfuncname = methname + "$joinpoint$method";
	var joinpoint = obj[jpname];
	if(!joinpoint){
		var isNode = false;
		if(dojo.event["browser"]){
			if((obj["attachEvent"])||(obj["nodeType"])||(obj["addEventListener"])){
				isNode = true;
				dojo.event.browser.addClobberAttrs(jpname, jpfuncname, methname);
				dojo.event.browser.addClobberNode(obj);
			}
		}
		obj[jpfuncname] = obj[methname];
		// joinpoint = obj[jpname] = new dojo.event.MethodJoinPoint(obj, methname);
		joinpoint = obj[jpname] = new dojo.event.MethodJoinPoint(obj, jpfuncname);
		obj[methname] = function(){ 
			var args = [];

			if((isNode)&&(!arguments.length)&&(window.event)){
				args.push(dojo.event.browser.fixEvent(window.event));
			}else{
				for(var x=0; x<arguments.length; x++){
					if((x==0)&&(isNode)&&(typeof Event != "undefined")&&(arguments[x] instanceof Event)){
						args.push(dojo.event.browser.fixEvent(arguments[x]));
					}else{
						args.push(arguments[x]);
					}
				}
			}
			// return joinpoint.run.apply(joinpoint, arguments); 
			return joinpoint.run.apply(joinpoint, args); 
		}
	}
	// dojo.hostenv.println("returning joinpoint");
	return joinpoint;
}

dojo.event.MethodJoinPoint.prototype.unintercept = function() {
	this.object[this.methodname] = this.methodfunc;
}

dojo.event.MethodJoinPoint.prototype.run = function() {
	// dojo.hostenv.println("in run()");
	var obj = this.object||dj_global;
	var args = arguments;

	// optimization. We only compute once the array version of the arguments
	// pseudo-arr in order to prevent building it each time advice is unrolled.
	var aargs = [];
	// NOTE: alex: I think this is safe since we apply() these args anyway, so
	// primitive types will be copied at the call boundary anyway, and
	// references to objects would be mutable anyway.
	for(var x=0; x<args.length; x++){
		aargs[x] = args[x];
	}

	var unrollAdvice  = function(marr){ 
		// dojo.hostenv.println("in unrollAdvice()");
		var callObj = marr[0]||dj_global;
		var callFunc = marr[1];
		
		if (!callObj[callFunc]) {
			throw new Error ("function \"" + callFunc + "\" does not exist on \"" + callObj + "\"");
		}
		
		var aroundObj = marr[2]||dj_global;
		var aroundFunc = marr[3];
		var undef;
		var delay = parseInt(marr[4]);
		var hasDelay = ((!isNaN(delay))&&(marr[4]!==null)&&(typeof marr[4] != "undefined"));
		var to = {
			args: [],
			jp_: this,
			object: obj,
			proceed: function(){
				return callObj[callFunc].apply(callObj, to.args);
			}
		};

		/*
		// FIXME: how slow is this? Is there a better/faster way to get this
		// done?
		// FIXME: is it necessaray to make this copy every time that
		// unrollAdvice gets called? Would it be better/possible to handle it
		// in run() where we make args in the first place?
		for(var x=0; x<args.length; x++){
			to.args[x] = args[x];
		}
		*/
		to.args = aargs;

		if(aroundFunc){
			// NOTE: around advice can't delay since we might otherwise depend
			// on execution order!
			aroundObj[aroundFunc].call(aroundObj, to);
		}else{
			// var tmjp = dojo.event.MethodJoinPoint.getForMethod(obj, methname);
			if((hasDelay)&&((dojo.render.html)||(dojo.render.svg))){  // FIXME: the render checks are grotty!
				dj_global["setTimeout"](function(){
					callObj[callFunc].apply(callObj, args); 
				}, delay);
			}else{ // many environments can't support delay!
				callObj[callFunc].apply(callObj, args); 
			}
		}
	}

	if(this.before.length>0){
		dojo.alg.forEach(this.before, unrollAdvice, true);
	}

	var result;
	if(this.around.length>0){
		var mi = new dojo.event.MethodInvocation(this, obj, args);
		result = mi.proceed();
	}else if(this.methodfunc){
		// dojo.hostenv.println("calling: "+this.methodname)
		result = this.object[this.methodname].apply(this.object, args);
	}

	if(this.after.length>0){
		dojo.alg.forEach(this.after, unrollAdvice, true);
	}

	return (this.methodfunc) ? result : null;
}

dojo.event.MethodJoinPoint.prototype.getArr = function(kind){
	var arr = this.after;
	// FIXME: we should be able to do this through props or Array.in()
	if((typeof kind == "string")&&(kind.indexOf("before")!=-1)){
		arr = this.before;
	}else if(kind=="around"){
		arr = this.around;
	}
	return arr;
}

dojo.event.MethodJoinPoint.prototype.kwAddAdvice = function(args){
	this.addAdvice(	args["adviceObj"], args["adviceFunc"], 
					args["aroundObj"], args["aroundFunc"], 
					args["adviceType"], args["precedence"], 
					args["once"], args["delay"]);
}

dojo.event.MethodJoinPoint.prototype.addAdvice = function(	thisAdviceObj, thisAdvice, 
															thisAroundObj, thisAround, 
															advice_kind, precedence, 
															once, delay){
	var arr = this.getArr(advice_kind);
	if(!arr){
		dj_throw("bad this: " + this);
	}

	var ao = [thisAdviceObj, thisAdvice, thisAroundObj, thisAround, delay];
	
	if(once){
		if(this.hasAdvice(thisAdviceObj, thisAdvice, advice_kind, arr) >= 0){
			return;
		}
	}

	if(precedence == "first"){
		arr.unshift(ao);
	}else{
		arr.push(ao);
	}
}

dojo.event.MethodJoinPoint.prototype.hasAdvice = function(thisAdviceObj, thisAdvice, advice_kind, arr){
	if(!arr){ arr = this.getArr(advice_kind); }
	var ind = -1;
	for(var x=0; x<arr.length; x++){
		if((arr[x][0] == thisAdviceObj)&&(arr[x][1] == thisAdvice)){
			ind = x;
		}
	}
	return ind;
}

dojo.event.MethodJoinPoint.prototype.removeAdvice = function(thisAdviceObj, thisAdvice, advice_kind, once){
	var arr = this.getArr(advice_kind);
	var ind = this.hasAdvice(thisAdviceObj, thisAdvice, advice_kind, arr);
	if(ind == -1){
		return false;
	}
	while(ind != -1){
		arr.splice(ind, 1);
		if(once){ break; }
		ind = this.hasAdvice(thisAdviceObj, thisAdvice, advice_kind, arr);
	}
	return true;
}

// needed for package satisfaction
dojo.provide("dojo.event.Event");
