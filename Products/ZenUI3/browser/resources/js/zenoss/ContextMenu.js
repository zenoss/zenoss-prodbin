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
(function () {
Ext.ns('Zenoss');
Zenoss.ContextConfigureMenu = Ext.extend( Ext.Button,{
    /**
     * onSetContext abstract function called when the context for the menu is
     * potentially changed
     */
    onSetContext: Ext.emptyFn,
    /**
     * onGetMenuItems abstract function; hook to provide 
     * more menu items based on context
     * @param {string} uid; item to get menu items for
     */
    onGetMenuItems: function(uid){ return []; },
    /**
     * Called when an item in the menu is selected
     * @param {object} this, the ContextConfigureMenu
     * @param {object} the menu item selection
     */
    onSelectionChange: Ext.emptyFn,
    /**
     * Filter out menu items;  Return true if it should be kept, false otherwise
     * @param {ContextConfigureMenu}
     * @param {Object} itemConfig
     */
    filterMenu: function(contextMenu, config) {return true;},
    /**
     * The object id for which the context menu belongs to
     */
    contextId: null,
     /**
     * Menu ids used to get dialog menus that will be used in context menu;
     * Empty or null if no items from old menu items is desired
     */
    menuIds: ['More','Manage','Edit', 'Actions','Add','TopLevel'],
    menu: {items:[]},
    disabled: true,
    /**
     * @cfg {array} menutItems
     * items that should always be included in the menu
     */
    menuItems: [],
    constructor: function(config){
        config = config || {};
        Ext.apply(config, {
            id: 'context-configure-menu',
            iconCls: 'customize',
            id: 'context-configure-menu'
        });
    Zenoss.ContextConfigureMenu.superclass.constructor.call(this, config);
    },
    /**
     * set the UID, menus for the corresponding object will be determined and
     * set
     * @param {Object} uid
     */
    setContext: function(uid) {
        this.disable();
        this.onSetContext(uid);
        this.contextId = uid;
        var menu = this.menu;
        menu.removeAll();
        this.getMenuItems(uid);
    },
    /**
     * private
     * gets the menu items to be displayed
     * @param {Object} uid
     */
    getMenuItems: function(uid){
        var callback = function(provider, response){
            //get statically defined menu items
            var menuItems = [];
            if (this.menuItems.length !== 0) {
                menuItems = menuItems.concat(this.menuItems);
            }
            //get any context specific menus if defined
            var moreMenuItems = this.onGetMenuItems(this.contextId);
            if (moreMenuItems !== null || moreMenuItems.length > 0){
                menuItems = menuItems.concat(moreMenuItems);
            }
            //menus from router
            var itemConfigs = response.result.menuItems;
            var filterFn = function(val) {
                return this.filterMenu(this, val);
            };
            itemConfigs = Zenoss.util.filter(itemConfigs, filterFn, this);
            if (itemConfigs){
                menuItems = menuItems.concat(itemConfigs);
            }
            //add all menus and set handlers if needed
            Ext.each(menuItems, function(item){
                if (!Ext.isDefined(item.handler)) {
                    item.handler = this.defaultHandler.createDelegate(this);
                }
                this.menu.add(item);
            }, this);
            if(this.menu.items.length !== 0){
                this.enable();
            }
        };
        var args = {
            'uid': uid
        };
        if (this.menuIds !== null && this.menuIds.length >= 1){
            args['menuIds'] = this.menuIds;
        } 
        Zenoss.remote.DetailNavRouter.getContextMenus(args, callback, this);
    },
    /**
     * private
     * handler used if a menu item does not have a handler defined
     * @param {Object} button
     */
    defaultHandler: function(button) {
        var dialog = new Zenoss.dialog.DynamicDialog();
        dialog.setTitle(_t(button.text.replace(/\.\.\./g, '')));
        dialog.show();
        dialog.body.load({
            scripts: true,
            url: this.contextId + '/' + button.viewName
        });
    }
});

Ext.reg('ContextConfigureMenu', Zenoss.ContextConfigureMenu);

})();
