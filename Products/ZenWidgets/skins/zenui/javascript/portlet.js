// Set up the namespace
YAHOO.namespace('zenoss.portlet');

var isIE//@cc_on=1;

var DDM = YAHOO.util.DragDropMgr;

var Portlet = Class.create();
var PortletContainer = Class.create();
var PortletColumn = Class.create();
var XHRDatasource = Class.create();
var StaticDatasource = Class.create();
var IFrameDatasource = Class.create();
var GoogleMapsDatasource = Class.create();
var TableDatasource = Class.create();

var pc_layouts = {
    '1col':   [1, 'yui-b' ],
    '2coleq': [2, 'yui-g' ],
    '2colbs': [2, 'yui-gc'],
    '2colsb': [2, 'yui-gd'],
    '3col':   [3, 'yui-gb']
};

function getUID(base) {
    return base + new Date().getTime();
}

PortletColumn.prototype = {
    __init__: function(domel, container) {
        this.domel = domel;
        this.container = container;
        new YAHOO.util.DDTarget(this.domel, 'PortletProxy');
        setStyle(this.domel, {'height':'400px'});
    },
    addPortlet: function(portlet, toTop) {
        this.container.portlets[portlet.id] = portlet;
        portlet.PortletContainer = this.container;
        if (toTop) {
            ports = this.getPortlets();
            if (ports.length) {
                first = this.getPortlets()[0];
                insertSiblingNodesBefore(first.container, portlet.render());
            } else {
                appendChildNodes(this.domel, portlet.render());
            }
        } else {
            appendChildNodes(this.domel, portlet.render());
        }
        if (!isIE) new YAHOO.zenoss.DDResize(portlet);
        j = new YAHOO.zenoss.portlet.PortletProxy(portlet.id, this.container);
        j.addInvalidHandleId(portlet.resizehandle.id);
        j.addInvalidHandleClass('nodrag');
        this.container.setContainerHeight();
        if (isIE) new YAHOO.zenoss.DDResize(portlet);
    },
    getPortlets: function() {
        els = getElementsByTagAndClassName('div', 'zenoss-portlet', this.domel);
        var portlets = [];
        for (var i=0;i<els.length;i++) {
            var id = els[i].id;
            var portlet = this.container.portlets[id];
            portlets.push(portlet);
        }
        return portlets;
    },
    serialize: function() {
        var portlets = this.getPortlets();
        return map(function(x){return x.serialize()}, portlets);
    }
}

