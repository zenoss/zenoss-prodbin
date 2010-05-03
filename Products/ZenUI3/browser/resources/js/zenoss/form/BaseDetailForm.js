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

function isField(c) {
    return !!c.setValue && !!c.getValue && !!c.markInvalid && !!c.clearInvalid;
}

ZF.BaseDetailForm = Ext.extend(Ext.form.FormPanel, {
    contextUid: null,
    isLoadInProgress: false,
    constructor: function(config){
        // Router doesn't technically matter, since they all do getInfo, but
        // getForm is definitely defined on DeviceRouter
        var router = config.router || Zenoss.remote.DeviceRouter;
        config.baseParams = Ext.applyIf(config.baseParams||{
            uid: config.contextUid
        });
        config.listeners = Ext.applyIf(config.listeners||{}, {
            'add': function(me, field, index){
                if (isField(field)) {
                    this.onFieldAdd.call(this, field);
                }
            }
        });
        config = Ext.applyIf(config||{}, {
            paramsAsHash: true,
            autoScroll: 'y',
            cls: 'detail-form-panel',
            buttonAlign: 'left',
            labelAlign: 'top',
            trackResetOnLoad: true,
            permission: 'Manage Device',
            api: {
                submit:  function(form, success, scope){
                    var o = {},
                        vals = scope.form.getFieldValues(true);
                    Ext.apply(o, vals, success.params);
                    router.setInfo(o, function(result) {
                        this.form.clearInvalid();
                        this.form.setValues(vals);
                        this.form.afterAction(this, true);
                        this.form.reset();
                    }, scope);
                },
                load: router.getInfo
            }
        });
        var hasPermission = function() {
            var perm = !Zenoss.Security.doesNotHavePermission(config.permission);
            if (Ext.isDefined(config.userCreated)) {
                return config.userCreated && perm;
            } else {
                return perm;
            }
        };
        if (hasPermission()) {
            Ext.apply(config, {
                buttons:  [{
                    xtype: 'button',
                    ref: '../savebtn',
                    text: _t('Save'),
                    disabled: true,
                    cls: 'detailform-submit-button',
                    handler: function(btn, e) {
                        this.refOwner.getForm().submit();
                    }
                },{
                    xtype: 'button',
                    ref: '../cancelbtn',
                    disabled: true,
                    text: _t('Cancel'),
                    cls: 'detailform-cancel-button',
                    handler: function(btn, e) {
                        this.refOwner.getForm().reset();
                    }
                }]
            });
        } 
        ZF.BaseDetailForm.superclass.constructor.call(this, config);
    },
    hasPermission: function() {
        var perm = !Zenoss.Security.doesNotHavePermission(this.permission);
        if (Ext.isDefined(this.userCreated)) {
            return this.userCreated && perm;
        } else {
            return perm;
        }
    },
    setButtonsDisabled: function(b) {
        if (this.hasPermission()) {
            this.savebtn.setDisabled(b);
            this.cancelbtn.setDisabled(b);
        }
    },
    doButtons: function() {
        this.setButtonsDisabled(!this.form.isDirty());
    },
    onFieldAdd: function(field) {
        if (!field.isXType('displayfield')) {
            this.mon(field, 'valid', this.doButtons, this);
        }
    },
    getFieldNames: function() {
        var keys = [];
        for (var k in this.getForm().getFieldValues(false)) {
            if (keys.indexOf(k)==-1) {
                keys.push(k);
            }
        }
        return keys;
    },
    load: function() {
        var o = Ext.apply({keys:this.getFieldNames()}, this.baseParams);
        this.form.load(o, function(result) {
            this.form.setValues(result.data);
            this.form.reset();
            this.doLayout();
        }, this);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.baseParams.uid = uid;
        this.isLoadInProgress = true;
        this.load();
    }
});

Ext.reg('basedetailform', ZF.BaseDetailForm);

})();
