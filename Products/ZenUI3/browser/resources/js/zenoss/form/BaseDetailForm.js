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

var ZF = Ext.ns('Zenoss.form');

ZF.BaseDetailForm = Ext.extend(Ext.form.FormPanel, {
    contextUid: null,
    constructor: function(config){
        var me = this;
        config.baseParams = Ext.applyIf(config.baseParams||{
            uid: config.contextUid
        });
        config = Ext.applyIf(config||{}, {
            autoScroll: 'y',
            cls: 'detail-form-panel',
            buttonAlign: 'left',
            buttons:  [{
                    xtype: 'button',
                    formBind: true,
                    text: _t('Save'),
                    cls: 'detailform-submit-button',
                    handler: function(btn, e) {
                        btn.ownerCt.ownerCt.getForm().submit();
                    }
                },{
                    xtype: 'button',
                    text: _t('Cancel'),
                    cls: 'detailform-cancel-button',
                    handler: function(btn, e) {
                        btn.ownerCt.ownerCt.getForm().reset();
                    }
                }]

        });
        ZF.BaseDetailForm.superclass.constructor.call(this, config);
    }
});

Ext.reg('basedetailform', ZF.BaseDetailForm);

})();
