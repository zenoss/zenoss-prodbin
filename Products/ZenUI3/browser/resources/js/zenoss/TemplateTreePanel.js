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

var router, treeId, initTreeDialogs;

router = Zenoss.remote.TemplateRouter;
treeId = 'templateTree';

initTreeDialogs = function(tree) {

    new Zenoss.HideFormDialog({
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
                xtype: 'HideDialogButton',
                text: _t('Submit'),
                handler: function(button, event) {
                    var id = Ext.getCmp('idTextfield').getValue();
                    tree.addTemplate(id);
                }
            }, {
                xtype: 'HideDialogButton',
                text: _t('Cancel')
            }
        ]
    });

    new Zenoss.MessageDialog({
        id: 'deleteNodeDialog',
        title: _t('Delete Tree Node'),
        message: _t('The selected node will be deleted.'),
        okHandler: function(){
            tree.deleteTemplate();
        }
    });

};

Ext.ns('Zenoss');

/**
 * @class Zenoss.TemplateTreePanel
 * @extends Ext.tree.TreePanel
 * @constructor
 */
Zenoss.TemplateTreePanel = Ext.extend(Ext.tree.TreePanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            id: treeId,
            title: _t('Monitoring Templates'),
            rootVisible: false,
            border: false,
            autoScroll: true,
            containerScroll: true,
            useArrows: true,
            cls: 'x-tree-noicon',
            loader: {
                directFn: router.getTemplates,
                baseAttrs: {singleClickExpand: true}
            },
            root: {
                nodeType: 'async',
                id: 'root'
            },
            listeners: {
                expandnode: function(node){
                    var container, firstTemplate;
                    if ( node === Ext.getCmp(treeId).getRootNode() ) {
                        container = node.childNodes[0];
                        container.expand();
                    } else {
                        container = node;
                    }
                    firstTemplate = container.childNodes[0];
                    firstTemplate.select();
                }
            }
        });
        Zenoss.TemplateTreePanel.superclass.constructor.call(this, config);
        initTreeDialogs(this);
        this.on('buttonClick', this.buttonClickHandler, this);
    },
    
    buttonClickHandler: function(buttonId) {
        switch(buttonId) {
            case 'addButton':
                Ext.getCmp('addTemplateDialog').show();
                break;
            case 'deleteButton':
                Ext.getCmp('deleteNodeDialog').show();
                break;
            default:
                break;
        }
    },
    
    addTemplate: function(id) {
        var rootNode, contextUid, params, tree, type;
        rootNode = this.getRootNode();
        contextUid = rootNode.attributes.uid;
        params = {contextUid: contextUid, id: id};
        tree = this;
        function callback(provider, response) {
            var result, nodeConfig, node, leaf;
            result = response.result;
            if (result.success) {
                nodeConfig = response.result.nodeConfig;
                node = tree.getLoader().createNode(nodeConfig);
                rootNode.appendChild(node);
                node.expand();
                leaf = node.childNodes[0];
                leaf.select();
            } else {
                Ext.Msg.alert('Error', result.msg);
            }
        }
        router.addTemplate(params, callback);
    },

    deleteTemplate: function() {
        var node, params, me;
        node = this.getSelectionModel().getSelectedNode();
        params = {uid: node.attributes.uid};
        me = this;
        function callback(provider, response) {
            me.getRootNode().reload();
        }
        router.deleteTemplate(params, callback);
    }

});

Ext.reg('TemplateTreePanel', Zenoss.TemplateTreePanel);

})();
