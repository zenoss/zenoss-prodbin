Ext.onReady(function(){

// If there is no searchbox-container, then we will not attempt to render
// the searchbox.  No context windows such as the event detail popout have
// no searchbox-container
if ( Ext.get('searchbox-container') == null ) {
            return
            }
else {
    new Zenoss.SearchField(
        {
            renderTo: 'searchbox-container',
            black: true,
            id: 'searchbox-query',
            fieldClass: 'searchbox-query',
            name: 'query',
            width: 150
        }
    );


    var ds = new Ext.data.DirectStore({
        directFn: Zenoss.remote.SearchRouter.getLiveResults,
        root: 'results',
        idProperty: 'url',
        fields: [ 'url', 'content', 'popout', 'category' ]
    });

    // Custom rendering Template
    var resultTpl = new Ext.XTemplate(
        '<tpl for=".">',
        '<table class="search-result"><tr class="x-combo-list-item">',
        '<th><tpl if="values.category && (xindex == 1 || parent[xindex - 2].category != values.category)">{category}</tpl></th>',
        '<td colspan="2">{content}</td>',
        '</tpl>' );

Zenoss.env.search = new Ext.form.ComboBox({
        store: ds,
        typeAhead: false,
        loadingText: 'Searching..',
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
  }
});
