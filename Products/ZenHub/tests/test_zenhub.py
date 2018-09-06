from unittest import TestCase
from mock import Mock, patch, create_autospec

from zope.interface.verify import verifyObject

# Breaks test isolation ImportError: No module named Globals
from Products.ZenHub.zenhub import (
    AuthXmlRpcService,
    XmlRpcService,
    HubAvitar,
    RemoteBadMonitor,
    pb,
    ServiceAddedEvent,
    IServiceAddedEvent,
    HubWillBeCreatedEvent,
    IHubWillBeCreatedEvent,
    HubCreatedEvent,
    IHubCreatedEvent,
    ParserReadyForOptionsEvent,
    IParserReadyForOptionsEvent,
    _ZenHubWorklist,
    publisher,
    redisPublisher,
    metricWriter,
)

PATH = {'src': 'Products.ZenHub.zenhub'}


class AuthXmlRpcServiceTest(TestCase):

    def setUp(t):
        t.dmd = Mock(name='dmd', spec_set=['ZenEventManager'])
        t.checker = Mock(name='checker', spec_set=['requestAvatarId'])

        t.axrs = AuthXmlRpcService(t.dmd, t.checker)

    @patch('{src}.XmlRpcService.__init__'.format(**PATH), autospec=True)
    def test___init__(t, XmlRpcService__init__):
        dmd = Mock(name='dmd', spec_set=[])
        checker = Mock(name='checker', spec_set=[])

        axrs = AuthXmlRpcService(dmd, checker)

        XmlRpcService__init__.assert_called_with(axrs, dmd)
        t.assertEqual(axrs.checker, checker)

    def test_doRender(t):
        '''should be refactored to call self.render,
        instead of the parrent class directly
        '''
        render = create_autospec(XmlRpcService.render, name='render')
        XmlRpcService.render = render
        request = Mock(name='request', spec_set=[])

        ret = t.axrs.doRender('unused arg', request)

        XmlRpcService.render.assert_called_with(t.axrs, request)
        t.assertEqual(ret, render.return_value)

    @patch('{src}.xmlrpc'.format(**PATH), name='xmlrpc', autospec=True)
    def test_unauthorized(t, xmlrpc):
        request = Mock(name='request', spec_set=[])
        t.axrs._cbRender = create_autospec(t.axrs._cbRender)

        t.axrs.unauthorized(request)

        xmlrpc.Fault.assert_called_with(t.axrs.FAILURE, 'Unauthorized')
        t.axrs._cbRender.assert_called_with(xmlrpc.Fault.return_value, request)

    @patch('{src}.server'.format(**PATH), name='server', autospec=True)
    @patch(
        '{src}.credentials'.format(**PATH), name='credentials', autospec=True
    )
    def test_render(t, credentials, server):
        request = Mock(name='request', spec_set=['getHeader'])
        auth = Mock(name='auth', spec_set=['split'])
        encoded = Mock(name='encoded', spec_set=['decode'])
        encoded.decode.return_value.split.return_value = ('user', 'password')
        auth.split.return_value = ('Basic', encoded)

        request.getHeader.return_value = auth

        ret = t.axrs.render(request)

        request.getHeader.assert_called_with('authorization')
        encoded.decode.assert_called_with('base64')
        encoded.decode.return_value.split.assert_called_with(':')
        credentials.UsernamePassword.assert_called_with('user', 'password')
        t.axrs.checker.requestAvatarId.assert_called_with(
            credentials.UsernamePassword.return_value
        )
        deferred = t.axrs.checker.requestAvatarId.return_value
        deferred.addCallback.assert_called_with(t.axrs.doRender, request)

        t.assertEqual(ret, server.NOT_DONE_YET)


