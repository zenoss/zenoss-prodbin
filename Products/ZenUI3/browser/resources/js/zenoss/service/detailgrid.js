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

Ext.onReady( function() {

    var zs = Ext.ns('Zenoss.Service.DetailGrid');

    /**********************************************************************
     *
     * Instances Functionality
     *
     */
    zs.initDetailPanel = function() {
        var config = {
            xtype: 'instancecardpanel',
            ref: 'detailCardPanel',
            region: 'south',
            split: true,
            router: Zenoss.remote.ServiceRouter,
            instancesTitle: 'Service Instances',
            zPropertyEditListeners: {
                frameload: function() {
                    var formPanel = Ext.getCmp('serviceForm');
                    if (formPanel.contextUid) {
                        formPanel.setContext(formPanel.contextUid);
                    }
                }
            }
        };

        Ext.getCmp('detail_panel').add(config);
    };
});
