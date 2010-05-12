(function(){

    var REMOTE = Zenoss.remote.DeviceRouter;

    var resetCombo = function(combo, manufacturer) {
        combo.clearValue();
        combo.getStore().setBaseParam('manufacturer', manufacturer);
        delete combo.lastQuery;
        //combo.doQuery(combo.allQuery, true);
    };

    var ClickToEditField = Ext.extend(Zenoss.form.LinkField, {
        constructor: function(config) {
            var editLink = '<a href="javascript:" class="manu-edit-link">'+
                           _t('Edit') + '</a>';
            config.fieldLabel += editLink;
            config.listeners = Ext.apply(config.listeners||{}, {
                render: function(p) {
                    p.editlink = p.label.select('a.manu-edit-link');
                    p.editlink.on('click', function(){
                        p.fireEvent('labelclick', p);
                    }, p);
                }
            });
            ClickToEditField.superclass.constructor.call(this, config);
            this.addEvents('labelclick');
        }
    });
    Ext.reg('clicktoedit', ClickToEditField);

    function editManuInfo (vals, uid) {
        
        function name(uid) {
            if (!uid){
                return 'Unknown';
            }
            if (!Ext.isString(uid)) {
                uid = uid.uid;
            }
            return uid.split('/').reverse()[0];
        }

        var FIELDWIDTH = 300;

        var hwManufacturers = {
            xtype: 'manufacturercombo',
            width: FIELDWIDTH,
            name: 'hwManufacturer',
            fieldLabel: _t('HW Manufacturer'),
            value: name(vals.hwManufacturer),
            listeners: {'select': function(combo, record, index){
                var productCombo = Ext.getCmp('hwproductcombo');
                resetCombo(productCombo, record.data.name);
            }}
        };

        var hwProduct = {
            xtype: 'productcombo',
            width: FIELDWIDTH,
            value: name(vals.hwModel),
            resizable: true,
            name: 'hwProductName',
            fieldLabel: _t('HW Product'),
            id: 'hwproductcombo'
        };

        var osManufacturers = {
            xtype: 'manufacturercombo',
            width: FIELDWIDTH,
            name: 'osManufacturer',
            value: name(vals.osManufacturer),
            fieldLabel: _t('OS Manufacturer'),
            listeners: {'select': function(combo, record, index){
                var productCombo = Ext.getCmp('osproductcombo');
                resetCombo(productCombo, record.data.name);
            }}
        };

        var osProduct = {
            xtype: 'productcombo',
            width: FIELDWIDTH,
            value: name(vals.osModel),
            resizable: true,
            name: 'osProductName',
            id: 'osproductcombo',
            fieldLabel: _t('OS Product')
        };

        var win = new Zenoss.FormDialog({
            autoHeight: true,
            width: 390,
            title: _t('Edit Manufacturer Info'),
            items: [{
                xtype: 'container',
                layout: 'form',
                autoHeight: true,
                style: 'padding-bottom:5px;margin-bottom:5px;border-bottom:1px solid #555;',
                items: [hwManufacturers, hwProduct]
            },{
                xtype: 'container',
                layout: 'form',
                autoHeight: true,
                items: [osManufacturers, osProduct]
            }],
            buttons: [{
                text: _t('Save'),
                ref: '../savebtn',
                handler: function(btn){
                    var vals = btn.refOwner.editForm.getForm().getFieldValues();
                    Ext.apply(vals, {uid:uid});
                    REMOTE.setProductInfo(vals, function(r) {
                        Ext.getCmp('device_overview').load();
                        win.destroy();
                    });
                }
            },{
                text: _t('Cancel'),
                handler: function(btn){
                    win.destroy();
                }
            }]
        });
        win.show();
        win.doLayout();
    }


    function isField(c) {
        return !!c.setValue && !!c.getValue && !!c.markInvalid && !!c.clearInvalid;
    }

    Zenoss.DeviceOverviewForm = Ext.extend(Ext.form.FormPanel, {
        labelAlign: 'top',
        paramsAsHash: true,
        frame: true,
        defaults: {
            labelStyle: 'font-size: 13px; color: #5a5a5a',
            anchor: '100%'
        },
        buttonAlign: 'left',
        buttons: [{
            text: _t('Save'),
            ref: '../savebtn',
            disabled: true,
            hidden: true,
            handler: function(btn){
                this.refOwner.getForm().submit();
            }
        },{
            text: _t('Cancel'),
            ref: '../cancelbtn',
            disabled: true,
            hidden: true,
            handler: function() {
                this.refOwner.getForm().reset();
            }
        }],
        cls: 'device-overview-form-wrapper',
        bodyCssClass: 'device-overview-form',
        listeners: {
            'add': function(me, field, index){
                if (isField(field)) {
                    this.onFieldAdd.call(this, field);
                }
            }
        },
        constructor: function(config) {
            config = Ext.applyIf(config || {}, {
                trackResetOnLoad: true
            });
            config.listeners = Ext.applyIf(config.listeners||{}, this.listeners);
            Zenoss.DeviceOverviewForm.superclass.constructor.call(this, config);
        },
        showButtons: function() {
            if (!this.rendered) {
                this.on('render', this.showButtons, this);
            } else {
                this.savebtn.show();
                this.cancelbtn.show();
            }
        },
        doButtons: function() {
            this.setButtonsDisabled(!this.form.isDirty());
        },
        setButtonsDisabled: function(b) {
            this.savebtn.setDisabled(b);
            this.cancelbtn.setDisabled(b);
        },
        onFieldAdd: function(field) {
            if (!field.isXType('displayfield')) {
                this.showButtons();
                this.mon(field, 'valid', this.doButtons, this);
            }
        },
        hideFooter: function() {
            this.footer.hide();
        },
        showFooter: function() {
            this.footer.show();
        }
    });

    Ext.reg('devformpanel', Zenoss.DeviceOverviewForm);

    Zenoss.DeviceOverviewPanel = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                autoScroll: true,
                bodyCssClass: 'device-overview-panel',
                padding: '10',
                border: false,
                frame: false,
                defaults: {
                    border: false
                },
                forms: [],
                listeners: {
                    add: function(item) {
                        if (item.isXType('form')) {
                            var f = item.getForm();
                            f.api = this.api;
                            f.baseParams = this.baseParams;
                            this.forms.push(item);
                        }
                    }
                },
                items: [{
                    layout: 'hbox',
                    defaults: {
                        flex: 1
                    },
                    layoutConfig: {
                        align: 'stretchmax',
                        defaultMargins: '10'
                    },
                    defaultType: 'devformpanel',
                    items: [{
                        defaultType: 'displayfield',
                        items: [{
                            fieldLabel: _t('Uptime'),
                            name: 'uptime'
                        },{
                            fieldLabel: _t('First Seen'),
                            name: 'firstSeen'
                        },{
                            fieldLabel: _t('Last Change'),
                            name: 'lastChanged'
                        },{
                            fieldLabel: _t('Model Time'),
                            name: 'lastCollected'
                        },{
                            fieldLabel: _t('Locking'),
                            name: 'locking'
                        },{
                            xtype: 'displayfield',
                            name: 'memory',
                            fieldLabel: _t('Memory/Swap')
                        }]
                    },{
                        defaultType: 'displayfield',
                        autoHeight: true,
                        listeners: {
                            actioncomplete: function(form, action) {
                                if (action.type=='directsubmit') {
                                    var bar = Ext.getCmp('devdetailbar');
                                    if (bar) {
                                        bar.refresh();
                                    }
                                }
                            }
                        },
                        items: [{
                            xtype: 'textfield',
                            name: 'name',
                            fieldLabel: _t('Device Name')
                        },{
                            xtype: 'ProductionStateCombo',
                            fieldLabel: _t('Production State'),
                            name: 'productionState'
                        },{
                            xtype: 'PriorityCombo',
                            fieldLabel: _t('Priority'),
                            name: 'priority'
                        },{
                            fieldLabel: _t('Collector'),
                            name: 'collector'
                        },{
                            xtype: 'linkfield',
                            fieldLabel: _t('Systems'),
                            name: 'systems'
                        },{
                            xtype: 'linkfield',
                            fieldLabel: _t('Groups'),
                            name: 'groups'
                        },{
                            xtype: 'linkfield',
                            fieldLabel: _t('Location'),
                            name: 'location'
                        }]
                    },{
                        defaultType: 'textfield',
                        items: [{
                            fieldLabel: _t('Tag'),
                            name: 'tagNumber'
                        },{
                            fieldLabel: _t('Serial Number'),
                            name: 'serialNumber'
                        },{
                            fieldLabel: _t('Rack Slot'),
                            name: 'rackSlot'
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'hwManufacturer',
                            fieldLabel: _t('Hardware Manufacturer')
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues());
                                },
                                scope: this
                            },
                            name: 'hwModel',
                            fieldLabel: _t('Hardware Model')
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues());
                                },
                                scope: this
                            },
                            name: 'osManufacturer',
                            fieldLabel: _t('OS Manufacturer')
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues());
                                },
                                scope: this
                            },
                            name: 'osModel',
                            fieldLabel: _t('OS Model') 
                        }]
                    }]
                },{
                    defaultType: 'devformpanel',
                    autoHeight: true,
                    layout: 'hbox',
                    layoutConfig: {
                        align: 'stretchmax',
                        defaultMargins: '10'
                    },
                    items: [{
                        defaultType: 'displayfield',
                        flex: 2,
                        items: [{
                            fieldLabel: _t('Links'),
                            name: 'links'
                        },{
                            xtype: 'textarea',
                            grow: true,
                            fieldLabel: _t('Comments'),
                            name: 'comments'
                        }]
                    },{
                        defaultType: 'displayfield',
                        flex: 1,
                        minHeight: 230,
                        items: [{
                            fieldLabel: _t('SNMP SysName'),
                            name: 'snmpSysName'
                        },{
                            fieldLabel: _t('SNMP Location'),
                            name: 'snmpLocation'
                        },{
                            fieldLabel: _t('SNMP Contact'),
                            name: 'snmpContact'
                        },{
                            fieldLabel: _t('SNMP Agent'),
                            name: 'snmpAgent'
                        }]
                    }]
                }]
            });
            Zenoss.DeviceOverviewPanel.superclass.constructor.call(this, config);
        },
        api: {
            load: REMOTE.getInfo,
            submit: function(form, success, scope) {
                var o = {},
                    vals = scope.form.getFieldValues(true);
                Ext.apply(o, vals, success.params);
                REMOTE.setInfo(o, function(result){
                    this.form.clearInvalid();
                    this.form.setValues(vals);
                    this.form.afterAction(this, true);
                    this.form.reset();
                }, scope);
            }
        },
        baseParams: {},
        setContext: function(uid) {
            this.contextUid = uid;
            this.baseParams.uid = uid;
            this.load();
        },
        getFieldNames: function() {
            var keys = [];
            Ext.each(this.forms, function(f){
                for (var key in f.getForm().getFieldValues(false)) {
                    if (keys.indexOf(key)==-1) {
                        keys.push(key);
                    }
                }
            });
            return keys;
        },
        load: function() {
            var o = Ext.apply({keys:this.getFieldNames()}, this.baseParams);
            this.api.load(o, function(result) {
                var systems = [], groups = [], D = result.data;
                if (D.locking) {
                    D.locking = Zenoss.render.locking(D.locking);
                }
                if (D.memory) {
                    D.memory = D.memory.ram + '/' + D.memory.swap;
                } else {
                    D.memory = 'Unknown/Unknown';
                }
                this.setValues(D);
                this.doLayout();
            }, this);
        },
        getValues: function() {
            var o = {};
            Ext.each(this.forms, function(form){
                Ext.apply(o, form.getForm().getFieldValues());
            }, this);
            return o;
        },
        setValues: function(d) {
            Ext.each(this.forms, function(form){
                form.getForm().setValues(d);
            });
        }
    });

    Ext.reg('deviceoverview', Zenoss.DeviceOverviewPanel);

})();
