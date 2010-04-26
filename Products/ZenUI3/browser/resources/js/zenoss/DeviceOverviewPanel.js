(function(){

    var REMOTE = Zenoss.remote.DeviceRouter;

    function isField(c) {
        return !!c.setValue && !!c.getValue && !!c.markInvalid && !!c.clearInvalid;
    }

    Zenoss.DeviceOverviewForm = Ext.extend(Ext.form.FormPanel, {
        labelAlign: 'top',
        paramsAsHash: true,
        frame: true,
        defaults: {
            labelStyle: 'font-size: 13px; color: #5a5a5a',
            labelSeparator: '',
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
                        }]
                    },{
                        defaultType: 'displayfield',
                        items: [{
                            fieldLabel: _t('Priority'),
                            name: 'priority'
                        },{
                            fieldLabel: _t('Collector'),
                            name: 'collector'
                        },{
                            fieldLabel: _t('Systems'),
                            name: 'systems'
                        },{
                            fieldLabel: _t('Groups'),
                            name: 'groups'
                        },{
                            fieldLabel: _t('Location'),
                            name: 'location'
                        }]
                    },{
                        defaultType: 'textfield',
                        autoHeight: true,
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
                            xtype: 'displayfield',
                            name: 'hwManufacturer',
                            fieldLabel: _t('Hardware Manufacturer')
                        },{
                            xtype: 'displayfield',
                            name: 'hwModel',
                            fieldLabel: _t('Hardware Model')
                        },{
                            xtype: 'displayfield',
                            name: 'osManufacturer',
                            fieldLabel: _t('OS Manufacturer')
                        },{
                            xtype: 'displayfield',
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
                        autoHeight: true,
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
                D.location = D.location ? Zenoss.render.link(D.location.uid) : 'None';
                Ext.each(D.systems, function(i){
                    systems.push(Zenoss.render.link(i.uid));
                });
                D.systems = systems.join('<br/>') || 'None';
                Ext.each(D.groups, function(i){
                    groups.push(Zenoss.render.link(i.uid));
                });
                D.groups = groups.join('<br/>') || 'None';
                if (D.locking) {
                    D.locking = Zenoss.render.locking(D.locking);
                }
                if (D.hwManufacturer) {
                    D.hwManufacturer = Zenoss.render.link(D.hwManufacturer.uid);
                } else {
                    D.hwManufacturer = 'None';
                }
                if (D.hwModel) {
                    D.hwModel = Zenoss.render.link(D.hwModel.uid);
                } else {
                    D.hwModel = 'None';
                }
                if (D.osManufacturer) {
                    D.osManufacturer = Zenoss.render.link(D.osManufacturer.uid);
                } else {
                    D.osManufacturer = 'None';
                }
                if (D.osModel) {
                    D.osModel = Zenoss.render.link(D.osModel.uid);
                } else {
                    D.osModel = 'None';
                }
                this.setValues(D);
                this.doLayout();
            }, this);
        },
        setValues: function(d) {
            Ext.each(this.forms, function(form){
                form.getForm().setValues(d);
            });
        }
    });

    Ext.reg('deviceoverview', Zenoss.DeviceOverviewPanel);

})();
