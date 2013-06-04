var IS_MAP_PORTLET = IS_MAP_PORTLET || false;

YAHOO.namespace('zenoss.geomap');

(function() {

    var Geocoder = function(geo) {
        this.geocoder = geo;
        this.cache = {};
        this.cached = false;
    };
    Geocoder.prototype.geocode = function(address, callback) {
        this.cached = true;
        try {
            address = window.parent.Ext.String.trim(address);
        } catch (x) {
            // we might not be running in an iframe so do nothing
        }


        if(address.match(latlngpat) ){
            this.cache[address] = [parseFloat(address.split(',')[0]),parseFloat(address.split(',')[1])];
            callback(this.cache[address], "OK", "RENDERING");
            return false;
        };

        if(!isCacheDirty){
            // we have cache from server, inject it and go until else end
            this.cache = geocodecache;
            callback(geocodecache[address], "OK", "RENDERING");
            return false;
        }

        if (!this.cache[address]) {
            var me = this;

            this.geocoder.geocode( {'address': address}, function(results, status) {

                if (results) {
                    me.cache[address] = [results[0].geometry.location.lat(),results[0].geometry.location.lng()];
                }

                callback(me.cache[address], status.toString(), "GEOCODING");
            });
        } else {
            // we have a clean result already in the Geocoder.cache, just return it.
            callback(this.cache[address], "OK", "RENDERING");
        }
    };

     /* PRIVATE GLOBALS */
        var ZenGeoMapPortlet = YAHOO.zenoss.Class.create(); // The main class
        var gmap = null;// global "map"
        var Geocoder = new Geocoder(new google.maps.Geocoder());

        var index = 0;
        var infowindow = null;
        var markers = [];
        var polylineregistry = [];
        var dialog = null;
        var nodedata = null;
        var linkdata = null;
        var errorCount = 0;
        var latlngpat = /^(\-?\d+(\.\d+)?),\s*(\-?\d+(\.\d+)?)$/;
        var linecolors = ['#00ff00', '#888888', '#0000ff', '#ffd700', '#ff8c00', '#ff0000'];
        var markercolors = ['green', 'grey', 'blue', 'yellow', 'orange', 'red'];
        var isCacheDirty = false;
        var nodeMap = {};
        var lineMap = {};
        var polling = 400;
        var refreshing = false;

    /* PUBLICIZE */
    ZenGeoMapPortlet.prototype = {
        __init__: function(container){
            this.map = gmap;
        },
        refresh: function(){
            _engine.refresh();
        }
    }

    /*  BASE ENGINE */
    var _engine = {
        initMap: function(container) {
            _engine.maximizeMapHeight();
            var myOptions = {
                zoom: 6,
                center: new google.maps.LatLng(43.907787,-79.359741),
                mapTypeControl: false,
                disableDefaultUI: true,
                streetViewControl: false,
                navigationControl: true,
                mapTypeControlOptions: {style: google.maps.MapTypeControlStyle.DROPDOWN_MENU},
                mapTypeId: google.maps.MapTypeId.ROADMAP
            }
            gmap = new google.maps.Map(document.getElementById(container), myOptions);
            // initialize the global popup window for reuse:
            infowindow = new google.maps.InfoWindow({
                content: "holding..."
            });
            _engine.refresh();
        },
        refresh: function() {
            // this is called when the page loads, and when it refreshes.
            var results = {
                'nodedata':[],
                'linkdata':[]
            };
            var myd = loadJSONDoc('getChildGeomapData');
            myd.addCallback(function(x){
                results['nodedata']=x;
                nodedata = results.nodedata;
            });
            var myd2 = loadJSONDoc('getChildLinks');
            myd2.addCallback(function(x){
                results['linkdata']=x;
                linkdata = results.linkdata;
            });
            var bigd = new DeferredList([myd, myd2], false, false, true);
            bigd.addCallback(method(this, function(){
                _overlay.doDraw(results);
            }));
        },
        maximizeMapHeight: function() {
            mapdiv = $('geomapcontainer');
            mapoffset = getElementPosition(mapdiv).y;
            maxbottom = getViewportDimensions().h;
            newdims = {'h':maxbottom-mapoffset};
            setElementDimensions(mapdiv, newdims);
        }
    }

   /* DRAWING OVERLAY AND MARKERS */
    var _overlay = {
        addMarkers: function() {
            if(!nodedata[index][0]) return false; // no addresses so nevermind

            if(refreshing && !_utils.isMemCacheDirty()){
                _utils.checkStatusColors();
                return true;
            }

            Geocoder.geocode(nodedata[index][0], function(address, status, msg){
                if (status == "OK") {
                    if(!refreshing){
                        _utils.overlayDialog(msg);
                    }else{
                        if(msg == "GEOCODING") {
                            _utils.overlayDialog(msg);
                        }
                    }
                    _overlay.constructMarker(address);
                }else if(status == "ZERO_RESULTS"){
                        _utils.statusDialog("Stopping! There was a problem with the location address: "+nodedata[index][0]);
                        return true;
                }else if(status == "OVER_QUERY_LIMIT") {
                    errorCount++;
                    if(errorCount >= 5){
                        _utils.statusDialog("QUERY_LIMIT error. If this is a free account, you may have reached your daily limit. Please try again later.");
                        errorCount = 0;
                        return false;
                    }
                    setTimeout(function(){_overlay.addMarkers();}, 1200);
                }else{
                    _utils.statusDialog(status+" in geocoding node location addresses");
                    dialog.style.display = 'block';
                    dialog.innerHTML = "";
                }
            } );
        },
        addPolyline: function() {
            if(linkdata.length == 0){
                // there's no linkdata, just save cache and move on
                _utils.saveCache();
                dialog.style.display = 'none';
                return;
            }
            var points  = [];
            var start   = Geocoder.cache[linkdata[index][0][0]];
            var end     = Geocoder.cache[linkdata[index][0][1]];
            if(start && end){
                points.push([start[0],start[1]]);
                points.push([end[0],end[1]]);
            }else{
                // abandon this line since something is wrong with the addresses
                index++;
                setTimeout(function(){_overlay.addPolyLine();}, polling);
                return false;
            }
            _overlay.constructLine(points);
        },
        constructMarker: function(address){
            var pinImage = _utils.generateMarkerIcon(index);
            var marker;
            if (address) {
                marker = new google.maps.Marker( {
                    position: new google.maps.LatLng(
                        address[0],
                        address[1]
                    ),
                    icon: pinImage,
                    map: gmap,
                    title: nodedata[index][0]
                });
                if(nodedata[index][1] == "red"){
                    // if it's bad, make sure it's visible and not covered up by other markers:
                    marker.setZIndex(google.maps.Marker.MAX_ZINDEX + 1);
                }
                markers.push(marker);
                google.maps.event.addListener(marker, 'click', (function(marker, index) {
                    return function(){
                        infowindow.setContent(_utils.infoContent(index));
                        infowindow.open(gmap, marker);
                        marker.setZIndex(google.maps.Marker.MAX_ZINDEX + 1);
                    };
                })(marker, index));
            }
            index++;
            if(index >= nodedata.length){
                _utils.autoCenter(markers);
                index = 0;
                refreshing = true;
                _overlay.addPolyline();
                return;
            }else{
                // done with that marker, but wait, there's more...
                // need a delay here to keep google from saying: OVER_QUERY_LIMIT
                // due to having too many queries per second
                setTimeout(function(){_overlay.addMarkers()}, polling);
            }
        },
        constructLine: function(points){
            points = [
                new google.maps.LatLng(points[0][0],points[0][1]),
                new google.maps.LatLng(points[1][0],points[1][1])
            ]
            var polyline = new google.maps.Polyline({
              path: points,
              strokeColor: linecolors[linkdata[index][1]],
              strokeOpacity: 1.0,
              strokeWeight: 2
            });
            polyline.setMap(gmap);
            polylineregistry.push(polyline);
            index++;
            if(index >= linkdata.length){
                // done with lines, and done with map drawing completely - let's get outta here.
                _utils.saveCache();
                dialog.style.display = 'none';
                index = 0;
                return;
            }else{
                // done with that line, but wait, there's more...
                setTimeout(function(){_overlay.addPolyline();}, polling);
            }
        },
        doDraw: function(results) {

            // set cache for refresh
            if(!Geocoder.cached){
                // there's no gcache = first time loading
                _utils.createMaps();
                // since this is the first time loading, we need to check the geocodecache
                if(geocodecache){
                    geocodecache = YAHOO.lang.JSON.parse(geocodecache);
                    if(_utils.isGeocacheDirty()){
                        // dirty, so reset
                        geocodecache = {};
                        isCacheDirty = true;
                    }
                }else{
                    isCacheDirty = true; // there was no geocodecache from server, so generate the caches
                                         // when drawing the map for the first time
                }
            }
            index = 0;
            _overlay.addMarkers();
        }
    }

    /* UTILS AND HELPERS */
    var _utils = {
        saveCache: function() {
            var cachestr = YAHOO.lang.JSON.stringify(Geocoder.cache);
            var savereq = doXHR(
                '/zport/dmd/setGeocodeCache',
                {'sendContent':cachestr,
                 'method':'POST',
                 'mimeType':'text/plain'
                }
            );
            _utils.createMaps();
            isCacheDirty = false;
        },
        isGeocacheDirty: function(){
            if(!geocodecache) return true; // there's no cache, so nevermind all the checking, just geocode
            var geocount = this.objLength(geocodecache);
            if(geocount > 0){
                // check nodedata[i][0] is in geocodecache[here]. If not, then cache is dirty
                // are nodedata and geocodecache the same length? if not, then there was a change
                if(geocount != nodedata.length) return true;
                return false;
            }else{
                return true;
            }
            return true;
        },
        isMemCacheDirty: function(){
            if(isCacheDirty == true) return true;

            var nodeMapLen = _utils.objLength(nodeMap);
            var linkMapLen = _utils.objLength(lineMap);

            if(nodeMapLen > 0){ // have cache
                // make sure there's no new/deleted nodes
                if(nodeMapLen != nodedata.length){//  something was added or removed
                    geocodecache = {};
                    isCacheDirty = true;
                    _utils.wipeMarkers();
                    refreshing = false;
                    return true;
                }
                return false;
            }else{
                // no cache? Create one.
                _utils.createMaps();
                return true;
            }
            if(linkMapLen > 0){ // have cache
                // make sure there's no new/deleted nodes
                if(linkMapLen != linkdata.length){//  something was added or removed
                    geocodecache = {};
                    isCacheDirty = true;
                    refreshing = false;
                    _utils.wipeMarkers();
                    return true;
                }
                return false;
            }else{
                // no cache? Create one.
                _utils.createMaps();
                return true;
            }
        },
        createMaps: function(){
            nodeMap = {};
            lineMap = {};
            var i = null;
            for (i = 0; i < nodedata.length; i++) {
                nodeMap[nodedata[i][2]] = nodedata[i]; // UID based keymap
            }

            for (i = 0; i < linkdata.length; i++) {
                lineMap[linkdata[i][0].toString()] = linkdata[i];
            }
        },
        checkStatusColors: function(){
            // run through the whole thing:
            var i = null;
            for (i = 0; i < nodedata.length; i++) {
               if(nodeMap[nodedata[i][2]][1] != nodedata[i][1]){
                    _utils.replaceMarker(i);
               }
            }
            for (i = 0; i < linkdata.length; i++) {
               if(lineMap[linkdata[i][0].toString()][1] != linkdata[i][1]){
                    // COLOR CHANGED FOR LINE!
                    _utils.changeLineColor(i);
                }
            }
            _utils.createMaps();
        },
        wipeMarkers: function(){
            var i;
            for(i = 0; i < markers.length; i++){
                markers[i].setMap(null);
            }
            for(i = 0; i < polylineregistry.length; i++){
                polylineregistry[i].setMap(null);
            }
            polylineregistry = [];
            markers = [];
        },
        replaceMarker: function(i){
            markers[i].setIcon(_utils.generateMarkerIcon(i));
        },
        changeLineColor: function(i){
            var severity = linkdata[i][1];
            polylineregistry[i].setOptions({strokeColor:linecolors[severity]});
        },
        generateMarkerIcon: function(i){
            var severity = findValue(markercolors, nodedata[i][1]);
            var iconsize = 30; // 30 is the required starting size per google API. FF will throw a bug without the correct initial size.
            var newsize = 11 + severity;
            var pinImage = new google.maps.MarkerImage(
                "img/"+nodedata[i][1]+"_dot.png",
                new google.maps.Size(iconsize, iconsize),// size
                null, //origin null so google will handle it on the fly
                new google.maps.Point((newsize/2),(newsize/2)), // anchor offset so dot is RIGHT on top of location
                new google.maps.Size(newsize, newsize)// scale
            );
            return pinImage;
        },
        infoContent: function(i){
            var clicklink = nodedata[i][2];
            clicklink = clicklink.replace('locationGeoMap', '');
            var contentString = _utils.hrefize(nodedata[i][3]) + '<a target="_top" href="'+clicklink+'">Go to the Infrastructure Location Organizer >';
                // the template language parser chokes when I close the anchor /a
                // it works like this so leaving it for now (even stranger is that you can have /a
                // in a comment, and the parser still picks it up and crashes!
            return contentString;
        },
        hrefize: function(h){
            return h.replace(/location.href/g, 'self.parent.location.href');
        },
        autoCenter: function(markers) {
            //  Create a new viewpoint bound
            var bounds = new google.maps.LatLngBounds();
            //  Go through each...
            for(var i = 0; i < markers.length; i++){
                bounds.extend(markers[i].position);
            }
            //  Fit these bounds to the map
            gmap.fitBounds(bounds);
        },
        statusDialog: function(status){
            alert("Google could not process addresses. Reason: " + status);
        },
        overlayDialog: function(msg){
            dialog.style.display = 'block';
            var content = msg+" "+ (index+1) + " of " + nodedata.length + " addresses, please wait...<br><br>";
            content += '<img src="http://us.i1.yimg.com/us.yimg.com/i/us/per/gr/gp/rel_interstitial_loading.gif" />';
            dialog.innerHTML = content;
        },
        objLength: function(obj){
            var count = 0;
            for (var key in obj){
                count++
            }
            return count;
        }
    }
    /* SET UP AND RUN THE MAP */
    YAHOO.zenoss.geomap.initialize = function (container) {
        addElementClass($('geomapcontainer'), "yui-skin-sam");
        dialog = document.getElementById('geocodingdialog');
        var pollrate = document.location.search.split('=')[1]?document.location.search.split('=')[1]:polling;
        polling = pollrate;
        _engine.initMap(container);
        connect(currentWindow(), 'onresize', _engine.maximizeMapHeight);
        if (IS_MAP_PORTLET) {
            var portlet_id = currentWindow().frameElement.parentNode.id.replace('_body', '');
            var pobj = currentWindow().parent.ContainerObject.portlets[portlet_id];
            pobj.mapobject = new ZenGeoMapPortlet();
        }
    }

})();

YAHOO.register('geomap', YAHOO.zenoss.geomap, {});
