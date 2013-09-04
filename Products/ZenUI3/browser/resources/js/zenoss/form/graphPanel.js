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
        tbarConfig,
        dateRangePanel,
        DATE_RANGES = [
            [3600000, _t('Last Hour')],
            [86400000, _t('Yesterday')],
            [604800000, _t('Last Week')],
            [2419200000, _t('Last Month')],
            [31536000000, _t('Last Year')]
        ],
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

    function formatForMetricService(ms) {
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
        start: now(),

        /**
         * @cfg {int} end
         * The end time of the graph in unix seconds.
         * Defaults to <code>new DateTime().getTime() - 3600 (an hour ago)</code>.
         */
        end: now() - DATE_RANGES[0][0],

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
            config = Ext.applyIf(config||{}, {
                html: '<div id="' + config.graphId + '" style="border-style: solid; border-width:1px;"></div>',
                cls: 'graph-panel',
                tbar: {
                    items: [{
                        xtype: 'tbtext',
                        text: config.graphTitle // + ' : ' + config.uid
                    },'->',{
                        xtype: 'button',
                        text: "?",
                        handler: Ext.bind(this.displayDefinition, this)
                    },{
                        text: '&lt;',
                        width: 67,
                        handler: Ext.bind(function(btn, e) {
                            this.onPanLeft(this);
                        }, this)
                    },{
                        text: _t('Zoom In'),
                        ref: '../zoomin',
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
                        width: 67,
                        handler: Ext.bind(function(btn, e) {
                            this.onPanRight(this);
                        }, this)
                    }]
                },
                graph_params: {
                    drange: DATE_RANGES[0][0],
                    end: config.end || now(),
                    start: config.start || now() - DATE_RANGES[0][0]
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
                type: this.type,
                footer: true
            };
            this.chartdefinition = visconfig;
            zenoss.visualization.chart.create(this.graphId, visconfig);
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
            gp.start = params.start || (gp.end - gp.drange);
            if (gp.start < 0) {
                gp.start = 0;
            }

            // see if end is explicitly defined on the params
            if (Ext.isDefined(params.end) && (params.end > params.start)){
                gp.end = params.end;
            } else {
                gp.end = Math.max(gp.start + gp.drange, new Date().getTime());
            }
            var changes = {
                range : {
                    start: formatForMetricService(gp.start),
                    end: formatForMetricService(gp.end)
                }
            };
            var delta = gp.end - gp.start;
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
        onPanLeft: function(graph) {
            var gp = this.graph_params;
            var delta = Math.round(gp.drange/this.pan_factor);
            var newstart = gp.start - delta > 0 ? gp.start - delta : 0;
            var newend = newstart + gp.drange;
            this.fireEventsToAll("updateimage", {start:newstart, end:newend});
        },
        onPanRight: function(graph) {
            var gp = this.graph_params;
            var delta = Math.round(gp.drange/this.pan_factor);
            var newstart = gp.start + delta > 0 ? gp.start + delta : 0;
            var newend = newstart + gp.drange;
            var now = new Date().getTime();
            if (newend > now) {
                newend = now;
                newstart = now - delta;
            }
            this.fireEventsToAll("updateimage", {start:newstart, end:newend});
        },
        doZoom: function(factor) {
            var gp = this.graph_params;
            var drange = Math.round(gp.drange/factor),
                // Zoom from the end
                newend = gp.end;
                newstart = (gp.end - drange < 0 ? 0 : gp.end - drange);

            this.fireEventsToAll("updateimage", {
                drange: drange,
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
                Ext.each(this.refOwner.getGraphs(), function(g) {
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
                    value: 3600000,
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
    tbarConfig = [
        {
            xtype: 'tbtext',
            text: _t('Performance Graphs')
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
                config.tbar = tbarConfig;
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

            if (data.length > 0){
                this.addGraphs(data);
            }else{
                el.mask(_t('No Graph Data') , 'x-mask-msg-noicon');
            }
        },
        addGraphs: function(data) {
            var graphs,
                graph,
                graphId,
                me = this,
                start = this.lastShown,
                end = this.lastShown + GRAPHPAGESIZE,
                i;
            // if we haven't already, show the start and end time widgets
            if (!this.start_date) {
                graphs = Ext.Array.clone(dateRangePanel);
            }

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
            this.add(graphs);
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
            //  set the start and end dates to the selected range
            this.end_date.setValue(new Date());
            this.start_date.setValue(new Date(new Date().getTime() - drange));

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
                        start: this.start || null,
                        end: this.end || null
                    }, this);
                });
            }
        },
        getGraphs: function() {
            var graphs = Zenoss.util.filter(this.items.items, function(item){
                return item.graphId;
            });
            return graphs;
        },
        setLinked: function(isLinked) {
            this.isLinked = isLinked;
            Ext.each(this.getGraphs(), function(g){
                g.setLinked(isLinked);
            });
        }
    });



}());
