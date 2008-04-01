var Class = YAHOO.zenoss.Class;

var GLOB_MARKERDATA = [];

function ZenossLocationCache() {
    GGeocodeCache.apply(this);
}

ZenossLocationCache.prototype = new GGeocodeCache();
ZenossLocationCache.prototype.reset = function() {
    GGeocodeCache.prototype.reset.call(this);
    if (geocodecache) {
      for (key in geocodecache)
          var mycache = geocodecache[key];
    } else {
      var mycache = [];
    }
    forEach(keys(mycache), method(this, function(x) {
        this.put(mycache[x].name, mycache[x]);
    }));
}

var ZenGeoMap = Class.create();
ZenGeoMap.prototype = {
    __init__: function(container){
        this.lock = new DeferredLock();
        this.map = new GMap2(container);
        this.map.addControl(new GSmallMapControl());
        this.map.setCenter(new GLatLng(0,0),0);
        this.bounds = new GLatLngBounds();
        this.cache = new ZenossLocationCache();
        this.dirtycache = false;
        this.geocoder = new GClientGeocoder(this.cache);
        var icon = new GIcon();
        icon.iconSize = new GSize(18,18);
        icon.iconAnchor = new GPoint(9,9);
        this.baseIcon = icon;
        this.geocodelock = new DeferredLock();
        this.mgr = new GMarkerManager(this.map);
        this.geocodetimeout = 500;
        bindMethods(this);
    },
    geocode: function(address, callback) {
        var checkStatus = method(this, function(ob) {
            if (ob.Status.code == G_GEO_SUCCESS) {
                callLater(this.geocodetimeout/1000, method(this, function(){
                        this.geocodelock.release()}));
                coords = ob.Placemark[0].Point.coordinates;
                lat = coords[1];
                lng = coords[0];
                callback(new GLatLng(lat, lng));
            } else if (ob.Status.code == 620) {
                this.geocodetimeout += 50;
                callLater(5, method(this, function(){makereq()}));
            } else {
                callback(null);
                callLater(this.geocodetimeout/1000, method(this, function(){
                        this.geocodelock.release()}));
            }
        });
        var makereq = method(this, function(){
            if (!!this.cache.get(address)) {
                this.geocodelock.release();
                this.geocoder.getLatLng(address, callback);
            } else {
                YAHOO.zenoss.geocodingdialog.show();
                this.geocoder.getLocations(address, checkStatus);
            }
            
        });
        var lockedreq = method(this, function(){
            this.geocodelock.acquire().addCallback(method(this, makereq));
        });
        lockedreq();
    },
    showAllMarkers: function(markers){
        this.mgr.refresh();
        this.map.setZoom(this.map.getBoundsZoomLevel(this.bounds));
        this.map.setCenter(this.bounds.getCenter());
        this.saveCache();
    },
    Dot: function(p, color) {
        colors = ['green', 'grey', 'blue', 'yellow', 'orange', 'red'];
        severity = findValue(colors, color);
        newsize = 16 + severity;
        this.baseIcon.iconSize = new GSize(newsize, newsize)
        function colorImportance (marker, b) {
            return GOverlay.getZIndex(marker.getPoint().lat()) + 
                      findValue(colors, color)*10000000;
        };
        var icon = new GIcon(this.baseIcon);
        icon.image = "img/"+color+"_dot.png";
        return new GMarker(p, {zIndexProcess:colorImportance, icon:icon});
    },
    addPolyline: function(addresses) {
        var addys = addresses[0];
        var severity = addresses[1];
        var colors = ['#00ff00', '#888888', '#0000ff', '#ffd700', 
                      '#ff8c00', '#ff0000']
        var color = colors[severity];
        var points = []
        var lock = new DeferredLock();
        var lock2 = new DeferredLock();
        var addadd = bind(function(address) {
            var d = lock.acquire();
            d.addCallback(bind(function(p){
                this.geocode(
                    address,
                    function(p){
                        points.push(p);
                        if(points.length==addys.length){
                            if (lock2.locked) lock2.release();
                        }
                        lock.release();
                    });
            }, this));
        }, this);
        var e = lock2.acquire();
        e.addCallback(bind(function(){
            map(addadd, addys);
        }, this));
        var f = lock2.acquire();
        f.addCallback(bind(function(p){
            var polyline = new GPolyline(points, color, 3);
            this.map.addOverlay(polyline);
            lock2.release();
        }, this));
    },
    addMarkers: function(nodedata){
        var ready_markers = [];
        var nummarkers = 0;
        var nodelen = nodedata.length;
        YAHOO.zenoss.geocodingdialog.setHeader(
            "Geocoding " + nummarkers + " of " + nodelen + " addresses..."
        );
        function makeMarker(node) {
            var address = node[0];
            var color = node[1];
            var clicklink = node[2].replace(
                'locationGeoMap',
                'simpleLocationGeoMap'
            );
            var summarytext = node[3];
            if (this.cache.get(address)==null)
                this.dirtycache = true;
            if (address) {
            this.geocode(
                address,
                bind(function(p){
                    nummarkers += 1;
                    YAHOO.zenoss.geocodingdialog.setHeader(
                        "Geocoding " + nummarkers + " of " + nodelen + " addresses..."
                    );
                    if (p) {
                        var marker = this.Dot(p, color);
                        this.bounds.extend(p);
                        GEvent.addListener(marker, "click", function(){
                           if (clicklink.search('ocationGeoMap')>0){
                               location.href = clicklink;
                           } else {
                            currentWindow().parent.location.href = clicklink;
                           }
                        });
                        ready_markers.push(marker);
                        GLOB_MARKERDATA.push([marker, clicklink, summarytext]);
                    }
                }, this)
            );
            } else { nummarkers += 1 }
        }
        var makeMarker = method(this, makeMarker);
        forEach(nodedata, makeMarker);
        function checkMarkers() {
            if (nodelen == nummarkers) {
                this.mgr.addMarkers(ready_markers, 0);
                YAHOO.zenoss.geocodingdialog.hide();
                this.showAllMarkers();
            } else {
                callLater(0.2, checkMarkers);
            }
        }
        var checkMarkers = method(this, checkMarkers);
        checkMarkers();
    },
    saveCache: function() {
        if (this.dirtycache) {
            cachestr = serializeJSON(this.cache);
            savereq = doXHR( 
                '/zport/dmd/setGeocodeCache', 
                {'sendContent':cachestr,
                 'method':'POST',
                 'mimeType':'text/plain'
                }
            );
        }
        this.dirtycache = false;
    },
    doDraw: function(results) {
        var nodedata = results.nodedata;
        var linkdata = results.linkdata;
        this.mgr = new GMarkerManager(this.map);
        //this.mgr.refresh();
        this.map.clearOverlays();
        this.addMarkers(nodedata);
        for (j=0;j<linkdata.length;j++) {
            this.addPolyline(linkdata[j]);
        }
        callLater(0.5, function(){ // Don't understand why this is necessary, but it works
            for (g=0;g<GLOB_MARKERDATA.length;g++) {
                post_process(GLOB_MARKERDATA[g]);
            }
            GLOB_MARKERDATA = [];
        });
    },
    refresh: function() {
        var results = {
            'nodedata':[],
            'linkdata':[]
        };
        var myd = loadJSONDoc('getChildGeomapData');
        myd.addCallback(function(x){results['nodedata']=x});
        var myd2 = loadJSONDoc('getChildLinks');
        myd2.addCallback(function(x){results['linkdata']=x});
        var bigd = new DeferredList([myd, myd2], false, false, true);
        bigd.addCallback(method(this, function(){this.doDraw(results)}));
    }
}

