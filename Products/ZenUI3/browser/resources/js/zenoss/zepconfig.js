/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.onReady(function() {

    var AGE_ALL_EVENTS = 6;

    Ext.define("Zenoss.EventAgeSeverity", {
        alias: ["widget.eventageseverity"],
        extend: "Ext.form.ComboBox",
        constructor: function(config) {
            config = config || {};
            var store = [[AGE_ALL_EVENTS, _t('Age All Events')]].concat(Zenoss.env.SEVERITIES);
            Ext.applyIf(config, {
                fieldLabel: _t('Severity'),
                name: 'severity',
                editable: false,
                forceSelection: true,
                autoSelect: true,
                triggerAction: 'all',
                queryMode: 'local',
                store: store
            });
            Zenoss.EventAgeSeverity.superclass.constructor.call(this, config);
        }
    });

    Ext.ns('Zenoss.settings');
    var router = Zenoss.remote.EventsRouter;


    function saveConfigValues(results, callback) {
        // if they wish to age all events update the inclusive flag
        var values = results.values;
        values.event_age_severity_inclusive = false;
        if (values.event_age_disable_severity === AGE_ALL_EVENTS) {
            values.event_age_disable_severity = 5; // critical
            values.event_age_severity_inclusive = true;
        }
        router.setConfigValues(results, callback);
    }

    function buildPropertyGrid(response) {
        var propsGrid,
            severityField, inclusiveField,
            data;
        data = response.data;
        severityField = Zenoss.util.filter(data, function(field) {
            return field.id === 'event_age_disable_severity';
        })[0];

        inclusiveField = Zenoss.util.filter(data, function(field) {
            return field.id === 'event_age_severity_inclusive';
        })[0];

        // fields can be filtered due to lack of perms need to check that
        if (inclusiveField && inclusiveField.value) {
            // set the dropdown box to include the selected severity (if it is critical,
            // then the drop down will show "Age All Events")
            severityField.value = severityField.value + 1;
        }
        propsGrid = new Zenoss.form.SettingsGrid({
            renderTo: 'propList',
            width: 500,
            saveFn: saveConfigValues
        }, data);

        Ext.each(data, function(row){
            // make sure the tooltip shows up
            Zenoss.registerTooltipFor(row.id);
        });

    }

    function loadProperties() {
        router.getConfig({}, buildPropertyGrid);
    }

    loadProperties();


});
