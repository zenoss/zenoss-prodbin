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

    var zs = Ext.ns('Zenoss.Service.Nav');

    /**********************************************************************
    *
    * Tree Navigation Functionality
    *
    */

    zs.getSelectedOrganizer = function() {
        var tree, selected;
        tree = Ext.getCmp('navTree');
        selected = tree.getSelectionModel().getSelectedNode();
        if ( ! selected ) {
            // No node is really selected (a ServiceClass is selected in the 
            // navGrid). Find the node that had the selected css class added
            // to it when the ServiceClass was selected
            tree.getRootNode().cascade(function(node){
                // TreeNodeUI delegates addClass and removeClass to it's
                // elNode, but not hasClass (so this gets ugly)
                var wrap = node.getUI().getEl();
                var elNode = wrap.childNodes[0];
                if ( Ext.fly(elNode).hasClass('x-tree-selected') ) {
                    selected = node;
                    return false;
                }
            });
        }
        return selected;
    };

    zs.treeBeforeSelectHandler = function(sm, node, oldNode) {
        var form = Ext.getCmp('serviceForm').getForm();
        if ( form.isDirty() ) {
            Ext.MessageBox.show({
                title: _t('Unsaved Data'),
                msg: _t('The changes made in the form will be lost.'),
                fn: function(buttonid){
                    if (buttonid=='ok') {
                        form.reset();
                        node.select();
                    }
                },
                buttons: Ext.MessageBox.OKCANCEL
            });
            return false;
        }
        Ext.getCmp('navTree').getRootNode().cascade(function(node) {
            node.getUI().removeClass('x-tree-selected');
        });
        return true;
    };

    // function that gets run when the user clicks on a node in the tree
    zs.treeSelectionChangeHandler = function(sm, node) {
        var oldToken, newToken, token, remainder, remainderParts, isRoot;
        if (node) {
            Ext.getCmp('serviceForm').setContext(node.attributes.uid);
            Ext.getCmp('detail_panel').detailCardPanel.setContext(node.attributes.uid);
            Zenoss.env.PARENT_CONTEXT = node.attributes.uid;
            
            oldToken = unescape(Ext.History.getToken());
            newToken = 'navTree' + Ext.History.DELIMITER + node.id;
            if ( oldToken.indexOf(newToken + '.serviceclasses.') !== 0 ) {
                Ext.History.add(newToken);
                token = newToken;
            } else {
                token = oldToken;
            }

            Ext.getCmp('navGrid').getSelectionModel().clearSelections();
            Ext.getCmp('navGrid').getView().contextUid = node.attributes.uid;

            if (token) {
                remainder = token.split(Ext.History.DELIMITER)[1];
                if ( remainder ) {
                    remainderParts = remainder.split('.serviceclasses.');
                    if ( remainderParts[1] ) {
                        Ext.getCmp('navGrid').filterAndSelectRow(remainderParts[1]);
                    } else {
                        Ext.getCmp('name').setRawValue('');
                    }
                } 
            }            
            Ext.getCmp('navGrid').getView().updateLiveRows(Ext.getCmp('navGrid').getView().rowIndex, true, true, false);
            
            isRoot = node == Ext.getCmp('navTree').root;
            Ext.getCmp('footer_bar').buttonDelete.setDisabled(isRoot);
        }
    };

    var selModel = new Ext.tree.DefaultSelectionModel({
        listeners: {
            beforeselect: zs.treeBeforeSelectHandler,
            selectionchange: zs.treeSelectionChangeHandler
        }
    });

    zs.ServiceTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {
        constructor: function(config) {
            Ext.applyIf(config, {
                id: 'navTree',
                flex: 1,
                cls: 'x-tree-noicon',
                searchField: false,
                directFn: Zenoss.remote.ServiceRouter.getOrganizerTree,
                router: Zenoss.remote.ServiceRouter,
                selModel: selModel,
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
            zs.ServiceTreePanel.superclass.constructor.call(this, config);
        },
        onBeforeNodeDrop: function(dropEvent) {
            var sourceUids, targetUid;
            if (dropEvent.dropNode) {
                // moving a ServiceOrganizer into another ServiceOrganizer
                sourceUids = [dropEvent.dropNode.attributes.uid];
            } else {
                // moving a ServiceClass from grid into a ServiceOrganizer
                var data = Ext.pluck(dropEvent.data.selections, 'data');
                sourceUids = Ext.pluck(data, 'uid');
            }
            dropEvent.target.expand();
            targetUid = dropEvent.target.attributes.uid;
            targetId = dropEvent.target.attributes.id;
            Zenoss.remote.ServiceRouter.moveServices(
                {
                    sourceUids: sourceUids, 
                    targetUid: targetUid
                }, function () {
                    this.moveServicesCallback(targetId);
                },
                this);
        },
        moveServicesCallback: function(targetId) {
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
            var tokenParts, node, serviceClassName;
            token = unescape(token);
            tokenParts = token.split('.serviceclasses.');
            node = this.getNodeById(tokenParts[0]);
            if (node) {
                if ( node !== zs.getSelectedOrganizer() ) {
                    node.select();
                } else {
                    Ext.getCmp('navGrid').filterAndSelectRow(tokenParts[1]);
                }
            }
        },
        
        initEvents: function() {
            zs.ServiceTreePanel.superclass.initEvents.call(this);
            // don't add history token on click like HierarchyTreePanel does
            // this is handled in the selection model
            this.un('click', this.addHistoryToken, this);
        }

    });
    Ext.reg('servicetreepanel', zs.ServiceTreePanel);

})();
