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

Ext.ns('Zenoss.events');

/**
 * @class Zenoss.EventPanelSelectionModel
 * @extends Zenoss.ExtraHooksSelectionModel
 *
 */
Zenoss.EventPanelSelectionModel = Ext.extend(Zenoss.ExtraHooksSelectionModel, {
    selectState: null,
    badIds: [],
    initEvents: function(){
        Zenoss.EventPanelSelectionModel.superclass.initEvents.call(this);
        this.on('beforerowselect', this.handleBeforeRowSelect, this);
        this.on('rowselect', this.handleRowSelect, this);
        this.on('rowdeselect', this.handleRowDeSelect, this);
        
    },
    handleBeforeRowSelect: function(sm, index, keepExisting, record){
        if (!keepExisting) {
            this.selectNone();
        }
        return true;
    },
    handleRowSelect: function(sm, index, record){
        if (record) {
            delete this.badIds[record.id];
        }
    },
    handleRowDeSelect: function(sm, index, record){
        if (this.selectState && record) {
            this.badIds[record.id] = 1;
        }
    },
    selectEventState: function(state){
        var start, end, record;
        start = this.grid.store.bufferRange[0];
        end = this.grid.store.bufferRange[1];
        for (var i = start; i <= end; i++) {
            record = this.grid.store.getAt(i);
            if (state === 'All' || record.data.eventState == state) {
                this.selectRow(i, true);
            }
        }
        this.clearSelections(true);
        this.selectState = state;

    },
    selectAll: function(){
    
        this.clearSelections();
        this.selectEventState('All');
    },
    selectNone: function(){
        this.clearSelections();
    },
    selectAck: function(){
        this.clearSelections();
        this.selectEventState('Acknowledged');
    },
    selectNew: function(){
        this.clearSelections();
        this.selectEventState('New');
    },
    selectSuppressed: function(){
        this.clearSelections();
        this.selectEventState('Suppressed');
    },
    handleMouseDown: function(g, rowIndex, e){
        //override from base class to disable shift-click 
        if (e.button !== 0 || this.isLocked()) {
            return;
        }
        
        var view = this.grid.getView();
        var isSelected = this.isSelected(rowIndex);
        if (e.ctrlKey && isSelected) {
            this.deselectRow(rowIndex);
        }
        else 
            if (!isSelected || this.getCount() > 1 || this.selectState) {
                this.selectRow(rowIndex, e.ctrlKey);
                view.focusRow(rowIndex);
            }
    },
    clearSelections: function(fast){
        var start, end, record;
        if (this.isLocked()) {
            return;
        }
        this.selectState = null;
        if(!fast){
            //make sure all rows are deselected so that UI renders properly
            //base class only deselects rows it knows are selected; so we need
            //to deselect rows that may have been selected via selectstate
            start = this.grid.store.bufferRange[0];
            end = this.grid.store.bufferRange[1];
            for (var i = start; i <= end; i++) {
                record = this.grid.store.getAt(i);
                this.deselectRow(i);
            }
        }
        this.badIds = [];
        Zenoss.EventPanelSelectionModel.superclass.clearSelections.apply(this, arguments);
    },
    onRefresh: function(){
        //override from base class to prevent reslect after sorting 
        var ds = this.grid.store, index;
        var s = this.getSelections();
        this.clearSelections(false);
        if (s.length != this.selections.getCount()) {
            this.fireEvent('selectionchange', this);
        }
    },
    isSelected: function(index){
        var r = Ext.isNumber(index) ? this.grid.store.getAt(index) : index;
        var selected = (r && this.selections.key(r.id) ? true : false);
        var badId = false;
        if (r && this.badIds[r.id]) {
            selected = false;
        }
        else if (this.selectState == 'All') {
                selected = true;
        }
        else if (r && !selected && this.selectState) {
            if (this.selectState == 'Acknowledged') {
                selected = r.data.eventState == 'Acknowledged';
            }
            else if (this.selectState == 'Suppressed') {
                selected = r.data.eventState == 'Suppressed';
            }
            else if (this.selectState == 'New') {
                selected = r.data.eventState == 'New';
            }
        }
        return selected;
        
    }
});
// the column model for the device grid
Zenoss.EventStore = Ext.extend(Ext.ux.grid.livegrid.Store, {
    constructor: function(config){
        Ext.applyIf(config, {
            proxy: new Ext.data.DirectProxy({
                directFn: Zenoss.remote.EventsRouter.query
            }),
            bufferSize: 100,
        defaultSort: {field:'severity', direction:'DESC'},
        sortInfo: {field:'severity', direction:'DESC'},
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'events',
                totalProperty: 'totalCount'
                }, [
                // List all possible columns. 
                // FIXME: This should come from the server.
                    'dedupid',
                    'evid',
                    'device',
                    'device_title',
                    'device_url',
                    'component',
                    'component_url',
                    'component_title',
                    'summary',
                    'eventState',
                    'eventClass',
                    'eventClass_url',
                    'eventKey',
                    'message',
                    'eventClassKey',
                    'eventGroup',
                    'prodState',
                    'suppid',
                    'manager',
                    'agent',
                    'DeviceClass',
                    'Location',
                    'Systems',
                    'DeviceGroups',
                    'ipAddress',
                    'facility',
                    'priority',
                    'ntevid',
                    'ownerid',
                    'clearid',
                    'DevicePriority',
                    'eventClassMapping',
                    'monitor',
                    {name:'count', type:'int'},
                    {name:'severity', type:'int'},
                    {name:'firstTime', type:'date', 
                        dateFormat:Zenoss.date.ISO8601Long},
                    {name:'lastTime', type:'date', 
                        dateFormat:Zenoss.date.ISO8601Long},
                    {name:'stateChange', type:'date',
                        dateFormat:Zenoss.date.ISO8601Long}
                ]) // reader
        }); // Ext.applyIf
        Zenoss.EventStore.superclass.constructor.call(this, config);
    } // constructor
}); // Ext.extend
Ext.reg('EventStore', Zenoss.EventStore);


