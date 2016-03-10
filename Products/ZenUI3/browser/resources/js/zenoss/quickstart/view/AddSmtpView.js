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
     * @class Zenoss.quickstart.Wizard.view.AddSmtpView
     * @extends Ext.panel.Panel
     * @constructor
     *
     */
    Ext.define('Zenoss.quickstart.Wizard.view.AddSmtpView', {
        extend: 'Ext.form.Panel',
        alias: 'widget.wizardaddsmtpview',
        stepTitle: _t('Setup SMTP'),
        setDefaultPort: function (_this, ev, eOpts) {
            var portField = _this.nextSibling();
            if (!Ext.isEmpty(_this.getValue())) {
                portField.allowBlank = false;
                if (Ext.isEmpty(portField.getValue())) {
                    portField.setValue(25);
                }
            }
            else {
                portField.allowBlank = true;
                portField.validate();
            }
        },
        constructor: function (config) {
            config = config || {};
            Ext.applyIf(config, {
                labelWidth: 100,
                frame: false,
                border: false,
                layout: {
                    type: 'vbox'
                },
                defaults: {
                    frame: false,
                    labelWidth: 200,
                    width: '100%',
                    border: false,
                    style: {
                        padding: "25px"
                    }
                },
                items: [
                    {
                        xtype: 'panel',
                        frame: false,
                        border: false,
                        cls: 'helptext',
                        html: _t("Define SMTP server host, port, username, and password to enable email from Zenoss")
                    },
                    {
                        xtype: 'textfield',
                        fieldLabel: _t('SMTP Host'),
                        name: 'smtpHost',
                        labelAlign: 'left',
                        allowBlank: true,
                        listeners: {
                            blur: this.setDefaultPort
                        }
                    },
                    {
                        xtype: 'numberfield',
                        fieldLabel: _t('SMTP Port (usually 25)'),
                        name: 'smtpPort',
                        minValue: 1,
                        hideTrigger: true,
                        allowDecimals: false,
                        allowExponential: false,
                        allowBlank: true,
                        blankText: 'This field is required if a SMTP host is provided',
                        msgTarget: 'under'
                    },
                    {
                        xtype: 'textfield',
                        fieldLabel: _t('SMTP Username (blank for none)'),
                        name: 'smtpUser',
                        allowBlank: true
                    },
                    {
                        xtype: 'textfield',
                        inputType: 'password',
                        fieldLabel: _t('SMTP Password (blank for none)'),
                        name: 'smtpPass',
                        allowBlank: true
                    }
                ]
            });
            this.callParent([config]);
        }
    });
})();