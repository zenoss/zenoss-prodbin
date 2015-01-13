/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

var router, dataSourcesId, graphsId, resetCombo,
    addMetricToGraph, showAddToGraphDialog, editDataSourcesId, treeId,
    editingReSelectId;

Ext.ns('Zenoss');

router = Zenoss.remote.TemplateRouter;
dataSourcesId = 'dataSourceTreeGrid';
graphsId = 'graphGrid';
editDataSourcesId = "editDataSource";

// NOTE: this must match the tree id from the template.js file
treeId = 'templateTree';

/**
 *@returns the currently selected Data Source or Data Point, or none if nothing is selected
 **/
function getSelectedDataSourceOrPoint() {
    return Ext.getCmp(dataSourcesId).getSelectionModel().getSelectedNode();
}

resetCombo = function(combo, uid) {
    combo.clearValue();
    combo.getStore().setBaseParam('uid', uid);
    delete combo.lastQuery;
    combo.doQuery(combo.allQuery, true);
};

addMetricToGraph = function(dataPointUid, graphUid) {
    var params, callback;
    params = {dataPointUid: dataPointUid, graphUid: graphUid};
    router.addDataPointToGraph(params, callback);
};

Ext.define('Zenoss.GraphModel', {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        'uid', 'name', 'graphPoints', 'units', 'height', 'width',
             'sequence'
    ]
});

Ext.define("Zenoss.GraphStore", {
    extend:"Zenoss.NonPaginatedStore",
    alias: ['widget.graphstore'],
    constructor: function(config) {
        Ext.applyIf(config, {
            root: 'data',
            directFn: router.getGraphs,
            model: 'Zenoss.GraphModel'
        });
        this.callParent(arguments);
    }
});


