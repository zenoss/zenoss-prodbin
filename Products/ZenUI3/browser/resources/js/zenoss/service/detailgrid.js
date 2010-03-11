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

Ext.onReady( function() {

    var zs = Ext.ns('Zenoss.Service.DetailGrid');

    /**********************************************************************
     *
     * Instances Functionality
     *
     */
    zs.initDetailPanel = function() {
        var config = {
            xtype: 'SimpleInstanceGridPanel',
            id: 'serviceInstancePanel',
            buttonTitle: _t('Services'),
            iconCls: 'services',
            directFn: Zenoss.remote.ServiceRouter.getInstances,
            tbar: {
                    items: [ { xtype: 'tbtext', text: _t('Instances') } ]
            }
        };

        Ext.getCmp('bottom_detail_panel').add(config);
    };
});