/* jshint boss:true */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){
    var router = Zenoss.remote.PropertiesRouter;

    Ext.ns('Zenoss.cproperties');


    /**
     * Allow zenpack authors to register custom cproperty
     * editors.
     **/
    Zenoss.cproperties.registerCPropertyType = function(id, config){
        Zenoss.zproperties.configPropertyConfigs[id] = config;
    };

    Zenoss.cproperties.hideApplyCheckbox = function(grid){
        if(grid.uid !== "/zport/dmd/Devices"){
            return false;
        }else{
            return true;
        }
    };

    function showAddNewPropertyDialog(grid) {
        var addhandler, uid, config, dialog, msg,
        clearPanel = function(panel){
            var f;
            while(f = panel.items.first()){
              panel.remove(f, true);// can do false to reuse the elements
            }
        };
        Zenoss.zproperties.configPropertyConfigs.state.context = "add";
        msg = '<span style="color:#aaa;">';
        msg += _t('Names must start with a lower case c')+' <br>';
        msg += _t('Example: ');
        msg += '<span style="color:yellow;">';
        msg += _t('cPropertyName');
        msg += '</span></span>';

        addhandler = function() {
            var c = dialog.getForm().getForm().getValues(), value;
            uid = "/zport/dmd/Devices"; // to force it to apply to the root on every newly created prop

            // if it's type 'lines' then it was already saved. the submit should be 'updating' it instead
            if (c.type === 'lines') {
                if (c.value) {
                    // send back as an array separated by a new line
                    value = Ext.Array.map(c.value.split('\n'), function(s) {return Ext.String.trim(s);});
                } else {
                    // send back an empty list if nothing is set
                    value = [];
                }
            }else{
                value = c.value;
            }

            if (c.type === 'selection'){
            // this is a submit on a selection, which was already added as new with the selection action on dialog
            // so here we're just updating the newly created item with the line item
                var params = {
                    uid: uid,
                    zProperty: c.name,
                    value: c.selection
                };
                Zenoss.remote.PropertiesRouter.setZenProperty(params, function(response){
                    if (response.success) {
                        grid.refresh();
                    }
                });
            }else{
                var params = {
                    uid: uid,
                    id: c.name,
                    type: c.type,
                    label: c.description,
                    value: value
                };

                Zenoss.remote.PropertiesRouter.addCustomProperty(params, function(response){
                    if (response.success) {
                        grid.refresh();
                    }
                });
            }
        };

        // form config
        config = {
            submitHandler: addhandler,
            minHeight: 315,
            autoHeight: true,
            width: 480,
            id: 'addCustomDialog',
            defaults:{
                applyLocalHidden: true
            },
            title: _t('Add Custom Config Property'),
            items: [{
                    xtype: 'panel',
                    layout: 'hbox',
                    margin: '0 0 1px 0',
                    items: [
                        {
                            xtype: 'textfield',
                            name: 'name',
                            fieldLabel: _t('Property Name'),
                            width:220,
                            regex: /^c[A-Z]/,
                            regexText: _t("Custom Properties must start with a lower case c"),
                            value: ""
                        },{
                            xtype: 'panel',
                            padding: '0 0 0 10px',
                            items: [
                                {
                                    xtype: 'label',
                                    width: 230,
                                    height: 50,
                                    html: msg
                                }
                            ]
                        }
                    ]
                },{
                    xtype: 'textareafield',
                    name: 'description',
                    margin: '3px 0 10px 0',
                    width:457,
                    height:55,
                    ref: 'desc',
                    fieldLabel: _t('Description')
                },{
                    xtype: 'panel',
                    layout: 'hbox',
                    padding: '8px',
                    style: {border:'1px solid #555'},
                    items: [
                        {
                            xtype: 'combo',
                            name: 'type',
                            ref: 'type',
                            valueField: 'name',
                            value:'string',
                            displayField: 'name',
                            typeAhead: false,
                            forceSelection: true,
                            triggerAction: 'all',
                            fieldLabel: _t('Type'),
                            listeners:{
                                change: function(e){
                                    var panel = Ext.getCmp('typeSelectionPanel');
                                    clearPanel(panel);
                                    panel.add(Zenoss.zproperties.configPropertyConfigs[e.value]);
                                }
                            },
                            listConfig: {
                                maxWidth:185
                            },
                            store: new Ext.data.ArrayStore({
                                model: 'Zenoss.model.Name',
                                data: [
                                ['boolean'],['date'],['float'],['int'],['lines'],
                                ['long'],['password'],['string' ],['selection']
                                ]
                            })
                        },{
                            xtype: 'panel',
                            padding: '0 0 0 10px',
                            id:'typeSelectionPanel',
                            items:[Zenoss.zproperties.configPropertyConfigs.string]

                        }
                ]
                }
            ],
            // explicitly do not allow enter to submit the dialog
            keys: {

            }
        };

        dialog = new Zenoss.SmartFormDialog(config);

        if (Zenoss.Security.hasPermission('zProperties Edit')) {
            dialog.show();
        }


    }

    function showEditCustPropertyDialog(data, grid){
        var path;
        if (grid.uid === "/zport/dmd/Devices"){
            path = "/";
        }else{
            path = grid.uid.split("Devices")[1];
        }
        var pathMsg = '<div style="padding-top:10px;">';
        pathMsg += _t(" This value will be changed to apply to the current location:");
        pathMsg += '<div style="color:#aaa;padding-top:3px;">';
        pathMsg += '<div style="color:#fff;background:#111;margin:2px 7px 2px 0;padding:5px;"> '+path+' </div>';
        pathMsg += '</div></div>';

        var lbltemplate = '<div style="margin:5px 0 15px 0;"><b>{0}</b> <span style="display:inline-block;padding-left:5px;color:#aaccaa">{1}</span></div>';

        var items = [
                {
                    xtype: 'label',
                    width: 500,
                    height: 50,
                    html: Ext.String.format(lbltemplate, _t("Name:"), data.id)
                },{
                    xtype: 'label',
                    width: 500,
                    height: 50,
                    html: Ext.String.format(lbltemplate, _t("Description:"),data.label)
                },{
                    xtype: 'label',
                    width: 500,
                    height: 50,
                    html: Ext.String.format(lbltemplate, _t("Path:"),data.path)
                },{
                    xtype: 'label',
                    width: 500,
                    height: 50,
                    html: Ext.String.format(lbltemplate, _t("Type:"),data.type)
                },{
                    xtype: 'label',
                    width: 300,
                    height: 90,
                    html: pathMsg
                }
        ];

        var pkg = {
            'items': items,
            'uid': grid.uid,
            'type': data.type,
            'value': data.valueAsString,
            'name': data.id,
            'grid': grid,
            'dialogId': 'editCustomDialog',
            'minHeight': 300,
            'width': 500,
            'options': data.options
        };
        Zenoss.zproperties.showEditPropertyDialog(pkg);

    }
    /**
     * @class Zenoss.CustomProperty.Model
     * @extends Ext.data.Model
     * Field definitions for the Config Properties
     **/
    Ext.define('Zenoss.CustomProperty.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: [
            {name: 'id'},
            {name: 'label'},
            {name: 'valueAsString'},
            {name: 'path'},
            {name: 'type'},
            {name: 'islocal'}
        ]
    });

    /**
     * @class Zenoss.CustomProperty.Store
     * @extends Zenoss.DirectStore
     * Store for our configuration properties grid
     **/
    Ext.define("Zenoss.CustomProperty.Store", {
        extend: "Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.CustomProperty.Model',
                initialSortColumn: 'id',
                pageSize: 300,
                directFn: Zenoss.remote.PropertiesRouter.getCustomProperties
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.CustomProperty.Grid", {
        alias: ['widget.custompropertygrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Zenoss.Security.onPermissionsChange(function() {
                this.disableButtons(Zenoss.Security.doesNotHavePermission('zProperties Edit'));
            }, this);

            Ext.applyIf(config, {
                stateId: config.id || 'custom_property_grid',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                stateful: true,
                tbar:[
                    {
                    xtype: 'button',
                    iconCls: 'add',
                    tooltip: _t('Add a new Custom Property'),
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    ref: 'addButton',
                        handler: function(button) {
                            var grid = button.up("custompropertygrid");
                            showAddNewPropertyDialog(grid);
                        }
                    },
                    {
                    xtype: 'button',
                    iconCls: 'customize',
                    tooltip: _t('Edit selected Custom Property'),
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    ref: 'customizeButton',
                        handler: function(button) {
                            var grid = button.up("custompropertygrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();

                            if (Ext.isEmpty(selected)) {
                                return;
                            }
                            // single selection
                            data = selected[0].data;
                            showEditCustPropertyDialog(data, grid);
                        }
                    }, {
                    xtype: 'button',
                    iconCls: 'refresh',
                    tooltip: _t('Refresh'),
                    ref: '../refreshButton',
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    handler: function(button) {
                        var grid = button.up("custompropertygrid");
                        grid.refresh();
                    }
                    },{
                        xtype: 'button',
                        iconCls: 'delete',
                        tooltip: _t('Delete Custom Property'),
                        handler: function(button) {
                            var grid = button.up("custompropertygrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();
                            if (Ext.isEmpty(selected)) {
                                return;
                            }

                            data = selected[0].data;
                            new Zenoss.dialog.SimpleMessageDialog({
                                title: _t('Delete Local Property'),
                                message: Ext.String.format(_t("Are you sure you want to delete the Custom Property {0}?"), data.id),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        if (grid.uid) {
                                            router.deleteZenProperty({
                                                uid: grid.uid,
                                                zProperty: data.id
                                            }, function(response){
                                                grid.refresh();
                                            });
                                        }
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    }
                ],
                store: Ext.create('Zenoss.CustomProperty.Store', {}),
                columns: [{
                        header: _t("Property Name"),
                        id: 'property',
                        dataIndex: 'id',
                        width: 150,
                        sortable: true
                    },{
                        id: 'label',
                        dataIndex: 'label',
                        header: _t('Description'),
                        width: 400,
                        sortable: true
                    },{
                        id: 'valueString',
                        dataIndex: 'valueAsString',
                        header: _t('Value'),
                        flex: 1,
                        sortable: true
                    },{
                        id: 'pathid',
                        dataIndex: 'path',
                        header: _t('Path'),
                        width: 90,
                        sortable: true
                    },{
                        id: 'type',
                        dataIndex: 'type',
                        header: _t('Type'),
                        width: 60,
                        sortable: true
                    },{
                        id: 'is_local',
                        dataIndex: 'islocal',
                        header: _t('Is Local'),
                        width: 50,
                        sortable: true,
                        filter: false,
                        renderer: function(value){
                            if (value) {
                                return 'Yes';
                            }
                            return '';
                        }
                    }]
            });
            this.callParent(arguments);
            this.on('itemdblclick', this.onRowDblClick, this);
        },
        setContext: function(uid) {

            this.uid = uid;
            // load the grid's store
            this.callParent(arguments);
        },
        onRowDblClick: function(grid, rowIndex, e) {
            var data,
                selected = this.getSelectionModel().getSelection();
            if (!selected) {
                return;
            }
            data = selected[0].data;
            showEditCustPropertyDialog(data, this);
        },
        disableButtons: function(bool) {
            var btns = this.query("button");
            Ext.each(btns, function(btn){
                btn.setDisabled(bool);
            });
        }
    });

    Ext.define("Zenoss.form.CustomPropertyPanel", {
        alias:['widget.custompropertypanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            this.gridId = "custompropgridId";
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                height: 800,
                items: [{
                    id: this.gridId,
                    xtype: "custompropertygrid",
                    ref: 'customGrid',
                    displayFilters: config.displayFilters
                }]
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            Ext.getCmp(this.gridId).setContext(uid);
        }
    });

})();
