(function(){ // Local scope

/**
 * Global Ext settings.
 */
Ext.BLANK_IMAGE_URL = '/++resource++zenui/img/s.gif';
//  Ext.Compat.showErrors = true;
Ext.Compat.silent = true;

/**
 * Enable this setting to log the stack trace of all direct requests to the browser console
 **/
Zenoss.logDirectRequests = false;
if (Zenoss.logDirectRequests) {
    Ext.apply(Ext.direct.RemotingProvider.prototype, {
        queueTransaction: Ext.Function.createInterceptor(Ext.direct.RemotingProvider.prototype.queueTransaction, function(transaction) {
            // will render a stack trace on firefox
            console.error(Ext.String.format("Router: {0} Method: {1}", transaction.action, transaction.method));
        })
    });
}


/**
 * Base namespace to contain all Zenoss-specific JavaScript.
 */
Ext.namespace('Zenoss');

/**
 * Constants
 */

Zenoss.SEVERITY_CLEAR = 0;
Zenoss.SEVERITY_DEBUG = 1;
Zenoss.SEVERITY_INFO = 2;
Zenoss.SEVERITY_WARNING = 3;
Zenoss.SEVERITY_ERROR = 4;
Zenoss.SEVERITY_CRITICAL = 5;
Zenoss.STATUS_NEW = 0;
Zenoss.STATUS_ACKNOWLEDGED = 1;
Zenoss.STATUS_SUPPRESSED = 2;
Zenoss.STATUS_CLOSED = 3; // Closed by the user.
Zenoss.STATUS_CLEARED = 4; // Closed by a matching clear event.
Zenoss.STATUS_DROPPED = 5; // Dropped via a transform.
Zenoss.STATUS_AGED = 6; // Closed via automatic aging.

/**
 * Namespace for anonymous scripts to attach data to avoid dumping it into
 * the global namespace.
 */
Ext.namespace('Zenoss.env');

Ext.QuickTips.init();


Ext.define('Zenoss.state.PersistentProvider', {
    extend: 'Ext.state.Provider',
    constructor: function() {
        this.callParent(arguments);
        this.on('statechange', this.save, this);
        this.task = null;
    },
    setState: function(stateString) {
        var state = Ext.decode(stateString);
        this.state = Ext.isObject(state) ? state : {};
    },
    // Private
    save: function() {
        // in the case where we get multiple requests to
        // update the state just send one request
        if(!this.onSaveTask) {
            this.onSaveTask = new Ext.util.DelayedTask(function(){
                Zenoss.remote.MessagingRouter.setBrowserState(
                    {state: Ext.encode(this.state)}
                );
            }, this);
        }
        // delay for half a second
        this.onSaveTask.delay(500);
    }
});
Ext.state.Manager.setProvider(Ext.create('Zenoss.state.PersistentProvider'));

/*
 * Hook up all Ext.Direct requests to the connection error message box.
 */
Ext.Direct.on('event', function(e, provider){
    if ( Ext.isDefined(e.result) && e.result && Ext.isDefined(e.result.asof) ) {
        Zenoss.env.asof = e.result.asof || null;
    }
});

Ext.Direct.on('event', function(e){

    if ( Ext.isDefined(e.result) && e.result && Ext.isDefined(e.result.msg) && e.result.msg.startswith("ObjectNotFoundException") ) {
         new Zenoss.dialog.SimpleMessageDialog({
                title: _t('Stale Data Warning'),
                message: _t('Another user has edited the information on this page since you loaded it. Please reload the page.'),
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('OK'),
                    handler: function() {
                        window.location.reload();
                    }
                }, {
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
            }).show();     
        return false;
    }
});

Ext.Direct.on('event', function(e){
    if (Ext.isDefined(e.result) && e.result && Ext.isDefined(e.result.msg)) {
        var success = e.result.success || false,
            sticky = e.result.sticky || false,
            flare;
        if (success) {
            flare = Zenoss.message.success(e.result.msg);
        } else {
            flare = Zenoss.message.error(e.result.msg);
        }
        if (sticky) {
            flare.sticky();
        }
    }
});

Ext.Direct.on('exception', function(e) {
    if (e.message.startswith("Error parsing json response") &&
        e.message.endswith("null")) {
        window.location.reload();
        return;
    }
    
         new Zenoss.dialog.SimpleMessageDialog({
        title: _t('Server Exception'),
        message: '<p>' + _t('The server reported the following error:') + '</p>' +
            '<p class="exception-message">' + e.message + '</p>' +
            '<p>' + _t('The system has encountered an error.') + ' ' +
            _t('Please reload the page.') + '</p>' ,
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('OK'),
                    handler: function() {
                        window.location.reload();
                    }
                }, {
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
            }).show();  
            
});

/*
 * Hide the server exception MessageBox if we get a good response. Primarily
 * used to have the event console starting functioning after a temporary
 * inability to reach the server.
 */
Ext.Direct.on('event', function(e){
    if (Ext.Msg.isVisible()) {
        var message_box = Ext.Msg.getDialog();
        if (message_box != null && message_box.title == 'Server Exception') {
            if (Ext.isDefined(e.result)) {
                Ext.Msg.hide();
            }
        }
    }
});


/*
* Add the ability to specify an axis for autoScroll.
* autoScroll: true works just as before, but now can also do:
* autoScroll: 'x'
* autoScroll: 'y'
*
* Code by Tom23, http://www.extjs.com/forum/showthread.php?t=80663
*/

Ext.Element.prototype.setOverflow = function(v, axis) {
    axis = axis ? axis.toString().toUpperCase() : '';
    var overflowProp = 'overflow';
    if (axis == 'X' || axis == 'Y') {
        overflowProp += axis;
    }
    if(v=='auto' && Ext.isMac && Ext.isGecko2){ // work around stupid FF 2.0/Mac scroll bar bug
        this.dom.style[overflowProp] = 'hidden';
        (function(){this.dom.style[overflowProp] = 'auto';}).defer(1, this);
    }else{
        this.dom.style[overflowProp] = v;
    }
};

Ext.override(Ext.Panel, {
    setAutoScroll : function() {
        if(this.rendered && this.autoScroll){
            var el = this.body || this.el;
            if(el){
                el.setOverflow('auto', this.autoScroll);
            }
        }
    }
});

var origGetDragData = Ext.dd.DragZone.prototype.getDragData;
Ext.override(Ext.dd.DragZone, {
    getDragData: function(e) {
        var t = Ext.lib.Event.getTarget(e);
        // If it's a link, set the target to the ancestor cell so the browser
        // doesn't do the default anchor-drag behavior. Otherwise everything
        // works fine, so proceed as normal.
        if (t.tagName=='A') {
            e.target = e.getTarget('div.x-grid3-cell-inner');
        }
        return origGetDragData.call(this, e);
    }
});


/**
 * @class Zenoss.PlaceholderPanel
 * @extends Ext.Panel
 * A custom panel that displays text in its center. This panel is styled
 * with custom CSS to look temporary. It is used to show devs the names of
 * panels and should not be seen by users.
 * @constructor
 * @param {Object} config
 * @cfg {String} text The text to be displayed in the center of the panel.
 */
Zenoss.PlaceholderPanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        Ext.apply(config, {
            cls: 'placeholder',
            layout: 'fit',
            border: false,
            items: [{
                baseCls: 'inner',
                border: false,
                html: config.text,
                listeners: {'resize':function(ob){
                        ob.getEl().setStyle({'line-height':
                            ob.getEl().getComputedHeight()+'px'});
                }}
            }]
        });
        Zenoss.PlaceholderPanel.superclass.constructor.apply(
            this, arguments);
    }
});

