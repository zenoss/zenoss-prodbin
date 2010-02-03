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

Ext.ns('Zenoss.devices');

var REMOTE = Zenoss.remote.DeviceRouter;

var treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function(sm, newnode, oldnode){
            var uid = newnode.attributes.uid;
            Zenoss.util.setContext(uid, 'detail_panel', 'organizer_events', 
                                   'commands-menu');
            Zenoss.devices.deleteDevices.disable();
            Ext.getCmp('commands-menu').disable();
            Ext.getCmp('actions-menu').disable();
            var card = Ext.getCmp('master_panel').getComponent(0),
                type = Zenoss.types.type(uid);
            if (type && !Ext.isEmpty(Zenoss.nav[type])) {
                card.navButton.show();
                Ext.getCmp('master_panel').getComponent(1).navButton.show();
            } else {
                card.navButton.hide();
            }
        }
    }
});

function gridOptions() {
    var grid = Ext.getCmp('device_grid'),
    sm = grid.getSelectionModel(),
    rows = sm.getSelections(),
    ranges = sm.getPendingSelections(true),
    pluck = Ext.pluck,
    uids = pluck(pluck(rows, 'data'), 'uid'),
    opts = Ext.apply(grid.view.getFilterParams(true), {
        uids: uids,
        ranges: ranges
    });
    return opts;
}

Ext.apply(Zenoss.devices, {
    lockDevices: new Ext.Action({
        text: _t('Lock Devices') + '...',
        iconCls: 'lock',
        handler: function() {
            var win = new Zenoss.FormDialog({
                title: _t('Lock Devices'),
                modal: true,
                width: 220,
                height: 200,
                items: [{
                    xtype: 'checkboxgroup',
                    id: 'lockingchecks',
                    columns: 1,
                    style: 'margin: 0 auto',
                    items: [{
                        name: 'updates',
                        boxLabel: _t('Lock from updates'),
                        checked: true
                    },{
                        name: 'deletion',
                        boxLabel: _t('Lock from deletion')
                    }]
                }],
                buttons: [{
                    text: _t('Lock'),
                    handler: function() {

                    }
                }, Zenoss.dialog.CANCEL
                ]
            });
            win.show();
        }
    }),
    resetIP: new Ext.Action({
        text: _t('Reset IP'),
        iconCls: 'set'
    }),
    resetCommunity: new Ext.Action({
        text: _t('Reset Community'),
        iconCls: 'set'
    }),
    setProdState: new Ext.Action({
        text: _t('Set Production State')+'...',
        iconCls: 'set'
    }),
    setPriority: new Ext.Action({
        text: _t('Set Priority')+'...',
        iconCls: 'set'
    }),
    setCollector: new Ext.Action({
        text: _t('Set Collector') + '...',
        iconCls: 'set'
    }),
    deleteDevices: new Ext.Action({
        //text: _t('Delete Devices'),
        iconCls: 'delete',
        handler: function(btn, e) {
            var grid = Ext.getCmp('device_grid'),
                selnode = treesm.getSelectedNode(),
                isclass = Zenoss.types.type(selnode.attributes.uid)=='DeviceClass',
                grpText = selnode.attributes.text.text;
            var win = new Zenoss.FormDialog({
                title: _t('Remove Devices'),
                modal: true,
                width: 300,
                height: 220,
                items: [{
                    xtype: 'panel',
                    bodyStyle: 'font-weight: bold; text-align:center',
                    html: _t('Are you sure you want to remove these devices? '+
                             'There is no undo.')
                },{
                    xtype: 'radiogroup',
                    id: 'removetype',
                    style: 'margin: 0 auto',
                    columns: 1,
                    items: [{
                        value: 'remove',
                        name: 'removetype',
                        boxLabel: _t('Just remove from ') + grpText,
                        disabled: isclass,
                        checked: !isclass
                    },{
                        value: 'delete',
                        name: 'removetype',
                        boxLabel: _t('Delete completely'),
                        checked: isclass
                    }]
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Remove'),
                    handler: function(b) {
                        grid.view.showLoadMask(true);
                        var opts = Ext.apply(gridOptions(), {
                            action: Ext.getCmp('removetype').getValue().value
                        });
                        Zenoss.remote.DeviceRouter.removeDevices(opts, 
                             function(response) {
                                 var devtree = Ext.getCmp('devices'),
                                 loctree = Ext.getCmp('locs'),
                                 grptree = Ext.getCmp('groups');
                                 grid.view.nonDisruptiveReset();
                                 devtree.update(response.devtree);
                                 loctree.update(response.loctree);
                                 grptree.update(response.grptree);
                                 grid.view.showLoadMask(false);
                             }
                        );
                    }
                },
                Zenoss.dialog.CANCEL
                ],
                buttonAlign: 'center'
            });
            win.show();
        }
    })
});

