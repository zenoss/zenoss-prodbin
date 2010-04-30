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

        // if the value has not changed do not send an ajax request
        if (this._previousValue !== undefined) {
            if (value === this._previousValue) {
                return this.reportResponse(this._previousResponseText);
            }
        }
        this._previousValue = value;
        
        if (this.vtransaction) {
            Ext.lib.Ajax.abort(this.vtransaction);
        }
        this.vtransaction = Ext.lib.Ajax.request(
            'GET',
            context + '/checkValidId?id='+value,
            {
                success: function(response) {
                    this._previousResponseText = response.responseText;
                    return this.reportResponse(response.responseText);
                },
                failure: function(response) {
                    this.markInvalid(
                        _t('That name is invalid or is already in use.')
                    );
                },
                scope: this
            }
        );
        return true;
    },
    /**
    * Interprets a response from the server to determine if this field is valid.
    **/
    reportResponse: function(responseText) {
        if (responseText === "True") {
            return true;
        }
        
        // the server responds with a string of why it is invalid 
        this.markInvalid(
            _t('That name is invalid: ') + ' ' + responseText
        );
        return false;
    }
});

Ext.reg('idfield', ZF.IDField);

})();
