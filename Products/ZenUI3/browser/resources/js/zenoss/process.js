/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


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
        Zenoss.env.node.getOwnerTree().getSelectionModel().select(Zenoss.env.node);
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
function selectionchangeHandler(sm, nodes) {
    if (nodes.length) {
        // load up appropriate data in the form
        var node = nodes[0],
            uid = node.get("uid"),
            grid = Ext.getCmp('navGrid');
        Ext.getCmp('processForm').setContext(uid);
        Ext.getCmp('detailCardPanel').setContext(uid);
        Ext.getCmp('footer_bar').setContext(uid);
        // don't allow the user to delete the root node
        Ext.getCmp('footer_bar').buttonDelete.setDisabled(
                node == Ext.getCmp(treeId).root);
        // refresh the process class grid
        grid.getSelectionModel().clearSelections();

        grid.setContext(node.get("uid"));
    }
}

var selModel = new Zenoss.TreeSelectionModel({
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
        node.data.uid = response.result.uid;
        tree.selectPath(this.node.getPath());
        tree.refresh({
            callback: function() {
                tree.expandAll();
                // select the node that just moved
                tree.selectByToken(node.get("uid"));
            }
        });

        Ext.History.add(tree.id + Ext.History.DELIMITER + node.get("id"));
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
            listeners: {
                scope: this,
                expandnode: this.onExpandnode
            },
            root: {
                id: 'Processes',
                uid: '/zport/dmd/Processes'
            },
            ddGroup: 'processDragDrop',
            viewConfig: {
                listeners: {
                    beforedrop: Ext.bind(this.onNodeDrop, this)
                }
            }
        });
        ProcessTreePanel.superclass.constructor.call(this, config);

    },
    onNodeDrop: function(element, event, target) {
        var uid, targetUid, params, callback;
        uid = event.records[0].get("uid");
        target.expand();
        targetUid = target.get("uid");
        params = {uid: uid, targetUid: targetUid};
        callback = new MoveProcessCallback(this, target);
        router.moveProcess(params, callback.call, callback);
        return false;
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
        if (tokenParts[0]) {
            this.callParent([tokenParts[0]]);
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

/**
 * @class Zenoss.process.ProcessModel
 * @extends Ext.data.Model
 * Field definitions for processes
 **/
Ext.define('Zenoss.process.ProcessModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name:'name', type:'string'},
        {name:'description', type:'string'},
        {name:'count', type:'integer'},
        {name:'uid', type:'string'}
    ]
});

/**
 * @class Zenoss.process.ProcessStore
 * @extend Zenoss.DirectStore
 * Direct store for loading processes
 */
Ext.define("Zenoss.process.ProcessStore", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.process.ProcessModel',
            initialSortColumn: "name",
            directFn: Zenoss.remote.ProcessRouter.query,
            root: 'processes',
            pageSize: 400
        });
        this.callParent(arguments);
    }
});


