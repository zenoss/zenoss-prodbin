
describe('Zenoss.date Test Suite', function(){
    beforeEach(function(){
        Zenoss.USER_DATE_FORMAT = 'YYYY-MM-DD';
        Zenoss.USER_TIME_FORMAT = 'hh:mm:ss a';
        Zenoss.USER_TIMEZONE = 'Singapore';
    });

    it('formatWithTimezone applies user format and timezone', function(){
        expect(
            Zenoss.date.renderWithTimeZone(1)
        ).toBe('1970-01-01 07:30:01 am SGT');
    });

    it('formatWithTimezone handles epoc 0', function(){
        expect(
            Zenoss.date.renderWithTimeZone(0)
        ).toBe('1970-01-01 07:30:00 am SGT');
    });

    it('formatWithTimezone applies given format', function(){
        expect(
            Zenoss.date.renderWithTimeZone(1, 'YYYY.MM.DD.hh.mm.ss')
        ).toBe('1970.01.01.07.30.01');
    });

    it('formats Date objects properly', function(){
        var extdate = new Date('1/10/2017 03:05:07 PM GMT-0600')
        expect(
            Zenoss.date.renderWithTimeZone(extdate)
        ).toBe('2017-01-11 05:05:07 am SGT')
    });
});

describe('Zenoss.date.Moment Test Suite', function() {
    beforeEach(function(){
        Zenoss.USER_DATE_FORMAT = 'YYYY-MM-DD';
        Zenoss.USER_TIME_FORMAT = 'hh:mm:ss a';
        Zenoss.USER_TIMEZONE = 'Singapore';
    });

    it('momentFormat has correct value', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(
            cmp.momentFormat
        ).toBe(
            'YYYY-MM-DD hh:mm:ss a'
        )
    });

    it('extFormat has correct value', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(
            cmp.extFormat
        ).toBe(
            'Y-m-d h:i:s A'
        )
    });

    it('asMoment accepts Javascript Date objects', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            dt = new Date(2005, 2, 15, 21, 35, 12);
        expect(
            cmp.asMoment(dt).format('YYYY-MM-DD HH:mm:ss')
        ).toBe(
            '2005-03-15 21:35:12'
        )
    });

    it('asMoment accepts formatted string primitives', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            dtstr = '2005-02-13 05:30:15 pm';
        expect(
            cmp.asMoment(dtstr).format('YYYY-MM-DD HH:mm:ss')
        ).toBe(
            '2005-02-13 17:30:15'
        )
    });

    it('asMoment accepts formatted String objects', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            dtstr = new String('2005-02-13 05:30:15 pm');
        expect(
            cmp.asMoment(dtstr).format('YYYY-MM-DD HH:mm:ss')
        ).toBe(
            '2005-02-13 17:30:15'
        )
    });

    it('asMoment accepts second timestamps', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            seconds = moment.tz(
                '2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE
            ).valueOf() / 1000;
        expect(
            cmp.asMoment(seconds).format('YYYY-MM-DD HH:mm:ss')
        ).toBe(
            '2005-03-15 21:35:12'
        );
    });

    it('asMoment returns a momentjs object', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(
            moment.isMoment(cmp.asMoment(Date.now()))
        ).toBe(
            true
        )
    });

    it('asMoment returns a momentjs with correct timezone', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(
            cmp.asMoment(Date.now()).tz()
        ).toBe(
            Zenoss.USER_TIMEZONE
        )
    });

    it('asMoment returns null for no args', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(cmp.asMoment()).toBe(null);
    });

    it('asMoment returns null for unsupported argument types', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(cmp.asMoment([1,2,3])).toBe(null);
        expect(cmp.asMoment({})).toBe(null);
    });

    it('now returns a momentjs object', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(moment.isMoment(cmp.now())).toBe(true);
    });

    it('now returns a momentjs object with correct timezone', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(
            cmp.now().tz()
        ).toBe(
            Zenoss.USER_TIMEZONE
        );
    });

    it('asDateTimeString accepts momentjs objects', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            ts = moment.tz('2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE);
        expect(
            cmp.asDateTimeString(ts)
        ).toBe(
            '2005-03-15 09:35:12 pm'
        )
    });

    it('asDateTimeString accepts Javascript Date objects', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            dt = new Date(2005, 2, 15, 21, 35, 12);
        expect(
            cmp.asDateTimeString(dt)
        ).toBe(
            '2005-03-15 09:35:12 pm'
        )
    });

    it('asDateTimeString accepts formatted string primitives', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            dtstr = '2005-03-15 09:30:15 pm';
        expect(
            cmp.asDateTimeString(dtstr)
        ).toBe(
            '2005-03-15 09:30:15 pm'
        )
    });

    it('asDateTimeString accepts formatted String objects', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            dtstr = new String('2005-03-15 09:30:15 pm');
        expect(
            cmp.asDateTimeString(dtstr)
        ).toBe(
            '2005-03-15 09:30:15 pm'
        )
    });

    it('asDateTimeString accepts timestamps in seconds', function() {
        var cmp = Ext.create('Zenoss.date.Moment'),
            seconds = moment.tz(
                '2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE
            ).valueOf() / 1000;
        expect(
            cmp.asDateTimeString(seconds)
        ).toBe(
            '2005-03-15 09:35:12 pm'
        );
    });

    it('asDateTimeString returns null for no arguments', function() {
        var cmp = Ext.create('Zenoss.date.Moment');
        expect(
            cmp.asDateTimeString()
        ).toBe(
            null
        );
    });
});

