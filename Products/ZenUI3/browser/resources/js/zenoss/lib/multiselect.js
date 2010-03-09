

/*!
 * Ext JS Library 3.1.1
 * Copyright(c) 2006-2010 Ext JS, LLC
 * licensing@extjs.com
 * http://www.extjs.com/license
 */
Ext.ns('Ext.ux.form');

/**
 * @class Ext.ux.form.MultiSelect
 * @extends Ext.form.Field
 * A control that allows selection and form submission of multiple list items.
 *
 *  @history
 *    2008-06-19 bpm Original code contributed by Toby Stuart (with contributions from Robert Williams)
 *    2008-06-19 bpm Docs and demo code clean up
 *
 * @constructor
 * Create a new MultiSelect
 * @param {Object} config Configuration options
 * @xtype multiselect
 */
Ext.ux.form.MultiSelect = Ext.extend(Ext.form.Field,  {
    /**
     * @cfg {String} legend Wraps the object with a fieldset and specified legend.
     */
    /**
     * @cfg {Ext.ListView} view The {@link Ext.ListView} used to render the multiselect list.
     */
    /**
     * @cfg {String/Array} dragGroup The ddgroup name(s) for the MultiSelect DragZone (defaults to undefined).
     */
    /**
     * @cfg {String/Array} dropGroup The ddgroup name(s) for the MultiSelect DropZone (defaults to undefined).
     */
    /**
     * @cfg {Boolean} ddReorder Whether the items in the MultiSelect list are drag/drop reorderable (defaults to false).
     */
    ddReorder:false,
    /**
     * @cfg {Object/Array} tbar The top toolbar of the control. This can be a {@link Ext.Toolbar} object, a
     * toolbar config, or an array of buttons/button configs to be added to the toolbar.
     */
    /**
     * @cfg {String} appendOnly True if the list should only allow append drops when drag/drop is enabled
     * (use for lists which are sorted, defaults to false).
     */
    appendOnly:false,
    /**
     * @cfg {Number} width Width in pixels of the control (defaults to 100).
     */
    width:100,
    /**
     * @cfg {Number} height Height in pixels of the control (defaults to 100).
     */
    height:100,
    /**
     * @cfg {String/Number} displayField Name/Index of the desired display field in the dataset (defaults to 0).
     */
    displayField:0,
    /**
     * @cfg {String/Number} valueField Name/Index of the desired value field in the dataset (defaults to 1).
     */
    valueField:1,
    /**
     * @cfg {Boolean} allowBlank False to require at least one item in the list to be selected, true to allow no
     * selection (defaults to true).
     */
    allowBlank:true,
    /**
     * @cfg {Number} minSelections Minimum number of selections allowed (defaults to 0).
     */
    minSelections:0,
    /**
     * @cfg {Number} maxSelections Maximum number of selections allowed (defaults to Number.MAX_VALUE).
     */
    maxSelections:Number.MAX_VALUE,
    /**
     * @cfg {String} blankText Default text displayed when the control contains no items (defaults to the same value as
     * {@link Ext.form.TextField#blankText}.
     */
    blankText:Ext.form.TextField.prototype.blankText,
    /**
     * @cfg {String} minSelectionsText Validation message displayed when {@link #minSelections} is not met (defaults to 'Minimum {0}
     * item(s) required').  The {0} token will be replaced by the value of {@link #minSelections}.
     */
    minSelectionsText:'Minimum {0} item(s) required',
    /**
     * @cfg {String} maxSelectionsText Validation message displayed when {@link #maxSelections} is not met (defaults to 'Maximum {0}
     * item(s) allowed').  The {0} token will be replaced by the value of {@link #maxSelections}.
     */
    maxSelectionsText:'Maximum {0} item(s) allowed',
    /**
     * @cfg {String} delimiter The string used to delimit between items when set or returned as a string of values
     * (defaults to ',').
     */
    delimiter:',',
    /**
     * @cfg {Ext.data.Store/Array} store The data source to which this MultiSelect is bound (defaults to <tt>undefined</tt>).
     * Acceptable values for this property are:
     * <div class="mdetail-params"><ul>
     * <li><b>any {@link Ext.data.Store Store} subclass</b></li>
     * <li><b>an Array</b> : Arrays will be converted to a {@link Ext.data.ArrayStore} internally.
     * <div class="mdetail-params"><ul>
     * <li><b>1-dimensional array</b> : (e.g., <tt>['Foo','Bar']</tt>)<div class="sub-desc">
     * A 1-dimensional array will automatically be expanded (each array item will be the combo
     * {@link #valueField value} and {@link #displayField text})</div></li>
     * <li><b>2-dimensional array</b> : (e.g., <tt>[['f','Foo'],['b','Bar']]</tt>)<div class="sub-desc">
     * For a multi-dimensional array, the value in index 0 of each item will be assumed to be the combo
     * {@link #valueField value}, while the value at index 1 is assumed to be the combo {@link #displayField text}.
     * </div></li></ul></div></li></ul></div>
     */

    // private
    defaultAutoCreate : {tag: "div"},

    // private
    initComponent: function(){
        Ext.ux.form.MultiSelect.superclass.initComponent.call(this);

        if(Ext.isArray(this.store)){
            if (Ext.isArray(this.store[0])){
                this.store = new Ext.data.ArrayStore({
                    fields: ['value','text'],
                    data: this.store
                });
                this.valueField = 'value';
            }else{
                this.store = new Ext.data.ArrayStore({
                    fields: ['text'],
                    data: this.store,
                    expandData: true
                });
                this.valueField = 'text';
            }
            this.displayField = 'text';
        } else {
            this.store = Ext.StoreMgr.lookup(this.store);
        }

        this.addEvents({
            'dblclick' : true,
            'click' : true,
            'change' : true,
            'drop' : true
        });
    },

    // private
    onRender: function(ct, position){
        Ext.ux.form.MultiSelect.superclass.onRender.call(this, ct, position);

        var fs = this.fs = new Ext.form.FieldSet({
            renderTo: this.el,
            title: this.legend,
            height: this.height,
            width: this.width,
            style: "padding:0;",
            tbar: this.tbar
        });
        fs.body.addClass('ux-mselect');

        this.view = new Ext.ListView({
            multiSelect: true,
            store: this.store,
            columns: [{ header: 'Value', width: 1, dataIndex: this.displayField }],
            hideHeaders: true
        });

        fs.add(this.view);

        this.view.on('click', this.onViewClick, this);
        this.view.on('beforeclick', this.onViewBeforeClick, this);
        this.view.on('dblclick', this.onViewDblClick, this);

        this.hiddenName = this.name || Ext.id();
        var hiddenTag = { tag: "input", type: "hidden", value: "", name: this.hiddenName };
        this.hiddenField = this.el.createChild(hiddenTag);
        this.hiddenField.dom.disabled = this.hiddenName != this.name;
        fs.doLayout();
    },

    // private
    afterRender: function(){
        Ext.ux.form.MultiSelect.superclass.afterRender.call(this);

        if (this.ddReorder && !this.dragGroup && !this.dropGroup){
            this.dragGroup = this.dropGroup = 'MultiselectDD-' + Ext.id();
        }

        if (this.draggable || this.dragGroup){
            this.dragZone = new Ext.ux.form.MultiSelect.DragZone(this, {
                ddGroup: this.dragGroup
            });
        }
        if (this.droppable || this.dropGroup){
            this.dropZone = new Ext.ux.form.MultiSelect.DropZone(this, {
                ddGroup: this.dropGroup
            });
        }
    },

    // private
    onViewClick: function(vw, index, node, e) {
        this.fireEvent('change', this, this.getValue(), this.hiddenField.dom.value);
        this.hiddenField.dom.value = this.getValue();
        this.fireEvent('click', this, e);
        this.validate();
    },

    // private
    onViewBeforeClick: function(vw, index, node, e) {
        if (this.disabled) {return false;}
    },

    // private
    onViewDblClick : function(vw, index, node, e) {
        return this.fireEvent('dblclick', vw, index, node, e);
    },

    /**
     * Returns an array of data values for the selected items in the list. The values will be separated
     * by {@link #delimiter}.
     * @return {Array} value An array of string data values
     */
    getValue: function(valueField){
        var returnArray = [];
        var selectionsArray = this.view.getSelectedIndexes();
        if (selectionsArray.length == 0) {return '';}
        for (var i=0; i<selectionsArray.length; i++) {
            returnArray.push(this.store.getAt(selectionsArray[i]).get((valueField != null) ? valueField : this.valueField));
        }
        return returnArray.join(this.delimiter);
    },

    /**
     * Sets a delimited string (using {@link #delimiter}) or array of data values into the list.
     * @param {String/Array} values The values to set
     */
    setValue: function(values) {
        var index;
        var selections = [];
        this.view.clearSelections();
        this.hiddenField.dom.value = '';

        if (!values || (values == '')) { return; }

        if (!Ext.isArray(values)) { values = values.split(this.delimiter); }
        for (var i=0; i<values.length; i++) {
            index = this.view.store.indexOf(this.view.store.query(this.valueField,
                new RegExp('^' + values[i] + '$', "i")).itemAt(0));
            selections.push(index);
        }
        this.view.select(selections);
        this.hiddenField.dom.value = this.getValue();
        this.validate();
    },

    // inherit docs
    reset : function() {
        this.setValue('');
    },

    // inherit docs
    getRawValue: function(valueField) {
        var tmp = this.getValue(valueField);
        if (tmp.length) {
            tmp = tmp.split(this.delimiter);
        }
        else {
            tmp = [];
        }
        return tmp;
    },

    // inherit docs
    setRawValue: function(values){
        setValue(values);
    },

    // inherit docs
    validateValue : function(value){
        if (value.length < 1) { // if it has no value
             if (this.allowBlank) {
                 this.clearInvalid();
                 return true;
             } else {
                 this.markInvalid(this.blankText);
                 return false;
             }
        }
        if (value.length < this.minSelections) {
            this.markInvalid(String.format(this.minSelectionsText, this.minSelections));
            return false;
        }
        if (value.length > this.maxSelections) {
            this.markInvalid(String.format(this.maxSelectionsText, this.maxSelections));
            return false;
        }
        return true;
    },

    // inherit docs
    disable: function(){
        this.disabled = true;
        this.hiddenField.dom.disabled = true;
        this.fs.disable();
    },

    // inherit docs
    enable: function(){
        this.disabled = false;
        this.hiddenField.dom.disabled = false;
        this.fs.enable();
    },

    // inherit docs
    destroy: function(){
        Ext.destroy(this.fs, this.dragZone, this.dropZone);
        Ext.ux.form.MultiSelect.superclass.destroy.call(this);
    }
});


