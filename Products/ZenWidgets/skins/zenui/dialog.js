
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

        this.parentElem = this.box.parentNode;
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
    show: function() {
        var dims = getViewportDimensions();
        var bdims = getElementDimensions(this.box);
        setElementDimensions(this.dimbg, getViewportDimensions());
        setElementPosition(this.box, {
            x:(dims.w/2)-(bdims.w/2),
            y:(dims.h/2)-(bdims.h/2)
        });
        this.moveBox('front');
        connect(this.dimbg, 'onclick', bind(this.hide, this));
        appear(this.dimbg, {duration:0.1, from:0.0, to:0.5});
        showElement(this.box);
    },
    hide: function() {
        fade(this.dimbg, {duration:0.1});
        hideElement(this.box);
        this.moveBox('back');
    }
}

        
