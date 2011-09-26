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


    /**
     * @class Zenoss.form.ModificationModel
     * @extends Ext.data.Model
     * Field definitions for modifications
     **/
    Ext.define('Zenoss.form.ModificationModel',  {
        extend: 'Ext.data.Model',
        idProperty: 'obj',
        fields: [
            {name: 'obj'},
            {name: 'meta_type'},
            {name: 'timeOfChange'},
            {name: 'user'},
            {name: 'description'}
        ]
    });


    /**
     * @class Zenoss.form.ModificationStore
     * @extend Ext.data.TreeStore
     * Direct store for loading modification records
     */
    Ext.define("Zenoss.form.ModificationStore", {
        extend: "Ext.data.TreeStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.form.ModificationStore',
                remoteSort: false,
                nodeParam: 'obj',
                proxy: {
                    type: 'direct',
                    directFn: router.getModifications,
                    reader: {
                        root: 'data',
                        totalProperty: 'count'
                    }
                }
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.form.ModificationGrid", {
        extend:"Ext.tree.Panel",

        constructor: function(config) {
            Ext.applyIf(config, {
                stripeRows: true,
                autoScroll: true,
                cls: 'x-tree-noicon',
                height: 550,
                border: false,
                enableSort: false,
                useArrows: true,
                store: Ext.create('Zenoss.form.ModificationStore', {}),
                root: {

                },
                columns: [{
                    xtype: 'treecolumn', //this is so we know which column will show the tree
                    header: _t("Object"),
                    id: 'obj',
                    dataIndex: 'obj',
                    flex: 2,
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
            this.callParent(arguments);
        },
        setContext: function(uid) {
            var root = this.getRootNode();
            this.getStore().load({
                params: {
                    id: uid,
                    types: this.types
                }
            });
        }
    });

    Ext.define("ModificationPanel", {
        alias:['widget.modificationpanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                bodyStyle: {
                    overflow: 'auto'
                },
                height: 550,
                items: [Ext.create('Zenoss.form.ModificationGrid', {
                    ref: 'modificationGrid',
                    types: config.types
                })]

            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            this.modificationGrid.setContext(uid);
        }
    });



}());