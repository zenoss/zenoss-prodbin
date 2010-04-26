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
        return true;
    };

    // function that gets run when the user clicks on a node in the tree
    zs.treeSelectionChangeHandler = function(sm, node) {
        if (node) {
            Ext.getCmp('serviceForm').setContext(node.attributes.uid);
            Ext.getCmp('navGrid').setContext(node.attributes.uid);

            var isRoot = node == Ext.getCmp('navTree').root;
            Ext.getCmp('footer_bar').buttonDelete.setDisabled(isRoot);
        }
    };

    var selModel = new Ext.tree.DefaultSelectionModel({
        listeners: {
            beforeselect: zs.treeBeforeSelectHandler,
            selectionchange: zs.treeSelectionChangeHandler
        }
    });

    var ServiceTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {
        constructor: function(config) {
            Ext.applyIf(config, {
                id: 'navTree',
                flex: 1,
                searchField: false,
                directFn: Zenoss.remote.ServiceRouter.getOrganizerTree,
                router: Zenoss.remote.ServiceRouter,
                selModel: selModel,
                selectRootOnLoad: true,
                enableDD: true,
                ddGroup: 'serviceDragDrop',
                ddAppendOnly: true,
                listeners: {
                    beforenodedrop: {
                        fn: this.onBeforeNodeDrop,
                        scope: this
                    }
                }
            });
            ServiceTreePanel.superclass.constructor.call(this, config);
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
            Zenoss.remote.ServiceRouter.moveServices(
                {
                    sourceUids: sourceUids, 
                    targetUid: targetUid
                },
                this.moveServicesCallback, 
                this);
        },
        moveServicesCallback: function() {
            this.getRootNode().reload(this.rootNodeReloadCallback, this);
        },
        rootNodeReloadCallback: function() {
            this.getRootNode().select();
            this.getRootNode().expand(true);
        }
    });
    Ext.reg('servicetreepanel', ServiceTreePanel);

})();
