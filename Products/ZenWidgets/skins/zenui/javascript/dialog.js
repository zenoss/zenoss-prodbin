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
        bindMethods(this);
        this.makeDimBg();
        this.box = $(id);
        this.framework = DIV(
            {'class':'dialog_container'},
            [
            //top row
            DIV({'class':'dbox_tl'},
             [ DIV({'class':'dbox_tr'},
               [ DIV({'class':'dbox_tc'}, null)])]),
            //middle row
            DIV({'class':'dbox_ml'},
             [ DIV({'class':'dbox_mr'},
               [ DIV({'class':'dbox_mc',
                      'id':'dialog_content'}, null)])]),
            //bottom row
            DIV({'class':'dbox_bl'},
             [ DIV({'class':'dbox_br'},
               [ DIV({'class':'dbox_bc'}, null)])])
            ]);
        insertSiblingNodesBefore(this.box, this.framework);
        setStyle(this.framework, {'position':'absolute'});
        removeElement(this.box);
        appendChildNodes($('dialog_content'), this.box);
        this.box.show = bind(this.show, this);
        this.box.hide = bind(this.hide, this);
        this.box.submit_form = bind(this.submit_form, this);
        this.parentElem = this.box.parentNode;
        this.defaultContent = this.box.innerHTML
        setStyle(this.box, {
            'position':'absolute',
            'z-index':'5001',
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
                'z-index':'5000',
                'width':'100%',
                'background-color':'white',
                'display':'none'
            });
            insertSiblingNodesBefore(document.body.firstChild, this.dimbg);
        }
    },
    moveBox: function(dir) {
        this.framework = removeElement(this.framework);
        if(dir=='back') {
            this.framework = this.dimbg.parentNode.appendChild(this.framework);
        } else {
            this.framework = this.dimbg.parentNode.insertBefore(
                this.framework, this.dimbg);
        }
    },
    lock: new DeferredLock(),
    show: function(form, url) {
        var d1 = this.lock.acquire();
        d1.addCallback(bind(function() {
            if (url) this.fetch(url);
        }, this));7
        this.form = form;
        var dims = getViewportDimensions();
        var vPos = getViewportPosition();
        setStyle(this.framework, {'z-index':'1','display':'block'});
        var bdims = getElementDimensions(this.framework);
        setStyle(this.framework, {'z-index':'10002','display':'none'});
        map(function(menu) {setStyle(menu, {'z-index':'3000'})}, 
            concat($$('.menu'), $$('.littlemenu'), $$('#messageSlot')));
        setElementDimensions(this.dimbg, getViewportDimensions());
        setElementPosition(this.dimbg, getViewportPosition());
        setStyle(this.box, {'position':'relative'});
        setElementPosition(this.framework, {
            x:((dims.w+vPos.x)/2)-(bdims.w/2),
            y:((dims.h/2)+vPos.y)-(bdims.h/2)
        });
        this.moveBox('front');
        connect('dialog_close','onclick',function(){$('dialog').hide()});
        var d2 = this.lock.acquire(); 
        d2.addCallback(bind(function(r) {
            removeElementAutoCompletes();
            try {
                connect('new_id','onkeyup', doLiveCheck);
            } catch(e) { noop(); }
            if (this.lock.locked) this.lock.release();
        }, this));
        appear(this.dimbg, {duration:0.1, from:0.0, to:0.7});
        showElement(this.box);
        showElement(this.framework);
    },
    hide: function() {
        fade(this.dimbg, {duration:0.1});
        this.box.innerHTML = this.defaultContent;
        hideElement(this.framework);
        this.moveBox('back');
        if (this.lock.locked) this.lock.release();
    },
    fetch: function(url) {
        var d = doSimpleXMLHttpRequest(url);
        d.addCallback(bind(this.fill, this));
    },
    fill: function(request) {
        $('dialog_innercontent').innerHTML = request.responseText;
        var els = findChildElements($('dialog_innercontent'), ['new_id','select','input','dialog_submit']);
        els = filter(function(x){return x.type!='button'&&x.type!='hidden'}, els);
        var first = els[0];
        first.focus();
        if (this.lock.locked) this.lock.release();
    },
    submit_form: function(action, formname) {
        var f = formname?document.forms[formname]:this.form
        setStyle(this.box, {'z-index':'-1'});
        this.box = removeElement(this.box);
        if (action != '') f.action = action;
        f.appendChild(this.box);
        return true;
    }
}

log("Dialog javascript loaded.")
