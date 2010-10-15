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

// Script for the processes page.

Ext.onReady(function(){

Ext.ns('Zenoss', 'Zenoss.env');
var treeId = 'processTree';
var router = Zenoss.remote.ProcessRouter;

new Zenoss.MessageDialog({
    id: 'dirtyDialog',
    title: _t('Unsaved Data'),
    message: _t('The changes made in the form will be lost.'),
    okHandler: function() {
        Ext.getCmp('processForm').getForm().reset();
        Zenoss.env.node.select();
    }
});

/* ***************************************************************************
 *
 *   master_panel - the processes tree on the left
 *
 */

function beforeselectHandler(sm, node, oldNode) {
    if (node == oldNode) {
        return false;
    }
    if ( Ext.getCmp('processForm').getForm().isDirty() ) {
        // the user made changes to the form make sure that they don't care
        // about losing those changes
        Zenoss.env.node = node;
        Ext.getCmp('dirtyDialog').show();
        return false;
    }
    return true;
}

// function that gets run when the user clicks on a node in the tree
function selectionchangeHandler(sm, node) {
    if (node) {
        // load up appropriate data in the form
        var uid = node.attributes.uid, grid =
            Ext.getCmp('navGrid');
        Ext.getCmp('processForm').setContext(uid);
        Ext.getCmp('detail_panel').detailCardPanel.setContext(uid);
        Ext.getCmp('footer_bar').setContext(uid);
        // don't allow the user to delete the root node
        Ext.getCmp('footer_bar').buttonDelete.setDisabled(
                node == Ext.getCmp(treeId).root);
        // refresh the process class grid
        grid.getSelectionModel().clearSelections();
        grid.serviceClassName = null;
        grid.getView().contextUid = node.attributes.uid;
        grid.getView().updateLiveRows(Ext.getCmp('navGrid').getView().rowIndex, true, true, false);
    }
}

var selModel = new Ext.tree.DefaultSelectionModel({
    listeners: {
        beforeselect: beforeselectHandler,
        selectionchange: selectionchangeHandler
    }
});

var MoveProcessCallback = Ext.extend(Object, {
    constructor: function(tree, node) {
        this.tree = tree;
        this.node = node;
        MoveProcessCallback.superclass.constructor.call(this);
    },
    call: function(provider, response) {
        var node = this.node,
            tree = this.tree;
        node.setId(response.result.id);
        node.attributes.uid = response.result.uid;
        tree.selectPath(this.node.getPath());
        tree.getRootNode().reload(function() {
            tree.expandAll();
            // select the node that just moved
            tree.selectByToken(node.attributes.id);
        });

        Ext.History.add(tree.id + Ext.History.DELIMITER + node.id);

    }
});

var ProcessTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            id: treeId,
            searchField: true,
            cls: 'x-tree-noicon',
            directFn: router.getTree,
            router: router,
            selModel: selModel,
            flex: 1,
            enableDD: true,
            ddGroup: 'processDragDrop',
            ddAppendOnly: true,
            listeners: {
                scope: this,
                beforenodedrop: this.onNodeDrop,
                expandnode: this.onExpandnode
            },
            root: {
                id: 'Processes',
                uid: '/zport/dmd/Processes'
            }
        });
        ProcessTreePanel.superclass.constructor.call(this, config);

    },

    onNodeDrop: function(dropEvent) {
        var node, uid, target, targetUid, params, callback, data;
        if (dropEvent.dropNode) {
            // moving a ServiceOrganizer into another ServiceOrganizer
            uid = dropEvent.dropNode.attributes.uid;
        } else {
            // moving a ServiceClass from grid into a ServiceOrganizer
            var data = Ext.pluck(dropEvent.data.selections, 'data');
            uid = data[0].uid;
        }
        target = dropEvent.target;
        target.expand();
        targetUid = target.attributes.uid;
        params = {uid: uid, targetUid: targetUid};
        callback = new MoveProcessCallback(this, target);
        router.moveProcess(params, callback.call, callback);
    },

    onExpandnode: function(node) {
        if (node.id === '.zport.dmd.Processes') {
            // the root node has been loaded from the server.  All the nodes
            // in this TreePanel have been registered and the getNodeById
            // method will now return a node instance instead of null.
            var token = Ext.History.getToken();
            if (token) {
                var nodeId = unescape(token.split(Ext.History.DELIMITER).slice(1));
                var organizers = nodeId.split('.osProcessClasses.')[0].split('.').slice(4);
                var orgId = '.zport.dmd.Processes';
                // expand each of the organizers leading to the node in the token
                Ext.each(organizers, function(org) {
                    orgId += '.' + org;
                    this.getNodeById(orgId).expand();
                }, this);
                this.selectByToken(nodeId);
            }
        }
    },

    selectByToken: function(nodeId) {
        var node, tokenParts;
        // called from Ext.History.selectByToken defined in HistoryManager.js
        // overrides HierarchyTreePanel method
        tokenParts = nodeId.split('.osProcessClasses.');
        node = this.getNodeById(unescape(tokenParts[0]));
        if (node) {
            this.selectPath(node.getPath());
        }
        if (tokenParts[1]) {
            Ext.getCmp('navGrid').filterAndSelectRow(tokenParts[1]);
        }

        // node is null prior to the TreePanel load event firing for the root
        // node with the id .zport.dmd.Processes (the id that comes from the
        // server). In this case the correct node will be selected once that
        // event fires and the onLoad method is called.
    }

});
var ProcessGridView = Ext.extend(Zenoss.FilterGridView, {

    constructor: function(config) {
        this.addEvents({
            /**
             * @event livebufferupdated
             * Fires at the end of a call to liveBufferUpdate.
             * @param {Ext.ux.BufferedGridView} this
             */
            'livebufferupdated' : true
        });
        ProcessGridView.superclass.constructor.call(this, config);
    },

    liveBufferUpdate: function() {
        ProcessGridView.superclass.liveBufferUpdate.apply(this, arguments);
        this.fireEvent('livebufferupdated', this);
    }});

