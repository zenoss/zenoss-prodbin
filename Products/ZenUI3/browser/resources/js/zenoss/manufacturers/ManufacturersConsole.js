/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

Ext.onReady(function(){

    Ext.ns('Zenoss.manufacturers');
    // page level variables
    var REMOTE = Zenoss.remote.ManufacturersRouter;

    function getOrganizerFields(mode) {
        var items = [
            {
                xtype: 'fieldset',
                margin: '0 15px 20px 0',
                items:[
                    {
                        xtype: 'panel',
                        layout: 'hbox',
                        items: [
                            {
                                xtype: 'textfield',
                                name: 'oldname',
                                hidden: true
                            },{
                                xtype: 'textfield',
                                name: 'name',
                                fieldLabel: _t('Manufacturer Name'),
                                margin: '0 10px 0 0',
                                width:320,
                                regex: Zenoss.env.textMasks.allowedDescText,
                                regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                                allowBlank: false
                            },{
                                xtype: 'textfield',
                                name: 'phone',
                                fieldLabel: _t('Phone'),
                                margin: '0 10px 0 0',
                                width:120,
                                regex: /^\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}$|^$/,
                                regexText: "Numbers, - . () only",
                                allowBlank: true
                            },{
                                xtype: 'textfield',
                                name: 'URL',
                                fieldLabel: _t('URL'),
                                width:420
                            }
                        ]
                    }
                ]
            },{
                xtype: 'fieldset',
                margin: '0 15px 20px 0',
                items: [
                    {
                        xtype: 'textfield',
                        name: 'address1',
                        fieldLabel: _t('Address 1'),
                        margin: '0 0 10px 0',
                        width:400
                    },{
                        xtype: 'textfield',
                        name: 'address2',
                        fieldLabel: _t('Address 2'),
                        width:400
                    }
                ]
            },{
                xtype: 'fieldset',
                margin: '0 15px 20px 0',
                items:[
                    {
                        xtype: 'panel',
                        layout: 'hbox',
                        items: [
                            {
                                xtype: 'textfield',
                                name: 'city',
                                fieldLabel: _t('City'),
                                margin: '0 10px 0 0',
                                width:320,
                                regex: Zenoss.env.textMasks.allowedDescText,
                                regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                                allowBlank: true
                            },{
                                xtype: 'combo',
                                name: 'state',
                                margin: '0 10px 0 0',
                                store: Ext.create('Ext.data.Store', {
                                    model: 'Zenoss.manufacturers.state',
                                    data: Zenoss.util.states
                                }),
                                fieldLabel: _t('State/Province'),
                                displayField: 'name',
                                width: 150,
                                queryMode: 'local',
                                typeAhead: true
                            },{
                                xtype: 'textfield',
                                name: 'zip',
                                fieldLabel: _t('Postal/Zip Code'),
                                margin: '0 10px 0 0',
                                width:180,
                                regex: Zenoss.env.textMasks.allowedDescText,
                                regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                                allowBlank: true
                            },{
                                xtype: 'textfield',
                                name: 'country',
                                fieldLabel: _t('Country'),
                                width:250,
                                regex: Zenoss.env.textMasks.allowedDescText,
                                regexText: Zenoss.env.textMasks.allowedDescTextFeedback
                            }
                        ]
                    }
                ]
            },{
                xtype: 'panel',
                items: [
                    {
                        xtype: 'minieditor',
                        title: _t('Regexes (matches for incoming products to manufacturer)'),
                        name: 'regexes_panel',
                        margin: '0 15 0 0'
                    }
                ]
            }

        ];

        var rootId = mantree.root.id;// sometimes the page loads with nothing selected and throws error. Need a default.
        if(getSelectedManufacturer()) rootId = getSelectedManufacturer().getOwnerTree().root.id;
        return items;
    }

    Ext.define('Zenoss.manufacturers.state', {
        extend: 'Ext.data.Model',
        fields: [
            {type: 'string', name: 'abbr'},
            {type: 'string', name: 'name'},
            {type: 'string', name: 'slogan'}
        ]
    });

    Zenoss.manufacturers.callEditManufacturerDialog = function(name, uid){
        var manufacturersDialog = new Zenoss.SmartFormDialog({
            title: _t('Edit Manufacturer'),
            formId: 'editManufacturerDialog',
            height:Ext.getBody().getViewSize().height,
            width:Ext.getBody().getViewSize().width*0.8, //80%
            autoDestroy: true,
            items: getOrganizerFields()
        });
        REMOTE.getManufacturerData({'uid':uid},function(response){
            if(response.success){
                var data = response.data[0];
                var fields = Ext.getCmp('editManufacturerDialog').getForm().getFields();
                for(var i = 0; i < fields.length; i++){
                    var record = fields.items[i];
                    switch(record.name){
                        case "oldname"  : record.setValue(data.id);  break;
                        case "name"     : record.setValue(name);  break;
                        case "URL"      : record.setValue(data.url);  break;
                        case "phone"    : record.setValue(data.phone);  break;
                        case "address1" : record.setValue(data.address1);  break;
                        case "address2" : record.setValue(data.address2);  break;
                        case "city"     : record.setValue(data.city); break;
                        case "state"    : record.setValue(data.state);  break;
                        case "zip"      : record.setValue(data.zip);  break;
                        case "country"  : record.setValue(data.country);  break;
                        case "regexes_panel"  : try{record.setValue(data.regexes);}catch(e){/*swallow codemirror split bug */}; break;
                    }
                }
            }
            manufacturersDialog.setSubmitHandler(function(e) {
                 var params = {
                    'oldname'   :e.oldname,
                    'name'      :e.name,
                    'phone'     :e.phone,
                    'URL'       :e.URL,
                    'address1'  :e.address1,
                    'address2'  :e.address2,
                    'city'      :e.city,
                    'zip'       :e.zip,
                    'state'     :(e.state || ""),
                    'country'   :e.country,
                    'regexes'   :e.regexes_panel
                  };
                REMOTE.editManufacturer({'params':params}, function(response){
                    if(response.success){
                        var tree = Ext.getCmp('manufacturers_tree');
                        tree.refresh();
                        tree.getStore().on('load', function(s){
                            var node = tree.getRootNode().findChild("uid", "/zport/dmd/Manufacturers/"+e.name, true);
                            tree.getView().select(node);
                        }, this, {single:true});
                        Zenoss.message.info(_t(e.name)+' added');
                    }
                });
            });
        });
        manufacturersDialog.show();
    };

    function getSelectedManufacturer(){
        return Ext.getCmp('manufacturers_tree').getSelectionModel().getSelectedNode();
    }

    function initializeTreeDrop(tree) {
        // fired when the user actually drops a node
        tree.getView().on('beforedrop', function(element, e, targetnode, location, dropfunc, empty) {
            var grid = Ext.getCmp('productsgrid_id'),
                moveFrom = e.records[0].data.uid.split('/products/')[0],
                moveTarget = targetnode.data.uid,
                ids =[],
                me = this,
                message = "";
            for(var i=0; e.records.length > i; i++){
                ids.push(e.records[i].get("id"));
            }

            message = _t("Are you sure you want to move these product(s) to a new manufacturer?");

            new Zenoss.dialog.SimpleMessageDialog({
                message: message,
                title: _t('Move Item'),
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('OK'),
                    handler: function() {
                        var params = {
                            'moveFrom': moveFrom,
                            'moveTarget': moveTarget,
                            'ids': ids
                        };
                        REMOTE.moveProduct(params, function(response){
                            if(response.success) {
                                var tree = Ext.getCmp('manufacturers_tree');
                                tree.refresh();
                                tree.getStore().on('load', function(s){
                                    var nodeId = targetnode.data.uid;
                                    var node = tree.getRootNode().findChild("uid", nodeId, true);
                                    tree.getView().select(node);
                                }, this, {single:true});
                            }
                        }, me);
                    }
                }, {
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
            }).show();
            // if we return true a dummy node will be appended to the tree
            return false;
        }, tree);
    }

    var mantree = {
        xtype: 'HierarchyTreePanel',
        loadMask: true,
        id: 'manufacturers_tree',
        searchField: true,
        directFn: REMOTE.returnTree,
        allowOrganizerMove: false,
        stateful: true,
        stateId: 'man_tree',
        ddAppendOnly: true,
        selectByToken: function(nodeId){
            var pieces = nodeId.split(":"),
                me = this, mId;
            if (pieces.length > 0) {
                mId = Ext.Object.fromQueryString("uid=" + pieces[0]).uid;
                this.store.on('load', function(){
                    var node = me.getRootNode().findChild("id", mId, true);
                    me.getView().select(node);
                }, this, {single:true});

                // see if we are deeplinking to a product class
                if (pieces.length === 2) {
                    var productClassId = pieces[1];
                    // when the product class grid is ready attach a load
                    // listener so we can select the product class
                    Zenoss.util.callWhenReady('productsgrid_id', function() {
                        var grid = Ext.getCmp('productsgrid_id');
                        grid.getStore().on('load', function() {
                            grid.selectByToken(productClassId);
                        }, grid, {single: true});
                    });
                }
            }
        },
        root: {
            id: '.zport.dmd.Manufacturers',
            uid: 'zport/dmd/Manufacturers',
            text: 'Manufacturers'
        },
        ddGroup: 'mangriddd',
        getContentPanel: function(){
            return Ext.getCmp('man_center_panel').items.items[Ext.getCmp('nav_combo').getSelectedIndex()];
        },
        columns:[
                {
                    xtype:'treecolumn',
                    flex:1,
                    dataIndex:'text',
                    renderer:function (value, l, n) {
                        if(Ext.isString(value)){
                            return value;
                        }
                        return Ext.String.format("<span class='subNode'>{0}</span>", value.text);
                    }
                }
            ],
        selModel: Ext.create('Zenoss.TreeSelectionModel',{
            tree: 'manufacturers_tree',
            listeners: {
                selectionchange: function(sm, newnodes, oldnode){
                    if (newnodes.length) {
                        var newnode = newnodes[0];
                        var uid = newnode.data.uid;
                        var data = newnode.data.text;
                        var contentPanel = mantree.getContentPanel();
                        var phone = "", url = "";
                        contentPanel.setContext(uid);

                        if (data.description != "") phone = " - "+data.description;
                        if (data.url != "") url = " - <a href='"+data.url+"'>"+data.url+"</a>";
                        Ext.getCmp("manufacturer_info").setText(
                        data.text + phone + url
                        , false);
                        Ext.getCmp('footer_bar').setContext(uid);
                        Zenoss.env.contextUid = uid;
                        // explicitly set the new security context (to update permissions)
                        Zenoss.Security.setContext(uid);
                    }
                }
            }
        }),
        router: REMOTE,
        nodeName: 'manufacturerNode',
        deleteSelectedNode: function(){
            var node = getSelectedManufacturer();
            REMOTE.deleteManufacturer({'uid':node.data.uid}, function(response){
                if(response.success){
                    var tree = Ext.getCmp('manufacturers_tree');
                    tree.refresh();
                    tree.getStore().on('load', function(s){
                        var node = tree.getRootNode().findChild("index", 0, true);
                        tree.getView().select(node);
                    }, this, {single:true});

                }
            });
        },
        listeners: {
            render: initializeTreeDrop,
            viewready: function(t){
                // fixes 20000px width bug on the targetEl div bug in Ext
                t.ownerCt.ownerCt.searchfield.container.setWidth(t.body.getWidth());
            },
            afterrender: function(tree){
                tree.getView().on('itemdblclick', function(e){
                    var node = getSelectedManufacturer();
                    if (Zenoss.Security.doesNotHavePermission('Manage DMD')) return false;
                    Zenoss.manufacturers.callEditManufacturerDialog(node.data.text.text, node.data.uid);
                });
            }
        }
    };

    var treepanel = {
        xtype: 'HierarchyTreePanelSearch',
        items: [mantree]
    };

    Ext.define("Zenoss.eventmanufacturers.NavigtaionCombo", {
        alias: ['widget.NavCombo'],
        extend: "Ext.form.ComboBox",
        constructor: function(config){
            config = config || {};
            Ext.applyIf(config, {
                id: 'nav_combo',
                width: 240,
                displayField: 'name',
                editable: false,
                typeAhead: false,
                value: _t('Products'),
                listeners:{
                    select: function(combo){
                        var container = Ext.getCmp('man_center_panel');
                        container.layout.setActiveItem(combo.getSelectedIndex());
                        // set the context for the active item:
                        var contentPanel = mantree.getContentPanel();
                        contentPanel.setContext(Zenoss.env.contextUid);
                        Zenoss.Security.setContext(Zenoss.env.contextUid);
                    }
                },
                store:  Ext.create('Ext.data.ArrayStore', {
                     model: 'Zenoss.model.Name',
                     data: [[
                        _t('Products')
                    ],[
                        _t('Configuration Properties')
                    ]]
                 })
            });
            this.callParent(arguments);
        }

    });


    Ext.getCmp('center_panel').add({
        id: 'center_panel_container',
        layout: 'border',
        defaults: {
            split: true
        },
        items: [{
            xtype: 'panel',
            id: 'master_panel',
            cls: 'x-zenoss-master-panel',
            region: 'west',
            width: 275,
            maxWidth: 275,
            layout: 'fit',
            items: [
                treepanel
            ]
        },{
            xtype: 'contextcardpanel',
            id: 'man_center_panel',
            region: 'center',
            activeItem: 0,
            tbar: {
                cls: 'largetoolbar',
                height: 38,
                items: [
                    {
                        xtype: 'NavCombo'
                    },{
                        xtype: 'label',
                        id: 'manufacturer_info'
                    }
                ]
            },
            items: [
                {
                    xtype: 'productsgrid',
                    id: 'productsgrid_id',
                    viewConfig: {
                        plugins: {
                            ptype: 'gridviewdragdrop',
                            dragGroup: 'mangriddd'
                        }
                    }
                },{
                    xtype: 'configpropertypanel',
                    id: 'configpanel_id'
                }

            ]
        }]
    });





    // Footer bar for the main manufacturers page.
    // This extends Zenoss.footerHelper in FooterBar.js
    /* ------------------------------------------------------------------------------ FOOTER --------------------------------- */
    var footerBar = Ext.getCmp('footer_bar');
        Zenoss.footerHelper(
        '',
        footerBar,
        {
            hasOrganizers: false,
            addToZenPack: false,
            // the message to display when user hits the [-] delete button.
            onGetDeleteMessage: function (itemName) {
                var node = getSelectedManufacturer(),
                    tree = node.getOwnerTree(),
                    rootId = tree.getRootNode().data.id,

                    msg = _t('Are you sure you want to delete the {0} {1}? <br/>There is <strong>no</strong> undo.');
                if (rootId==mantree.root.id) {
                    msg = [msg, '<br/><br/><strong>',
                           _t('WARNING'), '</strong>:',
                           _t(' This will also delete all manufacturers in this {0}.'),
                           '<br/>'].join('');
                }
                msg = "";
                return Ext.String.format(msg, itemName.toLowerCase(), '/'+node.data.path);
            },
            onGetItemName: function() {
                // runs when adding new organizer
                // runs 2x when hitting delete
                var node = getSelectedManufacturer();
                if ( node ) {
                    var tree = node.getOwnerTree();
                    return tree.nodeName;
                }
            },
            customAddDialog: {
                title: _t('Add New Manufacturer'),
                id: 'addNewManufacturerDialog',
                height:Ext.getBody().getViewSize().height,
                width:Ext.getBody().getViewSize().width*0.8,
                submitHandler: function(e){
                    var params = {
                                    'name'      :e.name,
                                    'phone'     :e.phone,
                                    'URL'       :e.URL,
                                    'address1'  :e.address1,
                                    'address2'  :e.address2,
                                    'city'      :e.city,
                                    'zip'       :e.zip,
                                    'state'     :(e.state || ""),
                                    'country'   :e.country,
                                    'regexes'   :e.regexes_panel
                                  }
                    REMOTE.addManufacturer({'id':e.name}, function(response){
                            if(response.success){
                                REMOTE.editManufacturer({'params':params}, function(response){
                                    if(response.success){
                                        var tree = Ext.getCmp('manufacturers_tree');
                                        tree.refresh();
                                        tree.getStore().on('load', function(s){
                                            var node = tree.getRootNode().findChild("uid", "/zport/dmd/Manufacturers/"+e.name, true);
                                            tree.getView().select(node);
                                        }, this, {single:true});
                                    }
                                });
                            }
                    });
                },
                items: getOrganizerFields()
            },
            buttonContextMenu: {
            xtype: 'ContextConfigureMenu',
                onSetContext: function(uid) {
                    Zenoss.env.PARENT_CONTEXT = uid;
                },
                onGetMenuItems: function(uid) {
                    var menuItems = [];
                    menuItems.push({
                        xtype: 'menuitem',
                        text: _t('Edit'),
                        hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        handler: function() {
                            var node = getSelectedManufacturer();
                            var uid = node.data.uid;
                            Zenoss.manufacturers.callEditManufacturerDialog(node.data.text.text, uid);
                        }
                    });
                    return menuItems;
                }
            }
        }
    );

    footerBar.on('buttonClick', function(actionName, id, values) {
        var tree = Ext.getCmp('manufacturers_tree');
        switch (actionName) {
            case 'addManufacturer': tree.addChildNode(Ext.apply(values, {type: 'organizer'})); break;
            case 'addOrganizer': throw new Ext.Error('Not Implemented');
            case 'delete': tree.deleteSelectedNode(); break;
            default: break;
        }
    });


}); // Ext. OnReady
