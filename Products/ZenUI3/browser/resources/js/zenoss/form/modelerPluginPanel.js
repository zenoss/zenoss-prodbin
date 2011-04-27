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
    ModelerPluginForm = Ext.extend(Ext.form.FormPanel, {
        constructor: function(config) {
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
                    name: 'name',
                    fieldLabel: _t('Name'),
                    value: 'zCollectorPlugins'
                },{
                    xtype: 'displayfield',
                    name: 'path',
                    ref: 'path',
                    fieldLabel: _t('Path')
                },{
                    xtype: 'displayfield',
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
                    ref: '../savebtn',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(btn){
                        var values = this.refOwner.modelerPlugins.getValue(),
                            panel = this.refOwner,
                            uid = this.refOwner.uid;
                        if (values) {
                            values = values.split(',');
                        }else {
                            values = [];
                        }
                        router.setZenProperty({uid:uid,
                                               zProperty: ZPROP_NAME,
                                               value:values},
                                                 function(response){
                                                     if (response.success){
                                                         Zenoss.message.info('Updated Modeler Plugins');
                                                         panel.path.setValue(response.data.path);
                                                         panel.toggleDeleteButton(response.data.path);
                                                     }

                                                 });
                    }
                },{
                    text: _t('Cancel'),
                    ref: '../cancelbtn',
                    handler: function() {
                        if (this.refOwner.uid) {
                            this.refOwner.setContext(this.refOwner.uid);
                        }
                    }
                },{
                    text: _t('Delete Local Copy'),
                    ref: '../deleteBtn',
                    hidden: true,
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(btn) {
                        var panel = btn.refOwner;
                        // show a confirmation
                        Ext.Msg.show({
                            title: _t('Delete zProperty'),
                            msg: _t("Are you sure you want to delete the local copy of zCollectorPlugin?"),
                            buttons: Ext.Msg.OKCANCEL,
                            fn: function(btn) {
                                if (btn=="ok") {
                                    if (panel.uid) {
                                        router.deleteZenProperty({
                                            uid: panel.uid,
                                            zProperty: ZPROP_NAME
                                        }, function(response){
                                            panel.setContext(panel.uid);
                                        });
                                    }
                                } else {
                                    Ext.Msg.hide();
                                }
                            }
                        });


                    }
                }],
                cls: 'device-overview-form-wrapper',
                bodyCssClass: 'device-overview-form'
            });
            ModelerPluginForm.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            if (this.modelerPlugins) {
                this.modelerPlugins.destroy();
            }
            this.doc.setValue('');
            this.uid = uid;
            // get the modeler plugins
            router.getZenProperty({
                uid: uid,
                zProperty: ZPROP_NAME
            }, this.loadData.createDelegate(this));

            router.getModelerPluginDocStrings({
                uid: uid
            }, this.loadDocs.createDelegate(this));

        },
        toggleDeleteButton: function(path){
            // show the delete button if locally defined
            var localPath = this.uid.replace('/zport/dmd/Devices', '');

            // can't delete the root
            if (path == '/') {
                this.deleteBtn.hide();
                return;
            }
            if (localPath == path) {
                this.deleteBtn.show();
            }else{
                this.deleteBtn.hide();
            }
        },
        loadData: function(response) {
            if (response.success) {
                var data = response.data,
                    clickHandler,
                    panel = this;

                this.path.setValue(data.path);
                this.toggleDeleteButton(data.path);
                clickHandler = function(select) {
                    // display the docs for the first one
                    var value = select.getValue();
                    if (value.indexOf(',') != -1) {
                        value = value.split(',')[0];
                    }
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
                    multiselects: [{
                        cls: 'multiselect-dialog',
                        legend: _t('Available'),
                        width: 350,
                        height: 475,
                        listeners: {
                            click: clickHandler
                        },
                        store: data.options
                    },{
                        cls: 'multiselect-dialog',
                        legend: _t('Selected'),
                        width: 350,
                        height: 475,
                        store: data.value,
                        listeners: {
                            click: clickHandler
                        }
                    }]
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
    ModelerPluginPanel = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                layout: 'fit',
                width: 800,
                autoScroll: 'auto',
                items: [new ModelerPluginForm({
                    ref: 'modelerForm'
                })]
            });
            ModelerPluginPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            this.modelerForm.setContext(uid);
        }
    });


    Ext.reg('modelerpluginpanel', ModelerPluginPanel);

})();