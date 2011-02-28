(function(){ // Local scope

/**
 * Global Ext settings.
 */
Ext.BLANK_IMAGE_URL = '/++resource++zenui/img/s.gif';

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
Zenoss.STATUS_NEW = 1;
Zenoss.STATUS_ACKNOWLEDGED = 2;
Zenoss.STATUS_SUPPRESSED = 3;
Zenoss.STATUS_CLOSED = 4; // Closed by the user.
Zenoss.STATUS_CLEARED = 5; // Closed by a matching clear event.
Zenoss.STATUS_DROPPED = 6; // Dropped via a transform.
Zenoss.STATUS_AGED = 7; // Closed via automatic aging.

/**
 * Namespace for anonymous scripts to attach data to avoid dumping it into
 * the global namespace.
 */
Ext.namespace('Zenoss.env');

Ext.QuickTips.init();

Ext.state.Manager.setProvider(new Ext.state.CookieProvider({
    expires: new Date(new Date().getTime()+(1000*60*60*24*30)) //30 days from now
}));

/*
 * Hook up all Ext.Direct requests to the connection error message box.
 */
Ext.Direct.on('event', function(e){
    if ( Ext.isDefined(e.result) && Ext.isDefined(e.result.asof) ) {
        Zenoss.env.asof = e.result.asof || null;
    }
});

Ext.Direct.on('event', function(e){
    if (Ext.isDefined(e.result) && Ext.isDefined(e.result.msg)) {
        var success = e.result.success || false;
        if (success) {
            Zenoss.message.success(e.result.msg);
        }
        else {
            Zenoss.message.error(e.result.msg);
        }
    }
});

Ext.Direct.on('exception', function(e) {
    if (e.message.startswith("Error parsing json response") &&
        e.message.endswith("null")) {
        window.location.reload();
        return;
    }
    Ext.Msg.show({
        title: _t('Server Exception'),
        msg: '<p>' + _t('The server reported the following error:') + '</p>' +
            '<p class="exception-message">' + e.message + '</p>' +
            '<p>' + _t('The system has encountered an error.') + ' ' +
            _t('Please reload the page.') + '</p>' ,
        buttons: { yes: _t('Reload Page'), cancel: _t('Dismiss') },
        minWidth: 300,
        fn: function(buttonId, text, opt) {
            if ('yes' == buttonId) {
                window.location.reload();
            }
        }
    });
});

/*
 * Hide the server exception MessageBox if we get a good response. Primarily
 * used to have the event console starting functioning after a temporary
 * inability to reach the server.
 */
Ext.Direct.on('event', function(e){
    var message_box = Ext.Msg.getDialog();
    if (message_box != null && message_box.title == 'Server Exception') {
        if (Ext.isDefined(e.result)) {
            Ext.Msg.hide();
        }
    }
});

Ext.namespace('Zenoss.flares');

/**
 * An invisible layer that contains all the Flares.
 * Must be the highest layer in order for Flares to show up.
 */
Zenoss.flares.Container = Ext.extend(Ext.Container, {
    _layoutDelay: null,
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            id: 'flare-container',
            baseCls: 'x-flare-container',
            alignment: 't-t',
            width: '100%',
            zindex: 400000,
            items: []
        });

        Zenoss.flares.Container.superclass.constructor.call(this, config);
    },
    onRender : function(ct, position) {
        this.el = ct.createChild({
            cls: this.baseCls + '-layer',
            children: [{
                cls: this.baseCls + '-body'
            }]
        });
        this.body = this.el.child('.' + this.baseCls + '-body');
        this.el = new Ext.Layer({ zindex: this.zindex }, this.el);

        Zenoss.flares.Container.superclass.onRender.apply(this, arguments);
        this.el.alignTo(document, this.alignment);
    },
    getLayoutTarget: function() {
        return this.body;
    },
    onShow: function() {
        this.el.show();
        Zenoss.flares.Container.superclass.onShow.apply(this, arguments);
    },
    onRemove: function() {
        // Move the sticky items back to the top. Wait a few microseconds to do it in case more items are
        // being removed at the same time.
        if ( !this._layoutDelay ) {
            this._layoutDelay = new Ext.util.DelayedTask(this.doLayout, this);
        }
        this._layoutDelay.delay(500);
    },
    show: function() {
        if ( !this.rendered ) {
            this.render(Ext.getBody());
        }
        Zenoss.flares.Container.superclass.show.apply(this, arguments);
    },
    onLayout: function() {
        Ext.each(this.items.items, function(item, index, items) {
            if ( item.canLayout() ) {
                if ( index == 0 ) {
                    item.anchorTo(this.el, this.alignment);
                }
                else {
                    item.anchorTo(items[index - 1].el, 'bl');
                }
            }
        }, this);
        Zenoss.flares.Container.superclass.onLayout.apply(this, arguments);
    }
});

/**
 * The UI manager for flares.
 */
Zenoss.flares.Manager = {
    container: new Zenoss.flares.Container(),
    INFO: 'x-flare-info',
    ERROR: 'x-flare-error',
    WARNING: 'x-flare-warning',
    DEBUG: 'x-flare-debug',
    SUCCESS: 'x-flare-success',
    CRITICAL: 'x-flare-critical',
    /**
     * Add the flare to the container and show it.
     *
     * @param flare Zenoss.flares.Flare
     */
    flare: function(flare) {
        flare.setAnimateTarget(Zenoss.flares.Manager.container.el);
        Zenoss.flares.Manager.container.add(flare);
        Zenoss.flares.Manager.container.doLayout();
        flare.show();
    },
    /**
     * Format a message and create a Flare.
     *
     * @param message string A message template
     * @param type string One of the status types assigned to this class (ex: INFO, ERROR)
     * @param args array Optional orguments to fill in the message template
     */
    _formatFlare: function(message, type, args) {
        args = Array.prototype.slice.call(args, 1);
        var flare = new Zenoss.flares.Flare(message, args, { iconCls: type });
        Zenoss.flares.Manager.flare(flare);
        return flare;
    },
    /**
     * Show a Flare with the info status.
     *
     * @param message string A message template
     * @param args mixed Optional orguments to fill in the message template
     */
    info: function(message, args) {
        return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.INFO, arguments);
    },
    error: function(message, args) {
        return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.ERROR, arguments);
    },
    warning: function(message, args) {
        return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.WARNING, arguments);
    },
    debug: function(message, args) {
        return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.DEBUG, arguments);
    },
    critical: function(message, args) {
        return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.CRITICAL, arguments);
    },
    success: function(message, args) {
        return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.SUCCESS, arguments);
    }
};

