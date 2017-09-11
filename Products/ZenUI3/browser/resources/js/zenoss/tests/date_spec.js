
describe("Zenoss.date Test Suite", function(){
    beforeEach(function(){
        Zenoss.USER_DATE_FORMAT = "YYYY-MM-DD";
        Zenoss.USER_TIME_FORMAT = "hh:mm:ss a";
        Zenoss.USER_TIMEZONE = "Singapore";
    });

    it('formatWithTimezone applies user format and timezone', function(){
        expect(
            Zenoss.date.renderWithTimeZone(1)
        ).toBe("1970-01-01 07:30:01 am SGT");
    });

    it('formatWithTimezone handles epoc 0', function(){
        expect(
            Zenoss.date.renderWithTimeZone(0)
        ).toBe("1970-01-01 07:30:00 am SGT");
    });

    it('formatWithTimezone applies given format', function(){
        expect(
            Zenoss.date.renderWithTimeZone(1, 'YYYY.MM.DD.hh.mm.ss')
        ).toBe("1970.01.01.07.30.01");
    });

    it('formats Date objects properly', function(){
        var extdate = new Date('1/10/2017 03:05:07 PM GMT-0600')
        expect(
            Zenoss.date.renderWithTimeZone(extdate)
        ).toBe('2017-01-11 05:05:07 am SGT')
    });
});