/**
 * @class Zenoss.LargeToolbar
 * @extends Ext.Toolbar
 * A toolbar with greater height and custom CSS class. Used at the top of
 * several screens, including the event console.
 * @constructor
 */

Ext.define('Zenoss.LargeToolbar',{
    alias: 'widget.largetoolbar',
    extend: 'Ext.toolbar.Toolbar',
    constructor: function(config) {
        Ext.applyIf(config, {
            ui: 'large',
            cls: 'largetoolbar',
            height: 45,
            border: false
        });
        Zenoss.LargeToolbar.superclass.constructor.apply(
            this, arguments);
    }
});

Ext.define('Zenoss.SingleRowSelectionModel', {
    extend: 'Ext.selection.RowModel',
    mode: 'SINGLE',
    getSelected: function() {
        var rows = this.getSelection();
        if (!rows.length) {
            return null;
        }
        return rows[0];
    }
});

/**
 * @class Zenoss.ExtraHooksSelectionModel
 * @extends Ext.ux.grid.livegrid.RowSelectionModel
 * A selection model that fires extra events.
 */
Ext.define("Zenoss.ExtraHooksSelectionModel", {
    extend: "Zenoss.SingleRowSelectionModel",
    suppressDeselectOnSelect: false,
    initEvents: function() {
        Zenoss.ExtraHooksSelectionModel.superclass.initEvents.call(this);
        this.addEvents('rangeselect');
        this.on('beforerowselect', function(){
            if (this.suppressDeselectOnSelect) {
                this.selectingRow = true;
            }
        }, this);
    },
    clearSelections: function() {
        if (this.selectingRow) {
            this.suspendEvents();
        }
        Zenoss.ExtraHooksSelectionModel.superclass.clearSelections.apply(this, arguments);
        if (this.selectingRow) {
            this.resumeEvents();
            this.selectingRow = false;
        }
    },
    selectRange: function (startRow, endRow, keepExisting) {
        this.suspendEvents();
        Zenoss.ExtraHooksSelectionModel.superclass.selectRange.apply(
            this, arguments);
        this.resumeEvents();
        this.fireEvent('rangeselect', this);
    }
});