describe('Zenoss.form.field.DateTime Test Suite', function() {
    beforeEach(function(){
        Zenoss.USER_DATE_FORMAT = 'YYYY-MM-DD';
        Zenoss.USER_TIME_FORMAT = 'hh:mm:ss a';
        Zenoss.USER_TIMEZONE = 'Singapore';
    });

    it('momentFormat has correct value', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime');
        expect(
            cmp.momentFormat
        ).toBe(
            'YYYY-MM-DD hh:mm:ss a'
        )
    });

    it('extFormat has correct value', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime');
        expect(
            cmp.extFormat
        ).toBe(
            'Y-m-d h:i:s A'
        )
    });

    it('format has correct value', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime');
        expect(
            cmp.format
        ).toBe(
            'Y-m-d h:i:s A'
        )
    });

    it('getValue returns seconds', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime'),
            seconds = cmp.getValue(),
            withSeconds = moment(seconds * 1000).format('YYYY-mm-dd HH:mm:ss'),
            withoutSeconds = moment.unix(seconds).format('YYYY-mm-dd HH:mm:ss');
        expect(
            withSeconds == withoutSeconds
        ).toBe(
            true
        )
    });

    it('setValue accepts Javascript Date objects', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime'),
            dt = new Date(2005, 2, 15, 21, 35, 12);
        expect(
            cmp.setValue(dt).getValue()
        ).toBe(
            moment.tz('2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE).valueOf()
        )
    });

    it('setValue accepts formatted string primitives', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime'),
            dtstr = '2005-02-13 05:30:15 pm';
        expect(
            cmp.setValue(dtstr).getValue()
        ).toBe(
            moment.tz(dtstr, 'YYYY-MM-DD hh:mm:ss a', Zenoss.USER_TIMEZONE).valueOf()
        )
    });

    it('setValue accepts formatted String objects', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime'),
            dtstr = new String('2005-02-13 05:30:15 pm');
        expect(
            cmp.setValue(dtstr).getValue()
        ).toBe(
            moment.tz(dtstr, 'YYYY-MM-DD hh:mm:ss a', Zenoss.USER_TIMEZONE).valueOf()
        )
    });

    it('setValue accepts timestamps in seconds', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime'),
            seconds = moment.tz(
                '2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE
            ).valueOf() / 1000;
        expect(
            cmp.setValue(seconds).getValue()
        ).toBe(
            seconds
        );
    });

    it('setValue accepts no arguments', function() {
        // No argument means use current time, but not sure how to test for 'current' time as it changes.
        var cmp = Ext.create('Zenoss.form.field.DateTime'),
            seconds = cmp.setValue().getValue();
        expect(
            seconds !== undefined && seconds !== null
        ).toBe(
            true
        );
    });

    it('getSubmitValue returns seconds', function() {
        var cmp = Ext.create('Zenoss.form.field.DateTime'),
            seconds = cmp.getSubmitValue(),
            withSeconds = moment(seconds * 1000).format('YYYY-mm-dd HH:mm:ss'),
            withoutSeconds = moment.unix(seconds).format('YYYY-mm-dd HH:mm:ss');
        expect(
            withSeconds == withoutSeconds
        ).toBe(
            true
        )
    });
});
