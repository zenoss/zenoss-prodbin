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



/**
 * The two default views
 **/
Ext.ns('Zenoss', 'Zenoss.templates');
Zenoss.templates.templateView = 'template';
Zenoss.templates.deviceClassView = 'deviceClass';


initTreeDialogs = function(tree) {

    new Zenoss.HideFormDialog({
        id: 'addTemplateDialog',
        title: _t('Add Monitoring Template'),
        items: {
            xtype: 'textfield',
            id: 'idTextfield',
            fieldLabel: _t('Name'),
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
        var view = config.view,
            directFn = router.getTemplates;
        if (view == Zenoss.templates.deviceClassView) {
            directFn = router.asyncGetTree;
        }
        this.view = view;
        config.listeners = config.listeners || {};
        Ext.applyIf(config.listeners, {
            contextmenu: Zenoss.treeContextMenu
        });
        Ext.applyIf(config, {
            id: treeId,
            rootVisible: false,
            border: false,
            autoScroll: true,
            containerScroll: true,
            useArrows: true,
            loadMask: true,
            cls: 'x-tree-noicon',
            loader: {
                directFn: directFn,
                baseAttrs: {singleClickExpand: true},
                getParams: function(node) {
                    return [node.attributes.uid];
                },
                listeners: {
                    beforeload: function(){
                        this.showLoadMask(true);
                    }.createDelegate(this),
                    load: function(){
                        this.showLoadMask(false);
                        var root = this.getRootNode();
                        root.expand();
                        if (root.childNodes.length) {
                            root.childNodes[0].expand();
                        }
                    }.createDelegate(this)
                }
            },
            root: {
                nodeType: 'async',
                id: 'root',
                uid: '/zport/dmd/Devices'
            },
            listeners: {
                scope: this,
                expandnode: this.onExpandnode
            }
        });
        Zenoss.TemplateTreePanel.superclass.constructor.call(this, config);
        initTreeDialogs(this);
        this.on('buttonClick', this.buttonClickHandler, this);
    },
    showLoadMask: function(bool) {
        if (!this.loadMask) { return; }
        var container = this.container;
        container._treeLoadMask = container._treeLoadMask || new Ext.LoadMask(this.container);
        var mask = container._treeLoadMask,
            _ = bool ? mask.show() : [mask.hide(), mask.disable()];
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
    },
    afterRender: function() {
        Zenoss.TemplateTreePanel.superclass.afterRender.call(this);

        var liveSearch = Zenoss.settings.enableLiveSearch,
            listeners = {
                scope: this,
                keypress: function(field, e) {

                    if (e.getKey() === e.ENTER) {

                        this.filterTree(field);
                    }
                }
            };

        if (liveSearch) {
            listeners.valid = this.filterTree;
        }
        // add the search text box
        this.add({
            xtype: 'searchfield',
            ref: 'searchField',
            enableKeyEvents: true,
            bodyStyle: {padding: 10},
            listeners: listeners
        });
    },

    clearFilter: function() {
        // use set raw value to not trigger listeners
        this.searchField.setRawValue('');
        this.hiddenPkgs = [];
    },
    createDeepLinkPath: function(node) {
        var path;
        if (this.view != Zenoss.templates.deviceClassView) {
            path = this.id + Ext.History.DELIMITER + node.attributes.uid;
        }else {
            path = this.id + Ext.History.DELIMITER + node.getPath();
        }

        return path;
    },
    filterTree: function(e) {
        var re,
            root = this.getRootNode(),
            text = e.getValue();

        // show all of our hidden nodes
        if (this.hiddenPkgs) {
            Ext.each(this.hiddenPkgs, function(node){node.ui.show();});
        }

        // de-select the selected node
        if (this.getSelectionModel().getSelectedNode()){
            this.getSelectionModel().getSelectedNode().unselect();
        }

        this.hiddenPkgs = [];
        if (!text) {
            // reset the tree to the initial state
            this.collapseAll();
            if (root) {
                root.expand();
                if (root.childNodes && root.childNodes.length > 0) {
                    root.childNodes[0].expand();
                }
            }
            return;
        }
        this.expandAll();

        // test every node against the Regular expression
        re = new RegExp(Ext.escapeRe(text), 'i');
        this.root.cascade(function(node){
            var attr = node.id, parentNode;
            if (!node.isRoot) {
                if (re.test(attr)) {
                    // if regex passes show our node and our parent
                    parentNode = node.parentNode;
                    while (parentNode) {
                        if (!parentNode.hidden) {
                            break;
                        }
                        parentNode.ui.show();
                        parentNode = parentNode.parentNode;
                    }
                    // the cascade is stopped on this branch
                    return false;
                } else {
                    node.ui.hide();
                    this.hiddenPkgs.push(node);
                }
            }
            // continue cascading down the tree from this node
            return true;
        }, this);
    },

    onExpandnode: function(node) {
        // select the first template when the base URL is accessed without a
        // history token and without a filter value
        if ( ! this.searchField.getValue() && ! Ext.History.getToken() ) {
            if ( node === this.getRootNode() ) {
                node.childNodes[0].expand();
            } else {
                node.childNodes[0].select();
            }
        }
    },
    selectByToken: function(uid) {
        if (this.view == Zenoss.templates.deviceClassView){
            this.selectPath(unescape(uid));
        }else{
            this.templateViewSelectByToken(uid);
        }
    },
    templateViewSelectByToken: function(uid) {
        // called on Ext.History change event (see HistoryManager.js)
        // convert uid to path and select the path
        // example uid: '/zport/dmd/Devices/Power/UPS/APC/rrdTemplates/Device'
        // example path: '/root/Device/Device..Power.UPS.APC'
        var templateSplit, pathParts, nameParts,
            templateName, dmdPath, path, deviceName;

        if (uid.search('/rrdTemplates/') != -1) {
            templateSplit = unescape(uid).split('/rrdTemplates/');
            pathParts = templateSplit[0].split('/');
            nameParts = templateSplit[1].split('/');
            templateName = nameParts[0];
        }else{
            // it is a template on a device
            pathParts = uid.replace('/devices/', '/').split('/');
            templateName = pathParts.pop();
        }

        if ( pathParts.length === 4 ) {
            // Defined at devices, special case, include 'Devices'
            dmdPath = 'Devices';
        } else {
            // all the DeviceClass names under Devices separated by dots
            dmdPath = pathParts.slice(4).join('.');
        }
        path = String.format('/root/{0}/{0}..{1}', templateName, dmdPath);
        this.selectPath(path);
    }

});

Ext.reg('TemplateTreePanel', Zenoss.TemplateTreePanel);

})();
