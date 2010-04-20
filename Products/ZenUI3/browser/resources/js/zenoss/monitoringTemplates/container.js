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

Ext.ns('Zenoss', 'Zenoss.templates');

var REMOTE = Zenoss.remote.DeviceRouter;

Zenoss.templates.Container = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'border',
            border: false,
            defaults: {
                border: false,
                split: true
            },
            items: [{
                xtype: 'DataSourceTreeGrid',
                id: 'dataSourceTreeGrid',
                region: 'center',
                ref: 'dataSourceTreeGrid'
            }, {
                xtype: 'panel',
                layout: 'border',
                region: 'east',
                width: '35%',
                defaults: {
                    border: false,
                    split: true
                },
                items: [{
                    xtype: 'thresholddatagrid',
                    id: 'thresholdGrid',
                    ref: '../thresholdGrid',
                    region: 'north',
                    height: 300
                }, {
                    xtype: 'graphgrid',
                    id: 'graphGrid',
                    ref: '../graphGrid',
                    region: 'center'
                }]
            }]
        });
        Zenoss.templates.Container.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        this.updateTreeGrid(this.dataSourceTreeGrid, uid);
        this.updateGrid(this.thresholdGrid, uid);
        this.updateGrid(this.graphGrid, uid);
    },
    updateTreeGrid: function(treeGrid, uid){
        treeGrid.getRootNode().setId(uid);
        treeGrid.getRootNode().reload();
    },
    updateGrid: function(grid, uid) {
        grid.getStore().load({
            params: {uid: uid}
        });
    }
});
Ext.reg('templatecontainer', Zenoss.templates.Container);

Zenoss.BubblingSelectionModel = Ext.extend(Ext.tree.DefaultSelectionModel, {
    constructor: function(config) {
        Zenoss.BubblingSelectionModel.superclass.constructor.call(this, config);
        this.enableBubble('selectionchange');
        this.bubbleTarget = config.bubbleTarget;
    },
    getBubbleTarget: function() {
        return this.bubbleTarget;
    }
});

Zenoss.MonTemplateSelectionModel = Ext.extend(Zenoss.BubblingSelectionModel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            listeners: {
                beforeselect: function(sm, node) {
                    return node.isLeaf();
                }
            }
        });
        Zenoss.MonTemplateSelectionModel.superclass.constructor.call(this, config);
    }
});

Zenoss.templates.MonTemplateTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config){
        Ext.applyIf(config, {
            useArrows: true,
            border: false,
            cls: 'x-tree-noicon',
            selModel: new Zenoss.MonTemplateSelectionModel({
                bubbleTarget: config.bubbleTarget
            }),
            loader: {
                directFn: REMOTE.getTemplates,
                baseAttrs: {singleClickExpand: true}
            },
            root: {
                text: _t('Monitoring Templates')
            }
        });
        Zenoss.templates.MonTemplateTreePanel.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        if ( uid.match('^/zport/dmd/Devices') ) {
            this.show();
            this.setRootNode({
                nodeType: 'async',
                id: uid,
                text: _t('Monitoring Templates'),
                expanded: true
            });
        } else {
            this.hide();
        }
    },
    onSelectionChange: function(node) {
        var detail;
        if (node) {
            detail = Ext.getCmp(this.initialConfig.detailPanelId);
            if ( ! detail.items.containsKey('montemplate') ) {
                detail.add({
                    xtype: 'templatecontainer',
                    id: 'montemplate',
                    ref: 'montemplate'
                });
            }
            detail.montemplate.setContext(node.attributes.uid);
            detail.getLayout().setActiveItem('montemplate');
        }
    }
});
Ext.reg('montemplatetreepanel', Zenoss.templates.MonTemplateTreePanel);

