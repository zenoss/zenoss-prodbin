/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

(function(){

Zenoss.DisplayField = Ext.extend(Ext.form.DisplayField, {
    constructor: function(config) {
        Ext.applyIf(config, {
            fieldClass: 'display-field',
            labelSeparator: '',
            labelStyle: 'font-weight:bold'
        });
        Zenoss.DisplayField.superclass.constructor.call(this, config);
    },
    setRawValue: function(v) {
        if (Ext.isIE) {
            v = v.replace(/\n/g, '<br/>');
        }
        Zenoss.DisplayField.superclass.setRawValue.call(this, v);
    }
});

Ext.reg('displayfield', Zenoss.DisplayField);


Zenoss.EditorWithButtons = Ext.extend(Ext.Editor, {
    onRender: function(ct, position) {
        Zenoss.EditorWithButtons.superclass.onRender.apply(this, arguments);
        this.editorpanel = new Ext.Panel({
            frame: true,
            bodyStyle: Ext.isIE ? 'padding-bottom:5px' : '',
            buttonAlign: 'left',
            buttons: [{
                text:_t('Save'), 
                handler: this.completeEdit.createDelegate(this)
            }, {
                text:_t('Cancel'), 
                handler: this.cancelEdit.createDelegate(this)
            }],
            items: this.field
        });
        if (Ext.isIE) {
            // IE can't set the layer width properly; always gets set to 11189
            this.el.setWidth(450);
        }
        this.editorpanel.render(this.el).show();
    },
    onBlur: function(){
        // do nothing
    }
});

Ext.reg('btneditor', Zenoss.EditorWithButtons);


Zenoss.EditableField = Ext.extend(Zenoss.DisplayField, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            cls: 'editable-field',
            overCls: 'editable-field-over',
            editEvent: 'click'
        });
        config.editor = Ext.applyIf(config.editor||{}, {
            xtype: 'btneditor',
            updateEl: !Ext.isIE,
            ignoreNoChange: true,
            autoSize: 'width',
            field: {
                xtype: 'textfield',
                selectOnFocus: true
            }
        });
        Zenoss.EditableField.superclass.constructor.call(this, config);
        this.initEditor();
        this.on('render', function(){
            this.getEl().on(this.editEvent, this.startEdit, this);
        }, this);
    },
    initEditor: function() {
        if (!(this.editor instanceof Ext.Editor)) {
            this.editor = Ext.create(this.editor);
        }
        var ed = this.editor;
        ed.on('beforecomplete', this.onBeforeComplete, this);
        if (Ext.isIE) {
            ed.field.origSetValue = ed.field.setValue;
            ed.field.setValue = function(v){
                v = v.replace(/\<BR\>/g, '\n');
                return this.origSetValue(v);
            }.createDelegate(ed.field);
        }
    },
    getForm: function() {
        var ownerCt = this.ownerCt;
        while (ownerCt && !(ownerCt instanceof Ext.FormPanel)) {
            ownerCt = ownerCt.ownerCt;
        }
        return ownerCt;
    },
    onBeforeComplete: function(t, val, startVal) {
        var opts = Ext.apply({}, this.getForm().baseParams||{});
        opts[this.name] = val;
        this.getForm().api.submit(opts, function(result) {
            if (result.success) {
                this.setValue(result[this.name] || val);
            } else {
                this.setValue(startVal);
            }
        }, this);
    },
    startEdit: function(e, t) {
        if (!this.disabled) {
            this.editor.startEdit(t);
        }
    }
});

Ext.reg('editable', Zenoss.EditableField);


Zenoss.EditableTextarea = Ext.extend(Zenoss.EditableField, {
    constructor: function(config) {
        config.editor = config.editor || {};
        config.editor.field = Ext.applyIf(config.editor.field||{}, {
            xtype: 'textarea',
            grow: true
        });
        Zenoss.EditableTextarea.superclass.constructor.call(this, config);
    }
});

Ext.reg('editabletextarea', Zenoss.EditableTextarea);


})();
