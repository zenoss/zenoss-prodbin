/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    /**
     * Add a vtype for "form fields must match"
     **/
    Ext.apply(Ext.form.VTypes, {
        password: function(val, field) {
            if (field.initialPassField) {
                var pwd = Ext.getCmp(field.initialPassField);
                return (val === pwd.getValue());
            }
        },
        passwordText: _t("The passwords you've typed don't match.")
    });
    /**
     * @class Zenoss.quickstart.Wizard.view.AddUserView
     * @extends Ext.panel.Panel
     * @constructor
     *
     */
    Ext.define('Zenoss.quickstart.Wizard.view.AddUserView', {
        extend: 'Ext.form.Panel',
        alias: 'widget.wizardadduserview',
        stepTitle: _t('Setup Users'),
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                labelWidth: 100,
                frame: false,
                stepHeight: 400,
                border: false,
                bodyStyle: 'padding:5px 5px 0',
                layout: {
                    type: 'hbox'
                },
                defaults: {
                    layout: 'anchor',
                    frame: false,
                    width: 450,
                    border: false,
                    style: 'padding 25px'
                },
                items: [{
                    xtype: 'fieldset',
                    border: false,
                    layout: 'anchor',
                    defaultType: 'textfield',
                    defaults: {
                        anchor: '95%',
                        labelAlign: 'top'
                    },
                    title: _t("Set admin password"),
                    items: [{
                        xtype: 'panel',
                        frame: false,
                        border: false,
                        cls: 'helptext',
                        html: _t("The admin account has extended privileges,"+
                            " similar to Linux's <"+"span class='noem'>root<"+
                            "/span> or Windows' <" + "span class='noem'>"+
                            "Administrator<"+"/span>. "+
                            "Its use should be limited to administrative"+
                            " tasks.<"+"br/><"+"br/>Enter and "+
                            "confirm a password for the admin account.")
                    },{
                        fieldLabel: _t('Admin password'),
                        inputType: 'password',
                        name: 'admin-password1',
                        id: 'admin-password1',
                        allowBlank: false
                    },{
                        fieldLabel: _t('Retype password'),
                        inputType: 'password',
                        vtype: 'password',
                        name: 'admin-password2',
                        initialPassField: 'admin-password1',
                        allowBlank: false
                    }]
                },{
                    xtype: 'fieldset',
                    border: false,
                    layout: 'anchor',
                    defaults: {
                        anchor: '95%',
                        labelAlign: 'top',
                        padding: "0px 0px 5px 0px"
                    },
                    id: 'userfieldset',
                    defaultType: 'textfield',
                    title: _t("Create your account"),
                    items: [{
                        xtype: 'panel',
                        frame: false,
                        border: false,
                        cls: 'helptext',
                        html: _t("Enter information for your personal user "+
                            "account. You'll use this to perform "+
                            "most tasks.")
                    },{
                        context: '/zport/dmd/ZenUsers',
                        xtype: 'idfield',
                        id: 'username',
                        fieldLabel: _t('Username'),
                        name: 'username',
                        allowBlank: false
                    },{
                        fieldLabel: _t('Password'),
                        inputType: 'password',
                        name: 'password1',
                        id: 'password1',
                        allowBlank: false
                    },{
                        fieldLabel: _t('Retype password'),
                        inputType: 'password',
                        vtype: 'password',
                        name: 'password2',
                        initialPassField: 'password1',
                        allowBlank: false
                    },{
                        fieldLabel: _t('Your email'),
                        vtype: 'email',
                        name: 'emailAddress',
                        allowBlank: true
                    }]
                }]
            });
            this.callParent([config]);
        }
    });




})();
