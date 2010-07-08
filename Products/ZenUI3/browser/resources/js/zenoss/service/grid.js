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
    * Grid Navigation Functionality
    *
    */
    
    zs.GridView = Ext.extend(Zenoss.FilterGridView, {
        
        constructor: function(config) {
            this.addEvents({
                /**
                 * @event livebufferupdated
                 * Fires at the end of a call to liveBufferUpdate.
                 * @param {Ext.ux.BufferedGridView} this
                 */
                'livebufferupdated' : true
            });
            zs.GridView.superclass.constructor.call(this, config);
        },
        
        liveBufferUpdate: function() {
            zs.GridView.superclass.liveBufferUpdate.apply(this, arguments);
            this.fireEvent('livebufferupdated', this);
        }
        
    });

    Ext.reg('servicenavgridview', zs.GridView);

    // handles the SelectionModel's rowselect event
    zs.rowselectHandler = function(sm, rowIndex, dataRecord) {
        var selectedOrganizer, token, tokenParts;
        selectedOrganizer = Ext.getCmp('navTree').getSelectionModel().getSelectedNode();
        if ( selectedOrganizer ) {
            // unselect the organizer, but leave it highlighted
            selectedOrganizer.unselect();
            selectedOrganizer.getUI().addClass('x-tree-selected');
        }
        Ext.getCmp('serviceForm').setContext(dataRecord.data.uid);
        Ext.getCmp('detail_panel').detailCardPanel.setContext(dataRecord.data.uid);
        Ext.getCmp('footer_bar').buttonDelete.setDisabled(false);
        token = Ext.History.getToken();
        if ( ! token ) {
            token = 'navTree:' + Ext.getCmp('navTree').getRootNode().attributes.uid.replace(/\//g, '.');
        }
        tokenParts = token.split('.serviceclasses.');
        if ( tokenParts[1] !== dataRecord.data.name ) {
            Ext.History.add( tokenParts[0] + '.serviceclasses.' + dataRecord.data.name);
        }
    };

    zs.storeConfig = {
            proxy: new Ext.data.DirectProxy({
                directFn:Zenoss.remote.ServiceRouter.query
            }),
            autoLoad: false,
            bufferSize: 100,
            defaultSort: {field:'name', direction:'ASC'},
            sortInfo: {field:'name', direction:'ASC'},
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'services',
                totalProperty: 'totalCount'
            }, [
                {name:'name', type:'string'},
                {name:'description', type:'string'},
                {name:'port', type:'int'},
                {name:'count', type:'int', sortDir: 'DESC'},
                {name:'uid', type:'string'}
                ]) // reader
    };

    zs.columnModelConfig = {
        defaults: {
            sortable: true,
            menuDisabled: true
        },
        columns: [
            {
                dataIndex : 'name',
                header : _t('Name'),
                id : 'name'
            }, {
                dataIndex : 'count',
                header : _t('Count'),
                id : 'count',
                width : 50,
                filter : false
            }
        ]
    };

    zs.GridPanel = Ext.extend(Zenoss.FilterGridPanel, {

        constructor: function(config) {
            Ext.applyIf(config, {
                id: 'navGrid',
                flex: 3,
                stateId: 'servicesNavGridState',
                enableDrag: true,
                ddGroup: 'serviceDragDrop',
                stateful: true,
                border: false,
                autoExpandColumn: 'name',
                rowSelectorDepth: 5,
                loadMask: true,
                view: Ext.create({
                    xtype: 'servicenavgridview',
                    nearLimit: 20,
                    loadMask: {msg: _t('Loading. Please wait...')},
                    listeners: {
                        beforeBuffer: function(view, ds, idx, len, total, opts) {
                            opts.params.uid = view._context;
                        }
                    }
                })
            });
            zs.GridPanel.superclass.constructor.call(this, config);
        },
        
        filterAndSelectRow: function(serviceClassName) {
            var selectedRecord;
            if (serviceClassName) {
                // the token includes a ServiceClass. Filter the grid
                // using the name of the ServiceClass and select the
                // correct row.
                selectedRecord = this.getSelectionModel().getSelected();
                if ( ! selectedRecord || selectedRecord.data.name !== serviceClassName ) {
                    this.serviceClassName = serviceClassName;
                    this.selectRow();
                    this.getView().on('livebufferupdated', this.filterGrid, this);
                }
            }
        },

        filterGrid: function() {
            this.getView().un('livebufferupdated', this.filterGrid, this);
            Ext.getCmp('name').setValue(this.serviceClassName);
            this.getView().on('livebufferupdated', this.selectRow, this);
        },

        selectRow: function() {
            this.getView().un('livebufferupdated', this.selectRow, this);
            this.getStore().each(this.selectRowByName, this);
        },
                
        selectRowByName: function(record) {
            if ( record.data.name === this.serviceClassName ) {
                this.getSelectionModel().selectRow( this.getStore().indexOf(record) );
                return false;
            }
        }

    });
    
    Ext.reg('servicegridpanel', zs.GridPanel);

})();
