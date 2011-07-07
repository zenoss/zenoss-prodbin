/*
############################################################################
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

Ext.onReady(function () {

var MibBrowser,
    mib_browser,
    router = Zenoss.remote.MibRouter,
    node_type_store,
    node_type_maps,
    NodeGrid,
    node_grid,
    node_details,
    addtozenpack,
    treesm,
    mib_tree,
    footerBar,
    selModel,
    currentAddNodeTitle = _t('Add OID Mapping'),
    currentAddFn = router.addOidMapping,
    currentDeleteFn = router.deleteOidMapping,
    zs = Ext.ns('Zenoss.ui.Mibs');

node_type_maps = [{
    detailsTitle: _t('OID Mapping Overview'),
    addNodeTitle: _t('Add OID Mapping'),
    addFn: router.addOidMapping,
    deleteFn: router.deleteOidMapping,
    accessOrObjectsLabel: _t('Access:'),
    proxyFn: router.getOidMappings,
    readerCfg: {
        root: 'data',
        idProperty: 'uid',
        totalProperty: 'count',
        fields: [
            {name: 'uid'},
            {name: 'name'},
            {name: 'oid'},
            {name: 'nodetype'},
            {name: 'access'},
            {name: 'status'},
            {name: 'description'}
        ],
    }
},{
    detailsTitle: _t('Trap Overview'),
    addNodeTitle: _t('Add Trap'),
    addFn: router.addTrap,
    deleteFn: router.deleteTrap,
    accessOrObjectsLabel: _t('Objects:'),
    proxyFn: router.getTraps,
    readerCfg: {
        root: 'data',
        idProperty: 'uid',
        totalProperty: 'count',
        fields: [
            {name: 'uid'},
            {name: 'name'},
            {name: 'oid'},
            {name: 'nodetype'},
            {name: 'objects'},
            {name: 'status'},
            {name: 'description'}
        ],
    }
}];

node_type_store = [
    _t('OID Mappings'),
    _t('Traps')
];

NodeGrid = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    constructor: function(config) {
        Ext.applyIf(config || {}, {
            view: new Ext.ux.grid.livegrid.GridView({
                rowHeight: 22,
                nearLimit: 100,
                loadMask: {msg: _t('Loading. Please wait...'),
                           msgCls: 'x-mask-loading'},
                nonDisruptiveReset: Zenoss.FilterGridView.prototype.nonDisruptiveReset
            }),
            fbar: {
                border: false,
                frame: false,
                height: 10,
                items: {
                    xtype: 'livegridinfo',
                    text: '',
                    grid: this
                }
            }
        });
        NodeGrid.superclass.constructor.call(this, config);
    }
});

node_grid = new NodeGrid({
    id: 'node_grid',
    stripeRows: true,
    autoExpandColumn: 'name',
    store: new Ext.ux.grid.livegrid.Store({
        bufferSize: 256,
        proxy: new Ext.data.DirectProxy({
            directFn: router.getOidMappings
        }),
        reader: new Ext.ux.grid.livegrid.JsonReader(
            node_type_maps[0].readerCfg
        )
    }),
    cm: new Ext.grid.ColumnModel({
        defaults: {
            sortable: true
        },
        columns: [{
            width: 300,
            id: 'name',
            dataIndex: 'name',
            header: _t('Name')
        },{
            width: 180,
            id: 'oid',
            dataIndex: 'oid',
            header: _t('OID')
        },{
            width: 100,
            id: 'nodetype',
            dataIndex: 'nodetype',
            header: _t('Node Type')
        }]
    }),
    sm: new Ext.ux.grid.livegrid.RowSelectionModel({
        singleSelect: true,
        listeners: {
            rowselect: function(sm, ri, rec) {
                var node = Ext.getCmp('node_details');
                node.name.setValue(rec.data.name);
                node.oid.setValue(rec.data.oid);
                node.accessOrObjects.setValue(rec.data.access);
                if (rec.data.access == undefined) {
                    node.accessOrObjects.setValue(rec.data.objects);
                } else {
                    node.accessOrObjects.setValue(rec.data.access);
                }
                node.nodetype.setValue(rec.data.nodetype);
                node.status.setValue(rec.data.status);
                node.description.setValue(rec.data.description);
            }
        }
    })
});

node_details = new Ext.form.FormPanel({
    title: _t('OID Mapping Overview'),
    id: 'node_details',
    region: 'center',
    split: true,
    columnWidth: 1,
    bodyStyle: 'padding:5px 15px 0',
    defaultType: 'displayfield',
    autoScroll: true,
    items: [{
        fieldLabel: _t('Name'),
        ref: 'name'
    },{
        fieldLabel: _t('OID'),
        ref: 'oid'
    },{
        id: 'access_or_objects',
        fieldLabel: _t('Access'),
        ref: 'accessOrObjects'
    },{
        fieldLabel: _t('Node Type'),
        ref: 'nodetype'
    },{
        fieldLabel: _t('Status'),
        ref: 'status'
    },{
        fieldLabel: _t('Description'),
        ref: 'description'
    }]
});

MibBrowser = Ext.extend(Ext.Container, {
    currentUid: null,
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'border',
            items: [{
                xtype: 'panel',
                title: _t('MIB Overview'),
                region: 'north',
                height: 250,
                split: true,
                autoScroll: true,
                layout: 'border',
                items: [{
                    xtype: 'form',
                    region: 'west',
                    id: 'mib_form_left',
                    autoScroll: true,
                    width: 500,
                    bodyStyle: 'padding:5px 8px 0',
                    defaultType: 'displayfield',
                    items: [{
                        fieldLabel: _t('Name'),
                        ref: 'name'
                    },{
                        fieldLabel: _t('Contact'),
                        ref: 'contact'
                    }]
                },{
                    xtype: 'form',
                    region: 'center',
                    id: 'mib_form_right',
                    autoScroll: true,
                    bodyStyle: 'padding:5px 8px 0',
                    defaultType: 'displayfield',
                    items: [{
                        fieldLabel: _t('Language'),
                        ref: 'language'
                    },{
                        fieldLabel: _t('Description'),
                        ref: 'description'
                    }]
                }]
            },{
                xtype: 'panel',
                region: 'center',
                layout: 'border',
                split: true,
                tbar: {
                    cls: 'largetoolbar componenttbar',
                    border: false,
                    height: 32,
                    items: [{
                        xtype: 'tbtext',
                        html: _t('Display:')
                    }, {
                        xtype: 'combo',
                        store: node_type_store,
                        typeAhead: true,
                        allowBlank: false,
                        forceSelection: true,
                        triggerAction: 'all',
                        value: _t('OID Mappings'),
                        selectOnFocus: false,
                        listeners: {
                            select: function (combo, record, index) {
                                var node_type_map = node_type_maps[index],
                                    node_details = Ext.getCmp('node_details'),
                                    node_grid = Ext.getCmp('node_grid');
                                currentAddNodeTitle = node_type_map.addNodeTitle;
                                currentAddFn = node_type_map.addFn;
                                currentDeleteFn = node_type_map.deleteFn;
                                node_grid.getStore().removeAll(true);
                                node_grid.getStore().proxy = new Ext.data.DirectProxy({
                                    directFn: node_type_map.proxyFn
                                });
                                node_grid.getStore().reader = new Ext.ux.grid.livegrid.JsonReader(node_type_map.readerCfg);
                                node_grid.getStore().load({
                                    params: {uid: Zenoss.env.currentUid}
                                });
                                node_details.setTitle(node_type_map.detailsTitle);
                                node_details.name.setValue('');
                                node_details.oid.setValue('');
                                node_details.accessOrObjects.setValue('');
                                node_details.accessOrObjects.setValue('');
                                node_details.nodetype.setValue('');
                                node_details.status.setValue('');
                                node_details.description.setValue('');
                                Ext.getCmp('access_or_objects').label.update(node_type_map.accessOrObjectsLabel);
                            }
                        }
                    }, '-', {
                        xtype: 'button',
                        id: 'add_node_button',
                        iconCls: 'add',
                        handler: function() {
                            var dialog = new Zenoss.dialog.CloseDialog({
                                id: 'addNodeDialog',
                                width: 300,
                                title: currentAddNodeTitle,
                                items: [{
                                    xtype: 'form',
                                    buttonAlign: 'left',
                                    labelAlign: 'top',
                                    footerStyle: 'padding-left: 0',
                                    border: false,
                                    id: 'addNodeForm',
                                    items: [{
                                        fieldLabel: _t('ID'),
                                        xtype: 'textfield',
                                        allowBlank: false,
                                        name: 'id'
                                    },{
                                        fieldLabel: _t('OID'),
                                        xtype: 'textfield',
                                        allowBlank: false,
                                        name: 'oid'
                                    }],
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        text: _t('Submit'),
                                        handler: function() {
                                            var form = Ext.getCmp('addNodeForm').getForm();
                                            var addParams = {
                                                    uid: Zenoss.env.currentUid,
                                                    id: form.findField('id').getValue(),
                                                    oid: form.findField('oid').getValue()
                                                };
                                            currentAddFn(addParams, function() {
                                                node_grid.getStore().load({
                                                    params: {uid: Zenoss.env.currentUid}
                                                });
                                            });
                                        }
                                    }, Zenoss.dialog.CANCEL]
                                }]
                            });
                            dialog.show();
                        }
                    }, {
                        xtype: 'button',
                        id: 'delete_node_button',
                        iconCls: 'delete',
                        handler: function() {
                            var sm = node_grid.getSelectionModel(),
                                sel = sm.getSelected();
                            if (sel == undefined) {
                                return;
                            }
                            currentDeleteFn({uid: sel.id}, function() {
                                var node = Ext.getCmp('node_details');
                                node.name.setValue('');
                                node.oid.setValue('');
                                node.accessOrObjects.setValue('');
                                node.accessOrObjects.setValue('');
                                node.nodetype.setValue('');
                                node.status.setValue('');
                                node.description.setValue('');
                                node_grid.getStore().load({
                                    params: {uid: Zenoss.env.currentUid}
                                });
                            });
                        }
                    }]
                },
                items: [{
                    region: 'west',
                    layout: 'fit',
                    split: true,
                    width: 600,
                    items: [node_grid]} , node_details]
            }]
        });
        MibBrowser.superclass.constructor.call(this, config);
    },
    setContext: function(node) {
        var params = {
            uid: node.attributes.uid,
            useFieldSets: false
        };
        router.getInfo(params, this.populateForm);
    },
    populateForm: function(response) {
        Zenoss.env.currentUid = response.data.uid;
        var mib_form_left = Ext.getCmp('mib_form_left');
            mib_form_right = Ext.getCmp('mib_form_right');
        mib_form_left.name.setValue(response.data.name);
        mib_form_left.contact.setValue(response.data.contact);
        mib_form_right.language.setValue(response.data.language);
        mib_form_right.description.setValue(response.data.description);
        var params = {uid: Zenoss.env.currentUid};
        Ext.getCmp('node_grid').getStore().load({
            params: params
        });
    }
});

mib_browser = new MibBrowser({});

/**********************************************************************
 *
 * Mib Tree
 *
 */

