/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
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
function createClickHandler(bubbleTargetId) {
    return function(button, event) {
        Ext.getCmp(bubbleTargetId).fireEvent('buttonClick', button.id);
    };
}

// options comprises the following:
//      addToZenPack: true puts the Add To ZenPack icon in, default true
//      hasOrganizers: true puts the Add ___  Organizer in, default true
//      customAddDialog: config for a SmartFormDialog to override the default
//      deleteMenu: needs separate menu items for deleting organizers and items,
//                  works in conjunction with hasOrganizers
//      contextGetter: fetches the context UIDs for the specific page

Zenoss.footerHelper = function(itemName, footerBar, options) {
    var addToZenPackDialog, items;

    options = Ext.applyIf(options || {}, {
        addToZenPack: true,
        hasOrganizers: true,
        deleteMenu: true,
        hasContextMenu: true,
        customAddDialog: {},
        buttonContextMenu: {},
        contextGetter: null,
        onGetDeleteMessage: function (itemName) {
            return Ext.String.format(_t('The selected {0} will be deleted.'), itemName.toLowerCase());
        },
        onGetAddDialogItems: function () {
            return [{
                xtype: 'textfield',
                name: 'id',
                fieldLabel: _t('Name'),
                anchor: '80%',
                allowBlank: false
            }];
        },
        onGetItemName: function() {
            return itemName;
        }
    });

    Ext.applyIf(options.buttonContextMenu, {
        xtype: 'ContextMenu',
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
            if (i.setContext) { i.setContext(contextUid); }
        });
    };


    function showAddDialog(template, event) {
        var handler, dialog, addDialogConfig;

        // Shallow copy config to avoid mangling the original config
        addDialogConfig = Ext.apply({}, options.customAddDialog);

        handler = function(values) {
            footerBar.fireEvent('buttonClick', event, values.id, values);
        };

        addDialogConfig = Ext.applyIf(addDialogConfig, {
            submitHandler: handler,
            items: options.onGetAddDialogItems(),
            title: Ext.String.format(template, options.onGetItemName())
        });
         // we have some screens with a higher zindex then they should, so for these popups, seed the zindex to be higher
        var oldSeed = Ext.WindowManager.zseed;
         Ext.WindowManager.zseed = 20000;
        dialog = new Zenoss.SmartFormDialog(addDialogConfig);
        dialog.show();
        // now set the seed down again so I don't mess up any others
        Ext.WindowManager.zseed = oldSeed;
    }

    items = [
        {
            xtype: 'FlexButton',
            id: 'footer_add_button',
            iconCls: 'add',
            hidden: Zenoss.Security.doesNotHavePermission('Add DMD Objects'),
            tooltip: _t('Add a child to the selected organizer'),
            menu: {
                items: [
                    {
                        text: Ext.String.format(_t('Add {0}'), itemName),
                        listeners: {
                            click: Ext.pass(showAddDialog, ['Add {0}', 'addClass'])
                        }
                    }
                ]
            },
            ref: 'buttonAdd'
        },
        {
            xtype: 'FlexButton',
            id: 'footer_delete_button',
            iconCls: 'delete',
            hidden: Zenoss.Security.doesNotHavePermission('Delete objects'),
            tooltip: Ext.String.format(_t('Delete {0}'), itemName),
            menu: {
                items: [{

                    text: Ext.String.format(_t('Delete {0}'), options.onGetItemName()),
                    listeners: {
                        click: function() {
                            var itemName = options.onGetItemName();
                            Ext.MessageBox.show({

                                msg: options.onGetDeleteMessage(itemName),
                                fn: function(buttonid){
                                    if (buttonid=='ok') {
                                        footerBar.fireEvent('buttonClick', 'delete');
                                    }
                                },
                                buttons: Ext.MessageBox.OKCANCEL
                            });
                        }
                    }
                }]

            },
            ref: 'buttonDelete'
        }
    ];





    if (options.hasOrganizers)
    {
        // add button
        items[0].menu.items.push({
            text: Ext.String.format(_t('Add {0} Organizer'), itemName),
            param: 'addOrganizer',
            listeners: {
                click: Ext.pass(showAddDialog, [_t('Add {0} Organizer'), 'addOrganizer'])
            },
            ref: 'buttonAddOrganizer'
        });

        if (options.deleteMenu)
        {

            items[1].menu.items.push({
                text: Ext.String.format(_t('Delete {0} Organizer'), itemName),
                ref: 'buttonDeleteOrganizer',
                listeners: {
                    click: function() {
                        var itemName = options.onGetItemName();
                        Ext.MessageBox.show({
                            title: Ext.String.format(_t('Delete {0} Organizer'), itemName),
                            msg: Ext.String.format(_t('The selected {0} organizer will be deleted.'),
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
    }

    if (options.addToZenPack) {
        addToZenPackDialog = new Zenoss.AddToZenPackWindow();
        options.buttonContextMenu.menu.items.push({
            ref: 'buttonAddToZenPack',
            text: Ext.String.format(_t('Add {0} to ZenPack'), itemName),
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

            options.buttonContextMenu.menu.items.push({
                ref: 'buttonAddOrganizerToZenPack',
                text: Ext.String.format(_t('Add {0} Organizer to ZenPack'), itemName),
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

    if ( options.hasContextMenu || options.addToZenPack ) {
        items.push(' ');
        items.push(options.buttonContextMenu);
    }

    items.push('-');
    footerBar.add(items);

};

})();
