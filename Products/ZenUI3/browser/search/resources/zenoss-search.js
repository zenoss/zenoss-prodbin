Ext.onReady(function(){

    new Zenoss.SearchField(
        {
            renderTo: 'searchbox-container',
            black: true,
            id: 'searchbox-query',
            fieldClass: 'searchbox-query',
            name: 'query',
            width: 120
        }
    );


    var ds = new Ext.data.DirectStore({
        directFn: Zenoss.remote.SearchRouter.getLiveResults,
        root: 'results',
        idProperty: 'url',
        fields: [ 'url', 'category', 'excerpt', 'icon' ]
    });

    // Custom rendering Template
    var resultTpl = new Ext.XTemplate(
        '<tpl for=".">',
        '<table class="search-result"><tr class="x-combo-list-item">',
        '<th><tpl if="values.category && (xindex == 1 || parent[xindex - 2].category != values.category)">{category}</tpl></th>',
        '<td class="icon"><img src="{icon}"/></td>',
        '<td class="excerpt">{excerpt}</td>',
        '</tpl>'
    );

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
                    window.location =
                        String.format('{0}', record.data.url);
                }
            }
        }
    });
});