function getSelectedMibTreeNode(){
    return Ext.getCmp('mibtree').getSelectionModel().getSelectedNode();
}

function reloadTree(selectedUid) {
    var tree = Ext.getCmp('mibtree');
    tree.getRootNode().reload(function(){
        tree.getRootNode().childNodes[0].expand();
        tree.selectByToken(selectedUid);
    });
}

function initializeTreeDrop(g) {
    var dz = new Ext.tree.TreeDropZone(g, {
        ddGroup: 'mibtreedd',
        appendOnly: true,
        onNodeDrop: function (target, dd, e, data) {
            if ((target.node.attributes.leaf) ||
                    (target.node == data.node.parentNode)) {
                try {
                    this.tree.selModel.suspendEvents(true);
                    data.node.unselect();
                    return false;
                } finally {
                    this.tree.selModel.resumeEvents();
                }
            }
            var tree = this.tree;
            router.moveNode({
                uids: [data.node.attributes.uid],
                target: target.node.attributes.uid
            }, function (response) {
                reloadTree(response.data.uid);
            });
            return true;
        }
    });
}

/*
 * TODO: determine if selecting a new folder with no items in it
 *       should leave a blank panel or not
 */
Zenoss.MibTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {
        constructor: function(config) {
            Ext.applyIf(config, {
                id: 'navTree',
                flex: 1,
                searchField: false,
                directFn: router.getOrganizerTree,
                router: router,
                selModel: treesm,
                relationshipIdentifier: 'mibs',
                selectRootOnLoad: true,
                enableDD: true,
                ddGroup: 'serviceDragDrop',
                ddAppendOnly: true,
                listeners: {
                    scope: this,
                    beforenodedrop: this.onBeforeNodeDrop,
                    expandnode: this.onExpandnode
                }
            });
            Zenoss.MibTreePanel.superclass.constructor.call(this, config);
        },
        onBeforeNodeDrop: function(dropEvent) {
            var sourceUids, targetUid, data, targetId;
            if (dropEvent.dropNode) {
                // moving a MibOrganizer into another MibOrganizer
                sourceUids = [dropEvent.dropNode.attributes.uid];
            } else {
                // moving a MIB from grid into a MibOrganizer
                data = Ext.pluck(dropEvent.data.selections, 'data');
                sourceUids = Ext.pluck(data, 'uid');
            }
            dropEvent.target.expand();
            targetUid = dropEvent.target.attributes.uid;
            targetId = dropEvent.target.attributes.id;
            router.MibRouter.moveMibs(
                {
                    sourceUids: sourceUids,
                    targetUid: targetUid
                }, function () {
                    this.moveMibsCallback(targetId);
                },
                this);
        },
        moveMibsCallback: function(targetId) {
            Ext.History.add('navTree' + Ext.History.DELIMITER + targetId);
            window.location.reload(); // instructed to by management :)
            //this.getRootNode().reload(this.rootNodeReloadCallback, this);
        },
        rootNodeReloadCallback: function() {
            this.getRootNode().select();
            this.getRootNode().expand(true);
        },
        onExpandnode: function(node) {
            var token, remainder;
            token = Ext.History.getToken();
            if (token) {
                remainder = token.split(Ext.History.DELIMITER)[1];
                this.selectByToken(remainder);
            }
        },

        selectByToken: function(token) {
            token = token.replace(/\//g, '.');
            var path = this.getNodePathById(token);
            this.selectPath(path);
        },
        initEvents: function() {
            Zenoss.MibTreePanel.superclass.initEvents.call(this);
            // don't add history token on click like HierarchyTreePanel does
            // this is handled in the selection model
            this.un('click', this.addHistoryToken, this);
        }

});

