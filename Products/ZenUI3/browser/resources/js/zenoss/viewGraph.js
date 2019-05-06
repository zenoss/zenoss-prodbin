/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, 2019 all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.onReady(function(){

    function buildGraph(data, drange){
        var config = Ext.JSON.decode(data);

        if (Ext.isDefined(drange) && Ext.isNumeric(drange)) {
            config.graph_params = {
                drange: parseInt(drange),
                end: new Date().getTime(),
                start: new Date().getTime() - parseInt(drange)
            };
        }

        var graph = new Zenoss.EuropaGraph(Ext.applyIf(config, {
            graphId: Ext.id(),
            renderTo: 'graphView',
            hasMenu: false,
        }));
        document.title = graph.graphTitle;

        // check if this graph is inside iframe
        // which is inside the Site Window Portlet
        var iframe = checkSiteWindowPortlet();
        if (iframe !== null) {
            var header = iframe.contentDocument.getElementById('header');
            if (header !== null) {
                header.style.display = 'none';
            }
        }
    }

    function checkSiteWindowPortlet() {
        var iframes = parent.document.getElementsByTagName('iframe');
        var thisIFrame;
        if (iframes.length > 0) {
            for (var i=0; i<iframes.length; i++) {
                var currentIFrame = iframes[i];
                if (currentIFrame.contentDocument === document) {
                    thisIFrame = currentIFrame;
                    break;
                }
            }
            var prnt = thisIFrame.parentElement;
            while(prnt) {
                if (prnt.id.search('sitewindowportlet') > -1) {
                    return thisIFrame;
                }
                prnt = prnt.parentElement;
            }
        }
        return null;
    }

    var decodedUrl = Ext.urlDecode(location.search.substring(1, location.search.length)),
        drange = decodedUrl.drange,
        data = decodedUrl.data,
        saved = 'saved' in decodedUrl;

    if (data) {
        if (saved) {
            Zenoss.remote.DeviceRouter.getGraphConfig({string: data}, function(resp) {
                if (resp.success && resp.data && resp.data.data) {
                    buildGraph(resp.data.data, drange);
                } else {
                    Zenoss.message.error("This graph link expired or never existed");
                }
            });
        } else {
            Zenoss.remote.DeviceRouter.gunzip_b64({string: data}, function(resp) {
                if (resp.success && resp.data && resp.data.data) {
                    buildGraph(resp.data.data, drange);
                }
            });
        }
    } else {
        Ext.DomHelper.append("graphView", {
            tag: 'h1',
            html: _t('Missing "data" query parameter, unable to render the graph.')
        });
    }
});
