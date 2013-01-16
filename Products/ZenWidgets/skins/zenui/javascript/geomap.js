var IS_MAP_PORTLET = IS_MAP_PORTLET || false;

YAHOO.namespace('zenoss.geomap');

(function() { 
        //console.log(YAHOO.geoportlet);
     /* PRIVATE GLOBALS */     
        var ZenGeoMapPortlet = YAHOO.zenoss.Class.create(); // The main class        
        var gmap = null;// global "map"
        var geocoder = new google.maps.Geocoder();
        var gcache = null;
        var lcache = null;
        var scache = {};
        var nodes = [];
        var linepoints = [];
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
            
            // do we have a cache that we think has the same nodes as the last time we looked?
            if(!_utils.isMemCacheDirty()){               
                // is this the first time through? If not, make sure we only redraw on a node color change:
                if(scache.hasOwnProperty("nodes")){ 
                    // run through and see if color has change. This method will update the map with a new
                    // icon if it has and move on to the next one.
                    _utils.checkNodeStatusColor();
                    index++;    
                    if(index >= nodedata.length){
                        index = 0;
                        _overlay.addPolyline(false);
                        return true;
                    }
                    _overlay.addMarkers(); 
                    return true;
                }  
                // draw the initial map with the server cache. 
                    dialog.style.display = 'block';
                    var content = "Loading locations, please wait...<br><br>";
                    content += '<img src="http://us.i1.yimg.com/us.yimg.com/i/us/per/gr/gp/rel_interstitial_loading.gif" />';
                    dialog.innerHTML = content;                
                _overlay.constructMarker(geocodecache.nodes[index], false);
                return true;
            }            
            
            
            if(nodedata[index][0].match(latlngpat) ){ // item is latlong entry only
                //Create custom object that can be digested by constructMarker:
                lonlatObject = {};                    
                lonlatObject.address_components = [{"LUID":nodedata[index][2], "color":nodedata[index][1]}];
                lonlatObject.geometry = {};
                lonlatObject.geometry.location = {};
                lonlatObject.geometry.location.lat = nodedata[index][0].split(",")[0];
                lonlatObject.geometry.location.lng = nodedata[index][0].split(",")[1];                    
                var lonlatResults = [lonlatObject];               
                nodes.push(lonlatResults);                      
                _overlay.constructMarker(lonlatResults, false);
                return true;
            }            

            // this entry has no cache, and is in address form = geocode it
            geocoder.geocode( { 'address': nodedata[index][0]}, function(results, status) {
                if (status == google.maps.GeocoderStatus.OK) {
                    // got a result, store it for the server cache builder under nodes                     
                    // add an identifier for each entry so we can test it later when reloading for changes
                    results[0].address_components.push({"LUID":nodedata[index][2], "color":nodedata[index][1]}); 
                    nodes.push(results);
                    dialog.style.display = 'block';
                    var content = "Geocoding " + (index+1) + " of " + nodedata.length + " addresses, please wait...<br><br>";
                    content += '<img src="http://us.i1.yimg.com/us.yimg.com/i/us/per/gr/gp/rel_interstitial_loading.gif" />';
                    dialog.innerHTML = content;                 
                    _overlay.constructMarker(results, true);
                }else if(status === google.maps.GeocoderStatus.ZERO_RESULTS){
                        _utils.statusDialog("Stopping! There was a problem with the location address: "+nodedata[index][0]);   
                        return true;                        
                }else if(status === google.maps.GeocoderStatus.OVER_QUERY_LIMIT) { 
                    /*  try the address a few times after some delay to make sure it really is a query limit
                        problem and not just erroring becuase we hit it too many times a second. We can get
                        this error when the user has reached their daily limit for their IP as well.
                    */
                    errorCount++;  
                    if(errorCount >= 5){
                        _utils.statusDialog("QUERY_LIMIT error. If this is a free account, you may have reached your daily limit. Please try again later.");
                        errorCount = 0;
                        return false;
                    }
                    setTimeout(function(){_overlay.addMarkers()}, 1200);
                }else{
                    _utils.statusDialog(status+" in geocoding node location addresses");
                    dialog.style.display = 'block';
                    dialog.innerHTML = "";                     
                }
            });  
           
        }, 
        addPolyline: function(geocoding) {
            if(linkdata.length == 0){
                // there's no linkdata, just save cache and move on
                if(isCacheDirty){
                    scache.lines = [];
                    _utils.saveCache();
                }
                dialog.style.display = 'none';
                return;
            }
            
            
            if(!_utils.isMemCacheDirty()){  
                // is this the first time through? If not, make sure we only redraw on a line color change:
                if(scache.hasOwnProperty("lines")){                     
                    // run through and see if color has change. This method will update the map with a new
                    // linecolor if it has and move on to the next one.
                    _utils.checkLineStatusColor();
                    index++;   
                    if(index >= linkdata.length){
                        dialog.style.display = 'none';
                        return true;
                    }
                    _overlay.addPolyline(false); 
                    return true;
                }                  
                _overlay.constructLine(geocodecache.lines[index], false);                
                return true
            }      
            
           
 
            if(linkdata[index][0][0].match(latlngpat) && linkdata[index][0][1].match(latlngpat)){            
                // we're loaded down with latlon, don't geocode
                //Create custom object that can be digested by constructLine:
                var points = [];
                points.push([
                            linkdata[index][0][0][0],
                            linkdata[index][0][0][1]
                            ]
                );

                points.push([   
                            linkdata[index][0][1][0],
                            linkdata[index][0][1][1]
                            ]
                ); 
                var severity = linkdata[index][1];
                linepoints.push([points, severity]);
                _overlay.constructLine([points, severity], false);
                return true;                
            }      
            
            var points = [];            
            geocoder.geocode( { 'address': linkdata[index][0][0]}, function(results, status) { 
                if (status == google.maps.GeocoderStatus.OK) {   
                    points.push([
                                results[0].geometry.location.lat(),
                                results[0].geometry.location.lng()
                                ]
                    );
                    geocoder.geocode( { 'address': linkdata[index][0][1]}, function(results, status) {
                        if (status == google.maps.GeocoderStatus.OK) {
                            points.push([   
                                        results[0].geometry.location.lat(),
                                        results[0].geometry.location.lng()
                                        ]
                            ); 
                            var severity = linkdata[index][1];
                            linepoints.push([points, severity]);
                            _overlay.constructLine([points, severity], true);
                        }else if(status === google.maps.GeocoderStatus.ZERO_RESULTS){
                                _utils.statusDialog("Stopping! There was a problem with connecting address for line: "+linkdata[index][0][1]);   
                                return true;                            
                        }else{
                            _utils.statusDialog(status+" in geocoding connection lines");
                        }
                    });                 
                }else if(status === google.maps.GeocoderStatus.ZERO_RESULTS){
                        _utils.statusDialog("Stopping! There was a problem with connecting address for line: "+linkdata[index][0][0]);   
                        return true;                        
                }else if(status === google.maps.GeocoderStatus.OVER_QUERY_LIMIT) {    
                    /*  try the address a few times after some delay to make sure it really is a query limit
                        problem and not just erroring becuase we hit it too many times a second. We can get
                        this error when the user has reached their daily limit for their IP as well.
                    */                    
                    errorCount++;
                    if(errorCount >= 5){
                        _utils.statusDialog("QUERY_LIMIT error. If this is a free account, you may have reached your daily limit. Please try again later.");
                        errorCount = 0;
                        return false;
                    }                    
                    setTimeout(function(){_overlay.addPolyline(geocoding)}, 1200);
                }else{
                    _utils.statusDialog(status+" in geocoding connection lines");
                }
            });
        },     
        constructMarker: function(results, geocoding){
            var pinImage = _utils.generateMarkerIcon(index); 
            if(geocoding){
                results[0].geometry.location.lat = results[0].geometry.location.lat(); 
                results[0].geometry.location.lng = results[0].geometry.location.lng();
                // create a new entry on the results object for cache storage                
            }
            var marker = new google.maps.Marker( {
                position: new google.maps.LatLng(
                    results[0].geometry.location.lat,
                    results[0].geometry.location.lng
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
                } 
            })(marker, index)); 
            index++;     
            if(index >= nodedata.length){
                scache.nodes = [];            
                if(isCacheDirty){ 
                    scache.nodes = nodes;
                }else{
                    scache.nodes = geocodecache.nodes;
                }
                // done with markers, let's get outta here.
                // center and add polyLines now
                _utils.autoCenter(markers);
                index = 0;
                _overlay.addPolyline(geocoding);
                return;
            }else{
                // done with that marker, but wait, there's more...
                // need a delay here to keep google from saying: OVER_QUERY_LIMIT
                // due to having too many queries per second
                setTimeout(function(){_overlay.addMarkers()}, polling);
            }
                        
        },
        constructLine: function(points, geocoding){
            var severity = points[1];
            points = [
                new google.maps.LatLng(points[0][0][0],points[0][0][1]),
                new google.maps.LatLng(points[0][1][0],points[0][1][1])                
            ]
            var polyline = new google.maps.Polyline({
              path: points,
              strokeColor: linecolors[severity],
              strokeOpacity: 1.0,
              strokeWeight: 2
            }); 
            polyline.setMap(gmap);
            polylineregistry.push(polyline); 
            index++;
            if(index >= linkdata.length){
                // done with lines, and done with map drawing completely - let's get outta here.
                scache.lines = [];
                if(isCacheDirty){                
                    scache.lines = linepoints;          
                }else{
                    scache.lines = geocodecache.lines;
                }
                _utils.saveCache();
                dialog.style.display = 'none';
                index = 0;
                return;
            }else{
                // done with that line, but wait, there's more...
                setTimeout(function(){_overlay.addPolyline(geocoding)}, polling);                           
            }
        },
        doDraw: function(results) {      
            // set cache for refresh
            if(gcache == null){
                // there's no gcache = first time loading
                _utils.createMaps();
                // since this is the first time loading, we need to check the geocodecache
                if(geocodecache){ 
                   try{
                        geocodecache = YAHOO.lang.JSON.parse(geocodecache);
                   }catch(e){
                        // there is a bug in the yahoo parser on a refresh
                        // catch it here
                   };
                   if(_utils.isGeocacheDirty()){
                        // dirty, so reset
                        geocodecache = {};
                        geocodecache.nodes = {};  
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
            var cachestr = YAHOO.lang.JSON.stringify(scache);
            var savereq = doXHR( 
                '/zport/dmd/setGeocodeCache', 
                {'sendContent':cachestr,
                 'method':'POST',
                 'mimeType':'text/plain'
                }
            );
            _utils.createMaps();
            isCacheDirty = false;            
            nodes = [];
            linepoints = [];
        },    
        isGeocacheDirty: function(){
            var dirty = true; 
            if(!geocodecache) return dirty; // there's no cache, so nevermind all the checking, just geocode

            if(geocodecache.nodes.length > 0){
                dirty = false;
                // are nodedata and geocodecache the same length? if not, then there was a change
                if(geocodecache.nodes.length != nodedata.length) return true;           
            }else{
                return true;
            }
            if(geocodecache.lines && geocodecache.lines.length > 0){
                dirty = false;
                if(geocodecache.lines.length != linkdata.length) return true;             
            }
            return dirty;
        },
        isMemCacheDirty: function(){
            if(isCacheDirty == true) return true;
            if(gcache.length > 0){ // have cache
                // make sure there's no new/deleted nodes                  
                if(gcache.length != nodedata.length){//  something was added or removed
                    geocodecache = {};
                    geocodecache.nodes = {};
                    isCacheDirty = true;
                    gcache = nodedata;
                    _utils.wipeMarkers();                    
                    return true;
                }       
                return false;
            }else{
                // no cache? Create one.
                _utils.createMaps();
                return true;
            }
            if(lcache.length > 0){ // have cache
                // make sure there's no new/deleted nodes                  
                if(lcache.length != linkdata.length){//  something was added or removed
                    geocodecache = {};
                    geocodecache.lines = {};
                    isCacheDirty = true;
                    lcache = linkdata;
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
            gcache = nodedata;
            lcache = linkdata;
            nodeMap = {};
            lineMap = {};
            var i = null;
            for (i = 0; i < gcache.length; i++) {           
                nodeMap[gcache[i][2]] = gcache[i]; // UID based keymap
            }         
            for (i = 0; i < lcache.length; i++) {  
                lineMap[lcache[i][0].toString()] = lcache[i];
            }             
        },
        checkNodeStatusColor: function(){                   
            if(nodeMap[nodedata[index][2]]){
                //check colors on the existing nodes for changes
               if(nodeMap[nodedata[index][2]][1] != nodedata[index][1]){
                    // COLOR CHANGED ON NODE!
                    // set the entry in the cache for proper saving
                    scache.nodes[index][0].address_components[scache.nodes[index][0].address_components.length-1].color = nodedata[index][1];                    
                    _utils.replaceMarker(index);                      
                }
                if((index+1) >= nodedata.length) _utils.saveCache();                
            }
        },
        checkLineStatusColor: function(){    
            if(lineMap[lcache[index][0].toString()]){
                //check colors on the existing nodes for changes;
               if(lineMap[lcache[index][0].toString()][1] != linkdata[index][1]){
                    // COLOR CHANGED FOR LINE!
                    // set the entry in the cache for proper saving
                    scache.lines[index][1] = linkdata[index][1];                    
                    _utils.changeLineColor(index);                      
                }
                if((index+1) >= linkdata.length) _utils.saveCache();                
            }
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
        }
    }
    /* SET UP AND RUN THE MAP */
    YAHOO.zenoss.geomap.initialize = function (container) {
        addElementClass($('geomapcontainer'), "yui-skin-sam");
        dialog = document.getElementById('geocodingdialog'); 
        _engine.initMap(container);        
        var pollrate = document.location.search.split('=')[1]?document.location.search.split('=')[1]:polling;
        polling = pollrate;
        connect(currentWindow(), 'onresize', _engine.maximizeMapHeight);        
        if (IS_MAP_PORTLET) {
            var portlet_id = currentWindow().frameElement.parentNode.id.replace('_body', '');
            var pobj = currentWindow().parent.ContainerObject.portlets[portlet_id];
            pobj.mapobject = new ZenGeoMapPortlet();
        }        
    }

})(); 

YAHOO.register('geomap', YAHOO.zenoss.geomap, {});

