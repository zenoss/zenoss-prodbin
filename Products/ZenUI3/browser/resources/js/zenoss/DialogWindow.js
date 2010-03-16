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

(function(){

Ext.ns('Zenoss', 'Zenoss.dialog');

/**
 * @class BaseDialog
 * @extends Ext.Window
 * A modal dialog with Zenoss styling. Subclasses should specify a layout. 
 * @constructor
 */
var BaseDialog = Ext.extend(Ext.Window, {
    constructor: function(config) {
        Ext.applyIf(config, {
            autoHeight: true,
            width: 310,
            closeAction: 'hide',
            plain: true,
            buttonAlign: 'left',
            padding: 10,
            modal: true
        });
        BaseDialog.superclass.constructor.call(this, config);
    }
});

function destroyWindow(button){
    button.ownerCt.ownerCt.destroy();
}

/**
 * @class Zenoss.dialog.HideDialogButton
 * @extends Ext.Button
 * A button that destroys it's window.
 * @constructor
 */
Zenoss.dialog.DialogButton = Ext.extend(Ext.Button, {
    constructor: function(config) {
        var h = config.handler;
        config.handler = h ? h.createSequence(destroyWindow) : destroyWindow;
        Zenoss.dialog.DialogButton.superclass.constructor.call(this, config);
    }
});

Ext.reg('DialogButton', Zenoss.dialog.DialogButton);

function hideWindow(button){
    button.ownerCt.ownerCt.hide();
}

/**
 * @class Zenoss.dialog.HideDialogButton
 * @extends Ext.Button
 * A button that hides it's window.
 * @constructor
 */
Zenoss.dialog.HideDialogButton = Ext.extend(Ext.Button, {
    constructor: function(config) {
        var h = config.handler;
        config.handler = h ? h.createSequence(hideWindow) : hideWindow;
        Zenoss.dialog.DialogButton.superclass.constructor.call(this, config);
    }
});

Ext.reg('HideDialogButton', Zenoss.dialog.HideDialogButton);

Zenoss.dialog.CANCEL = {
    xtype: 'DialogButton',
    text: _t('Cancel')
};

/**
 * @class Zenoss.MessageDialog
 * @extends BaseDialog
 * A modal dialog window with Zenoss styling and a fit layout.  This window
 * meant to be instantiated once per page, and hidden each time the user
 * closes it.  Includes an OK and Cancel button.
 * @constructor
 */
Zenoss.MessageDialog = Ext.extend(BaseDialog, {
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'fit',
            items: {
                border: false,
                html: config.message
            },
            buttons: [
                {
                    xtype: 'HideDialogButton',
                    text: _t('OK'),
                    handler: config.okHandler
                }, {
                    xtype: 'HideDialogButton',
                    text: _t('Cancel'),
                    handler: config.cancelHandler
                }
            ]
        });
        Zenoss.MessageDialog.superclass.constructor.call(this, config);
    }
});

/**
 * @class Zenoss.FormDialog
 * @extends Ext.Window
 * A modal dialog window with Zenoss styling and a form layout.  This window
 * meant to be instantiated multiple times per page, and destroyed each time
 * the user closes it.
 * @constructor
 */
Zenoss.FormDialog = Ext.extend(Ext.Window, {
    constructor: function(config) {
        var form = new Ext.form.FormPanel({
            border: false,
            id: config.formId,
            minWidth: 300,
            ref: "editForm",
            labelAlign: 'top',
            autoScroll:true,
            labelSeparator: ' ',
            bodyStyle: {
                'padding-left': '5%'
            },
            defaults: {
                xtype: 'textfield',
                anchor: '85%',
                border: false
            },
            items: config.items,
            html: config.html
        });
        config.items = form;
        
        Ext.applyIf(config, {
            layout: 'fit',
            plain: true,
            border: false,
            buttonAlign: 'left'
        });
        Zenoss.FormDialog.superclass.constructor.call(this, config);
    }
});

/**
 * @class Zenoss.HideFormDialog
 * @extends BaseDialog
 * A modal dialog window with Zenoss styling and a form layout.  This window
 * meant to be instantiated once per page, and hidden each time the user
 * closes it.
 * @constructor
 */