showAddToGraphDialog = function(node, templateUid) {
    var nodeDataSource, metricName, html, combo;
    nodeDataSource = node;
    if ( nodeDataSource && nodeDataSource.isLeaf() ) {
        metricName = nodeDataSource.data.name;
        html = '<div>Data Point</div>';
        html += '<div>' + metricName + '</div><br/>';

        Ext.create('Zenoss.dialog.BaseWindow', {
            id: 'addToGraphDialog',
            width: 400,
            height: 250,
            title: _t('Add Data Point to Graph'),
            items: [
                {
                    xtype: 'panel',
                    id: 'addToGraphMetricPanel'
                }, {
                    xtype: 'combo',
                    id: 'graphCombo',
                    fieldLabel: _t('Graph'),
                    displayField: 'name',
                    valueField: 'uid',
                    width:300,
                    minChars: 999, // only do an all query
                    resizeable: true,
                    editable: false,
                    emptyText: 'Select a graph...',
                    store: new Zenoss.GraphStore({}),
                    listeners: {select: function(){
                        Ext.getCmp('addToGraphDialog').submit.enable();
                    }}
                }],
            buttons: [
                {
                    xtype: 'DialogButton',
                    ref: '../submit',
                    text: _t('Submit'),
                    disabled: true,
                    handler: function() {
                        var node, datapointUid, graphUid;
                        node = Ext.getCmp(dataSourcesId).getSelectionModel().getSelectedNode();
                        datapointUid = node.data.uid;
                        graphUid = Ext.getCmp('graphCombo').getValue();
                        addMetricToGraph(datapointUid, graphUid);
                    }
                }, {
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
        }).show();

        Ext.getCmp('addToGraphMetricPanel').body.update(html);
        combo = Ext.getCmp('graphCombo');
        resetCombo(combo, templateUid);
        Ext.getCmp('addToGraphDialog').submit.disable();
    } else {
        new Zenoss.dialog.ErrorDialog({message: _t('You must select a Data Point.')});
    }
};


/**********************************************************************
 *
 * Add Data Point
 *
 **/

/**
 * Causes the DataSources Grid to refresh from the server
 *
 **/
function refreshDataSourceGrid(selectedId) {
    var grid = Ext.getCmp(dataSourcesId);
    if (selectedId) {
        grid.refresh(function(){
            grid.getRootNode().cascade(function(node){
                if (node.data.id === selectedId) {
                    node.expand();
                    node.select();
                }
            });
        });
    }else{
        grid.refresh();
    }
}


Ext.define('Zenoss.templates.AddDataPointDialog', {
    alias: ['widget.addDpDialog'],
    extend: 'Zenoss.dialog.BaseWindow',
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            title: _t('Add Data Point'),
            height: 160,
            width: 310,
            listeners: {
                validitychange: function(form, isValid) {
                    this.ownerCt.query('DialogButton')[0].setDisabled(!isValid);
                }
            },
            items:{
                xtype: 'form',
                buttonAlign: 'left',
                items: [{
                    xtype: 'idfield',
                    ref: 'metricName',
                    fieldLabel: _t('Name'),
                    allowBlank: false,
                    blankText: _t('Name is a required field')
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    ref: '../submitNewDataPoint',
                    text: _t('Submit'),
                    formBind: true,
                    handler: function() {
                        var parameters = {
                            name: this.refOwner.metricName.getValue(),
                            dataSourceUid: config.dataSourceUid
                        };
                        return router.addDataPoint(parameters, function() {
                            if (config.selectedId) {
                                refreshDataSourceGrid(config.dataSourceId);
                            } else {
                                refreshDataSourceGrid();
                            }
                        });
                    }
                },{
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
            }
        });
        this.callParent(arguments);
    }
});

/**
 * Displays the Add Data Point dialog and saves the inputted infomation
 * back to the server
 **/
function showAddDataPointDialog() {
    var grid = Ext.getCmp(dataSourcesId),
        selectedNode = grid.getSelectionModel().getSelectedNode();

    // make sure they selected a node
    if (!selectedNode) {
        new Zenoss.dialog.ErrorDialog({message: _t('You must select a data source.')});
        return;
    }

    // display the name dialog
    Ext.create('Zenoss.templates.AddDataPointDialog', {
        dataSourceUid: selectedNode.data.uid,
        dataSourceId: selectedNode.data.id
    }).show();
}

/**********************************************************************
 *
 * Add Data Source
 *
 */

/**
 * @class Zenoss.templates.DataSourceTypeModel
 * @extends Ext.data.Model
 *
 **/
Ext.define('Zenoss.templates.DataSourceTypeModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'type',
    fields: [
        {name: 'type'}
    ]
});

Ext.define('Zenoss.templates.AddDataSourceDialog', {
    alias: ['widget.addDsDialog'],
    extend: 'Zenoss.dialog.BaseWindow',
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            title: _t('Add Data Source'),
            height: 180,
            width: 350,
            items:{
                xtype:'form',
                buttonAlign: 'left',
                listeners: {
                    validitychange: function(form, isValid) {
                        if (isValid) {
                            this.ownerCt.query('button')[0].enable();
                        } else {
                            this.ownerCt.query('button')[0].disable();
                        }
                    }
                },
                items:[{
                    xtype: 'idfield',
                    ref: 'dataSourceName',
                    fieldLabel: _t('Name'),
                    allowBlank: false,
                    blankText: _t('Name is a required field')
                }, {
                    xtype: 'combo',
                    ref: 'dataSourceTypeCombo',
                    allowBlank: false,
                    displayField: 'type',
                    fieldLabel: _t('Type'),
                    editable: false,
                    value: 'SNMP',
                    triggerAction: 'all',
                    store:  {
                        type: 'directcombo',
                        model: 'Zenoss.templates.DataSourceTypeModel',
                        root: 'data',
                        directFn: router.getDataSourceTypes
                    }
                }],
                buttons:[{
                    xtype: 'DialogButton',
                    ref: '../submitNewDataSource',
                    disabled: true,
                    text: _t('Submit'),
                    handler: function() {
                        var parameters = {
                            name: this.refOwner.dataSourceName.getValue(),
                            type: this.refOwner.dataSourceTypeCombo.getValue(),
                            templateUid: config.templateUid
                        };
                        return router.addDataSource(parameters, refreshDataSourceGrid);
                    }
                },Zenoss.dialog.CANCEL
                ]
            }
        });
        this.callParent(arguments);
    }
});