/**
 * @class Zenoss.PostRefreshHookableDataView
 * @extends Ext.DataView
 * A DataView that fires a custom event after the view has refreshed.
 * @constructor
 */
Zenoss.PostRefreshHookableDataView = Ext.extend(Ext.DataView, {
    constructor: function(config) {
        Zenoss.PostRefreshHookableDataView.superclass.constructor.apply(
            this, arguments);
        this.addEvents(
            /**
             * @event afterrefresh
             * Fires after the view has been rendered.
             * @param {DataView} this
             */
            'afterrefresh');
    }
});

Ext.extend(Zenoss.PostRefreshHookableDataView, Ext.DataView, {
    /**
     * This won't survive upgrade.
     */
    refresh: function(){
        this.clearSelections(false, true);
        this.el.update("");
        var records = this.store.getRange();
        if(records.length < 1){
            if(!this.deferEmptyText || this.hasSkippedEmptyText){
                this.el.update(this.emptyText);
            }
            this.hasSkippedEmptyText = true;
            this.all.clear();
            return;
        }
        this.tpl.overwrite(this.el, this.collectData(records, 0));
        this.fireEvent('afterrefresh', this);
        this.all.fill(Ext.query(this.itemSelector, this.el.dom));
        this.updateIndexes(0);
    }
});


/**
 * @class Zenoss.MultiselectMenu
 * @extends Ext.Toolbar.Button
 * A combobox-like menu that allows one to toggle each option, and is able
 * to deliver its value like a form field.
 * @constructor
 */
Ext.define("Zenoss.MultiselectMenu", {
    extend: "Ext.button.Button",
    alias: ["widget.multiselectmenu"],
    makeItemConfig: function(text, value) {
        var config = {
            hideOnClick: false,
            handler: function() {
                this.fireEvent('change');
            }.createDelegate(this),
            value: value,
            text: text
        };
        return config;
    },
    constructor: function(config) {
        config.menu = config.menu || [];
        Zenoss.MultiselectMenu.superclass.constructor.apply(this, arguments);
        if (Ext.isDefined(config.store)) {
            this.hasLoaded = false;
            config.store.on('load', function(s, rows) {
                this.menu.removeAll();
                Ext.each(rows, function(row){
                    var cfg = this.makeItemConfig(row.data.name, row.data.value);
                    cfg.checked = (this.defaultValues.indexOf(row.data.value)>-1);
                    this.menu.add(cfg);
                }, this);
                this.hasLoaded = true;
            }, this);
            config.store.load();
        } else {
            this.hasLoaded = true;
            Ext.each(config.source, function(o){
                var cfg = this.makeItemConfig(o.name, o.value);
                cfg.checked = !Ext.isDefined(o.checked);
                this.menu.add(cfg);
            }, this);
        }
    },
    reset: function() {
        this.setValue();
    },
    _initialValue: null,
    getValue: function() {
        if (!this.hasLoaded) {
            // Check state, otherwise return default
            return this._initialValue || this.defaultValues;
        }
        var result = [];
        Ext.each(this.menu.items.items, function(item){
            if (item.checked) result[result.length] = item.value;
        });
        return result;
    },
    setValue: function(val) {
        if (!val) {
            this.constructor(this.initialConfig);
        } else {
            function check(item) {
                var shouldCheck = false;
                try{
                    shouldCheck = val.indexOf(item.value)!=-1;
                } catch(e) {var _x;}
                item.setChecked(shouldCheck);
            }
            if (!this.hasLoaded) {
                this._initialValue = val;
                this.menu.on('add', function(menu, item) {
                    check(item);
                });
            } else {
                Ext.each(this.menu.items.items, check);
            }
        }
    }

});

/**
 * @class Zenoss.StatefulRefreshMenu
 * @extends Ext.Menu
 * A refresh menu that is able to save and restore its state.
 * @constructor
 */