Ext.reg('multiselect', Ext.ux.form.MultiSelect);

//backwards compat
Ext.ux.Multiselect = Ext.ux.form.MultiSelect;


Ext.ux.form.MultiSelect.DragZone = function(ms, config){
    this.ms = ms;
    this.view = ms.view;
    var ddGroup = config.ddGroup || 'MultiselectDD';
    var dd;
    if (Ext.isArray(ddGroup)){
        dd = ddGroup.shift();
    } else {
        dd = ddGroup;
        ddGroup = null;
    }
    Ext.ux.form.MultiSelect.DragZone.superclass.constructor.call(this, this.ms.fs.body, { containerScroll: true, ddGroup: dd });
    this.setDraggable(ddGroup);
};

Ext.extend(Ext.ux.form.MultiSelect.DragZone, Ext.dd.DragZone, {
    onInitDrag : function(x, y){
        var el = Ext.get(this.dragData.ddel.cloneNode(true));
        this.proxy.update(el.dom);
        el.setWidth(el.child('em').getWidth());
        this.onStartDrag(x, y);
        return true;
    },

    // private
    collectSelection: function(data) {
        data.repairXY = Ext.fly(this.view.getSelectedNodes()[0]).getXY();
        var i = 0;
        this.view.store.each(function(rec){
            if (this.view.isSelected(i)) {
                var n = this.view.getNode(i);
                var dragNode = n.cloneNode(true);
                dragNode.id = Ext.id();
                data.ddel.appendChild(dragNode);
                data.records.push(this.view.store.getAt(i));
                data.viewNodes.push(n);
            }
            i++;
        }, this);
    },

    // override
    onEndDrag: function(data, e) {
        var d = Ext.get(this.dragData.ddel);
        if (d && d.hasClass("multi-proxy")) {
            d.remove();
        }
    },

    // override
    getDragData: function(e){
        var target = this.view.findItemFromChild(e.getTarget());
        if(target) {
            if (!this.view.isSelected(target) && !e.ctrlKey && !e.shiftKey) {
                this.view.select(target);
                this.ms.setValue(this.ms.getValue());
            }
            if (this.view.getSelectionCount() == 0 || e.ctrlKey || e.shiftKey) return false;
            var dragData = {
                sourceView: this.view,
                viewNodes: [],
                records: []
            };
            if (this.view.getSelectionCount() == 1) {
                var i = this.view.getSelectedIndexes()[0];
                var n = this.view.getNode(i);
                dragData.viewNodes.push(dragData.ddel = n);
                dragData.records.push(this.view.store.getAt(i));
                dragData.repairXY = Ext.fly(n).getXY();
            } else {
                dragData.ddel = document.createElement('div');
                dragData.ddel.className = 'multi-proxy';
                this.collectSelection(dragData);
            }
            return dragData;
        }
        return false;
    },

    // override the default repairXY.
    getRepairXY : function(e){
        return this.dragData.repairXY;
    },

    // private
    setDraggable: function(ddGroup){
        if (!ddGroup) return;
        if (Ext.isArray(ddGroup)) {
            Ext.each(ddGroup, this.setDraggable, this);
            return;
        }
        this.addToGroup(ddGroup);
    }
});

