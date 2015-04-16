/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2015, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function() {
    /**
     * Trendline Projection Parameters
     * This is a dynamic form that updates with inputs for the parameters based on the trendline algorithm that is used
     **/
    Ext.define("Zenoss.form.TrendlineProjectionParameters", {
        alias:['widget.trendlineprojectionparameters'],
        extend:"Ext.panel.Panel",
        constructor: function(config) {
            config = config || {};
            config.listeners = Ext.applyIf(config.listeners || {}, {
                afterrender: this.setupAlgorithmComboListeners,
                scope: this
            });
            Ext.applyIf(config, {
                layout: 'vbox',
                height: 50,
                items: [{
                    xtype: 'container',
                    html: config.fieldLabel + ":",
                    width: 300
                },{
                    xtype: 'hidden',
                    name: config.name,
                    value: config.value
                }, {
                    xtype: 'form',
                    itemId: 'parameterFields',
                    defaults: {
                        listeners: {
                            change: this.updateHiddenField,
                            scope: this
                        }
                    },
                    height: 200
                }]
            });
            this.callParent(arguments);
        },
        /**
         * Assumes that in the same form there is a combo that has the projection Algorithm.
         **/
        getAlgorithmComboBox: function(){
            return this.up('form').down('combo[name="projectionAlgorithm"]');
        },
        /**
         * Short cut for fetching the panel that has all of our parameter fields
         **/
        getFormFields: function() {
            return this.down('form[itemId="parameterFields"]');
        },
        /**
         * Sets up the listener for the combo box to update the parameter fields
         **/
        setupAlgorithmComboListeners: function() {
            var algorithmCombo = this.getAlgorithmComboBox();
            algorithmCombo.on('change', this.updateProjectionAlgorithmParametersPanel, this);
            this.updateProjectionAlgorithmParametersPanel();
        },
        /**
         * This is fired every time the projection algorithm combo changes. It removes all the fields
         * and rebuilds it based on the selected algorithm.
         **/
        updateProjectionAlgorithmParametersPanel: function() {
            var algorithmCombo = this.getAlgorithmComboBox(),
                fields = this.getFormFields(),
                values = Ext.JSON.decode(this.down('hidden').getValue());
            fields.removeAll();
            if (!algorithmCombo.getValue()) {
                return;
            }
            fields.add(this.getProjectionParameters(algorithmCombo.getValue(), values));
        },
        /**
         * This will need to be updated for each projection type, for example Holt Winters etc
         **/
        getProjectionParameters: function(type, values) {
            var fields = {
                linear: null,
                polynomial: [{
                    xtype: 'numberfield',
                    value: values['n'] || 2,
                    minValue: 1,
                    maxValue: 10,
                    name: 'n',
                    fieldLabel: _t('N')
                }]
            };
            return fields[type];
        },
        /**
         * stores the entries in json in a hidden field so it is easier to set it back on the server
         **/
        updateHiddenField: function() {
            var parameters = this.getFormFields().getForm().getValues();
            this.down('hidden').setValue(Ext.JSON.encode(parameters));
        }
    });
}());
