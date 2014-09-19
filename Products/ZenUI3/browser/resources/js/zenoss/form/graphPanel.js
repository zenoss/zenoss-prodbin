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
        DATEFIELD_DATE_FORMAT = "YYYY-MM-DD HH:mm:ss",
        GraphRefreshButton,
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
            '30d-ago': 2419200000,
            '1y-ago': 31536000000
        },
        DOWNSAMPLE = [
            // for now when the delta is < 1 hour we do NOT do downsampling
            [3600000, '10s-avg'],     // 1 Hour
            [7200000, '30s-avg'],     // 2 Hours
            [14400000, '45s-avg'],    // 4 Hours
            [18000000, '1m-avg'],     // 5 Hours
            [28800000, '2m-avg'],     // 8 Hours
            [43200000, '3m-avg'],     // 12 Hours
            [64800000, '4m-avg'],     // 18 Hours
            [86400000, '5m-avg'],     // 1 Day
            [172800000, '10m-avg'],   // 2 Days
            [259200000, '15m-avg'],   // 3 Days
            [604800000, '1h-avg'],    // 1 Week
            [1209600000, '2h-avg'],   // 2 Weeks
            [2419200000, '6h-avg'],   // 1 Month
            [9676800000, '1d-avg'],   // 4 Months
            [31536000000, '10d-avg']  // 1 Year
        ],

        /*
         * If a given request is over GRAPHPAGESIZE then
         * the results will be paginated.
         * Lower the number of graphs that are displayed for IE
         * since it dramatically speeds up the rendering speed.
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
        return d.getUTCFullYear() + '/' + (d.getUTCMonth() + 1).pad(2) + '/' + d.getUTCDate().pad(2) + '-' +
            d.getUTCHours().pad(2) + ':' + d.getUTCMinutes().pad(2) + ':' + d.getUTCSeconds().pad(2) + '-UTC';
    }

    Date.prototype.minus = function(secs) {
        return new Date(this.valueOf()-(secs*1000));
    };


    Ext.define("Zenoss.EuropaGraph", {
        alias:['widget.europagraph'],
        extend: "Ext.Panel",

        zoom_factor: 1.25,
        pan_factor: 4,

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
            var padding = "padding:25px 10px 5px 0px;";
            if (config.height <= 400) {
                padding = "padding:0px 0px 0px 0px;";
            }
            // dynamically adjust the height;
            config.height = this.adjustHeightBasedOnMetrics(config.height, config.datapoints);
            config = Ext.applyIf(config||{}, {
                html: '<div id="' + config.graphId + '" style="border-style: solid; border-width:1px;' + padding +  'height:' + String(config.height - 100)  + 'px;"> ' +
                    '<div class="graph_title">'+ config.graphTitle  + ' <div class="graph_description">' + config.description  +
                    '</div></div></div>',
                maxWidth: 800,
                cls: 'graph-panel',
                graph_params: {
                    drange: DATE_RANGES[0][0],
                    end: config.end || CURRENT_TIME,
                    start: config.start || DATE_RANGES[0][0]
                }
            });
            // setup graph controls
            config.dockedItems = [{
                xtype: 'toolbar',
                dock: 'top',
                items: ['->',{
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
                    ref: '../zoomin',
                    handler: Ext.bind(function(btn, e) {
                        this.doZoom.call(this, 0, 1/this.zoom_factor);
                    }, this)
                },{
                    text: _t('Zoom Out'),
                    ref: '../zoomout',
                    handler: Ext.bind(function(btn, e) {
                        this.doZoom.call(this, 0, this.zoom_factor);
                    }, this)
                },{
                    text: '&gt;',
                    width: 40,
                    handler: Ext.bind(function(btn, e) {
                        this.onPanRight(this);
                    }, this)
                }]
            }];

            Zenoss.EuropaGraph.superclass.constructor.call(this, config);
        },
        initComponent: function() {
            // the visualization library depends on our div rendering,
            // let's make sure that has happened
            this.on('afterrender', this.initChart, this);
            this.callParent(arguments);
        },
        initChart: function() {
            // these assume that the graph panel has already been rendered
            var width = this.getEl().getWidth(), height = this.getEl().getHeight();
            var visconfig = {
                returnset: "EXACT",
                range : {
                    start : formatForMetricService(this.graph_params.start),
                    end : formatForMetricService(this.graph_params.end)
                },
                base: this.base,
                tags: this.tags,
                datapoints: this.datapoints,
                overlays: this.thresholds,
                type: this.type,
                // lose the footer and yaxis label as the image gets smaller
                footer: (height >= 350) ? true : false,
                yAxisLabel: this.units,
                miny: (this.miny != -1) ? this.miny : null,
                maxy: (this.maxy != -1) ? this.maxy : null,
                // the visualization library currently only supports
                // one format for chart, not per metric
                format: (this.datapoints.length > 0) ? this.datapoints[0].format: "",
                timezone: Zenoss.USER_TIMEZONE
            };


            visconfig.downsample = this._getDownSample(this.graph_params);

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

            var config = {},
                encodedConfig, link,
                // keys to exclude when cloning config object
                exclusions = ["dockedItems"];

            // shallow clone initialConfig object as long as the
            // key being copied is no in the exclusions list.
            // This is useful because the final JSON string needs
            // to be as small as possible!
            for(var i in this.initialConfig){
                if(!~exclusions.indexOf(i)){
                    config[i] = this.initialConfig[i];
                }
            }

            encodedConfig = Zenoss.util.base64.encode(Ext.JSON.encode(config));
            link = "/zport/dmd/viewGraph?data=" + encodedConfig;

            new Zenoss.dialog.ErrorDialog({
                message: Ext.String.format(_t('<div>' + Ext.String.format(_t('Drag this link to your bookmark bar to link directly to this graph. {0}'),
                    '<br/><br/><a href="' + link + '">Graph: ' + this.graphTitle +  ' </a>') + '</div>')),
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
            var chart = zenoss.visualization.chart.getChart(this.graphId),
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
        /**
         * In response to ZEN-14295 if we have a lot of series we are trying to plot
         * ignore the set height and make the graph larger so the graph shows up.
         **/
        adjustHeightBasedOnMetrics: function(height, datapoints) {
            height = height || 500;
            // not necessary until we get above 5 datapoints
            if (datapoints.length <= 5) {
                return height;
            }

            var adjustment = height * .05;
            return height + (adjustment * datapoints.length);
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
            this.graphEl = Ext.get(this.graphId);
        },
        _getDownSample: function(gp) {
            var delta, downsample = null;
            if (Ext.isNumber(gp.start)) {
                delta = this.convertEndToAbsolute(gp.end) - gp.start;
            } else {
                delta = rangeToMilliseconds(gp.start);
            }

            // no downsampling for less than one hour.
            if (delta <  3600) {
                return null;
            }
            Ext.Array.each(DOWNSAMPLE, function(v) {
                if (delta >= v[0]) {
                    downsample = v[1];
                }
            });
            return downsample;
        },
        updateGraph: function(params) {
            var gp = Ext.apply({}, params, this.graph_params);
            gp.start = params.start || gp.start;
            if (gp.start < 0) {
                gp.start = 0;
            }

            // see if end is explicitly defined on the params
            if (Ext.isDefined(params.end) && (params.end > params.start)){
                gp.end = params.end;
            }

            var changes = {
                range : {
                    start: formatForMetricService(gp.start),
                    end: formatForMetricService(gp.end)
                }
            };
            changes.downsample = this._getDownSample(gp);
            zenoss.visualization.chart.update(this.graphId, changes);

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
                return now();
            }
            return end;
        },
        onPanLeft: function(graph) {
            var gp = this.graph_params;
            gp.start = this.convertStartToAbsoluteTime(gp.start);
            var delta = Math.round(rangeToMilliseconds(gp.drange)/this.pan_factor);
            var newstart = (gp.start) - delta > 0 ? gp.start - delta : 0;
            var newend = newstart + rangeToMilliseconds(gp.drange);

            this.fireEvent("updatelimits", {start:newstart, end:newend});
            this.fireEvent("updateimage", {start:newstart, end:newend});
        },
        onPanRight: function(graph) {
            var gp = this.graph_params;
            gp.start = this.convertStartToAbsoluteTime(gp.start);
            var delta = Math.round(rangeToMilliseconds(gp.drange)/this.pan_factor);
            var newstart = gp.start + delta > 0 ? gp.start + delta : 0;
            var newend = newstart + rangeToMilliseconds(gp.drange);
            var currTime = now();
            if (newend > currTime) {
                newend = currTime;
                newstart = currTime - delta;
            }

            this.fireEvent("updatelimits", {start:newstart, end:newend});
            this.fireEvent("updateimage", {start:newstart, end:newend});
        },
        doZoom: function(xpos, factor) {
            var gp = this.graph_params,
                el = Ext.get(this.graphId);

            gp.end = this.convertEndToAbsolute(gp.end);
            gp.drange = rangeToMilliseconds(gp.drange) * factor;

            var end = gp.end,
                start = gp.end - gp.drange;

            this.fireEvent("updatelimits", { start: start, end: end });
            this.fireEvent("updateimage", { start: start, end: end });
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
                        data: DATE_RANGES.concat([[0,"<hr>"],["custom", "["+ _t("Custom") +"]"]])
                    }),
                    valueField: 'id',
                    displayField: 'name'
            });
            this.callParent(arguments);
        }
    });

    // datefield that uses number of ms since epoch to
    // get and set date. Also accepts a `displayTZ` property
    // which is used to offset the date that is displayed to
    // the end user.
    // NOTE: when you set the date, it should be UTC. When you
    // get the date, it will be UTC. The `displayTZ` property is
    // only to adjust what the user sees, not to adjust the
    // actual date value.
    Ext.define("Zenoss.form.UTCDateField", {
        alias:['widget.utcdatefield'],
        extend:"Ext.form.DateField",
        constructor: function(config) {
            config = config || {};

            // "Africa/Abidjan" is moment.tz default UTC zone
            this.setDisplayTimezone(config.displayTZ || "Africa/Abidjan");

            // get the browser's local timezone so we can offset that as well :/
            // NOTE: zone returns minutes, so convert to milliseconds
            this.TZLocalMS = moment().zone() * 60 * 1000;

            this.callParent(arguments);
        },

        setDisplayTimezone: function(tz){
            // store provided timezone
            this.displayTZ = tz;

            // get timezone offset *in hours* and convert hours to ms
            this.TZOffsetMS = (+moment.utc().tz(this.displayTZ).format("ZZ") * 0.01) * 1000 * 60 * 60;
        },

        setValue: function(ms, isAdjusted){
            if(!ms){
                return;
            }

            var adjustedTime;

            // if someone is using a date object, get
            // the UTC time and use that
            if(ms instanceof Date){
                ms = ms.getTime();
            }

            // if incoming time is already adjusted, do not attempt
            // to offset it (this is the case when the value is coming
            // from inside the datepicker instead of outside)
            if(!isAdjusted){
                // take provided time, offset with local timezone, then
                // offset with displayTZ
                adjustedTime = ms + this.TZOffsetMS + this.TZLocalMS;
            } else {
                adjustedTime = ms;
            }

            this.callParent([new Date(adjustedTime)]);

            return this;
        },

        // returns ms since epoch (UTC)
        getValue: function(){
            // clear any previous offsets and return just the UTC
            // time since epoch
            return this.value.getTime() - this.TZOffsetMS - this.TZLocalMS;
        },

        beforeBlur : function(){
            var me = this,
                v = me.parseDate(me.getRawValue()),
                focusTask = me.focusTask;

            if (focusTask) {
                focusTask.cancel();
            }

            if (v) {
                // setValue but do not adjust for timezones because
                // it is already adjusted
                me.setValue(v, true);
            }
        },

        onSelect: function(m, d) {
            var me = this;

            // setValue but do not adjust for timezones because
            // it is already adjusted
            me.setValue(d, true);

            me.fireEvent('select', me, d);
            me.collapse();
        }
    });

    var tbarConfig = [
        '-',
        '->',

        {
            xtype: 'drangeselector',
            cls: 'drange_select',
            labelWidth: 40,
            labelAlign: "right",
            listeners: {
                select: function(self, records, index){
                    var value = records[0].data.id,
                        panel = self.up("graphpanel");

                    // if value is "custom", then reveal the date
                    // picker container
                    if(value === "custom"){
                        panel.showDatePicker();

                    // if user selected the separator, select custom
                    } else if(value === 0){
                        self.setValue("custom");
                        panel.showDatePicker();

                    // otherwise, update graphs
                    } else {
                        // all ranges are relative to now, so set
                        // end to current time
                        panel.setEndToNow();
                        panel.hideDatePicker();
                        // update drange and start values based
                        // on the new end value
                        panel.setDrange(value);
                    }
                }
            }
        },

        "-",

        {
            xtype: "container",
            layout: "hbox",
            cls: "date_picker_container",
            padding: "0 10 0 0",
            items: [
                {
                    xtype: 'utcdatefield',
                    cls: 'start_date',
                    width: 250,
                    fieldLabel: _t('Start'),
                    labelWidth: 40,
                    labelAlign: "right",
                    format:'Y-m-d H:i:s',
                    displayTZ: Zenoss.USER_TIMEZONE,
                    listeners: {
                        change: function(self, val){
                            var panel = self.up("graphpanel");
                            //update graphpanel.start with *UTC time*
                            //NOTE: panel.start should *always* be UTC!
                            panel.start = moment.utc(self.getValue());
                        }
                    }
                },{
                    xtype: 'utcdatefield',
                    cls: 'end_date',
                    width: 250,
                    fieldLabel: _t('End'),
                    labelWidth: 40,
                    labelAlign: "right",
                    disabled: true,
                    format:'Y-m-d H:i:s',
                    displayTZ: Zenoss.USER_TIMEZONE,
                    listeners: {
                        change: function(self, val){
                            var panel = self.up("graphpanel");
                            //update graphpanel.end with *UTC time*
                            //NOTE: panel.end should *always* be UTC!
                            panel.end = moment.utc(self.getValue());
                        }
                    }
                },{
                    xtype: 'checkbox',
                    cls: 'checkbox_now',
                    fieldLabel: _t('Now'),
                    labelWidth: 40,
                    labelAlign: "right",
                    checked: true,
                    listeners: {
                        change: function(self, val) {
                            var panel = self.up("graphpanel");
                            panel.query("datefield[cls='end_date']")[0].setDisabled(val);

                            // if it should be now, update it
                            if(val){
                                panel.setEndToNow();
                            }
                        }
                    }
                }
            ]
        },

        {
            xtype: 'graphrefreshbutton',
            ref: '../refreshmenu',
            iconCls: 'refresh',
            text: _t('Refresh'),
            handler: function(btn) {
                if (btn) {
                    var panel = btn.up("graphpanel");
                    panel.refresh();
                }
            }
        },
        '-',
        {
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
        tbar: tbarConfig,
        cls: "graphpanel",
        constructor: function(config) {
            config = config || {};

            var toolbar;

            Ext.applyIf(config, {
                drange: DATE_RANGES[0][0],
                newWindowButton: true,
                columns: 1,
                // images show up after Ext has calculated the
                // size of the div
                bodyStyle: {
                    overflow: 'auto'
                },
                directFn: router.getGraphDefs
            });

            Zenoss.form.GraphPanel.superclass.constructor.apply(this, arguments);

            // assumes just one docked item
            this.toolbar = this.getDockedItems()[0];

            this.startDatePicker = this.toolbar.query("utcdatefield[cls='start_date']")[0];
            this.endDatePicker = this.toolbar.query("utcdatefield[cls='end_date']")[0];
            this.nowCheck = this.toolbar.query("checkbox[cls='checkbox_now']")[0];

            this.startDatePicker.setDisplayTimezone(Zenoss.USER_TIMEZONE);
            this.endDatePicker.setDisplayTimezone(Zenoss.USER_TIMEZONE);

            // add title to toolbar
            this.toolbar.insert(0, {
                xtype: 'tbtext',
                text: config.tbarTitle || _t('Performance Graphs')
            });

            // default range value of 1 hour
            // NOTE: this should be a real number, not a relative
            // measurement like "1h-ago"
            this.drange = rangeToMilliseconds("1h-ago");

            // default start and end values in UTC time
            // NOTE: do not apply timezone adjustments to these values!
            this.start = moment.utc().subtract("ms", this.drange);
            this.setEndToNow();

            // set start and end dates
            this.updateStartDatePicker();
            this.updateEndDatePicker();

            this.hideDatePicker();

            if (config.hideToolbar){
                this.toolbar.hide();
            }
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

            if (el && el.isMasked()) {
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
                if(el){
                   el.mask(_t('No Graph Data') , 'x-mask-msg-noicon');
                }

                this.toolbar.query("graphrefreshbutton")[0].setInterval(-1);
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
                    ref: graphId,
                    height: 500
                })));

                // subscribe to updatelimits event
                graphs[graphs.length-1].on("updatelimits", function(limits){
                    this.setLimits(limits.start, limits.end);
                    this.refresh();
                }, this);
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
            this.organizeGraphsIntoColumns(graphs, this.columns);
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

            this.add({
                layout: 'column',
                items: columns
            });
        },
        refresh: function() {
            // if end should be set to `now`, set it
            if(this.nowCheck.getValue()){
                this.setEndToNow();
            }

            graphConfig = {
                drange: this.drange,
                // start and end are moments so they need to be
                // converted to millisecond values
                start: this.start.valueOf(),
                end: this.end.valueOf()
            };

            // if we are rendered but not visible do not refresh
            if(this.isVisible()){
                Ext.each(this.getGraphs(), function(g) {
                    g.fireEvent("updateimage", graphConfig, this);
                });
            }
        },
        getGraphs: function() {
            return this.query('europagraph');
        },

        ///////////////////////////
        // graph time and range type stuff
        //

        setDrange: function(drange) {
            this.drange = drange || this.drange;

            var graphConfig;

            // if drange is relative measurement, convert to ms
            if(!Ext.isNumeric(this.drange)){
                this.drange = rangeToMilliseconds(this.drange);
            }

            // check `now` checkbox since drange is always set from now
            this.nowCheck.setValue(true);

            // update start to reflect new range
            this.start = this.end.clone().subtract("ms", this.drange);

            //  set the start and end dates to the selected range.
            this.updateStartDatePicker();
            this.updateEndDatePicker();

            this.refresh();
        },

        setLimits: function(start, end){
            // TODO - validate end is greater than start
            this.start = moment.utc(start);
            this.end = moment.utc(end);

            // these limits require a custom date range
            this.drange = end - start;

            // set the range combo to custom
            this.toolbar.query("drangeselector[cls='drange_select']")[0].setValue("custom");

            // uncheck `now` checkbox since we're using a custom range
            this.nowCheck.setValue(false);

            this.showDatePicker();

            //  set the start and end dates to the selected range.
            this.updateStartDatePicker();
            this.updateEndDatePicker();
        },

        setEndToNow: function(){
            this.end = moment.utc();
            this.updateEndDatePicker();

            // if the "now" checkbox is set and range isn't custom, start time should be updated as well
            if(this.nowCheck.getValue() && this.toolbar.query("drangeselector")[0].getValue() !== "custom"){
                this.start = this.end.clone().subtract("ms", this.drange);
                this.updateStartDatePicker();
            }
        },

        // updates date picker with stored date value, offset for timezone,
        // but forced to be treated as UTC to prevent additional timezone offset
        updateStartDatePicker: function(){
            this.startDatePicker.suspendEvents();
            this.startDatePicker.setValue(this.start.valueOf());
            this.startDatePicker.resumeEvents(false);
        },
        updateEndDatePicker: function(){
            this.endDatePicker.suspendEvents();
            this.endDatePicker.setValue(this.end.valueOf());
            this.endDatePicker.resumeEvents(false);
        },

        showDatePicker: function(){
            // show date picker stuff
            this.toolbar.query("container[cls='date_picker_container']")[0].show();
        },
        hideDatePicker: function(){
            // hide date picker stuff
            this.toolbar.query("container[cls='date_picker_container']")[0].hide();
        }
    });



}());
