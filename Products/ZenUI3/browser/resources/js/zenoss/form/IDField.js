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

ZF.IDField = Ext.extend(Ext.form.TextField, {
    /* 
    * Context on which to check for id validity. Defaults to
    * Zenoss.env.PARENT_CONTEXT.
    */
    context: null,
    /* 
    * Limit characters to those accepted by ObjectManager 
    */
    maskRe: /[a-zA-Z0-9-_~,.$\(\)# @]/,
    /*
    * Validator function that makes a request to the parent context and calls
    * the checkValidId method.
    */
    validator: function(value) {
        var context = this.context || Zenoss.env.PARENT_CONTEXT;
        if (this.vtransaction) {
            Ext.lib.Ajax.abort(this.vtransaction);
        }
        this.vtransaction = Ext.lib.Ajax.request(
            'GET',
            context + '/checkValidId?id='+value,
            {
                success: function() {
                    this.isValid = true;
                },
                failure: function() {
                    this.markInvalid(
                        _t('That name is invalid or already in use.')
                    );
                    this.isValid = false;
                },
                scope: this
            }
        );
        return true;
    }
});

Ext.reg('idfield', ZF.IDField);

})();
