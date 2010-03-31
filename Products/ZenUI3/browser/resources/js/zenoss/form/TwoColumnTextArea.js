/*
 ###########################################################################
 #
 # This program is part of Zenoss Core, an open source monitoring platform.
 # Copyright (C) 2010, Zenoss Inc.
 #
 # This program is free software; you can redistribute it and/or modify it
 # under the terms of the GNU General Public License version 2 as published by
 # the Free Software Foundation.
 #
 # For complete information please visit: http://www.zenoss.com/oss/
 #
 ###########################################################################
 */


(function() {

Ext.ns('Zenoss.form');
/**
 * This is a special case of a text area. It is designed to take up the entire column
 * on a two column layout.
 **/
Zenoss.form.TwoColumnTextArea = Ext.extend(Ext.form.TextArea, {
     constructor: function(config) {
         config.width = 500;
         config.height = 120;
         Zenoss.form.TwoColumnTextArea.superclass.constructor.apply(this, arguments);
     }
 });
 Ext.reg('twocolumntextarea', Zenoss.form.TwoColumnTextArea);
})();
