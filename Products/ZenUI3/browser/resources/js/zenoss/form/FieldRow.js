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

Ext.define("Zenoss.form.FieldRow", {

    alias: ['widget.fieldrow'],
    extend: "Ext.Container",
    constructor: function(config) {
         Ext.apply(config, {
             layout: 'hbox',
             align: 'top'
         });

         var items = config.items;
         config.items = [];

         Ext.each(items, function(item) {
             var cfg = {
                xtype: 'container',
                autoHeight: true,
                minWidth: 10,
                width: item.width,
                labelAlign: item.labelAlign || 'top',
                layout: 'anchor',
                items: [item]
             };
             if (!item.width) {
                 cfg.flex = item.flex || 1;
             }
             config.items.push(cfg);
         });

         Zenoss.form.FieldRow.superclass.constructor.call(this, config);

     }
 });

})();
