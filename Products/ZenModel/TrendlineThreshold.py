##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__= """TrendlineThreshold
Makes a threshold comparison against a projected trendline
"""

from Globals import InitializeClass
from MinMaxThreshold import MinMaxThreshold, MinMaxThresholdInstance
from ThresholdInstance import ThresholdContext
from Products.ZenEvents.ZenEventClasses import Capacity

import logging
log = logging.getLogger('zen.TrendlineThreshold')

PREDICTION_TIME_UNITS = ['days', 'weeks', 'months']
PREDICTION_ALGORITHMS = ['linear']

class TrendlineThreshold(MinMaxThreshold):
    """
    Threshold class that alerts against predicted values
    """
    meta_type = "TrendlineThreshold"

    eventClass = Capacity
    # default to info since the prediction is unreliable
    severity = 2

    # amount of time of data we want to use in our prediction
    pastData = 10 # the type is string for TALES interpretation
    pastDataUnits = PREDICTION_TIME_UNITS[0]

    # how far to calculate the prediction to see if we cross the threshold
    amountToPredict = 10 # the type is string for TALES interpretation
    amountToPredictUnits = PREDICTION_TIME_UNITS[0]

    predictionAlgorithm = PREDICTION_ALGORITHMS[0]

    _properties = MinMaxThreshold._properties + (
        {'id':'pastData', 'type':'integer',  'mode':'w'},
        {'id':'pastDataUnits', 'type':'string',  'mode':'w'},
        {'id':'amountToPredict', 'type':'integer',  'mode':'w'},
        {'id':'amountToPredictUnits', 'type':'string',  'mode':'w'},
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
                                      escalateCount=0,
                                      eventFields=self.getEventFields(context),
              )
        return mmt



InitializeClass(TrendlineThreshold)


class TrendlineThresholdInstance(MinMaxThresholdInstance):
    pass


from twisted.spread import pb
pb.setUnjellyableForClass(TrendlineThresholdInstance, TrendlineThresholdInstance)
