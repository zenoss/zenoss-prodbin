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

/* package level */
(function() {
    Ext.namespace('Zenoss.templates');
    var router = Zenoss.remote.TemplateRouter,
     EditThresholdDialog;
     
    /**
     * Each Threshold Type has their own dialog as denoted by "ThresholdType"+Dialog, so
     * the MinMaxThreshold type has the name MinMaxThresholdDialog. It is up to the zenpacks to
     * register with Ext.reg their Dialog type. 
     * NOTE: the record from the datastore is passed in with the config (config.record)
     *
     * Config Options:
     *  saveHandler: Defined the call back from the router
     **/
    EditThresholdDialog = Ext.extend(Zenoss.FormDialog, {
        constructor: function(config) {
            var record = config.record,
                items;

            items = this.createComponentsFromProperties(record);
            Ext.apply(config, {
                title: _t('Edit Threshold'),
                width: 610,
                formId: 'editThresholdDialogForm',
                modal: true,
                height: 670,
                autoHeight: true,
                constrain: true,
                items: items,
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Save'),
                    handler: function () {
                        var form = Ext.getCmp('editThresholdDialogForm').getForm(),
                        values = form.getValues();
                        values.uid = record.id;
                        router.editThreshold(values, config.saveHandler);
                    }
                },
                    Zenoss.dialog.CANCEL
                ]
            });
            EditThresholdDialog.superclass.constructor.apply(
                this, arguments);
        },
                                           
        createComponentsFromProperties: function(record) {
            var items = [],
                i = 2,
                properties = record.thresholdProperties,
                property,
                item;

            // always have the label field first
            items[0] = {
                xtype: 'label',
                html: '<h1>' + record.name + '</h1>',
                name: 'thresholdName',
                fieldLabel: _t('Name')
            };
            items[1] = {
                xtype: 'label',
                html: record.type,
                name: 'thresholdType',
                fieldLabel: _t('Type')
            };
            
            // magically create the rest of the properties
            for (i = 0; i < properties.length; i++) {
                property = properties[i];
                item = {};
                // the post "name"
                item.name = property.id;
                
                // value
                if (record[property.id]) {
                    item.value = record[property.id];   
                }
                // label
                if (property.label) {
                    item.fieldLabel = property.label;    
                }else {
                    item.fieldLabel = property.id;
                }

                // minval and maxval should be number fields even though they
                // are string datatypes on the server
                if (property.id == 'minval' || property.id == 'maxval') {
                    property.type = 'int';
                }
                item.xtype = Zenoss.util.getExtControlType(property.id, property.type);

                // special case for checkboxes                
                if (item.xtype == 'checkbox') {
                    item.checked = item.value;
                }
                
                // allow the item to use the current data set we are working on
                item.record = record;
                items[i + 2] = item;
            }
            return items;
        }
    });
    Ext.reg('EditThresholdDialog', EditThresholdDialog);

}());