function commandMenuItemHandler(item) {
    var command = item.text,
        grid = Ext.getCmp('device_grid'),
        sm = grid.getSelectionModel(),
        ranges = sm.getPendingSelections(true),
        selections = sm.getSelections(),
        devids = Ext.pluck(Ext.pluck(selections, 'data'), 'uid');
    function showWindow() {
        var win = new Zenoss.CommandWindow({
            uids: devids,
            target: treesm.getSelectedNode().attributes.uid,
            command: command
        });
        win.show();
    }
    if (!Ext.isEmpty(ranges)) {
        var opts = Ext.apply(grid.view.getFilterParams(true),{ranges:ranges});
        REMOTE.loadRanges(opts, function(data){
            devids.concat(data);
            showWindow();
        });
    } else {
        showWindow();
    }
}


function updateNavTextWithCount(node) {
    var sel = treesm.getSelectedNode();
    if (sel) {
        var count = sel.attributes.text.count;
        node.setText('<b'+'>Devices ('+count+')<'+'/b>');
    }
}

Zenoss.nav.register({
    DeviceLocation: [{
        id: 'Devices',
        text: 'Devices',
        action: function(node, target) {
            target.layout.setActiveItem('device_grid');
        },
        listeners: {
            render: updateNavTextWithCount
        }
    }, {
        id: 'Map',
        text: 'Map',
        action: function(node, target) {
            target.layout.setActiveItem('map');
        }
    }],
    DeviceClass: [{
        id: 'Devices',
        text: 'Devices',
        action: function(node, target) {
            target.layout.setActiveItem('device_grid');
        },
        listeners: {
            render: updateNavTextWithCount
        }
    },{
        id: 'zprops',
        text: 'Configuration Properties',
        action: function(node, target){
            target.layout.setActiveItem('zprops');
        }
    },{
        id: 'templates',
        text: 'Monitoring Templates',
        action: function(node, target){
            target.layout.setActiveItem('templates');
        }

    }]

});

function initializeTreeDrop(g) {
    var dz = new Ext.tree.TreeDropZone(g, {
        ddGroup: 'devicegriddd',
        getTargetFromEvent: function(e) {
            return e.getTarget('.x-tree-node-el');
        },
        onNodeOver : function(target, dd, e, data){ 
            // Return the class that makes the check mark
            return Ext.dd.DropZone.prototype.dropAllowed;
        },
        onNodeDrop: function(target, dd, e, data) {
            var nodeid = target.getAttribute('ext:tree-node-id'),
                grid = Ext.getCmp('device_grid'),
                tree = this.tree,
                targetnode = tree.getNodeById(nodeid),
                targetuid = targetnode.attributes.uid,
                ranges = grid.getSelectionModel().getPendingSelections(true),
                devids;

            devids = Ext.pluck(Ext.pluck(data.selections, 'data'), 'uid');

            grid.view.showLoadMask(true);

            var opts = Ext.apply(grid.view.getFilterParams(true), {
                uids: devids,
                ranges: ranges,
                target: targetuid
            });

            REMOTE.moveDevices(opts, function(data){
                if(data.success) {
                    grid.view.nonDisruptiveReset();
                    tree.update(data.tree);
                } else {
                    grid.view.showLoadMask(false);
                }
            }, this);
        }
    });
}