class HubAvitarTest(TestCase):

    def setUp(t):
        t.hub = Mock(name='hub', spec_set=['getService', 'log', 'workers'])
        t.avitar = HubAvitar(t.hub)

    def test___init__(t):
        t.assertEqual(t.avitar.hub, t.hub)

    def test_perspective_ping(t):
        ret = t.avitar.perspective_ping()
        t.assertEqual(ret, 'pong')

    @patch('{src}.os.environ'.format(**PATH), name='os.environ', autospec=True)
    def test_perspective_getHubInstanceId(t, os_environ):
        ret = t.avitar.perspective_getHubInstanceId()
        os_environ.get.assert_called_with(
            'CONTROLPLANE_INSTANCE_ID', 'Unknown'
        )
        t.assertEqual(ret, os_environ.get.return_value)

    def test_perspective_getService(t):
        service_name = 'serviceName'
        instance = 'collector_instance_name'
        listener = Mock(name='listener', spec_set=[])
        options = Mock(name='options', spec_set=[])
        service = t.hub.getService.return_value

        ret = t.avitar.perspective_getService(
            service_name, instance=instance,
            listener=listener, options=options
        )

        t.hub.getService.assert_called_with(service_name, instance)
        service.addListener.assert_called_with(listener, options)
        t.assertEqual(ret, service)

    def test_perspective_getService_raises_RemoteBadMonitor(t):
        t.hub.getService.side_effect = RemoteBadMonitor('tb', 'msg')
        with t.assertRaises(RemoteBadMonitor):
            t.avitar.perspective_getService('service_name')

    def test_perspective_reportingForWork(t):
        worker = Mock(pb.RemoteReference, autospec=True)
        pid = 9999
        t.hub.workers = []

        t.avitar.perspective_reportingForWork(worker, pid=pid)

        t.assertFalse(worker.busy)
        t.assertEqual(worker.pid, pid)
        t.assertIn(worker, t.hub.workers)

        # Ugly test for the notifyOnDisconnect method, please refactor
        args, kwargs = worker.notifyOnDisconnect.call_args
        removeWorker = args[0]

        removeWorker(worker)
        t.assertNotIn(worker, t.hub.workers)


class ServiceAddedEventTest(TestCase):
    def test___init__(t):
        name, instance = 'name', 'instance'
        service_added_event = ServiceAddedEvent(name, instance)
        # the class Implements the Interface
        t.assertTrue(IServiceAddedEvent.implementedBy(ServiceAddedEvent))
        # the object provides the interface
        t.assertTrue(IServiceAddedEvent.providedBy(service_added_event))
        # Verify the object implments the interface properly
        verifyObject(IServiceAddedEvent, service_added_event)

        t.assertEqual(service_added_event.name, name)
        t.assertEqual(service_added_event.instance, instance)


class HubWillBeCreatedEventTest(TestCase):
    def test__init__(t):
        hub = Mock(name='zenhub_instance', spec_set=[])
        event = HubWillBeCreatedEvent(hub)
        # the class Implements the Interface
        t.assertTrue(
            IHubWillBeCreatedEvent.implementedBy(HubWillBeCreatedEvent)
        )
        # the object provides the interface
        t.assertTrue(IHubWillBeCreatedEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IHubWillBeCreatedEvent, event)

        t.assertEqual(event.hub, hub)


class HubCreatedEventTest(TestCase):
    def test__init__(t):
        hub = Mock(name='zenhub_instance', spec_set=[])
        event = HubCreatedEvent(hub)
        # the class Implements the Interface
        t.assertTrue(
            IHubCreatedEvent.implementedBy(HubCreatedEvent)
        )
        # the object provides the interface
        t.assertTrue(IHubCreatedEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IHubCreatedEvent, event)

        t.assertEqual(event.hub, hub)


class ParserReadyForOptionsEventTest(TestCase):
    def test__init__(t):
        parser = Mock(name='parser', spec_set=[])
        event = ParserReadyForOptionsEvent(parser)
        # the class Implements the Interface
        t.assertTrue(
            IParserReadyForOptionsEvent.implementedBy(
                ParserReadyForOptionsEvent
            )
        )
        # the object provides the interface
        t.assertTrue(IParserReadyForOptionsEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IParserReadyForOptionsEvent, event)

        t.assertEqual(event.parser, parser)


