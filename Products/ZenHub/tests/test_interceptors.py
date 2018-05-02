from unittest import TestCase
from mock import Mock

from Products.ZenHub.interceptors import (
    WorkerInterceptor,
    pb,
    pickle,
)


class WorkerInterceptorTest(TestCase):

    cap_broker = '<twisted.spread.pb.Broker instance at 0xa198680>'
    cap_message = 'sendEvents'
    cap_args = [
        'tuple',
        ['list',
            ['dictionary',
                ['monitor', 'localhost'],
                ['component', 'zenstatus'],
                ['agent', 'zenstatus'],
                ['manager', '550b82acdec1'],
                ['timeout', 900],
                ['device', 'localhost'],
                ['eventClass', '/Heartbeat']
    ]]]
    cap_kw = ['dictionary']

    def test_remoteMessageReceived(self):
        service = Mock(name='service')
        service.__class__ = 'Products.ZenHub.services.EventService.EventService'

        zenhub = Mock(name='zenhub instance')
        wi = WorkerInterceptor(zenhub=zenhub, service=service)
        wi.perspective = Mock(spec=pb.IPerspective)

        broker = Mock(spec=pb.Broker)

        svc = str(service.__class__).rpartition('.')[0]
        self.assertEqual(svc, 'Products.ZenHub.services.EventService')

        # unserialize args
        cap_args = [
            'tuple',
            ['list',
                ['dictionary',
                    ['monitor', 'localhost'],
                    ['component', 'zenstatus'],
                    ['agent', 'zenstatus'],
                    ['manager', '550b82acdec1'],
                    ['timeout', 900],
                    ['device', 'localhost'],
                    ['eventClass', '/Heartbeat']
        ]]]
        unserialized_args = ([{
            'monitor': 'localhost',
            'component': 'zenstatus',
            'agent': 'zenstatus',
            'manager': '550b82acdec1',
            'timeout': 900,
            'device': 'localhost',
            'eventClass': '/Heartbeat'
        }],)

        broker.unserialize = Mock(return_value=unserialized_args)
        args = broker.unserialize(cap_args)
        self.assertEqual(args, unserialized_args)

        cap_kw = ['dictionary']
        broker.unserialize = Mock(return_value={})
        kw = broker.unserialize(cap_kw)
        broker.unserialize.assert_called_with(cap_kw)
        self.assertEqual(kw, {})

        pickledArgs = pickle.dumps(
            (args, kw), pickle.HIGHEST_PROTOCOL
        )

        self.assertEqual(
            pickledArgs,
            '\x80\x02]q\x01}q\x02(U\x07monitorq\x03U\tlocalhostq\x04U\tcomponentq\x05U\tzenstatusq\x06U\x05agentq\x07h\x06U\x07managerq\x08U\x0c550b82acdec1q\tU\x07timeoutq\nM\x84\x03U\x06deviceq\x0bh\x04U\neventClassq\x0cU\n/Heartbeatq\rua\x85q\x0e}q\x0f\x86.'
        )

        chunkedArgs = []
        chunkSize = 102400
        while pickledArgs:
            chunk = pickledArgs[:chunkSize]
            chunkedArgs.append(chunk)
            pickledArgs = pickledArgs[chunkSize:]

        self.assertEqual(
            chunkedArgs,
            [pickle.dumps((args, kw), pickle.HIGHEST_PROTOCOL)]
        )

        out = wi.remoteMessageReceived(
            broker=broker,  # '<twisted.spread.pb.Broker instance at 0xb1a72d8>',
            message='sendEvents',
            args=[],
            kw=['dictionary'],
        )

        self.assertEqual(out, broker.serialize.return_value)
        broker.serialize.assert_called_with(
            zenhub.deferToWorker.return_value, wi.perspective
        )