/**
 * Shows the Add Data Source dialog and saves the inputted information
 * back to the server
 **/
function showAddDataSourceDialog() {
    var cmp = Ext.getCmp(treeId),
        selectedNode = cmp.getSelectionModel().getSelectedNode(),
        templateUid;

    // make sure they selected a node
    if (!selectedNode) {
        new Zenoss.dialog.ErrorDialog({message: _t('You must select a template.')});
        return;
    }
    templateUid = selectedNode.data.uid;
    Ext.create('Zenoss.templates.AddDataSourceDialog', {templateUid: templateUid}).show();
}

/**********************************************************************
 *
 * Delete DataSource
 *
 */

/**
 * Creates the dynamic delete message and shows the dialog
 **/
function showDeleteDataSourceDialog() {
    var msg, name, html, dialog;
    if (getSelectedDataSourceOrPoint()) {
        // set up the custom delete message
        msg = _t("Are you sure you want to remove {0}? There is no undo.");
        name = getSelectedDataSourceOrPoint().data.name;
        html = Ext.String.format(msg, name);

        // show the dialog
        dialog = Ext.getCmp('deleteDataSourceDialog');
        dialog.setText(html);
        dialog.show();
    }else{
        new Zenoss.dialog.ErrorDialog({message: _t('You must select a Data Source or Data Point.')});
    }
}

new Zenoss.MessageDialog({
    id: 'deleteDataSourceDialog',
    title: _t('Delete'),
    // msg is generated dynamically
    okHandler: function(){
        var params, node = getSelectedDataSourceOrPoint(),
        selectedId, callback;
        params = {
            uid: getSelectedDataSourceOrPoint().get("uid")
        };
        callback = function() {
            refreshDataSourceGrid(selectedId);
        };
        // data points are always leafs
        if (getSelectedDataSourceOrPoint().data.leaf) {
            selectedId = node.parentNode.data.id;

            router.deleteDataPoint(params, callback);
        }else {
            router.deleteDataSource(params, refreshDataSourceGrid);
        }
    }
});

/**********************************************************************
 *
 * Edit DataSource/DataPoint
 *
 */

/**
 * Closes the edit dialog and updates the store of the datasources.
 * This is called after the router request to save the edit dialog
 **/
function closeEditDialog(response) {
    if (!response.success) {
        return;
    }
    var dialog = Ext.getCmp(editDataSourcesId);
    refreshDataSourceGrid(editingReSelectId);

    // hide the dialog
    if (dialog) {
        dialog.hide();
    }
}

/**
 * Event handler for when a user wants to test a datasource
 * against a specific device.
 **/
function testDataSource() {
    var cmp = Ext.getCmp(editDataSourcesId),
        values = cmp.editForm.form.getValues(),
        win, testDevice;

    testDevice = values.testDevice;

    win = new Zenoss.CommandWindow({
        uids: testDevice,
        title: _t('Test Data Source'),
        data: values,
        target: values.uid + '/test_datasource'
    });

    win.show();
}

/**
 * Used when we save the data grid, it needs to
 * explicitly get the "Alias" value and turn it into a
 * list before going back to the server
 **/
function submitDataPointForm (values, callback) {
    // will always have only one alias form
    var aliases = Ext.getCmp(editDataSourcesId).query('alias'),
        alias;
    // assert that we have one exactly one alias form
    if (aliases.length < 1) {
        throw "The DataPoint form does not have an alias field, it should have only one";
    }

    alias = aliases[0];
    values.aliases = alias.getValue();
    router.setInfo(values, callback);
}