/**
 * Flares are growl like flash messages. Used for transient notifications. Flares are
 * managed by Zenoss.flares.Manager.
 *
 * Example:
 *
 * Zenoss.flares.Manager.info('{0} was saved as {1}.', itemName, newItemName);
 */
Zenoss.flares.Flare = Ext.extend(Ext.Window, {
    _task: null,
    _closing: false,
    focus: Ext.emptyFn,
    constructor: function(message, params, config) {
        if ( Ext.isArray(message) ) {
            var children = [];
            Ext.each(message, function(m) {
                children.push({ tag: 'li', html: m });
            });

            message = Ext.DomHelper.markup({
                tag: 'ul',
                children: children
            });
        }

        Ext.applyIf(config, {
            headerAsText: false,
            bodyCssClass: config.iconCls || 'x-flare-info',
            baseCls: 'x-flare',
            plain: false,
            draggable: false,
            shadow: false,
            closable: true,
            resizable: false,
            delay: 5000, // How long to show the message for
            alignment: 't-t',
            duration: 0.2, // How long to do the opening slide in
            hideDuration: 1, // How long to do the closing fade out
            template: new Ext.Template(message, { compiled: true } ),
            dismissOnClick: true
        });

        Ext.applyIf(config, {
            bodyCfg: {
                cls: 'x-flare-body',
                children: [
                    {cls: 'x-flare-icon'},
                    {
                        cls: 'x-flare-message',
                        html: config.template.apply(params)
                    }
                ]
            }
        });

        Zenoss.flares.Flare.superclass.constructor.call(this, config);
    },
    initEvents: function() {
        Zenoss.flares.Flare.superclass.initEvents.apply(this, arguments);

        if ( this.dismissOnClick ) {
            this.mon(this.el, 'click', function() { this.hide(); }, this);
        }
    },
    initComponent: function() {
        if ( this.delay ) {
            this._task = new Ext.util.DelayedTask(this.hide, this);
        }

        Zenoss.flares.Flare.superclass.initComponent.call(this);
    },
    _afterShow: function() {
        Zenoss.flares.Flare.superclass.show.call(this);
        if ( this._task ) {
            this._task.delay(this.delay);
       }
    },
    /**
     * Make this Flare "stick". It will not fade away and must manually be dismissed by the user.
     */
    sticky: function() {
        if ( this._task ) {
            this._task.cancel();
            delete this._task;
        }
    },
    animShow: function() {
        this.el.slideIn('t', {
            duration: this.duration,
            callback: this._afterShow,
            scope: this
        });
    },
    close: function() {
        this.hide();
    },
    animHide: function() {
        this._closing = true;
        this.el.ghost("b", {
            duration: this.hideDuration,
            remove: false,
            callback : function () {
                this.destroy();
            }.createDelegate(this)
        });
    },
    canLayout: function() {
        if ( !this._closing ) {
            // Only move if it's not already closing
            return Zenoss.flares.Flare.superclass.canLayout.apply(this, arguments);
        }
    }
});

Ext.namespace('Zenoss.messaging');
/**
 * Message for Zenoss.messaging.Messenger. This is for back-compat and should not be used directly.
 */
Zenoss.messaging.Message = Ext.extend(Object, {
    INFO: 0,                // Same as in messaging.py
    WARNING: 1,                // Same as in messaging.py
    CRITICAL: 2,                // Same as in messaging.py
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            body: '',
            priority: this.INFO,
            sticky: false
        });
        Ext.apply(this, config);
    }
});

/**
 * An interface to the old messaging API. This is for back-compat and should not be used directly.
 */
Zenoss.messaging.Messenger = Ext.extend(Ext.util.Observable, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            interval: 30000
        });
        Ext.apply(this, config);
        Zenoss.messaging.Messenger.superclass.constructor.call(this, config);
        this.addEvents('message');
    },
    init: function() {
        this._task = new Ext.util.DelayedTask(function(){
            this.checkMessages();
        }, this);
        this._task.delay(this.interval);
        this.checkMessages();
    },
    checkMessages: function() {
        Zenoss.remote.MessagingRouter.getUserMessages({}, function(results) {
            Ext.each(results.messages, function(m) {
                this.send(m);
            }, this);
        }, this);
    },
    send: function(msgConfig) {
        var message = new Zenoss.messaging.Message(msgConfig);
        this.fireEvent('message', this, message);

        var flare;
        if ( message.priority  === Zenoss.messaging.Message.WARNING ) {
            flare = Zenoss.flares.Manager.warning(message.body);
        }
        else if ( message.priority  === Zenoss.messaging.Message.CRITICAL ) {
            flare = Zenoss.flares.Manager.critical(message.body)
        }
        else {
            flare = Zenoss.flares.Manager.info(message.body);
        }

        if ( message.sticky ) {
            flare.sticky();
        }
    }
});

Zenoss.messenger = new Zenoss.messaging.Messenger();

Ext.onReady(function() {
    Zenoss.flares.Manager.container.show();
    Zenoss.messenger.init();
});

/**
 * Inform the user with a message. This is usually represented with a Flare. Use
 * this interface to alert users.
 */
