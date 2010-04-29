/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
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
function createClickHandler(bubbleTargetId) {
    return function(button, event) {
        Ext.getCmp(bubbleTargetId).fireEvent('buttonClick', button.id);
    };
}

// TreeFooterBar is legacy.  Please do not use this.  See the helper
// function below.  Thank you.
Zenoss.TreeFooterBar = Ext.extend(Ext.Toolbar, {

    constructor: function(config) {
        Ext.applyIf(config, {
            border: false,
            items: [
                {
                    id: 'addButton',
                    iconCls: 'add',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    tooltip: 'Add a child to the selected organizer',
                    handler: createClickHandler(config.bubbleTargetId)
                }, {
                    id: 'deleteButton',
                    iconCls: 'delete',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    tooltip: 'Delete the selected node',
                    handler: createClickHandler(config.bubbleTargetId)
                }
            ]
        });
        Zenoss.TreeFooterBar.superclass.constructor.call(this, config);
    }

});

Ext.reg('TreeFooterBar', Zenoss.TreeFooterBar);


// options is comprised of the following:
//      addToZenPack: true puts the Add To ZenPack icon in, default true
//      hasOrganizers: true puts the Add ___  Organizer in, default true
//      customAddDialog: config for a SmartFormDialog to override the default
//      deleteMenu: needs separate menu items for deleting organizers and items
//      contextGetter: fetches the context UIDs for the specific page

Zenoss.footerHelper = function(itemName, footerBar, options) {
    var addToZenPackDialog, items;

    options = Ext.applyIf(options || {}, {
        addToZenPack: true,
        hasOrganizers: true,
        hasContextMenu: true,
        customAddDialog: {},
        buttonContextMenu: {},
        contextGetter: null,
        onGetDeleteMessage: function (itemName) {
            return String.format(_t('The selected {0} will be deleted.'), itemName.toLowerCase());
        },
        onGetAddDialogItems: function () {
            return [{
                xtype: 'textfield',
                name: 'id',
                fieldLabel: _t('Name'),
                allowBlank: false
            }];
        }
    });

    Ext.applyIf(options.buttonContextMenu, {
        xtype: 'ContextMenu',
        disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
        tooltip: _t('Context-sensitive actions'),
        menu: {
            items: []
        },
        ref: 'buttonContextMenu'
    });

    footerBar = footerBar || Ext.getCmp('footer_bar');

    // For now, we will monkey-patch a setContext onto it.
    footerBar.setContext = function(contextUid) {
        Ext.each(this.items.items, function(i) {
            if (i.setContext) { i.setContext(contextUid); }} );
    };


    function showAddDialog(title, event) {
        var handler, dialog, addDialogConfig;

        // Shallow copy config to avoid mangling the original config
        addDialogConfig = Ext.apply({}, options.customAddDialog);

        handler = function(values) {
            footerBar.fireEvent('buttonClick', event, values.id, values);
        };

        addDialogConfig = Ext.applyIf(addDialogConfig, {
            submitHandler: handler,
            items: options.onGetAddDialogItems(),
            title: title
        });

        dialog = new Zenoss.SmartFormDialog(addDialogConfig);
        dialog.show();
    };

    items = [
        {
            xtype: 'FlexButton',
            iconCls: 'add',
            disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
            tooltip: _t('Add a child to the selected organizer'),
            menu: {
                items: [
                    {
                        text: String.format(_t('Add {0}'), itemName),
                        listeners: {
                            click: showAddDialog.createCallback(
                                    String.format(_t('Add {0}'), itemName),
                                    'addClass')
                        }
                    }
                ]
            },
            ref: 'buttonAdd'
        },
        {
            xtype: 'FlexButton',
            iconCls: 'delete',
            disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
            tooltip: String.format(_t('Delete {0}'), itemName),
            listeners: {
                click: function() {
                    Ext.MessageBox.show({
                        title: String.format(_t('Delete {0}'), itemName),
                        msg: options.onGetDeleteMessage(itemName),
                        fn: function(buttonid){
                            if (buttonid=='ok') {
                                footerBar.fireEvent('buttonClick', 'delete');
                            }
                        },
                        buttons: Ext.MessageBox.OKCANCEL
                    });
                }
            },
            ref: 'buttonDelete'
        }
    ];

    if ( options.hasContextMenu || options.addToZenPack ) {
        items.push(' ');
        items.push(options.buttonContextMenu);
    }

    items.push('-');

    footerBar.add(items);

    if (options.hasOrganizers)
    {
        footerBar.buttonAdd.add({
            text: String.format(_t('Add {0} Organizer'), itemName),
            listeners: {
                click: showAddDialog.createCallback(
                         String.format(_t('Add {0} Organizer'), itemName),
                         'addOrganizer')
            },
            ref: 'buttonAddOrganizer'
        });

        footerBar.buttonDelete.add({
            text: String.format(_t('Delete {0} Organizer'), itemName),
            ref: 'buttonDeleteOrganizer',
            listeners: {
                click: function() {
                    Ext.MessageBox.show({
                        title: String.format(_t('Delete {0} Organizer'), itemName),
                        msg: String.format(_t('The selected {0} organizer will be deleted.'),
                                itemName.toLowerCase()),
                        fn: function(buttonid){
                            if (buttonid=='ok') {
                                footerBar.fireEvent('buttonClick', 'deleteOrganizer');
                            }
                        },
                        buttons: Ext.MessageBox.OKCANCEL
                    });
                }
            }
        });
    }

    if (options.addToZenPack) {
        addToZenPackDialog = new Zenoss.AddToZenPackWindow();

        footerBar.buttonContextMenu.menu.add({
            ref: 'buttonAddToZenPack',
            text: String.format(_t('Add {0} to ZenPack'), itemName),
            listeners: {
                click: function() {
                    var target = options.contextGetter.getUid();
                    if ( ! target ) {
                        return;
                    }
                    addToZenPackDialog.setTarget(target);
                    addToZenPackDialog.show();
                }
            }
        });

        if ( options.contextGetter.hasTwoControls() ) {

            footerBar.buttonContextMenu.menu.add({
                ref: 'buttonAddOrganizerToZenPack',
                text: String.format(_t('Add {0} Organizer to ZenPack'), itemName),
                listeners: {
                    click: function() {
                        var target = options.contextGetter.getOrganizerUid();
                        if ( ! target ) {
                            return;
                        }
                        addToZenPackDialog.setTarget(target);
                        addToZenPackDialog.show();
                    }
                }
            });

        }

    }

};

})();
