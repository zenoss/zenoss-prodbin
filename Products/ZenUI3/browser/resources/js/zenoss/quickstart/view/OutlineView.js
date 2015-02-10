/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){


    Ext.define('Zenoss.quickstart.Wizard.view.WizardStep', {
        extend: 'Ext.panel.Panel',
        alias: 'widget.wizardstep',
        constructor: function(config) {
            config.html =  Ext.String.format('<div class="wizardStep">' +
                                             '<div class="wizardStepHeader"> <span class="wizardStepNumber">Step {0}</span> <img class="wizardIcon" src="{1}" /></div>' +

                                             '<div class="wizardStepTitle"> {2} </div>' +
                                             '<div class="wizardStepDescription"> {3} </div> '+
                                             '</div>',
                                            config.stepNumber,
                                            config.iconPath,
                                            config.stepTitle,
                                            config.stepDescription);
            this.callParent([config]);
        }
    });


    /**
     * @class Zenoss.quickstart.Wizard.view.OutlineView
     * @extends Ext.panel.Panel
     * @constructor
     *
     */
    Ext.define('Zenoss.quickstart.Wizard.view.OutlineView', {
        extend: 'Ext.panel.Panel',
        alias: 'widget.wizardoutlineview',
        stepHeight: 400,
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                stepTitle: _t('Zenoss Installation Wizard'),
                items:[{
                    layout: 'vbox',
                    items:[{
                        cls: 'wizard_subtitle',
                        html: '<h2>' + _t('This wizard will guide you through the initial setup of Zenoss.  Click <strong>Get Started</strong> to begin.') + '</h2>'
                    }, {
                        layout: 'hbox',
                        items: [{
                            xtype: 'wizardstep',
                            stepNumber: 1,
                            iconPath: '/++resource++zenui/img/users.png',
                            stepTitle: _t('Setup Users'),
                            stepDescription: _t('Set the admin password and create your user account.')
                        },{
                            xtype: 'wizardstep',
                            stepNumber: 2,
                            iconPath: '/++resource++zenui/img/networks.png',
                            stepTitle: _t('Network Discovery'),
                            stepDescription: _t('Discover devices to monitor.')
                        },{
                            xtype: 'wizardstep',
                            stepNumber: 3,
                            iconPath: '/++resource++zenui/img/monitoring.png',
                            stepTitle: _t('Add Infrastructure'),
                            stepDescription: _t('Manually add the devices in your infrastructure.')
                        }, {
                            xtype: 'image',
                            itemId: 'get_started',
                            src: 'img/qs_img_3.png',
                            width: 230
                        }]
                    }]
                }]
            });
            this.callParent([config]);
        },
        initComponent: function() {

            this.callParent(arguments);
        }
    });




})();
