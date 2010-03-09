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
Ext.ns('Zenoss.Service');

Ext.onReady( function() {

    /**********************************************************************
     *
     * Navigation Functionality
     *
     */

    // implements SelectionModel:rowselect event
    function navSelectHandler(sm, rowIndex, dataRecord)
    {
        var uid = dataRecord.data.uid;
        Ext.getCmp('serviceForm').setContext(uid);
        Ext.getCmp('serviceInstancePanel').setContext(uid);
    }

    Zenoss.Service.initNav = function(initialContext) {
        var storeConfig, columnModelConfig, columnModel, store, config,
            nonZeroRender;

        nonZeroRenderer = function(v) { if (v>0) return v; else return ''; };

        storeConfig = { proxy: new Ext.data.DirectProxy({
                                directFn:Zenoss.remote.ServiceRouter.query
                            }),
                        autoLoad: false,
                        bufferSize: 100,
                        defaultSort: {field:'name', direction:'ASC'},
                        sortInfo: {field:'name', direction:'ASC'},
                        params: { uid: initialContext } ,
                        reader: new Ext.ux.grid.livegrid.JsonReader({
                            root: 'services',
                            totalProperty: 'totalCount'
                            }, [
                                {name:'name', type:'string'},
                                {name:'description', type:'string'},
                                {name:'port', type:'string'},
                                {name:'count', type:'string'},
                                {name:'uid', type:'string'}
                            ]) // reader
        };

        columnModelConfig = { defaults: {
                                 sortable: false,
                                 menuDisabled: true
                              },
                              columns: [{
                                      dataIndex: 'name',
                                      header: _t('Name'),
                                      id: 'name'
                                  },{
                                      dataIndex: 'port',
                                      header: _t('port'),
                                      id: 'port',
                                      width: 40,
                                      filter: false
                                  },{
                                      dataIndex: 'count',
                                      header: _t('#'),
                                      id: 'count',
                                      width: 40,
                                      renderer: nonZeroRenderer,
                                      filter: false
                                  }
                              ]
        };

        columnModel = new Ext.grid.ColumnModel(columnModelConfig);

        store = new Ext.ux.grid.livegrid.Store(storeConfig);
        store.on('load',
                function(me, records, options)
                {
                    var grid = Ext.getCmp('navGrid');
                    grid.getSelectionModel().selectFirstRow();
                    grid.fireEvent('rowclick', grid, 0);
                }, store, { single: true });


        config = { id: 'navGrid',
                   stateId: 'servicesNavGridState',
                   enableDragDrop: false,
                   stateful: true,
                   border: false,
                   autoExpandColumn: 'name',
                   rowSelectorDepth: 5,
                   store: store,
                   cm: columnModel,
                   sm: new Zenoss.ExtraHooksSelectionModel({singleSelect:true}),
                   options: { params: { uid: initialContext } },
                   view: new Zenoss.FilterGridView({
                       nearLimit: 20,
                       loadMask: {msg: 'Loading. Please wait...'},
                       listeners: {
                           beforeBuffer:
                               function(view, ds, idx, len, total, opts) {
                                   opts.params.uid = view._context;
                               }
                       }
                   })
        };
        var navGrid = new Zenoss.FilterGridPanel(config);

        navGrid.on('afterrender',
                function(me){
                    me.setContext(initialContext);
                    me.showFilters();
                });

        navGrid.getSelectionModel().on('rowselect', navSelectHandler);
        Ext.getCmp('master_panel').add(navGrid);
    };
});