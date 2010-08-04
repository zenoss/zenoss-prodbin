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

Ext.onReady(function(){

var router, treeId, dataSourcesId, thresholdsId, graphsId,
    beforeselectHandler, updateDataSources, updateThresholds, updateGraphs,
    selectionchangeHandler, selModel, footerBar, override, overrideHtml1,
    overrideHtml2, showOverrideDialog, resetCombo, addTemplateDialogConfig,
    addToZenPack, currentView;
    
Ext.ns('Zenoss', 'Zenoss.templates');
router = Zenoss.remote.TemplateRouter;
treeId = 'templateTree';
dataSourcesId = 'dataSourceTreeGrid';
thresholdsId = Zenoss.templates.thresholdsId;
graphsId = 'graphGrid';
    
resetCombo = function(combo, uid) {
    combo.clearValue();
    combo.getStore().setBaseParam('uid', uid);
    delete combo.lastQuery;
    combo.doQuery(combo.allQuery, true);
};

/**
 * Returns which of the two views that the user has selected. Can be
 * either:
 * 1. "template" : the default view where nodes are templates and leaves are device classes
 * 2. "deviceClass" : leaves are templates and nodes are deviceClasses
 **/
function getCurrentView(){
    var currentView = Ext.util.Cookies.get('template_view');
    if (currentView) {
        return currentView;
    }
    currentView = 'template';
    Ext.util.Cookies.set('template_view', currentView, new Date().add(Date.MONTH, 1));
    return currentView;
}

/**
 * Will set the cookie for the default view. This will cause a page reload.
 **/
function setDefaultView(view) {
    var currentView = getCurrentView();
    if (currentView != view){
        Ext.util.Cookies.set('template_view', view, new Date().add(Date.MONTH, 1));
        window.location = "/zport/dmd/template";
    }    
}
    
function reloadTree(selectedId) {
    var tree = Ext.getCmp(treeId);
    if (selectedId){
        tree.getRootNode().reload(function() {
            tree.getRootNode().childNodes[0].expand();
            tree.selectByToken(selectedId);
        });
    }else{
        // select the first node
        tree.getRootNode().reload(function(){
            tree.getRootNode().childNodes[0].expand();
            tree.getRootNode().childNodes[0].childNodes[0].select();
        });
    }
}

beforeselectHandler = function(sm, node, oldNode) {
    return node.isLeaf();
};

updateDataSources = function(uid) {
    var panel, treeGrid, root;
    if ( ! Ext.getCmp(dataSourcesId) ) {
        panel = Ext.getCmp('center_detail_panel');
        panel.add({
            xtype: 'DataSourceTreeGrid'
        });
        treeGrid = Ext.getCmp(dataSourcesId);
        root = treeGrid.getRootNode();
        root.setId(uid);
        panel.doLayout();
    } else {
        // create a new async node since we may have had a dummy one
        root = Ext.getCmp(dataSourcesId).getRootNode();
        root.setId(uid);
        root.reload();
    }
};

updateThresholds = function(uid) {
    var panel, root, grid;
    panel = Ext.getCmp('top_detail_panel');

    if ( ! Ext.getCmp(thresholdsId) ) {
        panel.add({id: thresholdsId, xtype:'thresholddatagrid'});
        panel.doLayout();
    }
    Ext.getCmp(thresholdsId).getStore().load({
        params: {uid: uid}
    });
};

updateGraphs = function(uid) {
    var panel, root;
    panel = Ext.getCmp('bottom_detail_panel');
    if ( ! Ext.getCmp(graphsId) ) {
        panel.add({
            xtype: 'graphgrid',
            id: graphsId
        });
        panel.doLayout();
    }
    Ext.getCmp(graphsId).getStore().load({
        params: {uid: uid}
    });
};


selectionchangeHandler = function(sm, node) {
    if (node){
        updateDataSources(node.attributes.uid);
        updateThresholds(node.attributes.uid);
        updateGraphs(node.attributes.uid);
        // set the context for the id fields (they validate their id against this context)
        Zenoss.env.PARENT_CONTEXT = node.attributes.uid;
        // unfortunately because multiple templates exist on device class view we
        // have to track the history differently
        if (getCurrentView() == Zenoss.templates.templateView){
            Ext.History.add(treeId + Ext.History.DELIMITER + node.attributes.uid);   
        }else {
            Ext.History.add(treeId + Ext.History.DELIMITER + node.getPath());
        }        
    }

    // enable the footer bar buttons
    var footerBar = Ext.getCmp('footer_bar');
    footerBar.buttonContextMenu.setDisabled(!node);
    footerBar.buttonDelete.setDisabled(!node);
    footerBar.buttonAdd.setTooltip(_t('Add a monitoring template'));

    // disable/enable the add buttons
    Ext.getCmp(thresholdsId).addButton.setDisabled(!node);
    Ext.getCmp(graphsId).addButton.setDisabled(!node);
    Ext.getCmp(dataSourcesId).disableToolBarButtons(!node);
};

selModel = new Ext.tree.DefaultSelectionModel({
    listeners: {
        beforeselect: beforeselectHandler,
        selectionchange: selectionchangeHandler
    }
});

Ext.getCmp('master_panel').add({
    xtype: 'TemplateTreePanel',
    selModel: selModel,
    view: getCurrentView()
});

/**********************************************************************
 *
 * Edit Template Information
 *
 */

/**
 * Shows the edit template dialog and sends the form values back to the server.
 **/
function showEditTemplateDialog(response) {
    var config, dialog, handler,
        data = response.data,
        dirtyOnly = true;        

    // save function (also reloads the tree, in case we change the name)
    handler = function() {
        var values = Ext.getCmp('editTemplateDialog').editForm.getForm().getFieldValues(dirtyOnly);
        values.uid = data.uid;
        router.setInfo(values, function(response){
            reloadTree(response.data.uid);
        });
    };

    // form config
    config = {
        submitHandler: handler,
        id: 'editTemplateDialog',
        height: 300,
        title: _t('Edit Template Details'),
        items: [{
            xtype: 'textfield',
            name: 'newId',
            fieldLabel: _t('Name'),
            allowBlank: false,
            ref: 'templateName'
        },{
            xtype: 'textfield',
            name: 'targetPythonClass',
            fieldLabel: _t('Target Class'),
            allowBlank: true,
            ref: 'targetPythonClass'
        },{
            xtype: 'textarea',
            name: 'description',
            fieldLabel: _t('Description'),
            ref: 'description'
        }]
    };

    dialog = new Zenoss.SmartFormDialog(config);

    // set our form to monitor for errors
    dialog.editForm.startMonitoring();
    dialog.editForm.addListener('clientvalidation', function(formPanel, valid){
        var dialogWindow;
        dialogWindow = formPanel.refOwner;
        dialogWindow.buttonSubmit.setDisabled( !valid );
    });

    // populate the form
    dialog.editForm.templateName.setValue(data.name);
    dialog.editForm.targetPythonClass.setValue(data.targetPythonClass);
    dialog.editForm.description.setValue(data.description);
    dialog.show();
}

/**
 * Gets the selected template information from the server
 **/
function editSelectedTemplate() {
    var params = {
        uid: Ext.getCmp(treeId).getSelectionModel().getSelectedNode().attributes.uid
    };
    
    router.getInfo(params, showEditTemplateDialog);
}
/**********************************************************************
 *
 * Override Templates
 *
 */
override = function() {
    var node, params, callback;
    node = Ext.getCmp('templateTree').getSelectionModel().getSelectedNode();
    params = {
        uid: node.attributes.uid,
        targetUid: Ext.getCmp('targetCombo').getValue()
    };
    callback = function() {
        reloadTree();
    };
    router.copyTemplate(params, callback);
};

overrideHtml1 = function() {
    var html;
    html = _t('Do you wish to override the selected monitoring template? This will affect all devices using the monitoring template.');
    html += '<br/><br/>';
    return html;
};

overrideHtml2 = function() {
    var html;
    html = _t('If new thresholds, graphs, are added or removed, or datasources added or disabled, these will be saved to this local copy of template.');
    html += '<br/><br/>';
    html += _t('Override lets you save this template overriding the original template at the root level.');
    return html;
};

new Zenoss.HideFormDialog({
    id: 'overrideDialog',
    title: _t('Override'),
    width: 500,
    items: [
    {
        xtype: 'panel',
        border: false,
        html: overrideHtml1()
    }, {
        xtype: 'button',
        id: 'learnMore',
        border: false,
        text: _t('Learn more'),
        handler: function() {
            Ext.getCmp('learnMore').hide();
            Ext.getCmp('detailedExplanation').show();
        }
    }, {
        xtype: 'panel',
        id: 'detailedExplanation',
        border: false,
        html: overrideHtml2(),
        hidden: true
    }, {
        xtype: 'panel',
        border: false,
        html: '<br/>'
    }, {
        xtype: 'combo',
        id: 'targetCombo',
        fieldLabel: _t('Target'),
        quickTip: _t('The selected monitoring template will be copied to the specified device class or device.'),
        forceSelection: true,
        emptyText: _t('Select a target...'),
        minChars: 0,
        selectOnFocus: true,
        valueField: 'uid',
        displayField: 'label',
        typeAhead: true,
        allowBlank: false,
        width: 450,
        store: {
            xtype: 'directstore',
            directFn: router.getCopyTargets,
            fields: ['uid', 'label'],
            root: 'data'
        },
        listeners: {
            valid: function(){
                Ext.getCmp('overrideDialog').submit.enable();
            }
        }
    }],
    buttons: [
    {
        xtype: 'HideDialogButton',
        ref: '../submit',
        text: _t('Submit'),
        handler: function(button, event) {
            override();
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
});

showOverrideDialog = function() {
    var sm, uid, combo;
    sm = Ext.getCmp('templateTree').getSelectionModel();
    uid = sm.getSelectedNode().attributes.uid;
    Ext.getCmp('overrideDialog').show();
    combo = Ext.getCmp('targetCombo');
    resetCombo(combo, uid);
    Ext.getCmp('overrideDialog').submit.disable();
};

function bindSelectedTemplateHere() {
    var node = Ext.getCmp(treeId).getSelectionModel().getSelectedNode(),
    remote = Zenoss.remote.DeviceRouter,
    callback, path,
    params, uid;
    
    if (getCurrentView() == Zenoss.templates.deviceClassView) {
        uid = node.parentNode.attributes.uid;
        path = node.getPath();
    }else {
        // template view
        uid = node.attributes.uid.replace(/rrdTemplates\/(.)*$/, '');
        path = node.attributes.uid;
    }
    
    callback = function(response){
        reloadTree(path);
    };
    params = {
        uid: uid,
        templateUid: node.attributes.uid
    };
    remote.bindOrUnbindTemplate(params, callback);
}

                
/**********************************************************************
 *
 * Footer Bar
 *
 */
addTemplateDialogConfig = {
    title: _t('Add Template'),
    id: 'addNewTemplateDialog',
    height: 250,
    width: 350,
    listeners: {
        show: function() {
            var cmp = Ext.getCmp('addNewTemplateDialog');
            // completely reload the combobox every time
            // we show the dialog
            cmp.comboBox.setValue(null);
            cmp.comboBox.store.setBaseParam('query', '');
            cmp.comboBox.store.load();
        }
    },
    items: [{
        xtype: 'textfield',
        name: 'id',
        fieldLabel: _t('Name'),
        allowBlank: false
    }, {
        xtype: 'combo',
        fieldLabel: _t('Template Path'),
        forceSelection: true,
        emptyText: _t('Select a template path...'),
        minChars: 0,
        ref: '../comboBox',
        selectOnFocus: true,
        typeAhead: true,
        resizable: true,
        displayField: 'label',
        valueField: 'uid',
        name: 'targetUid',
        store: {
            xtype: 'directstore',
            ref:'store',
            directFn: router.getAddTemplateTargets,
            fields: ['uid', 'label'],
            root: 'data'
        }
    }]
};

/**********************************************************************
 *
 * Add to zenpack
 *
 */
addToZenPack = Ext.create({
    xtype:'AddToZenPackWindow'
});
function showAddToZenPackDialog() {
    var tree = Ext.getCmp(treeId),
    win = addToZenPack;
    win.target = tree.getSelectionModel().getSelectedNode().attributes.uid;
    win.show();
}

footerBar = Ext.getCmp('footer_bar');
Zenoss.footerHelper(_t('Monitoring Template'),
                    footerBar, {
                        hasOrganizers: false,
                        addToZenPack: false,
                        customAddDialog: addTemplateDialogConfig
                    });

footerBar.buttonContextMenu.menu.add({
    text: _t('View and Edit Details'),
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    handler: editSelectedTemplate
},{
    xtype: 'menuitem',
    text: _t('Override Template'),
    handler: showOverrideDialog
},{
    xtype: 'menuitem',
    text: _t('Add to ZenPack'),
    handler: showAddToZenPackDialog
    
},{
    text: _t('Toggle Template Binding'),
    hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    handler: bindSelectedTemplateHere
});

footerBar.on('buttonClick', function(actionName, id, values) {
    var params, tree = Ext.getCmp(treeId);
    switch (actionName) {
        case 'addClass':
            params = {
                id: values.id,
                targetUid: values.targetUid
            };
            router.addTemplate(params, function(response) {
                reloadTree(response.nodeConfig.uid);
                tree.clearFilter();
            });
        break;
        case 'delete':
            params = {
                uid: Ext.getCmp(treeId).getSelectionModel().getSelectedNode().attributes.uid
            };
            router.deleteTemplate(params,
            function(){
                reloadTree();
                tree.clearFilter();
                footerBar.buttonDelete.setDisabled(true);
                footerBar.buttonContextMenu.setDisabled(true);
            });
        break;
        default:
        break;
    }
});

/**
 * Add the view buttons
 **/
footerBar.add([{
    xtype: 'label',
    text: _t('Group By: ')
    },' ',{
    xtype: 'button',
    enableToggle: true,
    toggleGroup: 'templateView',
    pressed: getCurrentView() == Zenoss.templates.templateView,
    text: _t('Template'),
    toggleHandler: function(button, state) {
        if (state) {
            setDefaultView(Zenoss.templates.templateView);
        } else {
            // stay pressed, but don't do anything
            this.toggle(true, true);
        }
        
    }
},{
    xtype: 'button',
    enableToggle: true,
    pressed: getCurrentView() == Zenoss.templates.deviceClassView,
    toggleGroup: 'templateView',
    text: _t('Device Class'),
    toggleHandler: function(button, state) {
        if (state) {
            setDefaultView(Zenoss.templates.deviceClassView);
        } else {
            // stay pressed, but don't do anything
            this.toggle(true, true);
        }      
    }
}]);


footerBar.add(['-',{
    xtype: 'label',
    text: _t('Bound:')
},{
    xtype: 'label',        
    ctCls: 'x-tree-node-icon tree-template-icon-bound-span'
},' ',' ',{
    xtype: 'label',
    text: _t('Component:')        
},{
    xtype: 'label',
    ctCls: 'x-tree-node-icon tree-template-icon-component-span'
}
]);



                
}); // Ext.onReady
