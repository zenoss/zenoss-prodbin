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

(function(){

Ext.ns('Zenoss');

/**
 * @class Zenoss.ViewButton
 * @extends Ext.Button
 * A button that toggles between cards in a panel with a card layout.
 * @constructor
 */
Zenoss.ViewButton = Ext.extend(Ext.Button, {

    constructor: function(userConfig) {

        var baseConfig = {
            enableToggle: true,
            toggleGroup: 'CardButtonPanel',
            allowDepress: false
        };

        var config = Ext.apply(baseConfig, userConfig);
        Zenoss.ViewButton.superclass.constructor.call(this, config);
    }

});

Ext.reg('ViewButton', Zenoss.ViewButton);

/**
 * @class Zenoss.CardButtonPanel
 * @extends Ext.Button
 * A Panel with a card layout and toolbar buttons for switching between the
 * cards.
 * @constructor
 */
Zenoss.CardButtonPanel = Ext.extend(Ext.Panel, {

    constructor: function(config) {
        // Inner secret closure function to create the handler
        function createToggleHandler(cardPanel, panel) {
            return function(button, pressed) {
                if (pressed) {
                    cardPanel.getLayout().setActiveItem(panel.id);
                    cardPanel.fireEvent('cardchange', panel);
                }
            };
        }

        function syncButtons(me) {
//            alert(me.items.getCount());
            for (var idx=0; idx <= me.items.getCount(); ++idx) {
//                alert(idx + " of " + me.items.getCount());
//                alert(me.items.get(idx));
                addButtons(me, me.items.get(idx), idx);
            }
        }

        function addButtons(me, newComponent, index) {
//            alert(me["xtype"]);
//            alert(newComponent["xtype"]);
            if (newComponent instanceof Ext.Panel) {
                var tb = me.getTopToolbar();
//                alert(tb);
                tb.addButton({
                    xtype: 'ViewButton',
                    id: 'button_' + newComponent.id,
                    text: Ext.clean(newComponent.buttonTitle,
                                    newComponent.title, 'Undefined'),
                    pressed: (index == me.activeItem),
                    iconCls: newComponent.iconCls,
                    toggleHandler: createToggleHandler(me, newComponent)
                });
            }
        }

        Ext.applyIf(config, {
            id: 'cardPanel',
            layout: 'card',
            activeItem: 0
        });

        Ext.apply(config, {
            header: false,
            tbar: [{
                xtype: 'tbtext',
                text: _t('View: ')
            }]
        });


        Zenoss.CardButtonPanel.superclass.constructor.call(this, config);
        //syncButtons(this);
        this.addEvents('cardchange');
        var me = this;
        //this.on('added', addButtons, this);
        //this.on('beforeshow', syncButtons, this);
        this.listeners = config.listeners;
    },
    initEvents: function() {
        Zenoss.CardButtonPanel.superclass.initEvents.call(this);
    }
});

Ext.reg('CardButtonPanel', Zenoss.CardButtonPanel);

})();
