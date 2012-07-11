var IS_MAP_PORTLET = IS_MAP_PORTLET || false;

YAHOO.namespace('zenoss.geomap');

(function() { 
     /* PRIVATE GLOBALS */     
        var ZenGeoMapPortlet = YAHOO.zenoss.Class.create(); // The main class        
        var gmap = null;// global "map"
        var geocoder = new google.maps.Geocoder();
        var gcache = [];
        var scache = {};
        var nodes = [];
        var linepoints = [];
        var index = 0;
        var infowindow = null;    
        var markers = [];
        var polylineregistry = [];
        var dialog = null;
    
    /* PUBLICIZE */
    ZenGeoMapPortlet.prototype = {
        __init__: function(container){
            this.map = gmap;
        },
        refresh: function(){
            _engine.refresh();
        }
    }
        
    /* BASE ENGINE */
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
            myd.addCallback(function(x){results['nodedata']=x});
            var myd2 = loadJSONDoc('getChildLinks');
            myd2.addCallback(function(x){results['linkdata']=x;});
            var bigd = new DeferredList([myd, myd2], false, false, true);
            bigd.addCallback(method(this, function(){
                if(!_utils.checkMemCache()){// this is only used for refresh checking
                    _overlay.doDraw(results);                    
                }
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
            // check server cache to see if we need to geocode or not            
            if(geocodecache && geocodecache.nodes.length > 0){
                _overlay.constructMarker(geocodecache.nodes[index], false);                
            }else{
                if(!nodedata[index][0]) return false; // no addresses so nevermind
                geocoder.geocode( { 'address': nodedata[index][0]}, function(results, status) {
                    if (status == google.maps.GeocoderStatus.OK) {              
                        // got a result, store it for the server cache builder                       
                        nodes.push(results);
                        dialog.style.display = 'block';
                        var content = "Geocoding " + (index+1) + " of " + nodedata.length + " addresses, please wait...<br><br>";
                        content += '<img src="http://us.i1.yimg.com/us.yimg.com/i/us/per/gr/gp/rel_interstitial_loading.gif" />';
                        dialog.innerHTML = content;                 
                        _overlay.constructMarker(results, true);
                    }else{
                        _utils.statusDialog(status);
                        dialog.style.display = 'block';
                        dialog.innerHTML = "";                     
                    }
                });  
            }
           
        }, 
        addPolyline: function() {
            if(linkdata.length == 0){
                // there's no linkdata
                scache.lines = [];
                dialog.style.display = 'none';
                return;
            }
            var severity = linkdata[index][1];
            var colors = ['#00ff00', '#888888', '#0000ff', '#ffd700', 
                          '#ff8c00', '#ff0000']
            var color = colors[severity];
            var points = [];
            // check geocodecache to see if we need to geocode or not
            if(geocodecache && geocodecache.nodes.length > 0){
                // get points from cache and pass them
                _overlay.constructLine(color, geocodecache.lines[index], false);
            }else{
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
                                linepoints.push(points);
                                _overlay.constructLine(color, points, true);
                            }else{
                                _utils.statusDialog(status);
                            }
                        });                 
                    }else{
                        _utils.statusDialog(status);
                    }
                });
            }
        },     
        constructMarker: function(results, geocoding){
            var colors = ['green', 'grey', 'blue', 'yellow', 'orange', 'red'];
            var severity = findValue(colors, nodedata[index][1]);
            var newsize = 16 + severity;                
            var pinImage = new google.maps.MarkerImage("img/"+nodedata[index][1]+"_dot.png",
                new google.maps.Size(newsize, newsize),// size
                null, //origin null so google will handle it on the fly
                new google.maps.Point((newsize/2),(newsize/2)), // anchor offset so dot is RIGHT on top of location
                new google.maps.Size(newsize, newsize)// scale                    
            );
            var clicklink = nodedata[index][2];
            clicklink = clicklink.replace('locationGeoMap', '');             
            var contentString = _utils.hrefize(nodedata[index][3]), lat, lng;
                // for some reason, the template language parser chokes when I close the anchor /a
                // it works like this so leaving it for now (even stranger is that you can have /a
                // in a comment, and the parser still picks it up and crashes!
                contentString += '<a target="_top" href="'+clicklink+'">Go to the Infrastructure Location Organizer >';
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
                    infowindow.setContent(contentString); 
                    infowindow.open(gmap, marker);
                    marker.setZIndex(google.maps.Marker.MAX_ZINDEX + 1); 
                } 
            })(marker, index)); 
            index++;     
            if(index >= nodedata.length){
                if(geocoding) scache.nodes = nodes;
                // done with markers, let's get outta here.
                // center and add polyLines now
                _utils.autoCenter(markers);
                index = 0;
                _overlay.addPolyline();
                return;
            }else{
                // done with that marker, but wait, there's more...
                // need a delay here to keep google from saying: OVER_QUERY_LIMIT
                // due to having too many queries per second
                setTimeout(function(){_overlay.addMarkers()}, 200);
            }
                        
        },
        constructLine: function(color, points, geocoding){
            points = [
                new google.maps.LatLng(points[0][0],points[0][1]),
                new google.maps.LatLng(points[1][0],points[1][1])
            ]; 
            var polyline = new google.maps.Polyline({
              path: points,
              strokeColor: color,
              strokeOpacity: 1.0,
              strokeWeight: 2
            }); 
            polyline.setMap(gmap);
            polylineregistry.push(polyline); 
            index++;
            if(index >= linkdata.length){
                // done with lines, and done with map drawing completely - let's get outta here.
                if(geocoding){
                     scache.lines = linepoints;
                    // save the cache after a geocode                
                    _utils.saveCache();
                }    
                dialog.style.display = 'none';
                index = 0;
                return;
            }else{
                // done with that line, but wait, there's more...
                setTimeout(function(){_overlay.addPolyline()}, 200);                           
            }
        },
        doDraw: function(results) {      
            nodedata = results.nodedata;
            linkdata = results.linkdata;
            // set cache for refresh
            gcache = nodedata;
            
            if(geocodecache){
               try{
                    geocodecache = YAHOO.lang.JSON.parse(geocodecache);
               }catch(e){
                    geocodecache = null;
               };
            }
            // remove lines:
            forEach(polylineregistry, function(o){
                gmap.remove_overlay(o);
            });            
            _overlay.addMarkers();
        }
    }
    /* UTILS AND HELPERS */
    var _utils = {  
        saveCache: function() {
            cachestr = YAHOO.lang.JSON.stringify(scache);
            savereq = doXHR( 
                '/zport/dmd/setGeocodeCache', 
                {'sendContent':cachestr,
                 'method':'POST',
                 'mimeType':'text/plain'
                }
            );
            scache = {};
            nodes = [];
            linepoints = [];
        },    
        checkMemCache: function(){
            // check if there is a cache, return false if not = newmap
            // if there IS a cache then this is a refresh, check diff
            if(gcache.length > 0){ // have cache
                // make sure there's no new nodes or color changes              
                var nodeMap = {};
                var i = null;
                for (i = 0; i < gcache.length; i++) {
                    nodeMap[gcache[i][2]] = gcache[i]; // UID based keymap
                }    

                for (i = 0;i < nodedata.length; i++){
                    if(nodeMap[nodedata[i][2]]){
                        //check colors on the existing nodes for changes
                       if(nodeMap[nodedata[i][2]][1] != nodedata[i][1]){
                            geocodecache = null;
                            return false;// status (color) changed, refresh                        
                        }
                    }else{
                        // this is a new node
                        geocodecache = null;
                        return false;                    
                    }
                }
                return true;
            }else{
                return false; // new map
            }
       
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

        connect(currentWindow(), 'onresize', _engine.maximizeMapHeight);        
        if (IS_MAP_PORTLET) {
            var portlet_id = currentWindow().frameElement.parentNode.id.replace('_body', '');
            var pobj = currentWindow().parent.ContainerObject.portlets[portlet_id];
            pobj.mapobject = new ZenGeoMapPortlet();
        }        
    }

})(); 

YAHOO.register('geomap', YAHOO.zenoss.geomap, {});
