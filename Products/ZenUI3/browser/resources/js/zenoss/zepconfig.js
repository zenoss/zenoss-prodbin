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

Ext.onReady(function(){

    Ext.ns('Zenoss.settings');
    var router = Zenoss.remote.EventsRouter;

    function buildPropertyGrid(response) {
        var propsGrid,
            data;
        data = response.data;
        propsGrid = new Zenoss.form.SettingsGrid({
            renderTo: 'propList',
            width: 500,
            saveFn: router.setConfigValues
        }, data);
    }

    function loadProperties() {
        router.getConfig({}, buildPropertyGrid);
    }

    loadProperties();
    
    var clearHeartbeatPanel = new Ext.Panel({
        renderTo: 'clearHeartbeat',
        layout: 'hbox',
        layoutConfig: {
            pack: 'center',
            align: 'middle'
        },
        bodyStyle: 'background-color: #FAFAFA; border-style: none solid none solid;',
        width: 500,
        padding: 10,
        items: [
            {
                xtype: 'button',
                text: _t('Clear'),
                handler: function() {
                    var confirmDialog = new Zenoss.MessageDialog({
                        title: _t('Clear Heartbeats'),
                        message: _t('Clear all heartbeat events? This cannot be undone.'),
                        okHandler: function() {
                            router.clear_heartbeats({}, function(response) {
                                if (response.success) {
                                    Zenoss.message.success(_t('Heartbeat events succesfully deleted.'));
                                }
                                else {
                                    Zenoss.message.error(_t('Error deleting heartbeat events.'));
                                }
                            });
                        }
                    });
                    confirmDialog.show();
                }
            }, {
                xtype: 'spacer',
                width: 10
            }, {
                html: _t('Clear all heartbeat events'),
                bodyStyle: 'font-size:110%; font-color: #5A5A5A;'
            }
        ]
    });

});