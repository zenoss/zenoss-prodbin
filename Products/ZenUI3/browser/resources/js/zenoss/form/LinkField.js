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
     getValue: function() {
        return this.rawValue;
     },
     setValue: function(value) {
        this.rawValue = value;
        if (Ext.isEmpty(value)) {
            value = _t('None');
        } else {
            if (Ext.isArray(value)){
                var items = [];
                Ext.each(value, function(v){
                    items.push(Zenoss.render.link(v));
                });
                value = items.join('<br/>');
            } else {
                value = Zenoss.render.link(value);
            }
        }
        Zenoss.form.LinkField.superclass.setValue.call(this, value);
     }
 });
 Ext.reg('linkfield', Zenoss.form.LinkField);

})();
