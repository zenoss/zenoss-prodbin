/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.onReady(function(){

    function buildGraph(data){
        var config = Ext.JSON.decode(Zenoss.util.base64.decode(data));
        config.isLinked = false;
        
        var graph = new Zenoss.EuropaGraph(Ext.applyIf(config, {
            graphId: Ext.id(),
            renderTo: 'graphView'
        }));
        document.title = graph.graphTitle;
    }

    var decodedUrl = Ext.urlDecode(location.search.substring(1, location.search.length)),
        data = decodedUrl.data;

    if (data){
        buildGraph(data);
    } else {
        Ext.DomHelper.append("graphView", {
            tag: 'h1',
            html: _t('Missing "data" query parameter, unable to render the graph.')
        });

    }
});