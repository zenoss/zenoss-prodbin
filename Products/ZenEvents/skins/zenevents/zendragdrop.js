var Class = {
    create:function(){
        return function(){
            this.__init__.apply(this,arguments);
        }
    }
}

Function.prototype.bind = function(obj){
    var method=this;
    temp=function(){
        return method.apply(obj,arguments);
    }
        return temp;
}

var nodeHash = function(node) {
    var a = node.attributes;
    var r = {};
    for (i=0;i<a.length;i++) {
        if (isEmpty(a[i].nodeValue)) continue;
        r[a[i].localName] = a[i].nodeValue;
    }
    return r;
}

var getSelected = function(node) {
    var options = iter(node.getElementsByTagName('option'));
    var isSel = function(obj) { return obj.selected }
    var r = ifilter(isSel, options);
    return list(r);
}

ZenHiddenSelect = Class.create();
ZenHiddenSelect.prototype = {
    __init__: function(obj) {
        this.obj = obj;
    },
    values: function() {
        return this.obj.value.split('\n');
    },
    update: function(vals) {
        var opts = vals.getElementsByTagName('li');
        var getText = function(li) {
            return li.innerHTML
        }
        var strs = map(getText, opts);
        this.obj.innerHTML = strs.join('\n');
    },
    toUL: function() {
        var options = this.values();
        var atts = nodeHash(this.obj);
        atts['class'] = 'sortable_list';
        var ul = UL(atts,
                    map(this.toLI, options));
        return ul;
    },
    toLI: function(val) {
        var atts = {'id':'li_' + val,'class':'sortable_item'};
        var li = LI(atts, val);
        return li;
    }
}

ZenULSelect = Class.create();
ZenULSelect.prototype = {
    __init__: function(obj) {
        this.obj = obj;
        this.ul = obj.toUL();
        insertSiblingNodesAfter(this.obj.obj, this.ul);
        this.obj.obj.style.height="0";
        this.obj.obj.style.border="0";
        this.obj.obj.style.padding="0";
        this.obj.obj.style.visiblity = 'hidden';
            }
}

ZenDragDropList = Class.create();
ZenDragDropList.prototype = {
    // Pass a textarea of selected and a ul of possibles
    __init__: function(ta, ul) { 
        ta = $(ta);
        ul = $(ul);
        this.hiddenselect = new ZenHiddenSelect(ta);
        this.fields = ul;
        var s = new ZenULSelect(this.hiddenselect); 
        this.sortable1 = MochiKit.Sortable.Sortable.create(s.ul,
        {onUpdate:s.obj.update.bind(s.obj),
         dropOnEmpty:true,
         containment:[s.ul, this.fields],
         constraint:false});
        this.sortable2 = MochiKit.Sortable.Sortable.create(this.fields,
        {dropOnEmpty:true,
         containment:[s.ul, this.fields],
         constraint:false});

    }
}