Zenoss.HideFormDialog = Ext.extend(BaseDialog, {
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'form',
            labelAlign: 'top',
            labelSeparator: ' '
        });
        Zenoss.HideFormDialog.superclass.constructor.call(this, config);
    }
});

/**
 * @class Zenoss.HideFitDialog
 * @extends Ext.Window
 * A modal dialog window with Zenoss styling and a fit layout.
 * @constructor
 */
Zenoss.HideFitDialog = Ext.extend(Ext.Window, {
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'fit',
            width: 600,
            height: 300,
            closeAction: 'hide',
            plain: true,
            buttonAlign: 'left',
            padding: 10,
            modal: true
        });
        Zenoss.HideFitDialog.superclass.constructor.call(this, config);
    }
});

/**
 * Works in conjunction with Zenoss.dialog.DialogFormPanel. Loads a formPanel 
 * with ID diynamic-dialog-panel and submits the form on the panel when the 
 * submit button on this dialog is pressed. 
 */
Zenoss.dialog.DynamicDialog = Ext.extend(BaseDialog, {
    initEvents: function(){
        Zenoss.dialog.DynamicDialog.superclass.initEvents.call(this);
        this.body.getUpdater().on('failure', function(el, response) {
            el.update("Failed to load dialog");
        });
    },
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            layout: 'fit',
            modal: true,
            buttons: [{
                xtype: 'DialogButton',
                text: _t('Submit'),
                handler: this.submitHandler.createDelegate(this)
            }, Zenoss.dialog.CANCEL]
        });
        Ext.apply(config, {
            id: 'dynamic-dialog'
        });
        Zenoss.dialog.DynamicDialog.superclass.constructor.call(this, config);
    },
    submitHandler: function(b, event){
        var formPanel = Ext.getCmp('dynamic-dialog-panel');
        var form = formPanel.getForm();
        var params = {};
        if (Ext.isDefined(formPanel.submitName) && formPanel.submitName !== null){
            params[formPanel.submitName] = 'OK';
        }
        form.submit({
            params: params,
            success: function(form, action){
                var msg = this.title + ' finished successfully'; 
                Zenoss.message(msg, true);
            }.createDelegate(this),
            failure: function(form, action){
                var msg = this.title + ' had errors'; 
                Zenoss.message(msg, false);
                }
        });
    }
});

/**
 * Used to create dialogs that will be added dynamically
 */
Zenoss.dialog.DialogFormPanel = Ext.extend(Ext.form.FormPanel, {
    /**
     * whether or not the result of submitting the form associated with this 
     * panel will return a json result. Default true
     */
    jsonResult: true,
    /**
     * extra parameter to send when submitted
     */
    submitName: null,
    /**
     * name of an existing from to be submitted; if not defined a new form 
     * will be created.  Primarily used for backwards compatibility so existing
     * dialog forms don't have to be entirely rewritten.
     */
    existingFormId: null,
    constructor: function(config) {
        config = config || {};
        Ext.apply(config, {
            border: false,
            id: 'dynamic-dialog-panel'
        });
        Zenoss.dialog.DialogFormPanel.superclass.constructor.call(this, config);
    },
    /**
     * private; override from base class so that a basic form can be created
     * to point at an existing from if configured and also set a different 
     * response reader if expected result from submit is not JSON
     */
    createForm: function(){
        var config = Ext.applyIf({listeners: {}}, this.initialConfig);
        if (!this.jsonResult) {
            config['errorReader'] = {
                read: function(xhr) {
                    var success = true;
                    //TODO scan result for exceptions/errors
                    if (xhr.status != 200) {
                        success = false;
                    }
                    return {
                        records: [],
                        success: success
                    };
                }
            };
        }
        var formId = null;
        if (this.existingFormId !== null){
            formId = this.existingFormId;
        }
        return new Ext.form.BasicForm(formId, config);
    }
});

Ext.reg('DialogFormPanel', Zenoss.dialog.DialogFormPanel);

})();
