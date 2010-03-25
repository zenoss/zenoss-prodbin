/*
 ###########################################################################
 #
 # This program is part of Zenoss Core, an open source monitoring platform.
 # Copyright (C) 2010, Zenoss Inc.
 #
 # This program is free software; you can redistribute it and/or modify it
 # under the terms of the GNU General Public License version 2 as published by
 # the Free Software Foundation.
 #
 # For complete information please visit: http://www.zenoss.com/oss/
 #
 ###########################################################################
 */

(function() {

Ext.ns('Zenoss.form');

Zenoss.form.InheritField = Ext.extend(Zenoss.form.FieldRow, {
    constructor: function(config) {
        var item;

        // Take the first member of items
        if (Ext.isObject(config.items)) {
            item = config.items;
        } else {
            item = config.items[0];
        }

        // Add the checkbox
        this.inheritbox = new Ext.form.Checkbox({
            fieldLabel: _t('Inherit?'),
            labelSeparator: '',
            width: 60,
            handler: function(me) {
                console.log(me.checked ? 'checked' : 'unchecked');
            }
        });
        config.items = [this.inheritbox, item];
        Zenoss.form.InheritField.superclass.constructor.call(this, config);
        this.field = this.items.items[1].items.items[0];
    },
    inherit: function() {
        return this.inheritbox.checked;
    },
    getValue: function() {
        return {
            inherited: this.inherit(),
            value: this.field.getValue()
        };
    },
    setValue: function(value) {
        if (Ext.isObject(value)) {
            this.inheritbox.setValue(
                Ext.isDefined(value.inherited) ? value.inherited : false
            );
            value = value.value;
        } else {
            this.inheritbox.setValue(false);
        }
        this.field.setValue(value);
    }
 });
 Ext.reg('inheritfield', Zenoss.form.InheritField);

})();
