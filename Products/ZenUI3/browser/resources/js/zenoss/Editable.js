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
    }
});

Ext.reg('displayfield', Zenoss.DisplayField);


Zenoss.EditorWithButtons = Ext.extend(Ext.Editor, {
    onRender: function(ct, position) {
        Zenoss.EditorWithButtons.superclass.onRender.apply(this, arguments);
        this.editorpanel = new Ext.Panel({
            frame: true,
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
            updateEl: true,
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
        this.editor.on('beforecomplete', this.onBeforeComplete, this);
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