Ext.define("Zenoss.StatefulRefreshMenu", {
    extend: "Ext.menu.Menu",
    alias: ['widget.statefulrefreshmenu'],
    constructor: function(config) {
        config.stateful = true;
        config.stateEvents = ['itemclick'];
        Zenoss.StatefulRefreshMenu.superclass.constructor.apply(this, arguments);
    },
    getState: function() {
        //returning raw value doesn't work anymore; need to wrap in object/array
        return [this.trigger.interval];
    },
    applyState: function(interval) {
        //old cookie value not being in an array and we can't get the value, so
        //default to 60
        var savedIntveral = interval[0] || 60;
        var items = this.items.items;
        Ext.each(items, function(item) {
            if (item.value == savedIntveral)
                item.setChecked(true);
        }, this);
        this.trigger.on('afterrender', function() {
            this.trigger.setInterval(savedIntveral);
        }, this);
    }
});


/**
 * @class Zenoss.RefreshMenu
 * @extends Ext.SplitButton
 * A button that manages refreshing and allows the user to set a polling
 * interval.
 * @constructor
 */
Ext.define("Zenoss.RefreshMenuButton", {
    extend: "Ext.button.Split",
    alias: ['widget.refreshmenu'],
    constructor: function(config) {
        var menu = {
            xtype: 'statefulrefreshmenu',
            id: config.stateId || 'evc_refresh',
            trigger: this,
            width:127,
            items: [{
                cls: 'refreshevery',
                text: 'Refresh every',
                canActivate: false
            },{
                xtype: 'menucheckitem',
                text: '1 second',
                value: 1,
                group: 'refreshgroup'
            },{
                xtype: 'menucheckitem',
                text: '5 seconds',
                value: 5,
                group: 'refreshgroup'
            },{
                xtype: 'menucheckitem',
                text: '10 seconds',
                value: 10,
                group: 'refreshgroup'
            },{
                xtype: 'menucheckitem',
                text: '30 seconds',
                value: 30,
                group: 'refreshgroup'
            },{
                xtype: 'menucheckitem',
                text: '1 minute',
                value: 60,
                checked: true,
                group: 'refreshgroup'
            },{
                xtype: 'menucheckitem',
                text: 'Manually',
                value: -1,
                group: 'refreshgroup'
            }]
        };
        Ext.applyIf(config, {
            menu: menu
        });
        Zenoss.RefreshMenuButton.superclass.constructor.apply(this,
            arguments);
        this.refreshTask = new Ext.util.DelayedTask(this.poll, this);
        this.menu.on('itemclick', function(item){
            this.setInterval(item.value);
        }, this);
        //60 is the default interval; it matches the checked item above
        this.setInterval(60);
    },
    setInterval: function(interval) {
        this.interval = interval;
        this.refreshTask.delay(this.interval*1000);
    },
    poll: function(){
        if (this.interval>0) {
            if ( !this.disabled ) {
                if (Ext.isDefined(this.pollHandler)){
                    this.pollHandler()
                }
                else{
                    this.handler(this);
                }
            }
            this.refreshTask.delay(this.interval*1000);
        }
    }
});


/*
 * This EventActionManager class will handle issuing a router request for
 * actions to be taken on events. When constructing this class you must
 * provide the findParams() method and may provide the onFinishAction() method.
 * Unless you mimic the existing params structure, you'll need to override
 * isLargeRequest() as well in order to determine whether or not a dialog and
 * progress bar should be shown.
 */
