var Class={
    create:function(){
        return function(){
            this.__init__.apply(this,arguments);
        }
    }
}

postJSONDoc = function (url, postVars) {
        var req = getXMLHttpRequest();
        req.open("POST", url, true);
        req.setRequestHeader("Content-type", 
                             "application/x-www-form-urlencoded");
        var data = queryString(postVars);
        var d = sendXMLHttpRequest(req, data);
        return d.addCallback(evalJSONRequest);

}

var cancelWithTimeout = function (deferred, timeout) { 
    var canceller = callLater(timeout, function () { 
        // cancel the deferred after timeout seconds 
        deferred.cancel(); 
        //log("cancel load data")
    }); 
    return deferred.addCallback(function (res) { 
        // if the deferred fires successfully, cancel the timeout 
        canceller.cancel(); 
        return res; 
    }); 
};

function handle(delta) {
	if (delta < 0)
		/* something. */;
	else
		/* something. */;
}

function wheel(event){
	var delta = 0;
	if (!event) event = window.event;
	if (event.wheelDelta) {
		delta = event.wheelDelta/120; 
		if (window.opera) delta = -delta;
	} else if (event.detail) {
		delta = -event.detail/3;
	}
	if (delta)
		handle(delta);
       if (event.preventDefault)
           event.preventDefault();
       event.returnValue = false;
}

function checkValidId(path, input_id){
    var errmsg = $('errmsg');
    var input = $(input_id);
    var label = $(input_id+'_label');
    var new_id = escape(input.value);

    errmsg.innerHTML = "";
    Morph(input_id, {"style": {"color": "black"}});
    Morph(label.id, {"style": {"color": "white"}});
    
    d = callLater(0, doXHR, path+'/checkValidId', {queryString:{'id':new_id}});
    d.addCallback(function (r) { 
        if (r.responseText != 'True') {
            Morph(input_id, {"style": {"color": "red"}});
            Morph(label.id, {"style": {"color": "red"}});
            errmsg.innerHTML = r.responseText;
            shake(input);
            shake(label);
            shake(errmsg);
        }   
    });
}

function connectTextareas() {
    var resizeArea = function(area) {
        var vDims = getViewportDimensions();
        var vPos = getViewportPosition();
        var aDims = getElementDimensions(area);
        var aPos = getElementPosition(area);
        var rightedge_area = aDims.w + aPos.x;
        var rightedge_vp = vDims.w + vPos.x;
        aDims.w += rightedge_vp-rightedge_area-50;
        setElementDimensions(area, aDims);
    }
    connect(currentWindow(), 'onresize', function(e) {
        map(resizeArea, $$('textarea'));
    });
    map(resizeArea, $$('textarea'));
}


ImagePreloader = Class.create();
ImagePreloader.prototype = {
    __init__: function() {
        bindMethods(this);
        this.buffer = new Image(25, 25);
        this.queue = new Array();
        this.lock = new DeferredLock();
    },
    add: function(img) {
        this.queue.push(img);
        this.start();
    },
    start: function() {
        var d = this.lock.acquire();
        d.addCallback(this.next);
    },
    next: function() {
        var img = this.queue.pop();
        if (img) this.buffer.src = img;
        this.lock.release();
    }
}

