/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.require("dojo.logging.Logger");

function test_logging_log(){
	/*
	for(var x in dojo.logging){
		print(x);
	}
	print(dojo.logging.log.debug);
	*/
	// dojo.logging.log.debug("WTF?");
	dojo.log.debug("dojo.log.debug() working correctly");
	dojo.log.info("dojo.log.info() working correctly");
	dojo.log.warn("dojo.log.warn() working correctly");
	dojo.log.err("dojo.log.err() working correctly");
	dojo.log.crit("dojo.log.crit() working correctly");
	try{
		dj_throw("a synthetic exception");
	}catch(e){
		// catch and squelch
		dojo.log.exception("dojo.log.exception() working correctly", e, true);
	}
}
