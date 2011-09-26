/*
  ###########################################################################
  #
  # This program is part of Zenoss Core, an open source monitoring platform.
  # Copyright (C) 2010, Zenoss Inc.
  #
  # This program is free software; you can redistribute it and/or modify it
  # under the terms of the GNU General Public License version 2 or (at your
  # option) any later version as published by the Free Software Foundation.
  #
  # For complete information please visit: http://www.zenoss.com/oss/
  #
  ###########################################################################
*/

/* package level */
(function() {
    var ReverseSeverity,
        Severity;
    Ext.define("Severity", {
        alias:['widget.severity'],
        extend:"Ext.form.ComboBox",
        constructor: function(config) {
            config = config || {};

            Ext.applyIf(config, {
                fieldLabel: _t('Severity'),
                name: 'severity',
                editable: false,
                forceSelection: true,
                autoSelect: true,
                triggerAction: 'all',
                mode: 'local',
                // this is defined in zenoss.js so should always be present
                store: Zenoss.env.SEVERITIES
            });
            this.callParent(arguments);
        }
    });


    Ext.define("ReverseSeverity", {
        alias:['widget.reverseseverity'],
        extend:"Severity",
        constructor: function(config) {
            var severities = [[0, "Critical"], [1, "Error"], [2, "Warning"], [3, "Info"], [4, "Debug"], [5, "Clear"]];
            config = config || {};
            Ext.applyIf(config, {
                store: severities
            });
            this.callParent(arguments);
        }
    });


}());