Portlet.prototype = {
    __class__: "YAHOO.zenoss.portlet.Portlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id:"";
        datasource = 'datasource' in args? args.datasource:{};
        title = 'title' in args? args.title:"My Portlet";
        bodyHeight = 'bodyHeight' in args? args.bodyHeight:200;
        refreshTime = 'refreshTime' in args? args.refreshTime:0;
        if (!bodyHeight) bodyHeight = 50;
        this.bodyHeight = bodyHeight;
        this.refreshTime = refreshTime;
        this.PortletContainer = null;
        this.id = id;
        this.handleid = id+'_handle';
        this.isDirty = true;
        this.title = title;
        this.render();
        this.setTitleText(title);
        this.setDatasource(datasource);
        this.calllater = null;
        this.startRefresh(true);
    },
    setDatasource: function(datasource) {
        if (datasource) {
            this.datasource = datasource;
            if (datasource.__class__=='YAHOO.zenoss.portlet.TableDatasource') {
                this.datasource.get(this.fillTable);
            } else {
                this.datasource.get(this.fill);
            }
        }
    },
    setTitleText: function(text) {
        if (this.titlecont) {
            if (!text) text = "My Portlet";
            this.titlecont.innerHTML = text;
            this.title = text;
        }
    },
    fill: function(contents) {
        if (this.body) {
            if (contents.responseText) {
                contents = contents.responseText;
            }
            this.body.innerHTML = contents;
        }
    },
    fillTable: function(contents) {
        var columnDefs = contents.columnDefs;
        var dataSource = contents.dataSource;
        var oConfigs = {};
        addElementClass(this.body, 'yui-skin-sam');
        var myDataTable = new YAHOO.widget.DataTable(
            this.body.id, columnDefs, dataSource, oConfigs);
        currentWindow().dataTable = myDataTable;
    },
    toggleSettings: function(state) {
        var show = method(this, function() {
            this.body.style.marginTop = '-1px';
            showElement(this.settingsPane);
            this.PortletContainer.setContainerHeight();
        });
        var hide = method(this, function() {
            hideElement(this.settingsPane);
            this.body.style.marginTop = '0';
            this.PortletContainer.setContainerHeight();
        });
        if (state=='hide') hide();
        else if (state=='show') show();
        else if (this.settingsPane.style.display=='none') show();
        else if (this.settingsPane.style.display=='block') hide();
    },
    saveSettings: function(settings) {
        this.refreshTime = settings['refreshTime'];
        this.title = settings['title'];
        this.setTitleText(this.title);
        for (setting in settings) {
            this.datasource[setting] = settings[setting];
        }
        this.setDatasource(this.datasource);
        this.PortletContainer.isDirty = true;
        this.PortletContainer.save();
        this.startRefresh(true);
    },
    submitSettings: function(e, settings) {
        settings = settings || {};
        settings['refreshTime'] = this.refreshRateInput.value || 0;
        settings['title'] = this.titleInput.value;
        this.saveSettings(settings);
        this.toggleSettings('hide');
    },
    destroy: function() {
        removeElement(this.container);
        delete this.PortletContainer.portlets[this.id];
        this.PortletContainer.isDirty = true;
        this.PortletContainer.save();
    },
    render: function() {
        if (this.isDirty) {
            this.body = DIV({'class':'portlet-body','id':this.id+'_body'},
                            "Portlet Content");
            this.resizehandle = DIV(
                {'class':'resize-handle','id':this.id+'_resizer'}, null);
            this.titlecont = SPAN({'class':'nodrag'}, null);
            this.settingsToggle = DIV({'style':'position:absolute;'+
                                       'right:0;top:0;cursor:pointer'},'*');
            connect(this.settingsToggle, 'onclick', this.toggleSettings);
            this.refreshRateInput = INPUT({'value':this.refreshTime}, null);
            this.titleInput = INPUT({'value':this.title}, null);
            this.settingsSlot = DIV({'id':this.id+'_customsettings', 
                'class':'settings-controls'}, 
               [
                DIV({'class':'portlet-settings-control'}, [
                DIV({'class':'control-label'}, 'Title'),
                 this.titleInput
               ]),
               DIV({'class':'portlet-settings-control'}, [
                DIV({'class':'control-label'}, 'Refresh Rate'),
                 this.refreshRateInput
               ])]);
            this.destroybutton = A(
                {'class':'portlet-settings-control'}, 'Remove Portlet');
            this.savesettingsbutton = BUTTON(
                {'class':'portlet-settings-control'}, 'Save Settings');
            connect(this.savesettingsbutton, 'onclick', this.submitSettings);
            connect(this.destroybutton, 'onclick', this.destroy);
            this.buttonsSlot = DIV({'id':this.id+'_buttonslot', 
                'class':'settings-controls buttonslot'}, 
                    [this.destroybutton, this.savesettingsbutton]);
            this.settingsPane = DIV({'id':this.id+'_settings',
                'class':'portlet-settings'}, 
                [DIV({'class':'settings-controls'}, 
                    [this.settingsSlot, this.buttonsSlot]), 
                    DIV({'style':'clear:both'}, '')]);
            this.container = DIV({'class':'zenoss-portlet','id':this.id},
               DIV({'class':'zenportlet'},
                [
                 DIV({'class':'portlet-header'},
                  DIV({'class':'tabletitle-container','id':this.handleid},
                   DIV({'class':'tabletitle-left'},
                    DIV({'class':'tabletitle-right'},
                     DIV({'class':'tabletitle-center'},
                     [this.titlecont,this.settingsToggle]
                 ))))),
                DIV(null, this.settingsPane),
                DIV({'class':'portlet-body-outer'},
                    [this.body,this.resizehandle])
                ]));
            /*
            this.container = DIV({'class':'zenoss-portlet','id':this.id},
               TABLE({'class':'zenportlet'},
                [TR(null,
                 TD({'class':'portlet-header'},
                  DIV({'class':'tabletitle-container','id':this.handleid},
                   DIV({'class':'tabletitle-left'},
                    DIV({'class':'tabletitle-right'},
                     DIV({'class':'tabletitle-center'},
                     [this.titlecont,this.settingsToggle]
                 )))))),
                TBODY({}, TR(null, TD(null, this.settingsPane))),
                TR(null, TD({'class':'portlet-body'},
                    [this.body,this.resizehandle]))
                ]));
            */
            this.isDirty = false;
            setStyle(this.body, {'height':this.bodyHeight+'px'});
            hideElement(this.settingsPane);
            //this.body.style.marginTop = '-4px';
        }
        return this.container;
    },
    serialize: function() {
        portobj = {
            id: this.id,
            title: this.title,
            datasource: this.datasource,
            bodyHeight: this.bodyHeight,
            refreshTime: this.refreshTime,
            __class__: this.__class__
        };
        return portobj;
    },
    startRefresh: function(firsttime) {
        this.stopRefresh();
        if (!firsttime) this.setDatasource(this.datasource);
        if (this.refreshTime>0)
            this.calllater = callLater(this.refreshTime, this.startRefresh);
    },
    stopRefresh: function() {
        if (this.calllater) {
            this.calllater.cancel();
            this.calllater = null;
        }
    }
}