var devtree = {
    xtype: 'HierarchyTreePanel',
    id: 'devices',
    searchField: true,
    directFn: REMOTE.getTree,
    root: {
        id: 'Devices',
        uid: '/zport/dmd/Devices',
        text: 'Device Classes'
    },
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

var grouptree = {
    xtype: 'HierarchyTreePanel',
    id: 'groups',
    searchField: false,
    directFn: REMOTE.getTree,
    root: {
        id: 'Groups',
        uid: '/zport/dmd/Groups'
    },
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};

var loctree = {
    xtype: 'HierarchyTreePanel',
    id: 'locs',
    searchField: false,
    directFn: REMOTE.getTree,
    root: {
        id: 'Locations',
        uid: '/zport/dmd/Locations'
    },
    selectRootOnLoad: false,
    selModel: treesm,
    listeners: { render: initializeTreeDrop }
};


Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border': false
    },
    items: [{
        xtype: 'horizontalslide',
        id: 'master_panel',
        text: _t('IT Infrastructure'),
        region: 'west',
        split: true,
        width: 275,
        items: [{
            text: _t('IT Infrastructure'),
            buttonText: _t('Details'),
            items: [devtree, grouptree, loctree],
            autoScroll: true
        },{
            xtype: 'subselection',
            text: _t('Details'),
            target: 'detail_panel',
            buttonText: _t('See All'),
            html: 'some other stuff'
        }],
        listeners: {
            beforecardchange: function(me, card, index, from, fromidx) {
                if (index==1) {
                    var node = treesm.getSelectedNode().attributes;
                    card.setHeaderText(node.text.text);
                } else if (index===0) {
                    Ext.getCmp('subselecttreepanel').getSelectionModel().getSelectedNode().unselect();
                    Ext.getCmp('detail_panel').layout.setActiveItem(0);
                }
            },
            cardchange: function(me, card, index, from , fromidx) {
                if (index==1) {
                    var node = treesm.getSelectedNode().attributes;
                    card.card.setContext(node.uid);
                    // Now, we'll manually preload the iframes on the other
                    // cards. This is extremely temporary.
                    var others = Ext.getCmp('detail_panel').items.items.slice(1);
                    switch (Zenoss.types.type(node.uid)) {
                        case 'DeviceLocation':
                            others[2].setContext(node.uid);
                            break;
                        case 'DeviceClass':
                            var cards = others.slice(0,2);
                            Ext.each(cards, function(c){c.setContext(node.uid);});
                            break;
                    }
                }
            }
        }
    },{
        xtype: 'contextcardpanel',
        id: 'detail_panel',
        region: 'center',
        activeItem: 0,
        split: true,
        items: [{
            xtype: 'DeviceGridPanel',
            ddGroup: 'devicegriddd',
            id: 'device_grid', 
            enableDrag: true,
            sm: new Zenoss.ExtraHooksSelectionModel({
                listeners: {
                    selectionchange: function(sm) {
                        Zenoss.devices.deleteDevices.setDisabled(
                            !sm.getSelected()
                        );
                        var mnu = Ext.getCmp('commands-menu');
                        mnu.setDisabled(!sm.getSelected());
                        var amnu = Ext.getCmp('actions-menu');
                        amnu.setDisabled(!sm.getSelected());
                    }
                }
            }),
            tbar: {
                xtype: 'largetoolbar',
                items: [{
                    xtype: 'eventrainbow',
                    id: 'organizer_events'
                }, '-', {
                    id: 'adddevice-button',
                    iconCls: 'adddevice',
                    handler: null
                }, Zenoss.devices.deleteDevices,
                    /*
                    id: 'add-button',
                    iconCls: 'add'
                },{
                    id: 'set-button',
                    iconCls: 'set'
                }, '-', {
                    id: 'import-button',
                    iconCls: 'import'
                },{
                    id: 'export-button',
                    iconCls: 'export'
                },{
                    id: 'configure-button',
                    iconCls: 'configure'
                    */
                '->', 
                {
                    id: 'actions-menu',
                    text: _t('Actions'),
                    menu: {
                        items: [
                            Zenoss.devices.lockDevices,
                            Zenoss.devices.resetIP,
                            Zenoss.devices.resetCommunity,
                            Zenoss.devices.setProdState,
                            Zenoss.devices.setPriority,
                            Zenoss.devices.setCollector
                        ]
                    }
                },{
                    id: 'commands-menu',
                    text: _t('Commands'),
                    setContext: function(uid) {
                        var me = Ext.getCmp('commands-menu'),
                            menu = me.menu;
                        REMOTE.getUserCommands({uid:uid}, function(data){
                            menu.removeAll();
                            Ext.each(data, function(d){
                                menu.add({
                                    text:d.id, 
                                    tooltip:d.description,
                                    handler: commandMenuItemHandler
                                });
                            });
                        });
                    },
                    menu: {}
                }]
            }
        }, {
            xtype: 'backcompat',
            viewName: 'zPropertyEdit',
            id: 'zprops'
        }, {
            xtype: 'backcompat',
            viewName: 'perfConfig',
            id: 'templates'
        },{
            xtype: 'contextiframe',
            viewName: 'simpleLocationGeoMap',
            id: 'map'
        }]
    }]
});



});
