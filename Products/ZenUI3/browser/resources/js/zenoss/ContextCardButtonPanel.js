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
        this.contextUid = uid;
        this.layout.activeItem.setContext(uid);
    },
    cardChangeHandler: function(panel) {
        panel.setContext(this.contextUid);
    }
});

Ext.reg('ContextCardButtonPanel', Zenoss.ContextCardButtonPanel);

})();