/**********************************************************************
 *
 * Action Buttons
 *
 */

treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function (sm, newnode) {
            var isRoot = false;

            if (newnode && newnode.attributes.leaf) {
                var uid = newnode.attributes.uid,
                    meta_type = newnode.attributes.meta_type;
                    mib_browser.setContext(newnode);
            }

            if (newnode) {
                // set the context for the new nodes
                Zenoss.env.PARENT_CONTEXT = newnode.attributes.uid;
                if (newnode.attributes.uid == '/zport/dmd/Mibs') {
                    isRoot = true;
                }
                Ext.getCmp('add-organizer-button').setDisabled(newnode.attributes.leaf);
                Ext.getCmp('edit-mib-action').setDisabled(!newnode.attributes.leaf);
                // do not allow them to delete the root node
                Ext.getCmp('delete-button').setDisabled(isRoot);

                // add to history
                Ext.History.add('mibtree' + Ext.History.DELIMITER + newnode.attributes.uid);
            }

        }
    }
});

mib_tree = new Zenoss.MibTreePanel({
    id: 'mibtree',
    cls: 'mib-tree',
    ddGroup: 'mibtreedd',
    searchField: true,
    enableDD: true,
    router: router,
    root: {
        id: 'Mibs',
        uid: '/zport/dmd/Mibs',
        text: _t('Mib Classes'),
        allowDrop: false
    },
    //selModel: treesm,
    listeners: {
        render: initializeTreeDrop,
        click: function (node, e) {
            if (node.attributes.leaf) {
                mib_browser.setContext(node);
            }
        }
    },
    dropConfig: { appendOnly: true }
});


Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border': false
    },
    items: [{
        id: 'master_panel',
        layout: 'fit',
        region: 'west',
        width: 300,
        split: true,
        items: [mib_tree]
    }, {
        layout: 'fit',
        region: 'center',
        items: [mib_browser]
    }]
});

