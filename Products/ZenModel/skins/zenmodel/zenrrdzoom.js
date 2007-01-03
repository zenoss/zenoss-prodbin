/*
#####################################################
#
# ZenRRDZoom - Pan & Zoom for Zenoss RRDTool graphs
# 2006-12-29
#
#####################################################
*/


var zoom_factor = 1.5;
var pan_factor = 3; // Fraction of graph to move
var drange_re = /&drange=([0-9]*)/;
var end_re = /--end%3Dnow-([0-9]*)s%7C--start%3Dend-[0-9]*s%7C/;
var width_re  = /--width%3D([0-9]*)%7C/;
var height_re = /--height%3D([0-9]*)%7C/;
var start_re = /--start%3Dend-([0-9]*)s%7C/;
var comment_re = /COMMENT%3A.*?%7C/;


var graph_list = Array();
var linked_mode = 0;

_insertBefore = function(search, insert, source) {
    return source.replace(search, insert+search);
}

// Pull relevant info from the image source URL
function parseUrl(href) {
    var drange = Number(drange_re.exec(href)[1]);
    var width = Number(width_re.exec(href)[1]);
    var end = Number(end_re.exec(href)?end_re.exec(href)[1]:0);
    var start = Number(start_re.exec(href)?start_re.exec(href)[1]:0);
    return [drange, width, end, start];
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

insertComment = function(url, comment) {
    comment = comment.replace(/:/g, '\\:'); // escape colons
    comment = escape("COMMENT:" + comment + "\\c|");
    return url.match(comment_re)?url.replace(comment_re, comment):
        _insertBefore("DEF", comment, url);
}

createDateComment = function(url) {
    dates = updateDateRange(url);
    comment = dates[0] + "\\t\\t\\t\\t to \\t\\t\\t" + dates[1];
    newurl = insertComment(url, comment);
    return newurl;
}


// Calculate the new image parameters and generate the source URL
function generateNewUrl(cursor, obj) {
    var x = cursor.x - 67;
    var parsed = parseUrl(obj.src);
    var drange = parsed[0];
    var width = parsed[1];
    if ( x < 0 || x > width ) return obj.src ;
    var end = parsed[2];
    var secs = Math.round(drange);
    var newdrange = Math.round(drange/obj.zoom_factor);
    var newsecs = Math.round(newdrange);
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
    newurl = createDateComment(newurl);
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
    var myobj = $(id);
    objlist = linked_mode?graph_list:[myobj];
    for (i=0;i<objlist.length;i++) {
        obj = objlist[i];
        if (dir == 'out') {
            $(obj.id + '_zin').style.backgroundColor = 'transparent';
            $(obj.id + '_zout').style.backgroundColor = 'grey';
            if (obj.zoom_factor > 1) obj.zoom_factor=1/obj.zoom_factor;
        } else {
            $(obj.id + '_zin').style.backgroundColor = 'grey';
            $(obj.id + '_zout').style.backgroundColor = 'transparent';
            if (obj.zoom_factor < 1) obj.zoom_factor=1/obj.zoom_factor;
        }
    }
    
}

function updateDateRange(href) {
    parts = parseUrl(href);
    var end = parts[2];
    var start = parts[3] + end;
    start = start * 1000;
    end = end * 1000;
    endDate = new Date();
    startDate = new Date();
    endDate.setMilliseconds(endDate.getMilliseconds() - end);
    startDate.setMilliseconds(startDate.getMilliseconds() - start);
    return [toISOTimestamp(startDate), toISOTimestamp(endDate)];
}


// Check the source URL for valid data and display the image if so
function loadImage(obj, url) {

    testurl = url.replace(height_re,'--only-graph%7C--height%3D10%7C');
    var x = doSimpleXMLHttpRequest(testurl);

    x.addCallback(
        function(req) {
            if (req.responseText) {
              obj.src = url;
              updateDateRange(obj);
            }
        }
    );
}

// Pan the graph in either direction
function panGraph(direction, id) {
    myobj = $(id);
    objlist = linked_mode?graph_list:[myobj];
    for (i=0;i<objlist.length;i++) {
        var obj = objlist[i];
        var href = parseUrl(obj.src);
        var tenth = Math.round(href[0]/(pan_factor));
        var secs = Math.round(href[0]);
        if (direction == "right") {
            newend = href[2] - tenth;
        } else {
            newend = href[2] + tenth;
        };
        //alert(String(tenth) + " " + String(newend) + " " + String(href[2]));
        nepart = '--end%3Dnow-' + String(newend) + 's%7C';
        nepart += '--start%3Dend-' + String(secs) + 's%7C';
        if (obj.src.match(end_re)) { 
            newurl = obj.src.replace(end_re, nepart);
        } else {
            newurl = obj.src.replace('--height', nepart + '--height');
        };
        newurl = createDateComment(newurl);
        loadImage(obj, newurl);
    }
}
    
function gridUrl(drange) {
    var grid = String(Math.round( drange/21 + 1 ));
    var maj  = String(Math.round( drange/4 + 1 ));
    var lab  = String(Math.round( drange/4 + 1 ));
    var url = "--x-grid%3DSECOND%3A" + grid + // Grid lines every x secs
              "%3ASECOND%3A" + maj + // Major grid lines every x secs
              "%3ASECOND%3A" + lab + // Labels every x secs
              "%3A0%3A%25x%20%25X%7C";
    return url
}


// Replace the image with the table structure and buttons
function buildTables(obj) {
    var _height = function(thing){ 
        return String(thing.height + 14)+'px';
    };
    var me = $(obj.id);
    var newme = me.cloneNode(true);
    var drange = Number(drange_re.exec(me.src)[1]);
    var x = String(Math.round(drange));
    var end = '--end%3Dnow-0s%7C--start%3Dend-' + x + 's%7C';
    newurl = obj.src.match(end_re)?obj.src.replace(end_re, end):
                obj.src.replace('--height', end + '--height');
    dates = updateDateRange(newurl);
    comment = dates[0] + "\\t\\t\\t\\t to \\t\\t\\t" + dates[1];
    newurl = insertComment(newurl, comment);
    newme.src = newurl;
    newme.onload = null;
    newme.zoom_factor = zoom_factor;
    newme.style.cursor = 'crosshair';
    var table = TABLE({'id':obj.id + '_table'},
                TBODY(
                        {'id':obj.id + '_tbody'},
                        [
                            /*
                            TR(null,
                                TD({'colspan':'4',
                                    'style':'padding-left:4em;'},
                                [
                                SPAN({'style':'font-weight:bold;color:darkgrey;'},
                                    "Graph Range:"),
                                INPUT({
                                    'id':obj.id + '_start',
                                    'class':'tablevalues',
                                    'style':'border:1px solid transparent;' +
                                            'margin-left:1em;width:15em;' +
                                            'color:indianred;font-weight:bold'
                                },
                                   null ),
                                SPAN({'style':'font-weight:bold;color:darkgrey;'},
                                    "to"),
                                INPUT({
                                      'id':obj.id + '_end',
                                      'class':'tablevalues',
                                      'style':'border:1px solid transparent;' +
                                              'margin-left:1em;width:15em;' +
                                              'color:indianred;font-weight:bold'},
                                       null)
                                ]
                                )
                                )
                            ,*/
                            TR(null,
                                [
                                TD(
                                    {'rowspan':'2',
                                     'style':'background-color:lightgrey;',
                                     'onclick':'panGraph("left","'+obj.id+'")'},
                                    INPUT({'type':'button',
                                           'id':obj.id + '_panl',
                                    'style':'height:'+_height(me)+';border:1px solid grey;' + 
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
                                           'id':obj.id + '_panr',
                                    'style':'height:'+_height(me)+';border:1px solid grey;'+
                                    'cursor:pointer',
                                           'value':'>',
                                           'onfocus':'this.blur();'},
                                    ">")
                                ),
                                TD({'id' : obj.id + '_zin',
                                    'style':'cursor:pointer;background-color:grey;'+
                                    'width:3em;text-align:center;' +
                                    'border:1px solid grey;',
                                    'onclick':'toggleZoomMode("' + obj.id +
                                    '", "in")'},
                                    IMG({'src':'zoomin.gif'}, "Z+")
                                )
                                ]
                            ),
                            TR(null,
                                TD({'id':obj.id + '_zout',
                                    'style':'cursor:pointer;width:3em;'+
                                    'text-align:center;' +
                                    'border:1px solid grey;',
                                    'onclick':'toggleZoomMode("' + obj.id +
                                    '", "out")'},
                                    IMG({'src':'zoomout.gif'}, "Z-"))
                            )
                        ]
                    )
                );
    me.parentNode.appendChild(table);
    me.parentNode.removeChild(me);
    return $(obj.id);
}

// Zoom the image
function doZoom(event, myobj) {
    objlist = linked_mode?graph_list:[myobj];
    for (i=0;i<objlist.length;i++) {
        obj = objlist[i];
        var cursor = getPosition(event, obj);
        var newurl = generateNewUrl(cursor, obj);
        if (obj.src != newurl) loadImage(obj, newurl);
    }
}

function linkGraphs(bool) {
    linked_mode = bool;
    if (bool) { toggleZoomMode(graph_list[0], 'in'); 
    resetGraphs($('drange_select').value);}
}

function registerGraph(id) {
    var newobj = buildTables($(id));
    graph_list[graph_list.length] = newobj;
}

function resetGraphs(drange) {
    var objlist = graph_list;
    for (i=0;i<objlist.length;i++) {
        var obj = objlist[i];
        var x = String(drange);
        var end = '--end%3Dnow-0s%7C--start%3Dend-' + x + 's%7C';
        var newurl = obj.src.match(end_re)?obj.src.replace(end_re, end):
                    obj.src.replace('--height', end + '--height');
        newurl = newurl.replace(drange_re, '&drange=' + x);
        newurl = createDateComment(newurl);
        loadImage(obj, newurl);
    }
}