Ext.define("Zenoss.process.ProcessGrid", {
    extend:"Zenoss.FilterGridPanel",
    constructor: function(config) {
        Ext.applyIf(config, {
            id: 'navGrid',
            flex: 3,
            stateId: 'processNavGridState',
            stateful: true,
            viewConfig: {
                plugins: {
                    ptype: 'gridviewdragdrop',
                    ddGroup: 'processDragDrop'
                }
            },
            rowSelectorDepth: 5,
            height: 500,
            store: Ext.create('Zenoss.process.ProcessStore', {}),
            selModel: new Zenoss.ExtraHooksSelectionModel({
                singleSelect: true,
                listeners: {
                    select: function(sm, record, rowIndex) {
                        var uid = record.data.uid, token, tokenParts, cardpanel;
                        cardpanel = Ext.getCmp('detailCardPanel');
                        Ext.getCmp('processForm').setContext(uid);
                        cardpanel.setContext(uid);
                        Ext.getCmp('footer_bar').setContext(uid);
                        // add to history
                        token = Ext.History.getToken();
                        if ( ! token ) {
                            token = treeId + ':' + Ext.getCmp(treeId).getRootNode().data.uid.replace(/\//g, '.');
                        }
                        tokenParts = token.split('.osProcessClasses.');
                        if ( tokenParts[1] !== record.data.name ) {
                            Ext.History.add( tokenParts[0] + '.osProcessClasses.' + record.data.name);
                        }
                    }
                }
            }),
            columns: [ {
                dataIndex : 'name',
                header : _t('Name'),
                flex: 1,
                id : 'name'
            },{
                dataIndex : 'count',
                header : _t('Count'),
                filter: false,
                id : 'count'
            }]

        });
        this.callParent(arguments);
    },

    filterAndSelectRow: function(serviceClassName) {
        var selections, selectedRecord;
        if (serviceClassName) {
            // the token includes a ServiceClass. Filter the grid
            // using the name of the ServiceClass and select the
            // correct row.
            selections = this.getSelectionModel().getSelection();
            if (selections.length) {
                selectedRecord = selections[0];
            }

            if ( ! selectedRecord || selectedRecord.data.name !== serviceClassName ) {
                this.serviceClassName = serviceClassName;
                this.getStore().on('datachanged', this.filterGrid, this, {single: true});
            }
        }else{
            this.setFilter('name', '');
        }
    },
    filterGrid: function() {
        var me = this,
        serviceClassName = this.serviceClassName;
        if (!serviceClassName) {
            return;
        }
        // look for it in our current store
        function selectrow() {
            var found = false;
            me.getStore().each(function(record){
                if (record.get("name") == serviceClassName) {
                    me.getSelectionModel().select(record);
                    found = true;
                }
            });
            return found;
        }
        if (!selectrow()) {
            // otherwise filter for it and find the service then
            this.setFilter('name', serviceClassName);
            this.getStore().on('datachanged', selectrow, this, {single: true});
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
            me.refresh();
        });
    }
});

var tree = new ProcessTreePanel({});
var treepanel = {
    xtype: 'panel',
    layout: 'fit',
    flex: 1,
    items: [tree]

};

var grid =  Ext.create('Zenoss.process.ProcessGrid', {});
var panel = new Ext.Panel({
    layout: {
        type: 'vbox',
        align: 'stretch'
    },

    items:[treepanel, grid]
});



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
        Ext.getCmp('nameTextField2').setDisabled(isRoot);
        Ext.getCmp('regexTextField').setDisabled(!processInfo.hasRegex).allowBlank = !processInfo.hasRegex;
        Ext.getCmp('regexExcludeTextField').setDisabled(!processInfo.hasRegex);
        // Ext.getCmp('exampleTextField').setDisabled(!processInfo.hasRegex);
        var regexFieldSet = Ext.getCmp('regexFieldSet');
        regexFieldSet.setVisible(processInfo.hasRegex);
    } else if (action.type == 'directsubmit') {
        var processTree = Ext.getCmp(treeId);
        var selectionModel = processTree.getSelectionModel();
        var selectedNode = selectionModel.getSelectedNode();
        var nameTextField = Ext.getCmp('nameTextField2');
        if(selectedNode.data.text.text != nameTextField.getValue()){
            selectedNode.data.text.text = nameTextField.getValue();
            Ext.getCmp('navGrid').refresh();
            processTree.refresh();
        }
        Ext.getCmp('detail_panel').detailCardPanel.setContext(selectedNode.data.uid);
    }
}

var nameTextField2 = {
    xtype: 'textfield',
    id: 'nameTextField2',
    fieldLabel: _t('Name'),
    name: 'name',
    allowBlank: false
};

var descriptionTextField = {
    xtype: 'textarea',
    fieldLabel: _t('Description'),
    name: 'description',
    grow: true
};

var regexTextField = {
    xtype: 'textfield',
    id: 'regexTextField',
    fieldLabel: _t('Search Pattern'),
    name: 'regex',
    allowBlank: false
};

