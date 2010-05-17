Ext.onReady(function(){

// If there is no searchbox-container, then we will not attempt to render
// the searchbox.  No context windows such as the event detail popout have
// no searchbox-container
if ( Ext.get('searchbox-container') === null ) {
            return;
}else {
    var combo;
    Ext.create({
            black: true,
            id: 'searchbox-query',
            fieldClass: 'searchbox-query',
            name: 'query',
            width: 150,
            xtype: 'searchfield',
            renderTo: 'searchbox-container'
        });


    Ext.create({           
            xtype: 'button',
            id: 'saved-searches-button',
            renderTo: 'searchbox-container',
                   text: _t('Saved'), // TODO: Get an Icon for this,
            handler: function () {
                // everytime we press this button, we want
                // to go back to the server to get fresh data
                delete combo.lastQuery;
            }
        }
    );
    
    var ds = new Ext.data.DirectStore({
        directFn: Zenoss.remote.SearchRouter.getLiveResults,
        root: 'results',
        idProperty: 'url',
        fields: [ 'url', 'content', 'popout', 'category' ]
    }),

    // Custom rendering Template
    resultTpl = new Ext.XTemplate(
        '<tpl for=".">',
        '<table class="search-result"><tr class="x-combo-list-item">',
        '<th><tpl if="values.category && (xindex == 1 || parent[xindex - 2].category != values.category)">{category}</tpl></th>',
        '<td colspan="2">{content}</td>',
        '</tpl>' );
    
    Zenoss.env.search = new Ext.form.ComboBox({
        store: ds,
        typeAhead: false,
        loadingText: _t('Searching..'),
        triggerAction: 'all',
        width: 120,
        pageSize: 0,
        minChars: 3,
        hideTrigger: true,
        tpl: resultTpl,
        applyTo: Ext.get('searchbox-query'),
        listClass: 'search-result',
        listWidth: 375,
        listeners: {
            select: function(box,record){
                if (record.get('url') != '') {
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
    combo = new Ext.form.ComboBox({
        editable: false,
        triggerAction: 'all',
        triggerClass: 'no-trigger-icon',
        triggerConfig: {
            tag: "img",
            src: Ext.BLANK_IMAGE_URL,
            cls: "no-trigger-icon" + this.triggerClass
        },
        applyTo: Ext.get('saved-searches-button'),
        valueField: 'id',
        displayField: 'name',
        store: {
            xtype: 'directstore',
            ref:'store',
            directFn: Zenoss.remote.SearchRouter.getAllSavedSearches,
            fields: ['id', 'name'],
            root: 'data'
        },
        listeners: {
            select: function(box, record){
                // go to the selected search results page
                window.location = String.format('/zport/dmd/search?search={0}', record.id);
            }
        }

    });
  }
});
