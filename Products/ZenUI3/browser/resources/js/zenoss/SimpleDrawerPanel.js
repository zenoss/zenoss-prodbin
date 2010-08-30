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
    /**
     * A simple drawer is a layout that is designed to be used
     * in the detail panel in the master detail layout.
     * It has a center region and a collapsible east region.
     * Two config items are required.
     * 1. centerItems: This is what will be in the center "main" panel.
     * 2. drawerItems: This is what will be in the slide out drawer.
     **/
    Zenoss.SimpleDrawerPanel = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            if (!config.centerItems){
                throw "SimpleDrawerPanel did not receive a centerItems config option";
            }
            if (!config.drawerItems) {
                throw "SimpleDrawerPanel did not receive a drawerItems config option";
            }            
            Ext.applyIf(config, {
                split: true,
                layout: 'border',
                items: [{
                    region: 'center',
                    layout: 'fit',
                    autoScroll: true,
                    items: config.centerItems
                }, {
                    width: 650,
                    height: 800,
                    ref: 'drawerPanel',
                    region: 'east',
                    align: 'right',
                    animCollapse: false,
                    collapsed: true,
                    layout: 'border',
                    border: false,
                    items:[ {
                        id: 'evdetail_hd',
                        region: 'north',
                        height: 50,
                        cls: 'evdetail_hd',
                        defaults: {border: false},
                        items: [{
                            region: 'west',
                            width: 77,
                            layout: 'hbox',
                            defaults: {border: false},
                            items: [{
                                id: 'severity-icon',
                                cls: 'severity-icon'
                            },{
                                id: 'evdetail-sep',
                                cls: 'evdetail-sep'
                            }]
                        },{
                            region: 'center',
                            id: 'evdetail-summary',
                            html: ''
                        },{
                            region: 'east',
                            id: 'evdetail-tools',
                            layout: 'hbox',
                            width: 57,
                            defaults: {border: false},
                            items: [{
                                id: 'evdetail-popout',
                                cls: 'evdetail-popout'
                            },{
                                id: 'evdetail_tool_close',
                                cls: 'evdetail_close'
                            }]
                        }]
                    },{
                        id: 'evdetail_bd',
                        region: 'center',
                        defaults: {
                            frame: false,
                            border: false,
                            autoScroll: true
                        },
                        autoScroll: true,
                        cls: 'evdetail_bd',
                        layout: 'hbox',
                        align: 'right',
                        items: config.drawerItems

                    }]
                }]
            });
            Zenoss.SimpleDrawerPanel.superclass.constructor.apply(this, arguments);
        },
        isCollapsed: function() {
            return this.drawerPanel.collapsed;
        },
        expandDrawer: function(){
            this.drawerPanel.expand();
        },
        collapseDrawer: function(){
            this.drawerPanel.collapse();
        }
    });
    Ext.reg('simpledrawerpanel', Zenoss.SimpleDrawerPanel);
}());