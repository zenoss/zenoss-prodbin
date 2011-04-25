/*
 * triggersComponents.js
 */
(function(){

var router = Zenoss.remote.TriggersRouter;

var TriggerSubscriptions = Ext.extend(Ext.grid.EditorGridPanel, {
    constructor: function(config) {
        var me = this;
        this.allowManualEntry = false;
        Ext.applyIf(config, {
            ref: 'grid_panel',
            border: false,
            viewConfig: {forceFit: true},
            title: _t('Triggers'),
            autoExpandColumn: 'value',
            loadMask: {msg:_t('Loading...')},
            autoHeight: true,
            deferRowRender: true,
            keys: [{
                key: [Ext.EventObject.ENTER],
                handler: function() {
                    me.addValueFromCombo();
                }
            }],
            tbar: {
                items: [{
                    xtype: 'combo',
                    ref: 'data_combo',
                    typeAhead: true,
                    triggerAction: 'all',
                    lazyRender:true,
                    mode: 'local',
                    store: {
                        xtype: 'directstore',
                        autoLoad: true,
                        idProperty: 'uuid',
                        fields:['uuid','name'],
                        directFn: router.getTriggerList,
                        root: 'data',
                        listeners: {
                            load: function() {
                                // The renderer for the trigger column depends
                                // on this store being loaded in order for it to
                                // render the name correctly.
                                me.getView().refresh();
                            }
                        }
                    },
                    valueField: 'uuid',
                    displayField: 'name'
                },{
                        xtype: 'button',
                        text: 'Add',
                        ref: 'add_button',
                        handler: function(btn, event) {
                            me.addValueFromCombo()
                        }
                    },{
                        xtype: 'button',
                        ref: 'delete_button',
                        iconCls: 'delete',
                        handler: function(btn, event) {
                            var row = btn.refOwner.ownerCt.getSelectionModel().getSelected();
                            btn.refOwner.ownerCt.getStore().remove(row);
                            btn.refOwner.ownerCt.getView().refresh();
                        }
                    }
                ]
            },
            store: new Ext.data.JsonStore({
                autoDestroy: true,
                storeId: 'triggers_combo_store',
                autoLoad: false,
                idProperty: 'value',
                fields: [
                    'uuid'
                ],
                data: []
            }),
            colModel: new Ext.grid.ColumnModel({
                columns: [{
                    header: _t('Trigger'),
                    dataIndex: 'uuid',
                    renderer: function(value, metaData, record, rowIndex, colIndex, store) {
                        var comboStore = me.getTopToolbar().data_combo.getStore();
                        var idx = comboStore.find('uuid', value);
                        if (idx > -1) {
                            return comboStore.getAt(idx).data.name;
                        }
                        else {
                            // instead of displaying a uuid to the user, just display
                            // something that lets them know the value is hidden.
                            return _t('(Hidden)');
                        }
                   }
                }]
            }),
            sm: new Ext.grid.RowSelectionModel({singleSelect:true})
        });
        TriggerSubscriptions.superclass.constructor.apply(this, arguments);
    },
    addValueFromCombo: function() {
        var combo = this.getTopToolbar().data_combo;
            val = combo.getValue(),
            row = combo.getStore().getById(val)

        var existingIndex = this.getStore().findExact('uuid', val);

        if (!Ext.isEmpty(val) && existingIndex == -1) {
            var record = new Ext.data.Record({uuid:val});
            this.getStore().add(record);
            this.getTopToolbar().data_combo.clearValue();
        }
        else if (existingIndex != -1) {
            Zenoss.message.error(_t('Duplicate items not permitted here.'));
        }
    },
    loadData: function(data) {
        this.getStore().loadData(data);
    }
});
Ext.reg('triggersSubscriptions', TriggerSubscriptions);

})();
