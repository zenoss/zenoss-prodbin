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


}());
