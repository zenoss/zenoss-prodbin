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

(function(){

var router, dataSourcesId, graphsId, resetCombo,  
    addMetricToGraph, showAddToGraphDialog, editDataSourcesId, treeId, dataSourceMenu;

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
    callback = function(provider, response) {
        Ext.getCmp(graphsId).getStore().reload();
    };
    router.addDataPointToGraph(params, callback);
};

Zenoss.GraphStore = Ext.extend(Ext.data.DirectStore, {
    constructor: function(config) {
        Ext.applyIf(config, {
            xtype: 'directstore',
            directFn: router.getGraphs,
            idProperty: 'uid',
            fields: ['uid', 'name', 'graphPoints', 'units', 'height', 'width',
                     'sequence']
        });
        Zenoss.GraphStore.superclass.constructor.call(this, config);
    }
});
Ext.reg('graphstore', Zenoss.GraphStore);

new Zenoss.HideFormDialog({
    id: 'addToGraphDialog',
    title: _t('Add Data Point to Graph'),
    items: [
    {
        xtype: 'panel',
        id: 'addToGraphMetricPanel',
        border: false
    }, {
        xtype: 'combo',
        id: 'graphCombo',
        fieldLabel: _t('Graph'),
        displayField: 'name',
        valueField: 'uid',
        forceSelection: true,
        minChars: 999, // only do an all query
        triggerAction: 'all',
        emptyText: 'Select a graph...',
        selectOnFocus: true,
        store: {xtype: 'graphstore'},
        listeners: {select: function(){
            Ext.getCmp('addToGraphDialog').submit.enable();
        }}
    }],
    buttons: [
    {
        xtype: 'HideDialogButton',
        ref: '../submit',
        text: _t('Submit'),
        disabled: true,
        handler: function(button, event) {
            var node, datapointUid, graphUid;
            node = Ext.getCmp(dataSourcesId).getSelectionModel().getSelectedNode();
            datapointUid = node.attributes.uid;
            graphUid = Ext.getCmp('graphCombo').getValue();
            addMetricToGraph(datapointUid, graphUid);
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
});

showAddToGraphDialog = function() {
    var smTemplate, templateUid, smDataSource, 
        nodeDataSource, metricName, html, combo;
    smTemplate = Ext.getCmp('templateTree').getSelectionModel();
    templateUid = smTemplate.getSelectedNode().attributes.uid;
    smDataSource = Ext.getCmp(dataSourcesId).getSelectionModel();
    nodeDataSource = smDataSource.getSelectedNode();
    if ( nodeDataSource && nodeDataSource.isLeaf() ) {
        metricName = nodeDataSource.attributes.name;
        html = '<div>Data Point</div>';
        html += '<div>' + metricName + '</div><br/>';
        Ext.getCmp('addToGraphDialog').show();
        Ext.getCmp('addToGraphMetricPanel').body.update(html);
        combo = Ext.getCmp('graphCombo');
        resetCombo(combo, templateUid);
        Ext.getCmp('addToGraphDialog').submit.disable();
    } else {
        Ext.Msg.alert('Error', 'You must select a Data Point.');
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
function refreshDataSourceGrid() {
    var grid = Ext.getCmp(dataSourcesId);
    Ext.getCmp('addDataPointDialog').hide();
    Ext.getCmp('addDataSourceDialog').hide();
    return grid.getRootNode().reload();
}

/**
 * Gets the DataPoint name from the dialog and sends it to the server
 **/
function saveDataPoint() {
    var grid = Ext.getCmp(dataSourcesId),
        selectedNode = grid.getSelectionModel().getSelectedNode(),
        parameters;

    // if we have a datapoint, find the datasource associated with it
    if (selectedNode.attributes.leaf) {
        selectedNode = selectedNode.parentNode;
    }
    
    parameters = {
        name: Ext.getCmp('metricName').getValue(),
        dataSourceUid: selectedNode.attributes.uid
    };
    return router.addDataPoint(parameters, refreshDataSourceGrid);
                              
}
     
/**
 * Add Data Point Dialog Configuration
 **/
new Ext.Window({
        id: 'addDataPointDialog',
        title: _t('Add Data Point'),
        height: 160,
        width: 310,
        plain: true,
        modal: true,
        
        closeAction: 'hide',
        listeners: {
            hide: function() {
                Ext.getCmp('metricName').setValue(null);
                Ext.getCmp('metricName').clearInvalid();
            }
        },
        items:{
            xtype: 'form',
            border: false,
            buttonAlign: 'left',
            monitorValid: true,
            items: [{                       
                xtype: 'idfield',
                id: 'metricName',
                fieldLabel: _t('Name'),
                allowBlank: false,
                blankText: _t('Name is a required field')
                   }],
            buttons: [{
                    xtype: 'button',
                    text: _t('Submit'),
                    formBind: true,
                    handler: saveDataPoint
                }, {
                    xtype: 'button',
                    text: _t('Cancel'),
                    handler: function() {
                        Ext.getCmp('addDataPointDialog').hide();
                    }
                }]
            
        }
            
    }
);
     
/**
 * Displays the Add Data Point dialog and saves the inputted infomation
 * back to the server
 **/
function showAddDataPointDialog() {
    var grid = Ext.getCmp(dataSourcesId),
        selectedNode = grid.getSelectionModel().getSelectedNode();
    
    // make sure they selected a node
    if (!selectedNode) {
        Ext.Msg.alert(_t('Error'), _t('You must select data source'));
        return; 
    }
    
    // display the name dialog
    Ext.getCmp('addDataPointDialog').show();
}
     
/**********************************************************************
 *
 * Add Data Source
 *
 */
     
/**
 * Gets the info from the Add Datasource dialog and sends it to the server
 **/
function saveDataSource() {
    var grid = Ext.getCmp(treeId),
        selectedNode = grid.getSelectionModel().getSelectedNode(),    
        parameters = {
            name: Ext.getCmp('dataSourceName').getValue(),
            type: Ext.getCmp('dataSourceTypeCombo').getValue(),
            templateUid: selectedNode.attributes.uid
        };
    return router.addDataSource(parameters, refreshDataSourceGrid);
}
     
new Ext.Window({
        id: 'addDataSourceDialog',
        title: _t('Add Data Source'),
        height: 160,
        width: 310,
        modal: true,
        plain: true,
        closeAction: 'hide',
        buttonAlight: 'left',
        listeners: {
            hide: function() {
                Ext.getCmp('dataSourceTypeCombo').setValue('SNMP');
                Ext.getCmp('dataSourceName').setValue('');
                Ext.getCmp('dataSourceName').clearInvalid();
            }
        },
        items:{
            xtype:'form',
            border: false,
            buttonAlign: 'left',
            monitorValid: true,
            items:[{
            xtype: 'idfield',
            id: 'dataSourceName',
            fieldLabel: _t('Name'),
            allowBlank: false,
            blankText: _t('Name is a required field')           
          },
          {
            xtype: 'combo',
            id: 'dataSourceTypeCombo',
            displayField: 'type',
            fieldLabel: _t('Type'),
            editable: false,
            forceSelection: true,
            autoSelect: true,
            value: 'SNMP',
            selectOnFocus: true,
            triggerAction: 'all',
            store:  new Ext.data.DirectStore({
                fields: ['type'],
                root: 'data',
                directFn: router.getDataSourceTypes
            })
        }],
        buttons:[{
            xtype: 'button',
            text: _t('Submit'),
            formBind: true,
            handler: saveDataSource
        },{
            xtype: 'button',
            text: _t('Cancel'),
            handler: function () {
                Ext.getCmp('addDataSourceDialog').hide();
            }
        }]} 
});
     
/**
 * Shows the Add Data Source dialog and saves the inputted information
 * back to the server
 **/
function showAddDataSourceDialog() {
    var cmp = Ext.getCmp(treeId),
        selectedNode = cmp.getSelectionModel().getSelectedNode();
    
    // make sure they selected a node
    if (!selectedNode) {
        Ext.Msg.alert(_t('Error'), _t('You must select a template'));
        return; 
    }
    // clear the entries (all of our forms are blank when you load them)
    Ext.getCmp('addDataSourceDialog').show();    
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
        name = getSelectedDataSourceOrPoint().attributes.name;
        html = String.format(msg, name);

        // show the dialog
        dialog = Ext.getCmp('deleteDataSourceDialog');
        dialog.show();
        dialog.getComponent('message').update(html);
    }else{
        Ext.Msg.alert(_t('Error'), _t('You must select a Data Source or Data Point.'));
    }
}

new Zenoss.MessageDialog({
    id: 'deleteDataSourceDialog',
    title: _t('Delete'),
    // msg is generated dynamically
    okHandler: function(){
        var params;
        params = {
            uid: getSelectedDataSourceOrPoint().id
        };
        
        // data points are always leafs
        if (getSelectedDataSourceOrPoint().leaf) {
            router.deleteDataPoint(params, refreshDataSourceGrid);  
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
    var dialog = Ext.getCmp('editDataSources');
    
    refreshDataSourceGrid();
        
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
        win, testDevice, data;
    
    testDevice = values.testDevice;
    // turn values into a GET string
    data = Ext.urlEncode(values);
    
    win = new Zenoss.CommandWindow({
        uids: testDevice,
        panel: 'panel',
        title: _t('Test Data Source'),
        autoLoad: {
            url: values.uid + '/test_datasource?' + data
        }
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
    var aliases = Ext.getCmp(editDataSourcesId).findByType('alias'),
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
        attributes,
        isDataPoint = false,
        params;
    
    // make sure they selected something
    if (!selectedNode) {
        Ext.Msg.alert(_t('Error'), _t('You must select a data source or data point.'));
        return;
    }
    attributes = selectedNode.attributes;
    
    // find out if we are editing a datasource or a datapoint
    if (attributes.leaf) {
        isDataPoint = true;
    }
    
    // parameters for the router call    
    params = {
        uid: attributes.uid  
    };
    
    // callback for the router request
    function displayEditDialog(response) {
        var win,
        config = {};
        
        config.record = response.record;
        config.items = response.form;
        config.xtype = "datasourceeditdialog";
        config.id = editDataSourcesId;
        config.isDataPoint = isDataPoint;
        config.title = _t('Edit Data Source');
        config.directFn = router.setInfo;
        config.width = 800;
        if (isDataPoint) {
            config.title = _t('Edit Data Point');
            config.directFn = submitDataPointForm;
            config.singleColumn = true;
        }else if (config.record.testable){
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
                    name: 'testDevice'
                },{
                    xtype: 'hidden',
                    name: 'uid',
                    value: response.record.id
                },{
                    xtype: 'button',
                    text: _t('Test'),
                    handler: testDataSource
                }]});
         
        }
        
        config.saveHandler = closeEditDialog;
        win = Ext.create(config);
        win.show();
    }
    
    // get the details
    if (isDataPoint) {
        router.getDataPointDetails(params, displayEditDialog);
    }else{
        router.getDataSourceDetails(params, displayEditDialog);
    }
}

dataSourceMenu = new Ext.menu.Menu({
    id: 'dataSourceMenu',
    items: [{
        xtype: 'menuitem',
        text: _t('Add Data Point To Graph'),
        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
        handler: showAddToGraphDialog
    },{
        xtype: 'menuitem',
        text: _t('Add Data Point'),
        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
        handler: showAddDataPointDialog
    },{
        xtype: 'menuitem',
        text: _t('View and Edit Details'),
        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
        handler: editDataSourceOrPoint
    }]
});
     
/**
 * @class Zenoss.DataSourceTreeGrid
 * @extends Ext.ux.tree.TreeGrid
 * @constructor
 */
Zenoss.DataSourceTreeGrid = Ext.extend(Ext.ux.tree.TreeGrid, {

    constructor: function(config) {
        Ext.applyIf(config, {
            border: false,
            useArrows: true,
            cls: 'x-tree-noicon',
            id: dataSourcesId,
            title: _t('Data Sources'),
            listeners: {
                // when they doubleclick we will open up the tree and
                // display the dialog
                beforedblclick: editDataSourceOrPoint                
            },
            loader: new Ext.ux.tree.TreeGridLoader({
                directFn: router.getDataSources
            }),
            tbar: [{
                    xtype: 'button',
                    iconCls: 'add',
                    id:'datasourceAddButton',
                    handler: showAddDataSourceDialog,
                    listeners: {
                        render: function() {
                            Zenoss.registerTooltipFor('datasourceAddButton');
                        }
                    }
            }, {
                xtype: 'button',
                iconCls: 'delete',
                id: 'datasourceDeleteButton',
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('datasourceDeleteButton');
                    }
                },
                handler: showDeleteDataSourceDialog
            },{
                xtype: 'button',
                id: 'datasourceEditButton',
                iconCls: 'customize',
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('datasourceEditButton');
                    }
                },
                menu: 'dataSourceMenu'
            }],
            columns: [
                {
                    id: 'name',
                    dataIndex: 'name',
                    header: 'Data Points by Data Source',
                    width: 250
                }, {
                    dataIndex: 'source',
                    header: 'Source',
                    width: 250
                }, {
                    dataIndex: 'enabled',
                    header: 'Enabled',
                    width: 40
                }, {
                    dataIndex: 'type',
                    header: 'Type',
                    width: 90
                }
            ]
        });
        Zenoss.DataSourceTreeGrid.superclass.constructor.call(this, config);
        
    }
    
});

Ext.reg('DataSourceTreeGrid', Zenoss.DataSourceTreeGrid);

})();
