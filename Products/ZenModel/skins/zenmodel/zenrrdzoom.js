/*
#####################################################
#
# ZenRRDZoom - Pan & Zoom for Zenoss RRDTool graphs
# 2006-12-29
#
#####################################################
*/

if (typeof(isie)=='undefined') var isie = navigator.userAgent.indexOf('MSIE') != -1;
var zoom_factor = 1.5;
var pan_factor = 3; // Fraction of graph to move
var drange_re = /&drange=([0-9]*)/;
var end_re = /--end%3Dnow-([0-9]*)s%7C/;
var width_re  = /--width%3D([0-9]*)%7C/;
var height_re = /--height%3D([0-9]*)%7C/;
var start_re = /--start%3Dend-([0-9]*)s%7C/;
var comment_re = /COMMENT%3A.*?%5Cc%7C/;
var dashes_re = /(--.*?%7C)([^\-])/;

var linked_mode = 1;
var ZenQueue;

var Class={
    create:function(){
        return function(){
            this.__init__.apply(this,arguments);
        }
    }
}

Function.prototype.bind = function(obj) {
    var method = this;
    temp = function() {
        return method.apply(obj, arguments);
        };
    return temp;
}
var table = function(obj, newme) {
    _height = function(o) { return String(o.height + 14)+'px'; };
    return TABLE({'id':obj.id + '_table'},
    TBODY({'id':obj.id + '_tbody'},
    [TR(null,[TD({'rowspan':'2','style':'background-color:lightgrey;',
    },INPUT({'type':'button',
    'id':obj.id + '_panl','style':'height:'+_height(obj)+';border:1px solid grey;' + 
    'cursor:pointer','value':'<', 'onfocus':'this.blur();'},"<")),
    TD({'rowspan':'2'},newme),TD({'rowspan':'2','style':'background-color:lightgrey;',
    },INPUT({'type':'button',
    'id':obj.id + '_panr','style':'height:'+_height(obj)+';border:1px solid grey;'+
    'cursor:pointer','value':'>','onfocus':'this.blur();'},">")),
    TD({'id' : obj.id + '_zin','style':'cursor:pointer;background-color:grey;'+
    'width:3em;text-align:center;' +'border:1px solid grey;',},
    IMG({'src':'zoomin.gif'}, "Z+"))]),TR(null,TD({'id':obj.id + '_zout',
    'style':'cursor:pointer;width:3em;'+'text-align:center;'+'border:1px solid grey;',},
    IMG({'src':'zoomout.gif'}, "Z-")))]));
}

