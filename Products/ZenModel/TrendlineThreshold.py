##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__= """TrendlineThreshold
Makes a threshold comparison against a projected trendline
"""
import time
import datetime
from dateutil.relativedelta import relativedelta
from zope.component import queryUtility
from Globals import InitializeClass
from MinMaxThreshold import MinMaxThreshold, MinMaxThresholdInstance
from Products.ZenModel.ThresholdInstance import MetricThresholdInstance
from ThresholdInstance import ThresholdContext
from Products.ZenEvents.ZenEventClasses import Capacity
from Products.ZenCollector.interfaces import IDataService

import logging
log = logging.getLogger('zen.TrendlineThreshold')

PROJECTION_TIME_UNITS = ['days', 'weeks', 'months']
PROJECTION_ALGORITHMS = ['linear', 'polynomial']
AGGREGATE_FUNCTIONS = ['max', 'avg']

class TrendlineThreshold(MinMaxThreshold):
    """
    Threshold class that alerts against projected values
    """
    meta_type = "TrendlineThreshold"

    eventClass = Capacity
    # default to info since the projection is unreliable
    severity = 2

    # when asking for projected data which function we use when downsampling the values
    aggregateFunction = AGGREGATE_FUNCTIONS[0]

    # amount of time of data we want to use in our projected
    pastData = 10
    pastDataUnits = PROJECTION_TIME_UNITS[0]

    # how far to calculate the prediction to see if we cross the threshold
    amountToPredict = 10
    amountToPredictUnits = PROJECTION_TIME_UNITS[0]

    projectionAlgorithm = PROJECTION_ALGORITHMS[0]

    # json encoded parameters for this projection algorithm (for instance if polynomial then this has the value of "N")
    projectionParameters = "{}"

    _properties = MinMaxThreshold._properties + (
        {'id':'pastData', 'type':'integer',  'mode':'w'},
        {'id':'pastDataUnits', 'type':'string',  'mode':'w'},
        {'id':'amountToPredict', 'type':'integer',  'mode':'w'},
        {'id':'amountToPredictUnits', 'type':'string',  'mode':'w'},
        {'id':'aggregateFunction', 'type':'string',  'mode':'w'},
        {'id':'projectionParameters', 'type':'string',  'mode':'w'},
        )

    factory_type_information = (
        {
        'immediate_view' : 'editRRDThreshold',
        'actions'        :
        (

        )
        },
        )

    def createThresholdInstance(self, context):
        """
        Return the config used by the collector to process min/max
        thresholds. (id, minval, maxval, severity, escalateCount)
        """
        mmt = TrendlineThresholdInstance(self.id,
                                      ThresholdContext(context),
                                      self.dsnames,
                                      minval=self.getMinval(context),
                                      maxval=self.getMaxval(context),
                                      eventClass=self.eventClass,
                                      severity=self.getSeverity(context),
                                      # data needed for projections
                                      aggregateFunction=self.aggregateFunction,
                                      pastData=self.pastData,
                                      pastDataUnits=self.pastDataUnits,
                                      amountToPredict=self.amountToPredict,
                                      amountToPredictUnits=self.amountToPredictUnits,
                                      projectionAlgorithm=self.projectionAlgorithm,
                                      projectionParameters=self.projectionParameters,
                                      eventFields=self.getEventFields(context),
              )
        return mmt



InitializeClass(TrendlineThreshold)


class TrendlineThresholdInstance(MinMaxThresholdInstance):

    DOWNSAMPLE = [
        # for now when the delta is < 1 hour we do NOT do downsampling
        [3600, '10s-avg'],     # 1 Hour
        [7200, '30s-avg'],     # 2 Hours
        [14400, '45s-avg'],    # 4 Hours
        [18000, '1m-avg'],     # 5 Hours
        [28800, '2m-avg'],     # 8 Hours
        [43200, '3m-avg'],     # 12 Hours
        [64800, '4m-avg'],     # 18 Hours
        [86400, '5m-avg'],     # 1 Day
        [172800, '10m-avg'],   # 2 Days
        [259200, '15m-avg'],   # 3 Days
        [604800, '1h-avg'],    # 1 Week
        [1209600, '2h-avg'],   # 2 Weeks
        [2419200, '6h-avg'],   # 1 Month
        [9676800, '1d-avg'],   # 4 Months
        [31536000, '10d-avg']  # 1 Year
    ]

    def __init__(self, id, context, dpNames,
                 minval, maxval, eventClass, severity,
                 **kwargs):
        MetricThresholdInstance.__init__(self, id, context, dpNames, eventClass, severity)
        self.minimum = minval if minval != '' else None
        self.maximum = maxval if maxval != '' else None
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def _getStartDate(self):
        """
        Uses the pastData and pastData Units to get the unix timestamp for the sample we
        are using to create the projection
        """
        t = datetime.datetime.now()
        args = {
            self.pastDataUnits: self.pastData
        }
        startDate = t - relativedelta(**args)
        # return unix startime
        return int(startDate.strftime("%s"))

    def _getEndDate(self):
        return time.time()

    def _getDownsample(self):
        deltaInSeconds = self._getEndDate() - self._getStartDate()
        for seconds, downsample in self.DOWNSAMPLE:
            if deltaInSeconds <= seconds:
                return downsample

    def getPastData(self, dataPoint, value):
        """
        Uses defers to fetch the collected metrics from zenhub that we need to make our
        projection.
        """
        defer = queryUtility(IDataService).getService('MetricService')
        def queryMetrics(service):
            log.info("About to call fetch metrics %s context %s dataPoint", self._context.contextUid, [dataPoint])
            fetchDeferred = service.callRemote('fetchMetrics', self._context.contextUid, [dataPoint],
                                               {"cf": self.aggregateFunction,
                                                "returnSet": "EXACT",
                                                "start": self._getStartDate(),
                                                "end": self._getEndDate(),
                                                "downsample": self._getDownsample()
                                               })
            fetchDeferred.addCallback(self.doesProjectedDataBreachThreshold)
        defer.addCallback(queryMetrics)

    def doesProjectedDataBreachThreshold(self, results):
        datapoints = results[0]['datapoints']
        xValues = [d['timestamp'] for d in datapoints]
        yValues = [d['value'] for d in datapoints]
        projectionFn = self._getProjectionFn(xValues, yValues)
        args = {
            self.amountToPredictUnits:self.amountToPredict
        }
        futureTime = datetime.datetime.now() + relativedelta(**args)
        projectedYValue = projectionFn(int(futureTime.strftime("%s")))
        log.info("Projected XValue %s YValue %s min: %s max: %s polyfunc %s", int(futureTime.strftime("%s")),
                 projectedYValue, self.minimum, self.maximum, projectionFn)
        breached = False
        if self.maximum is not None and projectedYValue >= self.maximum:
            expectedDate = self.solve_for_y(projectionFn, self.maximum)
            self.sendProjectedBreachedEvent(expectedDate)
            breached = True
        if self.minimum is not None and  projectedYValue <= self.minimum:
            expectedDate = self.solve_for_y(projectionFn, self.minimum)
            self.sendProjectedBreachedEvent(expectedDate)
            breached = True
        if not breached:
            self.sendClearEvent()

    def _getProjectionFn(self, xValues, yValues):
        import numpy.polynomial.polynomial as poly
        from numpy import RankWarning
        import warnings
        warnings.simplefilter('ignore', RankWarning)
        n = 2
        if self.projectionAlgorithm == "linear":
            n = 1
        elif self.projectionAlgorithm == "polynomial":
            n = self.projectionParameters["n"]
        z = poly.polyfit(xValues, yValues, int(n))
        return poly.Polynomial(z)

    def solve_for_y(self, poly_coeffs, y):
        import numpy
        pc = poly_coeffs.copy()
        pc[-1] -= y
        return numpy.roots(pc)

    def sendProjectedBreachedEvent(self, expectedDate):
        pass

    def sendClearEvent(self, dataPoint):
        pass

    def _checkImpl(self, dataPoint, value):
        self.getPastData(dataPoint, value)

from twisted.spread import pb
pb.setUnjellyableForClass(TrendlineThresholdInstance, TrendlineThresholdInstance)
