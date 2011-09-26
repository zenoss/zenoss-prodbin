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
        ds = Ext.create('Zenoss.NonPaginatedStore', {
            directFn: Zenoss.remote.SearchRouter.getLiveResults,
            fields: [
                {name: 'url'},
                {name: 'content'},
                {name: 'popout'},
                {name: 'category'}
            ],
            root: 'results'
        }),
        // Custom rendering Template
        resultTpl = new Ext.XTemplate(
            '<tpl for=".">',
            '<table class="search-result"><tr class="x-combo-list-item">',
            '<th><tpl if="values.category && (xindex == 1 || parent[xindex - 2].category != values.category)"',
            '>{category}</tpl></th>',
            '<td colspan="2" class="x-boundlist-item">{content}</td>',
            '</tpl>'),
        searchfield = new Zenoss.SearchField({
            black: true,
            id: 'searchbox-query',
            fieldClass: 'searchbox-query',
            name: 'query',
            width: 150,
            renderTo: 'searchbox-container'
        });



    /**
     * @class Zenoss.search.SavedSearchModel
     * @extends Ext.data.Model
     * Field definitions for saved search
     **/
    Ext.define('Zenoss.search.SavedSearchModel',  {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: [
            {name: 'id'},
            {name: 'name'},
            {name: 'uid'},
            {name: 'createor'},
            {name: 'query'}
        ]
    });

    /**
     * @class Zenoss.search.SavedSearchStore
     * @extend Zenoss.NonPaginatedStore
     * Direct store for loading saved searches
     */
    Ext.define("Zenoss.search.SavedSearchStore", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.search.SavedSearchModel',
                directFn: Zenoss.remote.SearchRouter.getAllSavedSearches,
                root: 'data'

            });
            this.callParent(arguments);
        }
    });

    Zenoss.env.search = new Ext.form.ComboBox({
        store: ds,
        typeAhead: false,
        loadingText: _t('Searching..'),
        triggerAction: 'all',
        width: 120,
        maxWidth: 375,
        pageSize: 0,
        // delay all requests by one second
        delayQuery: 1000,
        minChars: 3,
        hideTrigger: false,
        applyTo: searchfield.getEl(),
        queryMode: 'remote',
        listClass: 'search-result',
        resizable: true,
        matchFieldWidth: false,
        listConfig: {
            emptyText: _t('No Results'),
            minWidth: 375,
            tpl: resultTpl
        },
        /**
         * Override the align picker method to make sure that
         * the width of the picker is 375, which is different than the width of the input
         **/
        alignPicker: function() {
            var me = this,
            picker;

            if (me.isExpanded) {
                picker = me.getPicker();

                // Auto the height (it will be constrained by min and max width) unless there are no records to display.
                picker.setSize(375, picker.store && picker.store.getCount() ? null : 0);

                if (picker.isFloating()) {
                    me.doAlign();
                }
            }
        },
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
                id: 'saved-search',
                height: 21,
                listClass: 'saved-search-item',
                displayField: 'name',
                applyTo: hiddeninput,
                store: Ext.create('Zenoss.search.SavedSearchStore', {
                    listeners: {
                        beforeload: function() {
                            this.setBaseParam('addManageSavedSearch', true);
                        },
                        load: function(){
                            Ext.fly("manage-search-link").parent().insertSibling({tag:"br"});
                        },
                        scope: this.savedSearchCombo
                    }
                }),
                // position the combobox drop down below the search input
                pickerOffset: [0, -30],
                listeners: {
                    select: function(box, records){
                        var record = records[0];
                        // magic string that means the user wishes to manage
                        // their saved searches
                        if (record.get("id") == 'manage_saved_search') {
                            var decodedUrl = Ext.urlDecode(location.search.substring(1, location.search.length)),
                                searchId = decodedUrl.search,
                                win = Ext.create('Zenoss.search.ManageSavedSearchDialog', {
                                    xtype:'managesavedsearchdialog',
                                    id:'manageSavedSearchesDialog',
                                    searchId: searchId
                                });
                            win.show();
                        }else {
                            // otherwise go to the selected search results page
                            window.location = String.format('/zport/dmd/search?search={0}', record.get("id"));

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
                this.mon(this.triggerEl, 'click', triggerclick, combo, {preventDefault:true});

                this.triggerEl.addClsOnOver('x-form-trigger-over ' + this.triggerClass);
                this.triggerEl.addClsOnClick('x-form-trigger-click ' + this.triggerClass);
            }, this);
            this.initSavedSearch();
        },
        listeners: {
            select: function(box,records){
                var record = records[0];
                if (record.get('url') !== '') {
                    // IE only supports these window names: _blank _media _parent _search _self _top
                    var windowname = Ext.isIE ? '_blank' : record.data.url;
                    if (record.get('popout')) {
                        window.open(String.format('{0}',record.data.url),
                                    windowname, 'status=1,width=600,height=500');
                    }
                    else {
                        window.location =
                            String.format('{0}', record.data.url);
                    }
                }
            }
        }
    });



    Ext.define("Zenoss.search.ManageSavedSearchDialog", {
        extend:"Ext.Window",
        alias: ['managesavedsearchdialog'],
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
                    selModel: new Zenoss.SingleRowSelectionModel({
                        singleSelect: true,
                        listeners: {
                            rowselect: function(grid, rowIndex, row) {

                                // do not allow them to delete the one they are editing
                                if (row.get("name") != searchId) {
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
                    store: Ext.create('Zenoss.search.SavedSearchStore', {
                        autoLoad:true
                    })
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
            this.callParent(arguments);
        },
        reloadGrid: function() {
            this.savedSearchGrid.getStore().load();
        }
    });

    ds.on("load", function(){
        Zenoss.env.search.select(0);
    });

}
});
