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

Ext.ns('Zenoss.Service');

Ext.onReady( function() {

    /**********************************************************************
     *
     * Instances Functionality
     *
     */
    Zenoss.Service.initDetailPanel = function() {
        var config, instancePanel;

        config = {
            xtype: 'SimpleInstanceGridPanel',
            id: 'serviceInstancePanel',
            buttonTitle: _t('Services'),
            iconCls: 'services',
            directFn: Zenoss.remote.ServiceRouter.getInstances,
            tbar: {
                    items: [ { xtype: 'tbtext', text: _t('Instances') } ]
            }
        };

        //instancePanel = new Zenoss.SimpleInstanceGridPanel(config);
        instancePanel = config;
        Ext.getCmp('bottom_detail_panel').add(instancePanel);
    };
});