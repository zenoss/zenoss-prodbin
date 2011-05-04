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
        var addevent = new Ext.Window({
            title: _t('Create Event'),
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
                defaults: {width: 180},
                autoHeight: true,
                border: false,
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
                    store: Zenoss.env.EVENT_CLASSES,
                    typeAhead: true,
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true
                }],
                buttons: [{
                    text: _t('Submit'),
                    formBind: true,
                    handler: function(){
                        var form = Ext.getCmp('addeventform');
                        Zenoss.remote.EventsRouter.add_event(
                            form.getForm().getValues(),
                            function(){
                                addevent.hide();
                                var grid = Ext.getCmp(gridId);
                                var view = grid.getView();
                                view.updateLiveRows(
                                    view.rowIndex, true, true);
                            }
                        );
                    }
                },{
                    text: _t('Cancel'),
                    handler: function(){
                        addevent.hide();
                    }
                }]
            }]

            });

        addevent.show(this);
    }

    /*
     * Show the dialog that allows one to classify an event
     */
    function showClassifyDialog(gridId) {

        var win = new Ext.Window({
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
                border: false,
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
                    emptyText: _t('Select an event class'),
                    selectOnFocus: true,
                    id: 'evclass_combo'
                }],
                buttons: [{
                    text: _t('Submit'),
                    formBind: true,
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
                            Ext.Msg.show({
                                title: 'Error',
                                msg: _t('No events were selected.'),
                                buttons: Ext.MessageBox.OK
                            });
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
                    handler: function(){
                        win.destroy();
                    }
                }
                         ]
            }]

            });

        win.show(this);
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
                var grid = btn.grid || this.ownerCt.ownerCt,
                view = grid.getView();
                view.updateLiveRows(view.rowIndex, true, true);
            }
        })
    };

    Zenoss.EventConsoleTBar = Ext.extend(Zenoss.LargeToolbar, {
        constructor: function(config){
            var gridId = config.gridId,
                showActions = true,
                showCommands = true,
                tbarItems = config.tbarItems || [];

            if (!gridId) {
                throw ("Event console tool bar did not receive a grid id");
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
                        ranges = sm.getPendingSelections(true),
                        pluck = Ext.pluck,
                        uids = pluck(pluck(pluck(rows, 'data'), 'device'), 'uid'),
                        opts = Ext.apply(grid.view.getFilterParams(true), {
                            uids: uids,
                            ranges: ranges,
                            hashcheck: 'none'
                        });
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
                            var archive = selection.value == 1,
                                grid = Ext.getCmp(gridId),
                                params = {
                                    uid: grid.view._context,
                                    archive: archive
                                };
                            grid.getStore().load({ params: params });
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
                    return null;
                }
            });

            Ext.applyIf(config, {
                border: false,
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

                                    var state = Ext.getCmp(gridId).getState(),
                                        historyCombo = Ext.getCmp('history_combo'),
                                        params = {
                                            type: 'xml',
                                            isHistory: false,
                                            params: {
                                                uid: context,
                                                fields: Ext.pluck(state.columns, 'id'),
                                                sort: state.sort.field,
                                                dir: state.sort.direction,
                                                params: state.filters.options
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
                                    var state = Ext.getCmp(gridId).getState(),
                                        historyCombo = Ext.getCmp('history_combo'),
                                        params = {
                                            type: 'csv',
                                            params: {
                                                uid: context,
                                                fields: Ext.pluck(state.columns, 'id'),
                                                sort: state.sort.field,
                                                dir: state.sort.direction,
                                                params: state.filters.options
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
                            items: [
                                {
                                    id: 'rowcolors_checkitem',
                                    xtype: 'menucheckitem',
                                    text: 'Show severity row colors',
                                    handler: function(checkitem) {
                                        var checked = !checkitem.checked;
                                        var view = Ext.getCmp(gridId).getView();
                                        view.toggleRowColors(checked);
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
                                    text: 'Save this configuration...',
                                    handler: function(){
                                        var grid = Ext.getCmp(gridId),
                                        link = grid.getPermalink();
                                        Ext.Msg.show({
                                            title: 'Permalink',
                                            msg: '<'+'div class="dialog-link">'+
                                                'Drag this link to your bookmark' +
                                                ' bar <'+'br/>to return to this grid '+
                                                'configuration later.'+
                                                '<'+'br/><'+'br/><'+'a href="'+
                                                link + '"> '+
                                                document.title + ' <'+'/a><'+'/div>',
                                            buttons: Ext.Msg.OK
                                        });
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
                                                    Ext.getCmp(gridId).resetGrid();
                                            }
                                        });
                                    }
                                }
                            ]
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
                            var view = Ext.getCmp(gridId).getView();
                            view.nonDisruptiveReset();
                        },
                        pollHandler: function() {
                            var view = Ext.getCmp(gridId).getView();
                            view.updateLiveRows(view.rowIndex, true, true);
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
    Zenoss.EventPanelSelectionModel = Ext.extend(Zenoss.ExtraHooksSelectionModel, {
        selectState: null,
        badIds: {},
        initEvents: function(){
            Zenoss.EventPanelSelectionModel.superclass.initEvents.call(this);
            this.on('beforerowselect', this.handleBeforeRowSelect, this);
            this.on('rowselect', this.handleRowSelect, this);
            this.on('rowdeselect', this.handleRowDeSelect, this);
            this.on('selectionchange', function(selectionmodel) {
                // Disable buttons if nothing selected (and vice-versa)
                var actions = Zenoss.events.EventPanelToolbarActions;
                var actionsToChange = [actions.acknowledge, actions.close, actions.unclose,
                                       actions.reopen, actions.reclassify];
                var newDisabledValue = !selectionmodel.hasSelection();
                Ext.each(actionsToChange, function(actionButton) {
                    actionButton.setDisabled(newDisabledValue);
                })
            })

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


    /**
     * @class Zenoss.EventsJsonReader
     * @extends Zenoss.ExtraHooksSelectionModel
     *
     * Subclass the LiveGrid JsonReader so that we can override how data is fetched
     * from a record that is returned by the router. Custom details use keys that
     * contain dots (zenpacks.foo.bar.baz) so we need to force key-method access.
     */
    Zenoss.EventsJsonReader = Ext.extend(Ext.ux.grid.livegrid.JsonReader, {
        createAccessor : function(){
            return function(expr) {
                return function(obj){
                    return obj[expr];
                };
            };
        }()
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
                reader: new Zenoss.EventsJsonReader(
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
            var store = config.store || {xtype:'EventStore'},
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
                    rowHeight: 22,
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
        onRowDblClick: function(grid, rowIndex, e) {
            var row = grid.getStore().getAt(rowIndex),
            evid = row.id,
            combo = Ext.getCmp('history_combo'),
            history = (combo.getValue() == '1') ? 'History' : '',
            url = '/zport/dmd/Events/view'+history+'Detail?evid='+evid;
            window.open(url, evid.replace(/-/g,'_'),
                        "status=1,width=600,height=500");
        },
        setContext: function(uid){
            Zenoss.EventGridPanel.superclass.setContext.call(this, uid);
            var toolbar = this.getTopToolbar();
            if (toolbar && Ext.isDefined(toolbar.setContext)) {
                toolbar.setContext(uid);
            }
        }
    });
    Ext.reg('EventGridPanel', Zenoss.EventGridPanel);


    Zenoss.EventRainbow = Ext.extend(Ext.Toolbar.TextItem, {
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
            this.directFn({uid:uid}, function(result){
                this.updateRainbow(result.data.events);
            }, this);
        },
        updateRainbow: function(severityCounts) {
            this.setText(Zenoss.render.events(severityCounts, this.count));
        }
    });
    Ext.reg('eventrainbow', Zenoss.EventRainbow);


})(); // end of function namespace scoping
