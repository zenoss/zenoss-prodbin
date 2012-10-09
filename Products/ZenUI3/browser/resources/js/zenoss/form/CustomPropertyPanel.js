/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


(function(){
    var router = Zenoss.remote.PropertiesRouter,
        customPropertyPanel,
        cpropertyConfigs = {};

    Ext.ns('Zenoss.cproperties');
    
    var checkText = function(e){
        uid = "/zport/dmd/Devices"; // to force it to apply to the root on every newly created prop
        
        var params = {
            uid: uid,
            zProperty: e
        };          
        Zenoss.remote.PropertiesRouter.getZenProperty(params, function(response){
            if (response.success) {
                if (response.data.type == "lines"){  
                    var lines = response.data.value, context = cpropertyConfigs.state.context, formID;
                    context == "add" ? formID = "addCustomDialog" : formID = "editCustomDialog";
                    var c = Ext.getCmp(formID).getForm().getForm().getValues();
                        
                    // we got a 'lines' item back. Lets save this so we can complete the users goal 

                    var params = {
                        uid: uid,
                        id: c.name,
                        type: c.type,
                        label: c.description,
                        value: c.value
                    };
                    var addToCombo = function(){
                        // dump the array response.data.value into the combo box by breaking it up into an array of arrays 
                        // for loadData to work
                        var combo = Ext.getCmp('linesCombo');                    
                        var data = [];
                        for (var i = 0; i < lines.length; i++){
                            data.push([lines[i]]);
                        }                   
                        combo.store.loadData(data);
                        // fire off a selection of the first item so it's obvious something happened
                        combo.setValue(combo.store.getAt('0'));                      
                    }
                    if (context == "add"){
                        Zenoss.remote.PropertiesRouter.addCustomProperty(params, function(response){
                            if (response.success) {
                                addToCombo();
                            }
                        });                      
                    }else{
                        addToCombo();
                    }
                
                }
            }
        });       
    };    
    
    var propValText = _t("Value for Property Type:");
    Ext.apply(cpropertyConfigs, {
        'state': {
            context: 'add'
        },
        'int': {
            xtype: 'numberfield',
            allowDecimals: false,
            fieldLabel: _t(propValText+' INT'),            
            name: 'value'
        },
        'float': {
            xtype: 'numberfield',
            fieldLabel: _t(propValText+' FLOAT'),            
            name: 'value'
        },
        'long': {
            xtype: 'numberfield',
            fieldLabel: _t(propValText+' LONG'), 
            name: 'value'
        },
        'date': {
            xtype: 'datefield',
            name: 'value',
            fieldLabel: _t(propValText+' DATE')           
        },
        'string': {
            xtype: 'textfield',
            name: 'value',
            fieldLabel: _t(propValText+' STRING'),
            width:220            
        },
        'lines': {
            xtype: 'textarea',
            name: 'value',
            width: 220,
            height: 70,
            fieldLabel: _t(propValText+' LINES')            
        },
        'boolean': {
            xtype: 'checkbox',
            name: 'value',
            fieldLabel: _t(propValText+' BOOLEAN')           
        },
        'password': {
            xtype: 'password',
            name: 'value',
            width:220,
            fieldLabel: _t(propValText+' PASSWORD')
        },
        'selection': {
            xtype: 'panel',
            items: [
                {
                    xtype: 'panel',
                    width: 260,
                    layout: 'hbox',
                    items: [
                        {
                            xtype: 'textfield',
                            name: 'value',
                            id: 'linesSearchBox',
                            width:220,
                            margin: '0 0 5px 0',
                            fieldLabel: _t(propValText+' SELECTION')
                        },{
                            xtype: 'button',
                            iconCls: 'acknowledge',
                            listeners: {
                                afterrender: function(button){
                                    button.setTooltip(_t("Retrieve lines from property for selection"));
                                    if (cpropertyConfigs.state.context == "add"){
                                        button.setTooltip(_t("Save new property and retrieve lines for selection"));
                                    } 
                                }
                            },
                            margin: '17px 0 0 7px',
                            handler: function(button) {
                                var txt = Ext.getCmp('linesSearchBox').getValue();
                                if(txt != ""){
                                    checkText(txt);
                                }else{
                                    Zenoss.message.info(_t('The "Lines" property type cannot be empty. Please enter a "Lines" custom property.'));                                
                                }
                            }
                        }
                        ]    
                },{
                    xtype: 'combo',
                    name: 'selection',
                    queryMode:'local',
                    id: 'linesCombo',
                    store: [ 'none' ],
                    width:220
                }
            ]
        }
    });
  

    /**
     * Allow zenpack authors to register custom cproperty
     * editors.
     **/
    Zenoss.cproperties.registerCPropertyType = function(id, config){
        cpropertyConfigs[id] = config;
    };
    
    Zenoss.cproperties.hideApplyCheckbox = function(grid){
        if(grid.uid != "/zport/dmd/Devices"){ 
            return false;
        }else{
            return true;
        }
    }
    
    function showAddNewPropertyDialog(grid) {
        var addhandler, uid, config, dialog, pathMsg, msg,
        clearPanel = function(panel){
            var f;
            while(f = panel.items.first()){
              panel.remove(f, true);// can do false to reuse the elements
            }
        }
        cpropertyConfigs.state.context = "add";
        msg = '<span style="color:#aaa;">';
        msg += _t('Names must start with lower case c')+' <br>';
        msg += _t('Example: ');
        msg += '<span style="color:yellow;">';
        msg += _t('cProperyName');
        msg += '</span></span>';

        addhandler = function() {
            var c = dialog.getForm().getForm().getValues(), value;
            uid = "/zport/dmd/Devices"; // to force it to apply to the root on every newly created prop
            
            // if it's type 'lines' then it was already saved. the submit should be 'updating' it instead
            if (c.type == 'lines') {
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
            
            if (c.type == 'selection'){ 
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
        }

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
                                    panel.add(cpropertyConfigs[e.value]);
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
                            items:[cpropertyConfigs.string]
        
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
            

        };    

    function showEditCustPropertyDialog(data, grid) {
        var handler, uid, config, editConfig, dialog, type;
        type = data.type;
        cpropertyConfigs.state.context = "edit";
        // Try the specific property id, next the type and finall default to string
        editConfig = cpropertyConfigs[data.id] || cpropertyConfigs[type] || cpropertyConfigs['string'];

        // in case of drop down lists
        if (Ext.isArray(data.options) && data.options.length > 0 && type == 'string') {
            // make it a combo and the options is the store
            editConfig = cpropertyConfigs['options'];
            editConfig.store = data.options;
        }

        // set the default values common to all configs
        Ext.apply(editConfig, {
            fieldLabel: _t('Value'),
            value: data.value,
            ref: 'editConfig',
            checked: data.value,
            name: data.id
        });

        // lines come in as comma separated and should be saved as such
        if (type == 'lines' && Ext.isArray(editConfig.value)){
            editConfig.value = editConfig.value.join('\n');
        }

        handler = function() {
            // save the junk and reload
            var values = dialog.getForm().getForm().getValues(),
                value = values[data.id];
            if ((typeof values.applylocal) == "undefined"){
                values.applylocal = false;
            }                
            if (type == 'lines') {
                if (value) {
                    // send back as an array separated by a new line
                    value = Ext.Array.map(value.split('\n'), function(s) {return Ext.String.trim(s);});
                } else {
                    // send back an empty list if nothing is set
                    value = [];
                }
            }
            // if this is a selection type, then the value is form.selection and not form.value
            if (type == 'selection'){
                value = values.selection;
            }
            var params = {
                uid: grid.uid,
                zProperty: data.id,
                value: value
            };              
            Zenoss.remote.PropertiesRouter.setZenProperty(params, function(response){
                if (response.success) {
                    grid.refresh();
                }
            });

        };
        var path;
        if (grid.uid == "/zport/dmd/Devices"){
            path = "/";
        }else{
            path = grid.uid.split("Devices")[1];
        }
        var pathMsg = '<div style="padding-top:10px;">';
        pathMsg += _t(" This value will be changed to apply to the current location:");
        pathMsg += '<div style="color:#aaa;padding-top:3px;">'; 
        pathMsg += '<div style="color:#fff;background:#111;margin:2px 7px 2px 0;padding:5px;"> '+path+' </div>';
        pathMsg += '</div></div>';
        
        var lbltemplate = '<div style="margin:5px 0 15px 0;"><b>{0}</b> <span style="display:inline-block;padding-left:5px;color:#aaccaa">{1}</span></div>'
        // form config
        config = {
            submitHandler: handler,
            minHeight: 300,
            autoHeight: true,
            width: 500,
            id: 'editCustomDialog',            
            title: _t('Edit Config Property'),
            items: [
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
                },  
                  editConfig,
                {
                    xtype: 'label',
                    width: 300,
                    height: 90,
                    html: pathMsg
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
