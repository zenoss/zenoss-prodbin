/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.provide("dojo.io.RhinoIO");

dojo.io.SyncHTTPRequest = function(){
	dojo.io.SyncRequest.call(this);

	this.send = function(URI){
	}
}

dj_inherits(dojo.io.SyncHTTPRequest, dojo.io.SyncRequest);

