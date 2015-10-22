/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.onReady(function() {

function renderDate(utcseconds) {
    if (utcseconds) {
        var d = new Date(0);
        d.setUTCSeconds(utcseconds);
        return d.readable(1);
    }
    return "--";
}

Ext.define("Zenoss.model.SupportBundle", {
    extend: 'Ext.data.Model',
    idProperty: 'filename',
    fields: [
        'fileName',
        'size',
        'sizeFormatted',
        'modDate',
        'modFateFormatted'
    ]
});

Ext.define('Zenoss.LegacyInnerPanelItem', {
    singleton: true,
    data: {
        layout: 'border',
        items: [{
            itemId: 'supportbundles',
            region: 'center',
            xtype: 'basegridpanel',
            uid: '/zport/dmd/support',
            store: Ext.create('Zenoss.DirectStore', {
                itemId: 'supportbundlestore',
                root: 'bundles',
                autoLoad: true,
                totalProperty: 'totalCount',
                pageSize: Zenoss.settings.supportBundlesGridBufferSize,
                initialSortColumn: 'modDate',
                initialSortDirection: 'DESC',
                totalProperty: 'totalCount',
                model: 'Zenoss.model.SupportBundle',
                directFn: Zenoss.remote.SupportRouter.getBundlesInfo,
                listeners: {
                    'load': function(store) {
                        store.loaded = true;
                    }
                }
            }),
            columns: [{
                id: 'fileName',
                dataIndex: 'fileName',
                header: _t('Filename'),
                flex: 6,
                sortable: true
            },{
                id: 'sizeFormatted',
                dataIndex: 'sizeFormatted',
                header: _t('Size'),
                flex: 1,
                sortable: true,
            },{
                id: 'modDate',
                dataIndex: 'modDate',
                header: _t('Date Modified'),
                flex: 1,
                sortable: true,
                renderer: renderDate
            }],
            multiSelect: true,
            title: _t('Support Bundles'),
            tbar: {
                itemId: 'support-toolbar',
                items: [{
                    itemId: 'gather-bundle',
                    iconCls: 'add',
                    text: _t('Add'),
                    tooltip: _t('Gather a support bundle in the background'),
                    handler: function() {
                        var grid = this.up('#supportbundles');
                        var dialog = Ext.create('Zenoss.MessageDialog', {
                            message: 'The support bundle will continue to be gathered even if you close this window.  The newly gathered support bundle will not appear until the process has completed.  The job log may be monitored for progress.',
                            okHandler: function() {
                                Zenoss.remote.SupportRouter.createSupportBundle({}, function(response) {
                                    if (response.success) {
                                        var win = Ext.create('Zenoss.JobLog', {
                                            job: response.new_jobs,
                                            title: _t('Create Support Bundle')
                                        });
                                        win.on('destroy', function() {
                                            grid.refresh();
                                        });
                                        win.show();
                                    }
                                });
                            }
                        });
                        dialog.show();
                    }
                },{
                    itemId: 'deletebundles-button',
                    iconCls: 'delete',
                    text: _t('Delete'),
                    tooltip: _t('Delete Support Bundles'),
                    disabled: true,
                    handler: function() {
                        var grid = this.up('#supportbundles');
                        bundleNames = [];
                        Ext.each(grid.getSelectionModel().getSelection(), function(row) {
                            bundleNames.push(row.data.fileName);
                        });

                        Zenoss.remote.SupportRouter.deleteBundles({bundleNames:bundleNames}, function() {
                            grid.refresh();
                        });

                    }
                },{
                    itemId: 'downloadbundles-button',
                    iconCls: 'export',
                    text: _t('Download'),
                    tooltip: _t('Download support bundle(s)'),
                    disabled: true,
                    handler: function() {
                        var grid = this.up('#supportbundles');
                        var filename = grid.getSelectionModel().getSelection()[0].data.fileName;

                        var form = Ext.create('Ext.form.Panel', {
                            renderTo: Ext.getBody(),
                            standardSubmit: true,
                            url: '/zport/dmd/getSupportBundle?bundle=' + filename
                        });
                        form.submit({
                            target: '_blank',
                        });
                        Ext.defer(function(){
                            form.close();
                        }, 100);
                    }
                },'->',{
                    itemId: 'refreshbundles-button',
                    xtype: 'refreshmenu',
                    ref: 'refreshmenu',
                    stateId: 'bundlesrefresh',
                    iconCls: 'refresh',
                    text: _t('Refresh'),
                    tooltip: _t('Refresh Support Bundles List'),
                    handler: function() {
                        this.up('#supportbundles').refresh();
                    }
                }]
            },
            listeners: {
                selectionchange: function() {
                    // download button
                    var downloadButton = this.down('#downloadbundles-button');
                    if (this.getSelectionModel().getSelection().length === 1) {
                        downloadButton.enable();
                    } else {
                        downloadButton.disable();
                    }
                    // delete button
                    var deleteButton = this.down('#deletebundles-button');
                    if (this.getSelectionModel().getSelection().length > 0) {
                        deleteButton.enable();
                    } else {
                        deleteButton.disable();
                    }
                }
            }
        }]
    }
});

});
