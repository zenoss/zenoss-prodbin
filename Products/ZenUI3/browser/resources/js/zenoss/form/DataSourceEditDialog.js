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
     Ext.namespace('Zenoss.form');
     /**
      * Config Options:
      * - addItemHandler(item) - called when iterating through each item, do any customizations there
      * - record (required) - the record we are editing, it is attached to each item
      * - items - received from the Schema declaration
      * - directFn - The server call when we press Save
      * - saveHandler - the router callback from after we save
      **/
     Zenoss.form.DataSourceEditDialog = Ext.extend(Zenoss.FormDialog, {
         constructor: function(config) {
             config = config || {};
             // verify we received the record we are editing
             var record = config.record,
                 items = config.items,
                 i,
                 that = this; // used in the save handler closure
             
             // make sure the record was passed in
             if (!record) {
                 throw "EditDialog did not recieve a record to edit (config.record is undefined)";
             }
             if (!config.thresholds) {
                 items = this.sortItems(items, record);  
             }else{
                 for(i=0; i<items.length; i+=1) {
                     items[i].record = record;
                 }
             }
             
             
             Ext.apply(config, {
                width: 800,
                modal: true,
                height: 670,
                items: items,
                constrain: true,
                
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Save'),
                    handler: function () {
                        var form = that.editForm.form,
                            values = form.getValues();
                        
                        values.uid = record.id;
                        config.directFn(values, config.saveHandler);
                    }
                },
                    Zenoss.dialog.CANCEL
                ]               
              });
             Zenoss.form.DataSourceEditDialog.superclass.constructor.apply(this, arguments);
         },

        /**
         * This function returns a two column layout with the fields auto divided between the
         * column according to the order they are defined.
         * If you specify a group in your datasource schema, they will appear in that "panel" on this dialog
         **/
        sortItems: function(fieldsets, record) {
            fieldsets = fieldsets.items;
            
            // items comes back from the server in the form
            // items.items[0] = fieldset
            var panel = [], i, j, currentPanel, item, fieldset;
            
            for (i =0; i < fieldsets.length; i += 1) {
                fieldset = fieldsets[i];
                currentPanel = {
                    xtype:'panel',
                    layout: 'column',
                    title: fieldset.title,
                    border: false,
                    items: [{
                                layout:'form',
                                border:false,
                                columnWidth: 0.5,
                                items: []
                            },{
                                layout:'form',
                                border:false,
                                columnWidth: 0.5,
                                items: []
                            }]
                };

                // alternate which column this item belongs too
                for(j = 0; j < fieldset.items.length; j += 1) {
                    item = fieldset.items[j];
                    item.record = record;
                    currentPanel.items[j%2].items.push(item);
                }
                
                panel.push(currentPanel);
            }
            
            return panel;
        }
     });
     Ext.reg('datasourceeditdialog', Zenoss.form.DataSourceEditDialog);

}());