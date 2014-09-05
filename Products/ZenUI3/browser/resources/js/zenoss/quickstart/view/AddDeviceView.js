/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    function addErrorToolTip(metadata, record) {
        if (record.get('errors')) {
            var msg = record.get('errors');
            msg = Ext.htmlEncode(msg);
            msg = "<pre style='white-space:normal;'>" + msg + "</pre>";
            msg = msg.replace(/\"/g, '&quot;');
            metadata.tdAttr = 'data-qtip="' + msg + '"';
        }
    }

    /**
     * @class Zenoss.quickstart.Wizard.AddDeviceGrid
     * @extends Ext.panel.Panel
     * @constructor
     *
     */
    Ext.define('Zenoss.quickstart.Wizard.AddDeviceGrid', {
        extend: 'Ext.grid.Panel',
        alias: ['widget.deviceaddgrid'],
        requires: [
            'Ext.grid.plugin.CellEditing',
            'Ext.form.field.Text',
            'Ext.toolbar.TextItem'
        ],
        constructor: function(config) {
            this.editing = Ext.create('Ext.grid.plugin.CellEditing');
            config = config || {};
            Ext.applyIf(config, {
                plugins: [this.editing],
                columns: [{
                    dataIndex: 'status',
                    header: _t('Status'),
                    width: 75,
                    renderer: function(val, metadata, record) {
                        // if there are errors show them in a tooltip
                        addErrorToolTip(metadata, record);
                        switch (val) {
                          case "STARTED":
                            return Ext.String.format("<img src='{0}' alt='{1}' />", "/++resource++zenui/img/ext4/icon/circle_arrows_ani.gif", status);
                          case "PENDING":
                            return Ext.String.format("<img src='{0}' alt='{1}' />", "/++resource++zenui/img/ext4/icon/circle_arrows_still.png", status);
                          case "ABORTED":
                            return "<span class=\"tree-severity-icon-small-warning\" style=\"padding-left:18px;padding-top:2px;\">Aborted</span>";
                          case "SUCCESS":
                            return "<span class=\"tree-severity-icon-small-clear\" style=\"padding-left:18px;padding-top:2px;\">Success</span>";
                          case "FAILURE":
                            return "<span class=\"tree-severity-icon-small-critical\" style=\"padding-left:18px;padding-top:2px;\">Failure</span>";
                        }
                        return val;
                    }
                }, {
                    dataIndex: 'deviceName',
                    header: _t('Host'),
                    flex: 1,
                    renderer: function(val, metadata, record) {
                        addErrorToolTip(metadata, record);
                        if (record.get('status') != "PENDING") {
                            var link = Zenoss.render.default_uid_renderer(record.get('deviceUid'), val);
                            return link.replace("<a ", "<a target='_blank' ");
                        }
                        return val;
                    },
                    field: {
                        xtype: 'textfield'
                    }
                },{
                    dataIndex: 'zProperties',
                    header: _t('Credentials'),
                    renderer: function(props, metadata, record) {
                        addErrorToolTip(metadata, record);
                        var values = [], msg, link, hash = window.location.hash, key;
                        for (key in props) {
                            if (key.indexOf('Password') == -1) {
                                values.push(props[key]);
                            }
                        }
                        msg = values.join(",");
                        return Ext.String.format("<a href=\"{2}\" onClick='{0}'> {1}</a>",
                                                 'Zenoss.quickstart.Wizard.editZProperties(\"' + record.get('uuid') + "\",\"" +  record.get('deviceName')  +"\")",
                                                 msg,
                                                 window.location.hash
                                                );
                    }
                }, {
                    dataIndex: 'collector',
                    header: _t('Collector'),
                    hidden: Zenoss.env.COLLECTORS.length == 1 ? true:  false
                }, {
                    dataIndex: 'displayDeviceClass',
                    header: _t('Type'),
                    width: 120
                },{
                    dataIndex: 'duration',
                    header: _t('Duration'),
                    renderer: function(value, metadata, record) {
                        addErrorToolTip(metadata, record);
                        if (value) {
                            return Ext.String.format("{0} {1}", value, _t('seconds'));
                        }
                        return "--";
                    }
                }, {
                    dataIndex: 'logfile',
                    header: _t('Job Log'),
                    renderer: function(val, metadata, record) {
                        addErrorToolTip(metadata, record);
                        if (!val) {
                            return "--";
                        }
                        return Ext.String.format("<a href=\"{2}\" onClick='{0}'> {1}</a>",
                                                 'Zenoss.quickstart.Wizard.openJobLogFile(\"' + record.get('uuid') + "\",\"" +  record.get('deviceName')  +"\")",
                                                 val.replace("/opt/zenoss/log/jobs/", ""),
                                                 window.location.hash
                                                );
                    }
                }, {
                    xtype: 'actioncolumn',
                    width: 75,
                    handler: function(grid, rowIndex){
                        // get the record and tell the database to delete the job
                        var store = grid.getStore(), record = store.getAt(rowIndex);
                        if (record.get('pendingDelete')) {
                            return;
                        }
                        record.set('pendingDelete', true);
                        Zenoss.remote.JobsRouter.deleteJobs({
                            jobids: [record.get('uuid')]
                        }, function(response) {
                            store.remove(record);
                        });

                        var uid = record.get('deviceUid');

                        if (record.get('status') !== "PENDING") {
                            Zenoss.remote.DeviceRouter.removeDevices({
                                uids: [uid],
                                action: 'delete',
                                hashcheck: 1
                            });
                        }
                    },
                    text: _t('Remove'),
                    icon: "/++resource++extjs/examples/restful/images/delete.png",
                    altText: _t('Remove')

                },{
                    xtype: 'actioncolumn',
                    width: 75,
                    id: 'resubmit_job',
                    tooltip: _t('Retry'),
                    text: _t('Retry'),
                    icon: '/++resource++extjs//examples/shared/icons/fam/table_refresh.png'

                }],
                store: Ext.create('Zenoss.quickstart.Wizard.AddDeviceStore', {})

            });
            this.callParent([config]);
        }
    });

    /**
     * @class Zenoss.quickstart.Wizard.view.AutoDiscoveryView
     * @extends Ext.panel.Panel
     * @constructor
     *
     */
    Ext.define('Zenoss.quickstart.Wizard.view.AddDeviceView', {
        extend: 'Ext.form.Panel',
        alias: 'widget.wizardadddeviceview',
        stepTitle:  _t('Add Infrastructure'),
        stepId: 'add-device',
        stepHeight: 630,
        constructor: function(config) {
            var me = this;
            config = config || {};
            Ext.applyIf(config, {
                layout: 'border',
                items:[{
                    xtype: 'form',
                    height: 400,
                    layout: 'hbox',
                    items: [{
                        width: 175,
                        xtype: 'fieldset',
                        height: 275,
                        autoScroll: true,
                        style: {
                            borderRight: '1px solid #CACACA !important'
                        },
                        title: _t('Category'),
                        items:[{
                            xtype: 'radiogroup',
                            itemId: 'category',
                            autoScroll: true,
                            columns: 1,
                            vertical: true,
                            items: []
                        }]
                    }, {
                        xtype: 'fieldset',
                        width: 250,
                        height: 275,
                        title: _t('Type'),
                        style: {
                            borderRight: '1px solid #CACACA !important',
                            paddingLeft: "15px"
                        },
                        items: [{
                            xtype: 'combo',
                            name: 'deviceclass',
                            itemId: 'deviceType',
                            queryMode: 'local',
                            queryParam: false,
                            width: 200,
                            emptyText:  _t('Select one...'),
                            editable: true,
                            store: Ext.create('Zenoss.quickstart.Wizard.store.DeviceType', {}),
                            valueField: 'value',
                            displayField: 'shortdescription'
                        }]
                    },{
                        xtype: 'fieldset',
                        width: 250,
                        itemId: 'credentials',
                        title: _t('Connection Information'),
                        style: {
                            paddingLeft: "15px"
                        },
                        layout: 'anchor',
                        autoHeight: true,
                        autoScroll: true,
                        minHeight: 300,
                        defaults: {
                            labelAlign: 'top',
                            anchor: "90%"
                        }
                    }]
                }, {
                    region: 'south',
                    xtype: 'fieldset',
                    title: _t('Devices'),
                    width: 860,
                    height: 190,
                    items: [{
                        xtype: 'deviceaddgrid',
                        autoScroll: true,
                        height: 150,
                        emptyText: _t('Add infrastructure using the above form'),
                        // the width is so that the right edge of the
                        // grid lines up with the Authentication form
                        width: 860
                    }]

                }]
            });
            this.callParent([config]);
        }

    });

})();
