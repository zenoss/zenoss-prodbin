/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/




(function(){
    DATE_RANGES =[
            [3600000, _t('Hourly')],
            [86400000, _t('Daily')],
            [604800000, _t('Weekly')],
            [2419200000, _t('Monthly')],
            [31536000000, _t('Yearly')]
    ];

    DOWNSMAPLE = [
            [86400000, '1h-avg'],    // Day
            [604800000, '12h-avg'],  // Week
            [2419200000, '1d-avg'],  // Month
            [31536000000, '30d-avg'] // Year
    ];

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

    /**********************************************************************
     *
     * Swoopy
     *
     */
    function toISOTimestamp(d) {
        function pad(n){
            return n<10 ? '0'+n : n;
        }
        return d.getUTCFullYear()+'-'
            + pad(d.getUTCMonth()+1)+'-'
            + pad(d.getUTCDate())+'T'
            + pad(d.getUTCHours())+':'
            + pad(d.getUTCMinutes())+':'
            + pad(d.getUTCSeconds())+'Z';
    }

    Date.prototype.minus = function(secs) {
        return new Date(this.valueOf()-(secs*1000));
    };

    Date.prototype.toPretty = function() {
        return toISOTimestamp(this);
    };

    function fixBase64Padding(s) {
        s = s.split('=',1)[0];
        var a = [s];
        for (var i = 0; i <= 4 - (s.length % 4); i++) {
            a.push('=');
        }
        return a.join('');
    }

    var ZenGraphs = ZenGraphs || {},
        zoom_factor = 1.5,
        pan_factor = 3,
        end_re = /now-([0-9]*)s/,
        start_re = /end-([0-9]*)s/;

    Ext.ns('Zenoss');

    Zenoss.SWOOP_CALLBACKS = {};

    Zenoss.EuropaGraph = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                html: '<div id="' + config.graphId + '" style="border-style: solid; border-width:1px;"></div>',
                width: 607,
                height: 250,
                ls: 'graph-panel',
                tbar: {
                    items: [{
                        xtype: 'tbtext',
                        text: config.graphTitle // + ' : ' + config.uid
                    },'->',{
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
                    end: now(),
                    start: now() - DATE_RANGES[0][0]
                }
            });

            Zenoss.EuropaGraph.superclass.constructor.call(this, config);
            var visconfig = {
                exact : true,
                range : {
                    start : formatForMetricService(this.graph_params.start),
                    end : formatForMetricService(this.graph_params.end)
                },
                width: config.width,
                height: config.height - 25,
                tags: config.tags
            };
            console.log(visconfig);
            console.log(config);
            zenoss.visualization.chart.create(config.graphId, config.graphId, visconfig);
        },
        initEvents: function() {
            Zenoss.EuropaGraph.superclass.initEvents.call(this);
            this.on('updateimage', this.updateGraph, this);
        },
        getComment: function(start, end) {
            var now = new Date(),
                endDate = now.minus(end).toPretty(),
                startDate = now.minus(start + end).toPretty();
            var com_ctr = "\\t\\t to \\t\\t";
            var comment = startDate + com_ctr + endDate;
            comment = comment.replace(/:/g, '\\:');
            return comment;
        },
        linked: function() {
            return this.isLinked;
        },
        setLinked: function(isLinked) {
            this.isLinked = isLinked;
        },
        updateGraph: function(params) {
            var gp = Ext.apply({}, params, this.graph_params);
            gp.start = gp.end - gp.drange;
            if (gp.start < 0) {
                gp.start = 0;
            }
            gp.end = Math.max(gp.start + gp.drange, new Date().getTime())
            gp.comment = this.getComment(gp.start, gp.end);
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
            var delta = Math.round(gp.drange/pan_factor);
            var newstart = gp.start - delta > 0 ? gp.start - delta : 0;
            var newend = newstart + gp.drange;
            this.fireEventsToAll("updateimage", {start:newstart, end:newend});
        },
        onPanRight: function(graph) {
            var gp = this.graph_params;
            var delta = Math.round(gp.drange/pan_factor);
            var newstart = gp.start + delta > 0 ? gp.start + delta : 0;
            var newend = newstart + gp.drange;
            var now = new Date().getTime();
            if (newend > now) {
                newend = now;
                newstart = now - drange;
            }
            this.fireEventsToAll("updateimage", {start:newstart, end:newend});
        },
        doZoom: function(factor) {
            var gp = this.graph_params;
            var drange = Math.round(gp.drange/factor),
                // Zoom from the end
                newend = gp.end;
                newstart = (gp.end - drange < 0 ? 0 : gp.end - drange);
            console.error(+drange + " " + newend + " " + newstart);
            this.fireEventsToAll("updateimage", {
                drange: drange,
                start: newstart,
                end: newend
            });
        },
        zoomIn: function(graph) {
            this.doZoom(zoom_factor);
        },
        zoomOut: function(graph) {
            this.doZoom(1/zoom_factor);
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

    Zenoss.SwoopyGraph = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            var cls = Ext.isGecko ? '-moz-zoom-in' :
                Ext.isWebKit ? '-webkit-zoom-in' :
                'crosshair';
            config = Ext.applyIf(config||{}, {
                html: {
                    tag: 'img',
                    src: config.graphUrl,
                    id: config.graphId,
                    style: 'cursor:' + cls
                },
                width: 607,
                cls: 'graph-panel',
                tbar: {
                    items: [{
                        xtype: 'tbtext',
                        text: config.graphTitle
                    },'->',{
                        text: '&lt;',
                        width: 67,
                        handler: Ext.bind(function(btn, e) {
                            this.onPanLeft(this);
                        }, this)
                    },{
                        text: _t('Zoom In'),
                        enableToggle: true,
                        pressed: true,
                        ref: '../zoomin',
                        handler: Ext.bind(function(btn, e) {
                            this.fireEventsToAll("zoommodechange", this, !btn.pressed);
                        }, this)
                    },{
                        text: _t('Zoom Out'),
                        ref: '../zoomout',
                        enableToggle: true,
                        handler: Ext.bind(function(btn, e) {
                            this.fireEventsToAll("zoommodechange", this, btn.pressed);
                        }, this)
                    },{
                        text: '&gt;',
                        width: 67,
                        handler: Ext.bind(function(btn, e) {
                            this.onPanRight(this);
                        }, this)
                    }]
                }
            });
            Zenoss.SwoopyGraph.superclass.constructor.call(this, config);
            this.mustUseImageUri = Ext.isIE;
        },
        initEvents: function() {
            this.addEvents("zoommodechange", "updateimage");
            Zenoss.SwoopyGraph.superclass.initEvents.call(this);
            this.on("zoommodechange", this.onZoomModeChange, this);
            this.on("updateimage", this.updateImage, this);
            this.graphEl = Ext.get(this.graphId);
            this.graphEl.on('click', this.onGraphClick, this);
            this.graphEl.on('load', function(){
                this.suspendLayouts();
                var size = this.graphEl.getSize();
                // set out panel to be the size of the graph
                // plus a little for the padding
                this.setWidth(size.width + 10);
                this.setHeight(size.height + 42);
                this.el.setHeight(size.height + 42); /* this line is for chrome */
                if (!size.width || !size.height){
                    this.showFailure();
                } else {
                    this.parseGraphParams();
                }
                this.resumeLayouts(true);
            }, this, {single:true});
        },
        showFailure: function() {
            this.failureMask = this.failureMask || Ext.DomHelper.insertAfter(this.graphEl, {
                tag: 'div',
                html: _t("There was a problem rendering this graph. Either the file does not exist or an error has occurred.  Initial graph creation can take up to 5 minutes.  If the graph still does not appear, look in the Zope log file $ZENHOME/log/event.log for errors.")
            });
            var el = Ext.fly(this.failureMask);
            var size = this.graphEl.getSize();
            if (!size.width || !size.height) {
                size = {height:150, width:500};
            }
            el.setSize(size);
            Ext.fly(this.failureMask).setDisplayed(true);
            this.graphEl.setDisplayed(false);
        },
        hideFailure: function() {
            if (this.failureMask) {
                this.graphEl.setDisplayed(true);
                Ext.fly(this.failureMask).setDisplayed(false);
            }
        },
        parseGraphParams: function(url) {
            url = url || this.graphEl.dom.src;
            var href = url.split('?'),
            gp = Ext.apply({url:href[0]}, Ext.urlDecode(href[1]));
            // Encoding can screw with the '=' padding at the end of gopts, so
            // strip and recreate it
            gp.gopts = fixBase64Padding(gp.gopts);
            gp.width = Number(gp.width);
            gp.drange = Number(gp.drange);
            gp.start = Ext.isDefined(gp.start) ? Number(start_re.exec(gp.start)[1]) : gp.drange;
            gp.end = Ext.isDefined(gp.end) ? Number(end_re.exec(gp.end)[1]) : 0;
            this.graph_params = gp;
        },
        getComment: function(start, end) {
            var now = new Date(),
                endDate = now.minus(end).toPretty(),
                startDate = now.minus(start + end).toPretty();
            var com_ctr = "\\t\\t to \\t\\t";
            var comment = startDate + com_ctr + endDate;
            comment = comment.replace(/:/g, '\\:');
            return comment;
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
        },
        linked: function() {
            return this.isLinked;
        },
        setLinked: function(isLinked) {
            this.isLinked = isLinked;
        },
        updateImage: function(params) {
            /*
             * params should look like:
             * {drange:n, start:n, end:n}
             */
            var gp = Ext.apply({}, params, this.graph_params);
            gp.comment = this.getComment(gp.start, gp.end);
            gp.end = 'now-' + gp.end + 's';
            gp.start = 'end-' + gp.start + 's';
            this.sendRequest(gp);
        },
        sendRequest: function(params) {
            var url = params.url,
                swoopie = this;
            delete params.url;
            params.getImage = null;
            if (this.mustUseImageUri === true) {
                params.getImage = true;
            }
            var now = new Date().getTime();
            var graphid = now + '_' + this.graphId;
            params.graphid = graphid;

            var fullurl = Ext.urlAppend(url, Ext.urlEncode(params));

            if (this.mustUseImageUri === true) {
                // IE 6 and 7 Cannoy display data:image stuff in image
                // src. If it's one of those browsers,
                // skip the SWOOP stuff and just set the image src.
                this.graphEl.dom.src = fullurl;
                this.parseGraphParams(fullurl);
            } else {
                Zenoss.SWOOP_CALLBACKS[graphid] = Ext.bind(function(packet) {
                    var ob = Ext.decode(packet);
                    if (ob.success) {
                        this.hideFailure();
                        this.graphEl.dom.src = "data:image/png;base64," + ob.data;
                        this.parseGraphParams(fullurl);
                    } else {
                        this.showFailure();
                    }
                    // Clean up callbacks and script tags
                    delete Zenoss.SWOOP_CALLBACKS[graphid];
                    Ext.get(graphid).remove();
                }, this);
                var sc = Ext.DomHelper.createDom({
                    tag: 'script',
                    id: graphid,
                    type: 'text/javascript',
                    src: fullurl
                });

                Ext.getDoc().dom.getElementsByTagName('head')[0].appendChild(sc);
            }

        },
        onPanLeft: function(graph) {
            var gp = this.graph_params;
            var delta = Math.round(gp.drange/pan_factor);
            var newend = gp.end + delta > 0 ? gp.end + delta : 0;
            this.fireEventsToAll("updateimage", {end:newend});
        },
        onPanRight: function(graph) {
            var gp = this.graph_params;
            var delta = Math.round(gp.drange/pan_factor);
            var newend = gp.end - delta > 0 ? gp.end - delta : 0;
            this.fireEventsToAll("updateimage", {end:newend});
        },
        onZoomModeChange: function(graph, zoomOut) {
            this.zoomout.toggle(zoomOut);
            this.zoomin.toggle(!zoomOut);
            var dir = zoomOut ? 'out' : 'in',
                cls = Ext.isGecko ? '-moz-zoom-'+dir :
                (Ext.isWebKit ? '-webkit-zoom-'+dir : 'crosshair');
            this.graphEl.setStyle({'cursor': cls});
        },
        doZoom: function(xpos, factor) {
            var gp = this.graph_params;
            if (xpos < 0 || xpos > gp.width) {
                return;
            }
            var drange = Math.round(gp.drange/factor),
                delta = ((gp.width/2) - xpos) * (gp.drange/gp.width) + (gp.drange - drange)/2,
                end = Math.round(gp.end + delta >= 0 ? gp.end + delta : 0);
            this.fireEventsToAll("updateimage", {
                drange: drange,
                start: drange,
                end: end
            });
        },
        onGraphClick: function(e) {
            var graph = e.getTarget(null, null, true),
                x = e.getPageX() - graph.getX() - 67,
            func = this.zoomin.pressed ? this.onZoomIn : this.onZoomOut;
            func.call(this, this, x);
        },
        onZoomIn: function(graph, xpos) {
            this.doZoom(xpos, zoom_factor);
        },
        onZoomOut: function(graph, xpos) {
            this.doZoom(xpos, 1/zoom_factor);
            }
        });

    /**********************************************************************
     *
     * Graph Panel
     *
     */
    var router = Zenoss.remote.DeviceRouter,
        GraphPanel,
        DRangeSelector,
        GraphRefreshButton,
        tbarConfig;

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
                    text: 'Refresh every'
                },{
                    xtype: 'menucheckitem',
                    text: '1 minute',
                    value: 60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '5 minutes',
                    value: 300,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '10 Minutes',
                    value: 600,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '30 Minutes',
                    checked: true,
                    value: 1800,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '1 Hour',
                    value: 3600,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: 'Manually',
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


    tbarConfig = [{
                    xtype: 'tbtext',
                    text: _t('Performance Graphs')

                }, '-', '->', {
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
                    stateId: 'graphRefresh',
                    iconCls: 'refresh',
                    text: _t('Refresh'),
                    handler: function(btn) {
                        if (btn) {
                            var panel = btn.refOwner;
                            panel.resetSwoopies();
                        }
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
            if (config.showToolbar){
                config.tbar = tbarConfig;
            }
            Ext.applyIf(config, {
                drange: 129600,
                isLinked: true,
                // images show up after Ext has calculated the
                // size of the div
                bodyStyle: {
                    overflow: 'auto'
                },
                directFn: router.getGraphDefs
            });
            Zenoss.form.GraphPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
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
            var graphs = [],
                graph,
                graphId,
                me = this,
                start = this.lastShown,
                end = this.lastShown + GRAPHPAGESIZE,
                i;
            // load graphs until we have either completed the page or
            // we ran out of graphs
            for (i=start; i < Math.min(end, data.length); i++) {
                graph = data[i];
                graphId = graph.name;
                graphTitle = graph.title;
                delete graph.title;
                graphs.push(new Zenoss.EuropaGraph(Ext.apply(graph, {
                    uid: this.uid,
                    graphId: graphId,
                    graphTitle: graphTitle,
                    isLinked: this.isLinked,
                    ref: graphId
                })));
                //graphs.push(Zenoss.SwoopyGraph({
                //    graphUrl: graph.url,
                //    graphTitle: graph.title,
                //    graphId: graphId,
                //    isLinked: this.isLinked,
                //    height: 250,
                //    ref: graphId
                //}));
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
        setDrange: function(drange) {
            drange = drange || this.drange;
            this.drange = drange;
            Ext.each(this.getGraphs(), function(g) {
                g.fireEvent("updateimage", {
                    drange: drange
                }, this);
            });
        },
        resetSwoopies: function() {
            Ext.each(this.getGraphs(), function(g) {
                g.fireEvent("updateimage", {
                }, this);
            });
        },
        getGraphs: function() {
            var graphs = Zenoss.util.filter(this.items.items, function(item){
                return item.graphUrl;
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
