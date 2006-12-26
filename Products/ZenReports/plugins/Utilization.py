from Products.ZenUtils import Time

def getSummaryArgs(dmd, args):
    zem = dmd.ZenEventManager
    startDate = args.get('startDate', zem.defaultAvailabilityStart())
    endDate = args.get('endDate', zem.defaultAvailabilityEnd())
    startDate, endDate = map(Time.ParseUSDate, (startDate, endDate))
    startDate = min(startDate, endDate - 1)
    how = args.get('how', 'AVERAGE')
    return dict(start=startDate, end=endDate, function=how)

