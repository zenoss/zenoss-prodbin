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

})();
