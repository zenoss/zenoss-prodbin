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
    var DATE_RANGES =[
            [_t('Hourly'), 129600],
            [_t('Daily'), 864000],
            [_t('Weekly'), 3628800],
            [_t('Monthly'), 41472000],
            [_t('Yearly'), 62208000]
    ];
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
                        handler: function(btn, e) {
                            this.onPanLeft(this);
                        }.createDelegate(this)
                    },{
                        text: _t('Zoom In'),
                        enableToggle: true,
                        pressed: true,
                        ref: '../zoomin',
                        handler: function(btn, e) {
                            this.fireEventsToAll("zoommodechange", this, !btn.pressed);
                        }.createDelegate(this)
                    },{
                        text: _t('Zoom Out'),
                        ref: '../zoomout',
                        enableToggle: true,
                        handler: function(btn, e) {
                            this.fireEventsToAll("zoommodechange", this, btn.pressed);
                        }.createDelegate(this)
                    },{
                        text: '&gt;',
                        width: 67,
                        handler: function(btn, e) {
                            this.onPanRight(this);
                        }.createDelegate(this)
                    }]
                }
            });
            Zenoss.SwoopyGraph.superclass.constructor.call(this, config);
            this.mustUseImageUri = Ext.isIE6 || Ext.isIE7;
        },
        initEvents: function() {
            this.addEvents("zoommodechange", "updateimage");
            Zenoss.SwoopyGraph.superclass.initEvents.call(this);
            this.on("zoommodechange", this.onZoomModeChange, this);
            this.on("updateimage", this.updateImage, this);
            this.graphEl = Ext.get(this.graphId);
            this.graphEl.on('click', this.onGraphClick, this);
            this.graphEl.on('load', function(){
                var size = this.graphEl.getSize();
                if (!size.width || !size.height){
                    this.showFailure();
                } else {
                    this.parseGraphParams();
                }
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
                Zenoss.SWOOP_CALLBACKS[graphid] = function(packet) {
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
                }.createDelegate(this);
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

    GraphRefreshButton = Ext.extend(Zenoss.RefreshMenuButton, {
        constructor: function(config) {
            config = config || {};
            var menu = {
                xtype: 'statefulrefreshmenu',
                id: config.stateId || 'graph_refresh',
                trigger: this,
                items: [{
                    xtype: 'menutextitem',
                    cls: 'refreshevery',
                    text: 'Refresh every'
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
            GraphRefreshButton.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('graphrefreshbutton', GraphRefreshButton);


    DRangeSelector = Ext.extend(Ext.form.ComboBox, {
        constructor: function(config) {
            config = config || {};
            Ext.apply(config, {
                fieldLabel: _t('Range'),
                    name: 'ranges',
                    editable: false,
                    forceSelection: true,
                    autoSelect: true,
                    triggerAction: 'all',
                    value: 129600,
                    mode: 'local',
                    store: new Ext.data.ArrayStore({
                        id: 0,
                        fields: [
                            'label',
                            'id'
                        ],
                        data: DATE_RANGES
                    }),
                    valueField: 'id',
                    displayField: 'label'
            });
            DRangeSelector.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('drangeselector', DRangeSelector);

    tbarConfig = [{
                    xtype: 'tbtext',
                    text: _t('Performance Graphs')

                }, '-', '->', {
                    xtype: 'tbtext',
                    text: _t('Range:')
                }, {
                    xtype: 'drangeselector',
                    ref: '../drange_select',
                    listeners: {
                        select: function(combo, record, index){
                            var value = record.data.id,
                                panel = combo.refOwner;
                            panel.drange = value;
                            panel.resetSwoopies();
                        }
                    }
                },'-', {
                    xtype: 'button',
                    ref: '../resetBtn',
                    text: _t('Reset'),
                    handler: function(btn) {
                        var panel = btn.refOwner;
                        panel.resetSwoopies();
                    }
                },'-',{
                    xtype: 'tbtext',
                    text: _t('Link Graphs?:')
                },{
                    xtype: 'checkbox',
                    ref: '../linkGraphs',
                    checked: true,
                    listeners: {
                        check: function(chkBx, checked) {
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

    GraphPanel = Ext.extend(Ext.Panel, {
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
            GraphPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            // remove all the graphs
            this.removeAll();

            var params = {
                uid: uid,
                drange: this.drange
            };
            this.uid = uid;
            this.directFn(params, this.loadGraphs.createDelegate(this));
        },
        loadGraphs: function(result){
            if (!result.success){
                return;
            }
            var data = result.data, panel = this;
            if (data.length > 0){
                Ext.each(data, function(graph){
                    var graphId = "graph_" + ++Ext.Component.AUTO_ID;
                    panel.add(new Zenoss.SwoopyGraph({
                        graphUrl: graph.url,
                        graphTitle: graph.title,
                        graphId: graphId,
                        isLinked: panel.isLinked,
                        ref: graphId
                    }));

                });
            }else{
                this.add({
                    xtype: 'panel',
                    html: _t('No Graph Data')
                });
            }

            panel.doLayout();
        },
        resetSwoopies: function(drange) {
            drange = drange || this.drange;
            Ext.each(this.getGraphs(), function(g) {
                g.fireEventsToAll("updateimage", {
                    drange: drange,
                    start: drange,
                    end: 0
                });
            });
        },
        getGraphs: function() {
            var graphs = [];
            Ext.each(this.items.items,
                     function(item){
                         if (item.graphUrl){
                             graphs.push(item);
                         }
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

    Ext.reg('graphpanel', GraphPanel);

}());