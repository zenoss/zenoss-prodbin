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
    var router = Zenoss.remote.DeviceRouter,
        ModelerPluginForm,
        ZPROP_NAME = 'zCollectorPlugins',
        ModelerPluginPanel;
    Ext.define("Zenoss.form.ModelerPluginForm", {
        extend:"Ext.form.FormPanel",
        alias: "widget:modelerpluginform",
        constructor: function(config) {
            var me = this;
            config = config || {};
            Ext.apply(config, {
                labelAlign: 'top',
                paramsAsHash: true,
                frame: true,
                autoScroll: 'y',
                defaults: {
                    labelStyle: 'font-size: 13px; color: #5a5a5a',
                    anchor: '100%'
                },
                items: [{
                    xtype: 'displayfield',
                    name: 'path',
                    id: 'modeler-plugin-path',
                    fieldLabel: _t('Path')
                },{
                    xtype: 'displayfield',
                    id: 'modeler-plugin-doc',
                    name: 'doc',
                    height: 65,
                    autoScroll: true,
                    ref: 'doc',
                    toolTip: 'Select a single plugin to see the docs',
                    fieldLabel: _t('Plugin Documentation')
                }],
                buttonAlign: 'left',
                buttons: [{
                    text: _t('Save'),
                    ref: 'savebtn',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(btn){
                        var values = me.modelerPlugins.getValue(),
                            panel = me,
                            uid = me.uid;
                        router.setZenProperty({uid:uid,
                                               zProperty: ZPROP_NAME,
                                               value:values},
                                              function(response){
                                                  if (response.success){
                                                      Zenoss.message.info('Updated Modeler Plugins');
                                                      Ext.getCmp('modeler-plugin-path').setValue(response.data.path);
                                                      panel.toggleDeleteButton(response.data.path);
                                                  }

                                              });
                    }
                },{
                    text: _t('Cancel'),
                    ref: 'cancelbtn',
                    handler: function() {
                        if (me.uid) {
                            me.setContext(me.uid);
                        }
                    }
                },{
                    text: _t('Delete Local Copy'),
                    ref: 'deleteBtn',
                    hidden: true,
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(btn) {
                        var panel = me;
                        // show a confirmation
                        new Zenoss.dialog.SimpleMessageDialog({
                            title: _t('Delete zProperty'),
                            msg: _t("Are you sure you want to delete the local copy of zCollectorPlugin?"),
                            buttons: [{
                                xtype: 'DialogButton',
                                text: _t('OK'),
                                handler: function() {
                                    if (panel.uid) {
                                        router.deleteZenProperty({
                                            uid: panel.uid,
                                            zProperty: ZPROP_NAME
                                        }, function(response){
                                            panel.setContext(panel.uid);
                                        });
                                    }
                                }
                            }, {
                                xtype: 'DialogButton',
                                text: _t('Cancel')
                            }]
                        }).show();
                    }
                }],
                cls: 'device-overview-form-wrapper',
                bodyCssClass: 'device-overview-form'
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            if (this.modelerPlugins) {
                this.modelerPlugins.destroy();
            }
            Ext.getCmp('modeler-plugin-doc').setValue('');
            this.uid = uid;
            // get the modeler plugins
            router.getZenProperty({
                uid: uid,
                zProperty: ZPROP_NAME
            }, Ext.bind(this.loadData, this));

            router.getModelerPluginDocStrings({
                uid: uid
            }, Ext.bind(this.loadDocs, this));

        },
        toggleDeleteButton: function(path){
            // show the delete button if locally defined
            var localPath = this.uid.replace('/zport/dmd/Devices', ''),
                deleteBtn = this.getButton("deleteBtn");

            // can't delete the root
            if (path == '/') {
                deleteBtn.hide();
                return;
            }
            if (localPath == path) {
                deleteBtn.show();
            }else{
                deleteBtn.hide();
            }
        },
        getButton: function(ref) {
            return this.query(Ext.String.format("button[ref='{0}']", ref))[0];
        },
        loadData: function(response) {
            if (response.success) {
                var data = response.data,
                    clickHandler,
                    panel = this;

                Ext.getCmp('modeler-plugin-path').setValue(data.path);
                this.toggleDeleteButton(data.path);
                clickHandler = function(select, record) {
                    // display the docs for the record clicked
                    var value = record.data.field1;
                    panel.showDocFor(value);
                };
                // add the multi select
                this.add({
                    name: 'modelerPlugins',
                    ref: 'modelerPlugins',
                    xtype: 'itemselector',
                    fieldLabel: _t('Modeler Plugins'),
                    imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
                    drawUpIcon: true,
                    drawDownIcon: true,
                    drawTopIcon: true,
                    drawBotIcon: true,
                    store: data.options,
                    value: data.value,
                    listeners: {
                        afterrender: function() {
                            // HACK: have to go into the internals of MultiSelect to properly register a click
                            // handler
                            this.modelerPlugins.fromField.boundList.on('itemclick', clickHandler);
                            this.modelerPlugins.toField.boundList.on('itemclick', clickHandler);
                        },
                        scope: this
                    }
                });
                this.doLayout();

            }
        },
        showDocFor: function(plugin) {
            if (plugin && this.docs && this.docs[plugin]) {
                this.doc.setValue(this.docs[plugin]);
            }else{
                this.doc.setValue(String.format(_t('No documentation found for {0}'), plugin));
            }
        },
        loadDocs: function(response) {
            if (response.success) {
                this.docs = response.data;
            }
        }
    });


    /**
     * Place the form inside a panel for sizing
     **/
    Ext.define("Zenoss.form.ModelerPluginPanel", {
        alias:['widget.modelerpluginpanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            var form = Ext.create("Zenoss.form.ModelerPluginForm", {});
            Ext.applyIf(config, {
                layout: 'fit',
                width: 800,
                autoScroll: 'auto',
                items: [form]
            });
            this.callParent(arguments);
            this.form = form;
        },
        setContext: function(uid) {
            this.form.setContext(uid);
        }
    });




})();