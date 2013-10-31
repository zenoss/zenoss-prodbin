/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    Ext.ns('Daemons');
    Daemons.states = {
        UP: 'RUNNING',
        DOWN: 'STOPPED',
        STARTING: 'STARTING'
    };
    Ext.application({
        name: 'Daemons',
        appFolder: "/++resource++zenui/js/zenoss/daemons",
        controllers: ["DaemonsListController", "DetailsController"],
        launch: function() {
            var panel = Ext.create('Ext.Panel', {
                layout: 'border',
                items: [{
                    xtype: 'daemonslist',
                    region: 'center',
                    id: 'daemonslist',
                    store: Ext.create('Daemons.store.Daemons', {})
                }, {
                    xtype: 'daemonsdetails',
                    region: 'south',
                    height: "40%",
                    split: true,
                    resizable: true,
                    collapsible: true
                }]
            });
            Ext.getCmp('center_panel').add(panel);
            var store = Ext.getCmp('daemonslist').getStore();
            store.setRootNode({id: 'localhost', uuid: '12', status: '1', enabled: true, uid:'localhost', name: 'Localhost'});
            // this will trigger a router request to get the subservices of localhost
            store.getRootNode().expand();
        }
    });
})();
