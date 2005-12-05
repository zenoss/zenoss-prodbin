/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.require("dojo.alg.*");

var testArr = ["foo", "bar", "baz", ["foo", "bar"]];

function test_alg_find(){
	// jum.debug(testArr);
	jum.assertEquals("test10", 0, dojo.alg.find(testArr, "foo"));
}

function test_alg_inArr(){
	// jum.debug(testArr);
	jum.assertTrue("test20", dojo.alg.inArr(testArr, "foo"))
	jum.assertFalse("test30", dojo.alg.inArr(testArr, "foobar"))
}

function test_alg_has(){
	var tclass = function(){
		this.foo = false;
		this.bar = true;
	}
	tclass.prototype.xyzzy = true;
	var tobj = new tclass();
	jum.assertTrue("test40", dojo.alg.has(tobj, "foo"));
	jum.assertTrue("test50", dojo.alg.has(tobj, "bar"));
	jum.assertTrue("test60", dojo.alg.has(tobj, "xyzzy"));
	jum.assertFalse("test70", dojo.alg.has(tobj, "baz"));
}

function test_alg_getNameInObj(){
	var tclass = function(){
		this.foo = false;
		this.bar = true;
		this.baz = "baz";
	}
	var tobj = new tclass();

	jum.assertEquals("test80", "foo", dojo.alg.getNameInObj(tobj, tobj.foo));
	jum.assertEquals("test80", "bar", dojo.alg.getNameInObj(tobj, tobj.bar));
	jum.assertEquals("test90", "baz", dojo.alg.getNameInObj(tobj, tobj.baz));
}
