describe("Zenoss.render.date Test Suite", function(){
    beforeEach(function(){
        Zenoss.USER_DATE_FORMAT = "YYYY-MM-DD";
        Zenoss.USER_TIME_FORMAT = "hh:mm:ss a";
        Zenoss.USER_TIMEZONE = "Singapore";
    });

    it('render.date applies user format and timezone', function(){
        expect(
            Zenoss.render.date(1)
        ).toBe("1970-01-01 07:30:01 am SGT");
    });

    it('render.date handles epoc 0', function(){
        expect(
            Zenoss.render.date(0)
        ).toBe("1970-01-01 07:30:00 am SGT");
    });

    it('render.date applies given format', function(){
        expect(
            Zenoss.render.date(1, 'YYYY.MM.DD.hh.mm.ss')
        ).toBe("1970.01.01.07.30.01");
    });

    it('render.date handles Date objects properly', function(){
        var extdate = new Date('1/10/2017 03:05:07 PM GMT-0600')
        expect(
            Zenoss.render.date(extdate)
        ).toBe('2017-01-11 05:05:07 am SGT')
    });
});
