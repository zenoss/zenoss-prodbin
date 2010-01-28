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
 * @class Zenoss.ContextCardButtonPanel
 * @extends Zenoss.CardButtonPanel
 * Support context-driven loading
 * @constructor
 */
Zenoss.ContextCardButtonPanel = Ext.extend(Zenoss.CardButtonPanel, {
    contextUid: null,
    initEvents: function() {
        this.on('cardchange', this.cardChangeHandler, this);
        Zenoss.CardButtonPanel.superclass.initEvents.call(this);
    },
    setContext: function(uid) {
        if (this.contextUid!=uid) {
            this.contextUid = uid;
            panel = this.layout.activeItem;
            if (panel.setContext) {
                panel.setContext(uid);
            }
        }
    },
    cardChangeHandler: function(panel) {
        if (panel.setContext) {
            panel.setContext(this.contextUid);
        }
    }
});

Ext.reg('ContextCardButtonPanel', Zenoss.ContextCardButtonPanel);

var oldActiveItem = Ext.layout.CardLayout.prototype.setActiveItem;
var oldInitEvents = Ext.layout.CardLayout.prototype.initEvents;

Ext.override(Ext.layout.CardLayout, {
    initEvents: function() {
        oldInitEvents.apply(this, arguments);
        this.container.addEvents('cardchange');
    },
    setActiveItem: function(item) {
        oldActiveItem.apply(this, arguments);
        this.container.fireEvent('cardchange', this.container, item);
    }
})

Zenoss.ContextCardPanel = Ext.extend(Ext.Panel, {
    contextUid: null,
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'card'
        });
        Zenoss.ContextCardPanel.superclass.constructor.call(this, config);
        this.on('cardchange', this.cardChangeHandler, this);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.cardChangeHandler(this.layout.activeItem);
    },
    cardChangeHandler: function(panel) {
        if (panel.setContext) {
            panel.setContext(this.contextUid);
        }
    }

});
Ext.reg('contextcardpanel', Zenoss.ContextCardPanel);

})();
