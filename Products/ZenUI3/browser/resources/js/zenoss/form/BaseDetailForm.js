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
    isLoadInProgress: false,
    constructor: function(config){
        var me = this;
        config.baseParams = Ext.applyIf(config.baseParams||{
            uid: config.contextUid
        });
        config = Ext.applyIf(config||{}, {
            paramsAsHash: true,
            autoScroll: 'y',
            cls: 'detail-form-panel',
            buttonAlign: 'left',
            labelAlign: 'top',
            autoScroll:true,
            buttons:  [{
                    xtype: 'button',
                    formBind: true,
                    text: _t('Save'),
                    cls: 'detailform-submit-button',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(btn, e) {
                        var values, form = me.getForm();

                        values = Ext.apply({uid: me.contextUid}, form.getFieldValues());

                        form.api.submit(values);
                        // Quirky work-around to clear all dirty flags on the
                        // fields in the form.
                        form.setValues(values);
                        // Raise a fake action complete event for posterity.
                        // TODO: make this a real action someday.
                        me.fireEvent('actioncomplete', me, {type:'zsubmit', values:values});
                    }
                },{
                    xtype: 'button',
                    text: _t('Cancel'),
                    cls: 'detailform-cancel-button',
                    handler: function(btn, e) {
                        me.getForm().reset();
                    }
                }]

        });
        ZF.BaseDetailForm.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.isLoadInProgress = true;
        this.load({ params: {uid: uid} });
    }
});

Ext.reg('basedetailform', ZF.BaseDetailForm);

})();
