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
     Ext.ns('Zenoss.Action');
          
     Zenoss.Action = Ext.extend(Ext.Action, {
         constructor: function(config) {
             // if they set the permissions config property
             // and the logged in user does not have permission, hide this element
             if (config.permission){
                 config.hidden = Zenoss.Security.doesNotHavePermission(config.permission);
             }
             
             // call the parent's constructor
             Zenoss.Action.superclass.constructor.apply(this, arguments);   
         }             
     });

     Ext.reg('Action', Zenoss.Action);
}());
