/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2016, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

(function () {

    /**
     * @class Zenoss.quickstart.Wizard.controller.AddSmtpController
     * This is the controller for the last page of the wizard
     * @extends Ext.app.Controller
     */
    Ext.define('Zenoss.quickstart.Wizard.controller.AddSmtpController', {
        models: [],
        views: [
            "AddSmtpView"
        ],
        refs: [{
            ref: 'userForm',
            selector: 'wizardaddsmtpview'
        }],
        extend: 'Ext.app.Controller',
        init: function () {
            var app = this.getApplication();
            app.on('finish', this.onFinish, this);
        },

        onFinish: function () {
            var values = this.getUserForm().getForm().getValues();
            var params = {
                smtpHost: values.smtpHost,
                smtpPort: values.smtpPort,
                smtpUser: values.smtpUser,
                smtpPass: values.smtpPass
            };
            Zenoss.remote.SettingsRouter.setDmdSettings(params);
        }
    });
})();