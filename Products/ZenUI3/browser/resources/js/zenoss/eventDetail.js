Ext.onReady(function() {
    var ns = Ext.ns('Zenoss.eventdetail');

    /**
     * This property is used by ZenPacks and other things to specify custom
     * renderers for fields in the detail panel before the panel has
     * instantiated. Once instantiated, the panel will apply any renderers
     * found here.
     */
    if (!Zenoss.hasOwnProperty('event_detail_custom_renderers')) {
        Zenoss.event_detail_custom_renderers = {};
    }

    /**
     * This property is by ZenPacks and other things to specify custom sections
     * for the detail panel before the panel has been instantiated. The section
     * config must specify a `section_class` property which is the string name
     * of a section class ('Section', 'RepeatedSection', etc.).
     *
     * A section config may also specify `renderers` which will specify a custom
     * renderer for a field. This will override the renderer for that field for
     * the entire detail panel.
     *
     * If a section config specifies a `title` property, the title will be used
     * to toggle display of the section.
     */
    if (!Zenoss.hasOwnProperty('event_detail_custom_sections')) {
        Zenoss.event_detail_custom_sections = {};
    }


    /**
     * The header used for the top of the event detail pane.
     * WAS ns.detail_table_template
     */
    ns.detail_header_template = ['<table width="100%" id="evdetail_props_table">',
        '<tr><td class="dt">',_t('Resource:'),'</td>',
            '<td>',
                '<tpl if="device">',
                    '{device}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">',_t('Component:'),'</td>',
            '<td>',
                '<tpl if="component">',
                    '{component}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">',_t('Event Class:'),'</td>',
            '<td>',
                '<tpl if="eventClass">',
                    '{eventClass}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">',_t('Status:'),'</td> <td>{eventState}</td></tr>',
        '<tr><td class="dt">',_t('Message:'),'</td> <td>{message}</td></tr>',        
    '</table><div style="clear:both;"></div>'];

    /**
     * The template used for regular event properties.
     * WAS: ns.fullprop_table_template
     */
    ns.detail_data_template = ['<table class="proptable">',
        '<tpl for="properties">',
        '<tr class=\'{[xindex % 2 === 0 ? "even" : "odd"]}\'>',
        '<td class="proptable_key">{key}</td>',
        '<td class="proptable_value">{value}</td></tr>',
        '</tpl>',
        '</table>'];

    /**
     * Template for log messages.
     * WAS: ns.log_table_template
     */
    ns.detail_log_template = ['<table>',
        '<tpl for="log">',
        '<tr><td class="time">{0} {1}: </td>',
            '<td class="message">{2}</td></tr>',
        '</tpl>',
        '</table>'];


    /**
     * This class will generate HTML based on a template that simply uses named
     * properties:
     *
     *      "<p>{my_key}</p>"
     *
     */
    ns.Section = Ext.extend(Object, {
        constructor: function(config){
            Ext.applyIf(config || {}, {
                template: ns.detail_data_template
            });
            Ext.apply(this, config);

            ns.Section.superclass.constructor.apply(this, arguments);
        },

        /**
         * A section is asked to generate its own HTML using this method.
         *
         * @param renderedData This is the event data after each field has been
         *                     rendered according to any renderers specified.
         *                     This contains all rendered data, not just the data
         *                     for the keys specified in this section.
         * @param eventData This is the raw event data. This is made available to
         *                  the section so that it may use it for whatever it wants.
         */
        generateHtml: function(renderedData, eventData) {
            var template = new Ext.XTemplate(this.template),
                props = {};
            Ext.each(this.keys, function(key) {
                props[key] = renderedData[key];
            });
            return template.apply(props);
        }
    });


    /**
     * This class will generate HTML based on a template that utilizes 'for'
     * and iterates over data on the 'properties' property:
     *
     *  "<tpl for="properties">
     *      <p>{key}: {value}</p>
     *   </tpl>"
     *
     */
    ns.RepeatedSection = Ext.extend(ns.Section, {
        constructor: function(config) {
            Ext.applyIf(config || {} , {
                generateHtml: function(renderedData, eventData) {
                    var template = new Ext.XTemplate(this.template),
                        props = {
                            properties: []
                        };
                    Ext.each(this.keys, function(key) {
                        props.properties.push({
                            key: key,
                            value: renderedData[key]
                        });
                    });
                    return template.apply(props);
                }
            });
            ns.RepeatedSection.superclass.constructor.apply(this, arguments);
        }
    });


    /**
     * This special details section knows how to iterate over event details. Any
     * keys specified will be looked for in an event's details data.
     */
    ns.DetailsSection = Ext.extend(ns.RepeatedSection, {
        constructor: function(config) {
            Ext.applyIf(config || {} , {
                generateHtml: function(renderedData, eventData) {
                    var template = new Ext.XTemplate(this.template),
                        props = {
                            properties: renderedData['details']
                        },
                        details = [];

                    if (this.hasOwnProperty('keys')) {
                        Ext.each(this.keys, function(key) {
                            Ext.each(renderedData['details'], function(detail) {
                                if (detail.key == key) {
                                    details.push(detail);
                                }
                            }, this);
                        }, this);
                        props.properties = details;
                    }

                    return template.apply(props);
                }
            });
            ns.DetailsSection.superclass.constructor.apply(this, arguments);
        }
    });


    /**
     * This panel represents the event detail panel. An initial "zenoss" config
     * is automatically loaded during instantiation in the `init` method.
     */
    Ext.define("Zenoss.DetailPanel", {
        extend:"Ext.Panel",
        alias: "widget.detailpanel",
        isHistory: false,
        layout: 'border',
        constructor: function(config){
            this.sections = [];
            this.renderers = {};
            config.onDetailHide = config.onDetailHide || Ext.emptyFn;
            config.items = [
                // Details Toolbar
                {
                    id: 'evdetail_hd',
                    region: 'north',
                    layout: 'border',
                    height: 50,
                    cls: 'evdetail_hd',
                    items: [{
                        region: 'west',
                        width: 77,
                        height:47,
                        defaults:{height:47},                       
                        layout: 'hbox',
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
                        items: [{
                            id: 'evdetail-popout',
                            cls: 'evdetail-popout'
                        },{
                            id: 'evdetail_tool_close',
                            cls: 'evdetail_close'
                        }]
                    }]
                },

                // Details Body
                {
                    id: 'evdetail_bd',
                    region: 'center',
                    autoScroll: true,
                    cls: 'evdetail_bd',
                    items: [
                    {
                        id: 'event_detail_properties',
                        frame: false,
                        defaults: {
                            frame: false
                        },
                        layout: {
                            type: 'fit',
                            columns: 1,
                            tableAttrs: {
                                style: {
                                    width: '90%'
                                }
                            }
                        }
                    },

                    // Event Log Header
                    {
                        id: 'evdetail-log-header',
                        cls: 'evdetail-log-header',
                        hidden: false,
                        html: '<'+'hr/><'+'h2>LOG<'+'/h2>'
                    },

                    // Event Audit Form
                    {
                        xtype: 'form',
                        id: 'log-container',
                        frame: true,
                        layout: {
                            type: 'table',
                            columns: 1
                        },
                        style: {'margin-left':'3em'},
                        hidden: false,
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
                            handler: function(btn, e) {
                                var form = Ext.getCmp('log-container'),
                                vals = form.getForm().getValues(),
                                params = {
                                    evid: Ext.getCmp('')
                                };
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
                    },

                    // Event Log Content
                    {
                        id: 'evdetail_log',
                        cls: 'log-content',
                        hidden: false
                    }
                    ]
                }
                
            ];

            Zenoss.DetailPanel.superclass.constructor.call(this, config);
            this.init();
        },

        init: function() {
            var default_renderers = {
                device: function(value, sourceData) {
                    var val = sourceData.device_title;
                    if (sourceData.device_url) {
                        val = Zenoss.render.default_uid_renderer(
                            sourceData.device_url,
                            sourceData.device_title);
                    }
                    return val;
                },
                component: function(value, sourceData) {
                    var val = sourceData.component_title;
                    if (sourceData.component_url) {
                        val = Zenoss.render.default_uid_renderer(
                            sourceData.component_url,
                            sourceData.component_title);
                    }
                    return val;
                },
                eventClass: function(value, sourceData) {
                    return  Zenoss.render.EventClass(
                        sourceData.eventClass_url,
                        sourceData.eventClass
                    );
                },
                eventClassMapping: function(value, sourceData) {
                    if (sourceData.eventClassMapping_url) {
                        return Zenoss.render.link(null,
                            sourceData.eventClassMapping_url,
                            sourceData.eventClassMapping
                        );
                    }
                },
                Systems: function(value, sourceData) {
                    return Zenoss.render.LinkFromGridUidGroup(value);
                },
                DeviceGroups: function(value, sourceData) {
                    return Zenoss.render.LinkFromGridUidGroup(value);
                },
                DeviceClass: function(value, sourceData) {
                    return Zenoss.render.LinkFromGridUidGroup(value);
                },
                Location: function(value, sourceData) {
                    return Zenoss.render.LinkFromGridUidGroup(value);
                }
                
            };
            Ext.apply(this.renderers, default_renderers);

            var eventInfoSection = new ns.Section({
                id: "evdetail_props",
                cls: 'evdetail_props',
                template: ns.detail_header_template,  
                keys: ['device', 'component', 'eventClass', 'eventState', 'message']
            });
            this.addSection(eventInfoSection);

            var eventManagementSection = new ns.RepeatedSection({
                id: "event_detail_management_section",
                title: _t("Event Management"),
                template: ns.detail_data_template,
                keys: [
                    'summary', 'message', 'severity', 'component',
                    'eventClass', 'eventClassKey', 'eventKey', 'dedupid',
                    'evid', 'eventClassMapping', 'eventState',
                    'eventGroup', 'priority', 'facility', 'ntevid',
                    'agent'
                ]
            });
            this.addSection(eventManagementSection);

            var deviceStateSection = new ns.RepeatedSection({
                id: 'event_detail_device_state_section',
                title: _t('Device State'),
                template: ns.detail_data_template,
                keys: [
                    'device', 'ipAddress', 'prodState', 'monitor',
                    'DevicePriority', 'Systems', 'DeviceGroups', 'Location',
                    'DeviceClass'
                ]
            });
            this.addSection(deviceStateSection);

            var eventMetaSection = new ns.RepeatedSection({
                id: 'event_detail_meta_section',
                title: _t('Event Data'),
                template: ns.detail_data_template,
                keys: [
                    'firstTime', 'stateChange', 'lastTime', 'count', 'owner',
                    'clearid'
                ]
            });
            this.addSection(eventMetaSection);

            var eventDetailsSection = new ns.DetailsSection({
                id: 'event_detail_details_section',
                title: _t('Event Details'),
                template: ns.detail_data_template
            });
            this.addSection(eventDetailsSection);

            this.checkCustomizations();
            
        },

        checkCustomizations: function() {
            // Apply any custom renderers that were registered before we loaded
            // the 'stock' sections and renderers.
            Ext.apply(this.renderers, Zenoss.event_detail_custom_renderers);

            // Add any sections that were registered before we loaded completely.
            Ext.each(Zenoss.event_detail_custom_sections, function(section) {
                if (section.hasOwnProperty('section_class')) {
                    var s = new ns[section.section_class](section);
                    this.addSection(section);
                }
            }, this);

            this.doLayout();
        },

        getBody: function() {
            return Ext.getCmp('event_detail_properties');
        },

        addSection: function(section) {
            if (section.hasOwnProperty('renderers')) {
                Ext.apply(this.renderers, section.renderers);
            }

            this.sections.push(section);

            if (section.hasOwnProperty('title')) {
                var section_title_config = {
                    id: section.id + '_title',
                    html: section.title + '...',
                    cls: 'show_details',
                    toggleFn: this.toggleSection.createDelegate(this, [section.id])
                };
                this.getBody().add(section_title_config);
            }

            var should_hide = false;
            if (section.hasOwnProperty('title')) {
                should_hide = true;
            }

            var content_cls = 'full_event_props';
            if (section.hasOwnProperty('cls')) {
                content_cls = section.cls;
            }
            var section_content_config = {
                layout: 'fit',
                id: section.id,
                hidden: should_hide,
                cls: content_cls,
                html: ''
            };

            this.getBody().add(section_content_config);
        },

        removeSection: function(section_id) {
            var remove_idx;
            Ext.each(this.sections, function(item, idx, sections) {
                if (item.id == section_id) {
                    remove_idx = idx;
                }
            });
            this.sections.splice(remove_idx, 1);

            Ext.getCmp(section_id).destroy();
            Ext.getCmp(section_id+'_title').destroy();
        },

        hideSection: function(section_id) {
            Ext.getCmp(section_id).hide();
        },

        showSection: function(section_id) {
            Ext.getCmp(section_id).show();
        },

        toggleSection: function(section_id) {
            var cmp = Ext.getCmp(section_id);
            if (cmp.hidden) {
                cmp.show();
            }
            else {
                cmp.hide();
            }
        },

        findSection: function(section_id) {
            var section;
            Ext.each(this.sections, function(item) {
                if (item.id == section_id) {
                    section = item;
                }
            });
            return section;
        },

        /**
         * This method will iterate over every property of the raw event data
         * and call extractData for that key.
         *
         * @param eventData The raw event data.
         */
        renderData: function(eventData) {
            var renderedData = {};
            Ext.iterate(eventData, function(key) {
                if (key == 'details') {
                    var detailsData = [];
                    Ext.each(eventData[key], function(item) {
                        var val = this.extractData(item.key, item.value, eventData);
                        detailsData.push({
                            key: item.key,
                            value: val
                        });
                    }, this);
                    renderedData[key] = detailsData;
                }
                else {
                    renderedData[key] = this.extractData(key, eventData[key], eventData);
                }
            }, this);

            return renderedData;
        },

        /**
         * Extract rendered data from raw event data. Handles the case where a
         * key does not have a specified renderer as well as the case where
         * the value is null or undefined.
         *
         * @param key The key to use for looking up a renderer.
         * @param value The value to be rendered.
         * @param sourceData All event data.
         */
        extractData: function(key, value, sourceData) {
            var data;
            if (this.renderers.hasOwnProperty(key)) {
                data = this.renderers[key](value, sourceData);
            }
            else if (value) {
                data = value;
            }
            else {
                data = '';
            }
            return data;
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
            Ext.each(Zenoss.env.SEVERITIES, function(sev) {
                sev = sev[1];
                panel.removeClass(sev.toLowerCase());
            });
        },

        update: function(eventData) {

            var renderedData = this.renderData(eventData);

            this.setSummary(renderedData.summary);
            this.setSeverityIcon(Zenoss.util.convertSeverity(eventData.severity));

            // Save the evid for popping out. This is also used when submitting
            // the log form.
            Ext.getCmp('detail-logform-evid').setValue(eventData.evid);

            // Update the data sections
            Ext.each(this.sections, function(section) {
                var cmp = Ext.getCmp(section.id),
                    html;
                html = section.generateHtml(renderedData, eventData);
                cmp.el.update(html);
            }, this);

            // Update Logs
            var logTemplate = new Ext.XTemplate(ns.detail_log_template),
                logHtml;
            logHtml = logTemplate.apply(eventData);
            Ext.getCmp('evdetail_log').el.update(logHtml);
           
        },
        bind: function() {
            var close_btn = Ext.getCmp('evdetail_tool_close').getEl(),
                pop = Ext.getCmp('evdetail-popout').getEl();

            Ext.each(this.sections, function(section) {
                var cmp = Ext.getCmp(section.id+'_title');

                // A section may opt to not have a title, in which case
                // we can't provide auto-collapsing.
                if (cmp) {
                    // We remove this first because we don't want to keep
                    // adding listeners for the same event each time a new
                    // event is loaded.
                    cmp.getEl().un('click', cmp.toggleFn);
                    cmp.getEl().on('click', cmp.toggleFn);
                }

            }, this);

            if (close_btn) {
                // The 'onDetailHide' property is set by the config
                // during instantiation.
                close_btn.un('click', this.onDetailHide);
                close_btn.on('click', this.onDetailHide);
            }

            if (pop) {
                pop.un('click', this.popout, this);
                pop.on('click', this.popout, this);
            }
        },

        popout: function(){
            var evid = Ext.getCmp('detail-logform-evid').getValue(),
                url = this.isHistory ? 'viewHistoryDetail' : 'viewDetail';
            url = url +'?evid='+evid;
            window.open(url, evid.replace(/-/g,'_'),
                        "status=1,width=600,height=500,resizable=1");
        },

        wipe: function() {
            Ext.each(this.sections, function(section) {
                if (section.hasOwnProperty('title')) {
                    this.hideSection(section.id);
                }
            }, this);
        },

        load: function(event_id) {

            Zenoss.remote.EventsRouter.detail({
                evid: event_id
            }, function(result) {
                var event = result.event[0];
                this.wipe();
                this.update(event);
                this.bind();
                this.show();
            }, this);
        }
    });
});
