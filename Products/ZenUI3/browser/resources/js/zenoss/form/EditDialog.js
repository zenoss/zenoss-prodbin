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
     Zenoss.form.EditDialog = Ext.extend(Zenoss.FormDialog, {
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
                          
             for (i=0; i<items.length; i++) {
                 // verify the xtypes of our items
                 if (!Ext.ComponentMgr.isRegistered(items[i].xtype)) {
                     throw items[i].xtype + " is not a valid xtype, please register it";
                 }
                 // todo individual item hook (incase there is any extra stuff to do)
                 if (config.addItemHandler){
                     config.addItemHandler(item);
                 }
                 // each item has a reference to the record we are editing
                 items[i].record = record;
             }
             
             Ext.applyIf(config, {
                width: 610,
                formId: config.id + 'editDataSourcesDialogForm',
                modal: true,
                height: 670,
                autoHeight: true,
                constrain: true,
                items: items,
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
             Zenoss.form.EditDialog.superclass.constructor.apply(this, arguments);
         }
     });
     Ext.reg('editdialog', Zenoss.form.EditDialog);

}());