/**********************************************************************
 *
 * Edit a Mib
 *
 */
function showEditMibDialog(response){
    var data = response.data, win,
        items = response.form.items[0].items;

    // show the edit form
    win = Ext.create({
        id: 'editMIBDialog',
        title: _t('Edit MIB'),
        xtype: 'basewindow',
        height: 360,
        width: 510,
        modal: true,
        plain: true,
        buttonAlight: 'left',
        items:{
            xtype:'form',
            border: false,
            ref: 'editForm',
            buttonAlign: 'left',
            monitorValid: true,
            items: items,
            listeners: {
                clientvalidation: function(form, valid) {
                    win.submitButton.setDisabled(!valid);
                }
            }
        },
        buttons:[{
            xtype: 'button',
            ref: '../submitButton',
            text: _t('Submit'),
            handler: function(button) {
                var form = button.refOwner.editForm.getForm(),
                dirtyOnly=true,
                opts = form.getFieldValues(dirtyOnly);
                opts.uid = data.uid;

                router.setInfo(opts, function(response) {
                    reloadTree(response.data.uid);
                    win.close();
                });
            }
        },{
            xtype: 'button',
            text: _t('Cancel'),
            handler: function () {
                win.close();
            }
        }]
    });

    win.show();
}
/**********************************************************************
 *
 * Footer Bar
 *
 */

