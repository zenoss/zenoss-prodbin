/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


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
    detail_panel.collapsible = true;


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
    container.on('render', function(){container.el.addClass('zenui3');});

    // Add the toolbar to the container
    var tbar = new Zenoss.LargeToolbar({
            region:'north',
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
                            sm.selectEventState('All');
                            sm.setSelectState("All");
                        }
                    },{
                        text: 'None',
                        handler: function(){
                            var grid = Ext.getCmp('events_grid'),
                            sm = grid.getSelectionModel();
                            sm.clearSelections();
                            sm.clearSelectState();
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
                        var grid = Ext.getCmp('events_grid'),
                            state = grid.getState(),
                            params = {
                                type: 'xml',
                                isHistory: true,
                                params: {
                                    fields: Ext.Array.pluck(state.columns, 'id'),
                                    sort: state.sort.property,
                                    dir: state.sort.direction,
                                    params: grid.getExportParameters()
                                }
                            };
                        Ext.get('export_body').dom.value =
                            Ext.encode(params);
                        Ext.get('exportform').dom.submit();
                    }
                }, {
                    text: 'CSV',
                    handler: function(){
                        var grid = Ext.getCmp('events_grid'),
                            state = grid.getState(),
                            params = {
                                type: 'csv',
                                isHistory: true,
                                params: {
                                    fields: Ext.Array.pluck(state.columns, 'id'),
                                    sort: state.sort.property,
                                    dir: state.sort.direction,
                                    params: grid.getExportParameters()
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
                            var checked = checkitem.checked;
                            var grid = Ext.getCmp('events_grid');
                            grid.toggleRowColors(checked);
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
                        new Zenoss.dialog.ErrorDialog({
                            message: Ext.String.format(_t('<div class="dialog-link">'
                                + 'Drag this link to your bookmark bar '
                                + '<br/>to return to this configuration later.'
                                + '<br/><br/><a href="'
                                + link
                                + '">Resource Manager: Event Archive</a></div>')),
                            title: _t('Save Configuration')
                            });
                        }
                    },{
                        text: "Restore defaults",
                        handler: function(){
                            new Zenoss.dialog.SimpleMessageDialog({
                                message: Ext.String.format(_t('Are you sure you want to restore '
                                    + 'the default configuration? All'
                                    + ' filters, column sizing, and column order '
                                    + 'will be lost.')),
                                title: _t('Confirm Restore'),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        Ext.getCmp('events_grid').resetGrid();
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
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
                handler: function() {
                    var grid = Ext.getCmp('events_grid');
                    grid.refresh();
                },
                pollHandler: function() {
                    var grid = Ext.getCmp('events_grid');
                    grid.refresh();
                }
            }
            ]
        });

    function doLastUpdated() {
        var box = Ext.getCmp('lastupdated'),
            dt = new Date(),
            dtext = Zenoss.date.renderWithTimeZone(new Date()/1000);
            dtext += " (" + Zenoss.USER_TIMEZONE + ")";
            box.setText(_t('Last updated at ') + dtext);
    }

    // Show filters by default on history console
    // State restoration occurs after render, so this won't persist if unwanted
    // myView.on('render', function(){myView.showFilters();});

    // Selection model
    var console_selection_model = new Zenoss.EventPanelSelectionModel({
    });

    /*
     * THE GRID ITSELF!
     */
    var grid = Ext.create('Zenoss.events.Grid', {
        region: 'center',
        tbar: tbar,
        id: 'events_grid',
        stateId: Zenoss.env.EVENTSGRID_STATEID,
        enableDragDrop: false,
        appendGlob: true,
        defaultFilters: {
            severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
            eventState: [Zenoss.STATUS_CLOSED, Zenoss.STATUS_CLEARED, Zenoss.STATUS_AGED],
            // _managed_objects is a global function sent from the server, see ZenUI3/security/security.py
            tags: _managed_objects()
        },
        stateful: true,
        rowSelectorDepth: 5,
        store: Ext.create('Zenoss.events.Store', {
            directFn: Zenoss.remote.EventsRouter.queryArchive
        }),

        // Zenoss.env.COLUMN_DEFINITIONS comes from the server, and depends on
        // the resultFields associated with the context.
        columns: Zenoss.env.getColumnDefinitions(),
        // Map some other keys
        keys: [{
        // Enter to pop open the detail panel
            key: Ext.EventObject.ENTER,
            fn: toggleEventDetailContent
        }],
        displayTotal: false,
        selModel: console_selection_model // defined above

    });
    console_selection_model.grid = grid;
    // Add it to the layout
    master_panel.add(grid);

    Zenoss.util.callWhenReady('events_grid', function(){
        Ext.getCmp('events_grid').setContext(Zenoss.env.PARENT_CONTEXT);
    });

    /*
     * DETAIL PANEL STUFF
     */
    // Pop open the event detail, depending on the number of rows selected
    function toggleEventDetailContent(){
        var selections = console_selection_model.getSelection();
        if (selections.length) {
            showEventDetail(selections[0]);
        } else {
            wipeEventDetail();
        }
    }

    // Pop open the event detail pane and populate it with the appropriate data
    // and switch triggers (single select repopulates detail, esc to close)
    function showEventDetail(r) {
        Ext.getCmp('dpanelcontainer').load(r.data.evid);
        grid.un('itemdblclick', toggleEventDetailContent);
        detail_panel.expand();
        detail_panel.show();
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
        grid.on('itemdblclick', toggleEventDetailContent);
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
    //  render the detail panel
    detail_panel.show();
    detail_panel.collapse();

    detail_panel.on('expand', function(ob, state) {
        toggleEventDetailContent();
    });

    detail_panel.on('collapse', function(ob, state) {
        eventDetailCollapsed();
    });

    // Hook up the "Last Updated" text
    var store = grid.getStore(),
        view = grid.getView();
    store.on('beforeprefetch', doLastUpdated);
    doLastUpdated();

    // Detail pane should pop open when double-click on event
    grid.on("itemdblclick", toggleEventDetailContent);
    console_selection_model.on("select", function(){
        if(detail_panel.collapsed == false){
            toggleEventDetailContent();
        }
        // if more than one is selected using the ctrl key, collapse the details:
        if(this.getCount() > 1) detail_panel.collapse();
    });
    // When multiple events are selected, detail pane should blank
    console_selection_model.on('rangeselect', function(){
        detail_panel.collapse();
    });

    // Key mapping for ESC to close detail pane
    var esckeymap = new Ext.KeyMap(document, {
        key: Ext.EventObject.ESC,
        fn: hideEventDetail
    });
    // Start disabled since pane is collapsed
    esckeymap.disable();

    // if there is a state apply it now
    if (window.location.search) {
        grid.restoreURLState();
    }
});
