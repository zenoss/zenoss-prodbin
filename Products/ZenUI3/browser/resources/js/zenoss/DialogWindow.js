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

Ext.ns('Zenoss');

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

Zenoss.DialogButton = Ext.extend(Ext.Button, {
    constructor: function(config) {
        if ( ! Ext.isDefined(config.handler) ) {
            config.handler = function(){};
        }
        config.handler = config.handler.createSequence(function(button) {
            var dialog = button.findParentBy(function(parent){
                return parent.id == config.dialogId;
            });
            dialog.hide();
        });
        Zenoss.DialogButton.superclass.constructor.call(this, config);
    }
});

Ext.reg('DialogButton', Zenoss.DialogButton);

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
                    xtype: 'DialogButton',
                    text: _t('OK'),
                    handler: config.okHandler,
                    dialogId: config.id
                }, {
                    xtype: 'DialogButton',
                    text: _t('Cancel'),
                    handler: config.cancelHandler,
                    dialogId: config.id
                }
            ]
        });
        Zenoss.MessageDialog.superclass.constructor.call(this, config);
    }
});

Zenoss.FormDialog = Ext.extend(BaseDialog, {
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'form',
            labelAlign: 'top',
            labelSeparator: ' '
        });
        Zenoss.FormDialog.superclass.constructor.call(this, config);
    }
});

})();