Zenoss.BindTemplatesItemSelector = Ext.extend(Ext.ux.form.ItemSelector, {
        constructor: function(config) {
        Ext.applyIf(config, {
            imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
            drawUpIcon: false,
            drawDownIcon: false,
            drawTopIcon: false,
            drawBotIcon: false,
            dislplayField: 'id',
            valueField: 'id',
            multiselects: [{
                width: 250,
                height: 200,
                appendOnly: true,
                store: ['']
            },{
                width: 250,
                height: 200,
                appendOnly: true,
                store: ['']
            }]
        });
        Zenoss.BindTemplatesItemSelector.superclass.constructor.apply(this, arguments);
    },
    setContext: function(uid) {
        REMOTE.getUnboundTemplates({uid: uid}, function(provider, response){
            this.fromMultiselect.store.loadData(response.result.data);
        }, this);
        REMOTE.getBoundTemplates({uid: uid}, function(provider, response){
            this.toMultiselect.store.loadData(response.result.data);
        }, this);
    }
});
Ext.reg('bindtemplatesitemselector', Zenoss.BindTemplatesItemSelector);

Zenoss.BindTemplatesDialog = Ext.extend(Zenoss.HideFitDialog, {
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            title: _t('Bind Templates'),
            items: {
                xtype: 'bindtemplatesitemselector',
                ref: 'itemselector',
                context: config.context
            },
            listeners: {
                show: function() {
                    this.itemselector.setContext(this.context);
                }
            },
            buttons: [
            {
                xtype: 'HideDialogButton',
                text: _t('Save'),
                handler: function(){
                    var records, data, templateIds;
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        records = me.itemselector.toMultiselect.store.getRange();
                        data = Ext.pluck(records, 'data');
                        templateIds = Ext.pluck(data, 'text');
                        REMOTE.setBoundTemplates({
                            uid: me.context,
                            templateIds: templateIds
                        }, function (){
                            // refresh the template tree
                            var cmp = Ext.getCmp('templateTree');
                            if (cmp) {
                                cmp.getRootNode().reload();
                            }
                        });
                    }
                }
            }, {
                xtype: 'HideDialogButton',
                text: _t('Cancel')
            }]
        });
        Zenoss.BindTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});
Ext.reg('bindtemplatesdialog', Zenoss.BindTemplatesDialog);


Zenoss.OverrideTemplatesDialog = Ext.extend(Zenoss.HideFitDialog, {
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            title: _t('Override Templates'),
            listeners: {
                show: function() {
                    // completely reload the combobox every time
                    // we show the dialog
                    me.submit.setDisabled(true);
                    me.comboBox.setValue(null);
                    me.comboBox.store.setBaseParam('query', me.context);
                    me.comboBox.store.setBaseParam('uid', me.context);
                    me.comboBox.store.load();
                }
            },
            items: [{
                xtype: 'label',
                border: false,
                html: _t('Select the bound template you wish to override.')
            },{
                xtype: 'combo',
                forceSelection: true,
                emptyText: _t('Select a template...'),
                minChars: 0,
                ref: 'comboBox',
                selectOnFocus: true,
                valueField: 'uid',
                displayField: 'label',
                typeAhead: true,
                store: {
                    xtype: 'directstore',
                    ref:'store',
                    directFn: REMOTE.getOverridableTemplates,
                    fields: ['uid', 'label'],
                    root: 'data'
                },
                listeners: {
                    select: function(){
                        // disable submit if something is selected
                        me.submit.setDisabled(!me.comboBox.getValue());
                    }
                }
            }],
            buttons: [
            {
                xtype: 'HideDialogButton',
                ref: '../submit',
                disabled: true,
                text: _t('Submit'),
                handler: function(){
                    var records, data, templateIds;
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        var templateUid = me.comboBox.getValue();
                        Zenoss.remote.TemplateRouter.copyTemplate({
                            uid: templateUid,
                            targetUid: me.context
                        }, function (){
                            // refresh the template tree
                            var cmp = Ext.getCmp('templateTree');
                            if (cmp) {
                                cmp.getRootNode().reload();
                            }
                        });
                    }
                }
            }, {
                xtype: 'HideDialogButton',
                text: _t('Cancel')
            }]
        });
        Zenoss.OverrideTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});
Ext.reg('overridetemplatesdialog', Zenoss.OverrideTemplatesDialog);

})();