PortletContainer.prototype = {
    __init__: function(target) {
        this.container = $(target);
        this.columns = [];
        this.portlets = {};
        this.columnContainer = null;
        this.isDirty = false;
    },
    setContainerHeight: function() {
        var heights = [];
        for (var i=0;i<this.columns.length;i++) {
            col = this.columns[i];
            ports = col.getPortlets();
            lastp = ports[ports.length-1]
            if (lastp) {
                cont = lastp.container;
                p = getElementPosition(cont).y;
                h = getElementDimensions(cont).h;
                heights.push(p+h);
            }
        }
        highest = listMax(heights);
        newHeight = highest - 80;
        if (newHeight!=getElementDimensions(this.container).h) {
            setStyle(this.container, {'height':newHeight + 'px'});
            map(function(x){setStyle(x.domel, {'height':newHeight+'px'})},
                this.columns);
        }
    },
    getColumnsAsDisplayed: function() {
        // Due to the CSS, columns are displayed out of order in 
        // the 33-33-33 format.
        if (this.numCols()==3) {
            return [this.columns[0], this.columns[2], this.columns[1]];
        } else {
            return this.columns;
        }
    },
    columnElements: function() {
        return map(function(x){return x.domel}, this.columns);
    },
    numCols: function() { 
        return this.columns.length;
    },
    leftCol: function() {
        return this.columns[0];
    },
    middleCol: function() {
        if (this.numCols()==3) {
            return this.columns[2];
        } else {
            return this.rightCol();
        }
    },
    rightCol: function() { 
        return this.columns[this.numCols()>1?1:0]; 
    },
    addPortlet: function(klass, args) {
        var portlet = new klass(args);
        this.rightCol().addPortlet(portlet, true);
        this.isDirty = true;
        this.save();
    },
    fillColumns: function(oldcols) {
        // Passed in an array of arrays of portlets,
        // distribute among current columns.
        // This works because this.middleCol on 2-column
        // layouts returns this.rightCol
        var fillfuncs = [this.leftCol, this.middleCol, this.rightCol];
        for (i=0;i<oldcols.length;i++) {
            var col = fillfuncs[i]();
            var oldcol = oldcols[i];
            for (k=0;k<oldcol.length;k++) {
                col.addPortlet(oldcol[k]);
            }
        }
    },
    getColumnState: function() {
        var curcols = this.getColumnsAsDisplayed();
        var curstate = map(function(x){return x.getPortlets()}, curcols);
        return curstate;
    },
    showLayoutDialog: function() {
        if (!this.configDialog) {
            configDialog = new YAHOO.widget.SimpleDialog("configureDialog",
                { width: "188px",
                  fixedcenter: true,
                  modal: false,
                  visible: false,
                  draggable:true });
            configDialog.setHeader("Column Layout");
            this.configDialog = configDialog;
            var threecol = bind(function(){this.setLayout('3col', true)},this);
            var onecol   = bind(function(){this.setLayout('1col', true)},this);
            var twocoleq = bind(function(){this.setLayout('2coleq', true)},this);
            var twocolsb = bind(function(){this.setLayout('2colsb', true)},this);
            var twocolbs = bind(function(){this.setLayout('2colbs', true)},this);
            var hidedialog = bind(function(){
                //this.configDialog.hide();
                this.configDialog.destroy();
                this.configDialog = null;
            }, this);
            var getImage = function(type) {
                el = DIV({'class':'column-layout-button',
                          'style':'background-image:url(img/icons/'+type+'.png)'
                         }, null);
                var imagehtml = toHTML(el);
                if (isIE) {
                    imagehtml = imagehtml.replace(
                        'align', 
                        'style="background-image:url(img/icons/'+type+
                            '.png)" align');
                }
                return imagehtml;
            }
            var mybuttons = [ { text:getImage("1col"),handler:onecol},  
                              { text:getImage("2coleq"),handler:twocoleq},  
                              { text:getImage("2colsb"),handler:twocolsb},  
                              { text:getImage("2colbs"),handler:twocolbs},
                              { text:getImage("3col"),handler:threecol}
                            ];
            configDialog.cfg.queueProperty("buttons", mybuttons);
            addElementClass(this.container, 'yui-skin-sam');
            configDialog.render(this.container);
        }
        this.configDialog.show();
    },
    setLayout: function(layout, makeDirty) {
        if (makeDirty) this.isDirty = true;
        layinfo = pc_layouts[layout];
        colsnum = layinfo[0];
        colsclass = layinfo[1];
        var curstate = this.getColumnState();
        this.columns = [];
        for (var i=0; i<colsnum; i++) {
            var unique = new Date().getTime();
            var unitclass = 'yui-u';
            if (i==0) unitclass += ' first';
            var col = new PortletColumn(DIV({'class':unitclass}, null), this);
            this.columns.push(col);
        }
        this.dialogLink = A({'class':"tinylink"}, "Configure layout...");
        this.portDialogLink = A({'class':"tinylink"}, "Add portlet...");
        this.doRefresh = A({'class':"tinylink"}, "Stop Refresh");
        connect(this.dialogLink, "onclick", this.showLayoutDialog);
        connect(this.portDialogLink, "onclick", this.showAddPortletDialog);
        connect(this.doRefresh, "onclick", this.stopRefresh);
        var newContainer = DIV({'class':colsclass}, 
            [DIV({'class':'tinylink-container'}, 
                [this.doRefresh, this.portDialogLink, this.dialogLink]), 
             this.columnElements()]);
        if (!this.columnContainer) {
            this.columnContainer = newContainer;
            appendChildNodes(this.container, newContainer);
        } else {
            this.columnContainer = swapDOM(
                this.columnContainer, newContainer);
        }
        this.layout = layout;
        if (curstate) this.fillColumns(curstate);
        this.save();
    },
    serialize: function() {
        var cols = this.getColumnState();
        var columns = map(
                function(x){
                    return map(function(y){return y.serialize()}, x)
                },
                cols
        );
        var settingsObject = {
            layout: this.layout,
            columns: columns
        };
        var json = serializeJSON(settingsObject);
        return json;
    },
    save: function() {
        if (this.isDirty) {
            var setUrl='/zport/dmd/ZenUsers/setDashboardState';
            doXHR(setUrl, {
                method: 'POST',
                sendContent: this.serialize()
            });
            this.isDirty = false;
        }
    },
    restore: function(state) {
        this.isDirty = false;
        var layout = state.layout;
        var columns = state.columns;
        var newcolumns = [];
        this.setLayout(layout);
        forEach (columns, function(portlets) {
            var thiscolumn = [];
            forEach (portlets, function(portsettings) {
                var dssettings = portsettings.datasource;
                var dsklass = eval(dssettings.__class__);
                var datasource = new dsklass(dssettings);
                portsettings.datasource = datasource;
                var portklass = eval(portsettings.__class__);
                var p = new portklass(portsettings);
                thiscolumn.push(p);
            });
            newcolumns.push(thiscolumn);
        });
        this.fillColumns(newcolumns);
    },
    startRefresh: function() {
        for (portlet in this.portlets) {
            p = this.portlets[portlet];
            p.startRefresh(true);
        }
        this.doRefresh.innerHTML = "Stop Refresh";
        disconnectAll(this.doRefresh, 'onclick');
        connect(this.doRefresh, 'onclick', this.stopRefresh);
    },
    stopRefresh: function() {
        for (portlet in this.portlets) {
            p = this.portlets[portlet];
            p.stopRefresh();
        }
        this.doRefresh.innerHTML = "Start Refresh";
        disconnectAll(this.doRefresh, 'onclick');
        connect(this.doRefresh, 'onclick', this.startRefresh);
    },
    showAddPortletDialog: function() {
        if (!this.addPortletDialog) {
            addPortletDialog = new YAHOO.widget.SimpleDialog("addPortletDialog",
                { width: "176px",
                  fixedcenter: true,
                  modal: false,
                  visible: false,
                  draggable:true });
            addPortletDialog.setHeader("Add Portlet");
            var hidedialog = bind(function(){
                //this.configDialog.hide();
                this.addPortletDialog.destroy();
                this.addPortletDialog = null;
            }, this);
            var addHeartbeats= method(this, function() {
                this.addPortlet(YAHOO.zenoss.portlet.HeartbeatsPortlet);
                hidedialog();
            });
            var addWatchList= method(this, function() {
                this.addPortlet(YAHOO.zenoss.portlet.WatchListPortlet);
                hidedialog();
            });
            var addDeviceIssues= method(this, function() {
                this.addPortlet(YAHOO.zenoss.portlet.DeviceIssuesPortlet);
                hidedialog();
            });
            var addGoogleMaps= method(this, function() {
                this.addPortlet(YAHOO.zenoss.portlet.GoogleMapsPortlet);
                hidedialog();
            });
            var addTopLevelOrgs= method(this, function() {
                this.addPortlet(YAHOO.zenoss.portlet.TopLevelOrgsPortlet);
                hidedialog();
            });
            var mybuttons = [ { text:"Device Issues",handler:addDeviceIssues},  
                              { text:"Top Level Organizers",
                                     handler:addTopLevelOrgs},  
                              { text:"Watch List",handler:addWatchList},  
                              { text:"Google Maps",handler:addGoogleMaps},  
                              { text:"Zenoss Issues",handler:addHeartbeats}
                            ];
            addPortletDialog.cfg.queueProperty("buttons", mybuttons);
            addElementClass(this.container, 'yui-skin-sam');
            addPortletDialog.render(this.container);
            this.addPortletDialog = addPortletDialog;
        }
        this.addPortletDialog.show();
    }
}

StaticDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.StaticDatasource",
    __init__: function(settings) {
        this.settings = settings;
        this.html = settings.html;
    },
    get: function(callback) {
        this.callback = callback;
        r = {responseText:this.html};
        callback(r);
    }
}

XHRDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.XHRDatasource",
    __init__: function(settings) {
        this.url = settings.url;        
    },
    get: function(callback) {
        this.callback = callback;
        var d = doXHR(this.url);
        d.addCallback(callback);
        return d;
    }
}

IFrameDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.IFrameDatasource",
    __init__: function(settings) {
        this.url = settings.url;
    },
    get: function(callback) {
        this.callback = callback;
        html = '<iframe src="' + this.url + '" ' +
               'style="border:medium none;margin:0;padding:0;'+
               'width:100%;height:100%;"/>';
        callback({responseText:html});
    }
}

TableDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.TableDatasource",
    __init__: function(settings) {
        this.url = settings.url;
        this.queryArguments = 'queryArguments' in settings? 
            settings.queryArguments:{};
        this.postContent = 'postContent' in settings?
            settings.postContent:'';
        this.method = 'method' in settings? settings.method:'POST';
    },
    get: function(callback) {
        var d = doXHR(this.url, {
            method: this.method,
            queryString: this.queryArguments,
            sendContent: serializeJSON(this.postContent)
        });
        d.addCallback(bind(function(r){
            this.parseResponse(r, callback)},this));
    },
    parseResponse: function(response, callback) {
        response = evalJSONRequest(response);
        var columns = response.columns;
        var mycolumndefs = map(function(x){
            return {key:x,sortable:true,resizeable:true}}, columns);
        var data = response.data;
        var myDataSource = new YAHOO.util.DataSource(data);
        myDataSource.responseType = YAHOO.util.DataSource.TYPE_JSARRAY;
        myDataSource.responseSchema = {fields:columns};
        callback({columnDefs:mycolumndefs,dataSource:myDataSource});
    }
}

