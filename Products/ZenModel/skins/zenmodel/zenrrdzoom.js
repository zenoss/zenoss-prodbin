/*
#####################################################
#
# ZenRRDZoom - Pan & Zoom for Zenoss RRDTool graphs
# 2006-12-29
#
#####################################################
*/


var zoom_factor = 1.5;
var pan_factor = 10; // Fraction of graph to move
var drange_re = /&drange=([0-9]*)/;
var end_re = /--end%3Dnow-([0-9]*)s%7C--start%3Dend-[0-9]*s%7C/;
var width_re  = /--width%3D([0-9]*)%7C/;

var url_cache = String();

// Pull relevant info from the image source URL
function parseUrl(href) {
    var drange = Number(drange_re.exec(href)[1]);
    var width = Number(width_re.exec(href)[1]);
    var end = Number(end_re.exec(href)?end_re.exec(href)[1]:0);
    return [drange, width, end];
}

// Determing the position of the cursor relative to the image
function getPosition(e, obj) {
    e = e || window.event;
    var cursor = { x:0, y:0 };
    var element = getElementPosition(obj);
    if (e.pageX || e.pageY) {
        cursor.x = e.pageX;
        cursor.y = e.pageY;
    } 
    else {
        var de = document.documentElement;
        var b = document.body;
        cursor.x = e.clientX + 
            (de.scrollLeft || b.scrollLeft) - (de.clientLeft || 0);
        cursor.y = e.clientY + 
            (de.scrollTop || b.scrollTop) - (de.clientTop || 0);
    }
    
    cursor.x = cursor.x - element.x;
    cursor.y = cursor.y - element.y; 
    return cursor;
}

// Calculate the new image parameters and generate the source URL
function generateNewUrl(cursor, obj) {
    var x = cursor.x - 67;
    var parsed = parseUrl(obj.src);
    var drange = parsed[0];
    var width = parsed[1];
    if ( x < 0 || x > width ) return obj.src ;
    var end = parsed[2];
    var secs = Math.round(drange/6);
    var newdrange = Math.round(drange/zoom_factor);
    var newsecs = Math.round(newdrange/6);
    var newurl = obj.src.replace(drange_re, '&drange=' + String(newdrange));
    var delta = ((width/2)-x)*(secs/width) + (secs-newsecs)/2;
    var newend = Math.round(end + delta >= 0 ? end + delta : 0);
    var nepart = '--end%3Dnow-' + String(newend) + 's%7C';
    nepart += '--start%3Dend-' + String(newsecs) + 's%7C';
    if (newurl.match(end_re)) { 
        newurl = newurl.replace(end_re, nepart);
    } else {
        newurl = newurl.replace('--height', nepart + '--height');
    }
    return newurl;
}

// Get the absolute position of the image
function getElementPosition(obj) {
	var curleft = curtop = 0;
	if (obj.offsetParent) {
		curleft = obj.offsetLeft
		curtop = obj.offsetTop
		while (obj = obj.offsetParent) {
			curleft += obj.offsetLeft
			curtop += obj.offsetTop
		}
	}
    var element = {x:0,y:0};
    element.x = curleft;
    element.y = curtop;
	return element;
}


// Handle the zoom buttons and invert the zoom_factor
function toggleZoomMode(id, dir){
    var obj = $(id);
    if (dir == 'out') {
        $(id + '_zin').style.backgroundColor = 'transparent';
        $(id + '_zout').style.backgroundColor = 'grey';
        if (zoom_factor > 1) zoom_factor = 1/zoom_factor;
    } else {
        $(id + '_zin').style.backgroundColor = 'grey';
        $(id + '_zout').style.backgroundColor = 'transparent';
        if (zoom_factor < 1) zoom_factor = 1/zoom_factor;
    }
    
}

// Check the source URL for valid data and display the image if so
function loadImage(obj, url) {

    if(url_cache==url) return;
    url_cache = url;
    
    var x = doSimpleXMLHttpRequest(url);

    x.addCallback(
        function(req) {
            if (req.responseText) {
              obj.src = url;
            }
        }
    );
}

// Pan the graph in either direction
function panGraph(direction, id) {
    var obj = $(id);
    var href = parseUrl(obj.src);
    var tenth = Math.round(href[0]/(6*pan_factor));
    var secs = Math.round(href[0]/6);
    if (direction == "right") {
        newend = href[2] - tenth;
    } else {
        newend = href[2] + tenth;
    };
    newend = Math.round(newend);
    nepart = '--end%3Dnow-' + String(newend) + 's%7C';
    nepart += '--start%3Dend-' + String(secs) + 's%7C';
    if (obj.src.match(end_re)) { 
        newurl = obj.src.replace(end_re, nepart);
    } else {
        newurl = obj.src.replace('--height', nepart + '--height');
    };
    loadImage(obj, newurl);
}
    

// Replace the image with the table structure and buttons
function buildTables(obj) {
    var me = $(obj.id);
    var newme = me.cloneNode(true);
    newme.onload = null;
    newme.style.cursor = 'crosshair';
    var table = TABLE({'id':obj.id + '_table'},
                TBODY(
                        {'id':obj.id + '_tbody'},
                        [
                            TR(null,
                                [
                                TD(
                                    {'rowspan':'2',
                                     'style':'background-color:lightgrey;',
                                     'onclick':'panGraph("left","'+obj.id+'")'},
                                    INPUT({'type':'button',
                                    'style':'height:14em;border:1px solid grey;' + 
                                    'cursor:pointer',
                                           'value':'<', 'onfocus':'this.blur();'},
                                        "<")
                                ),
                                TD(
                                    {'rowspan':'2'},
                                    newme
                                ),
                                TD(
                                    {'rowspan':'2',
                                     'style':'background-color:lightgrey;',
                                     'onclick':'panGraph("right","'+obj.id+'")'},
                                    INPUT({'type':'button',
                                    'style':'height:14em;border:1px solid grey;'+
                                    'cursor:pointer',
                                           'value':'>',
                                           'onfocus':'this.blur();'},
                                    ">")
                                ),
                                TD({'id' : obj.id + '_zin',
                                    'style':'cursor:pointer;background-color:grey;'+
                                    'width:3em;text-align:center;',
                                    'onclick':'toggleZoomMode("' + obj.id +
                                    '", "in")'},
                                    IMG({'src':'zoomin.gif'}, "Z+")
                                )
                                ]
                            ),
                            TR(null,
                                TD({'id':obj.id + '_zout',
                                    'style':'cursor:pointer;width:3em;'+
                                    'text-align:center;',
                                    'onclick':'toggleZoomMode("' + obj.id +
                                    '", "out")'},
                                    IMG({'src':'zoomout.gif'}, "Z-"))
                            )
                        ]
                    )
                );
    me.parentNode.appendChild(table);
    me.parentNode.removeChild(me);
}

// Zoom the image
function doZoom(event, obj) {
    var cursor = getPosition(event, obj);
    var newurl = generateNewUrl(cursor, obj);
    if (obj.src != newurl) loadImage(obj, newurl);
}


function registerGraph(id) {
    buildTables($(id));
}