ZenRRDGraph = Class.create();
ZenRRDGraph.prototype = {

    zoom_factor: 1.5,
    pan_factor: 3,

    __init__: function(obj) {
        this.obj = obj;
        this.updateFromUrl();
        this.setDates();
        this.buildTables();
        this.registerListeners();
    },

    updateFromUrl: function() {
        var href = this.obj.src;
        this.drange = Number(drange_re.exec(href)[1]);
        this.width  = Number(width_re.exec(href)[1]);
        this.end    = Number(end_re.exec(href)?end_re.exec(href)[1]:0);
        this.start  = Number(start_re.exec(href)?start_re.exec(href)[1]
                             :this.drange);
    },

    imgPos: function() {
        obj = this.obj;
        var curleft = curtop = 0;
        if (obj.offsetParent) {
            curleft = obj.offsetLeft;
            curtop = obj.offsetTop;
            while (obj=obj.offsetParent) {
                curleft += obj.offsetLeft;
                curtop += obj.offsetTop;
            }
        }
        var element = {x:curleft,y:curtop};
        return element;
    },

    setxpos: function(e) {
        e = e || window.event;
        var cursor = {x:0,y:0};
        var element = this.imgPos();
        if (e.pageX || e.pageY) {
            cursor.x = e.pageX;
            cursor.y = e.pageY;
        } else {
            var de = document.documentElement;
            var b = document.body;
            cursor.x = e.mouse().client.x +
                (de.scrollLeft||b.scrollLeft)-(de.clientLeft||0);
            cursor.y = e.mouse().client.y +
                (de.scrollTop||b.scrollTop)-(de.clientTop||0);
        }
        return cursor.x - element.x;
    },

    startString : function(s) {
        s = s || this.start;
        var x = "--start=end-" + String(s) + "s|";
        return escape(x);
    },

    endString : function(e) {
        e = e || this.end;
        var x = "--end=now-" + String(e) + "s|";
        return escape(x);
    },

    setZoom : function(e) {
        var x = this.setxpos(e)-67;
        var href = this.obj.src;
        if (x<0||x>this.width){return href};
        var drange = Math.round(this.drange/this.zoom_factor);
        var delta = ((this.width/2)-x)*(this.drange/this.width) +
                (this.drange-drange)/2;
        var end = Math.round(this.end+delta>=0?this.end+delta:0);
        this.drange = drange;
        this.start = drange;
        this.end = end;
        return [this.drange, this.start, this.end];
    },

    pan_left : function() {
        var delta = Math.round(this.drange/this.pan_factor);
        this.end = this.end+delta>0?this.end+delta:0;
        this.setDates();
        this.setComment();
        this.setUrl();
        this.loadImage();
    },

    pan_right : function() {
        var delta = Math.round(this.drange/this.pan_factor);
        this.end = this.end-delta>0?this.end-delta:0;
        this.setDates();
        this.setComment();
        this.setUrl();
        this.loadImage();
    },

    setDates : function() {
        var sD, eD;
        sD=new Date(); eD=new Date();
        eD.setMilliseconds(eD.getMilliseconds()-this.end*1000);
        sD.setMilliseconds(sD.getMilliseconds()-(this.start+this.end)*1000);
        this.sDate=toISOTimestamp(sD);
        this.eDate=toISOTimestamp(eD);
    },

    setComment : function(comment) {
        var com_ctr = "\\t\\t\\t\\t to \\t\\t\\t";
        comment = comment || this.sDate + com_ctr + this.eDate;
        comment = comment.replace(/:/g, '\\:');
        this.comment = escape("COMMENT:" + comment + "\\c|");
    },
    
    setUrl : function() {
        var newurl, dashes;
        var href = this.obj.src;
        var start_url = this.startString();
        var end_url = this.endString();
        if ( href.match(end_re) ) {
            newurl = href.replace(end_re, end_url);
            newurl = newurl.replace(start_re, start_url);
        } else {
            newurl = href.replace("--height", start_url+end_url+'--height');
        };
        newurl = newurl.replace(drange_re, "&drange=" + String(this.drange));
        this.setDates();
        this.setComment();
        dashes = dashes_re.exec(newurl);
        comurl = newurl.replace(dashes[1], dashes[1] + this.comment);
        newurl = newurl.match(comment_re)?
                 newurl.replace(comment_re, this.comment):
                 comurl;
        this.url = newurl;
    },

    doZoom : function(e) {
        this.setZoom(e);
        this.setDates();
        this.setComment();
        this.setUrl();
        this.loadImage();
    },
    
    buildTables : function() {
        this.setComment();
        this.setUrl();
        var newme = this.obj.cloneNode(false);
        newme.src = this.url;
        newme.style.cursor = 'crosshair';
        var t = table(this.obj, newme);
        this.obj.parentNode.appendChild(t);
        this.obj.parentNode.removeChild(this.obj);
        this.obj = newme;
        this.zin = $(this.obj.id + '_zin');
        this.zout = $(this.obj.id + '_zout');
        this.panl = $(this.obj.id + '_panl');
        this.panr = $(this.obj.id + '_panr');
    },

    zoom_in : function() {
        this.zin.style.backgroundColor = 'grey';
        this.zout.style.backgroundColor = 'transparent';
        if (this.zoom_factor < 1) this.zoom_factor=1/this.zoom_factor;
    },

    zoom_out: function() {
        this.zin.style.backgroundColor = 'transparent';
        this.zout.style.backgroundColor = 'grey';
        if (this.zoom_factor > 1) this.zoom_factor=1/this.zoom_factor;
    },

    loadImage : function() {
        this.buffer = new Image();
        var obj = this.obj;
        var onSuccess = function(e) {
            this.obj.src = this.url;
            disconnectAll(this.buffer);
            delete this.buffer;
        };
        var x = connect(this.buffer, 'onload', onSuccess.bind(this));
        this.buffer.src = this.url;
    },

    registerListeners : function() {
        if (!this.listeners) this.listeners=[];
        this.clearListeners();
        var l = this.listeners;
        l[0] = connect(this.obj, 'onclick', this.doZoom.bind(this));
        l[1] = connect(this.zin, 'onclick', this.zoom_in.bind(this));
        l[2] = connect(this.zout,'onclick', this.zoom_out.bind(this));
        l[3] = connect(this.panl,'onclick', this.pan_left.bind(this));
        l[4] = connect(this.panr,'onclick', this.pan_right.bind(this));
    },

    clearListeners : function() {
        for (l in this.listeners) {
            disconnect(this.listeners[l]);
        }
    }

}


