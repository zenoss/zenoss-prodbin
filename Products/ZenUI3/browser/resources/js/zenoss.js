Ext.onReady(function(){

    /**
     * Base namespace to contain all Zenoss-specific JavaScript.
     */
    Ext.namespace('Zenoss');

    /**
     * Namespace for anonymous scripts to attach data to avoid dumping it into
     * the global namespace.
     */
    Ext.namespace('Zenoss.env');

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
            Ext.apply(config, {
                cls: 'largetoolbar',
                height: 45,
                border: false
            });
            Zenoss.LargeToolbar.superclass.constructor.apply(
                this, arguments);
        }
    });

    /**
     * @class Zenoss.ExtraHooksSelectionModel
     * @extends Ext.grid.RowSelectionModel
     * A selection model that fires extra events.
     */
    Zenoss.ExtraHooksSelectionModel = Ext.extend(
       Ext.ux.grid.livegrid.RowSelectionModel, {
        initEvents: function() {
            Zenoss.ExtraHooksSelectionModel.superclass.initEvents.call(this);
            this.addEvents('rangeselect');
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
                'afterrefresh'
            );
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
            this.fireEvent('afterrefresh', this)
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

        displayMsg : 'Displaying {0} - {1} of {2}',
        emptyMsg: 'No data to display',

        initComponent: function() {
            Zenoss.LiveGridInfoPanel.superclass.initComponent.call(this);
            if (this.grid) {
                this.view = this.grid.getView();
            }
            var me = this;
            this.view.init = this.view.init.createSequence(function(){
                me.bind(this);
            }, this.view);
        },
        updateInfo : function(rowIndex, visibleRows, totalCount) {
            var msg = totalCount == 0 ?
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
    })

    /**
     * @class Zenoss.FilterGridView
     * @extends Ext.grid.GridView
     * A GridView that includes a row below the header with a row filter.
     * @constructor
     */
    Zenoss.FilterGridView = Ext.extend(Ext.ux.grid.livegrid.GridView, {
        rowColors: false,
        constructor: function(config) {
            if (typeof(config.displayFilters)=='undefined')
                config.displayFilters = false;
            Zenoss.FilterGridView.superclass.constructor.apply(this,
                arguments);
        },
        lastOptions: {},
        initEvents: function(){
            Zenoss.FilterGridView.superclass.initEvents.call(this);
            this.addEvents('filterchange');
            this.addEvents('filtertoggle');
            this.addEvents('rowcolorchange');
        },
        maskIsDisplayed: function() {
            var dom  = this._loadMaskAnchor.dom;
            var data = Ext.Element.data;
            var mask = data(dom, 'mask');
            return mask.isDisplayed();
        },
        delayedLoadMask: function() {
            if (!this._loadMaskTask) {
                this._loadMaskTask = new Ext.util.DelayedTask(function(){
                    this.showLoadMask(true);
                }, this);
            }
            if (!this.maskIsDisplayed())
                this._loadMaskTask.delay(250);
        },
        initData: function(ds, cm) {
            var store = this.grid.store;

            this.un('beforebuffer', this.onBeforeBuffer,  this);
            cm.un('hiddenchange',   this.updateHeaders,   this);
            store.un('beforeload',  this.delayedLoadMask, this);

            this.on('beforebuffer', this.onBeforeBuffer,  this);
            cm.on('hiddenchange',   this.updateHeaders,   this);
            store.on('beforeload',  this.delayedLoadMask, this);

            Zenoss.FilterGridView.superclass.initData.call(this, ds, cm);
        },
        // Gather the current values of the filter and apply them to a given
        // object.
        applyFilterParams: function(options) {
            var params = this.lastOptions || {};
            for(i=0;i<this.filters.length;i++){
                var filter = this.filters[i];
                var oldformat;
                query = filter.getValue();
                if (query) {
                    params[filter.id] = query;
                    if (filter.xtype=='datefield'){
                        dt = new Date(query);
                        query = dt.format(
                            Zenoss.date.UniversalSortableDateTime)
                    }
                } else {
                    delete params[filter.id];
                }
            }
            Ext.apply(options.params, {
                params: Ext.util.JSON.encode(params)
            });
            // Store them for later, just in case
            this.lastOptions = params;
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
        setFiltersDisplayed: function(bool) {
            this.displayFilters = bool;
            this.getFilterCt().setDisplayed(bool);
            this.fireEvent('filtertoggle');
            if(bool) this.renderEditors();
            this.layout();
        },
        renderFilterRow: function() {
            var cs = this.getColumnData(), 
                ct = this.templates.cell,
                ct = new Ext.Template( 
                    '<td class="x-grid3-col x-grid3-cell',
                    ' x-grid3-td-{id} {css}" style="{style}" tabIndex="-1"',
                    ' {cellAttr}> <div class="x-grid3-cell-inner',
                    ' x-grid3-col-{id}" unselectable="on" {attr}>',
                    '{value}</div></td>'),
                buf = [],
                p = {},
                rp = {},
                rt = new Ext.Template('<tr {display} class="x-grid3-filter"',
                    '>{cells}</tr>');
            for (i=0,len=cs.length; i<len; i++) {
                if (this.cm.isHidden(i)) continue;
                c = cs[i];
                p.id = c.id;
                p.css = 'x-grid3-cell-filter';
                p.attr ='id="filtergrid-'+c.id+'"';
                p.cellAttr = "";
                p.value = '';
                buf[buf.length] = ct.apply(p);
            }
            rp.tsyle = 'width:'+this.getTotalWidth()+';';
            rp.cols = buf.length;
            rp.cells = buf.join("");
            rp.display = this.displayFilters?'':'style="display:none"'
            return rt.apply(rp);
        },
        filters: [],
        renderEditors: function() {
            Ext.each(this.filters, function(ob){ob.destroy()});
            var cs = this.getColumnData();
            for (i=0,len=cs.length; i<len; i++) {
                if (this.cm.isHidden(i)) continue;
                var c = cs[i],
                    fieldid = c.id,
                    id = 'filtergrid-' + fieldid;
                var config = this.cm.config[i].filter;
                if (!config) config = {xtype:'textfield'};
                Ext.apply(config, {
                    id:fieldid, 
                    enableKeyEvents: true,
                    selectOnFocus: true
                });
                var filter = new Ext.ComponentMgr.create(
                    config?config:{xtype:'textfield', validationDelay:500});
                if (this.lastOptions) {
                    var newValue = this.lastOptions[fieldid];
                    filter.setValue(newValue);
                }
                var panel = new Ext.Panel({
                    frame: false,
                    border: false,
                    layout: 'fit',
                    renderTo: id,
                    items: filter
                });
                filter.setWidth('100%');
                this.filters[this.filters.length] = filter;
                filter.validationTask = new Ext.util.DelayedTask(function(){
                    this.fireEvent('filterchange', this);
                    this.updateLiveRows(0, true, true);
                }, this);
                if (filter.xtype=='textfield') {
                    filter.on('keyup', function(field, e) {
                        if(!e.isNavKeyPress()) this.validationTask.delay(250);
                    }, filter);
                } else {
                    filter.on('select', function(field, e) {
                        this.validationTask.delay(250);
                    }, filter);
                    filter.on('change', function(field, e) {
                        this.validationTask.delay(250);
                    }, filter);
                }
                
            }
        },
        updateHeaders: function() {
            Zenoss.FilterGridView.superclass.updateHeaders.call(this);
            this.renderEditors();
        },
        renderUI: function() {
            Zenoss.FilterGridView.superclass.renderUI.call(this);
            //this.renderEditors();
        },
        renderHeaders : function(){
            html = Zenoss.FilterGridView.superclass.renderHeaders.call(this);
            html = html.slice(0, html.length-8);
            html = html + this.renderFilterRow() + '</table>';
            return html;
        },
        getState: function(){
            return {
                rowColors: this.rowColors,
                displayFilters: this.displayFilters,
                options: this.lastOptions
            };
        },
        getFilterButton: function(){
            return Ext.getCmp(this.filterbutton);
        },
        getRowClass: function(record, index) {
            var stateclass = record.get('eventState')=='New' ? 
                                'unacknowledged':'acknowledged';
            var sev = Zenoss.util.convertSeverity(record.get('severity'));
            var sevclass = this.rowColors ? sev + ' rowcolor' : '';
            return stateclass + ' ' + sevclass;

        },
        toggleRowColors: function(bool){
            this.rowColors = bool;
            this.fireEvent('rowcolorchange');
            this.updateLiveRows(this.rowIndex, true, false);
        },
        applyState: function(state) {
            this.rowColors = state.rowColors;
            this.displayFilters = state.displayFilters;
            this.lastOptions = state.options;
            var btn = Ext.getCmp(this.filterbutton);
            var rowcoloritem = Ext.getCmp(this.rowcoloritem);
            btn.on('render', function(){
                this.toggle(state.displayFilters);
            }, btn);
            rowcoloritem.on('render', function(){
                this.setChecked(state.rowColors);
            }, rowcoloritem);
        },
        resetFilters: function(){
            this.lastOptions = {};
            this.getFilterButton().toggle(false);
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
            this.mon(this.view, 'rowcolorchange', this.saveState, this);
        },
        getView : function(){
            if(!this.view){
                this.view = new Zenoss.FilterGridView(this.viewConfig);
            }
            return this.view;
        },
        getState: function(){
            var val = Zenoss.FilterGridPanel.superclass.getState.call(this);
            var filterstate = this.getView().getState();
            val.filters = filterstate;
            return val
        },
        applyState: function(state){
            this.getView().applyState(state.filters);
            Zenoss.FilterGridPanel.superclass.applyState.apply(this, arguments);
        },
        resetGrid: function() {
            Ext.state.Manager.clear(this.getItemId());
            this.getView().resetFilters();
            this.reconfigure(this.store,this.initialConfig.cm);
            var view = this.getView();
            view.fitColumns();
            view.showLoadMask(true);
            view.updateLiveRows(view.rowIndex, true, true);
        },
        hideFilters: function() { this.getView().hideFilters(); },
        showFilters: function() { 
            this.getView().showFilters(); }
    });

    /**
     * @class Zenoss.MultiselectMenu
     * @extends Ext.Toolbar.Button
     * A combobox-like menu that allows one to toggle each option, and is able
     * to deliver its value like a form field.
     * @constructor
     */
    Zenoss.MultiselectMenu = Ext.extend(Ext.Toolbar.Button, {
        constructor: function(config) {
            items = [];
            var me = this;
            Ext.each(config.source, function(o){
                items[items.length] = {
                    checked: typeof(o.checked)=='undefined',
                    hideOnClick: false,
                    handler: function(){
                        me.fireEvent('change');
                    },
                    value: o.value,
                    text: o.text
                }
            });
            config.menu = {
                items: items
            };
            Zenoss.MultiselectMenu.superclass.constructor.apply(this, arguments);
        },
        getValue: function() {
            var result = [];
            Ext.each(this.menu.items.items, function(item){
                if (item.checked) result[result.length] = item.value
            });
            return result;
        },
        setValue: function(val) {
            if (!val) {
                this.constructor(this.initialConfig);
            } else {
                Ext.each(this.menu.items.items, function(item){
                    var shouldCheck = false;
                    try{
                        shouldCheck = val.indexOf(item.value)!=-1;
                    } catch(e) {var _x;}
                    item.setChecked(shouldCheck);
                });
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
            Zenoss.StatefulRefreshMenu.superclass.constructor.apply(this,
                arguments);
        },
        getState: function(){
            return this.trigger.interval;
        },
        applyState: function(interval){
            var items = this.items.items;
            Ext.each(items, function(item){
                if (item.value==interval)
                    item.setChecked(true);
            }, this);
            this.trigger.on('afterrender', function(){
                this.trigger.setInterval(interval);
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
                    text: '1 minute',
                    value: 60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '5 minutes',
                    value: 5*60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '10 minutes',
                    value: 10*60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '30 minutes',
                    value: 30*60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '1 hour',
                    value: 60*60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: 'Manually',
                    value: 0,
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
        },
        setInterval: function(interval) {
            this.interval = interval;
            this.refreshTask.delay(this.interval*1000);
        },
        poll: function(){
            if (this.interval) {
                this.handler();
                this.refreshTask.delay(this.interval*1000);
            }
        }
    });
    Ext.reg('refreshmenu', Zenoss.RefreshMenuButton);


    /**
     * General utilities
     */
    Ext.namespace('Zenoss.util');

    Zenoss.env.SEVERITIES = [
        [5, 'Critical'],
        [4, 'Error'],
        [3, 'Warning'],
        [2, 'Info'],
        [1, 'Debug'],
        [0, 'Clear']
    ];

    Zenoss.util.convertSeverity = function(severity){
        sevs = ['clear', 'debug', 'info', 'warning', 'error', 'critical'];
        return sevs[severity];
    }

    Zenoss.util.convertStatus = function(stat){
        var stati = ['New', 'Acknowledged', 'Suppressed'];
        return stati[stat];
    }

    Zenoss.util.render_severity = function(sev) {
        return '<div class="severity-icon-small '+
            Zenoss.util.convertSeverity(sev) +
            '"'+'><'+'/div>'
    }

    Zenoss.util.render_status = function(stat) {
        return '<div class="status-icon-small '+stat.toLowerCase()+'"><'+'/div>';
    }

    Zenoss.util.render_linkable = function(name, col, record) {
        var url = record.data[col.id + '_url'];
        if (url) {
            return '<a href="'+url+'">'+name+'</a>'
        } else {
            return name;
        }
    }

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

});
