/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    Ext.ns('Zenoss');
    var router = Zenoss.remote.DeviceRouter;

    Ext.define("Zenoss.form.ComponentGraphPanel", {
        alias:['widget.componentgraphpanel'],
        extend:"Ext.Panel",
        compType: "",
        constructor: function(config) {
            config = config || {};

            // create the component drop down store
            var data = [], i, comps = config.components;
            for (i=0; i<comps.length;i++) {
                data.push([Zenoss.component.displayName(comps[i])[0],
                           comps[i]]);
            }

            Ext.applyIf(config, {
                style: {
                    paddingTop: 10
                },
                bodyStyle: {
                    overflow: 'auto'
                },
                dockedItems: [{
                    layout: 'hbox',
                    dock: 'top',
                    items: [{
                        xtype: 'combo',
                        queryMode: 'local',
                        displayField: 'name',
                        valueField:'value',
                        ref: '../component',
                        store: Ext.create('Ext.data.Store', {
                            model: 'Zenoss.model.NameValue',
                            data: data
                        }),
                        fieldLabel: _t('Component Type'),
                        listeners: {
                            scope: this,
                            select: this.onSelectComponentType
                        }
                    }, {
                        xtype: 'combo',
                        disabled: true,
                        queryMode: 'local',
                        ref: '../graphTypes',
                        fieldLabel: _t('Graphs'),
                        displayField: 'name',
                        valueField: 'name',
                        listeners: {
                            scope: this,
                            select: this.onSelectGraph
                        }
                    }, {
                        xtype: 'checkbox',
                        fieldLabel: _t('All on Same Graph?'),
                        labelWidth: 150,
                        ref: '../allOnSame',
                        listeners: {
                            change: this.updateGraphs,
                            scope: this
                        }
                    }]
                }]
            });
            Zenoss.form.ComponentGraphPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            this.uid = uid;
        },
        onSelectComponentType: function(combo, selected) {
            this.compType = selected[0].get('value');
            Zenoss.remote.DeviceRouter.getGraphDefintionsForComponent({
                uid: this.uid,
                meta_type: this.compType
            }, function(results){
                var store, i, data=[];
                for (i=0;i<results.data.length;i++) {
                    data.push([
                        results.data[i].id
                    ]);
                }

                store = Ext.create('Ext.data.Store', {
                    model: 'Zenoss.model.Name',
                    data: data
                });
                this.graphTypes.bindStore(store, true);
                if (!data.length) {
                    this.graphTypes.disable();
                } else {
                    this.graphTypes.enable();
                    this.graphTypes.select(data[0][0]);
                    // go ahead and show the graphs for the first
                    // selected option
                    this.onSelectGraph(this.graphTypes,
                                       [this.graphTypes.store.getAt(0)]
                                      );
                }
            }, this);
        },
        onSelectGraph: function(combo, selected) {
            // go to the server and return a list of graph configs
            // from which we can create EuropaGraphs from
            var graphId = selected[0].get('name');
            this.graphId = graphId;
            this.updateGraphs();

        },
        updateGraphs: function() {
            var meta_type = this.compType, uid = this.uid,
                graphId = this.graphId;
            Zenoss.remote.DeviceRouter.getComponentGraphs({
                uid: uid,
                meta_type: meta_type,
                graphId: graphId,
                allOnSame: this.allOnSame.checked
            }, function(response){
                if (response.success) {
                    var i, graphs=[], graph, graphTitle, id;
                    this.removeAll();
                    for(i=0;i<response.data.length;i++) {
                        graph = response.data[i];
                        graphTitle = graph.contextTitle;
                        delete graph.title;
                        id = Ext.id();
                        graphs.push(new Zenoss.EuropaGraph(Ext.applyIf(graph, {
                            uid: this.uid,
                            graphId: id,
                            graphTitle: graphTitle,
                            isLinked: false,
                            ref: id,
                            height: 500
                        })));
                    }
                    this.add(graphs);
                }
            }, this);

        }
    });



}());
