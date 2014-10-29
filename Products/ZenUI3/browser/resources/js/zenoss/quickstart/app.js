/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    Ext.ns('Zenoss.quickstart.Wizard');

    Zenoss.quickstart.Wizard.wizardSteps = [{
        xtype: 'wizardoutlineview'
    }, {
        xtype: 'wizardadduserview'
    }, {
        xtype: 'wizardautodiscoveryview'
    }, {
        xtype: 'wizardadddeviceview'
    }];
    Zenoss.quickstart.Wizard.controllers = ["OutlineController", "AddUserController", "AutoDiscoveryController", "AddDeviceController"];
    Zenoss.quickstart.Wizard.events = Ext.create('Ext.util.Observable', {});
    Zenoss.quickstart.Wizard.events.addEvents('beforeapplaunch');


    /**
     * Allow zenpacks to add/remove steps
     **/
    Zenoss.quickstart.Wizard.addStep = function(config, position) {
        var steps = Zenoss.quickstart.Wizard.wizardSteps;
        steps = steps.splice(position, 0, config);
    };

    Zenoss.quickstart.Wizard.overrideStep = function(config, position) {
        Zenoss.quickstart.Wizard.wizardSteps[position] = config;
    };

    Zenoss.quickstart.Wizard.removeStep = function(position) {
        delete Zenoss.quickstart.Wizard.wizardSteps[position];
    };


    Zenoss.quickstart.Wizard.addController = function(name, id,  app) {
        var controller = Ext.create(name, {
            application: app,
            id: id
        });
        controller.doInit(app);
        app.controllers.add(controller);
    };

    Ext.application({
        name: 'Zenoss.quickstart.Wizard',
        appFolder: "/++resource++zenui/js/zenoss/quickstart",
        controllers: Zenoss.quickstart.Wizard.controllers,
        currentStep: 0,
        launch: function() {
            Zenoss.quickstart.Wizard.events.fireEvent('beforeapplaunch', this);
            var panel = Ext.create('Ext.Panel', {
                layout: 'border',
                renderTo: 'center_panel',
                height: 400,
                style: {
                    padding: "40px 0px 0px 100px"
                },
                items: [{
                    region: 'north',
                    layout: 'vbox',
                    items: [,{
                        id: 'wizard_step_id',
                        html: "<h1> Wizard Steps and outline here </h1>",
                        height: 28
                    },{
                        html: '<hr />',
                        width: 870,
                        height: 25
                    }],
                    height: 70
                }, {
                    id: 'wizard_card_panel',
                    region: 'center',
                    layout: 'card',
                    items: Zenoss.quickstart.Wizard.wizardSteps,
                    dockedItems:[{
                        dock: 'bottom',
                        itemId: 'toolbar',
                        baseCls: 'no-grey',
                        cls: 'no-grey',
                        hidden: true,
                        xtype: 'toolbar',
                        items: [{
                            xtype: 'button',
                            hidden: true,
                            itemId: 'doneButton',
                            text: _t('Done'),
                            handler: function() {
                                window.globalApp.doneAddingDevices();
                            }
                        }, {
                            xtype: 'button',
                            itemId: 'previousButton',
                            text: _t('Previous'),
                            handler: function() {
                                window.globalApp.fireEvent('previousstep');
                            }
                        }, {
                            xtype: 'tbspacer',
                            width: 763
                        }, {
                            xtype: 'button',
                            itemId: 'nextButton',
                            text: _t('Next'),
                            handler: function() {
                                window.globalApp.fireEvent('nextstep');
                            }
                        }, {
                            xtype: 'button',
                            hidden: true,
                            itemId: 'finishButton',
                            text: _t('Finish'),
                            handler: function() {
                                window.globalApp.fireEvent('finish');
                            }
                        }]
                    }]
                }]
            });
            // set shortcuts for wizard controls
            this.mainPanel = panel;
            this.cardPanel = Ext.getCmp('wizard_card_panel');
            this.titlePanel = Ext.getCmp('wizard_step_id');
            this.previous = this.cardPanel.query('button[itemId="previousButton"]')[0];
            this.next = this.cardPanel.query('button[itemId="nextButton"]')[0];
            this.done = this.cardPanel.query('button[itemId="doneButton"]')[0];
            this.finish = this.cardPanel.query('button[itemId="finishButton"]')[0];
            this.toolbar = this.cardPanel.getDockedItems()[0];

            // save any GET parameters
            this.params = Ext.Object.fromQueryString(window.location.search);

            // setup the wizard button events
            this.setupEvents();
            this.setTitle();
            this.deepLink();
            window.globalApp = this;
        },
        setupEvents: function() {
            this.addEvents(
                /**
                 * @event finish
                 * Fires when the wizard is finished
                 */
                'finish',
                /**
                 * @event next button pressed
                 * Fires when the next button on the wizard is pressed
                 * @param {integer} The step that you are moving towards
                 */
                'nextstep',
                /**
                 * @event previous button pressed
                 * Fires when the previous button on the wizard is pressed
                 * @param {integer} The page you are about to go to
                 */
                'previousstep');
            this.on('nextstep', this.pressNext, this);
            this.on('previousstep', this.pressPrevious, this);
        },
        /**
         * Sets the H1 title based on the current wizard step
         *
         **/
        setTitle: function() {
            var cardTitle = this.cardPanel.layout.getActiveItem().stepTitle;
            if (this.currentStep > 0 && !this.params.came_from) {
                cardTitle = Ext.String.format("{0} {1}: {2}",
                                          _t("Step"),
                                          this.currentStep,
                                          cardTitle);
            }
            this.titlePanel.update(Ext.String.format("<h1>{0}</h1>", cardTitle));
        },
        /**
         * Hide the toolbar for the initial page.
         **/
        setToolbar: function() {
            if (this.currentStep > 0) {
                this.toolbar.show();
            } else {
                this.toolbar.hide();
            }
        },
        /**
         * This is called when the application is loaded.
         * If we have a history in the URL then go straight to that step, otherwise
         * set the history for the first page.
         **/
        deepLink: function() {
            // called when
            var token = Ext.History.getToken(),
                cardPanel = this.cardPanel,
                i=0,
                me = this;
            if (Ext.isNumeric(token)) {
                token = parseInt(token);
            }

            // if it is not set or 0
            if (token) {
                this.currentStep = token;
                if (Ext.isNumeric(token)) {
                    cardPanel.layout.setActiveItem(this.currentStep);
                } else {
                    // look it up by step id
                    cardPanel.items.each(function(item) {
                        if (item.stepId == token) {
                            cardPanel.layout.setActiveItem(item);
                            me.currentStep = i;
                            return false;
                        }
                        i++;
                    });
                }

                this.updateWizard();
            } else {
                this.updateHistory();
            }
        },
        /**
         * Updates the History token with the current step. It is always assumed to
         * be the number of which step we are on.
         **/
        updateHistory: function() {
            var step = this.currentStep;
            Ext.History.add(step);
        },
        /**
         * This updates both the history and the toolbar buttons
         * based on which step of the wizard we are on.
         * It is expected to be called after the card panel is set
         * and application variable "currentStep" is set;
         **/
        updateWizard: function() {
            var stepCount = this.cardPanel.items.getCount() - 1,
                params = this.params;
            this.setHeight();
            this.setTitle();
            this.setToolbar();
            this.updateHistory();

            // we can redirected here to add devices after the user has finished the wizard
            if (params && params.came_from) {
                this.done.show();
                this.next.hide();
                this.previous.hide();
                this.finish.hide();
            }else if (this.currentStep == stepCount) {
                // they are on the last step
                this.next.hide();
                this.finish.show();
            } else {
                // they have more steps to go
                this.next.show();
                this.finish.hide();
            }
        },
        setHeight: function() {
            var item = this.cardPanel.layout.getActiveItem();
            if (item.stepHeight) {
                this.mainPanel.setHeight(item.stepHeight);
            } else {
                this.mainPanel.setHeight(600);
            }
        },
        formValidityChange: function(isValid) {
            this.next.setDisabled(!isValid);
        },
        /**
         * Application handler for the previouspressed event
         **/
        pressPrevious:function () {
            var form = this.cardPanel;

            this.currentStep--;

            // set the active page
            form.layout.setActiveItem(this.currentStep);
            this.updateWizard();
        },
        /**
         * Application handler for the nextstep event
         **/
        pressNext:function () {
            var form = this.cardPanel;
            this.currentStep++;

            // set the active page
            form.layout.setActiveItem(this.currentStep);
            this.updateWizard();
        },
        doneAddingDevices: function() {
            var params = this.params;
            window.location = params.came_from;
        }
    });
})();
