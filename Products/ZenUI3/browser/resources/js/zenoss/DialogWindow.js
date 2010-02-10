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

Ext.ns('Zenoss.dialog');

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

Zenoss.FormDialog = Ext.extend(Ext.Window, {
    constructor: function(config) {
        var form = new Ext.form.FormPanel({
            border: false,
            minWidth: 300,
            labelAlign: 'top',
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

})();
