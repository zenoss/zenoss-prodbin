
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

    def remoteMessageReceived(self, broker, message, args, kw):
        """Intercept requests and send them down to workers"""
        self.log.error('remoteMessageReceived(self, broker, message, args, kw):'
                  ' broker=%s, message=%s, args=%s, kw=%s',
                  broker, message, args, kw)

        self._serviceCalls.mark()
        self.log.error('self.service.__class__=%s', self.service.__class__)
        svc = str(self.service.__class__).rpartition('.')[0]
        self.log.error('svc=%s', svc)
        instance = self.service.instance
        self.log.error('instance=%s', instance)
        args = broker.unserialize(args)
        self.log.error('args=%s', args)
        kw = broker.unserialize(kw)
        self.log.error('kw=%s', kw)
        # hide the types in the args: subverting the jelly protection mechanism
        # but the types just passed through and the worker may not have loaded
        # the required service before we try passing types for that service
        # PB has a 640k limit, not bytes but len of sequences. When args are
        # pickled the resulting string may be larger than 640k, split into
        # 100k chunks
        pickledArgs = pickle.dumps(
            (args, kw), pickle.HIGHEST_PROTOCOL
        )
        chunkedArgs = []
        chunkSize = 102400
        while pickledArgs:
            chunk = pickledArgs[:chunkSize]
            chunkedArgs.append(chunk)
            pickledArgs = pickledArgs[chunkSize:]

        start = time()

        def recordTime(result):
            # get in milliseconds
            duration = int((time() - start) * 1000)
            self._admTimer.update(duration)
            return result

        deferred = self.zenhub.deferToWorker(
            svc, instance, message, chunkedArgs
        )
        if message == 'sendEvents':
            if args and len(args) == 1:
                self._eventsSent.mark(len(args[0]))
        elif message == 'sendEvent':
            self._eventsSent.mark()
        elif message == 'applyDataMaps':
            deferred.addCallback(recordTime)

        return broker.serialize(deferred, self.perspective)

    def remoteMessageReceived_monkey_patch(self, broker, message, args, kw):
        # Short circuit sendEvent() calls

        if message not in ('sendEvents', 'sendEvent'):
            #return original(self, broker, message, args, kw)
            return self.remoteMessageReceived(broker, message, args, kw)

        args = broker.unserialize(args)
        if message == 'sendEvents':
            self.zem.sendEvents(*args)
        elif message == 'sendEvent':
            self.zem.sendEvent(*args)

        return broker.serialize(defer.succeed("Events sent"), self.perspective)

    def __getattr__(self, attr):
        """Implement the HubService interface
        by forwarding to the local service
        """
        return getattr(self.service, attr)