GoogleMapsDatasource.prototype = {
    __class__ : "YAHOO.zenoss.portlet.GoogleMapsDatasource",
    __init__: function(settings) {
        this.baseLoc = settings.baseLoc;
    },
    get: function(callback) {
        this.callback = callback;
        var url = '/zport/dmd' + this.baseLoc + 
                  '/simpleLocationGeoMap';
        html = '<iframe src="' + url + '" ' +
               'style="border:medium none;margin:0;padding:0;'+
               'width:100%;height:100%;"/>';
        callback({responseText:html});
    }
}

// Portlet drag stuffz
YAHOO.zenoss.portlet.PortletProxy = function(id, container) {
    sGroup = 'PortletProxy';
    config = null;
    YAHOO.zenoss.portlet.PortletProxy.superclass.constructor.call(
        this, id, sGroup, config);
    var el = this.getDragEl();
    YAHOO.util.Dom.setStyle(el, "opacity", 0.67);
    YAHOO.util.Dom.setStyle(el, "z-index", 10000);
    this.container = container;
    this.goingUp = false;
    this.lastY = 0;
    this.setHandleElId(id+'_handle');
    this.addInvalidHandleClass('nodrag');
}

YAHOO.extend(YAHOO.zenoss.portlet.PortletProxy, YAHOO.util.DDProxy, {

    startDrag: function(x, y) {
        var dragEl = this.getDragEl();
        var clickEl = this.getEl();
        setStyle(clickEl, {'visibility':'hidden'});
        nodes = clickEl.childNodes;
        dragEl.innerHTML = clickEl.innerHTML;
    },
    endDrag: function(e) {
        var srcEl = this.getEl();
        var proxy = this.getDragEl();
        setStyle(proxy, {"visibility":""});
        var a = new YAHOO.util.Motion(
            proxy, {
                points: {
                    to: YAHOO.util.Dom.getXY(srcEl)
                }
            },
            0.2,
            YAHOO.util.Easing.easeOut
        )
        var proxyid = proxy.id;
        var thisid = this.id;
        a.onComplete.subscribe(function() {
            YAHOO.util.Dom.setStyle(proxyid, "visibility", "hidden");
            YAHOO.util.Dom.setStyle(thisid, "visibility", "");
        });
        a.animate();
    },
    onDragDrop: function(e, id) {
        if (DDM.interactionInfo.drop.length === 1) {
            var pt = DDM.interactionInfo.point;
            var region = DDM.interactionInfo.sourceRegion;
            if (!region.intersect(pt)) {
                var destEl = $(id);
                var destDD = DDM.getDDById(id);
                destEl.appendChild(this.getEl());
                destDD.isEmpty = false;
                this.container.isDirty = true;
                DDM.refreshCache();
            }
        }
        this.container.setContainerHeight();
        this.container.save();
        if (this.container.doRefresh.innerHTML=='Stop Refresh')
            this.container.startRefresh();
    },
    onDrag: function(e) {
        var y = YAHOO.util.Event.getPageY(e);
        if (y<this.lastY) {
            this.goingUp = true;
        } else if (y > this.lastY) {
            this.goingUp = false;
        }
        this.lastY = y;
    },
    onDragOver: function(e, id) {
        var srcEl = this.getEl();
        var destEl = $(id);
        if (destEl.className.toLowerCase() == 'zenoss-portlet') {
            var orig_p = srcEl.parentNode;
            var p = destEl.parentNode;
            if (this.goingUp) {
                p.insertBefore(srcEl, destEl);
            } else {
                p.insertBefore(srcEl, destEl.nextSibling);
            }
            DDM.refreshCache();
            this.container.setContainerHeight();
            this.container.isDirty = true;
        }
    }
});

