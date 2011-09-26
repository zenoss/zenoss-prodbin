/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
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
Ext.define("Zenoss.ContextCardButtonPanel", {
    extend:"Zenoss.CardButtonPanel",
    alias: ['widget.ContextCardButtonPanel'],
    contextUid: null,
    initEvents: function() {
        this.on('cardchange', this.cardChangeHandler, this);
        Zenoss.CardButtonPanel.superclass.initEvents.call(this);
    },
    setContext: function(uid) {
        var panel;
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



var oldActiveItem = Ext.layout.CardLayout.prototype.setActiveItem;
var oldInitEvents = Ext.layout.CardLayout.prototype.initEvents;

Ext.override(Ext.layout.CardLayout, {
    initEvents: function() {
        oldInitEvents.apply(this, arguments);
        this.owner.addEvents('cardchange');
    },
    setActiveItem: function(item) {
        oldActiveItem.apply(this, arguments);
        this.owner.fireEvent('cardchange', this.owner, item);
    }
});

Ext.define("Zenoss.ContextCardPanel", {
    extend:"Ext.Panel",
    alias: ['widget.contextcardpanel'],
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
        if (panel!=this && panel.setContext) {
            panel.setContext(this.contextUid);
        }
    }

});



Ext.define("Zenoss.ContextCardTabPanel", {
    extend:"Ext.TabPanel",
    alias: ['widget.contextcardtabpanel'],
    contextUid: null,
    initEvents: function() {
        Zenoss.ContextCardTabPanel.superclass.initEvents.call(this);
        this.on('beforetabchange', this.cardChangeHandler, this);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.cardChangeHandler(this, this.layout.activeItem);
    },
    cardChangeHandler: function(tabpanel, tab, oldtab) {
        if (tab!=oldtab && tab.setContext) {
            tab.setContext.call(tab, this.contextUid);
        }
    }

});



})();