Ext.define("EventActionManager", {
    extend: "Ext.util.Observable",
    constructor: function(config) {
        var me = this;
        config = config || {};
        Ext.applyIf(config, {
            cancelled: false,
            dialog: new Ext.Window({
                width: 300,
                modal: true,
                title: _t('Processing...'),
                layout: 'anchor',
                closable: false,
                bodyBorder: false,
                border: false,
                hideBorders: true,
                plain: true,
                buttonAlign: 'left',
                items: [{
                    xtype: 'panel',
                    ref: 'panel',
                    layout: 'anchor',
                    items: [{
                        xtype: 'box',
                        ref: '../status',
                        autoEl: {
                            tag: 'p',
                            html: _t('Processing...')
                        },
                        height: 20
                    },{
                        xtype: 'progress',
                        width: '100%',
                        unstyled: true,
                        ref: '../progressBar'
                    }]
                }],
                buttons: [{
                    xtype: 'button',
                    text: _t('Cancel'),
                    ref: '../cancelButton',
                    handler: function(btn, evt) {
                        me.cancelled = true;
                        me.finishAction();
                    }
                }]
            }),
            events: {
                'updateRequestIncomplete': true,
                'updateRequestComplete': true
            },
            listeners: {
                updateRequestIncomplete: function(data) {
                    if (!me.cancelled) {
                        me.run();
                    }
                },
                updateRequestComplete: function(data) {
                    me.finishAction();
                }
            },
            isLargeRequest: function() {
                // determine if this request is going to require batch
                // requests. If you have selected more than 100 ids, show
                // a progress bar. also if you have not selected ANY and
                // are just executing on a filter, we don't have any idea
                // how many will be updated, so show a progress bar just
                // in case.
                return me.params.evids.length > 100 || me.params.evids.length == 0;
            },
            action: function(params, callback) {
                throw('The EventActionManager action must be implemented before use.');
            },
            startAction: function() {
                me.cancelled = false;
                if (me.isLargeRequest()) {
                    me.dialog.show();
                    me.dialog.status.update(_t('Processing...'));
                }
                me.run();
            },
            run: function() {
                // First request
                if (me.next_request === null) {
                    Ext.apply(me.params, {limit: 100})
                    me.action(me.params, me.requestCallback);
                }
                else {
                    Zenoss.remote.EventsRouter.nextEventSummaryUpdate({next_request: me.next_request},
                            me.requestCallback);
                }
            },
            finishAction: function() {
                me.dialog.hide();
                if (me.onFinishAction) {
                    me.onFinishAction();
                }
            },
            requestCallback: function(provider, response) {
                var data = response.result.data;

                // no data due to an error. Handle it.
                if (!data) {
                    new Zenoss.dialog.ErrorDialog({message: _t('There was an error handling your request.')});
                    me.finishAction();
                    return;
                }

                me.eventsUpdated += data.updated;

                if (data.next_request) {
                    me.next_request = data.next_request;
                    // don't try to update the progress bar if it hasn't
                    // been created due to this being a small request.
                    if (me.isLargeRequest()) {
                        var progress = data.next_request.offset/data.total;
                        me.dialog.status.update(String.format(_t('Progress: {0}%'), Math.ceil(progress*100)));
                        me.dialog.progressBar.updateProgress(progress);
                    }
                    me.fireEvent('updateRequestIncomplete', {data:data});
                }
                else {
                    me.next_request = null;
                    me.fireEvent('updateRequestComplete', {data:data});
                }
            },
            reset: function() {
                me.eventsUpdated = 0;
                me.next_request = null;
                me.dialog.progressBar.reset();
            },
            findParams: function() {
                throw('The EventActionManager findParams() method must be implemented before use.');
            },
            execute: function(actionFunction) {
                me.action = actionFunction;
                me.params = me.findParams();
                if (me.params) {
                    me.reset();
                    me.startAction();
                }
            },
            configure: function(config) {
                Ext.apply(this, config);
            }
        });
        Ext.apply(this, config);
        EventActionManager.superclass.constructor.call(this, config);
    }
});


Ext.onReady(function() {
    Zenoss.EventActionManager = new EventActionManager();
});

/**
 * @class Zenoss.ColumnFieldSet
 * @extends Ext.form.FieldSet
 * A FieldSet with a column layout
 * @constructor
 */
Ext.define("Zenoss.ColumnFieldSet", {
    extend: "Ext.form.FieldSet",
    alias: ['widget.ColumnFieldSet'],
    constructor: function(userConfig) {

        var baseConfig = {
            items: {
                layout: 'column',
                border: false,
                items: userConfig.__inner_items__,
                defaults: {
                    layout: 'anchor',
                    border: false,
                    bodyStyle: 'padding-left: 15px'
                }
            }
        };

        delete userConfig.__inner_items__;
        var config = Ext.apply(baseConfig, userConfig);
        Zenoss.ColumnFieldSet.superclass.constructor.call(this, config);

    } // constructor
}); // Zenoss.ColumnFieldSet

/**
 * General utilities
 */
Ext.namespace('Zenoss.util');

/*
* Wrap the Ext.Direct remote call passed in as func so that calls to the
* wrapped function won't be sent in a batch. If you have an expensive call that
* you really want to run in parallel with the rest of the page, wrap it in
* this.
*
* e.g. {directFn: isolatedRequest(Zenoss.remote.DeviceRouter.getTree)}
*/
Zenoss.util.isolatedRequest = function(func) {
    var provider = Ext.Direct.getProvider(func.directCfg.action),
        combineAndSend = Ext.bind(provider.combineAndSend, provider),
        newFn;
    newFn = Ext.Function.createSequence(Ext.Function.createInterceptor(func, combineAndSend),
                                combineAndSend);
    newFn.directCfg = Ext.clone(func.directCfg);
    return newFn;
};


Zenoss.util.isSuccessful = function(response) {
    // Check the results of an Ext.Direct response for success.
    return response.result && response.result.success;
};

