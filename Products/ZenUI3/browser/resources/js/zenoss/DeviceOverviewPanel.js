(function(){
    var REMOTE = Zenoss.remote.DeviceRouter;

    var resetCombo = function(combo, manufacturer) {
        combo.clearValue();
        combo.store.setBaseParam('manufacturer', manufacturer);
        delete combo.lastQuery;
        //combo.doQuery(combo.allQuery, true);
    };

    var clickToEditConfig = function(obj, superclass) {
        return {
            constructor: function(config) {
                var title = _t('Click to edit this field');
                var editLink = '<a href="javascript:" title="' + title  + '" class="manu-edit-link">'+
                                _t('Edit') + '</a>',
                    hasPermission = true;
                // do not render the edit link if we don't have permission
                if (config.permission && !Zenoss.Security.hasPermission(config.permission)) {
                    hasPermission = false;
                    editLink = '';
                }
                config.fieldLabel += editLink;
                config.listeners = Ext.apply(config.listeners||{}, {
                    render: function(p) {
                        if (hasPermission) {
                            p.editlink = p.labelEl.select('a.manu-edit-link');
                            p.editlink.on('click', function(){
                                p.fireEvent('labelclick', p);
                            }, p);
                        }
                    }
                });

                obj.superclass.constructor.call(this, config);
                this.addEvents('labelclick');
            },
            setValue: function(value) {
                var origValue = value;
                if (Ext.isEmpty(value)) {
                    value = _t('None');
                } else {
                    if (Ext.isArray(value)){
                        var items = [];
                        Ext.each(value, function(v){
                            items.push(Zenoss.render.link(v));
                        });
                        value = items.join('<br/>');
                    } else {
                        if(value.uid && value.uid.match(/Manufacturers/)){
                            var grid = null;
                            var data = value;
                            if(value.uid.match(/products/)){
                                Zenoss.manufacturers.launchProductDialog = function(){
                                    Zenoss.manufacturers.productsDialog(grid, data);
                                }
                                value =  '<a title="Edit this Product details in place" href="javascript:void(0);" onClick="Zenoss.manufacturers.launchProductDialog()">'+value.id+'</a>';
                            }else{
                                value = '<a title="Go to the grid for this Manufacturer" href="/zport/dmd/manufacturers#manufacturers_tree:.zport.dmd.Manufacturers.'+value.name+'" >'+value.name+'</a>';
                            }
                        }else{
                            value = Zenoss.render.link(value);
                        }
                    }
                }
                this.setRawValue(value);
                this.rawValue = origValue;
            }


        };
    };

    Zenoss.ClickToEditField = Ext.extend(Zenoss.form.LinkField, {});


    Zenoss.ClickToEditField = Ext.extend(Zenoss.form.LinkField, clickToEditConfig(Zenoss.ClickToEditField));
    Ext.reg('clicktoedit', "Zenoss.ClickToEditField");

    Zenoss.ClickToEditNoLink = Ext.extend(Ext.form.DisplayField, {});
    Zenoss.ClickToEditNoLink = Ext.extend(Ext.form.DisplayField,
                                   clickToEditConfig(Zenoss.ClickToEditNoLink));
    Ext.reg('clicktoeditnolink', "Zenoss.ClickToEditNoLink");


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
            id: 'hwmanufacturercombo',
            fieldLabel: _t('HW Manufacturer'),
            listConfig: {
                resizable: true, resizeHandles: 'e'
            },
            listeners: {'select': function(combo, record, index){
                record = record[0];
                var productCombo = Ext.getCmp('hwproductcombo');
                resetCombo(productCombo, record.data.name);
            }}
        };

        var hwProduct = {
            xtype: 'productcombo',
            prodType: 'HW',
            width: FIELDWIDTH,
            listConfig: {
                resizable: true, resizeHandles: 'e'
            },
            name: 'hwProductName',
            fieldLabel: _t('HW Product'),
            id: 'hwproductcombo',
            manufacturer: name(vals.hwManufacturer)
        };

        var osManufacturers = {
            xtype: 'manufacturercombo',
            width: FIELDWIDTH,
            name: 'osManufacturer',
            id: 'osmanufacturercombo',
            fieldLabel: _t('OS Manufacturer'),
            listConfig: {
                resizable: true, resizeHandles: 'e'
            },
            listeners: {'select': function(combo, record, index){
                record = record[0];
                var productCombo = Ext.getCmp('osproductcombo');
                resetCombo(productCombo, record.data.name);
            }}
        };

        var osProduct = {
            xtype: 'productcombo',
            prodType: 'OS',
            width: FIELDWIDTH,
            listConfig: {
                resizable: true, resizeHandles: 'e'
            },
            name: 'osProductName',
            id: 'osproductcombo',
            fieldLabel: _t('OS Product'),
            manufacturer: name(vals.osManufacturer)
        };

        var win = new Zenoss.FormDialog({
            autoHeight: true,
            width: 390,
            title: _t('Edit Manufacturer Info'),
            items: [{
                xtype: 'container',
                layout: 'anchor',
                autoHeight: true,
                style: 'padding-bottom:5px;margin-bottom:5px;border-bottom:1px solid #555;',
                items: [hwManufacturers, hwProduct]
            },{
                xtype: 'container',
                layout: 'anchor',
                autoHeight: true,
                items: [osManufacturers, osProduct]
            }],
            buttons: [{
                text: _t('Save'),
                ref: '../savebtn',
                xtype: 'DialogButton',
                id: 'win-save-button',
                disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                handler: function(btn){
                    var form = btn.refOwner.editForm.getForm(),
                        vals = form.getValues();
                    Ext.apply(vals, {uid:uid});
                    REMOTE.setProductInfo(vals, function(r) {
                        Ext.getCmp('device_overview').load();
                        win.destroy();
                    });
                }
            },{
                text: _t('Cancel'),
                xtype: 'DialogButton',
                id: 'win-cancel-button',
                handler: function(btn){
                    win.destroy();
                }
            }]
        });
        win.show();
        win.doLayout();
        Ext.getCmp('hwmanufacturercombo').getStore().addListener('load', function fn(){
            var manufacturerName = name(vals.hwManufacturer);
            Ext.getCmp('hwmanufacturercombo').setValue(manufacturerName);
        });
        Ext.getCmp('hwproductcombo').getStore().addListener('load', function fn(){
            var modelName = name(vals.hwModel);
            Ext.getCmp('hwproductcombo').setValue(modelName);
        });
        Ext.getCmp('osmanufacturercombo').getStore().addListener('load', function fn(){
            var manufacturerName = name(vals.osManufacturer);
            Ext.getCmp('osmanufacturercombo').setValue(manufacturerName);
        });
        Ext.getCmp('osproductcombo').getStore().addListener('load', function fn(){
            var modelName = name(vals.osModel);
            Ext.getCmp('osproductcombo').setValue(modelName);
        });
    }


    var editCollector = function(values, uid) {
        var win = new Zenoss.FormDialog({
            autoHeight: true,
            width: 300,

            title: _t('Set Collector'),
            items: [{
                xtype: 'combo',
                name: 'collector',
                listConfig: {
                    resizable: true, resizeHandles: 'e'
                },
                fieldLabel: _t('Select a collector'),
                queryMode: 'local',
                store: new Ext.data.ArrayStore({
                    data: Zenoss.env.COLLECTORS,
                    fields: ['name']
                }),
                valueField: 'name',
                displayField: 'name',
                value: values.collector,
                forceSelection: true,
                editable: false,
                autoSelect: true,
                triggerAction: 'all'
            }],
            buttons: [{
                text: _t('Save'),
                ref: '../savebtn',
                xtype: 'DialogButton',
                id: 'editcollector-save-button',
                disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                handler: function(btn) {
                    var vals = btn.refOwner.editForm.getForm().getValues();
                    var submitVals = {
                        uids: [uid],
                        asynchronous: Zenoss.settings.deviceMoveIsAsync([uid]),
                        collector: vals.collector,
                        hashcheck: ''
                    };
                    Zenoss.remote.DeviceRouter.setCollector(submitVals, function(data) {
                        Ext.getCmp('device_overview').load();
                    });
                    win.destroy();
                }
            }, {
                text: _t('Cancel'),
                xtype: 'DialogButton',
                id: 'editcollector-cancel-button',
                handler: function(btn) {
                    win.destroy();
                }
            }]
        });
        win.show();
        win.doLayout();
    };

    var editGroups = function(currentGroups, uid, config) {
        var win = new Zenoss.FormDialog({
            width: 500,
            height: 150,
            title: config.title,
            items: [{
                xtype: 'panel',
                html: config.instructions
            }, {
                xtype: 'tbspacer',
                height: 5
            }, {
                xtype: 'panel',
                layout: 'hbox',
                width: '100%',
                items: [{
                    xtype: 'combo',
                    ref: '../../selectgroup',
                    name: 'group',
                    width: 250,
                    store: new Ext.data.DirectStore({
                        directFn: config.getGroupFn,
                        root: config.getGroupRoot,
                        fields: ['name']
                    }),
                    valueField: 'name',
                    displayField: 'name',
                    id: 'editgroups-combo',
                    forceSelection: true,
                    listConfig: {
                        resizable: true, resizeHandles: 'e'
                    },
                    editable: false,
                    autoSelect: true,
                    triggerAction: 'all',
                    flex: 4
                }, {
                    xtype: 'button',
                    ref: '../../addgroupbutton',
                    ui: 'dialog-dark',
                    text: _t('Add'),
                    id: 'addgroup-button',
                    handler: function(btn) {
                        var selectedGroup = btn.refOwner.selectgroup.getValue();
                        if (selectedGroup) {
                            btn.refOwner.grouplist.addGroup(selectedGroup);
                        }
                    },
                    flex: 1
                }]
            }, {
                xtype: 'panel',
                ref: '../grouplist',
                addGroup: function(group, displayOnly) {
                    if (group in this.groups) {
                        if (this.groups[group] == 'del')
                            this.groups[group] = '';
                        else
                            return;
                    }
                    else {
                        this.groups[group] = displayOnly ? '' : 'add';
                    }

                    var grouplist = this;
                    var oldHeight = this.getHeight();
                    this.add({xtype: 'tbspacer', height: 5});
                    this.add({
                        xtype: 'panel',
                        layout: 'hbox',
                        width: '100%',
                        layoutConfig: {
                            align:'middle'
                        },
                        items: [{
                            xtype: 'panel',
                            html: group
                        }, {
                            xtype: 'tbspacer',
                            flex: 1
                        }, {
                            xtype: 'button',
                            ui: 'dialog-dark',
                            text: _t('Remove'),
                            ref: 'delbutton',
                            group: group,
                            handler: function(btn) {
                                grouplist.delGroup(group, btn.refOwner);
                            }
                        }]
                    });
                    this.bubble(function() {this.doLayout();});

                    if (displayOnly) return;
                    win.setHeight(win.getHeight() + this.getHeight() - oldHeight);
                },
                delGroup: function(group, panel) {
                    if (this.groups[group] == 'add')
                        delete this.groups[group];
                    else
                        this.groups[group] = 'del';

                    var oldHeight = this.getHeight();
                    panel.destroy();
                    this.bubble(function() {this.doLayout();});
                    win.setHeight(win.getHeight() + this.getHeight() - oldHeight);
                },
                groups: {},
                listeners: {
                    render: function(thisPanel) {
                        Ext.each(currentGroups, function(group){
                            thisPanel.addGroup(group.uid.slice(config.dmdPrefix.length), true);
                        });
                    }
                }
            }],
            buttons: [{
                text: _t('Save'),
                ref: '../savebtn',
                xtype: 'DialogButton',
                id: 'editgroups-save-button',
                disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                handler: function(btn) {
                    Ext.iterate(btn.refOwner.grouplist.groups, function(group, op) {
                        var submitVals = {
                            uids: [uid],
                            hashcheck: ''
                        };

                        if (op == 'del') {
                            submitVals['uid'] = config.dmdPrefix + group;
                            Zenoss.remote.DeviceRouter.removeDevices(submitVals, function(data) {
                                Ext.getCmp('device_overview').load();
                            });
                        }
                        if (op == 'add') {
                            submitVals['target'] = config.dmdPrefix + group;
                            submitVals['asynchronous'] = Zenoss.settings.deviceMoveIsAsync(submitVals.uids);
                            Zenoss.remote.DeviceRouter.moveDevices(submitVals, function(data) {
                                Ext.getCmp('device_overview').load();
                            });
                        }
                    });
                    win.destroy();
                }
            }, {
                text: _t('Cancel'),
                xtype: 'DialogButton',
                id: 'editgroups-cancel-button',
                handler: function(btn) {
                    win.destroy();
                }
            }]
        });
        win.show();
        win.doLayout();
        win.setHeight(win.getHeight() + win.grouplist.getHeight());
    };

    var editLocation = function(values, uid) {
        var win = new Zenoss.FormDialog({
            autoHeight: true,
            width: 500,
            title: _t('Set Location'),
            items: [{
                xtype: 'combo',
                name: 'location',
                fieldLabel: _t('Select a location'),
                store: new Ext.data.DirectStore({
                    autoload: true,
                    directFn: Zenoss.remote.DeviceRouter.getLocations,
                    root: 'locations',
                    fields: ['name']
                }),
                valueField: 'name',
                displayField: 'name',
                id: 'editlocation-name-combo',
                value: values.location ? values.location.uid.slice(20) : '',
                listConfig: {
                    resizable: true, resizeHandles: 'e'
                },
                width: 250,
                triggerAction: 'all'
            }],
            buttons: [{
                text: _t('Save'),
                ref: '../savebtn',
                xtype: 'DialogButton',
                id: 'editlocation-save-button',
                disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                handler: function(btn) {
                    var vals = btn.refOwner.editForm.getForm().getValues();
                    if (vals.location) {
                        var submitVals = {
                            uids: [uid],
                            asynchronous: Zenoss.settings.deviceMoveIsAsync([uid]),
                            target: '/zport/dmd/Locations' + vals.location,
                            hashcheck: ''
                        };
                        Zenoss.remote.DeviceRouter.moveDevices(submitVals, function(data) {
                            if (data.success) {
                                Ext.getCmp('device_overview').load();
                            }
                        });
                    }
                    win.destroy();
                }
            }, {
                text: _t('Cancel'),
                xtype: 'DialogButton',
                id: 'editlocation-cancel-button',
                handler: function(btn) {
                    win.destroy();
                }
            }]
        });
        win.show();
        win.doLayout();
    };


    function isField(c) {
        return !!c.setValue && !!c.getValue && !!c.markInvalid && !!c.clearInvalid;
    }

    Ext.define("Zenoss.DeviceOverviewForm", {
        alias:['widget.devformpanel'],
        extend:"Ext.form.FormPanel",
        fieldDefaults: {
            labelAlign: 'top'
        },
        paramsAsHash: true,
        frame: false,
        defaults: {
            anchor: '95%',
            labelStyle: 'font-size: 13px; color: #5a5a5a'
        },
        buttonAlign: 'left',
        buttons: [{
            text: _t('Save'),
            xtype:'button',
            ref: '../savebtn',
            disabled: true,
            hidden: true,
            handler: function(btn){
                this.refOwner.getForm().submit();
            }
        },{
            text: _t('Cancel'),
            xtype: 'button',
            ref: '../cancelbtn',
            disabled: true,
            hidden: true,
            handler: function() {
                this.refOwner.getForm().reset();
            }
        }],
        cls: 'device-overview-form-wrapper',
        bodyCls: 'device-overview-form',
        style:{'background-color':'#fafafa'},
        listeners: {
            add: function(me, field, index){
                if (isField(field)) {
                    this.onFieldAdd.call(this, field);
                }
            },
            validitychange: function(me, isValid, eOpts) {
                this.setButtonsDisabled(!isValid);
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
                Ext.getCmp(this.savebtn.id).addCls("savebtn-button"+this.id);
                Ext.getCmp(this.cancelbtn.id).addCls("cancelbtn-button"+this.id);
                this.savebtn.show();
                this.cancelbtn.show();
            }
        },
        doButtons: function() {
            this.setButtonsDisabled(!this.form.isDirty());
        },
        setButtonsDisabled: function(b) {
            if (Zenoss.Security.hasPermission('Manage Device')) {
                this.savebtn.setDisabled(b);
            }
            this.cancelbtn.setDisabled(b);
        },
        onFieldAdd: function(field) {
            if (!field.isXType('displayfield')) {
                this.showButtons();
                this.mon(field, 'dirtychange', this.doButtons, this);
            }
        },
        hideFooter: function() {
            this.footer.hide();
        },
        showFooter: function() {
            this.footer.show();
        },
        addField: function(field) {
            this.add(field);
        },
        addFieldAfter: function(field, afterFieldName) {
            var position = this._indexOfFieldName(afterFieldName) +1;
            this.insert(position, field);
        },
        _indexOfFieldName: function(name) {
            var idx = -1, items = this.getItems(), i;
            for ( i = 0; i < items.length; i++ ){
                if (items[i].name == name){
                    idx = i;
                    break;
                }
            }
        return idx;
        },
        replaceField: function(name, field) {
            this.removeField(name);
            this.addField(field);
        },
        removeField: function(name) {
            var field = this.getField(name);

            if (field) {
                this.remove(field);
            }
        },
        getField: function(name) {
            return this.getItems()[this._indexOfFieldName(name)];
        },
        getItems: function(){
            return this.items.items;
        }
    });



    Ext.define("Zenoss.DeviceOverviewPanel", {
        alias:['widget.deviceoverview'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                autoScroll: true,
                bodyCls: 'device-overview-panel',
                padding: '10',
                frame: false,
                forms: [],
                listeners: {
                    add: function(me, container) {
                        Ext.each(container.items.items, function(item) {
                            if (item.isXType('form')) {
                                var f = item.getForm();
                                f.api = this.api;
                                f.baseParams = this.baseParams;
                                this.forms.push(item);
                            }
                        }, this);
                    }
                },
                items: [{
                    layout: {
                        type: 'hbox'
                    },
                    id: 'deviceoverviewpanel_main',
                    defaults: {
                        bodyStyle: 'background-color:#fafafa;',
                        minHeight: 350,
                        margin:'0 10 10 0',
                        flex: 1
                    },
                    defaultType: 'devformpanel',
                    items: [{
                        id:'deviceoverviewpanel_summary',
                        defaultType: 'displayfield',
                        frame:false,
                        items: [{
                            fieldLabel: _t('Device ID'),
                            id: 'device-id-label',
                            name: 'device'
                        },{
                            fieldLabel: _t('Uptime'),
                            id: 'uptime-label',
                            name: 'uptime'
                        },{
                            fieldLabel: _t('First Seen'),
                            id: 'first-seen-label',
                            name: 'firstSeen'
                        },{
                            fieldLabel: _t('Last Change'),
                            id: 'last-change-label',
                            name: 'lastChanged'
                        },{
                            fieldLabel: _t('Model Time'),
                            id: 'model-time-label',
                            name: 'lastCollected'
                        },{
                            fieldLabel: _t('Locking'),
                            id: 'locking-label',
                            name: 'locking'
                        },{
                            xtype: 'displayfield',
                            id: 'memory-displayfield',
                            name: 'memory',
                            fieldLabel: _t('Memory/Swap')
                        }]
                    },{
                        id:'deviceoverviewpanel_idsummary',
                        defaultType: 'displayfield',
                        frame:false,

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
                            fieldLabel: _t('Device Title'),
                            id: 'device-name-textfield',
                            allowBlank: false
                        },{
                            xtype: 'ProductionStateCombo',
                            fieldLabel: _t('Production State'),
                            id: 'production-state-combo',
                            name: 'productionState'
                        },{
                            xtype: 'PriorityCombo',
                            fieldLabel: _t('Priority'),
                            id: 'priority-combo',
                            name: 'priority'
                        },{
                            fieldLabel: _t('Tag'),
                            name: 'tagNumber',
                            id: 'tagnumber-textfield',
                            xtype: 'textfield'
                        },{
                            fieldLabel: _t('Serial Number'),
                            name: 'serialNumber',
                            id: 'serialnumber-textfield',
                            xtype: 'textfield'
                        }]
                    },{
                        id:'deviceoverviewpanel_descriptionsummary',
                        defaultType: 'textfield',
                        frame:false,

                        items: [{
                            fieldLabel: _t('Rack Slot'),
                            name: 'rackSlot',
                            id: 'rackslot-textfield',
                            xtype: 'textfield'
                        },{
                            xtype: 'clicktoeditnolink',
                            permission: 'Manage Device',
                            listeners: {
                                labelclick: function(p){
                                    editCollector(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            fieldLabel: _t('Collector'),
                            name: 'collector',
                            id: 'collector-editnolink'
                        },{
                            xtype: 'clicktoedit',
                            permission: 'Manage Device',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'hwManufacturer',
                            id: 'hwmanufacturer-editlink',
                            fieldLabel: _t('Hardware Manufacturer')
                        },{
                            xtype: 'clicktoedit',
                            permission: 'Manage Device',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'hwModel',
                            id: 'hwmodel-editlink',
                            fieldLabel: _t('Hardware Model')
                        },{
                            xtype: 'clicktoedit',
                            permission: 'Manage Device',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'osManufacturer',
                            id: 'osmanufacturer-editlink',
                            fieldLabel: _t('OS Manufacturer')
                        },{
                            xtype: 'clicktoedit',
                            permission: 'Manage Device',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'osModel',
                            id: 'osmodel-editlink',
                            fieldLabel: _t('OS Model')
                        }]
                    }]
                },{
                    id:'deviceoverviewpanel_customsummary',
                    defaultType: 'devformpanel',
                    frame:false,

                    layout: 'hbox',
                    defaults: {
                        bodyStyle: 'background-color:#fafafa;',
                        minHeight: 400,
                        margin:'0 10 10 0'
                    },
                    layoutConfig: {
                        align: 'stretchmax'
                    },
                    items: [{
                        defaultType: 'displayfield',
                        flex: 2,
                        minHeight: 400,
                        frame:false,
                        id: 'deviceoverviewpanel_systemsummary',
                        items: [{
                            xtype: 'clicktoedit',
                            permission: 'Manage Device',
                            listeners: {
                                labelclick: function(p){
                                    editGroups(this.getValues().systems, this.contextUid, {
                                        title: _t('Set Systems'),
                                        instructions: _t('Add/Remove systems'),
                                        getGroupFn: Zenoss.remote.DeviceRouter.getSystems,
                                        getGroupRoot: 'systems',
                                        dmdPrefix: '/zport/dmd/Systems'
                                    });
                                },
                                scope: this
                            },
                            fieldLabel: _t('Systems'),
                            name: 'systems',
                            id: 'systems-editlink'
                        },{
                            xtype: 'clicktoedit',
                            permission: 'Manage Device',
                            listeners: {
                                labelclick: function(p){
                                    editGroups(this.getValues().groups, this.contextUid, {
                                        title: _t('Set Groups'),
                                        instructions: _t('Add/Remove groups'),
                                        getGroupFn: Zenoss.remote.DeviceRouter.getGroups,
                                        getGroupRoot: 'groups',
                                        dmdPrefix: '/zport/dmd/Groups'
                                    });
                                },
                                scope: this
                            },
                            fieldLabel: _t('Groups'),
                            name: 'groups',
                            id: 'groups-editlink'
                        },{
                            xtype: 'clicktoedit',
                            permission: 'Manage Device',
                            listeners: {
                                labelclick: function(p){
                                    editLocation(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            fieldLabel: _t('Location'),
                            name: 'location',
                            id: 'location-editlink'
                        },{
                            fieldLabel: _t('Links'),
                            name: 'links',
                            id: 'links-label'
                        },{
                            xtype: 'textarea',
                            grow: true,
                            fieldLabel: _t('Comments'),
                            name: 'comments',
                            id: 'comments-textarea'
                        }]
                    },{
                        id:'deviceoverviewpanel_snmpsummary',
                        defaultType: 'displayfield',
                        frame:false,

                        flex: 1,
                        bodyStyle: 'background-color:#fafafa;',
                        minHeight: 400,
                        items: [{
                            fieldLabel: _t('SNMP SysName'),
                            name: 'snmpSysName',
                            id: 'snmpsysname-label'
                        },{
                            fieldLabel: _t('SNMP Location'),
                            name: 'snmpLocation',
                            id: 'snmplocation-label'
                        },{
                            fieldLabel: _t('SNMP Contact'),
                            name: 'snmpContact',
                            id: 'snmpcontact-label'
                        },{
                            fieldLabel: _t('SNMP Description'),
                            autoWidth: true,
                            name: 'snmpDescr',
                            id: 'snmpdescr-label'
                        },{
                            fieldLabel: _t('SNMP Community'),
                            name: 'snmpCommunity',
                            id: 'snmpcommunity-label',
                            hidden: Zenoss.Security.doesNotHavePermission('Manage Device')
                        },{
                            fieldLabel: _t('SNMP Version'),
                            name: 'snmpVersion',
                            id: 'snmpversion-label'
                        }]
                    }]
                }]
            });
            Zenoss.DeviceOverviewPanel.superclass.constructor.call(this, config);
        },
        api: {
            load: Zenoss.util.isolatedRequest(REMOTE.getInfo),
            submit: function(form, success, scope) {
                var o = {},
                vals = scope.form.getValues(false, true);
                Ext.apply(o, vals, scope.form.baseParams);
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
            // if we havne't rendered yet wait until we have rendered
            if (!this.getEl()) {
                this.on('afterrender', this.load, this, {single: true});
            } else {
                this.load();
            }

        },
        getFieldNames: function() {
            var keys = [], key;
            Ext.each(this.forms, function(f){
                Ext.each(f.getForm().getFields().items, function(field) {
                    key = field.name;
                    if (Ext.Array.indexOf(keys, key)==-1 && (key != 'links') && (key != 'uptime')) {
                        keys.push(key);
                    }
                });
            });
            return keys;
        },
        load: function() {
            var o = Ext.apply({keys:this.getFieldNames()}, this.baseParams), me = this;
            var callback = function(result) {
                var D = result.data;
                if (D.locking) {
                    D.locking = Zenoss.render.locking(D.locking);
                }
                if (D.memory) {
                    D.memory = D.memory.ram + '/' + D.memory.swap;
                } else {
                    D.memory = 'Unknown/Unknown';
                }
                this.setValues(D);

                // load zLinks and uptime in a separate request since they
                // can be very expensive
                var opts = Ext.apply({keys:['links', 'uptime']}, this.baseParams);
                this.api.load(opts, function(results){
                    this.setValues(results.data);
                }, this);
            };


            if (Zenoss.env.infoObject) {
                Ext.bind(callback, this, [Zenoss.env.infoObject])();
                delete Zenoss.env.infoObject;
            } else {
                this.api.load(o, callback, this);
            }
        },
        getValues: function() {
            var o = {};
            Ext.each(this.forms, function(form){
                Ext.apply(o, form.getForm().getValues(false, false, true, true));
            }, this);
            return o;
        },
        setValues: function(d) {
            this.suspendLayouts();
            Ext.each(this.forms, function(form){
                form.getForm().setValues(d);
            });
            this.resumeLayouts(true);
        }
    });

})();
