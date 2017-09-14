/* global EventActionManager:true, moment:true */
/**
 * Zenoss date patterns and manipulations
 */

(function(){ // Local scope
Ext.namespace('Zenoss')
Ext.namespace('Zenoss.date');


/**
 * A set of useful date formats. All dates should come from the server as
 * ISO8601Long, but we may of course want to render dates in many different
 * ways.
 */
Ext.apply(Zenoss.date, {
    ISO8601Long:"Y-m-d H:i:s",
    ISO8601Short:"Y-m-d",
    ShortDate: "n/j/Y",
    LongDate: "l, F d, Y",
    FullDateTime: "l, F d, Y g:i:s A",
    MonthDay: "F d",
    ShortTime: "g:i A",
    LongTime: "g:i:s A",
    SortableDateTime: "Y-m-d\\TH:i:s",
    UniversalSortableDateTime: "Y-m-d H:i:sO",
    YearMonth: "F, Y",
    ISO8601LongRange: "Y-m-d H:i:s \\T\\O Y-m-d H:i:s",
    LongRangeAndDefault: Ext.form.field.Date.prototype.altFormats + '|' + Zenoss.date.ISO8601LongRange,
    regex: {
        ISO8601LongRange: /^(19|20)\d\d-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01]) ([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]) TO (19|20)\d\d-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01]) ([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$/,
        ISO8601Long: /^(19|20)\d\d-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01]) ([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$/
    }
});


/**
 * This takes a unix timestamp and renders it in the
 * logged in users's selected timezone.
 * Format is optional, if not passed in the default will be used.
 * NOTE: value here must be in seconds, not milliseconds
 **/
Zenoss.date.renderWithTimeZone = function (date, format) {
    return Zenoss.render.date(date, format)
};

Zenoss.date.renderDateColumn = function(format) {
    return function(v) {
        return Zenoss.date.renderWithTimeZone(v, format||Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT);
    };
};


/**
 * @class Zenoss.DateRange
 * @extends Ext.form.field.Date
 * A DateRange
 */
Ext.define("Zenoss.DateRange", {
    extend: "Ext.form.field.Date",
    alias: ['widget.DateRange'],
    xtype: "daterange",
    formatDate: function (date) {
            return Ext.isDate(date) ? moment(date).format(Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT) : date;
    },
    getErrors: function(value) {
        var errors = new Array();
        if (value == "") {
            return errors;
        }
        //Look first for invalid characters, fail fast
        if (/[^0-9/TOampm :-]/.test(value)) {
            errors.push("Date contains invalid characters - valid characters include digits, dashes, colons, and spaces");
            return errors;
        }
        if (value.indexOf("TO") === -1) {
            if (!moment(value, Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT).isValid()) {
	        errors.push("Date is formatted incorrectly - format should be " + Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT);
            }
        }
        return errors;
    }
});

/* For UserInterfaceSettings */

Zenoss.date.dateFormats = {
    'year-month-day': 'YYYY-MM-DD',
    'day-month-year': 'DD-MM-YYYY',
    'month-day-year': 'MM-DD-YYYY',
    'year/month/day': 'YYYY/MM/DD',
    'day/month/year': 'DD/MM/YYYY',
    'month/day/year': 'MM/DD/YYYY',
}

Zenoss.date.timeFormats = {
    '12h am/pm': 'hh:mm:ss a',
    '24h': 'HH:mm:ss'
}

Ext.onReady(function(){
    // For compatibility use the same data format for Zenoss.date.timeZones
    // as before.
    zones = {}

    Ext.each(moment.tz.names(), function(zone) {
        zones[zone] = zone;
    });
    Zenoss.date.timeZones = {zones: zones};
});


/* Readable dates */
var _time_units = [
    ['year',   60*60*24*365],
    ['month',  60*60*24*30],
    ['week',   60*60*24*7],
    ['day',    60*60*24],
    ['hour',   60*60],
    ['minute', 60],
    ['second', 1]
];

Date.prototype.readable = function(precision) {
    var diff = (new Date().getTime() - this.getTime())/1000,
        remaining = Math.abs(diff),
        result = [], i;
    for (i=0;i<_time_units.length;i++) {
        var unit = _time_units[i],
            unit_name = unit[0],
            unit_mult = unit[1],
            num = Math.floor(remaining/unit_mult);
        remaining = remaining - num * unit_mult;
        if (num) {
            result.push(num + " " + unit_name + (num>1 ? 's' : ''));
        }
        if (result.length === precision) {
            break;
        }
    }
    var base = result.join(' ');
    return diff >= 0 ? base + " ago" : "in " + base;
};

})(); // End local scope
