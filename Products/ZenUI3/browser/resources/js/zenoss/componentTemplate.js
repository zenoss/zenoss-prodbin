/*
  ###########################################################################
  #
  # This program is part of Zenoss Core, an open source monitoring platform.
  # Copyright (C) 2011, Zenoss Inc.
  #
  # This program is free software; you can redistribute it and/or modify it
  # under the terms of the GNU General Public License version 2 or (at your
  # option) any later version as published by the Free Software Foundation.
  #
  # For complete information please visit: http://www.zenoss.com/oss/
  #
  ###########################################################################
*/

(function(){
    var router = Zenoss.remote.TemplateRouter,
        ComponentTemplatePanel;

    function createLocalCopy(grid, templateName) {
        var uid = grid.refOwner.getCurrentUid(),
            params = {
                uid: uid,
                templateName: templateName
            };

        router.makeLocalRRDTemplate(params, function(){
            grid.getStore().reload();
        });
    }

    function deleteLocalCopy(grid, templateName) {
        var uid = grid.refOwner.getCurrentUid(),
            params = {
                uid: uid,
                templateName: templateName
            };
        router.removeLocalRRDTemplate(params, function(){
            grid.getStore().reload();
        });
    }

    function isLocalTemplate(contextUid, templateUid) {
        return templateUid.startswith(contextUid);
    }

    ComponentTemplatePanel = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                items: [{
                    layout: 'border',
                    defaults: {
                        border: false,
                        split: true
                    },
                    items:[{
                        region: 'west',
                        width: '65%',
                        xtype: 'grid',
                        ref: '../templates',
                        sm: new Ext.grid.RowSelectionModel ({
                            singleSelect: true,
                            listeners : {
                                rowselect: function (selectionModel, rowIndex, record ) {
                                    var thresholds = selectionModel.grid.refOwner.thresholds,
                                        grid = selectionModel.grid;
                                    thresholds.getStore().load({
                                        params: {uid: record.data.uid}
                                    });
                                    // toggle the delete local and copy local buttons
                                    if (isLocalTemplate(grid.refOwner.getCurrentUid(), record.data.uid)) {
                                        grid.deleteLocalCopyButton.enable();
                                        grid.createLocalCopyButton.disable();
                                    }else{
                                        grid.createLocalCopyButton.enable();
                                        grid.deleteLocalCopyButton.disable();
                                    }
                                    // enable the threshold add button
                                    thresholds.addButton.enable();
                                },
                                rowdeselect: function(selectionModel) {
                                    var thresholds = selectionModel.grid.refOwner.thresholds,
                                        grid = selectionModel.grid;
                                    thresholds.addButton.disable();

                                    // disable both local copy buttons
                                    grid.deleteLocalCopyButton.disable();
                                    grid.createLocalCopyButton.disable();
                                }
                            }
                        }),
                        tbar: [{
                            ref: '../createLocalCopyButton',
                            xtype: 'button',
                            disabled: true,
                            text: _t('Create Local Copy'),
                            handler: function(btn) {
                                var grid = btn.refOwner,
                                    row = grid.getSelectionModel().getSelected();
                                if (row) {
                                    createLocalCopy(grid, row.data.name);
                                }
                            }
                        },{
                            ref: '../deleteLocalCopyButton',
                            xtype: 'button',
                            text: _t('Delete Local Copy'),
                            disabled: true,
                            tooltip: _t('Delete the local copy of this template'),
                            handler: function(btn) {
                                var grid = btn.refOwner,
                                    row = grid.getSelectionModel().getSelected();
                                if (row) {
                                    // show a confirmation
                                    Ext.Msg.show({
                                        title: _t('Delete Copy'),
                                        msg: String.format(_t("Are you sure you want to delete the local copy of this template? There is no undo.")),
                                        buttons: Ext.Msg.OKCANCEL,
                                        fn: function(btn) {
                                            if (btn=="ok") {
                                                deleteLocalCopy(grid, row.data.name);
                                            } else {
                                                Ext.Msg.hide();
                                            }
                                        }
                                    });
                                }
                            }
                        }],
                        store: {
                            xtype: 'directstore',
                            root: 'data',
                            panel: this,
                            directFn: router.getObjTemplates,
                            fields: ['uid', 'name', 'description', 'definition'],
                            listeners: {
                                load: function(store) {
                                    store.panel.templates.getSelectionModel().selectFirstRow();
                                }
                            }
                        },
                        viewConfig: {
                            emptyText: _t('No Templates')
                        },
                        autoExpandColumn: 'description',
                        stripeRows: true,
                        columns: [{
                            dataIndex: 'name',
                            id: 'name',
                            header: _t('Name'),
                            renderer: function(name, idx, record) {
                                var uid = record.data.uid;
                                if (uid){
                                    return Zenoss.render.link(null, uid, name);
                                }
                                return name;
                            }
                        },{
                            dataIndex: 'description',
                            id: 'description',
                            header: _t('Description')
                        },{
                            minWidth: 200,
                            dataIndex: 'definition',
                            id: 'definition',
                            header: _t('Definition')
                        }]
                    },{
                        id: 'component_template_threshold',
                        region: 'center',
                        title: null,
                        xtype: 'thresholddatagrid',
                        ref: '../thresholds',
                        getTemplateUid: function() {
                            var templateGrid = this.refOwner.templates,
                                row = templateGrid.getSelectionModel().getSelected();
                            if (row) {
                                return row.data.uid;
                            }
                        },
                        tbarItems:[{
                            xtype: 'tbtext',
                            text: _t('Thresholds')
                        }, '-']
                    }]
                }]

            });
            ComponentTemplatePanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            var templateGrid = this.templates,
                store = templateGrid.getStore();
            store.setBaseParam('uid', uid);
            store.load();
            this._uid = uid;
            // disable unless until we select a template
            this.thresholds.addButton.disable();
        },
        getCurrentUid: function() {
            return this._uid;
        }
    });

    Ext.reg('componenttemplatepanel', ComponentTemplatePanel);

})();