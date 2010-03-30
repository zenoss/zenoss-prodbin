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

Zenoss.form.Password = Ext.extend(Ext.form.TextField, {
     constructor: function(config) {
         config.inputType = 'password';
         Zenoss.form.Password.superclass.constructor.apply(this, arguments);
     }
 });
 Ext.reg('password', Zenoss.form.Password);

})();
