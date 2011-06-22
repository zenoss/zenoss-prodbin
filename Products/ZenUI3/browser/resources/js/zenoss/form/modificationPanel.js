/*
  ###########################################################################
  #
  # This program is part of Zenoss Core, an open source monitoring platform.
  # Copyright (C) 2011, Zenoss Inc.
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
    var router = Zenoss.remote.DeviceRouter,
        ModificationGrid,
        ModificationPanel,
        ZF = Ext.ns('Zenoss.form');

    Zenoss.form.showModificationsDialog = function(uid, types) {
        var win = new Zenoss.dialog.CloseDialog({
            title: _t('Modifications'),
            cls: 'white-background-panel',
            closeAction: 'destroy',
            resizable: false,
            height: 650,
            width: 800,
            items: [{
                xtype: 'modificationpanel',
                ref: 'modificationPanel',
                types: types
            }],
            buttons: [{
                xtype: 'DialogButton',
                text: _t('Close')
            }]
        });
        win.modificationPanel.setContext(uid);
        win.show();
    };

    /**
     * GetModifications
     * This method organizes the parameters for
     * direct request for the tree loader.
     * The standard tree loader doesn't really handle extra parameters well
     **/
    function getModifications(uid, types, callback) {
        router.getModifications({
            id: uid,
            types: types
        }, callback);
    }

    ModificationGrid = Ext.extend(Ext.ux.tree.TreeGrid, {

        constructor: function(config) {
            Ext.applyIf(config, {
                stripeRows: true,
                autoScroll: true,
                cls: 'x-tree-noicon',
                height: 550,
                border: false,
                enableSort: false,
                useArrows: true,
                loader: new Ext.ux.tree.TreeGridLoader({
                    directFn: getModifications,
                    paramOrder: ['types'],
                    baseParams: {
                        types: config.types
                    }
                }),
                columns: [{
                    header: _t("Object"),
                    id: 'obj',
                    dataIndex: 'obj',
                    width: 200,
                    sortable: false
                },{
                    header: _t("Type"),
                    id: 'meta_type',
                    dataIndex: 'meta_type',
                    width: 100,
                    sortable: false
                },{
                    header: _t("Time of Change"),
                    id: 'timeOfChange',
                    dataIndex: 'timeOfChange',
                    width: 200,
                    sortable: false
                },{
                    id: 'user',
                    dataIndex: 'user',
                    header: _t('User'),
                    width: 100,
                    sortable: false
                },{
                    id: 'description',
                    dataIndex: 'description',
                    header: _t('Description'),
                    width:  300,
                    sortable: false,
                    tpl: new Ext.XTemplate( '<span title="{description}">{description}</span>')
                }]
            });
            ModificationGrid.superclass.constructor.call(this, config);

        },
        setContext: function(uid) {
            var root = this.getRootNode();
            root.setId(uid);
            root.reload();
        }
    });

    ModificationPanel = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                bodyStyle: {
                    overflow: 'auto'
                },
                height: 550,
                items: [new ModificationGrid({
                    ref: 'modificationGrid',
                    types: config.types
                })]

            });
            ModificationPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            this.modificationGrid.setContext(uid);
        }
    });

    Ext.reg('modificationpanel', ModificationPanel);

}());