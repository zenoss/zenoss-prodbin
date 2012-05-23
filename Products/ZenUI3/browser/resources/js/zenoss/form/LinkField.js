/*
 ###########################################################################
 #
 # This program is part of Zenoss Core, an open source monitoring platform.
 # Copyright (C) 2010, Zenoss Inc.
 #
 # This program is free software; you can redistribute it and/or modify it
 # under the terms of the GNU General Public License version 2 or (at your
 # option) any later version as published by the Free Software Foundation.
 #
 # For complete information please visit: http://www.zenoss.com/oss/
 #
 ###########################################################################
 */

/* package level */
(function() {

Ext.ns('Zenoss.form');

Ext.define("Zenoss.form.LinkField", {
    extend: "Ext.form.DisplayField",
    alias: ['widget.linkfield'],
    initComponent: function() {
        this.callParent(arguments);
        // make sure our value is established
        // before rendering
        this.setValue(this.value);
    },
    getValue: function() {
        return this.rawValue;
    },
    setValue: function(value) {
        var origValue = value;
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
        this.callParent([value]);
        this.rawValue = origValue;
    }
 });


})();
