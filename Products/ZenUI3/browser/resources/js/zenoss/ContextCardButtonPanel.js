/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

Ext.ns('Zenoss');


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
            layout: {
                type: 'card',
                deferredRender: true
            }
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




})();
