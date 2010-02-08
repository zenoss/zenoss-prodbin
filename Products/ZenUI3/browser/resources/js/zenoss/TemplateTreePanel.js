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

function initTreeDialogs(tree) {

    new Zenoss.FormDialog({
        id: 'addTemplateDialog',
        title: _t('Add Monitoring Template'),
        items: {
            xtype: 'textfield',
            id: 'idTextfield',
            fieldLabel: _t('ID'),
            allowBlank: false
        },
        listeners: {
            'hide': function(treeDialog) {
                Ext.getCmp('idTextfield').setValue('');
            }
        },
        buttons: [
            {
                xtype: 'DialogButton',
                text: _t('Submit'),
                dialogId: 'addTemplateDialog',
                handler: function(button, event) {
                    var id = Ext.getCmp('idTextfield').getValue();
                    tree.addTemplate(id);
                }
            }, {
                xtype: 'DialogButton',
                text: _t('Cancel'),
                dialogId: 'addTemplateDialog'
            }
        ]
    });

    new Zenoss.MessageDialog({
        id: 'deleteNodeDialog',
        title: _t('Delete Tree Node'),
        message: _t('The selected node will be deleted.'),
        okHandler: function(){
            tree.deleteSelectedNode();
        }
    });

}

Ext.ns('Zenoss');

/**
 * @class Zenoss.TemplateTreePanel
 * @extends Ext.tree.TreePanel
 * @constructor
 */
Zenoss.TemplateTreePanel = Ext.extend(Ext.tree.TreePanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
        });
        Zenoss.TemplateTreePanel.superclass.constructor.call(this, config);
        initTreeDialogs(this);
        this.on('buttonClick', this.buttonClickHandler, this);
        this.getRootNode().on('expand', function(node){
            var firstChildNode, firstTemplate;
            firstChildNode = node.childNodes[0];
            firstChildNode.expand();
            firstTemplate = firstChildNode.childNodes[0];
            firstTemplate.select();
        });
    },
    
    buttonClickHandler: function(buttonId) {
        switch(buttonId) {
            case 'addButton':
                if (this.getRootNode().isSelected()) {
                    Ext.getCmp('addTemplateDialog').show();
                } else {
                    Ext.getCmp('addDeviceClassDialog').show();
                }
                break;
            case 'deleteButton':
                Ext.getCmp('deleteNodeDialog').show();
                break;
            default:
                break;
        }
    },
    
    addTemplate: function(id) {
        var selectedNode, parentNode, contextUid, params, tree, type;
        selectedNode = this.getSelectionModel().getSelectedNode();
        if (selectedNode.leaf) {
            parentNode = selectedNode.parentNode;
        } else {
            parentNode = selectedNode;
        }
        contextUid = parentNode.attributes.uid;
        type = 'template';
        params = {type: type, contextUid: contextUid, id: id};
        tree = this;
        function callback(provider, response) {
            var result, nodeConfig, node;
            result = response.result;
            if (result.success) {
                nodeConfig = response.result.nodeConfig;
                node = tree.getLoader().createNode(nodeConfig);
                parentNode.appendChild(node);
                node.select();
            } else {
                Ext.Msg.alert('Error', result.msg);
            }
        }
        this.router.addNode(params, callback);
    }

});

Ext.reg('TemplateTreePanel', Zenoss.TemplateTreePanel);

})();
