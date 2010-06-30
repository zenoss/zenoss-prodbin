Ext.onReady(function(){

// If there is no searchbox-container, then we will not attempt to render
// the searchbox.  No context windows such as the event detail popout have
// no searchbox-container

if ( Ext.get('searchbox-container') === null ) {
            return;
}else {
    
    var combo,
        router = Zenoss.remote.SearchRouter,
        ManageSavedSearchDialog,     
        ds = new Ext.data.DirectStore({
            directFn: Zenoss.remote.SearchRouter.getLiveResults,
            root: 'results',
            idProperty: 'url',
            fields: [ 'url', 'content', 'popout', 'category' ]
        }),
        // Custom rendering Template
        resultTpl = new Ext.XTemplate(
            '<tpl for=".">',
            '<table class="search-result"><tr class="x-combo-list-item">',
            '<th><tpl if="values.category && (xindex == 1 || parent[xindex - 2].category != values.category)"',
            '>{category}</tpl></th>',
            '<td colspan="2">{content}</td>',
            '</tpl>'),
        searchfield = new Zenoss.SearchField({
            black: true,
            id: 'searchbox-query',
            fieldClass: 'searchbox-query',
            name: 'query',
            width: 150,
            renderTo: 'searchbox-container'
        });



    Zenoss.env.search = new Ext.form.ComboBox({
        store: ds,
        typeAhead: false,
        loadingText: _t('Searching..'),
        //triggerAction: 'all',
        width: 120,
        pageSize: 0,
        minChars: 3,
        hideTrigger: false,
        tpl: resultTpl,
        applyTo: searchfield.getEl(),
        listClass: 'search-result',
        listWidth: 375,
        initSavedSearch: function() {
            // Create a dummy target for the saved search combo
            var container = Ext.get(Ext.select('.searchfield-black-mc').elements[0]),
                hiddeninput = container.createChild({tag:'input', style:{
                    position: 'absolute',
                    visibility: 'hidden',
                    width: 0
                }});
            this.savedSearchCombo = new Ext.form.ComboBox({
                editable: false,
                triggerAction: 'all',
                hideTrigger: true,
                height: 21,
                listClass: 'saved-search-item',
                valueField: 'id',
                listWidth: 200,
                displayField: 'name',
                applyTo: hiddeninput,
                store: {
                    xtype: 'directstore',
                    ref:'store',
                    directFn: Zenoss.remote.SearchRouter.getAllSavedSearches,
                    fields: ['id', 'name'],
                    root: 'data',
                    baseParams: {
                        'addManageSavedSearch': true
                    }
                },
                listeners: {
                    select: function(box, record){
                        // magic string that means the user wishes to manage
                        // their saved searches
                        if (record.id == 'manage_saved_search') {
                            var decodedUrl = Ext.urlDecode(location.search.substring(1, location.search.length)),
                                searchId = decodedUrl.search,
                                win = Ext.create({
                                    xtype:'managesavedsearchdialog',
                                    id:'manageSavedSearchesDialog',
                                    searchId: searchId
                                });
                            win.show();
                        }else {
                            // otherwise go to the selected search results page
                            window.location = String.format('/zport/dmd/search?search={0}', record.id);
                        }
                    }
                }

            });
            this.fireEvent('triggerready');
        },
        initTrigger: function() {
            this.on('triggerready', function(){
                var combo = this.savedSearchCombo,
                    triggerclick = combo.onTriggerClick.createInterceptor(function(){
                        delete combo.lastQuery;
                    }, this);
                this.mon(this.trigger, 'click', triggerclick, combo, {preventDefault:true});
                this.trigger.addClassOnOver('x-form-trigger-over ' + this.triggerClass);
                this.trigger.addClassOnClick('x-form-trigger-click ' + this.triggerClass);
            }, this);
            this.initSavedSearch();
        },
        listeners: {
            select: function(box,record){
                if (record.get('url') !== '') {
                    if (record.get('popout')) {
                        window.open( String.format('{0}',record.data.url ),
                                     record.data.url,
                                     'status=1,width=600,height=500' );
                    }
                    else {
                        window.location =
                            String.format('{0}', record.data.url);
                    }
                }
            }
        }
    });

    // drop down box of existing saved searches

    ManageSavedSearchDialog = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            var searchId = config.searchId,
                me = this;
            Ext.apply(config, {
                title: _t('Manage Saved Searches'),
                layout: 'form',
                autoHeight: true,
                width: 475,
                modal: true,
                listeners: {
                    show: function() {
                        this.reloadGrid();
                        this.savedSearchGrid.deleteButton.disable();
                    },
                    scope: this
                },
                items: [{
                    ref: 'savedSearchGrid',
                    xtype: 'grid',
                    stripeRows: true,
                    autoScroll: true,
                    border: false,
                    autoHeight: true,
                    tbar: [{
                        xtype: 'button',
                        ref: '../deleteButton',
                        iconCls: 'delete',
                        tooltip: _t('Delete the selected saved search'),
                        disabled: true,
                        handler: function(button, e) {
                            var grid = button.refOwner,
                            selectedRow = grid.getSelectionModel().getSelected(),
                            params = {
                                searchName: selectedRow.data.name
                            };

                            button.disable();
                            router.removeSavedSearch(params, me.reloadGrid.createDelegate(me));
                        }
                    }],
                    selModel: new Ext.grid.RowSelectionModel({
                        singleSelect: true,
                        listeners: {
                            rowselect: function(grid, rowIndex, row) {
                                // do not allow them to delete the one they are editing
                                if (row.data.name != searchId) {
                                    me.savedSearchGrid.deleteButton.enable();
                                }
                            },
                            rowdeselect: function() {
                                me.savedSearchGrid.deleteButton.disable();
                            }
                        }
                    }),
                    columns: [
                        {dataIndex: 'name', header: _t('Name'), width: 150},
                        {dataIndex: 'query', header: _t('Query'), width: 150},
                        {dataIndex: 'creator', header: _t('Created By'), width: 150}
                    ],
                    store: {
                        xtype: 'directstore',
                        directFn: router.getAllSavedSearches,
                        idProperty: 'uid',
                        root: 'data',
                        fields: ['uid', 'name', 'creator', 'query']
                    }
                }],

                buttons: [{
                    xtype: 'button',
                    text: _t('Close'),
                    handler: function() {
                        me.hide();
                        me.destroy();
                    }
                }]
            });
            ManageSavedSearchDialog.superclass.constructor.apply(this, arguments);
        },
        reloadGrid: function() {
            this.savedSearchGrid.getStore().load();
        }
    });
    Ext.reg('managesavedsearchdialog', ManageSavedSearchDialog);
    
    ds.on("load", function(){
        Zenoss.env.search.select(0);
    });
    
}
});