function createAction(typeName, text) {
    return new Zenoss.Action({
        text: _t('Add ') + text + '...',
        iconCls: 'add',
        handler: function () {
            var addDialog = new Zenoss.FormDialog({
                title: _t('Create ') + text,
                modal: true,
                width: 310,
                formId: 'addForm',
                items: [{
                    xtype: 'idfield',
                    fieldLabel: _t('ID'),
                    name: 'name',
                    tabIndex: 0,
                    allowBlank: false,
                    listeners: {
                        valid: function() {
                            addDialog.submitButton.setDisabled(false);
                        }
                    }
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Submit'),
                    ref: '../submitButton',
                    disabled: true,
                    tabIndex: 1,
                    handler: function () {
                        var form, newName;
                        form = Ext.getCmp('addForm').getForm();
                        newName = form.findField('name').getValue();
                        mib_tree.addNode(typeName, newName);
                    }
                },
                    Zenoss.dialog.CANCEL
                ]
            });
            addDialog.show(this);
        }
    });
}

function createLocalMIBAddAction() {

    return new Zenoss.Action({
    text: _t('Add MIB from Desktop') + '...',
    id: 'addmib-item',
    permission: 'Manage DMD',
    handler: function(btn, e){
        var node = getSelectedMibTreeNode(),
        src = node.attributes.uid + '/uploadfile',
        win;
        win= new Zenoss.dialog.CloseDialog({
            id: 'fileuploadwindow',
            width: 300,
            title: _t('Add MIB from Desktop'),
            listeners: {
                close: function(panel) {
                    // show the message about the uploaded file
                    Zenoss.messenger.checkMessages();
                }
            },
            items: [{
                xtype: 'panel',
                buttonAlign: 'left',
                labelAlign: 'top',
                footerStyle: 'padding-left: 0',
                border: false,
                items: [{
                    xtype: 'panel',
                    width: 270,
                    height: 70,
                    layout: 'form',
                    border: false,
                    html: '<iframe frameborder="0" src="' +  src  + '"></iframe>'
                }]
            }]
        });
        win.show();
    }
});
}