/**
 * Event handler for editing a specific datasource or
 * datapoint.
 **/
function editDataSourceOrPoint() {
    var cmp = Ext.getCmp(dataSourcesId),
        selectedNode = cmp.getSelectionModel().getSelectedNode(),
        data,
        isDataPoint = false,
        params;

    // make sure they selected something
    if (!selectedNode) {
        new Zenoss.dialog.ErrorDialog({message: _t('You must select a Data Source or Data Point.')});
        return;
    }
    data = selectedNode.data;

    // find out if we are editing a datasource or a datapoint
    if (data.leaf) {
        isDataPoint = true;
        editingReSelectId = selectedNode.parentNode.data.id;
    }else{
        editingReSelectId = data.id;
    }

    // parameters for the router call
    params = {
        uid: data.uid
    };

    // callback for the router request
    function displayEditDialog(response) {
        var win,
        config = {};

        config.record = response.record;
        config.items = response.form;
        config.id = editDataSourcesId;
        config.isDataPoint = isDataPoint;
        config.title = _t('Edit Data Source');
        config.directFn = router.setInfo;
        config.width = 800;
        if (isDataPoint) {
            config.title = _t('Edit Data Point');
            config.directFn = submitDataPointForm;
            config.singleColumn = true;
        } else if (config.record.testable &&
                   Zenoss.Security.hasPermission('Change Device')){
            // add the test against device panel
            config.items.items.push({
                xtype:'panel',
                columnWidth: 0.5,
                baseCls: 'test-against-device',
                hidden: Zenoss.Security.doesNotHavePermission('Run Commands'),
                title: _t('Test Against a Device'),
                items:[{
                    xtype: 'textfield',
                    fieldLabel: _t('Device Name'),
                    id: 'testDevice',
                    width: 300,
                    name: 'testDevice'
                },{
                    xtype: 'hidden',
                    name: 'uid',
                    value: response.record.id
                },{
                    xtype: 'button',
                    text: _t('Test'),
                    id: 'testDeviceButton',
                    handler: testDataSource
                }]});

        }

        config.saveHandler = closeEditDialog;
        win = new Zenoss.form.DataSourceEditDialog(config);
        var cmdField = win.editForm.form.findField('commandTemplate');
        if (cmdField !== null) {
            cmdField.addListener('dirtychange', function() {
                Ext.getCmp('testDeviceButton').disable();
                var devField = Ext.getCmp('testDevice');
                devField.setValue(_t("Save and reopen this dialog to test."));
                devField.disable();
            });
        }
        win.show();
    }
    // get the details
    if (isDataPoint) {
        router.getDataPointDetails(params, displayEditDialog);
    }else{
        router.getDataSourceDetails(params, displayEditDialog);
    }
}


/**
 * @class Zenoss.templates.DataSourceModel
 * @extends Ext.data.Model
 * Field definitions for the datasource/datapoint grid
 **/
Ext.define('Zenoss.templates.DataSourceModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name: 'uid'},
        {name: 'name'},
        {name: 'source'},
        {name: 'enabled'},
        {name: 'type'}
    ]
});

/**
 * @class Zenoss.templates.DataSourceStore
 * @extend Ext.data.TreeStore
 * Direct store for loading datasources and datapoints
 */
Ext.define("Zenoss.templates.DataSourceStore", {
    extend: "Ext.data.TreeStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.templates.DataSourceModel',
            nodeParam: 'uid',
            remoteSort: false,
            proxy: {
                limitParam: undefined,
                startParam: undefined,
                pageParam: undefined,
                sortParam: undefined,
                type: 'direct',
                directFn: router.getDataSources,
                reader: {
                    root: 'data',
                    totalProperty: 'count'
                }
            }
        });
        this.callParent(arguments);
    }
});

/**
 * @class Zenoss.DataSourceTreeGrid
 * @extends Ext.Tree.Panel
 * @constructor
 */
