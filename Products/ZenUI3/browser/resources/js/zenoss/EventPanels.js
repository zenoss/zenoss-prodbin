/*
  ###########################################################################
  #
  # This program is part of Zenoss Core, an open source monitoring platform.
  # Copyright (C) 2010, Zenoss Inc.
  #
  # This program is free software; you can redistribute it and/or modify it
  # under the terms of the GNU General Public License version 2 or (at your
  # option) any later version as published by the Free Software Foundation.
  #
  # For complete information please visit: http://www.zenoss.com/oss/
  #
  ###########################################################################
*/
(function(){
    Ext.ns('Zenoss.events');
    /*
     * Show the dialog that allows one to add an event.
     */
    function showAddEventDialog(gridId) {
        if (Ext.getCmp('addeventwindow')) {
            Ext.getCmp('addeventwindow').show();
            return;
        }
        var addevent = Ext.create('Zenoss.dialog.BaseWindow', {
            title: _t('Create Event'),
            id: 'addeventwindow',
            layout: 'fit',
            autoHeight: true,
            modal: true,
            width: 310,
            closeAction: 'hide',
            plain: true,
            items: [{
                id: 'addeventform',
                xtype: 'form',
                monitorValid: true,
                defaults: {width: 290},
                autoHeight: true,
                frame: false,
                labelWidth: 100,
                items: [{
                    xtype: 'textarea',
                    name: 'summary',
                    fieldLabel: _t('Summary'),
                    allowBlank: false
                },{
                    xtype: 'textfield',
                    fieldLabel: _t('Device'),
                    name: 'device',
                    allowBlank: false
                },{
                    xtype: 'textfield',
                    fieldLabel: _t('Component'),
                    name: 'component'
                },{
                    fieldLabel: _t('Severity'),
                    name: 'severity',
                    xtype: 'combo',
                    store: Zenoss.env.SEVERITIES,
                    typeAhead: true,
                    allowBlank: false,
                    forceSelection: true,
                    triggerAction: 'all',
                    value: 5,
                    selectOnFocus: true
                },{
                    xtype: 'textfield',
                    fieldLabel: _t('Event Class Key'),
                    name: 'evclasskey'
                },{
                    fieldLabel: _t('Event Class'),
                    name: 'evclass',
                    xtype: 'combo',
                    value: "/Unknown",
                    allowBlank: false,
                    store: Zenoss.env.EVENT_CLASSES,
                    typeAhead: true,
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true
                }],
                buttons: [{
                    text: _t('Submit'),
                    xtype: 'DialogButton',
                    formBind: true,
                    handler: function(){
                        var form = Ext.getCmp('addeventform');
                        Zenoss.remote.EventsRouter.add_event(
                            form.getForm().getValues(),
                            function(){
                                addevent.hide();
                                var grid = Ext.getCmp(gridId);
                                grid.refresh();
                            }
                        );
                    }
                },{
                    text: _t('Cancel'),
                    xtype: 'DialogButton',
                    handler: function(){
                        addevent.hide();
                    }
                }]
            }]

        });
        addevent.show();
    }

    /*
     * Show the dialog that allows one to classify an event
     */
    function showClassifyDialog(gridId) {

        var win = new Zenoss.dialog.BaseWindow({
            title: _t('Classify Events'),
            width: 300,
            autoHeight: true,
            modal: true,
            plain: true,
            items: [{
                id: 'classifyEventForm',
                xtype: 'form',
                monitorValid: true,
                autoHeight: true,
                frame: false,
                items: [{
                    padding: 10,
                    style: {'font-size':'10pt'},
                    html: _t('Select the event class with which'+
                             ' you want to associate these events.')
                },{
                    xtype: 'combo',
                    store: Zenoss.env.EVENT_CLASSES,
                    typeAhead: true,
                    allowBlank: false,
                    forceSelection: true,
                    triggerAction: 'all',
                    width: 180,
                    style: {'margin-left':'100px'},
                    resizable: true,
                    emptyText: _t('Select an event class'),
                    selectOnFocus: true,
                    id: 'evclass_combo'
                }],
                listeners: {
                    fieldvaliditychange: function(form, field, isValid) {
                        Ext.getCmp('classifyEventFormSubmitButton').setDisabled(!isValid);
                    },
                    scope: win
                },
                buttons: [{
                    text: _t('Submit'),
                    xtype: 'DialogButton',
                    id: 'classifyEventFormSubmitButton',
                    disabled: true,
                    handler: function(){
                        var cb = Ext.getCmp('evclass_combo'),
                        grid = Ext.getCmp(gridId),
                        sm = grid.getSelectionModel(),
                        rs = sm.getSelections(),
                        evrows = [];
                        Ext.each(rs, function(record){
                            evrows[evrows.length] = record.data;
                        });
                        if (!evrows.length) {
                            win.hide();
                            new Zenoss.dialog.ErrorDialog({message: _t('No events were selected.')});
                        } else {
                            Zenoss.remote.EventsRouter.classify({
                                'evclass': cb.getValue(),
                                'evrows': evrows
                            }, function(result){
                                win.destroy();
                                var title = result.success ?
                                    _t('Classified'):
                                    _t('Error');
                                Ext.MessageBox.show({
                                    title: title,
                                    msg: result.msg,
                                    buttons: Ext.MessageBox.OK
                                });
                            });
                        }
                    }
                },{
                    text: _t('Cancel'),
                    xtype: 'DialogButton',
                    handler: function(){
                        win.destroy();
                    }
                }]
            }]

        });

        win.show();
    }

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
        reclassify: new Zenoss.Action({
            iconCls: 'classify',
            tooltip: _t('Reclassify an event'),
            permission: 'Manage Events',
            handler: function(button) {
                var gridId = button.ownerCt.ownerCt.id;
                showClassifyDialog(gridId);
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
        unclose: new Zenoss.Action({
            iconCls: 'reopen',
            tooltip: _t('Reopen events'),
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
                var grid = btn.grid || this.ownerCt.ownerCt;
                grid.refresh();
            }
        })
    };

    Zenoss.EventConsoleTBar = Ext.extend(Zenoss.LargeToolbar, {
        constructor: function(config){
            var gridId = config.gridId,
            showActions = true,
                showCommands = true,
                configureMenuItems,
                tbarItems = config.tbarItems || [];

            if (!gridId) {
                throw ("Event console tool bar did not receive a grid id");
            }

            configureMenuItems = [{
                id: 'rowcolors_checkitem',
                xtype: 'menucheckitem',
                text: 'Show severity row colors',
                handler: function(checkitem) {
                    var checked = checkitem.checked;
                    var grid = Ext.getCmp(gridId);
                    grid.toggleRowColors(checked);
                }
            },{
                id: 'clearfilters',
                text: 'Clear filters',
                listeners: {
                    click: function(){
                        Ext.getCmp(gridId).clearFilters();
                    }
                }
            },{
                text: "Restore defaults",
                handler: function(){
                    new Zenoss.dialog.SimpleMessageDialog({
                        message: String.format(_t('Are you sure you want to restore '
                                                  + 'the default configuration? All'
                                                  + ' filters, column sizing, and column order '
                                                  + 'will be lost.')),
                        title: _t('Confirm Restore'),
                        buttons: [{
                            xtype: 'DialogButton',
                            text: _t('OK'),
                            handler: function() {
                                Ext.getCmp(gridId).resetGrid();
                            }
                        }, {
                            xtype: 'DialogButton',
                            text: _t('Cancel')
                        }]
                    }).show();
                }
            }];

            if (/^\/zport\/dmd\/Events/.test(window.location.pathname)) {
                configureMenuItems.splice(2, 0, {
                    text: 'Save this configuration...',
                    handler: function(){
                        var grid = Ext.getCmp(gridId),
                        link = grid.getPermalink();
                        new Zenoss.dialog.ErrorDialog({
                            message: String.format(_t('<div class="dialog-link">'
                                                      + 'Drag this link to your bookmark bar '
                                                      + '<br/>to return to this configuration later.'
                                                      + '<br/><br/><a href="'
                                                      + link
                                                      + '">Resource Manager: Events</a></div>')),
                            title: _t('Save Configuration')
                        });
                    }
                });
            }

            // actions
            if (Ext.isDefined(config.actionsMenu)) {
                showActions = config.actionsMenu;
            }

            if (showActions) {
                tbarItems.push({
                    id: 'event-actions-menu',
                    text: _t('Actions'),
                    xtype: 'deviceactionmenu',
                    deviceFetcher: function() {
                        var grid = Ext.getCmp(gridId),
                        sm = grid.getSelectionModel(),
                        rows = sm.getSelections(),
                        ranges = [],
                        pluck = Ext.pluck,
                        uids = pluck(pluck(pluck(rows, 'data'), 'device'), 'uid'),
                        opts =  {
                            uids: uids,
                            ranges: [],
                            hashcheck: 'none'
                        };
                        opts.params = grid.filterRow.getSearchValues();
                        // filter out the nulls
                        opts.uids = Zenoss.util.filter(opts.uids, function(uid){
                            return uid;
                        });

                        return opts;
                    },
                    saveHandler: Ext.emptyFn
                });
            }

            // commands
            if (Ext.isDefined(config.commandsMenu)) {
                showCommands = config.commandsMenu;
            }
            if (showCommands) {
                tbarItems.push({
                    id: 'event-commands-menu',
                    text: _t('Commands'),
                    hidden: !showCommands,
                    disabled: Zenoss.Security.doesNotHavePermission('Run Commands'),
                    setContext: function(uid) {
                        if (!uid) {
                            uid = '/zport/dmd/Devices';
                        }
                        var me = Ext.getCmp('event-commands-menu'),
                        menu = me.menu;
                        // load the available commands from the server
                        // commands are based on context
                        Zenoss.remote.DeviceRouter.getUserCommands({uid:uid}, function(data) {
                            menu.removeAll();
                            Ext.each(data, function(d) {
                                menu.add({
                                    text:d.id,
                                    tooltip:d.description,
                                    handler: function(item) {
                                        var command = item.text,
                                            grid = Ext.getCmp(gridId),
                                            sm = grid.getSelectionModel(),
                                            selections = sm.getSelections(),
                                            devids = Ext.pluck(Ext.pluck(Ext.pluck(selections, 'data'), 'device'), 'uid');

                                        // filter out the none device events
                                        devids = Zenoss.util.filter(devids, function(uid){ return uid; });
                                        if (devids.length) {

                                            // only run commands for the visible devices
                                            var win = new Zenoss.CommandWindow({
                                                uids: devids,
                                                target: uid + '/run_command',
                                                command: command
                                            });
                                            win.show();
                                        }
                                    }
                                });
                            });
                        });
                    },
                    menu: {}
                });
            }
            this.gridId = gridId;

            if (!config.hideDisplayCombo) {
                tbarItems.push('->');
                tbarItems.push(Ext.create('Ext.toolbar.TextItem', {
                    hidden: config.hideDisplayCombo || false,
                    text: _t('Display: ')
                }));
                tbarItems.push(Ext.create('Ext.form.ComboBox', {
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
                            var archive = selection.value == 1,
                                grid = Ext.getCmp(gridId),
                                yesterday = new Date();

                            // reload the grid. changing the filters
                            grid.setStoreParameter('archive', archive);

                            // if history set default lastseen to yesterday
                            if (archive) {
                                yesterday.setDate(yesterday.getDate() - 1);
                                grid.setFilter('lastTime', yesterday);
                            }else{
                                grid.setFilter('lastTime', null);
                            }


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

            Zenoss.EventActionManager.configure({
                onFinishAction: function() {
                    var grid = Ext.getCmp(gridId);
                    if (grid) {
                        grid.updateRows();
                        grid.getSelectionModel().clearSelections();
                    }
                },
                findParams: function() {
                    var grid = Ext.getCmp(gridId);
                    if (grid) {
                        return grid.getSelectionParameters();
                    }
                }
            });

            Ext.applyIf(config, {
                ref: 'tbar',
                listeners: {
                    afterrender: function(){
                        var grid = Ext.getCmp(gridId),
                        store = grid.getStore(),
                        tbar = this,
                        view = grid.getView();
                        store.on('load', this.doLastUpdated);
                        view.on('buffer', this.doLastUpdated);

                        view.on('filterchange', function(){
                            tbar.refreshmenu.setDisabled(!view.isValid());

                            // Hook up the "Last Updated" text
                            if ( !view.isValid() ) {
                                var box = Ext.getCmp('lastupdated');
                                box.setText(_t(''));
                            }
                        });
                        // set up the commands menu
                        var context = Zenoss.env.device_uid || Zenoss.env.PARENT_CONTEXT;
                        if (context == "/zport/dmd/Events") {
                            context = location.pathname.replace('/viewEvents', '');
                        }

                        this.setContext(context);
                    },
                    scope: this
                },
                items: [
                    Zenoss.events.EventPanelToolbarActions.acknowledge,
                    Zenoss.events.EventPanelToolbarActions.close,
                    Zenoss.events.EventPanelToolbarActions.reclassify,
                    Zenoss.events.EventPanelToolbarActions.reopen,
                    Zenoss.events.EventPanelToolbarActions.unclose,
                    new Zenoss.Action({
                        iconCls: 'add',
                        tooltip: _t('Add an event'),
                        permission: 'Manage Events',
                        handler: function(button) {

                            showAddEventDialog(gridId);
                        }
                    }),
                    {
                        xtype: 'tbseparator'
                    },
                    Zenoss.events.EventPanelToolbarSelectMenu,
                    {
                        text: _t('Export'),
                        id: 'export-button',
                        //iconCls: 'export',
                        menu: {
                            items: [{
                                text: 'XML',
                                handler: function(){
                                    var context = Zenoss.env.device_uid || Zenoss.env.PARENT_CONTEXT;
                                    if (context == "/zport/dmd/Events") {
                                        context = location.pathname.replace('/viewEvents', '');
                                    }

                                    var grid = Ext.getCmp(gridId),
                                        state = grid.getState(),
                                        historyCombo = Ext.getCmp('history_combo'),
                                        params = {
                                            type: 'xml',
                                            isHistory: false,
                                            params: {
                                                uid: context,
                                                fields: Ext.pluck(state.columns, 'id'),
                                                sort: state.sort.property,
                                                dir: state.sort.direction,
                                                params: grid.getExportParameters()
                                            }
                                        };
                                    if (historyCombo && historyCombo.getValue() == 1) {
                                        params.isHistory = true;
                                    }
                                    Ext.get('export_body').dom.value =
                                        Ext.encode(params);
                                    Ext.get('exportform').dom.submit();
                                }
                            }, {
                                text: 'CSV',
                                handler: function(){
                                    var context = Zenoss.env.device_uid || Zenoss.env.PARENT_CONTEXT;
                                    if (context == "/zport/dmd/Events") {
                                        context = location.pathname.replace('/viewEvents', '');
                                    }
                                    var grid = Ext.getCmp(gridId),
                                    state = Ext.getCmp(gridId).getState(),
                                    historyCombo = Ext.getCmp('history_combo'),
                                    params = {
                                        type: 'csv',
                                        params: {
                                            uid: context,
                                            fields: Ext.pluck(state.columns, 'id'),
                                            sort: state.sort.property,
                                            dir: state.sort.direction,
                                            params: grid.getExportParameters()
                                        }
                                    };
                                    if (historyCombo && historyCombo.getValue() == 1) {
                                        params.isHistory = true;
                                    }
                                    Ext.get('export_body').dom.value =
                                        Ext.encode(params);
                                    Ext.get('exportform').dom.submit();
                                }
                            }]
                        }
                    },
                    {
                        text: _t('Configure'),
                        id: 'configure-button',
                        //iconCls: 'customize',
                        menu: {
                            items: configureMenuItems
                        }
                    },{
                        xtype: 'tbfill'
                    },{
                        id: 'lastupdated',
                        xtype: 'tbtext',
                        cls: 'lastupdated',
                        text: _t('Updating...')
                    },{
                        xtype: 'refreshmenu',
                        ref: 'refreshmenu',
                        id: 'refresh-button',
                        iconCls: 'refresh',
                        text: _t('Refresh'),
                        handler: function() {
                            var grid = Ext.getCmp(gridId);
                            if (grid.isVisible(true)) {
                                grid.refresh();
                            }
                        }
                    },
                    tbarItems
                ]
            });
            Zenoss.EventConsoleTBar.superclass.constructor.call(this, config);
        },
        doLastUpdated: function() {
            var box = Ext.getCmp('lastupdated'),
            dt = new Date(),
            dtext = dt.format('g:i:sA');
            box.setText(_t('Last updated at ') + dtext);
        },
        setContext: function(uid) {
            var commands = Ext.getCmp('event-commands-menu');
            if (commands) {
                commands.setContext(uid);
            }
        }
    });

    /**
     * @class Zenoss.EventPanelSelectionModel
     * @extends Zenoss.ExtraHooksSelectionModel
     *
     */
        Ext.define("Zenoss.EventPanelSelectionModel", {
            extend:"Zenoss.ExtraHooksSelectionModel",
            selectState: null,
            badIds: {},
            mode: 'MULTI',
            constructor: function(config){
                this.callParent([config]);
                this.on('select', this.handleRowSelect, this);
                this.on('deselect', this.handleRowDeSelect, this);
                this.on('selectionchange', function(selectionmodel) {
                    // Disable buttons if nothing selected (and vice-versa)
                    var actions = Zenoss.events.EventPanelToolbarActions;
                    var actionsToChange = [actions.acknowledge, actions.close, actions.unclose,
                                           actions.reopen, actions.reclassify];
                    var newDisabledValue = !selectionmodel.hasSelection() || !selectionmodel.selectState === 'All';
                    Ext.each(actionsToChange, function(actionButton) {
                        actionButton.setDisabled(newDisabledValue);
                    });
                });


            },
            getGrid: function() {
                if (!Ext.isDefined(this.grid)) {
                    this.grid = Ext.getCmp(this.gridId);
                }
                return this.grid;
            },
            handleRowSelect: function(sm, record, index){
                if (record) {
                    delete this.badIds[record.get("evid")];
                }
            },
            handleRowDeSelect: function(sm, record, index){
                if (this.selectState && record) {
                    this.badIds[record.get("evid")] = 1;
                }
            },
            onStoreLoad: function() {
                var store = this.grid.getStore();
                if (this.selectState == 'All') {
                    this.suspendEvents();
                    var items = Zenoss.util.filter(store.data.items, function(item){
                        return (! this.badIds[item.get('evid')]);
                    }, this);
                    this.select(items, false, true);
                    this.resumeEvents();
                    this.fireEvent('selectionchange', this);
                }
            },
            selectEventState: function(state){
                var record,
                me = this,
                grid = this.getGrid(),
                store = grid.getStore();
                if (state === 'All') {

                    // surpress events
                    return this.selectAll(true);
                    this.fireEvent('selectionchange', this);
                }
                this.clearSelections(true);
                // Suspend events to avoid firing the whole chain for every row
                this.suspendEvents();

                Ext.each(store.data.items, function(record){
                    if (record) {
                        if (record.data.eventState == state) {
                            me.select(record, true);
                        }
                    }
                });
                this.selectState = state;

                // Bring events back and fire one selectionchange for the batch
                this.resumeEvents();
                this.fireEvent('selectionchange', this);
            },
            clearSelectState: function() {
                this.selectState = null;
                this.grid.getStore().un('datachanged', this.onStoreLoad, this);
                this.grid.disableSavedSelection(false);
            },
            setSelectState: function(state) {
                this.selectState = state;
                if (state === 'All') {
                    this.grid.getStore().on('datachanged', this.onStoreLoad, this);
                    this.grid.disableSavedSelection(true);
                }
            },
            selectNone: function(){
                this.clearSelections(true);
                // Fire one selectionchange to make buttons figure out their
                // disabledness
                this.fireEvent('selectionchange', this);
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

            clearSelections: function(fast){
                if (this.isLocked() || !this.grid) {
                    return;
                }

                // Suspend events to avoid firing the whole chain for every row
                this.suspendEvents();
                if(!fast){
                    //make sure all rows are deselected so that UI renders properly
                    //base class only deselects rows it knows are selected; so we need
                    //to deselect rows that may have been selected via selectstate
                    this.deselect(this.grid.getStore().data.items);
                }
                // Bring events back and fire one selectionchange for the batch
                this.resumeEvents();
                this.fireEvent('selectionchange', this);

                this.badIds = {};
                Zenoss.EventPanelSelectionModel.superclass.clearSelections.apply(this, arguments);
            }
        });

    /**
     * @class Zenoss.EventsJsonReader
     * @extends Zenoss.ExtraHooksSelectionModel
     *
     * Subclass the LiveGrid JsonReader so that we can override how data is fetched
     * from a record that is returned by the router. Custom details use keys that
     * contain dots (zenpacks.foo.bar.baz) so we need to force key-method access.
     */
    Ext.define("Zenoss.EventsJsonReader", {
        extend: "Ext.data.reader.Json",
        alias: 'reader.events',
        createAccessor : function(){
            return function(expr) {
                return function(obj){
                    return obj[expr];
                };
            };
        }()
    });



    /**
     * @class Zenoss.events.Store
     * @extend Zenoss.DirectStore
     * Direct store for loading ip addresses
     */
    Ext.define("Zenoss.events.Store", {
        extend: "Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.events.Model',
                initialSortColumn: "firstTime",
                initialSortDirection: 'DESC',
                pageSize: Zenoss.settings.eventConsoleBufferSize,
                proxy: {
                    type: 'direct',
                    directFn: config.directFn || Zenoss.remote.EventsRouter.query,
                    reader: {
                        type: 'events',
                        root: 'events',
                        totalProperty: 'totalCount'
                    }
                }


            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.SimpleEventColumnModel", {
        extend: "Ext.grid.ColumnModel",
        alias: ['widget.SimpleEventColumnModel'],
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


    Zenoss.events.customColumns = {};
    Zenoss.events.registerCustomColumn = function(dataIndex, obj) {
        Zenoss.events.customColumns[dataIndex] = obj;
    };

    /**
     * @class Zenoss.events.Grid
     * @extends Zenoss.FilterGridPanel
     * Base Class for the event panels
     **/
    Ext.define('Zenoss.events.Grid', {
        extend: 'Zenoss.FilterGridPanel',
        rowcolors: false,
        constructor: function(config) {
            var me = this;
            config = config || {};
            config.viewConfig = config.viewConfig || {};
            Ext.applyIf(config.viewConfig, {
                getRowClass: function(record, index) {
                    var stateclass = record.get('eventState')=='New' ?
                        'unacknowledged':'acknowledged';
                    var sev = Zenoss.util.convertSeverity(record.get('severity'));
                    var rowcolors = me.rowcolors ? 'rowcolor rowcolor-':'';
                    var cls = rowcolors + sev + '-' + stateclass + ' ' + stateclass;
                    return cls;
                }

            });
            this.callParent(arguments);
            this.on('itemclick', this.onItemClick, this );
        },
        initComponent: function() {
            this.getSelectionModel().grid = this;
            this.callParent(arguments);
        },
        onItemClick: function(){
            this.getSelectionModel().clearSelectState();
        },
        listeners: {
            'beforerender': function(){
                this.rowcolors = Ext.state.Manager.get('rowcolor');
                // Some event consoles (Impact Events) do not use severity
                // config colors.  Check and see if it's being used before
                // trying to use it.
                var rowcolorsCheckItem = Ext.getCmp('rowcolors_checkitem');
                if (rowcolorsCheckItem)
                    rowcolorsCheckItem.setChecked(this.rowcolors);
            }
        },
        getSelectionParameters: function() {
            var grid = this,
            sm = grid.getSelectionModel(),
            evids = [],  // Event IDs selected
            sels = sm.getSelections();  // UI records selected

            var selectedAll = (sm.selectState == 'All');
            if (selectedAll) {
                // If we are selecting all, we don't want to send back any evids.
                // this will make the operation happen on the filter's result
                // instead of whatever the view seems to have selected.
                sels = [];
            } else {
                Ext.each(sels, function(record){
                    evids[evids.length] = record.data.evid;
                });
            }

            // Don't run if nothing is selected.
            if (!selectedAll && Ext.isEmpty(sels)) {
                return false;
            }

            var params = {
                evids: evids,
                excludeIds: sm.badIds
            };
            Ext.apply(params, this.getUpdateParameters());
            return params;
        },
        clearFilters: function(){
            this.filterRow.clearFilters();
        },
        /*
         * Create parameters used for exporting events. This differs from
         * getSelectionParameters in that if no events are selected, all of
         * the events matching the current filters are exported.
         */
        getExportParameters: function() {
            var params = this.getSelectionParameters();
            if (params === false) {
                params = {
                    evids: [],
                    excludeIds: []
                };
                Ext.apply(params, this.getUpdateParameters());
            }
            return params;
        },
        /*
         * Build parameters for updates (don't need to include sort information).
         */
        getUpdateParameters: function() {
            var o = {};
            o.params = this.filterRow.getSearchValues();
            return o;
        },
        toggleRowColors: function(bool) {
            this.rowcolors = bool;
            Ext.state.Manager.set('rowcolor', bool);
            this.refresh();
        },
        restoreURLState: function() {
            var qs = window.location.search.replace(/^\?/, ''),
            state = Ext.urlDecode(qs).state;
                if (state) {
                    try {
                        state = Ext.decode(Zenoss.util.base64.decode(decodeURIComponent(state)));
                        this.applyState(state);

                    } catch(e) { }
                }
        },
        clearURLState: function() {
            var qs = Ext.urlDecode(window.location.search.replace(/^\?/, ''));
            if (qs.state) {
                delete qs.state;
                qs = Ext.urlEncode(qs);
                if (qs) {
                    window.location.search = '?' + Ext.urlEncode(qs);
                } else {
                    window.location.search = '';
                }
            }
        },
        getPermalink: function() {
            var l = window.location,
            path = l.protocol + '//' + l.host + l.pathname + l.hash,
            st = Zenoss.util.base64.encode(Ext.encode(this.getState()));
            return path + '?state=' + st;
        },
        resetGrid: function() {
            Ext.state.Manager.clear(this.getItemId());
            this.clearFilters();
            Zenoss.remote.EventsRouter.column_config({}, function(result){
                var results = [],
                store = this.getStore(),
                grid = this,
                filters = this.defaultFilters;
                Ext.each(result, function(r){
                    results[results.length] = Ext.decode(r);
                });
                var columns = results;
                    this.reconfigure(null, columns);
                this.filterRow.onGridColumnMove();

                // need to resize the filters to be the same size as the column
                // it is still off a little bit but much better than not doing this
                this.filterRow.eachFilterColumn(function(col) {
                    var width = col.getWidth();
                    if (width) {
                        col.filterField.setWidth(width - 2);
                    }

                    // reapply the default filters
                    if (Ext.isDefined(filters[col.id])) {
                        col.filterField.setValue(filters[col.id]);
                        // let the filters know we changed
                        grid.filterRow.onChange();
                    }
                });
                // resort by default sorter
                    store.sort(store.sorters.get(0));
            }, this);
        },
        updateRows: function(){
            this.refresh();
        }
    });

    /**
     * @class Zenoss.SimpleEventGridPanel
     * @extends Ext.ux.grid.livegrid.GridPanel
     * Shows events in a grid panel similar to that on the event console.
     * Fixed columns.
         * @constructor
         */
    Ext.define("Zenoss.SimpleEventGridPanel", {
            extend:"Zenoss.events.Grid",
            alias: ['widget.SimpleEventGridPanel'],
        constructor: function(config){

            var id = config.id || Ext.id();
            config.viewConfig = config.viewConfig || {};
                Ext.applyIf(config.viewConfig, {
                    getRowClass: function(record, index) {
                        var stateclass = record.get('eventState')=='New' ?
                            'unacknowledged':'acknowledged';
                        var sev = Zenoss.util.convertSeverity(record.get('severity'));
                        var rowcolors = Ext.state.Manager.get('rowcolor') ? 'rowcolor rowcolor-' : '';
                        var cls = rowcolors + sev + '-' + stateclass + ' ' + stateclass;
                        return cls;
                    }
                });
            Ext.applyIf(config, {
                id: 'eventGrid' + id,
                stripeRows: true,
                stateId: Zenoss.env.EVENTSGRID_STATEID || 'default_eventsgrid',
                enableDragDrop: false,
                stateful: true,
                rowSelectorDepth: 5,
                store: Ext.create('Zenoss.events.Store', {}),
                appendGlob: true,
                selModel: new Zenoss.EventPanelSelectionModel({
                    grid: this
                }),
                autoExpandColumn: Zenoss.env.EVENT_AUTO_EXPAND_COLUMN || '',
                defaultFilters: {
                    severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
                    eventState: [Zenoss.STATUS_NEW, Zenoss.STATUS_ACKNOWLEDGED]
                },
                viewConfig: {
                    getRowClass: function(record, index) {
                        var stateclass = record.get('eventState')=='New' ?
                            'unacknowledged':'acknowledged';
                        var sev = Zenoss.util.convertSeverity(record.get('severity'));
                        var rowcolors = Ext.state.Manager.get('rowcolor') ? 'rowcolor rowcolor-' : '';
                        var cls = rowcolors + sev + '-' + stateclass + ' ' + stateclass;
                        return cls;
                    }
                }
            }); // Ext.applyIf
            Zenoss.SimpleEventGridPanel.superclass.constructor.call(this, config);
            this.on('itemdblclick', this.onRowDblClick, this);
        }, // constructor
        onRowDblClick: function(view, record, e) {
            var evid = record.get('evid'),
                url = '/zport/dmd/Events/viewDetail?evid='+evid;
            window.open(url, evid.replace(/-/g,'_'),
                        "status=1,width=600,height=500,resizable=1");
        },
        initComponent: function() {
            this.callParent(arguments);

            /**
             * @event eventgridrefresh
             * Fires when the events grid is refreshed.
             * @param {Zenoss.SimpleEventGridPanel} this The gridpanel.
             */
            this.addEvents('eventgridrefresh');
        },
        /**
         *Since on a regular event console you can not choose which columns
         * are present we are overriding the default implementation of getState
         * to not remember the widths of columns that are not visible.
         * This is necessary because of our column definitions were creating
         * cookies larger than 8192 (the default zope max cookie size)
         **/
        getState: function(){

            var val = Zenoss.SimpleEventGridPanel.superclass.getState.call(this);
            // do not store the state of the hidden ones
            val.columns = Zenoss.util.filter(val.columns, function(col) {
                return !col.hidden;
            });
            return val;
        },
        refresh: function() {
            this.callParent(arguments);
            this.fireEvent('eventgridrefresh', this);
        }
    }); // SimpleEventGridPanel




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
                    sm.selectEventState('All');
                    sm.setSelectState("All");
                }
            },{
                text: 'None',
                handler: function(){
                    var grid = Ext.getCmp('select-button').ownerCt.ownerCt,
                    sm = grid.getSelectionModel();
                    sm.clearSelections();
                    sm.clearSelectState();
                }
            }]
        }
    };


    Ext.define("Zenoss.EventGridPanel", {
        extend: "Zenoss.SimpleEventGridPanel",
        alias: ['widget.EventGridPanel'],
        border:false,
        constructor: function(config) {
            var evtGrid = this;
            Ext.applyIf(config, {
                tbar: new Zenoss.EventConsoleTBar({
                    gridId: config.id,
                    actionsMenu: config.actionsMenu,
                    commandsMenu: config.commandsMenu
                })
            });
            Zenoss.EventGridPanel.superclass.constructor.call(this, config);
        },

        onRowDblClick: function(view, record, e) {
            var evid = record.get('evid'),
                combo = Ext.getCmp('history_combo'),
                history = (combo.getValue() == '1') ? 'History' : '',
                url = '/zport/dmd/Events/view'+history+'Detail?evid='+evid;
            window.open(url, evid.replace(/-/g,'_'),
                        "status=1,width=600,height=500,resizable=1");
        },
        setContext: function(uid){
            Zenoss.EventGridPanel.superclass.setContext.call(this, uid);
            var toolbar = this.getTopToolbar();
            if (toolbar && Ext.isDefined(toolbar.setContext)) {
                toolbar.setContext(uid);
            }
        }
    });



    Ext.define("Zenoss.EventRainbow", {
        extend:"Ext.Toolbar.TextItem",
        alias: ['widget.eventrainbow'],
        constructor: function(config) {
            var severityCounts = {
                critical: {count: 0, acknowledged_count: 0},
                error:    {count: 0, acknowledged_count: 0},
                warning:  {count: 0, acknowledged_count: 0},
                info:     {count: 0, acknowledged_count: 0},
                debug:    {count: 0, acknowledged_count: 0},
                clear:    {count: 0, acknowledged_count: 0}
            };
            config = Ext.applyIf(config || {}, {
                height: 45,
                directFn: Zenoss.remote.DeviceRouter.getInfo,
                text: Zenoss.render.events(severityCounts, config.count || 3)
            });
            Zenoss.EventRainbow.superclass.constructor.call(this, config);
        },
        setContext: function(uid){
            this.directFn({uid:uid, keys:['events']}, function(result){
                if (Zenoss.env.contextUid && Zenoss.env.contextUid != uid) {
                    return;
                }
                this.updateRainbow(result.data.events);
            }, this);
        },
        updateRainbow: function(severityCounts) {
            this.setText(Zenoss.render.events(severityCounts, this.count));
        }
    });



})(); // end of function namespace scoping
