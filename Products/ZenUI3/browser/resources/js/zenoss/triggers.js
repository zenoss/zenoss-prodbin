/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

Ext.ns('Zenoss.ui.Triggers');

Ext.onReady(function () {
    
    var router = Zenoss.remote.TriggersRouter,
        
        AddDialogue,
        addNotificationDialogue,
        addNotificationDialogueConfig,
        addScheduleDialogue,
        addScheduleDialogueConfig,
        addTriggerDialogue,
        colModel,
        colModelConfig,
        detailPanelConfig,
        displayEditTriggerDialogue,
        displayNotificationEditDialogue,
        displayScheduleEditDialogue,
        EditNotificationDialogue,
        editNotificationDialogue,
        editNotificationDialogueConfig,
        editScheduleDialogue,
        editScheduleDialogueConfig,
        editTriggerDialogue,
        EditTriggerDialogue,
        EditScheduleDialogue,
        masterPanelConfig,
        navSelectionModel,
        NotificationPageLayout,
        notificationPanelConfig,
        notificationsPanelConfig,
        NotificationSubscriptions,
        notification_panel,
        PageLayout,
        reloadNotificationGrid,
        reloadScheduleGrid,
        reloadTriggersGrid,
        SchedulesPanel,
        schedulesPanelConfig,
        schedules_panel,
        TriggersGridPanel,
        triggersPanelConfig;

    
    AddDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 120,
                width: 300,
                modal: true,
                plain: true,
                closeAction: 'hide',
                items:{
                    xtype:'form',
                    ref: 'addForm',
                    border: false,
                    monitorValid: true,
                    buttonAlign: 'center',
                    items:[{
                        xtype: 'textfield',
                        name: 'newId',
                        ref: 'newId',
                        allowBlank: false,
                        vtype: 'alphanum',
                        fieldLabel: _t('Id')
                    }],
                    buttons:[{
                        xtype: 'button',
                        text: _t('Submit'),
                        ref: '../../submitButton',
                        formBind: true,
                        /*
                         * This dialogue is used to generically add objects for
                         * triggers, notifications and schedule windows. For
                         * triggers and notifications, do the normal thing, but
                         * for schedules, let the config pass in a handler
                         * since creating a window requires slightly different
                         * context.
                         */
                        handler: function(button) {
                            if (config.submitHandler) {
                                config.submitHandler(button);
                            } else {
                                var params = {
                                    newId: button.refOwner.addForm.newId.getValue()
                                };
                                config.directFn(params, function(){
                                    button.refOwner.addForm.newId.setValue('');
                                    config.reloadFn();
                                    button.refOwner.hide();
                                });
                            }
                        }
                    },{
                        xtype: 'button',
                        ref: '../../cancelButton',
                        text: _t('Cancel'),
                        handler: function(button) {
                            button.refOwner.hide();
                        }
                    }]}
            });
            AddDialogue.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('triggersadddialogue', AddDialogue);
    
    
    /**
     * NOTIFICATIONS
     **/
    
    notificationPanelConfig = {
        id: 'notification_panel',
        xtype: 'notificationsubscriptions'
    };
    
    schedulesPanelConfig = {
        id: 'schedules_panel',
        xtype: 'schedulespanel'
    };
    
    
    reloadNotificationGrid = function() {
        Ext.getCmp(notificationPanelConfig.id).getStore().reload();
    };
    
    displayNotificationEditDialogue = function(data) {
        console.log(data);
        var dialogue = Ext.getCmp(editNotificationDialogueConfig.id);
        dialogue.loadData(data);
        dialogue.show();
    };
    
    reloadScheduleGrid = function() {
        var panel = Ext.getCmp(notificationPanelConfig.id),
            row = panel.getSelectionModel().getSelected();
        if (row) {
            Ext.getCmp(schedulesPanelConfig.id).getStore().reload({uid:row.data.uid});
        }
    };
    
    displayScheduleEditDialogue = function(data) {
        var dialogue = Ext.getCmp(editScheduleDialogueConfig.id);
        dialogue.loadData(data);
        dialogue.show();
    };
    
    
    editNotificationDialogueConfig = {
        id: 'edit_notification_dialogue',
        xtype: 'editnotificationdialogue',
        title: _t('Edit Notification Subscription'),
        directFn: router.updateNotification,
        reloadFn: reloadNotificationGrid
    };
    
    addNotificationDialogueConfig = {
        id: 'add_notification_dialogue',
        xtype: 'adddialogue',
        title: _t('Add Notification Subscription'),
        directFn: router.addNotification,
        reloadFn: reloadNotificationGrid
    };
    
    editScheduleDialogueConfig = {
        id: 'edit_schedule_dialogue',
        xtype: 'editscheduledialogue',
        title: _t('Edit Notification Subscription'),
        directFn: router.updateWindow,
        reloadFn: reloadScheduleGrid
    };
    
    addScheduleDialogueConfig = {
        id: 'add_schedule_dialogue',
        xtype: 'addialogue',
        title: _t('Add Schedule Window'),
        directFn: router.addWindow,
        submitHandler: function(button) {
            var panel = Ext.getCmp(notificationPanelConfig.id),
                row = panel.getSelectionModel().getSelected(),
                params = {
                    newId: button.refOwner.addForm.newId.getValue(),
                    contextUid: row.data.uid
                };
            
            router.addWindow(params, function(){
                button.refOwner.addForm.newId.setValue('');
                button.refOwner.hide();
                reloadScheduleGrid();
            });
        }
    };
    
    
    EditNotificationDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                modal: true,
                plain: true,
                width: 450,
                height: 600,
                autoScroll: true,
                border: false,
                closeAction: 'hide',
                listeners: {
                    beforeshow: function(window) {
                        window.editForm.setEmailFieldState(
                            window.editForm.action_combo.value
                        );
                    }
                },
                items:{
                    xtype:'form',
                    ref: 'editForm',
                    border: false,
                    buttonAlign: 'center',
                    monitorValid: true,
                    autoWidth: true,
                    setEmailFieldState: function(value) {
                        if (value === 'page') {
                            this.email_fields.collapse();
                        } else {
                            this.email_fields.expand();
                        }
                    },
                    items:[
                        {
                            xtype: 'hidden',
                            name: 'uid',
                            ref: 'uid'
                        },{
                            xtype: 'checkbox',
                            name: 'enabled',
                            ref: 'enabled',
                            fieldLabel: _t('Enabled')
                        }, 
                        new Ext.form.ComboBox({
                            store: new Ext.data.ArrayStore({
                                autoDestroy: true,
                                fields:['value','label'],
                                id: 0,
                                data: [
                                    ['email','Email'],
                                    ['page','Page']
                                ]
                            }),
                            listeners: {
                                beforeselect: function(combo, record, index) {
                                    combo.refOwner.setEmailFieldState(record.data.value);
                                }
                            },
                            name:'action',
                            ref: 'action_combo',
                            allowBlank:false,
                            required:true,
                            editable:false,
                            displayField:'label',
                            valueField:'value',
                            fieldLabel: _t('Action'),
                            mode:'local',
                            triggerAction: 'all'
                        }),{
                            xtype: 'fieldset',
                            ref: 'email_fields',
                            unstyled: true,
                            border: false,
                            collapsed: true,
                            hideBorders: true,
                            items: [
                                new Ext.form.ComboBox({
                                    id: 'htmltextcombo',
                                    store: new Ext.data.ArrayStore({
                                        autoDestroy: true,
                                        id: 0,
                                        fields:['value','label'],
                                        data: [
                                            ['html','HTML'],
                                            ['text','Text']
                                        ]
                                    }),
                                    name: 'body_content_type',
                                    ref: '../body_content_type',
                                    allowBlank:false,
                                    required:true,
                                    editable:false,
                                    displayField:'label',
                                    valueField:'value',
                                    fieldLabel: _t('Body Content Type'),
                                    mode:'local',
                                    triggerAction: 'all',
                                    width: 'auto'
                                }),{
                                    xtype: 'textfield',
                                    name: 'subject_format',
                                    ref: '../subject_format',
                                    width: 300,
                                    fieldLabel: _t('Message (Subject) Format')
                                },{
                                    xtype: 'textarea',
                                    name: 'body_format',
                                    ref: '../body_format',
                                    width: 300,
                                    height: 300,
                                    fieldLabel: _t('Body Format')
                                },{
                                    xtype: 'textfield',
                                    name: 'clear_subject_format',
                                    ref: '../clear_subject_format',
                                    width: 300,
                                    fieldLabel: _t('Clear Message (Subject) Format')
                                },{
                                    xtype: 'textarea',
                                    name: 'clear_body_format',
                                    ref: '../clear_body_format',
                                    width: 300,
                                    height: 300,
                                    fieldLabel: _t('Clear Body Format')
                                }
                            ]
                        }, {
                            xtype: 'textfield',
                            name: 'explicit_recipients',
                            ref: 'explicit_recipients',
                            width: 300,
                            fieldLabel: _t('Explicit Recipients')
                        },
                        new Ext.form.ComboBox({
                            store: new Ext.data.DirectStore({
                                fields:['uuid','name'],
                                directFn: router.getTriggers,
                                root: 'data',
                                autoLoad: true
                            }),
                            name: 'subscriptions',
                            allowBlank:false,
                            required:true,
                            editable:false,
                            displayField:'name',
                            valueField:'uuid',
                            triggerAction: 'all',
                            fieldLabel: _t('Subscribe To')
                        })
                        
                    ],
                    buttons:[
                        {
                            xtype: 'button',
                            text: _t('Submit'),
                            ref: '../../submitButton',
                            formBind: true,
                            handler: function(button) {
                                var params = button.refOwner.editForm.getForm().getFieldValues();
                                config.directFn(params, function(){
                                    button.refOwner.hide();
                                    config.reloadFn();
                                });
                            }
                        },{
                            xtype: 'button',
                            ref: '../../cancelButton',
                            text: _t('Cancel'),
                            handler: function(button) {
                                button.refOwner.hide();
                            }
                        }]
                    }
            });
            EditNotificationDialogue.superclass.constructor.apply(this, arguments);
        },
        loadData: function(data) {
            Ext.each(this.editForm.items.items, function(item, index, allitems) {
                if (item.xtype === 'fieldset') {
                    Ext.each(item.items.items, function(item, index, allitems) {
                        item.setValue(eval('data.'+item.name));
                    });
                } else {
                    item.setValue(eval('data.'+item.name));
                }
            });
        }
    });
    Ext.reg('editnotificationdialogue', EditNotificationDialogue);
    
    
    EditScheduleDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                modal: true,
                plain: true,
                border: false,
                closeAction: 'hide',
                items:{
                    xtype:'form',
                    ref: 'editForm',
                    border: false,
                    buttonAlign: 'center',
                    monitorValid: true,
                    autoWidth: true,
                    items:[
                        {
                            xtype: 'hidden',
                            name: 'uid',
                            ref: 'uid'
                        },{
                            xtype: 'checkbox',
                            name: 'enabled',
                            ref: 'enabled',
                            fieldLabel: _t('Enabled')
                        },{
                            xtype: 'datefield',
                            name: 'start',
                            ref: 'start',
                            fieldLabel: _t('Start')
                        },
                        new Ext.form.ComboBox({
                            store: new Ext.data.ArrayStore({
                                autoDestroy: true,
                                fields:['value'],
                                id: 0,
                                data: [
                                    ['Never'],
                                    ['Daily'],
                                    ['Every Weekday'],
                                    ['Weekly'],
                                    ['Monthly'],
                                    ['First Sunday of the Month']
                                ]
                            }),
                            mode: 'local',
                            name: 'repeat',
                            allowBlank:false,
                            required:true,
                            editable:false,
                            displayField:'value',
                            valueField:'value',
                            triggerAction: 'all',
                            fieldLabel: _t('Repeat')
                        }),{
                            xtype: 'textfield',
                            name: 'duration',
                            ref: 'duration',
                            fieldLabel: _t('Duration')
                        }
                    ],
                    buttons:[
                        {
                            xtype: 'button',
                            text: _t('Submit'),
                            ref: '../../submitButton',
                            formBind: true,
                            handler: function(button) {
                                var params = button.refOwner.editForm.getForm().getFieldValues();
                                config.directFn(params, function(){
                                    button.refOwner.hide();
                                    config.reloadFn();
                                });
                            }
                        },{
                            xtype: 'button',
                            ref: '../../cancelButton',
                            text: _t('Cancel'),
                            handler: function(button) {
                                button.refOwner.hide();
                            }
                        }]
                    }
            });
            EditScheduleDialogue.superclass.constructor.apply(this, arguments);
        },
        loadData: function(data) {
            Ext.each(this.editForm.items.items, function(item, index, allitems) {
                item.setValue(eval('data.'+item.name));
            });
        }
    });
    Ext.reg('editscheduledialogue', EditScheduleDialogue);
    
    
    editNotificationDialogue = new EditNotificationDialogue(editNotificationDialogueConfig);
    addNotificationDialogue = new AddDialogue(addNotificationDialogueConfig);
    
    editScheduleDialogue = new EditScheduleDialogue(editScheduleDialogueConfig);
    addScheduleDialogue = new AddDialogue(addScheduleDialogueConfig);
    
    
    NotificationSubscriptions = Ext.extend(Ext.grid.GridPanel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                autoScroll: true,
                border: false,
                height: 500,
                viewConfig: {
                    forceFit: true
                },
                listeners: {
                    rowdblclick: function(grid, rowIndex, event){
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayNotificationEditDialogue(row.data);
                        }
                    }
                },
                selModel: new Ext.grid.RowSelectionModel({
                    singleSelect: true,
                    listeners: {
                        rowselect: function(sm, rowIndex, record) {
                            var row = sm.getSelected(),
                                panel = Ext.getCmp(schedulesPanelConfig.id);
                            panel.setContext(row.data.uid);
                            panel.disableButtons(false);
                            sm.grid.customizeButton.setDisabled(false);
                        },
                        rowdeselect: function(sm, rowIndex, record) {
                            Ext.getCmp(schedulesPanelConfig.id).disableButtons(true);
                            sm.grid.customizeButton.setDisabled(true);
                        }
                    },
                    scope: this
                }),
                store: {
                    xtype: 'directstore',
                    directFn: router.getNotifications,
                    root: 'data',
                    autoLoad: true,
                    fields: [
                        'uid',
                        'newId',
                        'enabled',
                        'action',
                        'body_content_type',
                        'subject_format',
                        'body_format',
                        'clear_subject_format',
                        'clear_body_format',
                        'explicit_recipients',
                        'subscriptions'
                    ]
                },
                colModel: new Ext.grid.ColumnModel({
                    columns: [{
                        dataIndex: 'enabled',
                        header: _t('Enabled'),
                        sortable: true
                    },{
                        dataIndex: 'newId',
                        header: _t('Id'),
                        width:200,
                        sortable: true
                    },{
                        dataIndex: 'action',
                        header: _t('Action'),
                        sortable: true
                    }]
                }),
                tbar:[{
                    xtype: 'button',
                    iconCls: 'add',
                    ref: '../addButton',
                    handler: function(button) {
                        Ext.getCmp(addNotificationDialogueConfig.id).show();
                    }
                },{
                    xtype: 'button',
                    iconCls: 'delete',
                    ref: '../deleteButton',
                    handler: function(button) {
                        var row = button.refOwner.getSelectionModel().getSelected(),
                            uid, 
                            params, 
                            callback;
                        if (row){
                            uid = row.data.uid;
                            // show a confirmation
                            Ext.Msg.show({
                                title: _t('Delete Notification Subscription'),
                                msg: String.format(_t("Are you sure you wish to delete the notification, {0}?"), row.data.newId),
                                buttons: Ext.Msg.OKCANCEL,
                                fn: function(btn) {
                                    if (btn == "ok") {
                                        params = {
                                            uid:uid
                                        };
                                        callback = function(response){
                                            var panel = Ext.getCmp(schedulesPanelConfig.id);
                                            panel.getStore().removeAll();
                                            panel.disableButtons(true);
                                            Ext.getCmp(notificationPanelConfig.id).customizeButton.setDisabled(true);
                                            reloadNotificationGrid();
                                        };
                                        router.removeNotification(params, callback);

                                    } else {
                                        Ext.Msg.hide();
                                    }
                                }
                            });
                        }
                    }
                },{
                    xtype: 'button',
                    iconCls: 'customize',
                    disabled:true,
                    ref: '../customizeButton',
                    handler: function(button){
                        var row = button.refOwner.getSelectionModel().getSelected();
                        if (row) {
                            displayNotificationEditDialogue(row.data);
                        }
                    }
                }]
            });
            NotificationSubscriptions.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            this.uid = uid;
            this.getStore().load({
                params: {
                    uid: uid
                }
            });
        }
    });
    Ext.reg('notificationsubscriptions', NotificationSubscriptions);
    
    notification_panel = Ext.create(notificationPanelConfig);
    
    
    SchedulesPanel = Ext.extend(Ext.grid.GridPanel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                autoScroll: true,
                border: false,
                height: 500,
                viewConfig: {
                    forceFit: true
                },
                listeners: {
                    rowdblclick: function(grid, rowIndex, event){
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayScheduleEditDialogue(row.data);
                        }
                    }
                },
                selModel: new Ext.grid.RowSelectionModel({
                    singleSelect: true,
                    listeners: {
                        rowselect: function(sm, rowIndex, record) {
                            var row = sm.getSelected();
                            sm.grid.customizeButton.setDisabled(false);
                        },
                        rowdeselect: function(sm, rowIndex, record) {
                            sm.grid.customizeButton.setDisabled(true);
                        }
                    },
                    scope: this
                }),
                store: {
                    xtype: 'directstore',
                    directFn: router.getWindows,
                    root: 'data',
                    fields: [
                        'uid',
                        'newId',
                        'enabled',
                        'start',
                        'repeat',
                        'duration'
                    ]
                },
                colModel: new Ext.grid.ColumnModel({
                    columns: [{
                        dataIndex: 'enabled',
                        header: _t('Enabled'),
                        sortable: true
                    },{
                        dataIndex: 'newId',
                        header: _t('Id'),
                        width:200,
                        sortable: true
                    },{
                        dataIndex: 'start',
                        header: _t('Start'),
                        width:200,
                        sortable: true
                    }]
                }),
                tbar:[{
                    xtype: 'button',
                    iconCls: 'add',
                    ref: '../addButton',
                    handler: function(button) {
                        addScheduleDialogue.show();
                    }
                },{
                    xtype: 'button',
                    iconCls: 'delete',
                    ref: '../deleteButton',
                    handler: function(button) {
                        var row = button.refOwner.getSelectionModel().getSelected(),
                            uid, 
                            params;
                        if (row){
                            uid = row.data.uid;
                            console.log(row.data);
                            // show a confirmation
                            Ext.Msg.show({
                                title: _t('Delete Subscription Schedule'),
                                msg: String.format(_t("Are you sure you wish to delete the schedule, {0}?"), row.data.newId),
                                buttons: Ext.Msg.OKCANCEL,
                                fn: function(btn) {
                                    if (btn == "ok") {
                                        params = {
                                            uid:uid
                                        };
                                        router.removeWindow(params, reloadScheduleGrid);
                                    } else {
                                        Ext.Msg.hide();
                                    }
                                }
                            });
                        }
                    }
                },{
                    xtype: 'button',
                    iconCls: 'customize',
                    disabled:true,
                    ref: '../customizeButton',
                    handler: function(button){
                        var row = button.refOwner.getSelectionModel().getSelected();
                        if (row) {
                            displayScheduleEditDialogue(row.data);
                        }
                    }
                }]

            });
            SchedulesPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid){
            this.uid = uid;
            this.getStore().load({
                params: {
                    uid: uid
                }
            });
            this.disableButtons(false);
            this.customizeButton.setDisabled(true);
        },
        disableButtons: function(bool){
            this.addButton.setDisabled(bool);
            this.deleteButton.setDisabled(bool);
        }
    });
    Ext.reg('schedulespanel', SchedulesPanel);
    
    schedules_panel = Ext.create(schedulesPanelConfig);
    
    
    NotificationPageLayout = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                id: 'notification_subscription_panel',
                layout:'border',
                defaults: {
                    collapsible: false,
                    split: true,
                    border: false
                },
                items: [{
                    title: _t('Notification Subscription Schedules'),
                    region:'east',
                    width: 375,
                    minSize: 100,
                    maxSize: 375,
                    items: [config.schedulePanel]
                },{
                    title: _t('Notification Subscriptions'),
                    region:'center',
                    items:[config.notificationPanel]
                }]

            });
            NotificationPageLayout.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('notificationsubscriptions', NotificationPageLayout);
    
    
    notificationsPanelConfig = {
        id: 'notifications_panel',
        xtype: 'notificationsubscriptions',
        schedulePanel: schedules_panel,
        notificationPanel: notification_panel
    };
    
    
    
    
    /***
     * TRIGGERS
     **/
     
    colModelConfig = {
        defaults: {
            menuDisabled: true
        },
        columns: [
            {
                id: 'enabled',
                dataIndex: 'enabled',
                header: _t('Enabled'),
                xtype: 'booleancolumn',
                width: 70,
                sortable: true
            }, {
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                width: 200,
                sortable: true
            }, {
                id: 'delay',
                dataIndex: 'delay_seconds',
                header: _t('Delay'),
                xtype: 'numbercolumn',
                width: 70,
                format: '0',
                sortable: true
            }, {
                id: 'repeat',
                dataIndex: 'repeat_seconds',
                header: _t('Repeat'),
                xtype: 'numbercolumn',
                width: 70,
                format: '0',
                sortable: true
            }, {
                id: 'send_clear',
                dataIndex: 'send_clear',
                header: _t('Send Clear?'),
                xtype: 'booleancolumn',
                width: 110,
                sortable: true
            }
        ]
    };
    
    triggersPanelConfig = {
        id: 'triggers_grid_panel',
        xtype: 'TriggersGridPanel'
    };
    
    detailPanelConfig = {
        id: 'triggers_detail_panel',
        xtype: 'contextcardpanel',
        split: true,
        region: 'center',
        layout: 'card',
        activeItem: 0,
        items: [triggersPanelConfig, notificationsPanelConfig]
    };
    
    navSelectionModel = new Ext.tree.DefaultSelectionModel({
        listeners: {
            selectionchange: function (sm, newnode) {
                var p = Ext.getCmp(detailPanelConfig.id);
                p.layout.setActiveItem(newnode.attributes.target);
                p.setContext(newnode.attributes.target);
            }
        }
    });
    
    masterPanelConfig = {
        id: 'master_panel',
        region: 'west',
        split: 'true',
        width: 275,
        autoScroll: false,
        items: [
            {
                id: 'master_panel_navigation',
                xtype: 'treepanel',
                region: 'west',
                split: 'true',
                width: 275,
                autoScroll: true,
                border: false,
                rootVisible: false,
                selModel: navSelectionModel,
                layout: 'fit',
                bodyStyle: { 'margin-top' : 10 },
                root: {
                    text: 'Trigger Navigation',
                    draggable: false,
                    id: 'trigger_root',
                    expanded: true,
                    children: [
                        {
                            target: triggersPanelConfig.id,
                            text: 'Triggers',
                            leaf: true,
                            iconCls: 'no-icon'
                        }, {
                            target: notificationsPanelConfig.id,
                            text: 'Notifications',
                            leaf: true,
                            iconCls: 'no-icon'
                        }
                    ]
                }
            }
        ]
    };
    
    EditTriggerDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                modal: true,
                plain: true,
                border: false,
                closeAction: 'hide',
                items:{
                    xtype:'form',
                    ref: 'editForm',
                    border: false,
                    buttonAlign: 'center',
                    monitorValid: true,
                    items:[
                        {
                            xtype: 'hidden',
                            name: 'uuid',
                            ref: 'uuid'
                        },{
                            xtype: 'textfield',
                            name: 'name',
                            ref: 'name',
                            allowBlank: false,
                            fieldLabel: _t('Name')
                        },{
                            xtype: 'numberfield',
                            name: 'delay_seconds',
                            ref: 'delay_seconds',
                            allowBlank: true,
                            allowNegative: false,
                            allowDecimals: false,
                            fieldLabel: _t('Delay (seconds)')
                        },{
                            xtype: 'numberfield',
                            name: 'repeat_seconds',
                            ref: 'repeat_seconds',
                            allowBlank: true,
                            allowNegative: false,
                            allowDecimals: false,
                            fieldLabel: _t('Repeat (seconds)')
                        },{
                            xtype: 'checkbox',
                            name: 'enabled',
                            ref: 'enabled',
                            fieldLabel: _t('Enabled')
                        },{
                            xtype: 'checkbox',
                            name: 'send_clear',
                            ref: 'send_clear',
                            fieldLabel: _t('Send Clear')
                        },{
                            xtype: 'textarea',
                            name: 'filter',
                            ref: 'filter',
                            width: 400,
                            height: 400,
                            fieldLabel: _t('Filter Source')
                        }
                    ],
                    buttons:[
                        {
                            xtype: 'button',
                            text: _t('Submit'),
                            ref: '../../submitButton',
                            formBind: true,
                            handler: function(button) {
                                var params = button.refOwner.editForm.getForm().getFieldValues(),
                                    _filter = params.filter;
                                params.filter = {'content':_filter};
                                
                                config.directFn(params, function(){
                                    button.refOwner.hide();
                                    config.reloadFn();
                                });
                            }
                        },{
                            xtype: 'button',
                            ref: '../../cancelButton',
                            text: _t('Cancel'),
                            handler: function(button) {
                                button.refOwner.hide();
                            }
                        },{
                            xtype: 'button',
                            ref: '../../validateSource',
                            text: _t('Check Filter'),
                            handler: function(button) {
                                var params = {
                                    source: button.refOwner.editForm.filter.getValue()
                                };
                                config.validateFn(params, function(response){
                                    if (response.success) {
                                        Zenoss.message.success('Filter source validated successfully.');
                                    }
                                });
                                
                            }
                        }]
                    }
            });
            EditTriggerDialogue.superclass.constructor.apply(this, arguments);
        },
        loadData: function(data) {
            this.editForm.uuid.setValue(data.uuid);
            this.editForm.enabled.setValue(data.enabled);
            this.editForm.name.setValue(data.name);
            this.editForm.delay_seconds.setValue(data.delay_seconds);
            this.editForm.repeat_seconds.setValue(data.repeat_seconds);
            this.editForm.send_clear.setValue(data.send_clear);
            this.editForm.filter.setValue(data.filter.content);
        }
    });
    Ext.reg('edittriggerdialogue', EditTriggerDialogue);
    
    
    reloadTriggersGrid = function() {
        Ext.getCmp(triggersPanelConfig.id).getStore().reload();
    };
    
    displayEditTriggerDialogue = function(data) {
        editTriggerDialogue.loadData(data);
        editTriggerDialogue.show();
    };
    
    addTriggerDialogue = new AddDialogue({
        title: _t('Add Trigger'),
        directFn: router.addTrigger,
        reloadFn: reloadTriggersGrid
    });
    
    editTriggerDialogue = new EditTriggerDialogue({
        title: _t('Edit Trigger'),
        directFn: router.updateTrigger,
        reloadFn: reloadTriggersGrid,
        validateFn: router.parseFilter
    });

    colModel = new Ext.grid.ColumnModel(colModelConfig);
    
    TriggersGridPanel = Ext.extend(Ext.grid.GridPanel, {
        constructor: function(config) {
            Ext.applyIf(config, {
                autoExpandColumn: 'name',
                stripeRows: true,
                cm: colModel,
                title: _t('Triggers'),
                store: {
                    xtype: 'directstore',
                    directFn: router.getTriggers,
                    root: 'data',
                    autoLoad: true,
                    fields: ['uuid', 'enabled', 'name', 'delay_seconds', 'repeat_seconds', 'send_clear', 'filter']
                },
                sm: new Ext.grid.RowSelectionModel({
                    singleSelect: true,
                    listeners: {
                        rowselect: function(sm, rowIndex, record) {
                            // enable/disabled the edit button
                            sm.grid.deleteButton.setDisabled(false);
                            sm.grid.customizeButton.setDisabled(false);
                        },
                        rowdeselect: function(sm, rowIndex, record) {
                            sm.grid.deleteButton.setDisabled(true);
                            sm.grid.customizeButton.setDisabled(true);
                        }
                    },
                    scope: this
                }),
                listeners: {
                    rowdblclick: function(grid, rowIndex, event) {
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayEditTriggerDialogue(row.data);
                        }
                    }
                },
                tbar:[
                    {
                        xtype: 'button',
                        iconCls: 'add',
                        ref: '../addButton',
                        handler: function(button) {
                            addTriggerDialogue.show();
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'delete',
                        ref: '../deleteButton',
                        handler: function(button) {
                            var row = button.refOwner.getSelectionModel().getSelected(),
                                uuid, params, callback;
                            if (row){
                                uuid = row.data.uuid;
                                // show a confirmation
                                Ext.Msg.show({
                                    title: _t('Delete Trigger'),
                                    msg: String.format(_t("Are you sure you wish to delete the trigger, {0}?"), row.data.name),
                                    buttons: Ext.Msg.OKCANCEL,
                                    fn: function(btn) {
                                        if (btn == "ok") {
                                            params= {
                                                uuid:uuid
                                            };
                                            callback = function(response){
                                                // item removed, reload grid.
                                                button.refOwner.deleteButton.setDisabled(true);
                                                button.refOwner.customizeButton.setDisabled(true);
                                                reloadTriggersGrid();
                                            };
                                            router.removeTrigger(params, callback);
                                            
                                        } else {
                                            Ext.Msg.hide();
                                        }
                                    }
                                });
                            }
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'customize',
                        disabled:true,
                        ref: '../customizeButton',
                        handler: function(button){
                            var row = button.refOwner.getSelectionModel().getSelected();
                            if (row) {
                                displayEditTriggerDialogue(row.data);
                            }
                        }
                    }
                ]
            });
            TriggersGridPanel.superclass.constructor.call(this, config);
        },
        setContext: function(uid) {
            // triggers are not context aware.
            this.getStore().load();
        }
    });
    Ext.reg('TriggersGridPanel', TriggersGridPanel);
    
    Ext.getCmp('center_panel').add({
        id: 'center_panel_container',
        layout: 'border',
        defaults: {
            'border':false
        },
        items: [
            masterPanelConfig,  // navigation
            detailPanelConfig   // content panel
        ]
    });

});