function _getGMMarkerImage(marker) {
    var myval;
    forEach(values(marker), function(val){
        try {
            if (val.tagName=='IMG') {
                myval = val;
            }
        } catch(e) {noop()}
    });
    return myval;
}

function post_process(m) {
    var marker = m[0];
    var clicklink = m[1];
    var summarytext = m[2];
    var markerimg = _getGMMarkerImage(marker);
    addElementClass(markerimg.ownerDocument.body, 
                    "yui-skin-sam")
    addElementClass(markerimg.ownerDocument.body, 
                    "zenoss-gmaps")
    //summarytext = YAHOO.zenoss.unescapeHTML(summarytext);
    randint = parseInt(Math.random()*100000);
    var ttip = new YAHOO.widget.Tooltip(
        randint+"_tooltip",
        {
            context:markerimg, 
            text:summarytext
        }
    );
}

function geomap_initialize(){
    YAHOO.zenoss.geocodingdialog = new YAHOO.widget.Panel("geocoding",
        {   width:"240px",
            fixedcenter:true,
            close:false,
            draggable:false,
            zindex:40000,
            modal:true,
            visible:false
        }
    );
    YAHOO.zenoss.geocodingdialog.setHeader("Geocoding 1 of 30 addresses...")
    YAHOO.zenoss.geocodingdialog.setBody(
            '<img src="http://us.i1.yimg.com/us.yimg.com/'+
            'i/us/per/gr/gp/rel_interstitial_loading.gif" />'
    );
    var x = new ZenGeoMap($('geomapcontainer'));
    connect(currentWindow(), 'onunload', GUnload);

    addElementClass($('geomapcontainer'), "yui-skin-sam");
    YAHOO.zenoss.geocodingdialog.render($('geomapcontainer'));
    var portlet_id = currentWindow().frameElement.parentNode.id.replace(
        '_body', '');
    var pobj = currentWindow().parent.ContainerObject.portlets[portlet_id];
    pobj.mapobject = x;
    x.refresh();
}


addLoadEvent(function() {
    YAHOO.zenoss.loader.require("container");
    YAHOO.zenoss.loader.insert({onSuccess:geomap_initialize})
});

