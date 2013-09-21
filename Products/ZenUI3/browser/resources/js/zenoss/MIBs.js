/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


Ext.onReady(function () {

var MibBrowser,
    mib_browser,
    router = Zenoss.remote.MibRouter,
    node_type_store,
    node_type_maps,
    oid_grid,
    trap_grid,
    node_details,
    treesm,
    mib_tree,
    footerBar,
    currentAddNodeTitle = _t('Add OID Mapping'),
    currentAddFn = router.addOidMapping,
    currentDeleteFn = router.deleteOidMapping,
    zs = Ext.ns('Zenoss.ui.Mibs');

node_type_maps = [{
    detailsTitle: _t('OID Mapping Overview'),
    addNodeTitle: _t('Add OID Mapping'),
    addFn: router.addOidMapping,
    deleteFn: router.deleteOidMapping,
    accessOrObjectsLabel: _t('Access:')
},{
    detailsTitle: _t('Trap Overview'),
    addNodeTitle: _t('Add Trap'),
    addFn: router.addTrap,
    deleteFn: router.deleteTrap,
    accessOrObjectsLabel: _t('Objects:')
}];

node_type_store = [
    _t('OID Mappings'),
    _t('Traps')
];


/**
 * @class Zenoss.mibs.TrapModel
 * @extends Ext.data.Model
 * Field definitions for the traps
 **/
Ext.define('Zenoss.mibs.TrapModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
         {name: 'uid'},
         {name: 'name'},
         {name: 'oid'},
         {name: 'nodetype'},
         {name: 'objects'},
         {name: 'status'},
         {name: 'description'}
    ]
});

/**
 * @class Zenoss.mibs.TrapStore
 * @extend Zenoss.DirectStore
 * Direct store for loading trap
 */
Ext.define("Zenoss.mibs.TrapStore", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.mibs.TrapModel',
            pageSize: 50,
            initialSortColumn: "name",
            totalProperty: 'count',
            directFn: router.getTraps,
            root: 'data'
        });
        this.callParent(arguments);
    }
});

/**
 * @class Zenoss.mibs.OidModel
 * @extends Ext.data.Model
 * Field definitions for the oids
 **/
Ext.define('Zenoss.mibs.OidModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name: 'uid'},
        {name: 'name'},
        {name: 'oid'},
        {name: 'nodetype'},
        {name: 'access'},
        {name: 'status'},
        {name: 'description'}
    ]
});

/**
 * @class Zenoss.mibs.OidStore
 * @extend Zenoss.DirectStore
 * Direct store for loading ip addresses
 */
Ext.define("Zenoss.mibs.OidStore", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.mibs.OidModel',
            pageSize: 50,
            initialSortColumn: "name",
            totalProperty: 'count',
            directFn: router.getOidMappings,
            root: 'data'
        });
        this.callParent(arguments);
    }
});

