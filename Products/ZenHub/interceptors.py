##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import cPickle as pickle
from time import time

from metrology import Metrology
from twisted.spread import pb
from twisted.internet import defer


class WorkerInterceptor(pb.Referenceable):
    """Redirect service requests to one of the worker processes. Note
    that everything else (like change notifications) go through
    locally hosted services."""

    callTime = 0.

    def __init__(self, zenhub, service):
        self.zenhub = zenhub
        self.service = service
        self._serviceCalls = Metrology.meter("zenhub.serviceCalls")
        self.log = logging.getLogger('zen.zenhub.WorkerInterceptor')
        self._admTimer = Metrology.timer('zenhub.applyDataMap')
        self._eventsSent = Metrology.meter("zenhub.eventsSent")

        self.meters = {
            'sendEvent': self.mark_send_event_timer,
            'sendEvents': self.mark_send_events_timer,
            'applyDataMaps': self.mark_apply_datamaps_timer,
        }

    @defer.inlineCallbacks
    def remoteMessageRecieved(self, broker, message, args, kw):
        try:
            start = time()

            if message in ('sendEvent', 'sendEvents'):
                xargs = broker.unserialize(args)
                method = getattr(self.zenhub.zem, message, None)
                state = yield method(xargs)

            else:
                state = yield self.zenhub.deferToWorker(
                    self.service_name,
                    self.service.instance,
                    message,
                    self.serialize_args(args, kw)
                )

            if message in self.meters:
                self.meters[message](args, start)

            defer.returnValue(
                broker.serialize(state, self.perspective)
            )
        except Exception:
            self.log.exception('Failed to handle remote procedure call')

    @property
    def service_name(self):
        return str(self.service.__class__).rpartition('.')[0]

    def serialize_args(self, args, kwargs):
        pargs = pickle.dumps((args, kwargs), pickle.HIGHEST_PROTOCOL)
        size = 102400
        return [pargs[i:i + size] for i in xrange(0, len(pargs), size)]

    def mark_send_event_timer(self, events, start):
        self._eventsSent.mark()

    def mark_send_events_timer(self, events, start):
        self._eventsSent.mark(len(events))

    def mark_apply_datamaps_timer(self, events, start):
        self._admTimer.update(int((time() - start) * 1000))

    def __getattr__(self, attr):
        """Implement the HubService interface
        by forwarding to the local service
        """
        return getattr(self.service, attr)
