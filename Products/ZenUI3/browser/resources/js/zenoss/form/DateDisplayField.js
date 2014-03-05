/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function() {
    Ext.define("Zenoss.form.DateDisplayField", {
        alias:['widget.datedisplayfield'],
        extend:"Ext.form.field.Display",
        dateFormat: "YYYY-MM-DD HH:mm:ss a",
        constructor: function(config) {
            config = config || {};
            config.value = this.formatDate(config.value);
            this.callParent([config]);
        },
        formatDate: function(date) {
            var value = date;
            if (value && Ext.isNumeric(value)){
                // assume it is a timestamp and format it using the timezone
                value = Zenoss.date.renderWithTimeZone(value, this.format);
            }
            return value;
        },
        setValue: function(value) {
            this.callParent([this.formatDate(value)]);
        }
    });
}());