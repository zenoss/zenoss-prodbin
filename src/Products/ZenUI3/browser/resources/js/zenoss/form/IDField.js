/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function() {

Ext.ns('Zenoss.form');

Ext.define("Zenoss.form.IDField", {
    alias: ['widget.idfield'],
    extend: "Ext.form.TextField",
    /*
    * Context on which to check for id validity. Defaults to
    * Zenoss.env.PARENT_CONTEXT.
    */
    context: null,
    /*
    * Limit characters to those accepted by ObjectManager
    */
    maskRe: /[a-zA-Z0-9-_~,.$\(\)# @]/,
    _serverIsValid: false,
    validationErrorText: _t('That name is invalid or is already in use.'),
    // invalid text from server on success callback;
    _serverInvalidText: '',
    /*
    * "validator" fn should return error message - if not valid, or true - if valid;
    * if we want to validate field from Ajax we should call Ajax with some(300 ms) timeout to allow user end typing
    * and on response revalidate field;
    */
    validator: function(value) {
        var context = Zenoss.render.link(undefined, this.context || Zenoss.env.PARENT_CONTEXT),
            me = this,
            errorText = me._serverInvalidText || me.validationErrorText;

        // Don't bother with empty values
        if (Ext.isEmpty(value)) {
            return true;
        }

        if (value !== me._previousValue) {
            // stop validation task if it exist;
            clearTimeout(me.validationTask);
            // call Ajax with timeout to allow user end typing;
            me.validationTask = setTimeout(function () {
                Ext.Ajax.request({
                    url: context + '/checkValidId?id=' + value,
                    method: 'GET',
                    success: function (response) {
                        // name is valid if we get responseText="True"
                        me._serverIsValid = (response.responseText === "True");
                        // clear server invalid message to always get new one;
                        me._serverInvalidText = '';

                        if (!me._serverIsValid) {
                            // maybe we receive server error text
                            me._serverInvalidText = response.responseText || me.validationErrorText;
                        }
                        me.validate();
                    },
                    failure: function (response) {
                        me._serverIsValid = false;
                        me.validate();
                    }
                });
            }, 300);
        }
        me._previousValue = value;
        // always return true, later on Ajax callback we will revalidate this field;
        // we will have errorText after Ajax
        return me._serverIsValid ? true :  errorText;
    }
});

})();