Zenoss.util.addLoadingMaskToGrid = function(grid){
    // load mask stuff
    grid.store.proxy.on('beforeload', function(){
        var container = this.container;
        container._treeLoadMask = container._treeLoadMask || new Ext.LoadMask(this.container);
        var mask = container._treeLoadMask;
        mask.show();
    }, grid);
    grid.store.proxy.on('load', function(){
        var container = this.container;
        container._treeLoadMask = container._treeLoadMask || new Ext.LoadMask(this.container);
        var mask = container._treeLoadMask;
        mask.hide();
    }, grid);
}

Zenoss.env.SEVERITIES = [
    [5, 'Critical'],
    [4, 'Error'],
    [3, 'Warning'],
    [2, 'Info'],
    [1, 'Debug'],
    [0, 'Clear']
];

Zenoss.util.convertSeverity = function(severity){
    if (Ext.isString(severity)) return severity;
    var sevs = ['clear', 'debug', 'info', 'warning', 'error', 'critical'];
    return sevs[severity];
};

Zenoss.util.convertStatus = function(stat){
    var stati = ['New', 'Acknowledged', 'Suppressed'];
    return stati[stat];
};

Zenoss.util.render_severity = function(sev) {
    return Zenoss.render.severity(sev);
};

Zenoss.util.render_status = function(stat) {
    return Zenoss.render.evstatus(stat);
};

Zenoss.util.render_linkable = function(name, col, record) {
    var url = record.data[col.id + '_url'];
    var title = record.data[col.id + '_title'] || name;
    if (url) {
        return '<a href="'+url+'">'+title+'</a>';
    } else {
        return title;
    }
};


Zenoss.util.render_device_group_link = function(name, col, record) {
    var links = record.data.DeviceGroups.split('|'),
        returnString = "",
        link = undefined;
    // return a pipe-deliminated set of links to the ITInfrastructure page
    for (var i = 0; i < links.length; i++) {
        link = links[i];
        if (link) {
            returnString +=  '&nbsp;|&nbsp;' + Zenoss.render.DeviceGroup(link, link) ;
        }
    }

    return returnString;
};


Zenoss.util.base64 = {
    base64s : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_",
    encode: function(decStr){
        if (typeof btoa === 'function') {
             return btoa(decStr);
        }
        var base64s = this.base64s,
            i = 0,
            encOut = "",
            bits, dual, x, y, z;
        while(decStr.length >= i + 3){
            x = (decStr.charCodeAt(i) & 0xff) <<16;
            i++;
            y = (decStr.charCodeAt(i) & 0xff) <<8;
            i++;
            z = decStr.charCodeAt(i) & 0xff;
            i++;
            bits = x | y | z;
            encOut += base64s.charAt((bits & 0x00fc0000) >>18) +
                      base64s.charAt((bits & 0x0003f000) >>12) +
                      base64s.charAt((bits & 0x00000fc0) >> 6) +
                      base64s.charAt((bits & 0x0000003f));
        }
        if(decStr.length -i > 0 && decStr.length -i < 3){
            dual = Boolean(decStr.length -i -1);
            x = ((decStr.charCodeAt(i) & 0xff) <<16);
            i++;
            y = (dual ? (decStr.charCodeAt(i) & 0xff) <<8 : 0);
            bits = x | y;
            encOut += base64s.charAt((bits & 0x00fc0000) >>18) +
                      base64s.charAt((bits & 0x0003f000) >>12) +
                      (dual ? base64s.charAt((bits & 0x00000fc0) >>6) : '=') + '=';
        }
        return(encOut);
    },
    decode: function(encStr){
        if (typeof atob === 'function') {
            return atob(encStr);
        }
        var base64s = this.base64s;
        var bits;
        var decOut = "";
        var i = 0;
        for(; i<encStr.length; i += 4){
            bits = (base64s.indexOf(encStr.charAt(i)) & 0xff) <<18 |
                   (base64s.indexOf(encStr.charAt(i +1)) & 0xff) <<12 |
                   (base64s.indexOf(encStr.charAt(i +2)) & 0xff) << 6 |
                   base64s.indexOf(encStr.charAt(i +3)) & 0xff;
            decOut += String.fromCharCode((bits & 0xff0000) >>16,
                                          (bits & 0xff00) >>8, bits & 0xff);
        }
        if(encStr.charCodeAt(i -2) == 61){
            return(decOut.substring(0, decOut.length -2));
        }
        else if(encStr.charCodeAt(i -1) == 61){
            return(decOut.substring(0, decOut.length -1));
        }
        else {
            return(decOut);
        }
    }
};

// two functions for converting IP addresses
Zenoss.util.dot2num = function(dot) {
    var d = dot.split('.');
    return ((((((+d[0])*256)+(+d[1]))*256)+(+d[2]))*256)+(+d[3]);
};

Zenoss.util.num2dot = function(num) {
    var d = num % 256;
    for (var i = 3; i > 0; i--) {
        num = Math.floor(num/256);
        d = num%256 + '.' + d;
    }
    return d;
};

