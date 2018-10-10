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
var time_units = [
        ['year',   60*60*24*365],
        ['month',  60*60*24*30],
        ['week',   60*60*24*7],
        ['day',    60*60*24],
        ['hour',   60*60],
        ['minute', 60],
        ['second', 1]
    ],
    // Note: 'e2mTokens' is Ext.Date to MomentJS date format token mappings
    // and 'm2eTokens' is MomentJs to Ext.Date date format token mappings
    e2mTokens = {
        'Y': 'YYYY',
        'm': 'MM',
        'd': 'DD',
        'h': 'hh',
        'H': 'HH',
        'i': 'mm',
        's': 'ss',
        'A': 'a'
    },
    m2eTokens = Object.keys(e2mTokens).reduce(function(o, k) { o[e2mTokens[k]] = k; return o; }, {}),
    moment2ext = function(format) {
        var newFormat = format;
        for (token in m2eTokens) {
            newFormat = newFormat.replace(new RegExp(token, 'g'), m2eTokens[token]);
        }
        return newFormat;
    },
    ext2moment = function(format) {
        var target = [];
        for (var i = 0, len = format.length; i < len; ++i) {
            var ch = format.charAt(i);
            target.push((ch in e2mTokens) ? e2mTokens[ch] : ch);
        }
        return target.join('');
    },
    toMillis = function(value) {
        return Ext.isNumeric(value) ? (parseInt(value) * 1000) : null;
    },
    toSeconds = function(value) {
        return Ext.isNumeric(value) ? (parseInt(value) / 1000) : null;
    };