YAHOO.zenoss.DDResize = function(portlet) {
    sGroup = "PortletResize";
    config = null;
    panelElId = portlet.id;
    this.portlet = portlet;
    YAHOO.zenoss.DDResize.superclass.constructor.call(
        this, panelElId, sGroup, config);
    this.setHandleElId(portlet.resizehandle.id);
    this.addInvalidHandleId(portlet.handleid);
    this.addInvalidHandleId(portlet.body.id);
    this.addInvalidHandleId(portlet.handleid);
    this.addInvalidHandleId(portlet.container.id);
    this.addInvalidHandleId(portlet.titlecont.id);
};
YAHOO.extend(YAHOO.zenoss.DDResize, YAHOO.util.DragDrop, {
    onMouseDown: function(e) {
        var panel = this.portlet.body; 
        this.startWidth = panel.offsetWidth;
        this.startHeight = panel.offsetHeight;

        this.startPos = [YAHOO.util.Event.getPageX(e),
                         YAHOO.util.Event.getPageY(e)];
    },
    onDrag: function(e) {
        var newPos = [YAHOO.util.Event.getPageX(e),
                      YAHOO.util.Event.getPageY(e)];

        var offsetY = newPos[1] - this.startPos[1];
        var newHeight = Math.max(this.startHeight + offsetY, 10);
        var panel = this.portlet.body;
        panel.style.height = newHeight + "px";
        this.portlet.bodyHeight = newHeight;
        this.portlet.PortletContainer.setContainerHeight();
        this.portlet.PortletContainer.isDirty = true;
    },

    onMouseUp: function(e) {
        this.portlet.PortletContainer.save();
    }

});


