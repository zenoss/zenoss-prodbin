/* Copyright (c) 2004-2005 The Dojo Foundation, Licensed under the Academic Free License version 2.1 or above */dojo.require("dojo.widget.Button");

function test_button_ctor(){
	var b1 = new dojo.widget.Button();

	jum.assertTrue("test10", typeof b1 == "object");
	jum.assertTrue("test20", b1.widgetType == "Button");
	jum.assertTrue("test21", typeof b1["attachProperty"] == "undefined");

	var db1 = new dojo.widget.DomButton();
	jum.assertTrue("test30", typeof db1 == "object");
	jum.assertTrue("test40", db1.widgetType == "Button");
	jum.assertTrue("test50", db1.attachProperty == "dojoAttachPoint");
	jum.assertTrue("test60", typeof db1.domNode != "undefined");

}
