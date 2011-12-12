(function(){
    /**
     * This file contains overrides we are appyling to the Ext framework. These are default values we are setting
     * and convenience methods on the main Ext classes.
     **/


    /**
     * This makes the default value for checkboxes getSubmitValue (called by getFieldValues on the form)
     * return true/false if it is checked or unchecked. The normal default is "on" or nothing which means the
     * key isn't even sent to the server.
     **/
    Ext.override(Ext.form.field.Checkbox, {
        inputValue: true,
        uncheckedValue: false
    });
    
    /**
    * Splitter needs to be resized thinner based on the older UI. The default is 5
    **/
   Ext.override(Ext.resizer.Splitter, {
       width: 2
   });

    /**
     * In every one of our panels we want border and frame to be false so override it on the base class.
     **/
    Ext.override(Ext.panel.Panel, {
        frame: false,
        border: false
    });

    /**
     * Refs were removed when going from Ext3 to 4, we rely heavily on this feature and it is much more
     * concise way of accessing children so we are patching it back in.
     **/
    Ext.override(Ext.AbstractComponent, {
        initRef: function() {
            if(this.ref && !this.refOwner){
                var levels = this.ref.split('/'),
                last = levels.length,
                i = 0,
                t = this;
                while(t && i < last){
                    t = t.ownerCt;
                    ++i;
                }
                if(t){
                    t[this.refName = levels[--i]] = this;
                    this.refOwner = t;
                }
            }
        },
        recursiveInitRef: function() {
            this.initRef();
            if (Ext.isDefined(this.items)) {
                Ext.each(this.items.items, function(item){
                    item.recursiveInitRef();
                }, this);
            }
            if (Ext.isFunction(this.child)) {
                var tbar = this.child('*[dock="top"]');
                if (tbar) {
                    tbar.recursiveInitRef();
                }
                var bbar = this.child('*[dock="bottom"]');
                if (bbar) {
                    bbar.recursiveInitRef();
                }
            }
        },
        removeRef: function() {
            if (this.refOwner && this.refName) {
                delete this.refOwner[this.refName];
                delete this.refOwner;
            }
        },
        onAdded: function(container, pos) {
            this.ownerCt = container;
            this.recursiveInitRef();
            this.fireEvent('added', this, container, pos);
        },
        onRemoved: function() {
            this.removeRef();
            var me = this;
            me.fireEvent('removed', me, me.ownerCt);
            delete me.ownerCt;
        }
    });


    Ext.reg = function(xtype, cls){
        if (Ext.isString(cls)) {
            Ext.ClassManager.setAlias(cls, 'widget.'+xtype);
        } else {
            // try to register the component
            var clsName ="Zenoss.component." + xtype;
            if (Ext.ClassManager.get(clsName)) {
                Ext.ClassManager.setAlias(clsName, 'widget.'+xtype);
            }else {
                throw Ext.String.format("Unable to to register the xtype {0}: change the Ext.reg definition from the object to a string", xtype);
            }
        }
    };

    /**
     * The Ext.grid.Panel component row selection has a flaw in it:

     Steps to recreate:
     1. Create a standard Ext.grid.Panel with multiple records in it and turn "multiSelect: true"
     Note that you can just go to the documentation page
     http://docs.sencha.com/ext-js/4-0/#!/api/Ext.grid.Panel and insert the multiSelect:
     true line right into there and flip to live preview.

     2. Select the top row, then press and hold shift and click on the second row, then the third row,
     then the fourth. You would expect to see all 4 rows selected but instead you just get the last two.

     3. For reference, release the shift and select the bottom row (4th row). Now press and hold shift
     and select the 3rd row, then the 2nd row, then the 1st row. You now see all four rows selected.

     To Fix this I have to override the Ext.selection.Model to handle the top down versus bottom up selection.
     *
     */
    Ext.override(Ext.selection.Model, {
        /**
         * Selects a range of rows if the selection model {@link #isLocked is not locked}.
         * All rows in between startRow and endRow are also selected.
         * @param {Ext.data.Model/Number} startRow The record or index of the first row in the range
         * @param {Ext.data.Model/Number} endRow The record or index of the last row in the range
         * @param {Boolean} keepExisting (optional) True to retain existing selections
         */
        selectRange : function(startRow, endRow, keepExisting, dir){
            var me = this,
                store = me.store,
                selectedCount = 0,
                i,
                tmp,
                dontDeselect,
                records = [];

            if (me.isLocked()){
                return;
            }

            if (!keepExisting) {
                me.deselectAll(true);
            }

            if (!Ext.isNumber(startRow)) {
                startRow = store.indexOf(startRow);
            }
            if (!Ext.isNumber(endRow)) {
                endRow = store.indexOf(endRow);
            }

            // WG: create a flag to see if we are swapping
            var swapped = false;
            // ---

            // swap values
            if (startRow > endRow){
                // WG:  set value to true for my flag
                swapped = true;
                // ----
                tmp = endRow;
                endRow = startRow;
                startRow = tmp;
            }

            for (i = startRow; i <= endRow; i++) {
                if (me.isSelected(store.getAt(i))) {
                    selectedCount++;
                }
            }

            if (!dir) {
                dontDeselect = -1;
            } else {
                dontDeselect = (dir == 'up') ? startRow : endRow;
            }

            for (i = startRow; i <= endRow; i++){
                if (selectedCount == (endRow - startRow + 1)) {
                    if (i != dontDeselect) {
                        me.doDeselect(i, true);
                    }
                } else {
                    records.push(store.getAt(i));
                }
            }

            //WG:  START  CHANGE
            // This is my fix, we need to flip the order
            // for it to correctly track what was selected first.
            if(!swapped){
                records.reverse();
            }
            //WG:  END CHANGE



            me.doMultiSelect(records, true);
        }
    });


}());