YAHOO.zenoss.portlet.PortletContainer = PortletContainer;
YAHOO.zenoss.portlet.XHRDatasource = XHRDatasource;
YAHOO.zenoss.portlet.StaticDatasource = StaticDatasource;
YAHOO.zenoss.portlet.IFrameDatasource = IFrameDatasource;
YAHOO.zenoss.portlet.GoogleMapsDatasource = GoogleMapsDatasource;
YAHOO.zenoss.portlet.TableDatasource = TableDatasource;
YAHOO.zenoss.portlet.Portlet = Portlet;

var GoogleMapsPortlet = YAHOO.zenoss.Subclass.create(
    YAHOO.zenoss.portlet.Portlet);
GoogleMapsPortlet.prototype = {
    __class__: "YAHOO.zenoss.portlet.GoogleMapsPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('googlemaps');
        baseLoc = 'baseLoc' in args? args.baseLoc : '/Locations';
        bodyHeight = 'bodyHeight' in args? args.bodyHeight : 400;
        title = 'title' in args? args.title: "Locations";
        refreshTime = 'refreshTime' in args? args.refreshTime : 0;
        this.mapobject = null;
        var datasource = 'datasource' in args? 
            args.datasource:
            new YAHOO.zenoss.portlet.GoogleMapsDatasource(
                {'baseLoc':baseLoc?baseLoc:'/Locations'});
        this.superclass.__init__(
            {id:id, title:title, refreshTime:refreshTime,
            datasource:datasource, bodyHeight:bodyHeight}
        );
        this.buildSettingsPane();
        this.resizehandle.style.height="10px";
    },
    buildSettingsPane: function() {
        s = this.settingsSlot;
        this.locsearch = YAHOO.zenoss.zenautocomplete.LocationSearch(
            'Base Location', s);
        addElementClass(this.locsearch.container, 
                        'portlet-settings-control');
    },
    submitSettings: function(e, settings) {
        baseLoc = this.locsearch.input.value;
        if (baseLoc.length<1) baseLoc = this.datasource.baseLoc;
        this.locsearch.input.value = '';
        this.superclass.submitSettings(e, {'baseLoc':baseLoc});
    },
    startRefresh: function(firsttime) {
        if (!firsttime) this.mapobject.refresh();
        if (this.refreshTime>0)
            this.calllater = callLater(this.refreshTime, this.startRefresh);
    }
}
YAHOO.zenoss.portlet.GoogleMapsPortlet = GoogleMapsPortlet;

var DeviceIssuesPortlet = Subclass.create(YAHOO.zenoss.portlet.Portlet);
DeviceIssuesPortlet.prototype = {
    __class__:"YAHOO.zenoss.portlet.DeviceIssuesPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('devissues');
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource(
            {'url':'/zport/dmd/ZenEventManager/getDeviceIssuesJSON'});
        bodyHeight = 'bodyHeight' in args? args.bodyHeight :
            200;
        title = 'title' in args? args.title:"Device Issues";
        refreshTime = 'refreshTime' in args? args.refreshTime : 0;
        this.superclass.__init__(
            {id:id, title:title, 
             datasource:datasource, 
             refreshTime: refreshTime,
             bodyHeight:bodyHeight}
        );
    }
}
YAHOO.zenoss.portlet.DeviceIssuesPortlet = DeviceIssuesPortlet;

var HeartbeatsPortlet = Subclass.create(YAHOO.zenoss.portlet.Portlet);
HeartbeatsPortlet.prototype = {
    __class__: "YAHOO.zenoss.portlet.HeartbeatsPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('heartbeats');
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource(
            {'url':'/zport/dmd/ZenEventManager/getHeartbeatIssuesJSON'});
        bodyHeight = 'bodyHeight' in args? args.bodyHeight :
            200;
        title = 'title' in args? args.title:"Zenoss Issues";
        refreshTime = 'refreshTime' in args? args.refreshTime : 0;
        this.superclass.__init__(
            {id:id, 
             title:title,
             datasource:datasource,
             bodyHeight: bodyHeight,
             refreshTime: refreshTime
            }
        );
    }
}
YAHOO.zenoss.portlet.HeartbeatsPortlet = HeartbeatsPortlet;

