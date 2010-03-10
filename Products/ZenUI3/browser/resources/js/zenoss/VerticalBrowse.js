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

(function(){

Ext.ns('Zenoss');

Zenoss.VerticalBrowsePanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            layout: 'hbox',
            border: false,
            layoutConfig: {
                align: 'stretch'
            },
            defaults: {
                flex: 1,
                autoScroll: true
            }
        });
        Zenoss.VerticalBrowsePanel.superclass.constructor.call(this, config);
    }
});

})();
