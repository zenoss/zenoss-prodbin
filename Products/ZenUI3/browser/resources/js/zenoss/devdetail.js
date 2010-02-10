/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

Ext.onReady(function(){

var REMOTE = Zenoss.remote.DeviceRouter,
    UID = Zenoss.env.device_uid;

var comptree = {
    xtype: 'HierarchyTreePanel',
    id: 'components'
};

var overview = {
    layout: 'border',
    border: false,
    defaults: {border:false},
    items: [{
        id: 'detail_panel',
        region: 'center'
    },{
        region: 'south',
        id: 'bottom_detail_panel',
        split: true,
        layout: 'fit',
        height: 250,
        collapseMode: 'mini',
        collapsed: true
    }]
};

Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border':false
    },
    tbar: {
        xtype: 'devdetailbar',
        listeners: {
            render: function(me) {
                me.setContext(UID);
            }
        }
    },
    items: [{
        region: 'west',
        split: 'true',
        id: 'master_panel',
        width: 275
    },{
        xtype: 'contextcardpanel',
        split: true,
        activeItem: 0,
        region: 'center',
        items: [overview]
    }]
});

});
