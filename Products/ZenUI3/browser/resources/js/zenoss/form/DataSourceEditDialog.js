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
             
             if (!config.singleColumn) {
                 items = this.sortItems(items, record);  
             }else{
                 for(i=0; i<items.length; i+=1) {
                     items[i].record = record;
                 }
             }
                          
             Ext.apply(config, {
                width: 800,
                modal: true,
                items: items,
                constrain: true,
                autoHeight: true,
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
            var panel = [], i, j, currentPanel,
                item, fieldset, tmp, header;            
            // items comes back from the server in the form
            // fieldsets.items[0] = fieldset
            fieldsets = fieldsets.items;
            
            // The datasources have a convention to where the first items are
            // ungrouped. 
            // This section makes sure the non-titled one is first.
            // (It swaps the titled first fieldset with the untitled fieldset)
            if (fieldsets[0].title) {
                tmp = fieldsets[0];
                for (i=0; i < fieldsets.length; i += 1) {
                    if (!fieldsets[i].title) {
                        fieldsets[0] = fieldsets[i];
                        fieldsets[i] = tmp;
                        break;
                    }
                }
            }

            // this creates a new panel for each group of items that come back from the server
            for (i =0; i < fieldsets.length; i += 1) {
                fieldset = fieldsets[i];

                // format the title a little funny
                if (fieldset.title) {
                    header = {
                        xtype: 'panel',
                        layout: 'form',
                        html: '<br /><br /><h1>' + fieldset.title + '</h1>'
                    };
                }else {
                    header = null;    
                }
                
                currentPanel = {
                    xtype:'panel',
                    layout: 'column',
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
                    if (!Ext.ComponentMgr.isRegistered(item.xtype)) {
                        throw item.xtype + " is not a valid xtype, please register it.";
                    }
                    currentPanel.items[j%2].items.push(item);
                }
                // if we have a header set display it
                if (header) {
                    panel.push(header);
                }
                panel.push(currentPanel);
            }
            
            return panel;
        }
     });
     Ext.reg('datasourceeditdialog', Zenoss.form.DataSourceEditDialog);

}());