Zenoss.message = {
     /**
     * Show a message with the info status.
     *
     * @param message string A message template
     * @param args mixed Optional orguments to fill in the message template
     */
    info: function(message, args) {
        Zenoss.flares.Manager.info.apply(null, arguments);
    },
    error: function(message, args) {
        Zenoss.flares.Manager.error.apply(null, arguments);
    },
    warning: function(message, args) {
        Zenoss.flares.Manager.warning.apply(null, arguments);
    },
    debug: function(message, args) {
        Zenoss.flares.Manager.debug.apply(null, arguments);
    },
    /**
     * These messages have a critical error icon and stay until dismissed by the user.
     */
    critical: function(message, args) {
        Zenoss.flares.Manager.critical.apply(null, arguments).sticky();
    },
    success: function(message, args) {
        Zenoss.flares.Manager.success.apply(null, arguments);
    }
}

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

var origGetDragData = Ext.grid.GridDragZone.prototype.getDragData;
Ext.override(Ext.grid.GridDragZone, {
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
Zenoss.LargeToolbar = Ext.extend(Ext.Toolbar, {
    constructor: function(config) {
        Ext.applyIf(config, {
            cls: 'largetoolbar',
            height: 45,
            border: false,
            style:'border-top:1px solid #b8b8b8;border-bottom:1px solid #949494;'
        });
        Zenoss.LargeToolbar.superclass.constructor.apply(
            this, arguments);
    }
});

Ext.reg('largetoolbar', Zenoss.LargeToolbar);

/**
 * @class Zenoss.ExtraHooksSelectionModel
 * @extends Ext.grid.RowSelectionModel
 * A selection model that fires extra events.
 */
Zenoss.ExtraHooksSelectionModel = Ext.extend(
   Ext.ux.grid.livegrid.RowSelectionModel, {
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
 * @class Zenoss.LiveGridInfoPanel
 * @extends Ext.Toolbar.TextItem
 * Toolbar addition that displays, e.g., "Showing 1-10 of 100 events"
 * @constructor
 * @grid {Object} the GridPanel whose information should be displayed
 */
Zenoss.LiveGridInfoPanel = Ext.extend(Ext.Toolbar.TextItem, {

    displayMsg : 'Displaying {0} - {1} of {2} events',
    emptyMsg: 'No events',
    cls: 'livegridinfopanel',

    initComponent: function() {
        this.setText(this.emptyMsg);
        if (this.grid) {
            this.grid = Ext.getCmp(this.grid);
            var me = this;
            this.view = this.grid.getView();
            this.view.init = this.view.init.createSequence(function(){
                me.bind(this);
            }, this.view);
        }
        Zenoss.LiveGridInfoPanel.superclass.initComponent.call(this);
    },
    updateInfo : function(rowIndex, visibleRows, totalCount) {
        var msg = totalCount === 0 ?
            this.emptyMsg :
            String.format(this.displayMsg, rowIndex+1,
                          rowIndex+visibleRows, totalCount);
        this.setText(msg);
    },
    bind: function(view) {
        this.view = view;
        var st = view.ds;

        /*
        st.on('loadexception',   this.enableLoading,  this);
        st.on('beforeload',      this.disableLoading, this);
        st.on('load',            this.enableLoading,  this);
        */
        view.on('rowremoved',    this.onRowRemoved,   this);
        view.on('rowsinserted',  this.onRowsInserted, this);
        view.on('beforebuffer',  this.beforeBuffer,   this);
        view.on('cursormove',    this.onCursorMove,   this);
        view.on('buffer',        this.onBuffer,       this);
        //view.on('bufferfailure', this.enableLoading,  this);

    },
    onCursorMove : function(view, rowIndex, visibleRows, totalCount) {
        this.updateInfo(rowIndex, visibleRows, totalCount);
    },

    onRowsInserted : function(view, start, end) {
        this.updateInfo(view.rowIndex, Math.min(view.ds.totalLength,
                view.visibleRows-view.rowClipped), view.ds.totalLength);
    },
    onRowRemoved : function(view, index, record) {
        this.updateInfo(view.rowIndex, Math.min(view.ds.totalLength,
                view.visibleRows-view.rowClipped), view.ds.totalLength);
    },
    beforeBuffer : function(view, store, rowIndex, visibleRows, totalCount,
                            options) {
        //this.loading.disable();
        this.updateInfo(rowIndex, visibleRows, totalCount);
    },
    onBuffer : function(view, store, rowIndex, visibleRows, totalCount) {
        //this.loading.enable();
        this.updateInfo(rowIndex, visibleRows, totalCount);
    }
});
Ext.reg('livegridinfo', Zenoss.LiveGridInfoPanel);

/**
 * @class Zenoss.FilterGridView
 * @extends Ext.grid.GridView
 * A GridView that includes a row below the header with a row filter.
 * @constructor
 */
Zenoss.FilterGridView = Ext.extend(Ext.ux.grid.livegrid.GridView, {
    rowHeight: 22,
    rowColors: false,
    liveSearch: true,
    _valid: true,
    constructor: function(config) {
        if (typeof(config.displayFilters)=='undefined')
            config.displayFilters = true;
        Zenoss.FilterGridView.superclass.constructor.apply(this,
            arguments);
        Ext.applyIf(this.lastOptions, this.defaultFilters || {});
    },
    lastOptions: {},
    initEvents: function(){
        Zenoss.FilterGridView.superclass.initEvents.call(this);
        this.addEvents('filterchange');
        this.addEvents('filtertoggle');
    },
    initData: function(ds, cm) {
        this.un('beforebuffer', this.onBeforeBuffer,  this);
        cm.un('hiddenchange',   this.updateHeaders,   this);

        this.on('beforebuffer', this.onBeforeBuffer,  this);
        cm.on('hiddenchange',   this.updateHeaders,   this);

        Zenoss.FilterGridView.superclass.initData.call(this, ds, cm);

    },
    // Return an object representing the state of the grid
    getFilterParams: function(hash) {
        var sinfo = this.grid.store.sortInfo,
            o = {
                sort: sinfo.field,
                dir: sinfo.direction
            };
        this.applyFilterParams({params:o});
        if (hash) {
            o.hashcheck = this.grid.lastHash;
        }
        return o;
    },
    // Gather the current values of the filter and apply them to a given
    // object.
    applyFilterParams: function(options, globbing) {
        var params = this.lastOptions || {},
            i, filter, query, dt, excludeGlobChars = ['*','"'];
        options = options || {};
        globbing = (this.appendGlob && (Ext.isDefined(globbing) ? globbing : true));
        for(i=0;i<this.filters.length;i++){
            filter = this.filters[i];
            query = filter.getValue();
            if (query) {
                if (globbing && filter.xtype=="textfield" && filter.vtype != "numcmp" &&
                        filter.vtype != "numrange" &&
                        excludeGlobChars.indexOf(query.charAt(query.length-1)) === -1) {
                    query += "*";
                }
                params[filter.id] = query;
                if (filter.xtype=='datefield'){
                    dt = new Date(query);
                    query = dt.format(
                        Zenoss.date.UniversalSortableDateTime);
                }
            } else {
                delete params[filter.id];
            }
        }
        Ext.apply(options.params, {
            params: Ext.util.JSON.encode(params),
            uid: this.contextUid
        });
        // Store them for later, just in case
        this.lastOptions = params;
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.updateLiveRows(this.rowIndex, true, true, false);
    },
    getContext: function() {
        return this.contextUid;
    },
    updateLiveRows: function(index, forceRepaint, forceReload) {
        if ( this.isValid() ) {
            return Zenoss.FilterGridView.superclass.updateLiveRows.call(this, index, forceRepaint, forceReload);
        }
        return false;
    },
    onBeforeLoad: function(store, options) {
        this.applyFilterParams(options);
        return Zenoss.FilterGridView.superclass.onBeforeLoad.call(this,
            store, options);
    },
    onBeforeBuffer: function(view, store, rowIndex, visibleRows,
                             totalCount, options) {
        this.applyFilterParams(options);
        return true;
    },
    getFilterCt: function() {
        return Ext.select('.x-grid3-filter');
    },
    hideFilters: function() {
        this.setFiltersDisplayed(false);
    },
    showFilters: function() {
        this.setFiltersDisplayed(true);
    },
    clearFilters: function() {
        this._valid = true;
        Ext.each(this.filters, function(ob){
            // clear out any original values
            // (for instance when we come here from the device page)
            ob.originalValue = null;
            ob.reset();
        }, this);
        this.updateLiveRows(this.rowIndex, true, true, false);
    },
    validateFilters: function() {
        var valid = true;
        Ext.each(this.filters, function(ob){
            if ( ob.isValid != undefined ) {
                valid = ob.isValid(true) && valid;
            }
        }, this);
        this._valid = valid;
        return valid;
    },
    getErrors: function() {
        var errors = [];
        Ext.each(this.filters, function(ob){
            if ( ob.getActiveError != undefined ) {
                var err = ob.getActiveError();
                if ( err ) {
                    errors.push(err);
                }
            }
        }, this);

        return errors;
    },
    setFiltersDisplayed: function(bool) {
        // For now, always show the filters The rest of the filter-hiding
        // stuff is still in place, so just remove this and put back the
        // menu item when we're ready to do so.
        bool = true;
        this.displayFilters = bool;
        this.getFilterCt().setDisplayed(bool);
        this.fireEvent('filtertoggle');
        if(bool) this.renderEditors();
        this.layout();
    },
    renderFilterRow: function() {
        var cs = this.getColumnData(),
            ct = new Ext.Template(
                '<td class="x-grid3-col x-grid3-cell',
                ' x-grid3-td-{id} {css}" style="{style}" tabIndex="-1"',
                ' {cellAttr}> <div class="x-grid3-cell-inner',
                ' x-grid3-col-{id}" unselectable="on" {attr}>',
                '{value}</div></td>'),
            gridId = this.grid.id,
            buf = [],
            p = {},
            rp = {},
            rt = new Ext.Template('<tr {display} class="x-grid3-filter"',
                '>{cells}</tr>'),
            i, len, c;
        for (i=0,len=cs.length; i<len; i++) {
            if (this.cm.isHidden(i)) continue;
            c = cs[i];
            p.id = c.id;
            p.css = 'x-grid3-cell-filter';
            p.attr ='id="filtergrid-'+ gridId + '_' +c.id+'"';
            p.cellAttr = "";
            p.value = '';
            buf[buf.length] = ct.apply(p);
        }
        rp.tstyle = 'width:'+this.getTotalWidth()+';';
        rp.cols = buf.length;
        rp.cells = buf.join("");
        rp.display = this.displayFilters?'':'style="display:none"';
        //rp.display = '';
        return rt.apply(rp);
    },
    filters: [],
    /*
     * this.reset() has an annoying habit of blurring existing filter
     * fields and taking away row stripes. This is the resetting part of
     * the code, but we use updateLiveRows() instead of refresh(), which
     * fixes the problem.
     */
    nonDisruptiveReset: function() {
        this.ds.modified = [];
        //this.grid.selModel.clearSelections(true);
        this.rowIndex      = 0;
        this.lastScrollPos = 0;
        this.lastRowIndex = 0;
        this.lastIndex    = 0;
        this.adjustVisibleRows();
        this.adjustScrollerPos(-this.liveScroller.dom.scrollTop,
            true);
        this.showLoadMask(false);
        // this.reset(false);
        this.updateLiveRows(this.rowIndex, true, true);
    },
    renderEditors: function() {
        if (!this.displayFilters){
            return;
        }
        Ext.each(this.filters, function(ob){ob.destroy();});
        this.filters = [];
        var cs = this.getColumnData(),
            gridId = this.grid.id,
            i, len, c, config, fieldid, id;
        for (i=0,len=cs.length; i<len; i++) {
            if (this.cm.isHidden(i)) continue;
            c = cs[i];
            fieldid = c.id;
            id = 'filtergrid-' + gridId + '_' + fieldid;
            config = this.cm.config[i].filter;
            // if there was no explicit filter then
            // the column is not filterable
            var enable_filtering = !Ext.isEmpty(this.cm.config[i].filter);
            if (config===false) {
                config = {xtype: 'panel', reset: function(){},
                          getValue: function(){}};
                this.filters[this.filters.length] = Ext.create(config);
                continue;
            } else if (!config) {
                config = {xtype:'textfield'};
            }

            if (enable_filtering !== true) {
                config.disabled = true;
            }

            Ext.apply(config, {
                id:fieldid,
                enableKeyEvents: true,
                selectOnFocus: true,
                listeners: {
                    render: function(){
                        Zenoss.registerTooltipFor(fieldid);
                    }
                }
            });
            Ext.applyIf(config, {
                validationDelay: 500,
                validateOnBlur: false
            });

            var filter = new Ext.ComponentMgr.create(config);
            if (this.lastOptions) {
                var newValue = this.lastOptions[fieldid];
                filter.setValue(newValue);
            }
            filter.setWidth('100%');
            this.filters[this.filters.length] = filter;

            filter.liveSearchTask = new Ext.util.DelayedTask(function() {
                this.validFilter('');
            }, this);

            if (filter instanceof Ext.form.TextField) {
                filter.on('valid', this.validFilter, this);
                filter.on('invalid', this.onInvalidFilter, this);
            }

            if (filter instanceof Zenoss.MultiselectMenu) {
                filter.on('select', function(field, e) {
                    this.liveSearchTask.delay(500);
                }, filter);
                filter.on('change', function(field, e) {
                    this.liveSearchTask.delay(500);
                }, filter);
            }
            new Ext.Panel({
                frame: false,
                border: false,
                layout: 'fit',
                renderTo: id,
                items: filter
            });
        }
    },
    isValid: function() {
        return this._valid;
    },
    validFilter: function(filter) {
        // Ext calls valid twice when a textfield is emptied
        if (Ext.isObject(filter) && Ext.isEmpty(filter.getValue())) {
            filter.liveSearchTask.delay(500);
            return;
        }

        // Check all filters to determine if we are valid
        this.validateFilters();
        this.fireEvent('filterchange', this);

        if (this.liveSearch) {
            this.nonDisruptiveReset();
        }
    },
    onInvalidFilter: function() {
        // If one filter is invalid, all are
        this._valid = false;
        this.fireEvent('filterchange', this);
        var errors = this.getErrors();
        if ( errors ) {
            Zenoss.message.error(errors);
        }
        else {
            Zenoss.message.error(_t('Error loading, grid has invalid filters.'));
        }
    },
    updateHeaders: function() {
        Zenoss.FilterGridView.superclass.updateHeaders.call(this);
        this.renderEditors();
    },
    renderUI: function() {
        Zenoss.FilterGridView.superclass.renderUI.call(this);
    },
    renderHeaders : function(){
        var html = Zenoss.FilterGridView.superclass.renderHeaders.call(this);
        html = html.slice(0, html.length-8);
        html = html + this.renderFilterRow() + '</table>';
        return html;
    },
    getState: function(){
        // Update last options from the filter widgets
        this.applyFilterParams(this.lastOptions, false);
        // Iterate over last options, setting defaults where appropriate
        var options = {};
        Ext.iterate(this.lastOptions, function(k){
            var defaults = this.defaultFilters || {},
                dflt = defaults[k],
                opt = this.lastOptions[k];
            if (dflt) {
                var match;
                if (Ext.isDate(dflt) && Ext.isDate(opt)) {
                    var delta = Math.abs(dflt.getTime() - opt.getTime());
                    // If they're within a second, they match. We don't
                    // have finer resolution in the UI.
                    match = delta <= 1000;
                } else {
                    match = dflt==opt;
                }
                if (!match) {
                    options[k] = opt;
                }
            } else {
                options[k] = opt;
            }
        }, this);
        return {
            displayFilters: this.displayFilters,
            options: options
        };
    },
    getFilterButton: function(){
        return Ext.getCmp(this.filterbutton);
    },
    onRowSelect: function(row) {
        if (this.rowColors) {
            this.addRowClass(row, this.selectedRowClass + '-rowcolor');
        }
        Zenoss.FilterGridView.superclass.onRowSelect.apply(this, arguments);
    },
    onRowDeselect: function(row) {
        if (this.rowColors) {
            this.removeRowClass(row, this.selectedRowClass + '-rowcolor');
        }
        Zenoss.FilterGridView.superclass.onRowDeselect.apply(this, arguments);
    },
    onRowOver: function(e, t) {
        if (this.rowColors) {
            if((row = this.findRowIndex(t)) !== false && !e.within(this.getRow(row), true)){
                this.addRowClass(row, 'x-grid3-row-over-rowcolor');
            }
        }
        Zenoss.FilterGridView.superclass.onRowOver.apply(this, arguments);
    },
    onRowOut: function(e, t) {
        if (this.rowColors) {
            if((row = this.findRowIndex(t)) !== false && !e.within(this.getRow(row), true)){
                this.removeRowClass(row, 'x-grid3-row-over-rowcolor');
            }
        }
        Zenoss.FilterGridView.superclass.onRowOut.apply(this, arguments);
    },
    getRowClass: function(record, index) {
        var stateclass = record.get('eventState')=='New' ?
                            'unacknowledged':'acknowledged';
        var sev = Zenoss.util.convertSeverity(record.get('severity'));
        var rowcolors = this.rowColors ? 'rowcolor rowcolor-' : '';
        var cls = rowcolors + sev + '-' + stateclass + ' ' + stateclass;
        return cls;
    },
    toggleRowColors: function(bool){
        this.rowColors = bool;
        Ext.state.Manager.set('rowcolor', bool);
        this.updateLiveRows(this.rowIndex, true, false);
    },
    toggleLiveSearch: function(bool){
        this.liveSearch = bool;
        Ext.state.Manager.set('livesearch', bool);
    },
    applyState: function(state) {
        // For now, always show the filters The rest of the filter-hiding
        // stuff is still i'll gn place, so just remove this and put back the
        // menu item when we're ready to do so.
        this.displayFilters = true; //state.displayFilters;
        // End always show filters
        this.lastOptions = state.options;
        // Apply any default filters specified in the constructor
        Ext.applyIf(this.lastOptions, this.defaultFilters || {});
        /*
        var btn = Ext.getCmp(this.filterbutton);
        btn.on('render', function(){
            this.setChecked(state.displayFilters);
        }, btn);
        */
    },
    resetFilters: function(){
        this.lastOptions = {};
        Ext.applyIf(this.lastOptions, this.defaultFilters || {});
        //this.getFilterButton().setChecked(false);
    }
});

/**
 * @class Zenoss.FilterGridPanel
 * @extends Ext.grid.GridPanel
 * A GridPanel that uses a FilterGridView.
 * @constructor
 */
Zenoss.FilterGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
    initStateEvents: function(){
        Zenoss.FilterGridPanel.superclass.initStateEvents.call(this);
        this.mon(this.view, 'filterchange', this.saveState, this);
        this.mon(this.view, 'filtertoggle', this.saveState, this);
    },
    getView : function(){
        if(!this.view){
            this.view = new Zenoss.FilterGridView(this.viewConfig);
        }
        return this.view;
    },
    restoreURLState: function() {
        var qs = window.location.search.replace(/^\?/, ''),
            state = Ext.urlDecode(qs).state,
            noop;
        if (state) {
            try {
                state = Ext.decode(Zenoss.util.base64.decode(decodeURIComponent(state)));
                this.applyState(state);

            } catch(e) { noop(); }
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
            path = l.protocol + '//' + l.host + l.pathname,
            st = Zenoss.util.base64.encode(Ext.encode(this.getState()));
        return path + '?state=' + st;
    },
    initState: function() {
        Zenoss.FilterGridPanel.superclass.initState.apply(this, arguments);
        this.restoreURLState();
        var livesearchitem = Ext.getCmp(this.view.livesearchitem);
        if(livesearchitem) {
            var liveSearch = Ext.state.Manager.get('livesearch');
            if (!Ext.isDefined(liveSearch)){
                liveSearch = livesearchitem.checked;
            }else{
                livesearchitem.on('render', function(){
                    this.setChecked(liveSearch);
                },livesearchitem);
            }
            this.view.liveSearch = liveSearch;
        }
        var rowColors = Ext.state.Manager.get('rowcolor');
        this.view.rowColors = rowColors;
        if (this.view.rowcoloritem) {
            var rowcoloritem = Ext.getCmp(this.view.rowcoloritem);
            rowcoloritem.on('render', function(){
                this.setChecked(rowColors);
            }, rowcoloritem);
        }
    },
    getState: function(){
        var val = Zenoss.FilterGridPanel.superclass.getState.call(this);
        var filterstate = this.getView().getState();
        val.filters = filterstate;
        return val;
    },
    applyState: function(state){
        // We need to remove things from the state that don't apply to this
        // context, so we'll ditch things referring to columns that aren't
        // in the initial config.
        var availcols = Ext.pluck(this.initialConfig.cm.config, 'id'),
            cols = [],
            filters = {};
        Ext.each(state.columns, function(col){
            if (availcols.indexOf(col.id)>-1) cols.push(col);
        });
        Ext.iterate(state.filters.options, function(op){
            if (availcols.indexOf(op)>-1) {
                filters[op] = state.filters.options[op];
            }
        });
        state.columns = cols;
        state.filters.options = filters;
        // Apply the filter information to the view, the rest to this
        this.getView().applyState(state.filters);
        Zenoss.FilterGridPanel.superclass.applyState.apply(this, arguments);
    },
    resetGrid: function() {
        Ext.state.Manager.clear(this.getItemId());
        var view = this.getView();
        view.resetFilters();
        Zenoss.remote.EventsRouter.column_config({}, function(result){
            var results = [];
            Ext.each(result, function(r){
                results[results.length] = Ext.decode(r);
            });
            var cm = new Ext.grid.ColumnModel(results);
            this.store.sortInfo = this.store.defaultSort;
            this.reconfigure(this.store, cm);
            view.fitColumns();
            view.showLoadMask(true);
            view.nonDisruptiveReset();
            this.saveState();
            this.clearURLState();
        }, this);
    },
    setContext: function(uid) {
        this.view.setContext(uid);
    },
    hideFilters: function() { this.getView().hideFilters(); },
    showFilters: function() { this.getView().showFilters(); },
    clearFilters: function() { this.getView().clearFilters(); },


    /*
     * Assemble the parameters that define the grid state.
     */
    getQueryParameters: function() {
        this.view.applyFilterParams({'params':this.view.ds.sortInfo});
        return this.view.ds.sortInfo;
    },

    /*
     * Build parameters for updates (don't need to include sort information).
     */
    getUpdateParameters: function() {
        var o = {};
        this.view.applyFilterParams({params: o});
        return o;
    },

    /*
     * Assemble the parameters that define the records selected. This by
     * necessity includes query parameters, since ranges need row indices.
     */
    getSelectionParameters: function() {
        var grid = this,
            sm = grid.getSelectionModel(),
            ranges = sm.getPendingSelections(true),
            evids = [],
            sels = sm.getSelections();

        if (sm.selectState == 'All') {
            // If we are selecting all, we don't want to send back any evids.
            // this will make the operation happen on the filter's result
            // instead of whatever the view seems to have selected.
            sels = [];
        }
        Ext.each(sels, function(record){
            evids[evids.length] = record.data.evid;
        });
        if (!ranges && !evids) return false;
        var params = {
            evids: evids,
            excludeIds: sm.badIds
        };
        Ext.apply(params, this.getUpdateParameters());
        return params;
    },

    /*
     * A shortcut for updated grid rows.
     */
    updateRows: function() {
        var view = this.getView();
        view.updateLiveRows(view.rowIndex, true, true);
    }
});

Ext.reg('filtergridpanel', Zenoss.FilterGridPanel);

/**
 * @class Zenoss.MultiselectMenu
 * @extends Ext.Toolbar.Button
 * A combobox-like menu that allows one to toggle each option, and is able
 * to deliver its value like a form field.
 * @constructor
 */
Zenoss.MultiselectMenu = Ext.extend(Ext.Toolbar.Button, {
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
Ext.reg('multiselectmenu', Zenoss.MultiselectMenu);

/**
 * @class Zenoss.StatefulRefreshMenu
 * @extends Ext.Menu
 * A refresh menu that is able to save and restore its state.
 * @constructor
 */
Zenoss.StatefulRefreshMenu = Ext.extend(Ext.menu.Menu, {
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

Ext.reg('statefulrefreshmenu', Zenoss.StatefulRefreshMenu);

/**
 * @class Zenoss.RefreshMenu
 * @extends Ext.SplitButton
 * A button that manages refreshing and allows the user to set a polling
 * interval.
 * @constructor
 */
Zenoss.RefreshMenuButton = Ext.extend(Ext.SplitButton, {
    constructor: function(config) {
        var menu = {
            xtype: 'statefulrefreshmenu',
            id: 'evc_refresh',
            trigger: this,
            items: [{
                xtype: 'menutextitem',
                cls: 'refreshevery',
                text: 'Refresh every'
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
        config.menu = menu;
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
                this.handler();
            }
            this.refreshTask.delay(this.interval*1000);
        }
    }
});
Ext.reg('refreshmenu', Zenoss.RefreshMenuButton);


// FIXME: Refactor this to be much, much smarter about its own components.
Zenoss.DetailPanel = Ext.extend(Ext.Panel, {
    isHistory: false,
    constructor: function(config){
        config.onDetailHide = config.onDetailHide || function(){var _x;};
        config.layout = 'border';
        config.border = false;
        config.defaults = {border:false};
        config.items = [{
            id: 'evdetail_hd',
            region: 'north',
            layout: 'border',
            height: 50,
            cls: 'evdetail_hd',
            defaults: {border: false},
            items: [{
                region: 'west',
                width: 77,
                layout: 'hbox',
                defaults: {border: false},
                items: [{
                    id: 'severity-icon',
                    cls: 'severity-icon'
                },{
                    id: 'evdetail-sep',
                    cls: 'evdetail-sep'
                }]
            },{
                region: 'center',
                id: 'evdetail-summary',
                html: ''
            },{
                region: 'east',
                id: 'evdetail-tools',
                layout: 'hbox',
                width: 57,
                defaults: {border: false},
                items: [{
                    id: 'evdetail-popout',
                    cls: 'evdetail-popout'
                },{
                    id: 'evdetail_tool_close',
                    cls: 'evdetail_close'
                }]
            }]
        },{
            id: 'evdetail_bd',
            region: 'center',
            defaults: {
                frame: false,
                border: false
            },
            autoScroll: true,
            layout: 'table',
            layoutConfig: {
                columns: 1,
                tableAttrs: {
                    style: {
                        width: '90%'
                    }
                }
            },
            cls: 'evdetail_bd',
            items: [{
                id: 'evdetail_props',
                cls: 'evdetail_props',
                html: ''
            },{
                id: 'show_details',
                cls: 'show_details',
                hidden: true,
                html: 'Show more details...'
            },{
                id: 'full_event_props',
                cls: 'full_event_props',
                hidden: true,
                html: ''
            },{
                id: 'evdetail-log-header',
                cls: 'evdetail-log-header',
                hidden: true,
                html: '<'+'hr/><'+'h2>LOG<'+'/h2>'
            },{
                xtype: 'form',
                id: 'log-container',
                defaults: {border: false},
                frame: true,
                layout: 'table',
                style: {'margin-left':'3em'},
                hidden: true,
                labelWidth: 1,
                items: [{
                    id: 'detail-logform-evid',
                    xtype: 'hidden',
                    name: 'evid'
                },{
                    style: 'margin:0.75em',
                    width: 300,
                    xtype: 'textfield',
                    name: 'message',
                    hidden: Zenoss.Security.doesNotHavePermission('Manage Events'),
                    id: 'detail-logform-message'
                },{
                    xtype: 'button',
                    type: 'submit',
                    name: 'add',
                    hidden: Zenoss.Security.doesNotHavePermission('Manage Events'),
                    text: 'Add',
                    handler: function(btn, e){
                        var form = Ext.getCmp('log-container'),
                            vals = form.getForm().getValues(),
                            params = {};
                        Ext.apply(params, vals);
                        Zenoss.remote.EventsRouter.write_log(
                         params,
                         function(provider, response){
                             Ext.getCmp(
                                 'detail-logform-message').setRawValue('');
                             Ext.getCmp(config.id).load(
                                 Ext.getCmp(
                                     'detail-logform-evid').getValue());
                        });
                    }
                }]
            },{
                id: 'evdetail_log',
                cls: 'log-content',
                hidden: true
            }]
        }];
        Zenoss.DetailPanel.superclass.constructor.apply(this, arguments);
    },
    setSummary: function(summary){
        var panel = Ext.getCmp('evdetail-summary');
        if (panel && panel.el){
            panel.el.update(summary);
        }
    },
    setSeverityIcon: function(severity){
        var panel = Ext.getCmp('severity-icon');
        this.clearSeverityIcon();
        panel.addClass(severity);
    },
    clearSeverityIcon: function() {
        var panel = Ext.getCmp('severity-icon');
        Ext.each(Zenoss.env.SEVERITIES,
            function(sev){
                sev = sev[1];
                panel.removeClass(sev.toLowerCase());
            }
        );
    },
    update: function(event) {
        // For the Event Detail Page, set up the page
        // links. This is to make sure they link to the correct place
        // when we go to the new UI

        // device_link
        if (event.device_url) {
            event.device_link = Zenoss.render.default_uid_renderer(
                                 event.device_url,
                                 event.device_title);
        } else {
            event.device_link = event.device_title;
        }
        // component_link
        if (event.component_url) {
            event.component_link = Zenoss.render.default_uid_renderer(
                                    event.component_url,
                                    event.component_title);
        }else {
            event.component_link = event.component_title;
        }

        // eventClass_link
        event.eventClass_link = Zenoss.render.EventClass(event.eventClass_url,
                                                        event.eventClass);

        var top_prop_template = new
            Ext.XTemplate.from('detail_table_template');
        var full_prop_template = new
            Ext.XTemplate.from('fullprop_table_template');
        var log_template = new Ext.XTemplate.from('log_table_template');
        var severity = Zenoss.util.convertSeverity(event.severity),
            html = top_prop_template.applyTemplate(event),
            prophtml = full_prop_template.applyTemplate(event),
            loghtml = log_template.applyTemplate(event);


        this.setSummary(event.summary);
        this.setSeverityIcon(severity);
        Ext.getCmp('evdetail_props').el.update(html);
        Ext.getCmp('full_event_props').el.update(prophtml);
        Ext.getCmp('evdetail_log').el.update(loghtml);
        Ext.getCmp('detail-logform-evid').setValue(event.evid);
    },
    wipe: function(){
        this.clearSeverityIcon();
        this.setSummary('');
        Ext.getCmp('show_details').hide();
        Ext.getCmp('evdetail-log-header').hide();
        Ext.getCmp('evdetail_log').hide();
        Ext.getCmp('evdetail_props').hide();
        Ext.getCmp('full_event_props').hide();
        Ext.getCmp('log-container').hide();
    },
    show: function(){
        Ext.getCmp('show_details').show();
        Ext.getCmp('evdetail-log-header').show();
        Ext.getCmp('evdetail_log').show();
        Ext.getCmp('evdetail_props').show();
        if (this.isPropsVisible)
            Ext.getCmp('full_event_props').show();
        Ext.getCmp('log-container').show();

    },
    isPropsVisible: false,
    showProps: function(){
        var el = Ext.getCmp('full_event_props'),
            tgl = Ext.getCmp('show_details');
        if (!el.hidden){
            el.hide();
            this.isPropsVisible = false;
            tgl.body.update('Show more details...');
        } else {
            el.show();
            this.isPropsVisible = true;
            tgl.body.update('Hide details');
        }
    },
    popout: function(){
         var evid = Ext.getCmp('detail-logform-evid').getValue(),
             url = this.isHistory ? 'viewHistoryDetail' : 'viewDetail';
         url = url +'?evid='+evid;
         window.open(url, evid.replace(/-/g,'_'),
             "status=1,width=600,height=500");
    },
    bind: function(){
        var showlink = Ext.getCmp('show_details').getEl(),
            btn = Ext.getCmp('evdetail_tool_close').getEl(),
            pop = Ext.getCmp('evdetail-popout').getEl();

        showlink.un('click', this.showProps);
        showlink.on('click', this.showProps);
        if (btn){
            btn.un('click', this.onDetailHide);
            btn.on('click', this.onDetailHide);
        }
        if (pop){
            pop.un('click', this.popout, this);
            pop.on('click', this.popout, this);
        }
    },
    load: function(event_id){
        Zenoss.remote.EventsRouter.detail({
                evid:event_id
            },
            function(result){
                var event = result.event[0];
                this.update(event);
                this.bind();
                this.show();
            }, this);
    }
});
Ext.reg('detailpanel', Zenoss.DetailPanel);


/*
 * This EventActionManager class will handle issuing a router request for
 * actions to be taken on events. When constructing this class you must
 * provide the findParams() method and may provide the onFinishAction() method.
 * Unless you mimic the existing params structure, you'll need to override
 * isLargeRequest() as well in order to determine whether or not a dialog and
 * progress bar should be shown.
 */
var EventActionManager = Ext.extend(Ext.util.Observable, {
    constructor: function(config) {
        var me = this;
        config = config || {};
        Ext.applyIf(config, {
            cancelled: false,
            dialog: new Ext.Window({
                width: 300,
                modal: true,
                title: _t('Processing...'),
                layout: 'form',
                closable: false,
                bodyBorder: false,
                border: false,
                hideBorders: true,
                plain: true,
                buttonAlign: 'left',
                items: [{
                    xtype: 'panel',
                    ref: 'panel',
                    layout: 'form',
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
                    Ext.Msg.show({
                        title: _t('Error'),
                        msg: _t('There was an error handling your request.'),
                        buttons: Ext.MessageBox.OK
                    });
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
Zenoss.ColumnFieldSet = Ext.extend(Ext.form.FieldSet, {
    constructor: function(userConfig) {

        var baseConfig = {
            items: {
                layout: 'column',
                border: false,
                items: userConfig.__inner_items__,
                defaults: {
                    layout: 'form',
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

Ext.reg('ColumnFieldSet', Zenoss.ColumnFieldSet);


/**
 * General utilities
 */
Ext.namespace('Zenoss.util');

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
}

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
    realign: Ext.Shadow.prototype.realign.createInterceptor(
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

})(); // End local scope