Zenoss.util.setContext = function(uid) {
    var ids = Array.prototype.slice.call(arguments, 1);
    Ext.each(ids, function(id) {
        Ext.getCmp(id).setContext(uid);
    });
};

/**
 * Doing Ext.each's job for it. If it's an array, do Ext.each, if the obj has an each function, use it instead.
 * @param {Object} obj Array or MixedCollection works here
 * @param {Function} filterFn
 * @param {Object} scope
 */
Zenoss.util.each = function(obj, filterFn, scope) {
    if ( Ext.isFunction(obj.each) ) {
        obj.each(filterFn, scope);
    }
    else {
        Ext.each(obj, filterFn, scope);
    }
};

/**
 * Return an array filtered by function argument; Filter function should
 * return true if a value should be included in the filtered result
 * @param {Object} arr array to be filtered
 * @param {Object} filterFn function used to filter
 */
Zenoss.util.filter = function(arr, filterFn, scope) {
    var result = [];

    Zenoss.util.each(arr, function(val) {
        var include = filterFn.call(scope || this, val);
        if (include) {
            result.push(val);
        }
    });

    return result;
};

/**
 * Copies all the properties of values to orig only if they already exist.
 * @param {Object} orig The receiver of the properties
 * @param {Object} values The source of the properties
 * @return {Object} returns orig
 **/
Zenoss.util.applyNotIf = function(orig, values) {
    var k;
    if (orig) {
        for (k in values) {
            if (k in orig) {
                orig[k] = values[k];
            }
        }
    }
    return orig;
};

/**
 * Calls a function when a component is available. If it is already
 * available then the function is called immediately
 * @param {String} componentId The id of the component we want available
 * @param {Function} func Callable function, no arguments
 * @param {Object} scope (optional) the scope in which we want to call this func
 **/
Zenoss.util.callWhenReady = function(componentId, func, scope) {
    var cmp = Ext.getCmp(componentId);
    if (Ext.isDefined(cmp)){
        if (scope){
            func.createDelegate(scope)();
        }else{
            func();
        }
    }else{
        Ext.ComponentMgr.onAvailable(componentId, func, scope);
    }

};

/**
 * This converts server side types to Ext Controls,
 * it first looks for specific types based on the field name
 * and then reverts to a translation of the type.
 * @param {string} fieldId the "name" of the field (e.g. eventClass)
 * @param {string} type can be string, int, etc
 * @returns {string} The "xtype" of the control
 **/
Zenoss.util.getExtControlType = function(fieldId, type) {
    var customControls = {
        'eventClass': 'EventClass',
        'severity': 'Severity',
        'dsnames': 'DataPointItemSelector'
    },
    types = {
        'int': 'numberfield',
        'string': 'textfield',
        'boolean': 'checkbox',
        'text': 'textarea'
    };

    // see if a component of this type is registered (then return it)
    if (Ext.ComponentMgr.isRegistered(fieldId)) {
        return fieldId;
    }

    // check our conversions defined above
    if (customControls[fieldId]) {
        return customControls[fieldId];
    }

    // default to "textfield" if we don't have it set up yet"
    return (types[type] || 'textfield');
};

/**
 * Used by classes to validate config options that
 * are required.
 * Called like this:
 *      Zenoss.util.validateConfig(config, 'store', 'view');
 **/
Zenoss.util.validateConfig = function() {
    var config = arguments[0];
    Ext.each(arguments, function(param){
        if (Ext.isString(param) && !Ext.isDefined(config[param])){
            var error =  Ext.String.format("Did not receive expected config options: {0}", param);
            if (Ext.global.console) {
                // will show a stacktrace in firebug
                console.error(error);
            }
        };
    });
};

/**
 * Proxy that will only allow one request to be loaded at a time.  Requests
 * made while the proxy is already loading a previous requests will be discarded
 */
Zenoss.ThrottlingProxy = Ext.extend(Ext.data.DirectProxy, {
    constructor: function(config){
        Zenoss.ThrottlingProxy.superclass.constructor.apply(this, arguments);
        this.loading = false;
        //add event listeners for throttling
        this.addListener('beforeload', function(proxy, options){
            if (!proxy.loading){
                proxy.loading = true;
                return true;
            }
            return false;
        });
        this.addListener('load', function(proxy, options){
            proxy.loading = false;
        });
        this.addListener('exception', function(proxy, options){
            proxy.loading = false;
        });

    }
});

/**
 * Zenoss date patterns and manipulations
 */
Ext.namespace('Zenoss.date');