var WatchListPortlet = YAHOO.zenoss.Subclass.create(YAHOO.zenoss.portlet.Portlet);
WatchListPortlet.prototype = {
    __class__:"YAHOO.zenoss.portlet.WatchListPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('watchlist');
        title = 'title' in args? args.title: "Object Watch List",
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource({
                url:'/zport/dmd/ZenEventManager/getEntityListEventSummary',
                postContent: ['/Devices/Discovered']});
        bodyHeight = 'bodyHeight' in args? args.bodyHeight:200;
        refreshTime = 'refreshTime' in args? args.refreshTime: 0;
        this.superclass.__init__(
            {id:id, 
             title:title,
             datasource:datasource,
             refreshTime: refreshTime,
             bodyHeight: bodyHeight
            }
        );
        this.buildSettingsPane();
    },
    buildSettingsPane: function() {
        s = this.settingsSlot;
        this.locsearch = new YAHOO.zenoss.zenautocomplete.DevObjectSearch(
            'Zenoss Objects', s);
        addElementClass(this.locsearch.container, 'portlet-settings-control');
    },
    submitSettings: function(e, settings) {
        var postContent = settings?settings.postContent:
                          this.datasource.postContent;
        var newob = this.locsearch.input.value;
        if (findValue(postContent, newob)<0) {
            if (newob.length>0) postContent.push(newob);
            this.superclass.submitSettings(e, {'postContent':postContent});
        }
        this.locsearch.input.value = '';
    },
    fillTable: function(contents) {
        var columnDefs = contents.columnDefs;
        var dataSource = contents.dataSource;
        i=0;
        forEach(dataSource.liveData, bind(function(x){
            //log(this.id+"_row_"+i);
            var removelink = "<a id='"+this.id+"_row_"+i+
                         "' class='removerowlink'"+
                         " title='Stop watching this object'>" +
                         "X</a>";
            x['Object'] = removelink + x['Object'];
            i++;
        }, this));
        var oConfigs = {};
        addElementClass(this.body, 'yui-skin-sam');
        var myDataTable = new YAHOO.widget.DataTable(
            this.body.id, columnDefs, dataSource, oConfigs);
        this.dataTable = myDataTable;
        forEach(this.dataTable.getRecordSet().getRecords(), bind(function(x){
            var row = this.dataTable.getTrEl(x);
            var link = getElementsByTagAndClassName('a','removerowlink',row)[0];
            connect(link, "onclick", method(this, 
                function(){this.deleteRow(x);}));
        }, this));
    },
    deleteRow: function(record) {
        var data = record.getData()['Object'];
        var name = regex = data.match(/<\/div>(.*?)<\/a>/)[1];
        myarray = this.datasource.postContent;
        myarray.splice(findValue(myarray, name), 1);
        this.submitSettings(null, {'postContent':myarray});
    }
}
YAHOO.zenoss.portlet.WatchListPortlet = WatchListPortlet;

var TopLevelOrgsPortlet = YAHOO.zenoss.Subclass.create(
    YAHOO.zenoss.portlet.Portlet);
TopLevelOrgsPortlet.prototype = {
    __class__:"YAHOO.zenoss.portlet.TopLevelOrgsPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('toplevelorgs');
        title = 'title' in args? args.title: "Root Organizers",
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource({
                method:'GET',
                url:'/zport/getRootOrganizerInfo',
                queryArguments: {'dataRoot':'Devices'} });
        bodyHeight = 'bodyHeight' in args? args.bodyHeight:200;
        refreshTime = 'refreshTime' in args? args.refreshTime: 0;
        rootOrganizer = 'rootOrganizer' in args?args.rootOrganizer:'Devices';
        this.superclass.__init__(
            {id:id, 
             title:title,
             datasource:datasource,
             refreshTime: refreshTime,
             bodyHeight: bodyHeight
            }
        );
        this.buildSettingsPane();
    },
    buildSettingsPane: function() {
        s = this.settingsSlot;
        orgs = ["Devices", "Locations", "Systems", "Groups"];
        getopt = function(x) { return OPTION({'value':x}, x); }
        options = map(getopt, orgs);
        this.orgselect = new SELECT(null,options);
        mycontrol = DIV({'class':'portlet-settings-control'}, [
                DIV({'class':'control-label'}, 'Root Organizer'),
                 this.orgselect
               ]);
        appendChildNodes(s, mycontrol);
    },
    submitSettings: function(e, settings) {
        var newroot = this.orgselect.value;
        this.datasource.dataRoot = newroot;
        this.superclass.submitSettings(e, {'queryArguments':
            {'dataRoot':newroot}
        });
    }
}
YAHOO.zenoss.portlet.TopLevelOrgsPortlet = TopLevelOrgsPortlet;

// Tell the loader we're all done!
YAHOO.register("portlet", YAHOO.zenoss.portlet, {});
