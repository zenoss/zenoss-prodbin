/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/
Ext.ns('Zenoss.ui.EvHistory');

Ext.onReady(function(){
    // Global dialogs, will be reused after first load
    var win,
    // Date renderer object, used throughout
        date_renderer = Ext.util.Format.dateRenderer(Zenoss.date.ISO8601Long),
    // Get references to the panels
        detail_panel = Ext.getCmp('detail_panel'),
        master_panel = Ext.getCmp('master_panel');

    master_panel.layout = 'border';

    // Make this instance of the detail panel use a unique state ID so
    // it doesn't interfere with the state of other instances of this panel.
    detail_panel.stateId = 'Zenoss.ui.EvHistory.detail_panel';

    // Make the detail panel collapsible
    detail_panel.animCollapse = false;
    detail_panel.collapsible = false;
    detail_panel.collapsed = true;

    /*
     * Select all events with a given state.
     * This requires a call to the back end, since we don't know anything about
     * records that are outside the current buffer. So we let the server
     * perform a query to determine ranges, then we select the ranges.
     */
    function selectByState(state) {
        var params = {'state':state, 'history':true, 'asof':Zenoss.env.asof},
            grid = Ext.getCmp('events_grid');
        Ext.apply(params, getQueryParameters());
        Zenoss.remote.EventsRouter.state_ranges(
            params,
            function(result) {
                var sm = grid.getSelectionModel();
                sm.clearSelections();
                Ext.each(result, function(range){
                    if (range.length==1)
                        range[1] = grid.getStore().totalLength + 1;
                   sm.selectRange(range[0]-1, range[1]-1, true);
                });
            }
        );
    }

    // Get the container surrounding master/detail, for adding the toolbar
    var container = Ext.getCmp('center_panel_container');

    // Add a CSS class to scope some styles that affect other parts of the UI
    container.on('render', function(){container.el.addClass('zenui3')});

    // Add the toolbar to the container
    var tbar = new Zenoss.LargeToolbar({
            region:'north',
            border: false,
            items: [{
                /*
                 * SELECT MENU
                 */
                text: _t('Select'),
                id: 'select-button',
                menu:{
                    xtype: 'menu',
                    items: [{
                        text: 'All',
                        handler: function(){
                            var grid = Ext.getCmp('events_grid'),
                                sm = grid.getSelectionModel();
                            sm.selectAll();
                        }
                    },{
                        text: 'None',
                        handler: function(){
                            var grid = Ext.getCmp('events_grid'),
                                sm = grid.getSelectionModel();
                            sm.selectNone();
                        }
                    }
                    ]
                }
            },{
                text: _t('Export'),
                id: 'export-button',
                //iconCls: 'export',
                menu: {
                items: [{
                    text: 'XML',
                    handler: function(){
                        var state = Ext.getCmp('events_grid').getState(),
                            params = {
                                type: 'xml',
                                isHistory: true,
                                params: {
                                    fields: Ext.pluck(state.columns, 'id'),
                                    sort: state.sort.field,
                                    dir: state.sort.direction,
                                    params: state.filters.options
                                }
                            };
                        Ext.get('export_body').dom.value =
                            Ext.encode(params);
                        Ext.get('exportform').dom.submit();
                    }
                }, {
                    text: 'CSV',
                    handler: function(){
                        var state = Ext.getCmp('events_grid').getState(),
                            params = {
                                type: 'csv',
                                isHistory: true,
                                params: {
                                    fields: Ext.pluck(state.columns, 'id'),
                                    sort: state.sort.field,
                                    dir: state.sort.direction,
                                    params: state.filters.options
                                }
                            };
                        Ext.get('export_body').dom.value =
                            Ext.encode(params);
                        Ext.get('exportform').dom.submit();
                    }
                }]
                }
            },{
                /*
                 * CONFIGURE MENU
                 */
                text: _t('Configure'),
                id: 'configure-button',
                //iconCls: 'customize',
                menu: {
                    items: [{
                        id: 'rowcolors_checkitem',
                        xtype: 'menucheckitem',
                        text: 'Show severity row colors',
                        handler: function(checkitem) {
                            var checked = !checkitem.checked;
                            var view = Ext.getCmp('events_grid').getView();
                            view.toggleRowColors(checked);
                        }
                    },{
                        id: 'clearfilters',
                        text: 'Clear filters',
                        listeners: {
                            click: function(){
                                grid.clearFilters();
                            }
                        }
                    },/*{
                        id: 'showfilters',
                        text: 'Show filters',
                        checked: false,
                        listeners: {
                            'checkchange' : function(ob, on) {
                                if(on) grid.showFilters()
                                else grid.hideFilters()
                            }
                        }
                    },*/{
                        text: 'Save this configuration...',
                        handler: function(){
                            var grid = Ext.getCmp('events_grid'),
                                link = grid.getPermalink();
                           Ext.Msg.show({
                            title: 'Permalink',
                            msg: '<'+'div class="dialog-link">'+
                            'Drag this link to your bookmark' +
                            ' bar <'+'br/>to return to this grid '+
                             'configuration later.'+
                             '<'+'br/><'+'br/><'+'a href="'+
                             link + '">'+
                             'Event Console<'+'/a><'+'/div>',
                            buttons: Ext.Msg.OK
                            })
                        }
                    },{
                        text: "Restore defaults",
                        handler: function(){
                            Ext.Msg.show({
                                title: 'Confirm Restore',
                                msg: 'Are you sure you want to restore '+
                                  'the default grid configuration? All' +
                                  ' filters, column sizing, and column order '+
                                  'will be lost.',
                                buttons: Ext.Msg.OKCANCEL,
                                fn: function(val){
                                    if (val=='ok')
                                        Ext.getCmp('events_grid').resetGrid();
                                }
                            });
                        }
                    }]
                }
            },'-',{
                xtype: 'tbfill'
            },{
                id: 'lastupdated',
                xtype: 'tbtext',
                cls: 'lastupdated',
                text: 'Updating...'
            },{
                xtype: 'refreshmenu',
                id: 'refresh-button',
                text: _t('Refresh'),
                handler: function(){
                    view = Ext.getCmp('events_grid').getView();
                    view.updateLiveRows(view.rowIndex, true, true);
                }
            }
            ]
        });

    function doLastUpdated() {
        var box = Ext.getCmp('lastupdated'),
            dt = new Date(),
            dtext = dt.format('g:i:sA');
            box.setText(_t('Last updated at ') + dtext);
    };

    // View to render the grid
    var myView = new Zenoss.FilterGridView({
        nearLimit : 20,
        appendGlob: true,
        filterbutton: 'showfilters',
        defaultFilters: {
            severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
            eventState: [Zenoss.STATUS_CLOSED, Zenoss.STATUS_CLEARED, Zenoss.STATUS_AGED]
        },
        rowcoloritem: 'rowcolors_checkitem',
        livesearchitem: 'livesearch_checkitem',
        loadMask  : { msg :  'Loading. Please wait...' }
    });

    // Show filters by default on history console
    // State restoration occurs after render, so this won't persist if unwanted
    myView.on('render', function(){myView.showFilters()});


    // Store to hold the events data
    var console_store = new Zenoss.EventStore({
        proxy: new Zenoss.ThrottlingProxy({
            directFn:Zenoss.remote.EventsRouter.queryArchive,
            listeners: {

                'exception': function(proxy, type, action, options,
                response, arg){
                    if (response.result && response.result.msg){
                        Ext.Msg.show({
                            title: 'Error',
                            msg: response.result.msg,
                            buttons: Ext.Msg.OK,
                            minWidth: 300
                            });
                        }
                    }
                }
        }),
        sortInfo: {field:'lastTime', direction:'DESC'},
        defaultSort: {field:'lastTime', direction:'DESC'},
        autoLoad: true
    });


    // Selection model
    var console_selection_model = new Zenoss.EventPanelSelectionModel();

    /*
     * THE GRID ITSELF!
     */
    var grid = new Zenoss.FilterGridPanel({
        region: 'center',
        tbar: tbar,
        id: 'events_grid',
        stateId: Zenoss.env.EVENTSGRID_STATEID,
        enableDragDrop: false,
        stateful: true,
        border: false,
        rowSelectorDepth: 5,
        autoExpandColumn: Zenoss.env.EVENT_AUTO_EXPAND_COLUMN || '',
        store: console_store, // defined above
        view: myView, // defined above
        // Zenoss.env.COLUMN_DEFINITIONS comes from the server, and depends on
        // the resultFields associated with the context.
        cm: new Zenoss.FullEventColumnModel(),
        stripeRows: true,
        // Map some other keys
        keys: [{
        // Enter to pop open the detail panel
            key: Ext.EventObject.ENTER,
            fn: toggleEventDetailContent
        }],
        displayTotal: false,
        sm: console_selection_model // defined above
    });
    // Add it to the layout
    master_panel.add(grid);


    /*
     * DETAIL PANEL STUFF
     */
    // Pop open the event detail, depending on the number of rows selected
    function toggleEventDetailContent(){
        var count = console_selection_model.getCount();
        if (count==1) {
            showEventDetail(console_selection_model.getSelected());
        } else {
            wipeEventDetail();
        }
    }

    // Pop open the event detail pane and populate it with the appropriate data
    // and switch triggers (single select repopulates detail, esc to close)
    function showEventDetail(r) {
        Ext.getCmp('dpanelcontainer').load(r.data.evid);
        grid.un('rowdblclick', toggleEventDetailContent);
        detail_panel.expand();
        esckeymap.enable();
    }

    // Wipe event detail values
    function wipeEventDetail() {
        Ext.getCmp('dpanelcontainer').wipe();
    }

    // Collapse the event detail pane and switch triggers (double select
    // repopulates detail, esc no longer closes)
    function hideEventDetail() {
        detail_panel.collapse();
    }
    function eventDetailCollapsed(){
        wipeEventDetail();
        grid.on('rowdblclick', toggleEventDetailContent);
        esckeymap.disable();
    }
    // Finally, add the detail panel (have to do it after function defs to hook
    // up the hide callback)
    detail_panel.add({
        xtype:'detailpanel',
        id: 'dpanelcontainer',
        isHistory: true,
        onDetailHide: hideEventDetail
    });

    detail_panel.on('expand', function(ob, state) {
        toggleEventDetailContent();
    });

    detail_panel.on('collapse', function(ob, state) {
        eventDetailCollapsed()
    });

    // Hook up the "Last Updated" text
    var store = grid.getStore(),
        view = grid.getView();
    store.on('load', doLastUpdated);
    view.on('buffer', doLastUpdated);

    // Detail pane should pop open when double-click on event
    grid.on("rowdblclick", toggleEventDetailContent);
    console_selection_model.on("rowselect", function(){
        if(detail_panel.isVisible()){
            toggleEventDetailContent();
        }
        });

    // When multiple events are selected, detail pane should blank
    console_selection_model.on('rangeselect', wipeEventDetail);

    // Key mapping for ESC to close detail pane
    var esckeymap = new Ext.KeyMap(document, {
        key: Ext.EventObject.ESC,
        fn: hideEventDetail
    });
    // Start disabled since pane is collapsed
    esckeymap.disable();

});
