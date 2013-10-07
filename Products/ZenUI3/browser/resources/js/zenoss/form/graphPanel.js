/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    Ext.ns('Zenoss');
    /**********************************************************************
     *
     * Graph Panel
     *
     */
    function syntaxHighlight(json) {
        json = JSON.stringify(json, undefined, 4);
        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
            var cls = 'syntax-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'syntax-string';
                } else {
                    cls = 'syntax-text';
                }
            } else if (/true|false/.test(match)) {
                cls = 'syntax-boolean';
            } else if (/null/.test(match)) {
                cls = 'syntax-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        });
    }

    var router = Zenoss.remote.DeviceRouter,
        GraphPanel,
        DRangeSelector,
        GraphRefreshButton,
        dateRangePanel,
        CURRENT_TIME = "0s-ago",
        DATE_RANGES = [
            ["1h-ago", _t('Last Hour')],
            ["1d-ago", _t('Yesterday')],
            ["7d-ago", _t('Last Week')],
            ["30d-ago", _t('Last 30 days')],
            ["1y-ago", _t('Last Year')]
        ],
        RANGE_TO_MILLISECONDS = {
            '1h-ago': 3600000,
            '1d-ago': 86400000,
            '7d-ago': 604800000,
            '1m-ago': 2419200000,
            '1y-ago': 31536000000
        },
        DOWNSMAPLE = [
            [86400000, '1h-avg'],    // Day
            [604800000, '12h-avg'],  // Week
            [2419200000, '1d-avg'],  // Month
            [31536000000, '30d-avg'] // Year
        ],

        /*
         * If a given request is over GRAPHPAGESIZE then
         * the results will be paginated.
         * IE can't handle the higher number that compliant browsers can
         * so setting lower.
         **/
        GRAPHPAGESIZE = Ext.isIE ? 25 : 50;

    Number.prototype.pad = function(count) {
        var zero = count - this.toString().length + 1;
        return Array(+(zero > 0 && zero)).join("0") + this;
    };

    function now() {
        return new Date().getTime();
    }

    function rangeToMilliseconds(range){
        if (RANGE_TO_MILLISECONDS[range]) {
            return RANGE_TO_MILLISECONDS[range];
        }
        return range;
    }

    function formatForMetricService(ms) {
        // only format absolute times
        if (!Ext.isNumber(ms)) {
            return ms;
        }
        var d = new Date(ms);
        return d.getUTCFullYear() + '/' + (d.getUTCMonth() + 1).pad(2) + '/' + d.getUTCDate().pad(2) + '-'
            + d.getUTCHours().pad(2) + ':' + d.getUTCMinutes().pad(2) + ':' + d.getUTCSeconds().pad(2) + '-UTC';
    }

    Date.prototype.minus = function(secs) {
        return new Date(this.valueOf()-(secs*1000));
    };


    Ext.define("Zenoss.EuropaGraph", {
        alias:['widget.europagraph'],
        extend: "Ext.Panel",


        zoom_factor: 1.5,
        pan_factor: 3,

        /**
         * @cfg {int} start
         * The start time of the graph in unix seconds.
         * Defaults to <code>new DateTime().getTime()</code>.
         */
        start: DATE_RANGES[0][0] ,

        /**
         * @cfg {int} end
         * The end time of the graph in unix seconds.
         * Defaults to <code>new DateTime().getTime() - 3600 (an hour ago)</code>.
         */
        end: CURRENT_TIME,

        /**
         * @cfg {String}  graphId
         * The id of the div that is used to contain the graph
         *
         */
        graphId: "",

        /**
         * @cfg {String}  graphTitle
         * The upper left hand title of the graph
         * Defaults to an empty string.
         */
        graphTitle: "",

        /**
         * @cfg {Object}  tags
         * The tags we are sending to the metric service. This is a key value pair of tagname, value.
         * For Example: <code>{'ip_address': '191.168.4.10'}
         * Defaults to an empty object
         */
        tags: {},

        /**
         * @cfg {String} type
         * The type of chart we are asking the metric service to render. See the central-query documentation for a list of valid types.
         * Defaults to an <code>line</code>
         */
        type: 'line',

        /**
         * @cfg {Array} datapoints
         * Datapoints we are sending to the metric service. This is an
         * array of objects. A datapoint object has the following
         * available properties:
         * <ul>
         *   <li> aggregator - example: "avg". The available aggregator functions  are: ("avg", "min", "max", "sum")</li>
         *   <li> color - example: "#0000ff99"</li>
         *   <li> format - example: "%6.2lf"</li>
         *   <li> id - example: "laLoadInt15"</li>
         *   <li> legend - example: "15 Minute"</li>
         *   <li> metric - example: "laLoadInt15"</li>
         *   <li> rpn - example: "100,/"</li>
         *   <li> uuid - example: "480fc36d-1ffa-4bbd-a41d-2ad0e459fb85""</li>
         * </ul>
         **/
        datapoints: [],
        constructor: function(config) {
            var padding = "padding:45px 20px 15px 0px;";
            if (config.height <= 400) {
                padding = "padding:0px 0px 0px 0px;";
            }
            config = Ext.applyIf(config||{}, {

                html: '<div id="' + config.graphId + '" style="border-style: solid; border-width:1px;' + padding +  'height:' + String(config.height - 75)  + 'px;"></div>',
                cls: 'graph-panel',
                dockedItems: [{
                    xtype: 'toolbar',
                    dock: 'top',
                    items: [{
                        xtype: 'tbtext',
                        style: {
                            fontWeight: 'bolder',
                            fontSize: '1.5em'
                        },
                        text: config.graphTitle // + ' : ' + config.uid
                    },'->',{
                        xtype: 'button',
                        iconCls: 'customize',
                        menu: [{
                            text: _t('Definition'),
                            handler: Ext.bind(this.displayDefinition, this)
                        }, {
                            text: _t('Export to CSV'),
                            handler: Ext.bind(this.exportData, this)
                        }, {
                            text: _t('Link to this Graph'),
                            handler: Ext.bind(this.displayLink, this)
                        }]
                    },{
                        text: '&lt;',
                        width: 40,
                        handler: Ext.bind(function(btn, e) {
                            this.onPanLeft(this);
                        }, this)
                    },{
                        text: _t('Zoom In'),
                        handler: Ext.bind(function(btn, e) {
                            this.zoomIn(this);
                        }, this)
                    },{
                        text: _t('Zoom Out'),
                        handler: Ext.bind(function(btn, e) {
                            this.zoomOut(this);
                        }, this)
                    },{
                        text: '&gt;',
                        width: 40,
                        handler: Ext.bind(function(btn, e) {
                            this.onPanRight(this);
                        }, this)
                    }]
                }],
                graph_params: {
                    drange: DATE_RANGES[0][0],
                    end: config.end || CURRENT_TIME,
                    start: config.start || DATE_RANGES[0][0]
                }
            });

            Zenoss.EuropaGraph.superclass.constructor.call(this, config);
        },
        initComponent: function() {
            // the visualization library depends on our div rendering,
            // let's make sure that has happened
            this.on('afterrender', this.initChart, this);
            this.callParent(arguments);
        },
        initChart: function() {
            var visconfig = {
                returnset: "EXACT",
                range : {
                    start : formatForMetricService(this.graph_params.start),
                    end : formatForMetricService(this.graph_params.end)
                },
                width: this.width,
                height: this.height - 25,
                tags: this.tags,
                datapoints: this.datapoints,
                overlays: this.thresholds,
                type: this.type,
                // lose the footer and yaxis label as the image gets smaller
                footer: (this.height >= 350) ? true : false,
                yAxisLabel: (this.width >= 500) ? this.units : null,
                miny: (this.miny != -1) ? this.miny : null,
                maxy: (this.maxy != -1) ? this.maxy : null,
                // the visualization library currently only supports
                // one format for chart, not per metric
                format: this.datapoints[0].format
            };
            var delta;
            if (Ext.isNumber(this.graph_params.start)) {
                delta = new Date().getTime() - this.graph_params.start;
            } else {
                delta = rangeToMilliseconds(this.graph_params.start);
            }
            // always down sample to a 1m-avg for now. This
            // means that if we collect at less than a minute the
            // values will be averaged out.
            visconfig.downsample = '1m-avg';
            DOWNSMAPLE.forEach(function(v) {
                if (delta >= v[0]) {
                    visconfig.downsample = v[1];
                }
            });

            // determine scaling
            if (this.autoscale) {
                visconfig.autoscale = {
                    factor: this.base,
                    ceiling: this.ceiling
                };
            }
            this.chartdefinition = visconfig;
            zenoss.visualization.chart.create(this.graphId, visconfig);
        },
        displayLink: function(){
            var config = Zenoss.util.base64.encode(Ext.JSON.encode(this.initialConfig)),
                link = "/zport/dmd/viewGraph?data=" + config;
            new Zenoss.dialog.ErrorDialog({
                message: Ext.String.format(_t('<div>'
                                              + Ext.String.format(_t('Drag this link to your bookmark bar to link directly to this graph. {0}'), '<br/><br/><a href="'
                                              + link
                                              + '">Graph: ' + this.graphTitle +  ' </a>')
                                              + '</div>')),
                title: _t('Save Configuration')
            });
        },
        displayDefinition: function(){
            Ext.create('Zenoss.dialog.BaseWindow', {
                closeAction: 'destroy',
                title: _t('Graph JSON Definition'),
                autoScroll: true,
                minWidth: 700,
                height: 500,
                items: [{
                    xtype: 'panel',
                    autoScroll: true,
                    html: Ext.String.format('<pre>{0}</pre>', syntaxHighlight(this.chartdefinition))
                }]
            }).show();
        },
        exportData: function() {
            var chart = zenoss.visualization.__charts[this.graphId],
                plots = Ext.JSON.encode(chart.plots),
                form;
            form = Ext.DomHelper.append(document.body, {
                tag: 'form',
                method: 'POST',
                action: '/zport/dmd/exportGraph',
                children: [{
                    tag: 'textarea',
                    style: {
                        display: 'none'
                    },
                    name: 'plots',
                    html: plots
                }, {
                    tag: 'input',
                    type: 'hidden',
                    name: 'title',
                    value: this.graphTitle
                }]
            });
            form.submit();
        },

        initEvents: function() {
            Zenoss.EuropaGraph.superclass.initEvents.call(this);
            this.addEvents(
                /**
                 * @event updateimage
                 * Fire this event to force the chart to redraw itself.
                 * @param {object} params The parameters we are sending to the object.
                 **/
                'updateimage'
            );
            this.on('updateimage', this.updateGraph, this);
        },
        linked: function() {
            return this.isLinked;
        },
        setLinked: function(isLinked) {
            this.isLinked = isLinked;
        },
        updateGraph: function(params) {
            var gp = Ext.apply({}, params, this.graph_params);
            gp.start = params.start || gp.drange;
            if (gp.start < 0) {
                gp.start = 0;
            }

            // see if end is explicitly defined on the params
            if (Ext.isDefined(params.end) && (params.end > params.start)){
                gp.end = params.end;
            } else {
                // otherwise it needs to be now
                gp.end = CURRENT_TIME;
            }
            var changes = {
                range : {
                    start: formatForMetricService(gp.start),
                    end: formatForMetricService(gp.end)
                }
            };
            // gp.start is something like "1h-ago", convert to milliseconds
            var delta;
            if (Ext.isNumber(gp.start)) {
                delta = new Date() - gp.start;
            } else {
                delta = rangeToMilliseconds(gp.start);
            }

            changes.downsample = '-';
            DOWNSMAPLE.forEach(function(v) {
                if (delta >= v[0]) {
                    changes.downsample = v[1];
                }
            });
            zenoss.visualization.chart.update(this.graphId, changes);

            //zenoss.visualization.chart.setRange(this.graphId,
            //    formatForMetricService(gp.start),
            //    formatForMetricService(gp.end));
            this.graph_params = gp;
        },
        convertStartToAbsoluteTime: function(start) {
            if (Ext.isNumber(start)) {
                return start;
            }
            return new Date() - rangeToMilliseconds(start);
        },
        convertEndToAbsolute: function(end) {
            if (end == CURRENT_TIME) {
                return new Date().getTime();
            }
            return end;
        },
        onPanLeft: function(graph) {
            var gp = this.graph_params;
            gp.start = this.convertStartToAbsoluteTime(gp.start);
            var delta = Math.round(rangeToMilliseconds(gp.drange)/this.pan_factor);
            var newstart = (gp.start) - delta > 0 ? gp.start - delta : 0;
            var newend = newstart + rangeToMilliseconds(gp.drange);
            this.fireEventsToAll("updateimage", {start:newstart, end:newend});
        },
        onPanRight: function(graph) {
            var gp = this.graph_params;
            gp.start = this.convertStartToAbsoluteTime(gp.start);
            var delta = Math.round(rangeToMilliseconds(gp.drange)/this.pan_factor);
            var newstart = gp.start + delta > 0 ? gp.start + delta : 0;
            var newend = newstart + rangeToMilliseconds(gp.drange);
            var now = new Date().getTime();
            if (newend > now) {
                newend = now;
                newstart = now - delta;
            }
            this.fireEventsToAll("updateimage", {start:newstart, end:newend});
        },
        doZoom: function(factor) {
            var gp = this.graph_params;
            gp.end = this.convertEndToAbsolute(gp.end);
            var delta = Math.round(rangeToMilliseconds(gp.drange)/factor),
                // Zoom from the end
                newend = gp.end,
                newstart = (gp.end - rangeToMilliseconds(gp.drange) < 0 ? 0 : gp.end - delta);
            this.fireEventsToAll("updateimage", {
                start: newstart,
                end: newend
            });
        },
        zoomIn: function(graph) {
            this.doZoom(this.zoom_factor);
        },
        zoomOut: function(graph) {
            this.doZoom(1/this.zoom_factor);
        },
        fireEventsToAll: function() {
            if (this.linked()) {
                var args = arguments;
                Ext.each(this.up('graphpanel').getGraphs(), function(g) {
                    g.fireEvent.apply(g, args);
                });
            } else {
                this.fireEvent.apply(this, arguments);
            }
        }
    });


    Ext.define("Zenoss.form.GraphRefreshButton", {
        alias:['widget.graphrefreshbutton'],
        extend:"Zenoss.RefreshMenuButton",
        constructor: function(config) {
            config = config || {};
            var menu = {
                xtype: 'statefulrefreshmenu',
                id: config.stateId || Ext.id(),
                trigger: this,
                items: [{
                    cls: 'refreshevery',
                    text: _t('Refresh every')
                },{
                    xtype: 'menucheckitem',
                    text: _t('1 minute'),
                    value: 60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: _t('5 minutes'),
                    value: 300,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: _t('10 Minutes'),
                    value: 600,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: _t('30 Minutes'),
                    checked: true,
                    value: 1800,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: _t('1 Hour'),
                    value: 3600,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: _t('Manually'),
                    value: -1,
                    group: 'refreshgroup'
                }]
            };
            Ext.apply(config, {
                menu: menu
            });
            this.callParent(arguments);
        }
    });


    Ext.define("Zenoss.form.DRangeSelector", {
        alias:['widget.drangeselector'],
        extend:"Ext.form.ComboBox",
        constructor: function(config) {
            config = config || {};
            Ext.apply(config, {
                fieldLabel: _t('Range'),
                    name: 'ranges',
                    editable: false,
                    forceSelection: true,
                    autoSelect: true,
                    triggerAction: 'all',
                    value: '1h-ago',
                    queryMode: 'local',
                    store: new Ext.data.ArrayStore({
                        id: 0,
                        model: 'Zenoss.model.IdName',
                        data: DATE_RANGES
                    }),
                    valueField: 'id',
                    displayField: 'name'
            });
            this.callParent(arguments);
        }
    });

    dateRangePanel = [{
        margin: '10, 0, 15, 0',
        xtype: 'container',
        layout: 'hbox',
        defaults: {
            margin: '0 0 0 10',
            labelWidth: 30
        },
        items:[{
            xtype: 'datefield',
            ref: '../start_date',
            width: 250,
            fieldLabel: _t('Start'),
            format:'Y-m-d H:i:s',
            // the default is one hour ago
            value: Ext.Date.format(new Date((new Date().getTime() - 3600 * 1000)), "Y-m-d H:i:s")
        },{
            xtype: 'container',
            width: 5
        },{
            xtype: 'datefield',
            ref: '../end_date',
            width: 250,
            fieldLabel: _t('End'),
            disabled: true,
            format:'Y-m-d H:i:s',
            value: Ext.Date.format(new Date(), "Y-m-d H:i:s")
        }, {
            xtype: 'checkbox',
            ref: '../checkbox_now',
            fieldLabel: _t('Now'),
            checked: true,
            listeners: {
                change: function(chkbox, newValue) {
                    chkbox.refOwner.end_date.setDisabled(newValue);
                }
            }
        }, {
            xtype: 'button',
            text: _t('Update'),
            ref: '../updatebutton',
            handler: function(b){
                var me = b.refOwner;
                me.start = me.start_date.getValue().getTime();
                me.updateEndTime();
                me.end = me.end_date.getValue().getTime();
                Ext.each(me.getGraphs(), function(g) {
                    g.fireEvent("updateimage", {
                        start: me.start,
                        end: me.end
                    }, me);
                });
            }
        }]
    }];

    function getTBarConfig(title) {
        var tbarConfig = [
            {
                xtype: 'tbtext',
                text: title || _t('Performance Graphs')
            },
            '-',
            '->',
            {
                xtype: 'drangeselector',
                ref: '../drange_select',
                listeners: {
                    select: function(combo, records, index){
                        var value = records[0].data.id,
                        panel = combo.refOwner;
                        panel.setDrange(value);
                    }
                }
            },'-', {
                xtype: 'button',
                ref: '../resetBtn',
                text: _t('Reset'),
                handler: function(btn) {
                    var panel = btn.refOwner;
                    panel.setDrange();
                }
            },'-',{
                xtype: 'tbtext',
                text: _t('Link Graphs?:')
            },{
                xtype: 'checkbox',
                ref: '../linkGraphs',
                checked: true,
                listeners: {
                    change: function(chkBx, checked) {
                        var panel = chkBx.refOwner;
                        panel.setLinked(checked);
                    }
                }
            }, '-',{
                xtype: 'graphrefreshbutton',
                ref: '../refreshmenu',
                iconCls: 'refresh',
                text: _t('Refresh'),
                handler: function(btn) {
                    if (btn) {
                        var panel = btn.refOwner;
                            panel.refresh();
                    }
                }
            }, '-', {
                xtype: 'button',
                ref: '../newwindow',
                iconCls: 'newwindow',
                hidden: true,
                handler: function(btn) {
                    var panel = btn.refOwner;
                    var config = panel.initialConfig,
                    win = Ext.create('Zenoss.dialog.BaseWindow',  {
                        cls: 'white-background-panel',
                        layout: 'fit',
                        items: [Ext.apply(config,{
                            id: 'device_graphs_window',
                            xtype: 'graphpanel',
                            ref: 'graphPanel',
                            uid: panel.uid,
                            newWindowButton: false
                        })],
                        maximized: true
                    });
                    win.show();
                    win.graphPanel.setContext(panel.uid);
                }
            }];
        return tbarConfig;
    }


    Ext.define("Zenoss.form.GraphPanel", {
        alias:['widget.graphpanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            // default to showing the toolbar
            if (!Ext.isDefined(config.showToolbar) ) {
                config.showToolbar = true;
            }

            Ext.applyIf(config, {
                drange: DATE_RANGES[0][0],
                isLinked: true,
                newWindowButton: true,
                // images show up after Ext has calculated the
                // size of the div
                bodyStyle: {
                    overflow: 'auto'
                },
                directFn: router.getGraphDefs
            });
            if (config.showToolbar){
                config.tbar = getTBarConfig(config.tbarTitle);
            }
            Zenoss.form.GraphPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            if (this.newwindow) {
                if (this.newWindowButton) {
                    this.newwindow.show();
                } else {
                    this.newwindow.hide();
                }
            }

            // remove all the graphs
            this.removeAll();
            this.lastShown = 0;

            var params = {
                uid: uid,
                drange: this.drange
            };
            this.uid = uid;
            this.directFn(params, Ext.bind(this.loadGraphs, this));
        },
        loadGraphs: function(result){
            if (!result.success){
                return;
            }
            var data = result.data,
                panel = this,
                el = this.getEl();

            if (el.isMasked()) {
                el.unmask();
            }
            // this is defined by the visualization library, if it is missing then we can not
            // render any charts
            if (!Ext.isDefined(window.zenoss)) {
                el.mask(_t('Unable to load the visualization library.') , 'x-mask-msg-noicon');
            } else if (data.length > 0){
                this.addGraphs(data);
            }else{
                // no graphs were returned
                el.mask(_t('No Graph Data') , 'x-mask-msg-noicon');
            }
        },
        addGraphs: function(data) {
            var graphs = [],
                graph,
                graphId,
                me = this,
                start = this.lastShown,
                end = this.lastShown + GRAPHPAGESIZE,
                graphTitle,
                i;

            // load graphs until we have either completed the page or
            // we ran out of graphs
            for (i=start; i < Math.min(end, data.length); i++) {
                graph = data[i];
                graphId = Ext.id();
                graphTitle = graph.title;
                delete graph.title;
                graphs.push(new Zenoss.EuropaGraph(Ext.applyIf(graph, {
                    uid: this.uid,
                    graphId: graphId,
                    graphTitle: graphTitle,
                    isLinked: this.isLinked,
                    ref: graphId
                })));
            }

            // set up for the next page
            this.lastShown = end;

            // if we have more to show, add a button
            if (data.length > end) {
                graphs.push({
                    xtype: 'button',
                    text: _t('Show more results...'),
                    margin: '0 0 7 7',
                    handler: function(t) {
                        t.hide();
                        // will show the next page by looking at this.lastShown
                        me.addGraphs(data);
                    }
                });
            }
            // render the graphs
            if (this.columns) {
                this.organizeGraphsIntoColumns(graphs, this.columns);
            } else {
                // if we are not paginating then add the date range filter
                if (!this.start_date) {
                    graphs = Ext.Array.clone(dateRangePanel).concat(graphs);
                }
                this.add(graphs);
            }
        },
        organizeGraphsIntoColumns: function(graphs, numCols) {
            var columns = [], i, col=0;
            // create a column container for each column specified
            for (i=0; i < numCols; i ++) {
                columns.push({
                    xtype: 'container',
                    items: [],
                    // make them equal space
                    columnWidth: 1 / numCols
                });
            }

            // divide the graphs into buckets based on the order in which they were defined.
            for (i=0; i < graphs.length; i ++) {
                columns[col].items.push(graphs[i]);
                col++;
                if (col>=numCols) {
                    col = 0;
                }
            }

            if (!this.start_date) {
                // add the date filters as well as the columns
                this.add([{
                    xtype: 'container',
                    items: Ext.Array.clone(dateRangePanel)
                },{
                    layout: 'column',
                    items: columns
                }]);
            } else {
                // just add the columns
                this.add({
                    layout: 'column',
                    items: columns
                });
            }
        },
        updateEndTime: function(){
            if (this.checkbox_now && this.checkbox_now.getValue()) {
                this.end_date.setValue(new Date());
            }
        },
        setDrange: function(drange) {
            this.start = null;
            this.end = null;
            drange = drange || this.drange;
            this.drange = drange;
            //  set the start and end dates to the selected range.
            this.end_date.setValue(new Date());
            this.start_date.setValue(new Date(new Date().getTime() - rangeToMilliseconds(drange)));

            // tell each graph to update
            Ext.each(this.getGraphs(), function(g) {
                g.fireEvent("updateimage", {
                    drange: drange
                }, this);
            });
        },
        refresh: function() {
            // if we are rendered but not visible do not refresh
            if (this.isVisible()) {
                this.updateEndTime();
                Ext.each(this.getGraphs(), function(g) {
                    g.fireEvent("updateimage", {
                        // if they selected a specific start then use that otherwise use the drange
                        start: this.start || this.drange,
                        end: this.end || CURRENT_TIME
                    }, this);
                });
            }
        },
        getGraphs: function() {
            return this.query('europagraph');
        },
        setLinked: function(isLinked) {
            this.isLinked = isLinked;
            Ext.each(this.getGraphs(), function(g){
                g.setLinked(isLinked);
            });
        }
    });



}());
