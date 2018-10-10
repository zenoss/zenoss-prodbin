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

    Zenoss.quickstart.Wizard.events = Ext.create('Ext.util.Observable', {});
    Zenoss.quickstart.Wizard.events.addEvents('beforeapplaunch');

    Ext.application({
        name: 'Zenoss.quickstart.Wizard',
        appFolder: "/++resource++zenui/js/zenoss/quickstart",
        controllers: ["AutoDiscoveryController", "AddDeviceController"],
        launch: function() {
            var me = this;

            Zenoss.quickstart.Wizard.events.fireEvent('beforeapplaunch', this);

            Ext.create('Ext.Panel', {
                renderTo: 'center_panel-body',
                cls: 'wizard-container',
                items: [{
                    xtype: 'header',
                    title: Zenoss.quickstart.Wizard.pageOptions.title,
                    cls: 'wizard-title'
                }, {
                    html: '<hr>'
                }, {
                    id: 'wizard_card_panel',
                    items: [{
                        xtype: Zenoss.quickstart.Wizard.pageOptions.componentType
                    }],
                    dockedItems: [{
                        dock: 'bottom',
                        itemId: 'toolbar',
                        xtype: 'toolbar',
                        items: [{
                            xtype: 'tbfill'
                        }, {
                            xtype: 'button',
                            itemId: 'doneButton',
                            scale: 'large',
                            cls: 'wizard-done-button',
                            disabledCls: "disabled",
                            text: _t('Done'),
                            handler: function () {
                                me.doneButtonPressed();
                            }
                        }]
                    }]
                }]
            });

            // save any GET parameters
            this.params = Ext.Object.fromQueryString(window.location.search);
        },
        doneButtonPressed: function() {
            var link = Zenoss.render.link(undefined, this.params.came_from || '/zport/dmd/Dashboard');

            window.location = link;
        }
    });
})();