Date.prototype.readable = function(precision) {
    var diff = toSeconds(new Date().getTime() - this.getTime()),
        remaining = Math.abs(diff),
        result = [];
    for (var i = 0; i < time_units.length; ++i) {
        var unit = time_units[i],
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

/**
 * A mixin class that provides support for handling momentjs objects and integrating them with ExtJS components.
 *
 * Classes that mix in this class *must* call the constructor manually.  Ext will not call the constructors
 * of mixin classes automatically.
 */
Ext.define('Zenoss.date.Moment', {

    statics: {
        /**
         * Convert a Moment format string into an Ext.Date format string.
         *
         * @private
         * @param {format} A string containing a momentjs format.
         * @return {string} A string containing an Ext.Date format.
         */
        fromMomentFormat: moment2ext,

        /**
         * Convert an Ext.Date format string into a Moment format string.
         *
         * @private
         * @param {format} A string containing an Ext.Date format.
         * @return {string} A string containing a momentjs format.
         */
        toMomentFormat: ext2moment,

        /**
         * Returns a momentjs object representing the current time.
         */
        now: function() {
            return moment.tz(Zenoss.USER_TIMEZONE);
        },

        tzstring: (function() {
            return moment.tz(Zenoss.USER_TIMEZONE).format('z');
        })()
    },

    constructor: function(config) {
        var config = config || {};
        Ext.applyIf(config, {
            dateOnly: false
        });

        if (config.dateOnly) {
            this.momentFormat = Zenoss.USER_DATE_FORMAT;
            this.extFormat = moment2ext(Zenoss.USER_DATE_FORMAT);
        } else {
            this.momentFormat = Zenoss.USER_DATE_FORMAT + " " + Zenoss.USER_TIME_FORMAT;
            this.extFormat = moment2ext(Zenoss.USER_DATE_FORMAT + " " + Zenoss.USER_TIME_FORMAT);
        }
    },

    /**
     * Returns a momentjs object that represents the given object.
     *
     * This method accepts Javascript Date objects, string objects (and string primitives) that
     * are formatted as given in the format argument, numbers that are absolute time in seconds,
     * and other momentjs objects.
     *
     * If the given obj argument is not a supported type, null is returned.
     *
     * The format argument is only necessary for Javascript Date and string objects.
     *
     * @param {obj} A datetime representation to be reformatted.
     * @param {string} An Ext.Date format string.
     * @return {String} A datetime string formatted according to momentFormat.
     */
    asMoment: function(obj, format) {
        var args = [],
            value = Ext.isNumeric(obj) ? parseInt(obj) : obj,
            format = (format === undefined) ? this.extFormat : format;
        if (moment.isMoment(obj)) {
            args.push(obj)
        }
        else if (value instanceof Date) {
            var repr = Ext.Date.format(value, format),
                reprFmt = Zenoss.date.Moment.toMomentFormat(format);
            args.push(repr, reprFmt);
        }
        else if (typeof value == "string" || value instanceof String) {
            args.push(value, Zenoss.date.Moment.toMomentFormat(format));
        }
        else if (typeof value == "number" || moment.isMoment(value)) {
            args.push(toMillis(value))
        }
        return (args.length > 0) ? moment.tz.apply(this, args.concat(Zenoss.USER_TIMEZONE)) : null;
    },

    /**
     * Returns a string representation of the given momentjs object.
     */
    asDateTimeString: function(m) {
        if (!moment.isMoment(m)) {
            m = this.asMoment(m);
        }
        return (m != null) ? m.format(this.momentFormat) : null;
    }

});


/**
 * Form field for handling datetimes with timezones.
 */
Ext.define('Zenoss.form.field.DateTime', {
    extend: 'Ext.form.field.Date',
    alias: 'widget.zendatetimefield',
    mixins: ['Zenoss.date.Moment'],
    constructor: function(config) {
        var config = config || {};

        // Calling the mixin constructor because Ext does not.
        // Note: call this first.
        this.mixins['Zenoss.date.Moment'].constructor.call(this, config);

        config = Ext.applyIf(config, {
            format: this.extFormat
        });
        this.callParent([config]);
    },
    setValue: function(timestamp) {
        var value = this.asMoment(timestamp, this.format),
            repr = (value != null) ? this.asDateTimeString(value) : null,
            input = (repr != null) ? repr : undefined;
        return this.callParent([input]);
    },
    getValue: function() {
        var value = this.callParent(arguments),
            output = (value !== null) ? this.asMoment(value, this.format) : null;
        return (output !== null) ? toSeconds(output.valueOf()) : null;
    },
    getSubmitValue: function() {
        return this.getValue();
    }
});


/**
 * Form field for handling datetimes with timezones.
 */
Ext.define('Zenoss.form.field.DateTimeDisplay', {
    extend: 'Ext.form.field.Date',
    alias: 'widget.zendatetimedisplayfield',
    mixins: ['Zenoss.date.Moment'],
    constructor: function(config) {
        // Calling the mixin constructor because Ext does not.
        this.mixins['Zenoss.date.Moment'].constructor.call(this, config);

        var config = config || {};
        config = Ext.applyIf(config, {
            format: this.extFormat
        });
        this.callParent([config]);
    },
    setValue: function(timestamp) {
        var value = this.asMoment(timestamp, this.format),
            repr = (value != null) ? this.asDateTimeString(value) : null,
            input = (repr != null) ? repr : this.asDateTimeString(Zenoss.date.Moment.now());
        return this.callParent([input]);
    },
    getValue: function() {
        var value = this.callParent(arguments),
            output = this.asMoment(value, this.format);
        return toSeconds(output.valueOf());
    },
    getSubmitValue: function() {
        return this.getValue();
    }
});


/**
 * Grid column for handling datetimes with timezones.
 */
Ext.define('Zenoss.grid.column.DateTime', {
    extend: 'Ext.grid.column.Column',
    alias: 'widget.zendatetimecolumn',
    mixins: ['Zenoss.date.Moment'],
    constructor: function(config) {
        // Calling the mixin constructor because Ext does not.
        this.mixins['Zenoss.date.Moment'].constructor.call(this);

        var config = config || {};
        config = Ext.applyIf(config, {
            scope: this  // make sure the renderer is called using the Zenoss.grid.column.DateTime context
        });
        this.callParent([config]);
    },
    renderer: function(value, metadata, record) {
        metadata.tdAttr = 'data-qtip="' + Zenoss.date.Moment.tzstring + '"';
        return Zenoss.render.date(value, this.momentFormat);
    }
});

})(); // End local scope