var regexExcludeTextField = {
    xtype: 'textfield',
    id: 'regexExcludeTextField',
    fieldLabel: _t('Exclude Pattern'),
    name: 'excludeRegex',
    allowBlank: true
};

var exampleTextField = {
    xtype: 'textfield',
    id: 'exampleTextField',
    fieldLabel: _t('Example'),
    name: 'example'

};

var minCountThreshold = {
    xtype: 'numberfield',
    id: 'minProcessCount',
    fieldLabel: _t("Minimum"),
    name: 'minProcessCount',
    allowBlank: true
};

var maxCountThreshold = {
    xtype: 'numberfield',
    id: 'maxProcessCount',
    fieldLabel: _t("Maximum"),
    name: 'maxProcessCount',
    allowBlank: true
};    

var zMonitor = {
    xtype: 'zprop',
    ref: '../../zMonitor',
    title: _t('Enable Monitoring? (zMonitor)'),
    name: 'zMonitor',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        displayField: 'name',
        valueField: 'value',
        store: new Ext.data.ArrayStore({
            data: [['Yes', true], ['No', false]],
            model: 'Zenoss.model.NameValue'
        })
    }
};

var zAlertOnRestart = {
    xtype: 'zprop',
    ref: '../../zAlertOnRestart',
    title: _t('Send Event on Restart? (zAlertOnRestart)'),
    name: 'zAlertOnRestart',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        displayField: 'name',
        valueField: 'value',
        store: new Ext.data.ArrayStore({
            data: [['Yes', true], ['No', false]],
            model: 'Zenoss.model.NameValue'
        })
    }
};

var zFailSeverity = {
    xtype: 'zprop',
    ref: '../../zFailSeverity',
    title: _t('Failure Event Severity (zFailSeverity)'),
    name: 'zFailSeverity',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        store: Zenoss.env.SEVERITIES.slice(0, 5)
    }
};

var zModelerLock = {
    xtype: 'zprop',
    ref: '../../zModelerLock',
    title: _t('Lock Process Components? (zModelerLock)'),
    name: 'zModelerLock',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        displayField: 'name',
        valueField: 'value',
        store: new Ext.data.ArrayStore({
            data: [['Unlocked', 0], [_t('Lock from Deletes'), 1], [_t('Lock from Updates'), 2]],
            model: 'Zenoss.model.NameValue'
        })
    }
};

var zSendEventWhenBlockedFlag = {
    xtype: 'zprop',
    ref: '../../zSendEventWhenBlockedFlag',
    title: _t('Send an event when action is blocked? (zSendEventWhenBlockedFlag)'),
    name: 'zSendEventWhenBlockedFlag',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        displayField: 'name',
        valueField: 'value',
        store: new Ext.data.ArrayStore({
            data: [['Yes', true], ['No', false]],
            model: 'Zenoss.model.NameValue'
        })
    }
};

var regexFieldSet = {
    xtype: 'fieldset',
    id: 'regexFieldSet',
    title: _t('Regular Expression'),
    hidden: true,
    style: 'padding: 5px 0 0 0',
    items: [
        regexTextField,
        regexExcludeTextField,
        // , exampleTextField
    ]
}; // regexFieldSet

var processCountThreshold = {
    xtype: 'fieldset',
    id: 'processCountFieldSet',
    title: _t("Process Count Threshold"),
    hidden: false,
    style: 'padding: 5px 0 0 0',
    items: [
        minCountThreshold,
        maxCountThreshold
    ]
}; // processCountThreshold

// the items that make up the form
var processFormItems = {
    layout: 'column',
    autoScroll: true,
    defaults: {
        layout: 'anchor',
        bodyStyle: 'padding: 15px',
        columnWidth: 0.5
    },
    items: [
        {defaults:{anchor:'95%'}, items: [nameTextField2, descriptionTextField, regexFieldSet, processCountThreshold]},
        {defaults:{anchor:'95%'}, items: [zMonitor, zAlertOnRestart, zFailSeverity, zModelerLock, zSendEventWhenBlockedFlag]}
    ]
}; // processFormItems


