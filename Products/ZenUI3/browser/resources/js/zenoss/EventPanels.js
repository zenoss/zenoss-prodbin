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
    badIds: {},
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
        var record,
            start = this.grid.store.bufferRange[0],
            end = this.grid.store.bufferRange[1];

        this.clearSelections(true);

        for (var i = start; i <= end; i++) {
            record = this.grid.store.getAt(i);
            if (record) {
                if (state === 'All' || record.data.eventState == state) {
                    this.selectRow(i, true);
                }
            }
        }

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
    selectClosed: function(){
        this.clearSelections();
        this.selectEventState('Closed');
    },
    selectCleared: function(){
        this.clearSelections();
        this.selectEventState('Cleared');
    },
    selectAged: function(){
        this.clearSelections();
        this.selectEventState('Aged');
    },
    /**
     * Override handle mouse down method from "Ext.grid.RowSelectionModel"
     * to handle shift select more intelligently.
     * We need to disallow shift select when the selection range crosses
     * a buffer to prevent a user from taking action upon an event they they
     * may not have seen yet. See trac #6959
     **/
    handleMouseDown: function(g, rowIndex, e){
        if(e.button !== 0 || this.isLocked()){
            return;
        }
        var view = this.grid.getView();
        // handle shift select
        if(e.shiftKey && !this.singleSelect && this.last !== false){
            // last is the index of the previous row they selected
            var last = this.last;

            // bufferRange is the first and last item in our current view
            var startIndex = this.grid.store.bufferRange[0];
            var endIndex = this.grid.store.bufferRange[1];

            // only allow shift select if the range is in our current view
            if (last >= startIndex && last <= endIndex){
                this.selectRange(last, rowIndex, e.ctrlKey);
                this.last = last; // reset the last
                view.focusRow(rowIndex);
            }else{
                // unselect everything (in case they shift select, then jump around buffers and shift select again)
                this.clearSelections();
                this.doSingleSelect(rowIndex, e);
            }
        }else{
            this.doSingleSelect(rowIndex, e);
        }
    },
    /**
     * Used by handleMouseDown to handle a single selection
     **/
    doSingleSelect: function(rowIndex, e){
        var view = this.grid.getView();
        var isSelected = this.isSelected(rowIndex);
        if(e.ctrlKey && isSelected){
            this.deselectRow(rowIndex);
        }else if(!isSelected || this.getCount() > 1){
            this.selectRow(rowIndex, e.ctrlKey || e.shiftKey);
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
        this.badIds = {};
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
            bufferSize: 400,
            defaultSort: {field:'severity', direction:'DESC'},
            sortInfo: {field:'severity', direction:'DESC'},
            reader: new Ext.ux.grid.livegrid.JsonReader(
                {
                    root: 'events',
                    totalProperty: 'totalCount'
                },
                Zenoss.env.READER_DEFINITIONS
            )
        });
        Zenoss.EventStore.superclass.constructor.call(this, config);
    }
});
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
                id: 'device',
                dataIndex: 'device',
                header: _t('Device'),
                renderer: Zenoss.render.linkFromGrid
            }, {
                id: 'component',
                dataIndex: 'component',
                header: _t('Component'),
                renderer: Zenoss.render.linkFromGrid
            }, {
                id: 'eventClass',
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
Zenoss.SimpleEventGridPanel = Ext.extend(Zenoss.FilterGridPanel, {
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
        config.listeners = config.listeners || {};
        Ext.applyIf(config.listeners, {
            afterrender: function() {
                if (Ext.isEmpty(this.getView().filters)) {

                    this.getView().renderEditors();
                }
            },
            scope: this
        });
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
            appendGlob: true,
            cm: cm,
            sm: new Zenoss.EventPanelSelectionModel(),
            autoExpandColumn: Zenoss.env.EVENT_AUTO_EXPAND_COLUMN || '',
            view: new Zenoss.FilterGridView(Ext.applyIf(config.viewConfig ||  {}, {
                nearLimit: 100,
                displayFilters: Ext.isDefined(config.displayFilters) ? config.displayFilters : true,
                rowHeight: 10,
                emptyText: _t('No events'),
                loadMask: {msg: 'Loading. Please wait...'},
                defaultFilters: {
                    severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
                    eventState: [Zenoss.STATUS_NEW, Zenoss.STATUS_ACKNOWLEDGED]
                },
                getRowClass: function(record, index) {
                    var stateclass = record.get('eventState')=='New' ?
                                        'unacknowledged':'acknowledged';
                    var sev = Zenoss.util.convertSeverity(record.get('severity'));
                    var rowcolors = Ext.state.Manager.get('rowcolor') ? 'rowcolor rowcolor-' : '';
                    var cls = rowcolors + sev + '-' + stateclass + ' ' + stateclass;
                    return cls;
                }
            }))
        }); // Ext.applyIf
        Zenoss.SimpleEventGridPanel.superclass.constructor.call(this, config);
        this.on('rowdblclick', this.onRowDblClick, this);
    }, // constructor
    setContext: function(uid){
        this.view.setContext(uid);
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



// Define all of the items that could be shown in an EventConsole toolbar.
Zenoss.events.EventPanelToolbarSelectMenu = {
    text: _t('Select'),
    id: 'select-button',
    menu:{
        xtype: 'menu',
        items: [{
            text: 'All',
            handler: function(){
                var grid = Ext.getCmp('select-button').ownerCt.ownerCt,
                sm = grid.getSelectionModel();
                sm.selectAll();
                grid.selectedState = 'all';
            }
        },{
            text: 'None',
            handler: function(){
                var grid = Ext.getCmp('select-button').ownerCt.ownerCt,
                sm = grid.getSelectionModel();
                sm.selectNone();
                sm.selectedState = 'none';
            }
        }]
    }
};


Zenoss.EventGridPanel = Ext.extend(Zenoss.SimpleEventGridPanel, {
    constructor: function(config) {
        
        var evtGrid = this,
            tbarItems = [
                {
                    xtype: 'tbtext',
                    text: config.text || _t('Event Console')
                },
                '-',
                Zenoss.events.EventPanelToolbarActions.acknowledge,
                Zenoss.events.EventPanelToolbarActions.close,
                Zenoss.events.EventPanelToolbarActions.reopen,
                '-',
                config.selectMenu || Zenoss.events.EventPanelToolbarSelectMenu,
                Zenoss.events.EventPanelToolbarActions.refresh
            ];

        if (!config.hideDisplayCombo) {
            tbarItems.push('->');
            tbarItems.push(Ext.create({
                xtype: 'tbtext',
                hidden: config.hideDisplayCombo || false,
                text: _t('Display: ')
            }));
            tbarItems.push(Ext.create({
                xtype: 'combo',
                id: 'history_combo',
                hidden: config.hideDisplayCombo || false,
                name: 'event_display',
                mode: 'local',
                store: new Ext.data.SimpleStore({
                    fields: ['id', 'event_type'],
                    data: [[0,'Events'],[1,'Event Archive']]
                }),
                displayField: 'event_type',
                valueField: 'id',
                width: 120,
                value: 0,
                triggerAction: 'all',
                forceSelection: true,
                editable: false,
                listeners: {
                    select: function(selection) {
                        var archive = selection.value == 1;
                        var params = {
                            uid: evtGrid.view._context,
                            archive: archive
                        };
                        evtGrid.getStore().load({ params: params });
                        Zenoss.events.EventPanelToolbarActions.acknowledge.setHidden(archive);
                        Zenoss.events.EventPanelToolbarActions.close.setHidden(archive);
                    }
                }
            }));

        }
        if (config.newwindowBtn) {
            tbarItems.push('-');
            tbarItems.push(Zenoss.events.EventPanelToolbarActions.newwindow);
        }
        Ext.applyIf(config, {
            tbar: {
                xtype: 'largetoolbar',
                cls: 'largetoolbar consolebar',
                height: 35,
                items: config.tbarItems || tbarItems
            }
        });
        Zenoss.EventGridPanel.superclass.constructor.call(this, config);
    },
    onRowDblClick: function(grid, rowIndex, e) {
        var row = grid.getStore().getAt(rowIndex),
            evid = row.id,
            combo = Ext.getCmp('history_combo'),
            history = (combo.getValue() == '1') ? 'History' : '',
            url = '/zport/dmd/Events/view'+history+'Detail?evid='+evid;
        window.open(url, evid.replace(/-/g,'_'),
            "status=1,width=600,height=500");
    }
});
Ext.reg('EventGridPanel', Zenoss.EventGridPanel);


Zenoss.EventRainbow = Ext.extend(Ext.Toolbar.TextItem, {
    constructor: function(config) {
        var severityCounts = {
            critical: 0,
            error: 0,
            warning: 0,
            info: 0,
            debug: 0,
            clear: 0
        };
        config = Ext.applyIf(config || {}, {
            height: 45,
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            text: Zenoss.render.events(severityCounts, config.count || 3)
        });
        Zenoss.EventRainbow.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        this.directFn({uid:uid}, function(result){
            this.updateRainbow(result.data.events);
        }, this);
    },
    updateRainbow: function(severityCounts) {
        this.setText(Zenoss.render.events(severityCounts, this.count));
    }
});
Ext.reg('eventrainbow', Zenoss.EventRainbow);


Zenoss.events.EventPanelToolbarActions = {
    acknowledge: new Zenoss.Action({
        iconCls: 'acknowledge',
        tooltip: _t('Acknowledge events'),
        permission: 'Manage Events',
        handler: function() {
            Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.acknowledge);
        }
    }),
    close: new Zenoss.Action({
        iconCls: 'close',
        tooltip: _t('Close events'),
        permission: 'Manage Events',
        handler: function() {
            Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.close);
        }
    }),
    reopen: new Zenoss.Action({
        iconCls: 'unacknowledge',
        tooltip: _t('Unacknowledge events'),
        permission: 'Manage Events',
        handler: function() {
            Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.reopen);
        }
    }),
    newwindow: new Zenoss.Action({
        iconCls: 'newwindow',
        permission: 'View',
        tooltip: _t('Go to event console'),
        handler: function(btn) {
            var grid = btn.grid || this.ownerCt.ownerCt,
                curState = Ext.state.Manager.get('evconsole') || {},
                filters = curState.filters || {},
                opts = filters.options || {},
                pat = /devices\/([^\/]+)(\/.*\/([^\/]+)$)?/,
                matches = grid.view.getContext().match(pat),
                st, url;
            // on the device page
            if (matches) {
                opts.device = matches[1];
                if (matches[3]) {
                    opts.component = matches[3];
                }
            }
            filters.options = opts;
            curState.filters = filters;
            st = encodeURIComponent(Zenoss.util.base64.encode(Ext.encode(curState)));
            url = '/zport/dmd/Events/evconsole?state=' + st;
            window.open(url, '_newtab', "");
        }
    }),
    refresh: new Zenoss.Action({
        iconCls: 'refresh',
        permission: 'View',
        tooltip: _t('Refresh events'),
        handler: function(btn) {
            var grid = btn.grid || this.ownerCt.ownerCt,
                view = grid.getView();
            view.updateLiveRows(view.rowIndex, true, true);
        }
    })
}

Zenoss.events.EventPanelToolbarConfigs = {
    addEvent: {
        iconCls: 'add',
        tooltip: _t('Add an event')
    },
    reclassify: {
        iconCls: 'classify',
        tooltip: _t('Reclassify an event')
    }
};

})(); // end of function namespace scoping