class _ZenHubWorklistTest(TestCase):

    def setUp(t):
        t.wl = _ZenHubWorklist()

    def test____init__(t):
        t.assertEqual(
            t.wl.eventPriorityList,
            [t.wl.eventworklist, t.wl.otherworklist, t.wl.applyworklist]
        )
        t.assertEqual(
            t.wl.otherPriorityList,
            [t.wl.otherworklist, t.wl.applyworklist, t.wl.eventworklist]
        )
        t.assertEqual(
            t.wl.applyPriorityList,
            [t.wl.applyworklist, t.wl.eventworklist, t.wl.otherworklist]
        )
        t.assertEqual(
            t.wl.dispatch,
            {
                'sendEvents': t.wl.eventworklist,
                'sendEvent': t.wl.eventworklist,
                'applyDataMaps': t.wl.applyworklist
            }
        )

    def test___getitem__(t):
        '''zenhub_worker_list[dispatch] uses the dispatch dict to
        map 'sendEvents', 'sendEvent', 'applyDataMaps' keys to worklists
        '''
        wl = _ZenHubWorklist()
        t.assertEqual(wl['sendEvents'], t.wl.eventworklist)
        t.assertEqual(wl['sendEvent'], t.wl.eventworklist)
        t.assertEqual(wl['applyDataMaps'], t.wl.applyworklist)
        t.assertEqual(wl['anything else'], t.wl.otherworklist)

    def test___len__(t):
        '''len(zenhub_worker_list) returns the sum of all work lists
        '''
        t.wl.eventworklist = range(1)
        t.wl.applyworklist = range(2)
        t.wl.otherworklist = range(4)
        t.assertEqual(len(t.wl), 7)

    def test_push(t):
        other = Mock(
            name='apply_datamap', spec_set=['method'], method='other'
        )
        t.wl.push(other)
        t.assertEqual(t.wl.otherworklist, [other])

    def test_push_sendEvent(t):
        send_event = Mock(
            name='send_event', spec_set=['method'], method='sendEvent'
        )
        t.wl.push(send_event)
        t.assertEqual(t.wl['sendEvent'], [send_event])

    def test_push_sendEvents(t):
        send_events = Mock(
            name='send_events', spec_set=['method'], method='sendEvents'
        )
        t.wl.push(send_events)
        t.assertEqual(t.wl['sendEvents'], [send_events])

    def test_push_applyDataMaps(t):
        apply_datamap = Mock(
            name='apply_datamap', spec_set=['method'], method='applyDataMaps'
        )
        t.wl.push(apply_datamap)
        t.assertEqual(t.wl['applyDataMaps'], [apply_datamap])

    def test_append(t):
        t.assertEqual(t.wl.append, t.wl.push)

    def test_pop(t):
        '''randomizes selection from lists in an attempt to weight and balance
        item selection. with an option to ignore the applyDataMaps queue.
        current implementation is highly inefficient.
        current logic will not apply weighing properly if allowADM=False.
        cannot set random.seed('static'), random was not imported

        Should be reviewed and refactored.
        '''
        job_a = Mock(name='job_a', spec_set=['method'], method='sendEvent')

        t.wl.push(job_a)

        ret = t.wl.pop()
        t.assertEqual(ret, job_a)
        ret = t.wl.pop()
        t.assertEqual(ret, None)


class ZenHubModuleTest(TestCase):

    @patch('{src}.HttpPostPublisher'.format(**PATH), autospec=True)
    def test_publisher(t, HttpPostPublisher):
        ret = publisher('username', 'password', 'url')
        HttpPostPublisher.assert_called_with('username', 'password', 'url')
        t.assertEqual(ret, HttpPostPublisher.return_value)

    @patch('{src}.RedisListPublisher'.format(**PATH), autospec=True)
    def test_redisPublisher(t, RedisListPublisher):
        ret = redisPublisher()
        RedisListPublisher.assert_called_with()
        t.assertEqual(ret, RedisListPublisher.return_value)

    @patch('{src}.AggregateMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.FilteredMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.publisher'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.redisPublisher'.format(**PATH), autospec=True)
    @patch('{src}.MetricWriter'.format(**PATH), autospec=True)
    def test_metricWriter(
        t,
        MetricWriter,
        redisPublisher,
        os,
        publisher,
        FilteredMetricWriter,
        AggregateMetricWriter
    ):
        '''Returns an initialized MetricWriter instance,
        should probably be refactored into its own class
        '''
        os.environ = {
            'CONTROLPLANE': '1',
            'CONTROLPLANE_CONSUMER_URL': 'consumer_url',
            'CONTROLPLANE_CONSUMER_USERNAME': 'consumer_username',
            'CONTROLPLANE_CONSUMER_PASSWORD': 'consumer_password',
        }

        ret = metricWriter()

        MetricWriter.assert_called_with(redisPublisher.return_value)
        publisher.assert_called_with(
            os.environ['CONTROLPLANE_CONSUMER_USERNAME'],
            os.environ['CONTROLPLANE_CONSUMER_PASSWORD'],
            os.environ['CONTROLPLANE_CONSUMER_URL'],
        )
        AggregateMetricWriter.assert_called_with(
            [MetricWriter.return_value, FilteredMetricWriter.return_value]
        )
        t.assertEqual(ret, AggregateMetricWriter.return_value)


class ZenHubTest(TestCase):

    def test___init__(t):
        pass