function rowSelect(sm, rec, ri) {
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

oid_grid = Ext.create('Zenoss.BaseGridPanel', {
    id: 'oid_grid',
    store: Ext.create('Zenoss.mibs.OidStore', {}),
    columns: [{
        width: 300,
        id: 'name',
        flex: 1,
        dataIndex: 'name',
        header: _t('Name'),
        sortable: true
    },{
        width: 180,
        id: 'oid',
        dataIndex: 'oid',
        header: _t('OID'),
        sortable: true
    },{
        width: 100,
        id: 'nodetype',
        dataIndex: 'nodetype',
        header: _t('Node Type'),
        sortable: true
    }],
    selModel: Ext.create('Zenoss.SingleRowSelectionModel', {
        listeners: {
            select: rowSelect
        }
    })
});

trap_grid = Ext.create('Zenoss.BaseGridPanel', {
    id: 'trap_grid',
    store: Ext.create('Zenoss.mibs.TrapStore', {}),
    columns: [{
        width: 300,
        id: 'trapname',
        flex: 1,
        dataIndex: 'name',
        header: _t('Name'),
        sortable: true
    },{
        width: 180,
        id: 'trapoid',
        dataIndex: 'oid',
        header: _t('OID'),
        sortable: true
    },{
        width: 100,
        id: 'trapnodetype',
        dataIndex: 'nodetype',
        header: _t('Node Type'),
        sortable: true
    }],
    selModel: Ext.create('Zenoss.SingleRowSelectionModel', {
        listeners: {
            select: rowSelect
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
            id: 'mibbottom',
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
                    height: 37,
                    items: [{
                        xtype: 'tbtext',
                        html: _t('Display:')
                    }, {
                        xtype: 'combo',
                        cls: 'mibcombobottom',
                        store: node_type_store,
                        typeAhead: true,
                        allowBlank: false,
                        forceSelection: true,
                        triggerAction: 'all',
                        value: _t('OID Mappings'),
                        selectOnFocus: false,
                        listeners: {
                            select: function (combo, records, options) {
                                if (!records || !records.length) {
                                    return;
                                }
                                var record = records[0],
                                    node_type_map = node_type_maps[record.index],
                                    node_details = Ext.getCmp('node_details');

                                currentAddNodeTitle = node_type_map.addNodeTitle;
                                currentAddFn = node_type_map.addFn;
                                currentDeleteFn = node_type_map.deleteFn;
                                Ext.getCmp('gridCardPanel').layout.setActiveItem(record.index);
                                Ext.getCmp('gridCardPanel').layout.activeItem.setContext(Zenoss.env.PARENT_CONTEXT);
                                node_details.setTitle(node_type_map.detailsTitle);
                                node_details.name.setValue('');
                                node_details.oid.setValue('');
                                node_details.accessOrObjects.setValue('');
                                node_details.accessOrObjects.setValue('');
                                node_details.nodetype.setValue('');
                                node_details.status.setValue('');
                                node_details.description.setValue('');
                                Ext.getCmp('access_or_objects').labelEl.update(node_type_map.accessOrObjectsLabel);
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
                                    fieldDefaults: {
                                        labelAlign: 'top'
                                    },
                                    footerStyle: 'padding-left: 0',
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
                                                Ext.getCmp('gridCardPanel').layout.activeItem.refresh();
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
                            var grid = Ext.getCmp('gridCardPanel').layout.activeItem;
                            var sm = grid.getSelectionModel(),
                                sel = sm.getSelected();
                            if (sel == undefined) {
                                return;
                            }
                            currentDeleteFn({uid: sel.get("uid")}, function() {
                                var node = Ext.getCmp('node_details');
                                node.name.setValue('');
                                node.oid.setValue('');
                                node.accessOrObjects.setValue('');
                                node.accessOrObjects.setValue('');
                                node.nodetype.setValue('');
                                node.status.setValue('');
                                node.description.setValue('');
                                grid.refresh();
                            });
                        }
                    }]
                },
                items: [{
                    region: 'west',
                    layout: 'card',
                    disabled: true,
                    id: 'gridCardPanel',
                    split: true,
                    width: 600,
                    items: [oid_grid, trap_grid ]
                } , node_details]
            }]
        });
        MibBrowser.superclass.constructor.call(this, config);
    },
    setContext: function(node) {
        var params = {
            uid: node.data.uid,
            useFieldSets: false
        };
        router.getInfo(params, this.populateForm);
    },
    populateForm: function(response) {
        Zenoss.env.currentUid = response.data.uid;
        var mib_form_left = Ext.getCmp('mib_form_left'),
            mib_form_right = Ext.getCmp('mib_form_right');
        mib_form_left.name.setValue(Ext.htmlEncode(response.data.name));
        mib_form_left.contact.setValue(Ext.htmlEncode(response.data.contact));
        mib_form_right.language.setValue(Ext.htmlEncode(response.data.language));
        mib_form_right.description.setValue(Ext.htmlEncode(response.data.description));
        Ext.getCmp('gridCardPanel').layout.activeItem.setContext(Zenoss.env.PARENT_CONTEXT);
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
    tree.refresh(function(){
        tree.getRootNode().childNodes[0].expand();
        tree.selectByToken(selectedUid);
    });
}

/*
 * TODO: determine if selecting a new folder with no items in it
 *       should leave a blank panel or not
 */
Ext.define("Zenoss.MibTreePanel", {
    extend:"Zenoss.HierarchyTreePanel",
        constructor: function(config) {
            Ext.applyIf(config, {
                id: 'navTree',
                flex: 1,
                searchField: false,
                directFn: router.getOrganizerTree,
                router: router,
                selModel: treesm,
                relationshipIdentifier: 'mibs',
                pathSeparator: '/',
                selectRootOnLoad: true,
                ddGroup: 'serviceDragDrop',
                ddAppendOnly: true,
                listeners: {
                    scope: this,
                    expandnode: this.onExpandnode
                },
                viewConfig: {
                    listeners: {
                        drop: this.onNodeDrop,
                        scope:this
                    }
                
                }
            });
            this.callParent(arguments);
        },
        onNodeDrop: function(n, nodedata, model, drop, func, opt) {
            router.moveNode({
                    uids: [nodedata.records[0].data.uid],
                    target: nodedata.records[0].parentNode.data.uid
                }, 
                function () {
                    this.moveMibsCallback(nodedata.records[0].parentNode.data.uid);
                }, this);
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
            this.un('itemclick', this.addHistoryToken, this);
        }

});

/**********************************************************************
 *
 * Action Buttons
 *
 */

treesm = new Zenoss.TreeSelectionModel({
    listeners: {
        'selectionchange': function (sm, nodes) {
            var newnode;
            if (nodes.length) {
                newnode = nodes[0];
            }
            var isRoot = false;

            if (newnode && newnode.data.leaf) {
                var uid = newnode.data.uid,
                    meta_type = newnode.data.meta_type;
                    mib_browser.setContext(newnode);
                Ext.getCmp('gridCardPanel').setDisabled(false);
            }

            if (newnode) {
                // set the context for the new nodes
                Zenoss.env.PARENT_CONTEXT = newnode.data.uid;
                if (newnode.data.uid == '/zport/dmd/Mibs') {
                    isRoot = true;
                }
                Ext.getCmp('add-organizer-button').setDisabled(newnode.data.leaf);
                Ext.getCmp('edit-mib-action').setDisabled(!newnode.data.leaf);
                // do not allow them to delete the root node
                Ext.getCmp('delete-button').setDisabled(isRoot);

                // add to history
                Ext.History.add('mibtree' + Ext.History.DELIMITER + newnode.data.uid);
            }

        }
    }
});

mib_tree = new Zenoss.MibTreePanel({
    id: 'mibtree',
    cls: 'mib-tree',
    ddGroup: 'mibtreedd',
    searchField: true,
    router: router,
    root: {
        id: 'Mibs',
        uid: '/zport/dmd/Mibs',
        text: _t('Mib Classes'),
        allowDrop: false
    },
    listeners: {
        click: function (node, e) {
            if (node.data.leaf) {
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
        width: 250,
        maxWidth: 250,
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
    win = Ext.create('Zenoss.dialog.BaseWindow', {
        id: 'editMIBDialog',
        title: _t('Edit MIB'),
        height: 360,
        width: 510,
        modal: true,
        autoScroll: true,
        plain: true,
        buttonAlight: 'left',
        items:{
            xtype:'form',
            ref: 'editForm',
            buttonAlign: 'left',

            items: items,
            listeners: {
                validitychange: function(form, valid) {
                    if (win.isVisible()){
                        win.submitButton.setDisabled(!valid);
                    }
                }
            }
        },
        buttons:[{
            xtype: 'DialogButton',
            ref: '../submitButton',
            text: _t('Submit'),
            handler: function(button) {
                var form = button.refOwner.editForm.getForm(),
                dirtyOnly=true,
                opts = form.getValues(false, dirtyOnly);
                opts.uid = data.uid;
                router.setInfo(opts, function(response) {
                    reloadTree(response.data.uid);
                });
            }
        },{
            xtype: 'DialogButton',
            text: _t('Cancel')
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
                formId: Ext.id(),
                formListeners: {
                    validitychange: function(field, isValid) {
                        if (addDialog.isVisible()) {
                             addDialog.submitButton.setDisabled(!isValid);
                        }
                    }
                },
                width: 310,
                items: [{
                    xtype: 'idfield',
                    fieldLabel: _t('ID'),
                    ref: '../nameField',
                    name: 'name',
                    tabIndex: 0,
                    allowBlank: false
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Submit'),
                    ref: '../submitButton',
                    disabled: true,
                    tabIndex: 1,
                    handler: function () {
                        var newName;
                        newName = addDialog.nameField.getValue();
                        mib_tree.addNode(typeName, newName);
                    }
                },
                    Zenoss.dialog.CANCEL
                ]
            });
            addDialog.show();
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
        src = node.data.uid + '/uploadfile',
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
                fieldDefaults: {
                    labelAlign: 'top'
                },
                footerStyle: 'padding-left: 0',
                items: [{
                    xtype: 'panel',
                    width: 270,
                    height: 70,
                    layout: 'anchor',
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
                fieldDefaults: {
                    labelAlign: 'top'
                },
                footerStyle: 'padding-left: 0',
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
                            opts = form.getValues();
                        opts.organizer = Zenoss.env.PARENT_CONTEXT.replace('/zport/dmd/Mibs', '');
                        router.addMIB(opts,
                        function(response) {
                            if (!response.success) {
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
    disabled: true,
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
    if (!node.data.leaf) {
        nodeType = "Organizer";
    }
    new Zenoss.dialog.SimpleMessageDialog({
        message: Ext.String.format(_t('Are you sure you want to delete the selected {0}?'), nodeType),
        title: _t('Delete Mib'),
        buttons: [{
            xtype: 'DialogButton',
            text: _t('Delete'),
            handler: function() {
                var params = {
                    uid: node.data.uid
                },
                parentUid = node.parentNode.data.uid,
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
    var addtozenpack = new Zenoss.AddToZenPackWindow();
    addtozenpack.setTarget(treesm.getSelectedNode().data.uid);
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
                        uid: node.data.uid,
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