function createDownloadMIBAddAction() {
    return new Zenoss.Action({
    text: _t('Download MIB') + '...',
    id: 'download-addmib-item',
    permission: 'Manage DMD',
    handler: function(btn, e){
        var win = new Zenoss.dialog.CloseDialog({
            width: 300,
            title: _t('Download MIB'),

            items: [{
                xtype: 'form',
                buttonAlign: 'left',
                monitorValid: true,
                labelAlign: 'top',
                footerStyle: 'padding-left: 0',
                border: false,
                items: [{
                    xtype: 'textfield',
                    name: 'package',
                    fieldLabel: _t('URL'),
                    id: "add-mib-url",
                    allowBlank: false
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Add'),
                    formBind: true,
                    handler: function(b) {
                        var form = b.ownerCt.ownerCt.getForm(),
                            opts = form.getFieldValues();
                        opts.organizer = Zenoss.env.PARENT_CONTEXT.replace('/zport/dmd/Mibs', '');
                        router.addMIB(opts,
                        function(response) {
                            if (response.success) {
                                new Zenoss.dialog.SimpleMessageDialog({
                                    message: _t('Add MIB job submitted'),
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        text: _t('OK')
                                    }, {
                                        xtype: 'button',
                                        text: _t('View Job Log'),
                                        handler: function() {
                                            window.location =
                                                '/zport/dmd/JobManager/jobs/' +
                                                response.jobId + '/viewlog';
                                        }
                                    }]
                                }).show();
                            }
                            else {
                                new Zenoss.dialog.SimpleMessageDialog({
                                    message: response.msg,
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        text: _t('OK')
                                    }]
                                }).show();
                            }
                        });
                    }
                }, Zenoss.dialog.CANCEL]
            }]
        });
        win.show();
    }
});
}

footerBar = Ext.getCmp('footer_bar');

footerBar.add({
    id: 'add-organizer-button',
    tooltip: _t('Add MIB organizer or MIB'),
    iconCls: 'add',
    menu: {
        width: 190, // mousing over longest menu item was changing width
        items: [
            createAction('organizer', _t('MIB Organizer')),
            createAction('MIB', _t('blank MIB')),
            createLocalMIBAddAction(),
            createDownloadMIBAddAction()
        ]
    }
});

/*
 * Delete a mib class
 */
function deleteNode() {
    var node = getSelectedMibTreeNode(),
        nodeType = "Mib";
    if (!node.attributes.leaf) {
        nodeType = "Organizer";
    }
    new Zenoss.dialog.SimpleMessageDialog({
        message: String.format(_t('Are you sure you want to delete the selected {0}?'), nodeType),
        title: _t('Delete Mib'),
        buttons: [{
            xtype: 'DialogButton',
            text: _t('Delete'),
            handler: function() {
                var params = {
                    uid: node.attributes.uid
                },
                parentUid = node.parentNode.attributes.uid,
                callback = function(response) {
                    // after deleting the child, select the parent
                    reloadTree(parentUid);
                };
                router.deleteNode(params, callback);
            }
        }, {
            xtype: 'DialogButton',
            text: _t('Cancel')
        }]
    }).show();

}

footerBar.add({
    id: 'delete-button',
    tooltip: _t('Delete an item'),
    iconCls: 'delete',
    handler: deleteNode
});

/*
 * add mib class to zenpack
 */
function addToZenPack(e) {
    if (!addtozenpack) {
        addtozenpack = new Zenoss.AddToZenPackWindow();
    }
    addtozenpack.setTarget(treesm.getSelectedNode().attributes.uid);
    addtozenpack.show();
}

footerBar.add([{
    xtype: 'button',
    iconCls: 'customize',
    id: 'mibs-configure-menu',
    disabled: false,
    menu: {
        items: [{
            xtype: 'menuitem',
            id: 'edit-mib-action',
            disabled: true,
            text: _t('Edit a Mib'),
            handler: function() {
                var node = getSelectedMibTreeNode(),
                    params;
                if (node){
                    params = {
                        uid: node.attributes.uid,
                        useFieldSets: false
                    };
                    router.getInfo(params, showEditMibDialog);
                }
            }
        },{
            xtype: 'menuitem',
            text: _t('Add to ZenPack'),
            handler: addToZenPack
        }]
    }
}]);

});