Ext.ux.form.MultiSelect.DropZone = function(ms, config){
    this.ms = ms;
    this.view = ms.view;
    var ddGroup = config.ddGroup || 'MultiselectDD';
    var dd;
    if (Ext.isArray(ddGroup)){
        dd = ddGroup.shift();
    } else {
        dd = ddGroup;
        ddGroup = null;
    }
    Ext.ux.form.MultiSelect.DropZone.superclass.constructor.call(this, this.ms.fs.body, { containerScroll: true, ddGroup: dd });
    this.setDroppable(ddGroup);
};

Ext.extend(Ext.ux.form.MultiSelect.DropZone, Ext.dd.DropZone, {
    /**
     * Part of the Ext.dd.DropZone interface. If no target node is found, the
     * whole Element becomes the target, and this causes the drop gesture to append.
     */
    getTargetFromEvent : function(e) {
        var target = e.getTarget();
        return target;
    },

    // private
    getDropPoint : function(e, n, dd){
        if (n == this.ms.fs.body.dom) { return "below"; }
        var t = Ext.lib.Dom.getY(n), b = t + n.offsetHeight;
        var c = t + (b - t) / 2;
        var y = Ext.lib.Event.getPageY(e);
        if(y <= c) {
            return "above";
        }else{
            return "below";
        }
    },

    // private
    isValidDropPoint: function(pt, n, data) {
        if (!data.viewNodes || (data.viewNodes.length != 1)) {
            return true;
        }
        var d = data.viewNodes[0];
        if (d == n) {
            return false;
        }
        if ((pt == "below") && (n.nextSibling == d)) {
            return false;
        }
        if ((pt == "above") && (n.previousSibling == d)) {
            return false;
        }
        return true;
    },

    // override
    onNodeEnter : function(n, dd, e, data){
        return false;
    },

    // override
    onNodeOver : function(n, dd, e, data){
        var dragElClass = this.dropNotAllowed;
        var pt = this.getDropPoint(e, n, dd);
        if (this.isValidDropPoint(pt, n, data)) {
            if (this.ms.appendOnly) {
                return "x-tree-drop-ok-below";
            }

            // set the insert point style on the target node
            if (pt) {
                var targetElClass;
                if (pt == "above"){
                    dragElClass = n.previousSibling ? "x-tree-drop-ok-between" : "x-tree-drop-ok-above";
                    targetElClass = "x-view-drag-insert-above";
                } else {
                    dragElClass = n.nextSibling ? "x-tree-drop-ok-between" : "x-tree-drop-ok-below";
                    targetElClass = "x-view-drag-insert-below";
                }
                if (this.lastInsertClass != targetElClass){
                    Ext.fly(n).replaceClass(this.lastInsertClass, targetElClass);
                    this.lastInsertClass = targetElClass;
                }
            }
        }
        return dragElClass;
    },

    // private
    onNodeOut : function(n, dd, e, data){
        this.removeDropIndicators(n);
    },

    // private
    onNodeDrop : function(n, dd, e, data){
        if (this.ms.fireEvent("drop", this, n, dd, e, data) === false) {
            return false;
        }
        var pt = this.getDropPoint(e, n, dd);
        if (n != this.ms.fs.body.dom)
            n = this.view.findItemFromChild(n);

        if(this.ms.appendOnly) {
            insertAt = this.view.store.getCount();
        } else {
            insertAt = n == this.ms.fs.body.dom ? this.view.store.getCount() - 1 : this.view.indexOf(n);
            if (pt == "below") {
                insertAt++;
            }
        }

        var dir = false;

        // Validate if dragging within the same MultiSelect
        if (data.sourceView == this.view) {
            // If the first element to be inserted below is the target node, remove it
            if (pt == "below") {
                if (data.viewNodes[0] == n) {
                    data.viewNodes.shift();
                }
            } else {  // If the last element to be inserted above is the target node, remove it
                if (data.viewNodes[data.viewNodes.length - 1] == n) {
                    data.viewNodes.pop();
                }
            }

            // Nothing to drop...
            if (!data.viewNodes.length) {
                return false;
            }

            // If we are moving DOWN, then because a store.remove() takes place first,
            // the insertAt must be decremented.
            if (insertAt > this.view.store.indexOf(data.records[0])) {
                dir = 'down';
                insertAt--;
            }
        }

        for (var i = 0; i < data.records.length; i++) {
            var r = data.records[i];
            if (data.sourceView) {
                data.sourceView.store.remove(r);
            }
            this.view.store.insert(dir == 'down' ? insertAt : insertAt++, r);
            var si = this.view.store.sortInfo;
            if(si){
                this.view.store.sort(si.field, si.direction);
            }
        }
        return true;
    },

    // private
    removeDropIndicators : function(n){
        if(n){
            Ext.fly(n).removeClass([
                "x-view-drag-insert-above",
                "x-view-drag-insert-left",
                "x-view-drag-insert-right",
                "x-view-drag-insert-below"]);
            this.lastInsertClass = "_noclass";
        }
    },

    // private
    setDroppable: function(ddGroup){
        if (!ddGroup) return;
        if (Ext.isArray(ddGroup)) {
            Ext.each(ddGroup, this.setDroppable, this);
            return;
        }
        this.addToGroup(ddGroup);
    }
});



