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
        setDefaultPort: function(_this, ev, eOpts) {
            if(_this.getValue() != null) {
                var portField = _this.nextSibling();
                if(portField.getValue() == null) {
                    portField.setValue(25);
                }
            }
        },
        constructor: function (config) {
            config = config || {};
            Ext.applyIf(config, {
                labelWidth: 100,
                frame: false,
                border: false,
                layout: {
                    type: 'hbox'
                },
                defaults: {
                    layout: 'anchor',
                    frame: false,
                    width: "50%",
                    border: false,
                    style: {
                        padding: "25px"
                    }
                },
                items: [
                    {
                        xtype: 'fieldset',
                        border: false,
                        layout: 'anchor',
                        defaults: {
                            anchor: '95%',
                            labelAlign: 'top',
                            padding: "0 0 7px 0"
                        },
                        defaultType: 'textfield',
                        items: [
                            {
                                xtype: 'textfield',
                                fieldLabel: _t('SMTP Host'),
                                name: 'smtpHost',
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
                                allowBlank: true
                            }
                        ]
                    },
                    {
                        xtype: 'fieldset',
                        border: false,
                        layout: 'anchor',
                        defaults: {
                            anchor: '95%',
                            labelAlign: 'top',
                            padding: '0 0 7px 0'
                        },
                        items: [
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
                    }
                ]
            });
            this.callParent([config]);
        }
    });
})();