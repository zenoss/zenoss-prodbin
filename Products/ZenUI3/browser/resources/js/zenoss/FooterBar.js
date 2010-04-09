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


Zenoss.footerHelper = function(itemName, footerBar) {
    var addDialog, addToZenPackDialog, items;

    footerBar = footerBar || Ext.getCmp('footer_bar');

    // For now, we will monkey-patch a setContext onto it.

    footerBar.setContext = function(contextUid) {
        Ext.each(this.items.items, function(i) {
            if (i.setContext) { i.setContext(contextUid); }} );
    };

    addDialog = new Zenoss.SmartFormDialog({
        itemId: 'addDialog',
        items: [{
            xtype: 'textfield',
            name: 'idTextField',
            fieldLabel: _t('ID'),
            allowBlank: false
        }]
    });

    addToZenPackDialog = new Zenoss.AddToZenPackWindow();

    items = [
        {
            xtype: 'button',
            iconCls: 'add',
            disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
            tooltip: _t('Add a child to the selected organizer'),
            menu: {
                items: [
                    {
                        text: _t('Add ') + itemName,
                        listeners: {
                            click: function() {
                                addDialog.setTitle(_t('Add ') + itemName);
                                addDialog.setSubmitHandler(function(values) {
                                    footerBar.fireEvent('buttonClick', 'addClass', values.idTextField);
                                });
                                addDialog.show();
                            }
                        },
                        ref: 'buttonAddClass'
                    }, {
                        text: _t('Add ') + itemName + _t(' Organizer'),
                        listeners: {
                            click: function () {
                                addDialog.setTitle(_t('Add ') + itemName + _t(' Organizer'));
                                addDialog.setSubmitHandler(function(values) {
                                    footerBar.fireEvent('buttonClick', 'addOrganizer', values.idTextField);
                                });
                                addDialog.show();
                            }
                        },
                        ref: 'buttonAddOrganizer'
                    }
                ]
            },
            ref: 'buttonAdd'
        }, {
            xtype: 'button',
            iconCls: 'delete',
            disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
            tooltip: _t('Delete the selected ') + itemName.toLowerCase()
                        + _t(' or organizer.'),
            listeners: {
                click: function() {
                    Ext.MessageBox.show({
                        title: _t('Delete ' + itemName),
                        msg: _t('The selected ') + itemName.toLowerCase()
                                + _t(' will be deleted.'),
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
        }, ' ', {
            xtype: 'ContextMenu',
            disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
            tooltip: _t('Context-sensitive actions'),
            menu: {
                items: [
                    {
                        text: _t('Add to ZenPack'),
                        listeners: {
                            click: function() {
                                addToZenPackDialog.setTarget(this.contextUid);
                                addToZenPackDialog.show();
                            }
                        },
                        ref: 'buttonAddToZenPack'
                    }
                ]
            },
            ref: 'buttonContextMenu'
        }, '-'
    ];

    footerBar.add(items);
};

})();