/*!
 * Ext JS Library 3.1.1
 * Copyright(c) 2006-2010 Ext JS, LLC
 * licensing@extjs.com
 * http://www.extjs.com/license
 */
/*
 * Note that this control will most likely remain as an example, and not as a core Ext form
 * control.  However, the API will be changing in a future release and so should not yet be
 * treated as a final, stable API at this time.
 */

/**
 * @class Ext.ux.form.ItemSelector
 * @extends Ext.form.Field
 * A control that allows selection of between two Ext.ux.form.MultiSelect controls.
 *
 *  @history
 *    2008-06-19 bpm Original code contributed by Toby Stuart (with contributions from Robert Williams)
 *
 * @constructor
 * Create a new ItemSelector
 * @param {Object} config Configuration options
 * @xtype itemselector 
 */
Ext.ux.form.ItemSelector = Ext.extend(Ext.form.Field,  {
    hideNavIcons:false,
    imagePath:"",
    iconUp:"up2.gif",
    iconDown:"down2.gif",
    iconLeft:"left2.gif",
    iconRight:"right2.gif",
    iconTop:"top2.gif",
    iconBottom:"bottom2.gif",
    drawUpIcon:true,
    drawDownIcon:true,
    drawLeftIcon:true,
    drawRightIcon:true,
    drawTopIcon:true,
    drawBotIcon:true,
    delimiter:',',
    bodyStyle:null,
    border:false,
    defaultAutoCreate:{tag: "div"},
    /**
     * @cfg {Array} multiselects An array of {@link Ext.ux.form.MultiSelect} config objects, with at least all required parameters (e.g., store)
     */
    multiselects:null,

    initComponent: function(){
        Ext.ux.form.ItemSelector.superclass.initComponent.call(this);
        this.addEvents({
            'rowdblclick' : true,
            'change' : true
        });
    },

    onRender: function(ct, position){
        Ext.ux.form.ItemSelector.superclass.onRender.call(this, ct, position);

        // Internal default configuration for both multiselects
        var msConfig = [{
            legend: 'Available',
            draggable: true,
            droppable: true,
            width: 100,
            height: 100
        },{
            legend: 'Selected',
            droppable: true,
            draggable: true,
            width: 100,
            height: 100
        }];

        this.fromMultiselect = new Ext.ux.form.MultiSelect(Ext.applyIf(this.multiselects[0], msConfig[0]));
        this.fromMultiselect.on('dblclick', this.onRowDblClick, this);

        this.toMultiselect = new Ext.ux.form.MultiSelect(Ext.applyIf(this.multiselects[1], msConfig[1]));
        this.toMultiselect.on('dblclick', this.onRowDblClick, this);

        var p = new Ext.Panel({
            bodyStyle:this.bodyStyle,
            border:this.border,
            layout:"table",
            layoutConfig:{columns:3}
        });

        p.add(this.fromMultiselect);
        var icons = new Ext.Panel({header:false});
        p.add(icons);
        p.add(this.toMultiselect);
        p.render(this.el);
        icons.el.down('.'+icons.bwrapCls).remove();

        // ICON HELL!!!
        if (this.imagePath!="" && this.imagePath.charAt(this.imagePath.length-1)!="/")
            this.imagePath+="/";
        this.iconUp = this.imagePath + (this.iconUp || 'up2.gif');
        this.iconDown = this.imagePath + (this.iconDown || 'down2.gif');
        this.iconLeft = this.imagePath + (this.iconLeft || 'left2.gif');
        this.iconRight = this.imagePath + (this.iconRight || 'right2.gif');
        this.iconTop = this.imagePath + (this.iconTop || 'top2.gif');
        this.iconBottom = this.imagePath + (this.iconBottom || 'bottom2.gif');
        var el=icons.getEl();
        this.toTopIcon = el.createChild({tag:'img', src:this.iconTop, style:{cursor:'pointer', margin:'2px'}});
        el.createChild({tag: 'br'});
        this.upIcon = el.createChild({tag:'img', src:this.iconUp, style:{cursor:'pointer', margin:'2px'}});
        el.createChild({tag: 'br'});
        this.addIcon = el.createChild({tag:'img', src:this.iconRight, style:{cursor:'pointer', margin:'2px'}});
        el.createChild({tag: 'br'});
        this.removeIcon = el.createChild({tag:'img', src:this.iconLeft, style:{cursor:'pointer', margin:'2px'}});
        el.createChild({tag: 'br'});
        this.downIcon = el.createChild({tag:'img', src:this.iconDown, style:{cursor:'pointer', margin:'2px'}});
        el.createChild({tag: 'br'});
        this.toBottomIcon = el.createChild({tag:'img', src:this.iconBottom, style:{cursor:'pointer', margin:'2px'}});
        this.toTopIcon.on('click', this.toTop, this);
        this.upIcon.on('click', this.up, this);
        this.downIcon.on('click', this.down, this);
        this.toBottomIcon.on('click', this.toBottom, this);
        this.addIcon.on('click', this.fromTo, this);
        this.removeIcon.on('click', this.toFrom, this);
        if (!this.drawUpIcon || this.hideNavIcons) { this.upIcon.dom.style.display='none'; }
        if (!this.drawDownIcon || this.hideNavIcons) { this.downIcon.dom.style.display='none'; }
        if (!this.drawLeftIcon || this.hideNavIcons) { this.addIcon.dom.style.display='none'; }
        if (!this.drawRightIcon || this.hideNavIcons) { this.removeIcon.dom.style.display='none'; }
        if (!this.drawTopIcon || this.hideNavIcons) { this.toTopIcon.dom.style.display='none'; }
        if (!this.drawBotIcon || this.hideNavIcons) { this.toBottomIcon.dom.style.display='none'; }

        var tb = p.body.first();
        this.el.setWidth(p.body.first().getWidth());
        p.body.removeClass();

        this.hiddenName = this.name;
        var hiddenTag = {tag: "input", type: "hidden", value: "", name: this.name};
        this.hiddenField = this.el.createChild(hiddenTag);
    },
    
    doLayout: function(){
        if(this.rendered){
            this.fromMultiselect.fs.doLayout();
            this.toMultiselect.fs.doLayout();
        }
    },

    afterRender: function(){
        Ext.ux.form.ItemSelector.superclass.afterRender.call(this);

        this.toStore = this.toMultiselect.store;
        this.toStore.on('add', this.valueChanged, this);
        this.toStore.on('remove', this.valueChanged, this);
        this.toStore.on('load', this.valueChanged, this);
        this.valueChanged(this.toStore);
    },

    toTop : function() {
        var selectionsArray = this.toMultiselect.view.getSelectedIndexes();
        var records = [];
        if (selectionsArray.length > 0) {
            selectionsArray.sort();
            for (var i=0; i<selectionsArray.length; i++) {
                record = this.toMultiselect.view.store.getAt(selectionsArray[i]);
                records.push(record);
            }
            selectionsArray = [];
            for (var i=records.length-1; i>-1; i--) {
                record = records[i];
                this.toMultiselect.view.store.remove(record);
                this.toMultiselect.view.store.insert(0, record);
                selectionsArray.push(((records.length - 1) - i));
            }
        }
        this.toMultiselect.view.refresh();
        this.toMultiselect.view.select(selectionsArray);
    },

    toBottom : function() {
        var selectionsArray = this.toMultiselect.view.getSelectedIndexes();
        var records = [];
        if (selectionsArray.length > 0) {
            selectionsArray.sort();
            for (var i=0; i<selectionsArray.length; i++) {
                record = this.toMultiselect.view.store.getAt(selectionsArray[i]);
                records.push(record);
            }
            selectionsArray = [];
            for (var i=0; i<records.length; i++) {
                record = records[i];
                this.toMultiselect.view.store.remove(record);
                this.toMultiselect.view.store.add(record);
                selectionsArray.push((this.toMultiselect.view.store.getCount()) - (records.length - i));
            }
        }
        this.toMultiselect.view.refresh();
        this.toMultiselect.view.select(selectionsArray);
    },

    up : function() {
        var record = null;
        var selectionsArray = this.toMultiselect.view.getSelectedIndexes();
        selectionsArray.sort();
        var newSelectionsArray = [];
        if (selectionsArray.length > 0) {
            for (var i=0; i<selectionsArray.length; i++) {
                record = this.toMultiselect.view.store.getAt(selectionsArray[i]);
                if ((selectionsArray[i] - 1) >= 0) {
                    this.toMultiselect.view.store.remove(record);
                    this.toMultiselect.view.store.insert(selectionsArray[i] - 1, record);
                    newSelectionsArray.push(selectionsArray[i] - 1);
                }
            }
            this.toMultiselect.view.refresh();
            this.toMultiselect.view.select(newSelectionsArray);
        }
    },

    down : function() {
        var record = null;
        var selectionsArray = this.toMultiselect.view.getSelectedIndexes();
        selectionsArray.sort();
        selectionsArray.reverse();
        var newSelectionsArray = [];
        if (selectionsArray.length > 0) {
            for (var i=0; i<selectionsArray.length; i++) {
                record = this.toMultiselect.view.store.getAt(selectionsArray[i]);
                if ((selectionsArray[i] + 1) < this.toMultiselect.view.store.getCount()) {
                    this.toMultiselect.view.store.remove(record);
                    this.toMultiselect.view.store.insert(selectionsArray[i] + 1, record);
                    newSelectionsArray.push(selectionsArray[i] + 1);
                }
            }
            this.toMultiselect.view.refresh();
            this.toMultiselect.view.select(newSelectionsArray);
        }
    },

    fromTo : function() {
        var selectionsArray = this.fromMultiselect.view.getSelectedIndexes();
        var records = [];
        if (selectionsArray.length > 0) {
            for (var i=0; i<selectionsArray.length; i++) {
                record = this.fromMultiselect.view.store.getAt(selectionsArray[i]);
                records.push(record);
            }
            if(!this.allowDup)selectionsArray = [];
            for (var i=0; i<records.length; i++) {
                record = records[i];
                if(this.allowDup){
                    var x=new Ext.data.Record();
                    record.id=x.id;
                    delete x;
                    this.toMultiselect.view.store.add(record);
                }else{
                    this.fromMultiselect.view.store.remove(record);
                    this.toMultiselect.view.store.add(record);
                    selectionsArray.push((this.toMultiselect.view.store.getCount() - 1));
                }
            }
        }
        this.toMultiselect.view.refresh();
        this.fromMultiselect.view.refresh();
        var si = this.toMultiselect.store.sortInfo;
        if(si){
            this.toMultiselect.store.sort(si.field, si.direction);
        }
        this.toMultiselect.view.select(selectionsArray);
    },

    toFrom : function() {
        var selectionsArray = this.toMultiselect.view.getSelectedIndexes();
        var records = [];
        if (selectionsArray.length > 0) {
            for (var i=0; i<selectionsArray.length; i++) {
                record = this.toMultiselect.view.store.getAt(selectionsArray[i]);
                records.push(record);
            }
            selectionsArray = [];
            for (var i=0; i<records.length; i++) {
                record = records[i];
                this.toMultiselect.view.store.remove(record);
                if(!this.allowDup){
                    this.fromMultiselect.view.store.add(record);
                    selectionsArray.push((this.fromMultiselect.view.store.getCount() - 1));
                }
            }
        }
        this.fromMultiselect.view.refresh();
        this.toMultiselect.view.refresh();
        var si = this.fromMultiselect.store.sortInfo;
        if (si){
            this.fromMultiselect.store.sort(si.field, si.direction);
        }
        this.fromMultiselect.view.select(selectionsArray);
    },

    valueChanged: function(store) {
        var record = null;
        var values = [];
        for (var i=0; i<store.getCount(); i++) {
            record = store.getAt(i);
            values.push(record.get(this.toMultiselect.valueField));
        }
        this.hiddenField.dom.value = values.join(this.delimiter);
        this.fireEvent('change', this, this.getValue(), this.hiddenField.dom.value);
    },

    getValue : function() {
        return this.hiddenField.dom.value;
    },

    onRowDblClick : function(vw, index, node, e) {
        if (vw == this.toMultiselect.view){
            this.toFrom();
        } else if (vw == this.fromMultiselect.view) {
            this.fromTo();
        }
        return this.fireEvent('rowdblclick', vw, index, node, e);
    },

    reset: function(){
        range = this.toMultiselect.store.getRange();
        this.toMultiselect.store.removeAll();
        this.fromMultiselect.store.add(range);
        var si = this.fromMultiselect.store.sortInfo;
        if (si){
            this.fromMultiselect.store.sort(si.field, si.direction);
        }
        this.valueChanged(this.toMultiselect.store);
    }
});

Ext.reg('itemselector', Ext.ux.form.ItemSelector);

//backwards compat
Ext.ux.ItemSelector = Ext.ux.form.ItemSelector;
