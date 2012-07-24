/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2011, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


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
            grid.refresh();
        });
    }

    function deleteLocalCopy(grid, templateName) {
        var uid = grid.refOwner.getCurrentUid(),
            params = {
                uid: uid,
                templateName: templateName
            };
        router.removeLocalRRDTemplate(params, function(){
            grid.refresh();
        });
    }

    function isLocalTemplate(contextUid, templateUid) {
        return templateUid.startswith(contextUid);
    }

    Ext.define("Zenoss.ComponentTemplatePanel", {
        alias:['widget.componenttemplatepanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            var me = this;
            config = config || {};
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                items: [{
                    layout: 'border',
                    defaults: {
                        split: true
                    },
                    items:[{
                        region: 'west',
                        width: '65%',
                        xtype: 'contextgridpanel',
                        ref: '../templates',
                        selModel: Ext.create('Zenoss.SingleRowSelectionModel', {
                            listeners : {
                                select: function (selectionModel, record, rowIndex) {
                                    var thresholds = me.thresholds,
                                        grid = me.templates;
                                    thresholds.setContext(record.get("uid"));
                                    // toggle the delete local and copy local buttons
                                    if (isLocalTemplate(grid.refOwner.getCurrentUid(), record.get("uid"))) {
                                        grid.deleteLocalCopyButton.enable();
                                        grid.createLocalCopyButton.disable();
                                    }else{
                                        grid.createLocalCopyButton.enable();
                                        grid.deleteLocalCopyButton.disable();
                                    }
                                    // enable the threshold add button
                                    thresholds.addButton.enable();
                                },
                                deselect: function(selectionModel) {
                                    var thresholds = me.thresholds,
                                        grid = me.templates;
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
                                 new Zenoss.dialog.SimpleMessageDialog({
                                        title: _t('Delete Copy'),
                                        message: Ext.String.format(_t("Are you sure you want to delete the local copy of this template? There is no undo.")),
                                        buttons: [{
                                            xtype: 'DialogButton',
                                            text: _t('OK'),
                                            handler: function() {
                                                deleteLocalCopy(grid, row.data.name);
                                            }
                                        }, {
                                            xtype: 'DialogButton',
                                            text: _t('Cancel')
                                        }]
                                    }).show();
                                }
                            }
                        }],
                        store: Ext.create('Zenoss.NonPaginatedStore', {
                            directFn: router.getObjTemplates,
                            fields: ['uid', 'name', 'description', 'definition'],
                            root: 'data',
                            listeners: {
                                load: function(store) {
                                    if (store.getCount()) {
                                        me.templates.getSelectionModel().selectRange(0, 0);
                                    }
                                    return true;
                                }
                            }
                        }),
                        viewConfig: {
                            emptyText: _t('No Templates'),
                            stripeRows: true
                        },
                        columns: [{
                            dataIndex: 'name',
                            header: _t('Name'),
                            width: 80,
                            renderer: function(name, idx, record) {
                                var uid = record.data.uid;
                                if (uid){
                                    return Zenoss.render.link(null, uid, name);
                                }
                                return name;
                            }
                        },{
                            dataIndex: 'description',
                            flex: 1,
                            header: _t('Description')
                        },{
                            minWidth: 200,
                            dataIndex: 'definition',
                            header: _t('Definition')
                        }]
                    },{
                        id: 'component_template_threshold',
                        region: 'center',
                        title: null,
                        stateId: 'component_template_thresholds',
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
            this.callParent(arguments);
        },
        setContext: function(uid) {
            var templateGrid = this.templates,
                store = templateGrid.getStore();
            templateGrid.setContext(uid);
            this._uid = uid;
            // disable unless until we select a template
            this.thresholds.addButton.disable();
        },
        getCurrentUid: function() {
            return this._uid;
        }
    });

})();
