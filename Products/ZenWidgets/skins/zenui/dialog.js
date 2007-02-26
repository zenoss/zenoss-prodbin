var Class={
    create:function(){
        return function(){
            this.__init__.apply(this,arguments);
        }
    }
}

var Dialog = {};
Dialog.Box = Class.create();
Dialog.Box.prototype = {
    __init__: function(id) {
        this.makeDimBg();
        this.box = $(id);
        this.box.show = bind(this.show, this);
        this.box.hide = bind(this.hide, this);
        this.box.submit_form = bind(this.submit_form, this);
        this.parentElem = this.box.parentNode;
        log(this.parentElem);
        this.defaultContent = this.box.innerHTML
        setStyle(this.box, {
            'position':'absolute',
            'z-index':'3001',
            'display':'none'});
    },
    makeDimBg: function() {
        if($('dialog_dim_bg')) {
            this.dimbg = $('dialog_dim_bg');
        } else {
            this.dimbg = DIV({'id':'dialog_dim_bg'},null);
            setStyle(this.dimbg, {
                'position':'absolute',
                'top':'0',
                'left':'0',
                'z-index':'3000',
                'width':'100%',
                'background-color':'white',
                'display':'none'
            });
            insertSiblingNodesBefore(document.body.firstChild, this.dimbg);
        }
    },
    moveBox: function(dir) {
        this.box = removeElement(this.box);
        if(dir=='back') {
            this.box = this.dimbg.parentNode.appendChild(this.box);
        } else {
            this.box = this.dimbg.parentNode.insertBefore(this.box, this.dimbg);
        }
    },
    show: function(url) {
        if (url) this.fetch(url);
        var dims = getViewportDimensions();
        setStyle(this.box, {'z-index':'1','display':'block'});
        var bdims = getElementDimensions(this.box);
        setStyle(this.box, {'z-index':'3001','display':'none'});
        setElementDimensions(this.dimbg, getViewportDimensions());
        setElementPosition(this.box, {
            x:(dims.w/2)-(bdims.w/2),
            y:(dims.h/2)-(bdims.h/2)
        });
        this.moveBox('front');
        //connect(this.dimbg, 'onclick', bind(this.hide, this));
        appear(this.dimbg, {duration:0.1, from:0.0, to:0.5});
        showElement(this.box);
    },
    hide: function() {
        fade(this.dimbg, {duration:0.1});
        this.box.innerHTML = this.defaultContent;
        hideElement(this.box);
        this.moveBox('back');
    },
    fetch: function(url) {
        var d = doSimpleXMLHttpRequest(url);
        d.addCallback(this.fill);
    },
    fill: function(request) {
        $('dialog_content').innerHTML = request.responseText;
    },
    submit_form: function(formname, action) {
        var f = document.forms[formname];
        setStyle(this.box, {'z-index':'-1'});
        this.box = removeElement(this.box);
        f.action = action;
        f.appendChild(this.box);
        return true;
    }
}

