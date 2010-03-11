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

/* package level */
(function() {

Ext.ns('Zenoss.form');

Zenoss.form.LinkField = Ext.extend(Ext.form.DisplayField, {
     constructor: function(config) {
         config.value = Zenoss.render.link(config.value);
         Zenoss.form.LinkField.superclass.constructor.apply(this, arguments);
     }
 });
 Ext.reg('linkfield', Zenoss.form.LinkField);

})();
