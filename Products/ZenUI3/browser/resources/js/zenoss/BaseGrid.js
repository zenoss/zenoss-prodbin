(function () {


    /**
     * Base Configuration for direct stores
     * @class Zenoss.DirectStore
     */
    Ext.define('Zenoss.DirectStore', {
        extend:'Ext.data.Store',
        alias:'store.zendirectstore',
        constructor:function (config) {
            config = config || {};
            Ext.applyIf(config, {
                remoteSort:true,
                pageSize:config.pageSize || 50,
                buffered: true,
                sorters:[
                    {
                        property:config.initialSortColumn,
                        direction:config.initialSortDirection || 'ASC'
                    }
                ],
                proxy:{
                    type:'direct',
                    simpleSortMode: true,
                    directFn:config.directFn,
                    extraParams: config.baseParams || {},
                    reader:{
                        root:config.root || 'data',
                        totalProperty:config.totalProperty || 'totalCount'
                    }
                }
            });
            this.callParent(arguments);
        },
        setBaseParam:function (key, value) {
            this.proxy.extraParams[key] = value;
        }
    });

    /**
     * @class Zenoss.NonPaginatedStore
     * @extends Ext.data.Store
     * Direct Store for when you want all of the results on a single
     * grid.
     * Use this if the expected number of rows is always going to be less than
     * a hundred or so since every request will load the entire grid without pagination.
     **/
    Ext.define('Zenoss.NonPaginatedStore', {
        extend:'Ext.data.Store',
        alias:['store.directcombo'],
        constructor:function (config) {
            config = config || {};
            Ext.applyIf(config, {
                remoteSort:false,
                buffered:false,
                proxy:{
                    type:'direct',
                    limitParam:undefined,
                    startParam:undefined,
                    pageParam:undefined,
                    sortParam: undefined,
                    extraParams: config.baseParams || {},
                    directFn:config.directFn,
                    reader:{
                        type:'json',
                        root:config.root || 'data'
                    }
                }
            });
            this.callParent(arguments);
        },
        setContext:function (context) {

            if (this.proxy.extraParams) {
                this.proxy.extraParams.uid = context;
            }
            this.load();
        },
        setBaseParam:function (key, value) {
            this.proxy.extraParams[key] = value;
        }
    });

    Ext.define('Ext.ux.grid.FilterRow', {
        extend:'Ext.util.Observable',

        init:function (grid) {
            this.grid = grid;

            // when column width programmatically changed
            grid.headerCt.on('columnresize', this.resizeFilterField, this);

            grid.headerCt.on('columnmove', this.resetFilterRow, this);
            grid.headerCt.on('columnshow', this.resetFilterRow, this);
            grid.headerCt.on('columnhide', this.resetFilterRow, this);
            // if (grid.horizontalScroller) {
            //     grid.horizontalScroller.on('bodyscroll', this.scrollFilterField, this);
            // }

            // if (grid.verticalScroller) {
            //     grid.verticalScroller.on('bodyscroll', this.scrollFilterField, this);
            // }

            grid.on('columnmove', this.onGridColumnMove, this);
        },
        /**
         * Every time a column is moved on the grid destroy and rebuild the filters
         **/
        onGridColumnMove:function () {
            var grid = this.grid;
            // each column has a reference to its filter remove that first
            this.eachColumn(function (col) {
                if (Ext.isDefined(col.filterField)) {
                    col.filterField.destroy();
                    delete col.filterField;
                }
            });
            // destroy docked item the filters are rendered to
            Ext.each(grid.getDockedItems(), function (item) {
                if (item.id == grid.id + 'docked-filter') {
                    grid.removeDocked(item, true);
                }
            });

            // rebuild the filters
            this.applyTemplate();
        },
        applyTemplate:function () {
            var searchItems = [],
                defaultFilters = this.defaultFilters;
            // set the default params
            this.eachColumn(function (col) {
                // this is the value we are going to send to the server
                // for this filter
                if (!col.filterKey) {
                    col.filterKey = col.id;
                    if (!col.filterKey || col.filterKey.startswith("gridcolumn")) {
                        col.filterKey = col.dataIndex;
                    }
                }
                var filterDivId = this.getFilterDivId(col.filterKey);

                if (!col.filterField) {
                    if (Ext.isDefined(col.filter) && col.filter === false) {
                        col.filter = {};
                        col.filter.xtype = 'hidden';
                    }
                    if (col.nofilter || col.isCheckerHd != undefined) {
                        col.filter = { };
                    } else if (!col.filter) {
                        col.filter = { };
                        col.filter.xtype = 'textfield';
                    }

                    col.filter = Ext.apply({
                        id:filterDivId,
                        hidden:col.isHidden(),
                        xtype:'component',
                        baseCls:'x-grid-filter',
                        width:col.width - 2,
                        enableKeyEvents:true,
                        style:{
                            margin:'1px 1px 1px 1px'
                        },
                        hideLabel:true,
                        value:this.defaultFilters[col.filterKey]
                    }, col.filter);
                    col.filterField = Ext.ComponentManager.create(col.filter);

                } else {
                    if (col.hidden != col.filterField.hidden) {
                        col.filterField.setVisible(!col.hidden);
                    }
                }
                if(Zenoss.SELENIUM){
                    col.filterField.on('afterrender', function(e){
                        if(Ext.getCmp(e.id).inputEl){
                            /*  add an id to the input element of filters if
                                it has one. If not, don't worry about it.
                                example: events_grid-filter-devices-input
                                -- for selenium automation --
                            */
                            var filterInput = Ext.getCmp(e.id).inputEl;
                            filterInput.dom.id = e.id+"-input";
                        }
                    }, this);
                }

                if (Zenoss.settings.enableLiveSearch) {
                    col.filterField.on('change', this.onChange, this);
                }
                col.filterField.on('keydown', this.onKeyDown, this);

                searchItems.push(col.filterField);
            });

            // make sure we send our default filters on the initial load
            if (!Ext.isEmpty(this.defaultFilters)) {
                if (!this.grid.store.proxy.extraParams) {
                    this.grid.store.proxy.extraParams = {};
                }
                this.grid.store.proxy.extraParams.params = this.getSearchValues();
            }

            if (searchItems.length > 0) {
                this.grid.addDocked(this.dockedFilter = Ext.create('Ext.container.Container', {
                    id:this.grid.id + 'docked-filter',
                    weight:100,
                    dock:'top',
                    border:false,
                    baseCls:Ext.baseCSSPrefix + 'grid-header-ct',
                    items:searchItems,
                    layout:{
                        type:'hbox'
                    }
                }));
            }
        },
        clearFilters:function () {
            this.eachColumn(function (col) {
                if (Ext.isDefined(col.filterField)) {
                    col.filterField.reset();
                }
            });
        },
        getState:function () {
            return this.getSearchValues();
        },
        applyState:function (state) {
            if (Ext.isEmpty(state)) {
                return;
            }
            if (!this.dockedFilter) {
                this.applyTemplate();
            }
            this.eachColumn(function (col) {
                // do not apply a filter to a hidden column (will be confusing for the user)
                if (!col.isHidden()) {
                    if (Ext.isDefined(state[col.filterKey]) && !Ext.isEmpty(state[col.filterKey])) {
                        col.filterField.setValue(state[col.filterKey]);
                    }
                } else {
                    // column is hidden so hide the filter
                    col.filterField.setVisible(false);
                }
            });
        },
        onChange:function (field, newValue, oldValue) {
            if (!this.onChangeTask) {
                this.onChangeTask = new Ext.util.DelayedTask(function () {
                    this.storeSearch();
                }, this);
            }

            this.onChangeTask.delay(1000);

        },
        onKeyDown:function (field, e) {
            // if live search is enabled fire the change delay
            // if live search is disabled then they have to explictly
            // hit enter to search
            if (Zenoss.settings.enableLiveSearch) {
                this.onChange();
            }

            // if they explicitly pressed enter then search now
            if (e.getKey() == e.ENTER) {
                this.onChange();
            }
        },

        getSearchValues:function () {
            var values = {},
                globbing = (this.appendGlob && (Ext.isDefined(globbing) ? globbing : true));
            this.eachColumn(function (col) {
                var filter = col.filterField, excludeGlobChars = ['*', '"', '?'], query;
                if (filter && filter.xtype != 'component') {
                    if (!Ext.isEmpty(filter.getValue())) {
                        query = filter.getValue();
                        if (globbing && filter.xtype == 'textfield' && filter.vtype != 'numcmp' &&
                            filter.vtype != 'numrange' && filter.vtype != 'floatrange' &&
                            excludeGlobChars.indexOf(query.charAt(query.length - 1)) === -1) {
                            query += '*';
                        }
                        values[col.filterKey] = query;
                    }
                }
            });
            values = Ext.applyIf(values, this.defaultFilters);
            return values;
        },

        storeSearch:function () {
            var values = this.getSearchValues();
            if (!this.grid.store.proxy.extraParams) {
                this.grid.store.proxy.extraParams = {};
            }
            // this will make sure that all subsequent buffer loads have the parameters
            this.grid.store.proxy.extraParams.params = values;

            // reset their scrolling when the filters change
            this.grid.scrollToTop();

            // only load the store if a context has been applied
            if (Ext.isDefined(this.grid.getContext()) || this.grid.getStore().autoLoad) {
                this.grid.refresh({
                    callback:function () {
                        this.grid.fireEvent('filterschanged', this.grid, values);
                    },
                    scope:this
                });
            }

            // save the state
            this.grid.saveState();
        },

        resetFilterRow:function () {
            this.eachColumn(function (col) {
                if (!col.filterField) {
                    return;
                }
                col.filterField.setVisible(!col.isHidden());
            });

            if (!this.dockedFilter) {
                this.applyTemplate();
            }
        },

        resizeFilterField:function (headerCt, column, newColumnWidth) {
            var editor;
            if (!column.filterField) {
                //This is because of the reconfigure
                this.resetFilterRow();
                editor = this.grid.headerCt.items.findBy(
                    function (item) {
                        return item.dataIndex == column.dataIndex;
                    }).filterField;
            } else {
                editor = column.filterField;
            }

            if (editor) {
                editor.setWidth(newColumnWidth - 2);
            }
        },

        scrollFilterField:function (e, target) {
            var width = this.grid.headerCt.el.dom.firstChild.style.width;
            this.dockedFilter.el.dom.firstChild.style.width = width;
            this.dockedFilter.el.dom.scrollLeft = target.scrollLeft;
        },

        // Returns HTML ID of element containing filter div
        getFilterDivId:function (columnId) {
            return this.grid.id + '-filter-' + columnId;
        },

        // Iterates over each column that has filter
        eachFilterColumn:function (func) {
            this.eachColumn(function (col, i) {
                if (col.filterField) {
                    func.call(this, col, i);
                }
            });
        },
        setFilter:function (colId, value) {
            this.eachColumn(function (col) {
                if (col.filterKey == colId) {
                    col.filterField.setValue(value);
                }
            });
        },
        // Iterates over each column in column config array
        eachColumn:function (func) {
            Ext.each(this.grid.headerCt.getGridColumns(), func, this);
        }
    });

    /**
     * @class Zenoss.ContextGridPanel
     * @extends Ext.grid.GridPanel
     * Base class for all of our grids that have a context.
     * @constructor
     */
    Ext.define('Zenoss.ContextGridPanel', {
        extend:'Ext.grid.Panel',
        alias:['widget.contextgridpanel'],
        selectedNodes:[],
        constructor:function (config) {
            var viewConfig = config.viewConfig || {};

            Zenoss.util.validateConfig(config,
                'store',
                'columns');
            viewConfig = config.viewConfig || {};

            Ext.applyIf(viewConfig, {
                autoScroll:false,
                stripeRows:true,
                loadMask:true
            });

            Ext.applyIf(config, {
                scroll:'both',
                viewConfig:viewConfig
            });
            this.callParent([config]);
            this.getStore().on("load", function (store, records) {
                if (!this._disableSavedSelection) {
                    this.applySavedSelection();
                }
            }, this);
            // once a uid is set always send that uid
            this.getStore().on('beforeprefetch', function (store, operation) {
                if (!operation) {
                    return true;
                }

                this.start = operation.start;
                this.limit = operation.limit;
                if (!Ext.isDefined(operation.params)) {
                    operation.params = {};
                }
                if (this.uid) {
                    operation.params.uid = this.uid;
                }

                this.applyOptions(operation);
                return true;

            }, this);
            this.addEvents(
                /**
                 * @event beforeactivate
                 * Fires when the context of the grid panel changes
                 * @param {Ext.Component} this
                 * @param {String} contextId
                 */
                'contextchange'
            );
        },
        saveSelection:function () {
            this.selectedNodes = this.getSelectionModel().getSelection();
        },
        disableSavedSelection: function(bool) {
            this._disableSavedSelection = bool;
        },
        applySavedSelection:function () {
            var curStore = this.getStore(),
                selModel = this.getSelectionModel(),
                items = [];
            Ext.each(this.selectedNodes, function(node) {
                var rec = curStore.getAt(node.index);
                if (rec && rec.getId() == node.getId()) {
                    items.push(rec);
                }
            });
            if (items.length > 0) {
                this.suspendEvents();
                this.getSelectionModel().select(items, false, true);
                this.resumeEvents();
                selModel.fireEvent('selectionchange', selModel, selModel.getSelection());
                this.selectedNodes = [];
            }
        },
        applyOptions:function (options) {
            // Do nothing in the base implementation
        },
        /**
         * This will add a parameter to be sent
         * back to the server on every request for this store.
         **/
        setStoreParameter:function (name, value) {
            var store = this.getStore();
            if (!store.proxy.extraParams) {
                store.proxy.extraParams = {};
            }
            store.proxy.extraParams[name] = value;
        },
        setContext:function (uid) {
            this.uid = uid;
            this.setStoreParameter('uid', uid);
            this.fireEvent('contextchange', this, uid);
            this.refresh();
        },
        getContext:function () {
            return this.uid;
        },
        refresh:function () {
            // only refresh if we have a context set
            if (!this.getContext()) {
                return;
            }
            this.saveSelection();
            var store = this.getStore();
            store.load();
        }
    });


    /**
     * @class Zenoss.BaseGridPanel
     * @extends Zenoss.ContextGridPanel
     * Base class for all of our Live Grids.
     * @constructor
     */
    Ext.define('Zenoss.BaseGridPanel', {
        extend:'Zenoss.ContextGridPanel',
        alias:['widget.basegridpanel'],
        constructor:function (config) {
            Ext.applyIf(config, {
                verticalScrollerType:'paginggridscroller',
                invalidateScrollerOnRefresh:false,
                scroll:'both',
                bbar: {
                    cls: 'commonlivegridinfopanel',
                    items: [
                        '->',
                    {
                        xtype:'livegridinfopanel',
                        grid:this
                    }]
                }
            });
            this.callParent([config]);
        },
        refresh:function (callback, scope) {
            // only refresh if a context is set
            if (!this.getContext()) {
                return;
            }
            this.saveSelection();
            var store = this.getStore();
            store.currentPage = 1;
            store.load({
                callback:function () {
                    if (store.getCount()) {
                        // -1 so we don't prefetch multiple pages, we just need one until the user
                        // scrolls down a bit more
                        store.guaranteeRange(0, store.pageSize - 1);
                    }
                    // Add a callback if one was passed in to here.
                    Ext.callback(callback, scope || this);
                },
                scope:this
            });
        },
        scrollToTop:function () {
            var scroller = this.down('paginggridscroller');
            if (scroller) {
                scroller.scrollToTop();
            }
        }

    });


    /**
     * @class Zenoss.FilterGridPanel
     * @extends Zenoss.BaseGridPanel
     * Sub class of the base grid that allows adds filters to the columns.
     * @constructor
     */
    Ext.define('Zenoss.FilterGridPanel', {
        extend:'Zenoss.BaseGridPanel',
        alias:['widget.filtergridpanel'],
        constructor:function (config) {
            config = config || {};
            Ext.applyIf(config, {
                displayFilters:true
            });

            this.callParent(arguments);
        },
        initComponent:function () {
            /**
             * @event filterschanged
             * Fires after the filters are changed but after the store is reloaded
             * @param {Zenoss.FilterGridPanel} grid The grid panel.
             * @param {Object} filters Key/value pair of the new filters.
             */
            this.addEvents('filterschanged');

            this.callParent();
            // create the filter row
            var filters = Ext.create('Ext.ux.grid.FilterRow', {
                grid:this,
                appendGlob:this.appendGlob,
                defaultFilters:this.defaultFilters || {}
            });

            if (this.displayFilters) {
                filters.init(this);
            }
            this.filterRow = filters;
        },
        getState:function () {
            var state = this.callParent();
            state.filters = this.filterRow.getState();
            return state;
        },
        applyState:function (state) {
            this.callParent([state]);
            if (this.displayFilters) {
                this.filterRow.applyState(state.filters);
            }
        },
        getFilters:function () {
            return this.filterRow.getSearchValues();
        },
        setFilter:function (colId, value) {
            this.filterRow.setFilter(colId, value);
        }
    });

    /**
     * @class Zenoss.LiveGridInfoPanel
     * @extends Ext.toolbar.TextItem
     * Toolbar addition that displays, e.g., "Showing 1-10 of 100 Rows"
     * @constructor
     * @grid {Object} the GridPanel whose information should be displayed
     */
    Ext.define('Zenoss.LiveGridInfoPanel', {
        extend:'Ext.toolbar.TextItem',
        alias:['widget.livegridinfopanel'],
        cls:'livegridinfopanel',
        initComponent:function () {
            this.setText(this.emptyMsg);
            if (this.grid) {
                if (!Ext.isObject(this.grid)) {
                    this.grid = Ext.getCmp(this.grid);
                }
                // We need to refresh this when one of two events happen:
                //  1.  The data in the data store changes
                //  2.  The user scrolls.
                this.grid.getStore().on('datachanged', this.onDataChanged, this);
                this.grid.getView().on('bodyscroll', this.onScroll, this);
            }

            this.displayMsg = _t('Displaying {0} - {1} of {2} Rows');
            this.emptyMsg = _t('No Results');
            this.callParent(arguments);
        },
        onDataChanged:function () {
            var totalCount = this.grid.getStore().getTotalCount();
            this.totalCount = totalCount;
            if (totalCount && totalCount > 0) {
                this.onScroll();
            } else {
                this.setText(this.emptyMsg);
            }
        },
        onScroll: function() {
            var pagingScroller = this.grid.verticalScroller;

            if (pagingScroller) {
                var  start = pagingScroller.getFirstVisibleRowIndex() || 0,
                     end = pagingScroller.getLastVisibleRowIndex(),
                     msg;
                if (end > this.totalCount) {
                    end = this.totalCount;
                }
                msg = Ext.String.format(this.displayMsg, start + 1, end, this.totalCount);
                this.setText(msg);
            } else {
                // Drat, we didn't have the paging scroller, so assume we are showing all
                var showingAllMsg = _t('Found {0} records');
                var msg = Ext.String.format(showingAllMsg, this.totalCount);
                this.setText(msg);
            }

        }
    });

}());
