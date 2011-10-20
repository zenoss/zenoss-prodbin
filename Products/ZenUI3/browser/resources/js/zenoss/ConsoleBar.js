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
        var me = this;
        var title = config.title || 'Title';
        var panel = config.parentPanel;

        delete config.title;
        config = Ext.apply(config||{}, {
            cls: 'largetoolbar consolebar',
            height: 35,
            collapseTitle: 'Instances',
            items: [{
                xtype: 'tbtext',
                text: title
            }].concat(config.leftItems||[]).concat([{
                xtype: 'tbfill'
            }]).concat(config.items||[]).concat(['-',{
                iconCls: 'collapse',
                ref: 'togglebutton',
                handler: function() {
                    me.toggleDockedItemPosition();
                }
            }])
        });

        if (config.collapsed) {
            config.iconCls = 'expand';
        }
        this.callParent(arguments);



        // Set the icons properly
        panel.on('collapse', function(p) {
            this.togglebutton.setIconCls('expand');
        }, this);
        panel.on('expand', function(p) {
            this.togglebutton.setIconCls('collapse');
        }, this);
        // when the page first loads the panel is expanded
        // we then collapse the panel so the toolbar is in the correct spot
        this.parentPanel.on('expand', function(){
            this.getTopToolbar().togglebutton.handler();
        }, this.parentPanel, {single: true});

    },
    /**
     * Because in our UI we want the console bar visible when the
     * panel is collapse we add ourselves to the "dockedItems" when
     * our expand and collapse button is pressed.
     **/
    toggleDockedItemPosition: function() {
        this.up('panel').removeDocked(this, false);
        if (this.parentPanel.collapsed) {
            this.moveToSouthRegion();
        } else {
            this.moveToCenterRegion();
        }
    },
    moveToSouthRegion: function() {
        this.dock = "top";
        Ext.getCmp(this.centerPanel).layout.regions.south.addDocked(this);
        this.parentPanel.setHeight(this.oldHeight);
        this.parentPanel.expand();
    },
    moveToCenterRegion: function() {
        this.dock = "bottom";

        Ext.getCmp(this.centerPanel).layout.regions.center.addDocked(this, 0);
        // remember the old height for when we expand
        this.oldHeight = Math.max(this.parentPanel.getEl().getComputedHeight(), this.parentPanel.initialConfig.height);
        this.parentPanel.collapse();
        // set height to 0 so the header bar disappears
        this.parentPanel.setHeight(0);
    }

});

})(); // End local namespace