var ProcessGridPanel = Ext.extend(Zenoss.FilterGridPanel, {

        constructor: function(config) {
            Ext.applyIf(config, {
                id: 'navGrid',
                flex: 3,
                stateId: 'processNavGridState',
                stateful: true,
                border: false,
                enableDrag: true,
                ddGroup: 'processDragDrop',
                autoExpandColumn: 'name',
                rowSelectorDepth: 5,
                height: 500,
                loadMask: true,
                store: new Ext.ux.grid.livegrid.Store({
                    proxy: new Ext.data.DirectProxy({
                        directFn:Zenoss.remote.ProcessRouter.query
                    }),
                    autoLoad: false,
                    bufferSize: 100,
                    defaultSort: {field:'name', direction:'ASC'},
                    sortInfo: {field:'name', direction:'ASC'},
                    reader: new Ext.ux.grid.livegrid.JsonReader({
                        root: 'processes',
                        totalProperty: 'totalCount'
                    }, [
                        {name:'name', type:'string'},
                        {name:'description', type:'string'},
                        {name:'count', type:'integer'},
                        {name:'uid', type:'string'}
                    ]) // reader
                }),
                sm: new Zenoss.ExtraHooksSelectionModel({
                    singleSelect: true,
                    listeners: {
                        rowselect: function(sm, rowIndex, record) {
                            var uid = record.data.uid, token, tokenParts, detail;
                            Ext.getCmp('processForm').setContext(uid);
                            detail = Ext.getCmp('detail_panel');
                            detail.detailCardPanel.setContext(uid);
                            detail.detailCardPanel.expand();
                            Ext.getCmp('footer_bar').setContext(uid);
                            // add to history
                            token = Ext.History.getToken();
                            if ( ! token ) {
                                token = treeId + ':' + Ext.getCmp(treeId).getRootNode().attributes.uid.replace(/\//g, '.');
                            }
                            tokenParts = token.split('.osProcessClasses.');
                            if ( tokenParts[1] !== record.data.name ) {
                                Ext.History.add( tokenParts[0] + '.osProcessClasses.' + record.data.name);
                            }
                        }
                    }
                }),
                cm: new Ext.grid.ColumnModel({

                    defaults: {
                        sortable: true,
                        menuDisabled: true
                    },
                    columns: [ {
                        dataIndex : 'name',
                        header : _t('Name'),
                        id : 'name'
                    },{
                        dataIndex : 'count',
                        header : _t('Count'),
                        filter: false,
                        id : 'count'
                    }]
                }),
                view:  new ProcessGridView({
                    nearLimit: 20,
                    loadMask: {msg: 'Loading...',
                              msgCls: 'x-mask-loading'},
                    listeners: {
                        beforeBuffer: function(view, ds, idx, len, total, opts) {
                            opts.params.uid = view._context;
                        }
                    }
                })
            });
            ProcessGridPanel.superclass.constructor.call(this, config);
            this.on('afterrender',
            function(me){
                me.view.showFilters();
            });
            // load mask stuff
            this.store.proxy.on('beforeload', function(){
                this.view.showLoadMask(true);
            }, this);
            this.store.proxy.on('load', function(){
                this.view.showLoadMask(false);
            }, this);
        },

        filterAndSelectRow: function(serviceClassName) {
            var selectedRecord;
            if (serviceClassName) {
                // the token includes a ServiceClass. Filter the grid
                // using the name of the ServiceClass and select the
                // correct row.
                selectedRecord = this.getSelectionModel().getSelected();
                if ( ! selectedRecord || selectedRecord.data.name !== serviceClassName ) {
                    this.serviceClassName = serviceClassName;
                    this.selectRow();
                    this.getView().on('livebufferupdated', this.filterGrid, this);
                }
            }
        },

        filterGrid: function() {
            if (this.serviceClassName) {
                this.getView().un('livebufferupdated', this.filterGrid, this);
                Ext.getCmp('name').setValue(unescape(this.serviceClassName));
                this.getView().on('livebufferupdated', this.selectRow, this);
            }
        },

        selectRow: function() {
            this.getView().un('livebufferupdated', this.selectRow, this);
            this.getStore().each(this.selectRowByName, this);
        },
        selectRowByName: function(record) {
            if ( record.data.name === this.serviceClassName ) {
                this.getSelectionModel().selectRow( this.getStore().indexOf(record) );
                return false;
            }
        },
        deleteSelectedRow: function() {
            var row = this.getSelectionModel().getSelected(),
                me = this;
            if (!row){
                return;
            }
            var uid = row.data.uid;
            router.deleteNode({uid:uid}, function(response){
                me.reload();
            });
        },
        reload: function() {
            this.getView().contextUid = this.getView().contextUid;
            this.getView().updateLiveRows(this.getView().rowIndex, true, true, false);
        }
});

var tree = new ProcessTreePanel({});
var grid = new  ProcessGridPanel({});
var panel = new Ext.Panel({
    layout: {
        type:'vbox',
        align: 'stretch'
    },

    items:[tree, grid]
}
);

Ext.getCmp('master_panel').add(panel);

/* **************************************************************************
 *
 *   top_detail_panel - the process form on the top right
 *
 */

// when the form loads, show/hide the regex fieldset
function actioncompleteHandler(basicForm, action) {
    if (action.type == 'directload') {
        var formPanel = Ext.getCmp('processForm');
        formPanel.isLoadInProgress = false;
        var processInfo = action.result.data;
        // disabling the forms will disable all of the elements in it
        if ( Zenoss.Security.doesNotHavePermission('Manage DMD') ) {
            formPanel.disable();
        }
        var isRoot = processInfo.name == 'Processes';
        Ext.getCmp('nameTextField').setDisabled(isRoot);
        Ext.getCmp('regexTextField').setDisabled(!processInfo.hasRegex);
        Ext.getCmp('ignoreParametersSelect').setDisabled(!processInfo.hasRegex);
        var regexFieldSet = Ext.getCmp('regexFieldSet');
        regexFieldSet.setVisible(processInfo.hasRegex);
        regexFieldSet.doLayout();
    } else if (action.type == 'directsubmit') {
        var processTree = Ext.getCmp(treeId);
        var selectionModel = processTree.getSelectionModel();
        var selectedNode = selectionModel.getSelectedNode();
        var nameTextField = Ext.getCmp('nameTextField');

        selectedNode.attributes.text.text = nameTextField.getValue();
        selectedNode.setText(selectedNode.attributes.text);
        Ext.getCmp('detail_panel').detailCardPanel.setContext(selectedNode.attributes.uid);
        // reload the detail grid
        var grid = Ext.getCmp('navGrid');
        grid.reload();
    }
}

var nameTextField = {
    xtype: 'textfield',
    id: 'nameTextField',
    fieldLabel: _t('Name'),
    name: 'name',
    allowBlank: false,
    width: "100%"
};

var descriptionTextField = {
    xtype: 'textarea',
    fieldLabel: _t('Description'),
    name: 'description',
    width: "100%",
    grow: true
};

var regexTextField = {
    xtype: 'textfield',
    id: 'regexTextField',
    fieldLabel: _t('Pattern'),
    name: 'regex',
    width: "94%",
    allowBlank: false
};

var ignoreParametersSelect = {
    xtype: 'select',
    id: 'ignoreParametersSelect',
    fieldLabel: _t('Ignore Parameters'),
    name: 'ignoreParameters',
    mode: 'local',
    store: [[true, 'Yes'], [false, 'No']]
};

var zMonitor = {
    xtype: 'zprop',
    ref: '../../zMonitor',
    title: _t('Enable Monitoring? (zMonitor)'),
    name: 'zMonitor',
    localField: {
        xtype: 'select',
        mode: 'local',
        store: [[true, 'Yes'], [false, 'No']]
    }
};

var zAlertOnRestart = {
    xtype: 'zprop',
    ref: '../../zAlertOnRestart',
    title: _t('Send Event on Restart? (zAlertOnRestart)'),
    name: 'zAlertOnRestart',
    localField: {
        xtype: 'select',
        mode: 'local',
        store: [[true, 'Yes'], [false, 'No']]
    }
};

var zFailSeverity = {
    xtype: 'zprop',
    ref: '../../zFailSeverity',
    title: _t('Failure Event Severity (zFailSeverity)'),
    name: 'zFailSeverity',
    localField: {
        xtype: 'select',
        mode: 'local',
        store: Zenoss.env.SEVERITIES.slice(0, 5)
    }
};

var regexFieldSet = {
    xtype: 'fieldset',
    id: 'regexFieldSet',
    title: _t('Regular Expression'),
    hidden: true,
    items: [
        regexTextField,
        ignoreParametersSelect
    ]
}; // regexFieldSet

// the items that make up the form
var processFormItems = {
    layout: 'column',
    border: false,
    defaults: {
        layout: 'form',
        border: false,
        bodyStyle: 'padding: 15px',
        columnWidth: 0.5
    },
    items: [
        {items: [nameTextField, descriptionTextField, regexFieldSet]},
        {items: [zMonitor, zAlertOnRestart, zFailSeverity]}
    ]
}; // processFormItems

var processFormConfig = {
    xtype: 'basedetailform',
    trackResetOnLoad: true,
    id: 'processForm',
    permission: 'Manage DMD',
    region: 'center',
    items: processFormItems,
    router: router
};

var processForm = Ext.getCmp('detail_panel').add(processFormConfig);
processForm.on('actioncomplete', actioncompleteHandler);

/************************************************************************
 *
 *   bottom_detail_panel - the device and event grid on the bottom right
 *
 **/
Ext.getCmp('detail_panel').add({
    xtype: 'instancecardpanel',
    ref: 'detailCardPanel',
    region: 'south',
    split: true,
    router: router,
    instancesTitle: 'Process Instances',
    nameDataIndex: 'processName',
    zPropertyEditListeners: {
        frameload: function() {
            var formPanel = Ext.getCmp('processForm');
            formPanel.setContext(formPanel.contextUid);
        }
    }
});

var ContextGetter = Ext.extend(Object, {
    getUid: function() {
        var selected = Ext.getCmp('processTree').getSelectionModel().getSelectedNode();
        if ( ! selected ) {
            Ext.Msg.alert(_t('Error'), _t('You must select a process.'));
            return null;
        }
        return selected.attributes.uid;
    },
    hasTwoControls: function() {
        return false;
    }
});

/* ***********************************************************************
 *
 *   footer_panel - the add/remove tree node buttons at the bottom
 *
 */
function dispatcher(actionName, value) {
    var tree = Ext.getCmp(treeId);
    var grid = Ext.getCmp('navGrid');
    switch (actionName) {
        case 'addClass': tree.addNode('class', value); break;
        case 'addOrganizer': tree.addNode('organizer', value); break;
        case 'delete': grid.deleteSelectedRow(); break;
        case 'deleteOrganizer': tree.deleteSelectedNode(); break;
        default: break;
    }
};

var footer = Ext.getCmp('footer_bar');
Zenoss.footerHelper('Process', footer, {contextGetter: new ContextGetter()});
footer.on('buttonClick', dispatcher);
footer.buttonDelete.setDisabled(true);

Zenoss.SequenceGrid = Ext.extend(Zenoss.BaseSequenceGrid, {
    constructor: function(config) {
        Ext.applyIf(config, {
            stripeRows: true,
            autoScroll: true,
            border: false,
            layout: 'fit',
            viewConfig: {forceFit: true},
            store: {
                xtype: 'directstore',
                root: 'data',
                autoSave: false,
                idProperty: 'uid',
                directFn: router.getSequence,
                fields: ['uid', 'folder', 'name', 'regex', 'monitor', 'count']
            },
            columns: [
                {dataIndex: 'folder', header: 'Folder'},
                {dataIndex: 'name', header: 'Name'},
                {dataIndex: 'regex', header: 'Regex'},
                {dataIndex: 'monitor', header: 'Monitor'},
                {dataIndex: 'count', header: 'Count'}
            ]
        });
        Zenoss.SequenceGrid.superclass.constructor.call(this, config);
    }
});
Ext.reg('sequencegrid', Zenoss.SequenceGrid);

Ext.getCmp('footer_bar').buttonContextMenu.menu.addItem({
    id: 'sequenceButton',
    iconCls: 'set',
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    tooltip: 'Sequence the process classes',
    text: _t('Change Sequence'),
    handler: function(button, event) {
        if ( ! Ext.getCmp('sequenceDialog') ) {
            new Zenoss.HideFitDialog({
                id: 'sequenceDialog',
                title: _t('Sequence'),
                items: [
                {
                    xtype: 'sequencegrid',
                    id: 'sequenceGrid'
                }],
                buttons: [{
                    xtype: 'HideDialogButton',
                    text: _t('Submit'),
                    handler: function(button, event) {
                        var records, uids;
                        records = Ext.getCmp('sequenceGrid').getStore().getRange();
                        uids = Ext.pluck(records, 'id');
                        router.setSequence({'uids': uids});
                    }
                 }, {
                    xtype: 'HideDialogButton',
                    text: _t('Cancel')
                }]
            });
        }
        Ext.getCmp('sequenceGrid').getStore().load();
        Ext.getCmp('sequenceDialog').show();
    }
});

}); // Ext.onReady