/************************************************************************
 *
 *   bottom_detail_panel - the device and event grid on the bottom right
 *
 **/


Ext.getCmp('center_panel').add(
        new Ext.Panel({
            layout: 'border',
            items: [{
                id: 'master_panel',
                region: 'west',
                layout: 'fit',
                width: 250,
                maxWidth: 250,
                split: true,
                items: panel
            },{
                id: 'detail_panel',
                region: 'center',
                layout: 'border',
                items: [{
                    xtype: 'basedetailform',
                    layout: 'fit',
                    trackResetOnLoad: true,
                    id: 'processForm',
                    permission: 'Manage DMD',
                    region: 'center',
                    items: processFormItems,
                    router: router,
                    listeners: {
                        actioncomplete: actioncompleteHandler
                    }
                }, {
                    xtype: 'instancecardpanel',
                    id: 'detailCardPanel',
                    ref: 'detailCardPanel',
                    region: 'south',
                    split: true,
                    collapsed: false,
                    collapsible: false,
                    router: router,
                    bufferSize: 100,
                    nearLimit: 20,
                    instancesTitle: _t('Process Instances'),
                    zPropertyEditListeners: {
                        frameload: function() {
                            var formPanel = Ext.getCmp('processForm');
                            formPanel.setContext(formPanel.contextUid);
                        }
                    }
                }]
            }]
        }
    ));


var ContextGetter = Ext.extend(Object, {
    getUid: function() {
        var selected = Ext.getCmp('processTree').getSelectionModel().getSelectedNode();
        if ( ! selected ) {
            Ext.Msg.alert(_t('Error'), _t('You must select a process.'));
            return null;
        }
        return selected.data.uid;
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
Ext.getCmp('footer_delete_button').setDisabled(true);


/**
 * @class Zenoss.SequenceModel
 * @extends Ext.data.Model
 * Model for sequence data grid
 **/
Ext.define('Zenoss.SequenceModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields:
        [ {name: 'uid'},
          {name: 'folder'},
          {name: 'name'},
          {name: 'regex'},
          {name: 'monitor'},
          {name: 'count'}
        ]

});
/**
 * @class Zenoss.SequenceStore
 * @extend Zenoss.DirectStore
 * Direct store for loading up the sequence grid
 */
Ext.define("Zenoss.SequenceStore", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.SequenceModel',
            directFn: router.getSequence,
            root: 'data'
        });
        this.callParent(arguments);
    }
});


Ext.define("Zenoss.SequenceGrid", {
    alias: ['widget.sequencegrid'],
    extend:"Zenoss.BaseSequenceGrid",
    constructor: function(config) {
        Ext.applyIf(config, {
            sortableColumns: false,
            forceFit: true,
            store: Ext.create('Zenoss.SequenceStore', {}),
            columns: [
                {dataIndex: 'folder', header: 'Folder', menuDisabled: true},
                {dataIndex: 'name', header: 'Name', menuDisabled: true},
                {dataIndex: 'regex', header: 'Regex', menuDisabled: true },
                {dataIndex: 'monitor', header: 'Monitor', menuDisabled: true},
                {dataIndex: 'count', layout:'anchor', header: 'Count', menuDisabled: true}
            ]
        });
        this.callParent(arguments);
    }
});


Ext.getCmp('footer_bar').buttonContextMenu.menu.add({
    id: 'sequenceButton',
    iconCls: 'set',
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    tooltip: _t('Sequence the process classes'),
    text: _t('Change Sequence'),
    handler: function(button, event) {
        if ( ! Ext.getCmp('sequenceDialog') ) {
            new Zenoss.HideFitDialog({
                id: 'sequenceDialog',
                title: _t('Sequence'),
                layout: 'fit',
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
                        uids = Ext.Array.pluck(Ext.Array.pluck(records, 'data'), 'uid');
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