Zenoss.SimpleEventColumnModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config){
        config = Ext.applyIf(config || {}, {
            defaults: {
                sortable: false,
                menuDisabled: true,
                width: 200
            },
            columns: [{
                dataIndex: 'severity',
                header: _t('Severity'),
                width: 60,
                id: 'severity',
                renderer: Zenoss.util.render_severity
            }, {
                dataIndex: 'device',
                header: _t('Device'),
                renderer: Zenoss.render.linkFromGrid
            }, {
                dataIndex: 'component',
                header: _t('Component'),
                renderer: Zenoss.render.linkFromGrid
            }, {
                dataIndex: 'eventClass',
                header: _t('Event Class'),
                renderer: Zenoss.render.linkFromGrid
            }, {
                dataIndex: 'summary',
                header: _t('Summary'),
                id: 'summary'
            }] // columns
        }); // Ext.applyIf
    Zenoss.SimpleEventColumnModel.superclass.constructor.call(
        this, config);
    } // constructor
}); // Ext.extend
Ext.reg('SimpleEventColumnModel', Zenoss.SimpleEventColumnModel);


Zenoss.FullEventColumnModel = Ext.extend(Ext.grid.ColumnModel, {
    constructor: function(config){
        // Zenoss.env.COLUMN_DEFINITIONS comes from the server, and depends on
        // the resultFields associated with the context.
        // FIXME: This shouldn't come from the server.
        config = Ext.applyIf(config || {}, {
            columns:Zenoss.env.COLUMN_DEFINITIONS
        });
        Zenoss.FullEventColumnModel.superclass.constructor.call(this, config);
    }
});
Ext.reg('FullEventColumnModel', Zenoss.FullEventColumnModel);


/**
 * @class Zenoss.SimpleEventGridPanel
 * @extends Ext.ux.grid.livegrid.GridPanel
 * Shows events in a grid panel similar to that on the event console.
 * Fixed columns.
 * @constructor
 */
