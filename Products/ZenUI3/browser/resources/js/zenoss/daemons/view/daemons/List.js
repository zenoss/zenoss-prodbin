/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    /**
     * @class Daemons.view.daemons.SearchField
     * @extends Ext.form.TextField
     * @constructor
     */
    Ext.define("Daemons.view.daemons.SearchField", {
        extend: "Ext.form.TextField",
        alias: ['widget.daemonsearchfield'],
        constructor: function(config){
            config = Ext.applyIf(config||{}, {
                validationDelay: 500,
                selectOnFocus: true
            });
            config.cls += ' x-field-search';
            this.callParent([config]);
        },
        getClass: function(){
            var cls = this.altCls ? this.altCls : 'searchfield';
            return this.black ? cls + '-black' : cls;
        }
    });

    /**
     * @class Daemons.view.daemons.List
     * @extends Ext.tree.Panel
     * @constructor
     * This class represents the TreeGrid of all the deamons and services.
     */
    Ext.define('Daemons.view.daemons.List' ,{
        extend: 'Ext.tree.Panel',
        alias: 'widget.daemonslist',
        title: _t('All Daemons'),
        stores: ['Daemons'],
        multiSelect: true,
        rootVisible: true,
        useArrows: true,
        dockedItems: [{
            xtype: 'toolbar',
            dock: 'top',
            items: [{
                xtype: 'button',
                text: _t('Start'),
                ref: 'start'
            },{
                xtype: 'button',
                text: _t('Stop'),
                ref: 'stop'
            },{
                xtype: 'button',
                text: _t('Restart'),
                ref: 'restart'
            },'->',{
                xtype: 'daemonsearchfield',
                id: 'component_searchfield',
                emptyText: _t('Type to filter...'),
                enableKeyEvents: true
            }]
        }],
        selectionModel: 'rowmodel',
        initComponent: function() {
            this.columns = [{
                xtype: 'treecolumn', //this is so we know which column will show the tree
                text: _t('ID'),
                flex: 2,
                tooltip: _t('Deamon ID'),
                sortable: true,
                dataIndex: 'id'
            }, {
                text: _t('Logs'),
                flex: .25,
                tooltip: _t('Deamon logs'),
                dataIndex: 'uuid',
                sortable: true,
                renderer: function(value, m, record) {
                    return Ext.String.format("<a href='/zport/dmd/getDeamonLogs?uuid={0}'>{1}</a>",
                                             value,
                                             _t('View Logs'));
                }
            },{
                xtype: 'actioncolumn',
                text: _t('Enabled'),
                flex: .25,
                dataIndex: 'enabled',
                tooltip: _t('Enable or disable deamon'),
                sortable: true,
                getClass: function(v, m, record) {
                    if (record.data.enabled) {
                        return 'grid-action checked enabled';
                    } else {
                        return 'grid-action unchecked enabled';
                    }
                }
            },{
                text: _t('Restart'),
                flex: .1,
                menuDisabled: true,
                xtype: 'actioncolumn',
                tooltip: _t('restart deamon'),
                // Only leaf level tasks may be edited
                isDisabled: function(view, rowIdx, colIdx, item, record) {
                    return !record.data.leaf;
                },
                refreshingIcon: '/++resource++zenui/img/ext4/icon/circle_arrows_ani.gif',
                stillIcon: '/++resource++zenui/img/ext4/icon/circle_arrows_still.png',
                ref: 'restartcolumn',
                items: [{
                    text: _t('Restart'),
                    icon: '/++resource++zenui/img/ext4/icon/circle_arrows_still.png',
                    iconCls: 'restarticon'
                }]
            },{
                text: _t('Status'),
                flex: .25,
                xtype: 'actioncolumn',
                ref: 'statuscolumn',
                tooltip: _t('Click to stop/start the deamon'),
                dataIndex: 'status',
                sortable: true,
                renderer: Zenoss.render.pingStatus,
                /**
                 * Action columns expect an image so override the
                 * defaultRenderer to just use the supplied renderer (pingStatus)
                 **/
                defaultRenderer: function(v, meta, record, rowIdx, colIdx, store, view) {
                    return this.origRenderer.apply(this, arguments);
                }
            }];

            this.callParent(arguments);
        }
    });

})();