Ext.define("Zenoss.DataSourceTreeGrid", {
    extend: "Ext.tree.Panel",
    alias: ['widget.DataSourceTreeGrid'],

    constructor: function(config) {
        var tbarItems = config.tbarItems || [],
            dsAddHandler = config.dsAddHandler || showAddDataSourceDialog,
            dsDelHandler = config.dsDelHandler || showDeleteDataSourceDialog,
            addToGraphHandler = config.addToGraphHandler || showAddToGraphDialog,
            dpAddHandler = config.dpAddHandler || showAddDataPointDialog,
            editEitherHandler = config.editEitherHandler || editDataSourceOrPoint,
            me = this;
            //dsDelHandler = config.dsDelHandler || showDeleteDataSourceDialog,
            //dsEditMenu = config.dsEditMenu || dataSourceMenu;
        Ext.applyIf(config, {
            useArrows: true,
            cls: 'x-tree-noicon',
            rootVisible: false,
            id: dataSourcesId,
            title: _t('Data Sources'),
            listeners: {
                // when they doubleclick we will open up the tree and
                // display the dialog
                beforeitemdblclick: editDataSourceOrPoint
            },
            store: Ext.create('Zenoss.templates.DataSourceStore', {}),
            tbar: tbarItems.concat([{
                    xtype: 'button',
                    iconCls: 'add',
                    id:'datasourceAddButton',
                    ref: '../addButton',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: dsAddHandler,
                    listeners: {
                        render: function() {
                            Zenoss.registerTooltipFor('datasourceAddButton');
                        }
                    }
            }, {
                xtype: 'button',
                iconCls: 'delete',
                ref: '../deleteButton',
                id: 'datasourceDeleteButton',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('datasourceDeleteButton');
                    }
                },
                handler: dsDelHandler
            },{
                xtype: 'button',
                id: 'datasourceEditButton',
                iconCls: 'customize',
                ref: '../customizeButton',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('datasourceEditButton');
                    }
                },
                menu: new Ext.menu.Menu({
                    items: [{
                        xtype: 'menuitem',
                        text: _t('Add Data Point To Graph'),
                        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        handler: function() {
                            var node = me.getSelectionModel().getSelectedNode();
                            addToGraphHandler(node, me.uid);
                        }
                    },{
                        xtype: 'menuitem',
                        text: _t('Add Data Point'),
                        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        handler: dpAddHandler
                    },{
                        xtype: 'menuitem',
                        text: _t('View and Edit Details'),
                        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        handler: editEitherHandler
                    }]
                })
            }]),
            columns: [{
                xtype: 'treecolumn', //this is so we know which column will show the tree
                text: 'Name',
                flex: 2,
                sortable: true,
                dataIndex: 'name'
            }, {
                dataIndex: 'source',
                flex: 1,
                header: 'Source',
                width: 250
            }, {
                dataIndex: 'enabled',
                header: 'Enabled',
                width: 60
            }, {
                dataIndex: 'type',
                header: 'Type',
                width: 90
            }],
            selModel: Ext.create('Zenoss.TreeSelectionModel', {
                mode: 'SINGLE'
            })
        });
        this.callParent(arguments);
    },
    disableToolBarButtons: function(bool) {
        this.addButton.setDisabled(bool && Zenoss.Security.hasPermission('Manage DMD'));
        this.deleteButton.setDisabled(bool && Zenoss.Security.hasPermission('Manage DMD'));
        this.customizeButton.setDisabled(bool && Zenoss.Security.hasPermission('Manage DMD'));
    },
    setContext: function(uid) {
        if (uid !== this.uid){
            this.uid = uid;
            this.refresh();
        }
    },
    refresh: function(callback, scope) {
        var root = this.getRootNode();
        root.setId(this.uid);
        root.data.uid = this.uid;
        root.uid = this.uid;
        if (callback) {
            this.getStore().load({
                callback: callback,
                scope: scope || this
            });
        }else {
            this.getStore().load();
        }

    }

});



})();
