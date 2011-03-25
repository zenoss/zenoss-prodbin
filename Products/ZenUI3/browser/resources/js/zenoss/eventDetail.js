(function(){
    var ns = Ext.ns('Zenoss.eventdetail');
    ns.detail_table_template = ['<table>',
        '<tr><td class="dt">Device:</td>',
            '<td>',
                '<tpl if="device">',
                    '{device_link}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">Component:</td>',
            '<td>',
                '<tpl if="component">',
                    '{component_link}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">Event Class:</td>',
            '<td>',
                '<tpl if="eventClass">',
                    '{eventClass_link}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">Status:</td> <td>{eventState}</td></tr>',
        '<tr><td class="dt">Message:</td> <td><pre>{message}</pre></td></tr>',
    '</table>'];

    ns.fullprop_table_template = ['<table class="proptable">',
        '<tpl for="properties">',
        '<tr class=\'{[xindex % 2 === 0 ? "even" : "odd"]}\'>',
        '<td class="proptable_key">{key}</td>',
        '<td class="proptable_value">{value}</td></tr>',
        '</tpl>',
        '</table>'];
    ns.log_table_template = ['<table>',
    '<tpl for="log">',
    '<tr><td class="time">{0} {1}: </td>',
        '<td class="message">{2}</td></tr>',
    '</tpl>',
    '</table>'];
    // FIXME: Refactor this to be much, much smarter about its own components.
    Zenoss.DetailPanel = Ext.extend(Ext.Panel, {
        isHistory: false,
        constructor: function(config){
            config.onDetailHide = config.onDetailHide || function(){var _x;};
            config.layout = 'border';
            config.border = false;
            config.defaults = {border:false};
            function toggleSection(link) {
                var id = link.id.replace('_title', ''),
                    props = Ext.getCmp(id);
                if (link.showProps)  {
                    props.hide();
                } else {
                    props.show();
                }
                link.showProps = !link.showProps;
            }
            function getToggle(field) {
                var link = Ext.getCmp(field);

            }
            config.items = [{
                id: 'evdetail_hd',
                region: 'north',
                layout: 'border',
                height: 50,
                cls: 'evdetail_hd',
                defaults: {border: false},
                items: [{
                    region: 'west',
                    width: 77,
                    layout: 'hbox',
                    defaults: {border: false},
                    items: [{
                        id: 'severity-icon',
                        cls: 'severity-icon'
                    },{
                        id: 'evdetail-sep',
                        cls: 'evdetail-sep'
                    }]
                },{
                    region: 'center',
                    id: 'evdetail-summary',
                    html: ''
                },{
                    region: 'east',
                    id: 'evdetail-tools',
                    layout: 'hbox',
                    width: 57,
                    defaults: {border: false},
                    items: [{
                        id: 'evdetail-popout',
                        cls: 'evdetail-popout'
                    },{
                        id: 'evdetail_tool_close',
                        cls: 'evdetail_close'
                    }]
                }]
            },{
                id: 'evdetail_bd',
                region: 'center',
                defaults: {
                    frame: false,
                    border: false
                },
                autoScroll: true,
                layout: 'table',
                layoutConfig: {
                    columns: 1,
                    tableAttrs: {
                        style: {
                            width: '90%'
                        }
                    }
                },
                cls: 'evdetail_bd',
                items: [{
                    id: 'evdetail_props',
                    cls: 'evdetail_props',
                    html: ''
                },{ // Event Management
                    id: 'event_management_title',
                    cls: 'show_details',
                    toggleFn:  function() {
                        var link = Ext.getCmp('event_management_title');
                        toggleSection(link);
                    },
                    html: _t('Event Management...')
                },{
                    id: 'event_management',
                    hidden: true,
                    cls: 'full_event_props',
                    html: ''
                },{ // Device State
                    id: 'device_state_title',
                    cls: 'show_details',
                    toggleFn:  function() {
                        var link = Ext.getCmp('device_state_title');
                        toggleSection(link);
                    },
                    html: _t('Device State...')
                },{
                    id: 'device_state',
                    hidden: true,
                    cls: 'full_event_props',
                    html: ''
                },{ // Event Data
                    id: 'event_data_title',
                    cls: 'show_details',
                    toggleFn:  function() {
                        var link = Ext.getCmp('event_data_title');
                        toggleSection(link);
                    },
                    html: _t('Event Data...')
                },{
                    id: 'event_data',
                    hidden: true,
                    cls: 'full_event_props',
                    html: ''
                },{ // Event Details
                    id: 'event_details_title',
                    cls: 'show_details',
                    toggleFn:  function() {
                        var link = Ext.getCmp('event_details_title');
                        toggleSection(link);
                    },
                    hidden: false,
                    html: _t('Event Details...')
                },{
                    id: 'event_details',
                    hidden: true,
                    cls: 'full_event_props',
                    html: ''
                },{
                    id: 'evdetail-log-header',
                    cls: 'evdetail-log-header',
                    hidden: true,
                    html: '<'+'hr/><'+'h2>LOG<'+'/h2>'
                },{
                    xtype: 'form',
                    id: 'log-container',
                    defaults: {border: false},
                    frame: true,
                    layout: 'table',
                    style: {'margin-left':'3em'},
                    hidden: true,
                    labelWidth: 1,
                    items: [{
                        id: 'detail-logform-evid',
                        xtype: 'hidden',
                        name: 'evid'
                    },{
                        style: 'margin:0.75em',
                        width: 300,
                        xtype: 'textfield',
                        name: 'message',
                        hidden: Zenoss.Security.doesNotHavePermission('Manage Events'),
                        id: 'detail-logform-message'
                    },{
                        xtype: 'button',
                        type: 'submit',
                        name: 'add',
                        hidden: Zenoss.Security.doesNotHavePermission('Manage Events'),
                        text: 'Add',
                        handler: function(btn, e){
                            var form = Ext.getCmp('log-container'),
                            vals = form.getForm().getValues(),
                            params = {};
                            Ext.apply(params, vals);
                            Zenoss.remote.EventsRouter.write_log(
                                params,
                                function(provider, response){
                                    Ext.getCmp(
                                        'detail-logform-message').setRawValue('');
                                    Ext.getCmp(config.id).load(
                                        Ext.getCmp(
                                            'detail-logform-evid').getValue());
                                });
                        }
                    }]
                },{
                    id: 'evdetail_log',
                    cls: 'log-content',
                    hidden: true
                }]
            }];
            Zenoss.DetailPanel.superclass.constructor.apply(this, arguments);
        },
        setSummary: function(summary){
            var panel = Ext.getCmp('evdetail-summary');
            if (panel && panel.el){
                panel.el.update(summary);
            }
        },
        setSeverityIcon: function(severity){
            var panel = Ext.getCmp('severity-icon');
            this.clearSeverityIcon();
            panel.addClass(severity);
        },
        clearSeverityIcon: function() {
            var panel = Ext.getCmp('severity-icon');
            Ext.each(Zenoss.env.SEVERITIES,
                     function(sev){
                         sev = sev[1];
                         panel.removeClass(sev.toLowerCase());
                     }
                    );
        },
        createPropertyTable: function(fields, event) {
            var full_prop_template = new
                Ext.XTemplate(ns.fullprop_table_template),
                props = [],
                html;
            Ext.each(fields, function(field){
                if (event[field]){
                    props.push({
                        key: field,
                        value: event[field]
                    });
                }
            });
            html = full_prop_template.apply({
                properties: props
            });
            return html;
        },
        update: function(event) {
            // For the Event Detail Page, set up the page
            // links. This is to make sure they link to the correct place
            // when we go to the new UI


            // device_link
            if (event.device_url) {
                event.device_link = Zenoss.render.default_uid_renderer(
                    event.device_url,
                    event.device_title);
            } else {
                event.device_link = event.device_title;
            }
            // component_link
            if (event.component_url) {
                event.component_link = Zenoss.render.default_uid_renderer(
                    event.component_url,
                    event.component_title);
            }else {
                event.component_link = event.component_title;
            }

            // eventClass_link
            event.eventClass_link = Zenoss.render.EventClass(event.eventClass_url,
                                                             event.eventClass);

            // render the organizers as links
            var organizerFields = ['Systems', 'DeviceGroups', 'DeviceClass', 'Location'];
            Ext.each(organizerFields, function(field){
                if (event[field]) {
                    event[field] = Zenoss.render.LinkFromGridGuidGroup(event[field]);
                }
            });
            var details = {
                properties: event.details
            };
            var top_prop_template = new
            Ext.XTemplate(ns.detail_table_template);
            var full_prop_template = new
            Ext.XTemplate(ns.fullprop_table_template);
            var log_template = new Ext.XTemplate(ns.log_table_template);
            var severity = Zenoss.util.convertSeverity(event.severity),
            html = top_prop_template.applyTemplate(event),
            detailhtml = full_prop_template.applyTemplate(details),
            loghtml = log_template.applyTemplate(event);

            this.setSummary(event.summary);
            this.setSeverityIcon(severity);
                Ext.getCmp('evdetail_props').el.update(html);
            Ext.getCmp('evdetail_log').el.update(loghtml);
            Ext.getCmp('detail-logform-evid').setValue(event.evid);
            // hidden sections
            var event_management_html  = this.createPropertyTable(['summary', 'message',
                                                                   'severity', 'component',
                                                                   'eventClass', 'eventClassKey',
                                                                   'eventKey', 'dedupid', 'evid',
                                                                   'eventClassMapping', 'eventState',
                                                                   'eventGroup', 'priority',
                                                                   'facility', 'ntevid',
                                                                   'agent'], event);
            var device_state_html = this.createPropertyTable(['device', 'ipAddress', 'prodState',
                                                              'monitor', 'DevicePriority', 'Systems', 'DeviceGroups',
                                                              'Location', 'DeviceClass'], event);

            var event_meta_data_html = this.createPropertyTable(['firstTime', 'stateChange', 'lastTime', 'count',
                                                                 'owner', 'clearid'], event);
            Ext.getCmp('event_management').el.update(event_management_html);
            Ext.getCmp('device_state').el.update(device_state_html);
            Ext.getCmp('event_data').el.update(event_meta_data_html);
            Ext.getCmp('event_details').el.update(detailhtml);
        },
        wipe: function(){
            this.clearSeverityIcon();
            this.setSummary('');
            Ext.getCmp('evdetail-log-header').hide();
            Ext.getCmp('evdetail_log').hide();
            Ext.getCmp('evdetail_props').hide();
            Ext.getCmp('log-container').hide();
        },
        show: function(){
            Ext.getCmp('evdetail-log-header').show();
            Ext.getCmp('evdetail_log').show();
            Ext.getCmp('evdetail_props').show();
            if (this.isPropsVisible) {
                this.isPropsVisible = false;
                this.showProps();
            }
            Ext.getCmp('log-container').show();
        },
        isPropsVisible: false,
        showProps: function(){
            var fields = ['event_management',
                          'device_state',
                          'event_data',
                          'event_details'
                         ];
            if (this.isPropsVisible){
                Ext.each(fields, function(field){
                    Ext.getCmp(field).hide();
                    Ext.getCmp(field + '_title').hide();
                });
                this.isPropsVisible = false;
            } else {
                Ext.each(fields, function(field){
                    Ext.getCmp(field).show();
                    Ext.getCmp(field + '_title').show();
                });
                this.isPropsVisible = true;
            }
        },
        popout: function(){
            var evid = Ext.getCmp('detail-logform-evid').getValue(),
                url = this.isHistory ? 'viewHistoryDetail' : 'viewDetail';
            url = url +'?evid='+evid;
            window.open(url, evid.replace(/-/g,'_'),
                        "status=1,width=600,height=500");
        },
        bind: function(){
            var btn = Ext.getCmp('evdetail_tool_close').getEl(),
                pop = Ext.getCmp('evdetail-popout').getEl(),
                fields = ['event_management_title', 'device_state_title',
                           'event_data_title', 'event_details_title'];



            Ext.each(fields, function(field){
                var cmp = Ext.getCmp(field),
                    el = cmp.getEl();
                el.un('click', cmp.toggleFn);
                el.on('click', cmp.toggleFn);
            });

            if (btn){
                btn.un('click', this.onDetailHide);
                btn.on('click', this.onDetailHide);
            }
            if (pop){
                pop.un('click', this.popout, this);
                pop.on('click', this.popout, this);
            }
        },
        load: function(event_id){
            Zenoss.remote.EventsRouter.detail({
                evid:event_id
            }, function(result){
                var event = result.event[0];
                this.update(event);
                this.bind();
                this.show();
            }, this);
        }
    });
    Ext.reg('detailpanel', Zenoss.DetailPanel);

}());
