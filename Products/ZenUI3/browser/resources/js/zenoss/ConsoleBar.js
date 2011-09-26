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
(function(){

Ext.ns('Zenoss');

Ext.define("Zenoss.ConsoleBar", {
    alias:['widget.consolebar'],
    extend:"Zenoss.LargeToolbar",
    constructor: function(config) {
        var title = config.title || 'Title';
        var panel = config.parentPanel;
        delete config.title;
        config = Ext.apply(config||{}, {
            cls: 'largetoolbar consolebar',
            height: 35,
            items: [{
                xtype: 'tbtext',
                text: title
            }].concat(config.leftItems||[]).concat([{
                xtype: 'tbfill'
            }]).concat(config.items||[]).concat(['-',{
                iconCls: 'collapse',
                ref: 'togglebutton',
                handler: function() {
                    panel.toggleCollapse();
                }
            }])
        });

        if (config.collapsed) {
            config.iconCls = 'expand';
        }
        this.callParent(arguments);


        // Set the icons properly
        // panel.on('collapse', function(p) {
        //     this.togglebutton.setIconCls('expand');
        // }, this);
        // panel.on('expand', function(p) {
        //     this.togglebutton.setIconCls('collapse');
        // }, this);
        // /*
        // * Have the toolbar remain visible when collapsed. This is accomplished
        // * by physically moving the element into the collapsedEl of the region
        // * on collapse, and moving it back before expanding.
        // */
        // panel.on('collapse', function(p) {
        //     var region = p.layout.container.ownerCt.layout[p.region],
        //         collapsedEl = region.getCollapsedEl(),
        //         tbEl = p.dockedItems.items[0].getEl(),
        //         tbHeight = tbEl.getComputedHeight();
        //     p.tbParent = tbEl.parent();
        //     collapsedEl.insertFirst(tbEl);
        //     collapsedEl.setHeight(tbHeight);
        //     p.layout.container.ownerCt.doLayout();
        // });
        // panel.on('beforeexpand', function(p) {
        //     var tb = p.dockedItems.items[0];
        //     p.addDocked(tb, 0);
        // });
        // /*
        // * Force the region to be unfloatable by detaching the listener. This
        // * avoids a few problems by disabling a feature we probably won't ever
        // * use.
        // */
        // panel.on('afterlayout', function(p) {
        //     var region = p.layout.owner.layout[p.region];

        //     if (region && region.floatable) {
        //         region.getCollapsedEl().un('click', region.collapseClick,
        //                                    region);
        //     }
        // });
    }
});




})(); // End local namespace