ZenGraphQueue = Class.create();

ZenGraphQueue.prototype = {
    graphs : [],
    __init__: function(graphs) {
        for (g in graphs) {
            graph = graphs[g];
            this.add.bind(this)(graph);
        }
    },
    add: function(graph) {
        this.graphs[this.graphs.length] = graph;
        this.registerListeners(graph);
    },
    reset: function(graph) {
        for (g in this.graphs) {
            this.registerListeners(this.graphs[g]);
        }
    },
    registerListeners: function(graph) {
        if (!graph.listeners) graph.listeners=[];
        var l = graph.listeners;
        graph.clearListeners();
        l[0] = connect(graph.obj, 'onclick', this.doZoom.bind(this));
        l[1] = connect(graph.zin, 'onclick', this.zoom_in.bind(this));
        l[2] = connect(graph.zout,'onclick', this.zoom_out.bind(this));
        l[3] = connect(graph.panl,'onclick', this.pan_left.bind(this));
        l[4] = connect(graph.panr,'onclick', this.pan_right.bind(this));
    },
    remove: function(graph) {
        graph.registerListeners();
    },
    removeAll: function() {
        for (g in this.graphs) {
            this.remove(this.graphs[g]);
        }
    },
    updateAll: function(vars) {
        var end = vars[2];
        var start = vars[1];
        var drange = vars[0];
        for (g in this.graphs) {
            x = this.graphs[g];
            x.end = end;
            x.start = start;
            x.drange = drange;
            x.setDates();
            x.setComment();
            x.setUrl();
            x.loadImage();
        }
    },
    doZoom: function(e) {
        var g = this.find_graph(e.target());
        var graph = this.graphs[g];
        var vars = graph.setZoom.bind(graph)(e);
        this.updateAll(vars);
    },
    zoom_in: function(e) {
        for (g in this.graphs) {
            graph = this.graphs[g];
            graph.zoom_in.bind(graph)(e);
        }
    },
    zoom_out: function(e) {
        for (g in this.graphs) {
            graph = this.graphs[g];
            graph.zoom_out.bind(graph)(e);
        }
    },
    pan_left: function(e) {
        for (g in this.graphs) {
            graph = this.graphs[g];
            graph.pan_left.bind(graph)(e);
        }
    },
    pan_right: function(e) {
        for (g in this.graphs) {
            graph = this.graphs[g];
            graph.pan_right.bind(graph)(e);
        }
    },
    find_graph: function(obj) {
        for (g in this.graphs) {
            if (this.graphs[g].obj==obj) return g;
        }
    }
};

function linkGraphs(bool) {
    linked_mode = bool;
    if (!linked_mode) {
        ZenQueue.removeAll();
    } else {
        resetGraphs($('drange_select').value);
        ZenQueue.reset();
    }
}

function resetGraphs(drange) {
    if (!isie) {
        var end = 0;
        var start = drange;
        var drange = drange;
        ZenQueue.updateAll([drange, start, end]);
    } else {
        document.href = document.href;
    }
}

function registerGraph(id) {
    var graph = new ZenRRDGraph($(id));
}

function zenRRDInit() {
    ZenQueue = new ZenGraphQueue();
    for (graphid in ZenGraphs) {  // ZenGraphs is set in the template
        graph = new ZenRRDGraph($(ZenGraphs[graphid]));
        ZenQueue.add(graph);
    }
}

addLoadEvent(zenRRDInit);