/**
 * A set of useful date formats. All dates should come from the server as
 * ISO8601Long, but we may of course want to render dates in many different
 * ways.
 */
Ext.apply(Zenoss.date, {
    ISO8601Long:"Y-m-d H:i:s",
    ISO8601Short:"Y-m-d",
    ShortDate: "n/j/Y",
    LongDate: "l, F d, Y",
    FullDateTime: "l, F d, Y g:i:s A",
    MonthDay: "F d",
    ShortTime: "g:i A",
    LongTime: "g:i:s A",
    SortableDateTime: "Y-m-d\\TH:i:s",
    UniversalSortableDateTime: "Y-m-d H:i:sO",
    YearMonth: "F, Y"
});

// Fix an IE bug
Ext.override(Ext.Shadow, {
    realign: Ext.Function.createInterceptor(Ext.Shadow.prototype.realign,
        function(l, t, w, h) {
            if (Ext.isIE) {
                var a = this.adjusts;
                a.h = Math.max(a.h, 0);
            }
        }
    )
});

// Force checkbox to fire valid
var oldcbsetvalue = Ext.form.Checkbox.prototype.setValue;
Ext.override(Ext.form.Checkbox, {
    setValue: function(v) {
        var result = oldcbsetvalue.call(this, v);
        this.fireEvent('valid', this);
        return result;
    }
});

String.prototype.startswith = function(str){
    return (this.match('^'+str)==str);
};

String.prototype.endswith = function(str){
    return (this.match(str+'$')==str);
};


/* Cross-Browser Split 1.0.1
(c) Steven Levithan <stevenlevithan.com>; MIT License
An ECMA-compliant, uniform cross-browser split method
http://blog.stevenlevithan.com/archives/cross-browser-split
*/

var cbSplit;

// avoid running twice, which would break `cbSplit._nativeSplit`'s reference to the native `split`
if (!cbSplit) {

cbSplit = function (str, separator, limit) {
    // if `separator` is not a regex, use the native `split`
    if (Object.prototype.toString.call(separator) !== "[object RegExp]") {
        return cbSplit._nativeSplit.call(str, separator, limit);
    }

    var output = [],
        lastLastIndex = 0,
        flags = (separator.ignoreCase ? "i" : "") +
                (separator.multiline  ? "m" : "") +
                (separator.sticky     ? "y" : ""),
        separator = RegExp(separator.source, flags + "g"), // make `global` and avoid `lastIndex` issues by working with a copy
        separator2, match, lastIndex, lastLength;

    str = str + ""; // type conversion
    if (!cbSplit._compliantExecNpcg) {
        separator2 = RegExp("^" + separator.source + "$(?!\\s)", flags); // doesn't need /g or /y, but they don't hurt
    }

    /* behavior for `limit`: if it's...
    - `undefined`: no limit.
    - `NaN` or zero: return an empty array.
    - a positive number: use `Math.floor(limit)`.
    - a negative number: no limit.
    - other: type-convert, then use the above rules. */
    if (limit === undefined || +limit < 0) {
        limit = Infinity;
    } else {
        limit = Math.floor(+limit);
        if (!limit) {
            return [];
        }
    }

    while (match = separator.exec(str)) {
        lastIndex = match.index + match[0].length; // `separator.lastIndex` is not reliable cross-browser

        if (lastIndex > lastLastIndex) {
            output.push(str.slice(lastLastIndex, match.index));

            // fix browsers whose `exec` methods don't consistently return `undefined` for nonparticipating capturing groups
            if (!cbSplit._compliantExecNpcg && match.length > 1) {
                match[0].replace(separator2, function () {
                    for (var i = 1; i < arguments.length - 2; i++) {
                        if (arguments[i] === undefined) {
                            match[i] = undefined;
                        }
                    }
                });
            }

            if (match.length > 1 && match.index < str.length) {
                Array.prototype.push.apply(output, match.slice(1));
            }

            lastLength = match[0].length;
            lastLastIndex = lastIndex;

            if (output.length >= limit) {
                break;
            }
        }

        if (separator.lastIndex === match.index) {
            separator.lastIndex++; // avoid an infinite loop
        }
    }

    if (lastLastIndex === str.length) {
        if (lastLength || !separator.test("")) {
            output.push("");
        }
    } else {
        output.push(str.slice(lastLastIndex));
    }

    return output.length > limit ? output.slice(0, limit) : output;
};

cbSplit._compliantExecNpcg = /()??/.exec("")[1] === undefined; // NPCG: nonparticipating capturing group
cbSplit._nativeSplit = String.prototype.split;

} // end `if (!cbSplit)`

// for convenience...
String.prototype.xsplit = function (separator, limit) {
    return cbSplit(this, separator, limit);
};



})(); // End local scope
