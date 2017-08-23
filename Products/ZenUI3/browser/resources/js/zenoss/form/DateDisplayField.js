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
        dateFormat: Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT,

        constructor: function(config) {
            config = config || {};
            config.value = this.formatDate(config.value);
            this.callParent([config]);
        },

        formatDate: function(date) {
            var value = date;
            if (value && Ext.isNumeric(value)){
                // assume it is a timestamp and format it using the timezone
                //value = Zenoss.date.renderWithTimeZone(value);
                value = moment.unix(value
                        ).tz(Zenoss.USER_TIMEZONE
                        ).format(this.dateFormat);
            }
            return value;
        },

        setValue: function(value) {
            this.callParent([this.formatDate(value)]);
        },

        afterRender: function(){
            Ext.create('Ext.tip.ToolTip', {
                target: this.bodyEl.dom.id,
                html: Zenoss.USER_TIMEZONE
            });
        }
    });
}());
