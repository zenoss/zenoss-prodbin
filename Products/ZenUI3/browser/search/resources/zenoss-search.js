Ext.onReady(function () {

// If there is no searchbox-container, then we will not attempt to render
// the searchbox.  No context windows such as the event detail popout have
// no searchbox-container

    if (!Ext.get('searchbox-container')) return;
        /**
         * So we do indeed want the search.
         * But we almost want two different searches:
         * 1.  Free form text entry search for anything out there.
         * 2.  Drop down listing of saved searches.
         *
         * In the ExtJS land, both of these would be served by
         * a ComboBox.  So we would kinda want two combo boxes
         * to be melded into one.  To accomplish this, we will
         * have one combo box and just swap out the Store and the display
         * for the picker  when the user does stuff.
         */

        var router = Zenoss.remote.SearchRouter;

        // Create two variables to hold the store ids
        var storedSearchesDataStoreID = "storedSearchesDataStoreID";
        var freeSearchDataStoreID = "freeSearchDataStoreID";

        // Custom rendering Template for the Free Search Results
        // this defines the way the picker (drop down box) will look
        var resultTpl = new Ext.XTemplate(
            '<tpl for=".">',
            '<tpl if="isSavedResult">',
                '<div class="x-boundlist-item">{name}</div>',
            '<tpl else>',
                '<table class="search-result"><tr class="x-combo-list-item">',
                '<th><tpl if="values.category && (xindex == 1 || parent[xindex - 2].category != values.category)"',
                '>{category}</tpl></th>',
                '<td colspan="2" class="x-boundlist-item">{content}</td>',
            '</tpl>',
            '</tpl>');

        /**
         * @class Zenoss.search.FreeSearchModel
         * @extends Ext.data.Model
         * Field definitions for free search
         **/
        Ext.define('Zenoss.search.FreeSearchModel', {
            extend:'Ext.data.Model',
            idProperty:'url',
            fields:[
                {name:'url'},
                {name:'id'},
                {name:'name'},
                {name:'content'},
                {name:'popout'},
                {name:'category'},
                {name:'isSavedResult', type: 'boolean', convert: function(val, record) {
                    return !!record.get('id');
                }}
            ]
        });

        // Create the Store for the Free Search
        var freeSearchDataStore = Ext.create('Zenoss.NonPaginatedStore', {
            storeId: freeSearchDataStoreID,
            directFn: router.getLiveResults,
            model: 'Zenoss.search.FreeSearchModel',
            root: 'results',
            listeners: {
                beforeload: {
                    fn: function(store, operation) {
                        // clear store before load to not show previous search result;
                        store.loadData([]);
                        // clear last query in combo to trigger search query for same text;
                        theSearchBox.lastQuery = null;
                        if (!operation.params.query) {
                            // if we click on trigger "query" will be empty this mean that we want to see
                            // stored search results, simply load stored store and load it's data to combo store;
                            theSearchBox.getPicker().setLoading(true);
                            theSearchBox.clearValue();
                            storedSearchesDataStore.load({
                                params: {
                                    'addManageSavedSearch': true
                                },
                                callback: function(records, operation, success) {
                                    store.loadData(records);
                                    theSearchBox.getPicker().setLoading(false);
                                }
                            });
                            return false;
                        }
                        return true;
                    }
                }
            }
        });

        /**
         * @class Zenoss.search.SavedSearchModel
         * @extends Ext.data.Model
         * Field definitions for saved search
         **/
        Ext.define('Zenoss.search.SavedSearchModel', {
            extend:'Ext.data.Model',
            idProperty:'uid',
            fields:[
                {name:'id'},
                {name:'name'},
                {name:'uid'},
                {name:'createor'},
                {name:'query'},
                // default true for liveSearch store we compute this field on store load;
                {name:'isSavedResult', type: 'boolean', defaultValue: true}
            ]
        });

        /**
         * @class Zenoss.search.SavedSearchStore
         * @extend Zenoss.NonPaginatedStore
         * Direct store for loading saved searches
         */
        Ext.define("Zenoss.search.SavedSearchStore", {
            extend:"Zenoss.NonPaginatedStore",
            constructor:function (config) {
                config = config || {};
                Ext.applyIf(config, {
                    model: 'Zenoss.search.SavedSearchModel',
                    directFn: router.getAllSavedSearches,
                    root: 'data'
                });
                this.callParent(arguments);
            }
        });

        // Create the Store for the saved searches
        var storedSearchesDataStore = Ext.create('Zenoss.search.SavedSearchStore', {
            storeId:storedSearchesDataStoreID
        });

        // Create a container with Combo Box and render it to "searchbox-container".
        var searchContainer = new Ext.container.Container({
            width: 160,
            renderTo: 'searchbox-container',
            layout: 'hbox',
            items: [{
                xtype: 'combobox',
                flex: 1,
                store:freeSearchDataStore,
                typeAhead:false,
                triggerAction:'all',
                width:148,
                maxWidth:375,
                fieldCls: 'x-form-field searchbox-query',
                pageSize:0,
                // delay all requests by one second
                delayQuery:1000,
                minChars:3,
                hideTrigger:false,
                queryMode:'remote',
                matchFieldWidth:false,
                displayField:'name',
                valueField:'url',
                listConfig:{
                    cls:'search-result',
                    loadingText:_t('Searching..'),
                    resizable:true,
                    emptyText:_t('No Results'),
                    tpl:resultTpl,
                    minWidth:375
                },
                listeners: {
                    // Fire this off when a selection is made
                    select: function (box, records) {
                        // we are looking at a saved search
                        var record = records[0],
                            id = record.get("id"),
                            url = record.get('url');

                        // open saved search result manager popUp;
                        if (id === 'manage_saved_search') {
                            var decodedUrl = Ext.urlDecode(location.search.substring(1, location.search.length)),
                                win = Ext.create('Zenoss.search.ManageSavedSearchDialog', {
                                    xtype: 'managesavedsearchdialog',
                                    id: 'manageSavedSearchesDialog',
                                    searchId: decodedUrl.search
                                });
                            win.show();
                            // and clear out the typed in search box
                            this.clearValue();
                        } else if (url) {
                            // IE only supports these window names: _blank _media _parent _search _self _top
                            var windowname = Ext.isIE ? '_blank' : url;
                            if (record.get('popout')) {
                                window.open(Ext.String.format('{0}', url),
                                    windowname, 'status=1,width=600,height=500');
                            }
                            else {
                                window.location = Ext.String.format('{0}', url);
                            }
                        } else if (id) {
                            // otherwise go to the selected search results page
                            window.location = Ext.String.format('/zport/dmd/search?search={0}', id);
                        }
                    }
                }
            }]
        }),
        theSearchBox = searchContainer.down('combobox');

        // Now set the combo box to the env
        Zenoss.env.search = theSearchBox;

        // =================================================================================
        // Managed Search floating dialog box.
        Ext.define("Zenoss.search.ManageSavedSearchDialog", {
            extend:"Ext.Window",
            alias:['managesavedsearchdialog'],
            constructor:function (config) {
                config = config || {};
                var searchId = config.searchId,
                    me = this;
                Ext.apply(config, {
                    title:_t('Manage Saved Searches'),
                    layout: 'fit',
                    stateful: false,
                    autoHeight:true,
                    width:460,
                    modal:true,
                    items:[{
                            ref:'savedSearchGrid',
                            xtype:'grid',
                            autoScroll:true,
                            border:false,
                            autoHeight:true,
                            sortableColumns:false,
                            enableColumnHide:false,
                            viewConfig: {
                                striperows: true,
                                style:{cursor: 'pointer'},
                                listeners: {
                                    itemdblclick: function(gridview,rowrecord,rowhtml,rowindex,e) {
                                        window.location = "/zport/dmd/search?search="+rowrecord.data.name;
                                    }
                                }
                            },
                            dockedItems: [{
                                xtype: 'toolbar',
                                dock: 'top',
                                height:30,
                                items: [{
                                        xtype:'button',
                                        ref:'../deleteButton',
                                        disabled: true,
                                        iconCls:'delete',
                                        tooltip:_t('Delete the selected saved search'),
                                        handler:function (button, e) {
                                            var grid = button.refOwner,
                                                selectedRow = grid.getSelectionModel().getSelected(),
                                                params = {
                                                    searchName:selectedRow.data.name
                                                };
                                            router.removeSavedSearch(params, Ext.bind(me.reloadGrid, me));
                                            if(selectedRow.data.name == searchId) window.location = "/zport/dmd/search";
                                    }
                                }]
                            }],
                            selModel:new Zenoss.SingleRowSelectionModel({
                                singleSelect:true
                            }),
                            columns:[
                                {dataIndex:'name', header:_t('Name'), flex: 1},
                                {dataIndex:'query', header:_t('Query'), flex: 1}
                            ],
                            store:Ext.create('Zenoss.search.SavedSearchStore', {
                                autoLoad:true
                            }),
                            listeners: {
                                selectionchange: function(t, selection) {
                                    this.deleteButton.setDisabled(!selection.length);
                                }
                            }
                        }
                    ],

                    buttons:[
                        {
                            xtype:'DialogButton',
                            text:_t('Close'),
                            handler:function () {
                                me.hide();
                                me.destroy();
                            }
                        }
                    ]
                });
                this.callParent(arguments);
            },
            reloadGrid:function () {
                this.savedSearchGrid.getStore().load();
            }
        });
});