Zenoss.SimpleEventGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    constructor: function(config){
        var store = {xtype:'EventStore'},
            cmConfig = {};
        if (Ext.isDefined(config.columns)) {
            cmConfig.columns = config.columns;
        }
        var cm = new Zenoss.SimpleEventColumnModel(cmConfig);
        if (!Ext.isEmpty(config.directFn)) {
            Ext.apply(store, {
                proxy: new Ext.data.DirectProxy({
                    directFn: config.directFn
                })
            });
        }
        var id = config.id || Ext.id();
        Ext.applyIf(config, {
            id: 'eventGrid' + id,
            stripeRows: true,
            stateId: Zenoss.env.EVENTSGRID_STATEID || 'default_eventsgrid',
            enableDragDrop: false,
            stateful: true,
            border: false,
            rowSelectorDepth: 5,
            store: store,
            cm: cm,
            sm: new Zenoss.EventPanelSelectionModel(),
            autoExpandColumn: 'summary',
            view: new Ext.ux.grid.livegrid.GridView({
                nearLimit: 20,
                rowHeight: 10,
                emptyText: _t('No events'),
                loadMask: {msg: 'Loading. Please wait...'},
                listeners: {
                    beforeBuffer: function(view, ds, idx, len, total, opts){
                        opts.params.uid = view._context;
                    }
                },
                getRowClass: function(record, index) {
                    var stateclass = record.get('eventState')=='New' ?
                                        'unacknowledged':'acknowledged';
                    var sev = Zenoss.util.convertSeverity(record.get('severity'));
                    var rowcolors = Ext.state.Manager.get('rowcolor') ? 'rowcolor rowcolor-' : '';
                    var cls = rowcolors + sev + '-' + stateclass + ' ' + stateclass;
                    return cls;
                }
            })
        }); // Ext.applyIf
        Zenoss.SimpleEventGridPanel.superclass.constructor.call(this, config);
        this.on('rowdblclick', this.onRowDblClick, this);
    }, // constructor
    setContext: function(uid){
        this.view._context = uid;
        this.view.updateLiveRows(this.view.rowIndex, true, true);
    },
    onRowDblClick: function(grid, rowIndex, e) {
        var row = grid.getStore().getAt(rowIndex),
            evid = row.id,
             url = '/zport/dmd/Events/viewDetail?evid='+evid;
         window.open(url, evid.replace(/-/g,'_'),
             "status=1,width=600,height=500");
    }
}); // SimpleEventGridPanel
Ext.reg('SimpleEventGridPanel', Zenoss.SimpleEventGridPanel);


Zenoss.EventRainbow = Ext.extend(Ext.Toolbar.TextItem, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            height: 45,
            directFn: Zenoss.remote.DeviceRouter.getInfo,
        text: Zenoss.render.events({'critical':0, 'error':0, 'warning':0})
        });
        Zenoss.EventRainbow.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        this.directFn({uid:uid}, function(result){
            this.setText(Zenoss.render.events(result.data.events));
        }, this);
    }
});

Ext.reg('eventrainbow', Zenoss.EventRainbow);

Zenoss.events.EventPanelToolbarActions = {
    acknowledge: new Zenoss.Action({
        //text: _t('Acknowledge'),
        iconCls: 'acknowledge',
        permission: 'Manage Events',
        handler: function(btn) {
            var grid = this.ownerCt.ownerCt,
                sm = grid.getSelectionModel(),
                selected = sm.getSelections(),
                evids = Ext.pluck(selected, 'id');
            Zenoss.remote.EventsRouter.acknowledge(
                {evids:evids},
                function(provider, response){
                    var view = grid.getView();
                    view.updateLiveRows(view.rowIndex, true, true);
                }
            );
        }
    }),
    close: new Zenoss.Action({
        //text: _t('Close'),
        iconCls: 'close',
        permission: 'Manage Events',
        handler: function(btn) {
            var grid = this.ownerCt.ownerCt,
                sm = grid.getSelectionModel(),
                selected = sm.getSelections(),
                evids = Ext.pluck(selected, 'id');
            Zenoss.remote.EventsRouter.close(
                {evids:evids},
                function(provider, response){
                    var view = grid.getView();
                    view.updateLiveRows(view.rowIndex, true, true);
                }
            );
        }
    }),
    newwindow: new Zenoss.Action({
        //text: _t('Open in new window'),
        iconCls: 'newwindow',
        permission: 'View',
        handler: function(btn) {
            var grid = this.ownerCt.ownerCt,
                curState = Ext.state.Manager.get('evconsole') || {},
                filters = curState.filters || {},
                opts = filters.options || {},
                pat = /devices\/([^\/]+)(\/.*\/([^\/]+)$)?/,
                matches = grid.view._context.match(pat),
                st, url;
            opts.device = matches[1];
            opts.component = matches[3];
            filters.options = opts;
            curState.filters = filters;
            st = Zenoss.util.base64.encode(Ext.encode(curState));
            url = '/zport/dmd/Events/evconsole?state=' + st;
            window.open(url, '_newtab', "");
        }
    })
}


})(); // end of function namespace scoping
