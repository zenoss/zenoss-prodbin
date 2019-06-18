
import logging

from unittest import TestCase
from mock import Mock, patch, create_autospec, call

from zope.interface.verify import verifyObject

# Breaks Test Isolation. Products/ZenHub/metricpublisher/utils.py:15
# ImportError: No module named eventlet
from Products.ZenHub.PBDaemon import (
    RemoteException,
    RemoteConflictError,
    RemoteBadMonitor,
    pb,
    translateError,
    ConflictError,
    DefaultFingerprintGenerator,
    ICollectorEventFingerprintGenerator,
    sha1,
    _load_utilities,
    BaseEventQueue,
    collections,
    DequeEventQueue,
    DeDupingEventQueue,
    EventQueueManager,
    TRANSFORM_DROP,
    TRANSFORM_STOP,
    Clear,
    defer,
    PBDaemon,
)
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

PATH = {'src': 'Products.ZenHub.PBDaemon'}


class RemoteExceptionsTest(TestCase):
    '''These exceptions can probably be moved into their own module
    '''

    def test_raise_RemoteException(t):
        with t.assertRaises(RemoteException):
            raise RemoteException('message', 'traceback')

    def test_RemoteException_is_pb_is_copyable(t):
        t.assertTrue(issubclass(RemoteException, pb.Copyable))
        t.assertTrue(issubclass(RemoteException, pb.RemoteCopy))

    def test_raise_RemoteConflictError(t):
        with t.assertRaises(RemoteConflictError):
            raise RemoteConflictError('message', 'traceback')

    def test_RemoteConflictError_is_pb_is_copyable(t):
        t.assertTrue(issubclass(RemoteConflictError, pb.Copyable))
        t.assertTrue(issubclass(RemoteConflictError, pb.RemoteCopy))

    def test_raise_RemoteBadMonitor(t):
        with t.assertRaises(RemoteBadMonitor):
            raise RemoteBadMonitor('message', 'traceback')

    def test_RemoteBadMonitor_is_pb_is_copyable(t):
        t.assertTrue(issubclass(RemoteBadMonitor, pb.Copyable))
        t.assertTrue(issubclass(RemoteBadMonitor, pb.RemoteCopy))

    def test_translateError_transforms_ConflictError(t):
        traceback = Mock(spec_set=['_p_oid'])

        @translateError
        def raise_conflict_error():
            raise ConflictError('message', traceback)

        with t.assertRaises(RemoteConflictError):
            raise_conflict_error()

    def test_translateError_transforms_Exception(t):

        @translateError
        def raise_error():
            raise Exception('message', 'traceback')

        with t.assertRaises(RemoteException):
            raise_error()


class DefaultFingerprintGeneratorTest(TestCase):

    def test_init(t):
        fingerprint_generator = DefaultFingerprintGenerator()

        # the class Implements the Interface
        t.assertTrue(
            ICollectorEventFingerprintGenerator.
            implementedBy(DefaultFingerprintGenerator)
        )
        # the object provides the interface
        t.assertTrue(
            ICollectorEventFingerprintGenerator.
            providedBy(fingerprint_generator)
        )
        # Verify the object implments the interface properly
        verifyObject(
            ICollectorEventFingerprintGenerator, fingerprint_generator
        )

    def test_generate(t):
        '''Takes an event, chews it up and spits out a sha1 hash
        without an intermediate function that returns its internal fields list
        we have to duplicate the entire function in test.
        REFACTOR: split this up so we can test the fields list generator
        and sha generator seperately.
        Any method of generating the a hash from the dict should work so long
        as its the same hash for the event with the _IGNORE_FILEDS stripped off
        '''
        event = {'k%s' % i: 'v%s' % i for i in range(3)}
        fields = []
        for k, v in sorted(event.iteritems()):
            fields.extend((k, v))
        expected = sha1('|'.join(fields)).hexdigest()

        # any keys listed in _IGNORE_FIELDS are not hashed
        for key in DefaultFingerprintGenerator._IGNORE_FIELDS:
            event[key] = 'IGNORE ME!'

        fingerprint_generator = DefaultFingerprintGenerator()
        out = fingerprint_generator.generate(event)

        t.assertEqual(out, expected)


class load_utilities_Test(TestCase):

    @patch('{src}.getUtilitiesFor'.format(**PATH), autospec=True)
    def test_load_utilities(t, getUtilitiesFor):
        ICollectorEventTransformer = 'some transform function'

        def func1():
            pass

        def func2():
            pass

        func1.weight = 100
        func2.weight = 50
        getUtilitiesFor.return_value = (('func1', func1), ('func2', func2))

        ret = _load_utilities(ICollectorEventTransformer)

        getUtilitiesFor.assert_called_with(ICollectorEventTransformer)
        # NOTE: lower weight comes first in the sorted list
        # Is this intentional?
        t.assertEqual(ret, [func2, func1])


class BaseEventQueueTest(TestCase):

    def setUp(t):
        t.beq = BaseEventQueue(maxlen=5)

    def test_init(t):
        base_event_queue = BaseEventQueue(maxlen=5)
        t.assertEqual(base_event_queue.maxlen, 5)

    def test_append(t):
        with t.assertRaises(NotImplementedError):
            t.beq.append('event')

    def test_popleft(t):
        with t.assertRaises(NotImplementedError):
            t.beq.popleft()

    def test_extendleft(t):
        with t.assertRaises(NotImplementedError):
            t.beq.extendleft(['event_a', 'event_b'])

    def test___len__(t):
        with t.assertRaises(NotImplementedError):
            len(t.beq)

    def test___iter__(t):
        with t.assertRaises(NotImplementedError):
            [i for i in t.beq]


class DequeEventQueueTest(TestCase):

    def setUp(t):
        t.deq = DequeEventQueue(maxlen=10)
        t.event_a, t.event_b = {'name': 'event_a'}, {'name': 'event_b'}

    def test_init(t):
        maxlen = 100
        deq = DequeEventQueue(maxlen=maxlen)
        t.assertEqual(deq.maxlen, maxlen)
        t.assertIsInstance(deq.queue, collections.deque)

    @patch('{src}.time'.format(**PATH))
    def test_append(t, time):
        event = {}
        deq = DequeEventQueue(maxlen=10)

        ret = deq.append(event)

        # append sets the time the event was added to the queue
        t.assertEqual(event['rcvtime'], time.time())
        t.assertEqual(ret, None)

    def test_append_pops_and_returns_leftmost_if_full(t):
        event_a, event_b = {'name': 'event_a'}, {'name': 'event_b'}
        deq = DequeEventQueue(maxlen=1)

        deq.append(event_a)
        ret = deq.append(event_b)

        t.assertIn(event_b, deq.queue)
        t.assertNotIn(event_a, deq.queue)
        t.assertEqual(ret, event_a)

    @patch('{src}.time'.format(**PATH))
    def test_popleft(t, time):
        t.deq.append(t.event_a)
        t.deq.append(t.event_b)

        ret = t.deq.queue.popleft()

        t.assertEqual(ret, t.event_a)

    def test_base_popleft(t):
        t.deq.queue.append('a')
        t.deq.queue.append('b')

        ret = t.deq.queue.popleft()
        t.assertEqual(ret, 'a')

    @patch('{src}.time'.format(**PATH))
    def test_extendleft(t, time):
        '''WARNING: extendleft does NOT add timestamps, as .append does
        is this behavior is intentional?
        '''
        event_c = {'name': 'event_c'}
        t.deq.append(event_c)
        t.assertEqual(list(t.deq), [event_c])
        events = [t.event_a, t.event_b]

        ret = t.deq.extendleft(events)

        t.assertEqual(ret, [])
        t.assertEqual(list(t.deq), [t.event_a, t.event_b, event_c])
        '''
        # to validate all events get timestamps
        t.assertEqual(
            list(t.deq),
            [{'name': 'event_a', 'rcvtime': time.time.return_value},
             {'name': 'event_b', 'rcvtime': time.time.return_value},
             {'name': 'event_c', 'rcvtime': time.time.return_value},
            ]
        '''

    def test_extendleft_returns_events_if_falsey(t):
        ret = t.deq.extendleft(False)
        t.assertEqual(ret, False)
        ret = t.deq.extendleft([])
        t.assertEqual(ret, [])
        ret = t.deq.extendleft(0)
        t.assertEqual(ret, 0)

    def test_extendleft_returns_extra_events_if_nearly_full(t):
        t.deq.maxlen = 3
        t.deq.extendleft([t.event_a, t.event_b])
        event_c, event_d = {'name': 'event_c'}, {'name': 'event_d'}
        events = [event_c, event_d]

        ret = t.deq.extendleft(events)

        t.assertEqual(list(t.deq), [event_d, t.event_a, t.event_b])
        t.assertEqual(ret, [event_c])

    def test___len__(t):
        ret = len(t.deq)
        t.assertEqual(ret, 0)
        t.deq.extendleft([t.event_a, t.event_b])
        t.assertEqual(len(t.deq), 2)

    def test___iter__(t):
        t.deq.extendleft([t.event_a, t.event_b])
        ret = [event for event in t.deq]
        t.assertEqual(ret, [t.event_a, t.event_b])


class DeDupingEventQueueTest(TestCase):

    def setUp(t):
        t.ddeq = DeDupingEventQueue(maxlen=10)
        t.event_a, t.event_b = {'name': 'event_a'}, {'name': 'event_b'}

    @patch('{src}._load_utilities'.format(**PATH))
    def test_init(t, _load_utilities):
        ddeq = DeDupingEventQueue(maxlen=10)
        t.assertEqual(ddeq.maxlen, 10)

        t.assertIsInstance(
            ddeq.default_fingerprinter, DefaultFingerprintGenerator
        )
        t.assertEqual(ddeq.fingerprinters, _load_utilities.return_value)
        t.assertIsInstance(ddeq.queue, collections.OrderedDict)

    def test_event_fingerprint(t):
        t.ddeq.fingerprinters = []

        ret = t.ddeq._event_fingerprint(t.event_a)
        expected = DefaultFingerprintGenerator().generate(t.event_a)
        t.assertEqual(ret, expected)

        # Identical events generate the same fingerprint
        event_2 = t.event_a.copy()
        ret = t.ddeq._event_fingerprint(event_2)
        t.assertEqual(ret, expected)

    def test_event_fingerprint_fingerprinters_list(t):
        '''_event_fingerprint will attempt to generate a fingerprint from
        each ICollectorEventFingerprintGenerator it loaded,
        and return the first non-falsey value from them
        '''
        fp1 = Mock(spec_set=['generate'])
        fp1.generate.return_value = None
        fp2 = Mock(spec_set=['generate'])
        fp2.generate.side_effect = lambda x: str(x)
        # fp2 returns a value, so fp3 is never called
        fp3 = Mock(spec_set=['generate'])
        fp3.generate.side_effect = lambda x: 1 / 0

        t.ddeq.fingerprinters = [fp1, fp2, fp3]

        ret = t.ddeq._event_fingerprint(t.event_a)

        fp1.generate.assert_called_with(t.event_a)
        fp2.generate.assert_called_with(t.event_a)
        fp3.generate.assert_not_called()
        t.assertEqual(ret, str(t.event_a))

    def test_first_time(t):
        '''given 2 events, retrun the earliest timestamp of the two
        use 'firstTime' if available, else 'rcvtime'
        '''
        event1 = {'firstTime': 1, 'rcvtime': 0}
        event2 = {'rcvtime': 2}

        ret = t.ddeq._first_time(event1, event2)
        t.assertEqual(ret, 1)

        event1 = {'firstTime': 3, 'rcvtime': 1}
        event2 = {'rcvtime': 2}

        ret = t.ddeq._first_time(event1, event2)
        t.assertEqual(ret, 2)

    @patch('{src}.time'.format(**PATH))
    def test_append_timestamp(t, time):
        '''Make sure every processed event specifies the time it was queued.
        '''
        t.ddeq.append(t.event_a)
        event = t.ddeq.popleft()

        t.assertEqual(event['rcvtime'], time.time.return_value)

    @patch('{src}.time'.format(**PATH))
    def test_append_deduplication(t, time):
        '''The same event cannot be added to the queue twice
        appending a duplicate event replaces the original
        '''
        event1 = {'data': 'some data'}
        event2 = {'data': 'some data'}
        t.assertEqual(event1, event2)

        t.ddeq.append(event1)
        t.ddeq.append(event2)

        t.assertEqual(len(t.ddeq), 1)

        ret = t.ddeq.popleft()
        # The new event replaces the old one
        t.assertIs(ret, event2)
        t.assertEqual(event2['count'], 2)

    @patch('{src}.time'.format(**PATH))
    def test_append_deduplicates_and_counts_events(t, time):
        time.time.side_effect = (t for t in range(100))
        t.ddeq.append({'name': 'event_a'})
        t.assertEqual(list(t.ddeq), [{'rcvtime': 0, 'name': 'event_a'}])
        t.ddeq.append({'name': 'event_a'})
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 1, 'firstTime': 0, 'count': 2, 'name': 'event_a'}]
        )
        t.ddeq.append({'name': 'event_a'})
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 2, 'firstTime': 0, 'count': 3, 'name': 'event_a'}]
        )
        t.ddeq.append({'name': 'event_a'})
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 3, 'firstTime': 0, 'count': 4, 'name': 'event_a'}]
        )

    def test_append_pops_and_returns_leftmost_if_full(t):
        t.ddeq.maxlen = 1

        t.ddeq.append(t.event_a)
        ret = t.ddeq.append(t.event_b)

        # NOTE: events are stored in a dict, key=fingerprint
        t.assertIn(t.ddeq._event_fingerprint(t.event_b), t.ddeq.queue)
        t.assertNotIn(t.ddeq._event_fingerprint(t.event_a), t.ddeq.queue)
        t.assertEqual(ret, t.event_a)

    def test_popleft(t):
        t.ddeq.append(t.event_a)
        t.ddeq.append(t.event_b)

        ret = t.ddeq.popleft()

        t.assertEqual(ret, t.event_a)

    def test_popleft_raises_IndexError(t):
        '''Raises IndexError instead of KeyError, for api compatability
        '''
        with t.assertRaises(IndexError):
            t.ddeq.popleft()

    @patch('{src}.time'.format(**PATH))
    def test_extendleft(t, time):
        '''WARNING: extendleft does NOT add timestamps, as .append does
        is this behavior is intentional?
        '''
        event_c = {'name': 'event_c'}
        t.ddeq.append(event_c)
        t.assertEqual(list(t.ddeq), [event_c])
        events = [t.event_a, t.event_b]

        ret = t.ddeq.extendleft(events)

        t.assertEqual(ret, [])
        t.assertEqual(list(t.ddeq), [t.event_a, t.event_b, event_c])
        '''
        # to validate all events get timestamps
        t.assertEqual(
            list(t.ddeq),
            [{'name': 'event_a', 'rcvtime': time.time.return_value},
             {'name': 'event_b', 'rcvtime': time.time.return_value},
             {'name': 'event_c', 'rcvtime': time.time.return_value},
            ]
        )
        '''

    @patch('{src}.time'.format(**PATH))
    def test_extendleft_counts_events_BUG(t, time):
        time.time.side_effect = (t for t in range(100))
        t.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        t.assertEqual(
            list(t.ddeq),
            # This should work
            # [{'rcvtime': 0, 'name': 'event_a'}]
            # current behavior
            [{'name': 'event_a'}, {'name': 'event_b'}]
        )
        # rcvtime is required, but is not set by extendleft
        with t.assertRaises(KeyError):
            t.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        '''
        Test Breaks Here due to missing rcvtime
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 1, 'firstTime': 0, 'count': 2, 'name': 'event_a'},
             {'rcvtime': 1, 'firstTime': 0, 'count': 2, 'name': 'event_b'}]
        )
        t.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 2, 'firstTime': 0, 'count': 3, 'name': 'event_a'},
             {'rcvtime': 2, 'firstTime': 0, 'count': 3, 'name': 'event_b'}]
        )
        t.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        t.assertEqual(
            list(t.ddeq),
            [{'rcvtime': 3, 'firstTime': 0, 'count': 4, 'name': 'event_a'},
             {'rcvtime': 3, 'firstTime': 0, 'count': 4, 'name': 'event_b'}]
        )
        '''

    def test_extendleft_returns_events_if_empty(t):
        ret = t.ddeq.extendleft([])
        t.assertEqual(ret, [])

    def test_extendleft_returns_extra_events_if_nearly_full(t):
        t.ddeq.maxlen = 3
        t.ddeq.extendleft([t.event_a, t.event_b])
        event_c, event_d = {'name': 'event_c'}, {'name': 'event_d'}
        events = [event_c, event_d]

        ret = t.ddeq.extendleft(events)

        t.assertEqual(list(t.ddeq), [event_d, t.event_a, t.event_b])
        t.assertEqual(ret, [event_c])

    def test___len__(t):
        ret = len(t.ddeq)
        t.assertEqual(ret, 0)
        t.ddeq.extendleft([t.event_a, t.event_b])
        t.assertEqual(len(t.ddeq), 2)

    def test___iter__(t):
        t.ddeq.extendleft([t.event_a, t.event_b])
        ret = [event for event in t.ddeq]
        t.assertEqual(ret, [t.event_a, t.event_b])


class EventQueueManagerTest(TestCase):

    def setUp(t):
        options = Mock(
            name='options',
            spec_set=[
                'maxqueuelen', 'deduplicate_events', 'allowduplicateclears',
                'duplicateclearinterval', 'eventflushchunksize'
            ]
        )
        options.deduplicate_events = True
        log = Mock(name='logger.log', spec_set=['debug', 'warn'])

        t.eqm = EventQueueManager(options, log)
        t.eqm._initQueues()

    def test_initQueues(t):
        options = Mock(
            name='options', spec_set=['maxqueuelen', 'deduplicate_events']
        )
        options.deduplicate_events = True
        log = Mock(name='logger.log', spec_set=[])

        eqm = EventQueueManager(options, log)
        eqm._initQueues()

        t.assertIsInstance(eqm.event_queue, DeDupingEventQueue)
        t.assertEqual(eqm.event_queue.maxlen, options.maxqueuelen)
        t.assertIsInstance(eqm.perf_event_queue, DeDupingEventQueue)
        t.assertEqual(eqm.perf_event_queue.maxlen, options.maxqueuelen)
        t.assertIsInstance(eqm.heartbeat_event_queue, collections.deque)
        t.assertEqual(eqm.heartbeat_event_queue.maxlen, 1)

    def test_transformEvent(t):
        '''a transformer mutates and returns an event
        '''

        def transform(event):
            event['transformed'] = True
            return event

        transformer = Mock(name='transformer', spec_set=['transform'])
        transformer.transform.side_effect = transform
        t.eqm.transformers = [transformer]

        event = {}
        ret = t.eqm._transformEvent(event)

        t.assertEqual(ret, event)
        t.assertEqual(event, {'transformed': True})

    def test_transformEvent_drop(t):
        '''if a transformer returns TRANSFORM_DROP
        stop running the event through transformer, and return None
        '''

        def transform_drop(event):
            return TRANSFORM_DROP

        def transform_bomb(event):
            0 / 0

        transformer = Mock(name='transformer', spec_set=['transform'])
        transformer.transform.side_effect = transform_drop
        transformer_2 = Mock(name='transformer', spec_set=['transform'])
        transformer_2.transform.side_effect = transform_bomb

        t.eqm.transformers = [transformer, transformer_2]

        event = {}
        ret = t.eqm._transformEvent(event)
        t.assertEqual(ret, None)

    def test_transformEvent_stop(t):
        '''if a transformer returns TRANSFORM_STOP
        stop running the event through transformers, and return the event
        '''

        def transform_drop(event):
            return TRANSFORM_STOP

        def transform_bomb(event):
            0 / 0

        transformer = Mock(name='transformer', spec_set=['transform'])
        transformer.transform.side_effect = transform_drop
        transformer_2 = Mock(name='transformer', spec_set=['transform'])
        transformer_2.transform.side_effect = transform_bomb

        t.eqm.transformers = [transformer, transformer_2]

        event = {}
        ret = t.eqm._transformEvent(event)
        t.assertIs(ret, event)

    def test_clearFingerprint(t):
        event = {k: k + '_v' for k in t.eqm.CLEAR_FINGERPRINT_FIELDS}

        ret = t.eqm._clearFingerprint(event)

        t.assertEqual(
            ret, ('device_v', 'component_v', 'eventKey_v', 'eventClass_v')
        )

    def test__removeDiscardedEventFromClearState(t):
        '''if the event's fingerprint is in clear_events_count
        decrement its value
        '''
        t.eqm.options.allowduplicateclears = False
        t.eqm.options.duplicateclearinterval = 0

        discarded = {'severity': Clear}
        clear_fingerprint = t.eqm._clearFingerprint(discarded)
        t.eqm.clear_events_count[clear_fingerprint] = 3

        t.eqm._removeDiscardedEventFromClearState(discarded)

        t.assertEqual(t.eqm.clear_events_count[clear_fingerprint], 2)

    def test__addEvent(t):
        '''remove the event from clear_events_count
        and append it to the queue
        '''
        t.eqm.options.allowduplicateclears = False

        queue = Mock(name='queue', spec_set=['append'])
        event = {}
        clear_fingerprint = t.eqm._clearFingerprint(event)
        t.eqm.clear_events_count = {clear_fingerprint: 3}

        t.eqm._addEvent(queue, event)

        t.assertNotIn(clear_fingerprint, t.eqm.clear_events_count)
        queue.append.assert_called_with(event)

    def test__addEvent_status_clear(t):
        t.eqm.options.allowduplicateclears = False
        t.eqm.options.duplicateclearinterval = 0

        queue = Mock(name='queue', spec_set=['append'])
        event = {'severity': Clear}
        clear_fingerprint = t.eqm._clearFingerprint(event)

        t.eqm._addEvent(queue, event)

        t.assertEqual(t.eqm.clear_events_count[clear_fingerprint], 1)
        queue.append.assert_called_with(event)

    def test__addEvent_drop_duplicate_clear_events(t):
        t.eqm.options.allowduplicateclears = False
        clear_count = 1

        queue = Mock(name='queue', spec_set=['append'])
        event = {'severity': Clear}
        clear_fingerprint = t.eqm._clearFingerprint(event)
        t.eqm.clear_events_count = {clear_fingerprint: clear_count}

        t.eqm._addEvent(queue, event)

        # non-clear events are not added to the clear_events_count dict
        t.assertNotIn(t.eqm.clear_events_count, clear_fingerprint)

        queue.append.assert_not_called()

    def test__addEvent_drop_duplicate_clear_events_interval(t):
        t.eqm.options.allowduplicateclears = False
        clear_count = 3
        t.eqm.options.duplicateclearinterval = clear_count

        queue = Mock(name='queue', spec_set=['append'])
        event = {'severity': Clear}
        clear_fingerprint = t.eqm._clearFingerprint(event)
        t.eqm.clear_events_count = {clear_fingerprint: clear_count}

        t.eqm._addEvent(queue, event)

        # non-clear events are not added to the clear_events_count dict
        t.assertNotIn(t.eqm.clear_events_count, clear_fingerprint)
        queue.append.assert_not_called()

    def test__addEvent_counts_discarded_events(t):
        queue = Mock(name='queue', spec_set=['append'])
        event = {}
        discarded_event = {'name': 'event'}
        queue.append.return_value = discarded_event

        t.eqm._removeDiscardedEventFromClearState = create_autospec(
            t.eqm._removeDiscardedEventFromClearState,
        )
        t.eqm._discardedEvents.mark = create_autospec(
            t.eqm._discardedEvents.mark
        )

        t.eqm._addEvent(queue, event)

        t.eqm._removeDiscardedEventFromClearState.assert_called_with(
            discarded_event
        )
        t.eqm._discardedEvents.mark.assert_called_with()
        t.assertEqual(t.eqm.discarded_events, 1)

    def test_addEvent(t):
        t.eqm._addEvent = create_autospec(t.eqm._addEvent)
        event = {}
        t.eqm.addEvent(event)

        t.eqm._addEvent.assert_called_with(t.eqm.event_queue, event)

    def test_addPerformanceEvent(t):
        t.eqm._addEvent = create_autospec(t.eqm._addEvent)
        event = {}
        t.eqm.addPerformanceEvent(event)

        t.eqm._addEvent.assert_called_with(t.eqm.perf_event_queue, event)

    def test_addHeartbeatEvent(t):
        heartbeat_event_queue = Mock(spec_set=t.eqm.heartbeat_event_queue)
        t.eqm.heartbeat_event_queue = heartbeat_event_queue
        heartbeat_event = {}
        t.eqm.addHeartbeatEvent(heartbeat_event)

        heartbeat_event_queue.append.assert_called_with(heartbeat_event)

    def test_sendEvents(t):
        '''chunks events from EventManager's queues
        yields them to the event_sender_fn
        and returns a deffered with a result of events sent count
        '''
        t.eqm.options.eventflushchunksize = 3
        t.eqm.options.maxqueuelen = 5
        t.eqm._initQueues()
        heartbeat_events = [{'heartbeat': i} for i in range(2)]
        perf_events = [{'perf_event': i} for i in range(2)]
        events = [{'event': i} for i in range(2)]

        t.eqm.heartbeat_event_queue.extendleft(heartbeat_events)
        # heartbeat_event_queue set to static maxlen=1
        t.assertEqual(len(t.eqm.heartbeat_event_queue), 1)
        t.eqm.perf_event_queue.extendleft(perf_events)
        t.eqm.event_queue.extendleft(events)

        event_sender_fn = Mock(name='event_sender_fn')

        ret = t.eqm.sendEvents(event_sender_fn)

        # Priority: heartbeat, perf, event
        event_sender_fn.assert_has_calls(
            [
                call([heartbeat_events[1], perf_events[0], perf_events[1]]),
                call([events[0], events[1]]),
            ]
        )
        t.assertIsInstance(ret, defer.Deferred)
        t.assertEqual(ret.result, 5)

    def test_sendEvents_exception_handling(t):
        '''In case of exception, places events back in the queue,
        and remove clear state for any discarded events
        '''
        t.eqm.options.eventflushchunksize = 3
        t.eqm.options.maxqueuelen = 5
        t.eqm._initQueues()
        heartbeat_events = [{'heartbeat': i} for i in range(2)]
        perf_events = [{'perf_event': i} for i in range(2)]
        events = [{'event': i} for i in range(2)]

        t.eqm.heartbeat_event_queue.extendleft(heartbeat_events)
        t.eqm.perf_event_queue.extendleft(perf_events)
        t.eqm.event_queue.extendleft(events)

        def event_sender_fn(args):
            raise Exception('event_sender_fn failed')

        ret = t.eqm.sendEvents(event_sender_fn)
        # validate Exception was raised
        t.assertEqual(ret.result.check(Exception), Exception)
        # quash the unhandled error in defferd exception
        ret.addErrback(Mock())

        # Heartbeat events get dropped
        t.assertNotIn(heartbeat_events[1], t.eqm.heartbeat_event_queue)
        # events and perf_events are returned to the queues
        t.assertIn(perf_events[0], t.eqm.perf_event_queue)
        t.assertIn(events[0], t.eqm.event_queue)

    def test_sendEvents_exception_removes_clear_state_for_discarded(t):
        t.eqm.options.eventflushchunksize = 3
        t.eqm.options.maxqueuelen = 2
        t.eqm._initQueues()
        events = [{'event': i} for i in range(2)]

        t.eqm.event_queue.extendleft(events)

        def send(args):
            t.eqm.event_queue.append({'new_event': 0})
            raise Exception('event_sender_fn failed')

        event_sender_fn = Mock(name='event_sender_fn', side_effect=send)

        t.eqm._removeDiscardedEventFromClearState = create_autospec(
            t.eqm._removeDiscardedEventFromClearState,
            name='_removeDiscardedEventFromClearState'
        )

        ret = t.eqm.sendEvents(event_sender_fn)
        # validate Exception was raised
        t.assertEqual(ret.result.check(Exception), Exception)
        # quash the unhandled error in differd exception
        ret.addErrback(Mock())

        event_sender_fn.assert_called_with([events[0], events[1]])

        t.eqm._removeDiscardedEventFromClearState.assert_called_with(events[0])


class PBDaemonClassTest(TestCase):
    '''PBDaemon's __init__ modifies the class attribute heartbeatEvent
    so we have to test it separately

    WARNING: this test fails when running all ZenHub tests together
    Caused by lines: 605, 606
        for evt in self.startEvent, self.stopEvent, self.heartbeatEvent:
            evt.update(details)
    which changes the class attribute when __init__ is run the first time
    '''

    def test_class_attributes(t):
        from Products.ZenHub.PBDaemon import PBDaemon
        t.assertEqual(PBDaemon.name, 'pbdaemon')
        t.assertEqual(PBDaemon.initialServices, ['EventService'])
        # this is the problem line, heartbeatEvent differs
        # /opt/zenoss/bin/runtests \
        #     --type=unit --name Products.ZenHub.tests.test_PBDaemon
        # t.assertEqual(PBDaemon.heartbeatEvent, {'eventClass': '/Heartbeat'})
        # /opt/zenoss/bin/runtests --type=unit --name Products.ZenHub
        # t.assertEqual(
        #    PBDaemon.heartbeatEvent, {
        #        'device': 'localhost',
        #        'eventClass': '/Heartbeat',
        #        'component': 'pbdaemon'
        #    }
        # )
        t.assertEqual(PBDaemon.heartbeatTimeout, 60 * 3)
        t.assertEqual(PBDaemon._customexitcode, 0)
        t.assertEqual(PBDaemon._pushEventsDeferred, None)
        t.assertEqual(PBDaemon._eventHighWaterMark, None)
        t.assertEqual(PBDaemon._healthMonitorInterval, 30)


class PBDaemonTest(TestCase):

    def setUp(t):
        # Patch external dependencies; e.g. twisted.internet.reactor
        t.reactor_patcher = patch(
            '{src}.reactor'.format(**PATH), autospec=True
        )
        t.reactor = t.reactor_patcher.start()
        t.addCleanup(t.reactor_patcher.stop)
        t.publisher_patcher = patch(
            '{src}.publisher'.format(**PATH), autospec=True,
        )
        t.publisher = t.publisher_patcher.start()
        t.addCleanup(t.publisher_patcher.stop)

        t.name = 'pb_daemon_name'
        t.pbd = PBDaemon(name=t.name)

        # Mock out 'log' to prevent spurious output to stdout.
        t.pbd.log = Mock(spec=logging.getLoggerClass())

        t.pbd.eventQueueManager = Mock(
            EventQueueManager, name='eventQueueManager'
        )

    @patch('{src}.sys'.format(**PATH), autospec=True)
    @patch('{src}.task.LoopingCall'.format(**PATH), autospec=True)
    @patch('{src}.stopEvent'.format(**PATH), name='stopEvent', autospec=True)
    @patch('{src}.startEvent'.format(**PATH), name='startEvent', autospec=True)
    @patch('{src}.DaemonStats'.format(**PATH), autospec=True)
    @patch('{src}.EventQueueManager'.format(**PATH), autospec=True)
    @patch('{src}.ZenDaemon.__init__'.format(**PATH), autospec=True)
    def test___init__(
        t, ZenDaemon_init, EventQueueManager, DaemonStats, startEvent,
        stopEvent, LoopingCall, sys
    ):
        noopts = 0,
        keeproot = False

        # Mock out attributes set by the parent class
        # Because these changes are made on the class, they must be reversable
        t.pbdaemon_patchers = [
            patch.object(PBDaemon, 'options', create=True),
            patch.object(PBDaemon, 'log', create=True),
        ]
        for patcher in t.pbdaemon_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        pbd = PBDaemon(noopts=noopts, keeproot=keeproot, name=t.name)

        # runs parent class init
        # this should really be using super(
        ZenDaemon_init.assert_called_with(pbd, noopts, keeproot)

        t.assertEqual(pbd.name, t.name)
        t.assertEqual(pbd.mname, t.name)

        EventQueueManager.assert_called_with(PBDaemon.options, PBDaemon.log)

        # Check lots of attributes, should verify that they are needed
        t.assertEqual(pbd._thresholds, None)
        t.assertEqual(pbd._threshold_notifier, None)
        t.assertEqual(pbd.rrdStats, DaemonStats.return_value)
        t.assertEqual(pbd.lastStats, 0)
        t.assertEqual(pbd.perspective, None)
        t.assertEqual(pbd.services, {})
        t.assertEqual(pbd.eventQueueManager, EventQueueManager.return_value)
        t.assertEqual(pbd.startEvent, startEvent.copy())
        t.assertEqual(pbd.stopEvent, stopEvent.copy())

        # appends name and device to start, stop, and heartbeat events
        details = {'component': t.name, 'device': PBDaemon.options.monitor}
        pbd.startEvent.update.assert_called_with(details)
        pbd.stopEvent.update.assert_called_with(details)
        t.assertEqual(
            pbd.heartbeatEvent, {
                'device': PBDaemon.options.monitor,
                'eventClass': '/Heartbeat',
                'component': 'pb_daemon_name'
            }
        )

        # more attributes
        t.assertIsInstance(pbd.initialConnect, defer.Deferred)
        t.assertEqual(pbd.stopped, False)
        t.assertIsInstance(pbd.counters, collections.Counter)
        t.assertEqual(pbd._pingedZenhub, None)
        t.assertEqual(pbd._connectionTimeout, None)
        t.assertEqual(pbd._publisher, None)  # should be a property
        t.assertEqual(pbd._internal_publisher, None)
        t.assertEqual(pbd._metric_writer, None)
        t.assertEqual(pbd._derivative_tracker, None)
        t.assertEqual(pbd._metrologyReporter, None)

        # Add a shutdown trigger to send a stop event and flush the event queue
        t.reactor.addSystemEventTrigger.assert_called_with(
            'before', 'shutdown', pbd._stopPbDaemon
        )

        # Set up a looping call to support the health check.
        t.assertEqual(pbd.healthMonitor, LoopingCall.return_value)
        LoopingCall.assert_called_with(pbd._checkZenHub)
        pbd.healthMonitor.start.assert_called_with(pbd._healthMonitorInterval)

    @patch('{src}.ZenDaemon.__init__'.format(**PATH), side_effect=IOError)
    def test__init__exit_on_ZenDaemon_IOError(t, ZenDaemon):
        # Mock out attributes set by the parent class
        # Because these changes are made on the class, they must be reversable
        log_patcher = patch.object(PBDaemon, 'log', create=True)
        log_patcher.start()
        t.addCleanup(log_patcher.stop)

        with t.assertRaises(SystemExit):
            PBDaemon()

    # this should be a property
    def test_publisher(t):
        pbd = PBDaemon(name=t.name)
        host = 'localhost'
        port = 9999
        pbd.options.redisUrl = 'http://{}:{}'.format(host, port)

        ret = pbd.publisher()

        t.assertEqual(ret, t.publisher.RedisListPublisher.return_value)
        t.publisher.RedisListPublisher.assert_called_with(
            host,
            port,
            pbd.options.metricBufferSize,
            channel=pbd.options.metricsChannel,
            maxOutstandingMetrics=pbd.options.maxOutstandingMetrics,
        )

    @patch('{src}.os'.format(**PATH), autospec=True)
    def test_internalPublisher(t, os):
        # All the methods with this pattern need to be converted to properties
        t.assertEqual(t.pbd._internal_publisher, None)
        url = Mock(name='url', spec_set=[])
        username = 'username'
        password = 'password'
        os.environ = {
            'CONTROLPLANE_CONSUMER_URL': url,
            'CONTROLPLANE_CONSUMER_USERNAME': username,
            'CONTROLPLANE_CONSUMER_PASSWORD': password,
        }

        ret = t.pbd.internalPublisher()

        t.assertEqual(ret, t.publisher.HttpPostPublisher.return_value)
        t.publisher.HttpPostPublisher.assert_called_with(username, password, url)

        t.assertEqual(t.pbd._internal_publisher, ret)

    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.MetricWriter'.format(**PATH), autospec=True)
    def test_metricWriter_legacy(t, MetricWriter, os):
        t.assertEqual(t.pbd._metric_writer, None)

        t.pbd.publisher = create_autospec(t.pbd.publisher)
        t.pbd.internalPublisher = create_autospec(t.pbd.internalPublisher)
        os.environ = {'CONTROLPLANE': '0'}

        ret = t.pbd.metricWriter()

        MetricWriter.assert_called_with(t.pbd.publisher())
        t.assertEqual(ret, MetricWriter.return_value)
        t.assertEqual(t.pbd._metric_writer, ret)

    @patch('{src}.AggregateMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.FilteredMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.MetricWriter'.format(**PATH), autospec=True)
    def test_metricWriter_controlplane(
        t, MetricWriter, os, FilteredMetricWriter, AggregateMetricWriter
    ):
        t.assertEqual(t.pbd._metric_writer, None)

        t.pbd.publisher = create_autospec(t.pbd.publisher, name='publisher')
        t.pbd.internalPublisher = create_autospec(
            t.pbd.internalPublisher, name='internalPublisher'
        )
        os.environ = {'CONTROLPLANE': '1'}

        ret = t.pbd.metricWriter()

        MetricWriter.assert_called_with(t.pbd.publisher())
        AggregateMetricWriter.assert_called_with(
            [MetricWriter.return_value, FilteredMetricWriter.return_value]
        )
        t.assertEqual(ret, AggregateMetricWriter.return_value)
        t.assertEqual(t.pbd._metric_writer, ret)

    @patch('{src}.DerivativeTracker'.format(**PATH), autospec=True)
    def test_derivativeTracker(t, DerivativeTracker):
        t.assertEqual(t.pbd._derivative_tracker, None)

        ret = t.pbd.derivativeTracker()

        t.assertEqual(ret, DerivativeTracker.return_value)
        t.assertEqual(t.pbd._derivative_tracker, ret)

    def test_connecting(t):
        # logs a message, noop
        t.pbd.connecting()

    def test_getZenhubInstanceId(t):
        # returns a deferred, should be replaced with inlineCallbacks
        perspective = Mock(name='perspective', spec_set=['callRemote'])
        t.pbd.perspective = perspective

        ret = t.pbd.getZenhubInstanceId()

        t.assertEqual(ret, perspective.callRemote.return_value)
        perspective.callRemote.assert_called_with('getHubInstanceId')

    def test_gotPerspective(t):
        perspective = Mock(name='perspective', spec_set=['callRemote'])
        _connectionTimeout = Mock(
            spec_set=t.pbd._connectionTimeout, name='_connectionTimeout'
        )
        t.pbd._connectionTimeout = _connectionTimeout
        getInitialServices = Mock(name='getInitialServices', spec_set=[])
        t.pbd.getInitialServices = getInitialServices
        initialConnect = Mock(name='initialConnect', spec_set=[])
        t.pbd.initialConnect = initialConnect

        t.pbd.gotPerspective(perspective)

        # sets the perspective attribute
        t.assertEqual(t.pbd.perspective, perspective)
        #  if _connectionTimeoutcall is set call _connectionTimeout.cancel()
        _connectionTimeout.cancel.assert_called_with()
        t.assertEqual(t.pbd._connectionTimeout, None)
        # if initialConnect is set, it is set to None,
        # and executed after getInitialServices as a deferred
        getInitialServices.assert_called_with()
        d2 = getInitialServices.return_value
        t.assertEqual(t.pbd.initialConnect, None)
        d2.chainDeferred.assert_called_with(initialConnect)

    @patch(
        '{src}.credentials'.format(**PATH), name='credentials', autospec=True
    )
    @patch(
        '{src}.ReconnectingPBClientFactory'.format(**PATH),
        name='ReconnectingPBClientFactory',
        autospec=True
    )
    def test_connect(t, ReconnectingPBClientFactory, credentials):
        factory = ReconnectingPBClientFactory.return_value
        options = t.pbd.options
        connectTimeout = Mock(t.pbd.connectTimeout, name='connectTimeout')
        t.pbd.connectTimeout = connectTimeout

        ret = t.pbd.connect()

        # ensure the connection factory is setup properly
        factory.connectTCP.assert_called_with(options.hubhost, options.hubport)
        t.assertEqual(factory.gotPerspective, t.pbd.gotPerspective)
        t.assertEqual(factory.connecting, t.pbd.connecting)
        credentials.UsernamePassword.assert_called_with(
            options.hubusername, options.hubpassword
        )
        factory.setCredentials.assert_called_with(
            credentials.UsernamePassword.return_value
        )

        # connectionTimeout is set
        t.assertEqual(
            t.pbd._connectionTimeout, t.reactor.callLater.return_value
        )

        # returns pbd.initialconnect, not sure where the factory goes
        t.assertEqual(ret, t.pbd.initialConnect)

        # test timeout method passed to reactor.callLater
        # unpack the args to get the timeout function
        args, kwargs = t.reactor.callLater.call_args
        timeout = args[1]
        d = Mock(defer.Deferred, name='initialConnect.result')
        d.called = False
        timeout(d)
        connectTimeout.assert_called_with()

    def test_connectTimeout(t):
        '''logs a message and passes,
        not to be confused with _connectionTimeout, which is set to a deferred
        '''
        t.pbd.connectTimeout()

    def test_eventService(t):
        # alias for getServiceNow
        t.pbd.getServiceNow = create_autospec(t.pbd.getServiceNow)
        t.pbd.eventService()
        t.pbd.getServiceNow.assert_called_with('EventService')

    def test_getServiceNow(t):
        svc_name = 'svc_name'
        t.pbd.services[svc_name] = 'some service'
        ret = t.pbd.getServiceNow(svc_name)
        t.assertEqual(ret, t.pbd.services[svc_name])

    @patch('{src}.FakeRemote'.format(**PATH), autospec=True)
    def test_getServiceNow_FakeRemote_on_missing_service(t, FakeRemote):
        ret = t.pbd.getServiceNow('svc_name')
        t.assertEqual(ret, FakeRemote.return_value)

    def test_getService_known_service(t):
        t.pbd.services['known_service'] = 'service'
        ret = t.pbd.getService('known_service')

        t.assertIsInstance(ret, defer.Deferred)
        t.assertEqual(ret.result, t.pbd.services['known_service'])

    def test_getService(t):
        '''this is going to be ugly to test,
        and badly needs to be rewritten as an inlineCallback
        '''
        perspective = Mock(name='perspective', spec_set=['callRemote'])
        serviceListeningInterface = Mock(
            name='serviceListeningInterface', spec_set=[]
        )
        t.pbd.perspective = perspective
        service_name = 'service_name'

        ret = t.pbd.getService(service_name, serviceListeningInterface)

        perspective.callRemote.assert_called_with(
            'getService', service_name, t.pbd.options.monitor,
            serviceListeningInterface, t.pbd.options.__dict__
        )
        t.assertEqual(ret, perspective.callRemote.return_value)

        # Pull the callbacks out of ret, to make sure they work as intended
        args, kwargs = ret.addCallback.call_args
        callback = args[0]
        # callback adds the service to pbd.services
        ret_callback = callback(ret.result, service_name)
        t.assertEqual(t.pbd.services[service_name], ret.result)
        # the service (result) has notifyOnDisconnect called with removeService
        args, kwargs = ret_callback.notifyOnDisconnect.call_args
        removeService = args[0]
        # removeService
        removeService(service_name)
        t.assertNotIn(service_name, t.pbd.services)

    @patch('{src}.defer'.format(**PATH), autospec=True)
    def test_getInitialServices(t, defer):
        '''execute getService(svc_name) for every service in initialServices
        in parallel deferreds
        '''
        getService = create_autospec(t.pbd.getService, name='getService')
        t.pbd.getService = getService
        ret = t.pbd.getInitialServices()

        defer.DeferredList.assert_called_with(
            [getService.return_value for svc in t.pbd.initialServices],
            fireOnOneErrback=True,
            consumeErrors=True
        )
        getService.assert_has_calls(
            [call(svc) for svc in t.pbd.initialServices]
        )

        t.assertEqual(ret, defer.DeferredList.return_value)

    def test_connected(t):
        # does nothing
        t.pbd.connected()

    @patch('{src}.ThresholdNotifier'.format(**PATH), autospec=True)
    def test__getThresholdNotifier(t, ThresholdNotifier):
        # refactor to be a property
        t.assertEqual(t.pbd._threshold_notifier, None)
        ret = t.pbd._getThresholdNotifier()

        ThresholdNotifier.assert_called_with(
            t.pbd.sendEvent, t.pbd.getThresholds()
        )
        t.assertEqual(ret, ThresholdNotifier.return_value)
        t.assertEqual(t.pbd._threshold_notifier, ret)

    @patch('{src}.Thresholds'.format(**PATH), autospec=True)
    def test_getThresholds(t, Thresholds):
        # refactor to be a property
        t.assertEqual(t.pbd._thresholds, None)

        ret = t.pbd.getThresholds()

        Thresholds.assert_called_with()
        t.assertEqual(ret, Thresholds.return_value)
        t.assertEqual(t.pbd._thresholds, ret)

    @patch('{src}.sys'.format(**PATH), autospec=True)
    @patch('{src}.task'.format(**PATH), autospec=True)
    @patch('{src}.TwistedMetricReporter'.format(**PATH), autospec=True)
    def test_run(t, TwistedMetricReporter, task, sys):
        '''Starts up all of the internal loops,
        does not return until reactor.run() completes (reactor is shutdown)
        '''
        t.pbd.rrdStats = Mock(spec_set=t.pbd.rrdStats)
        t.pbd.connect = create_autospec(t.pbd.connect)
        t.pbd._customexitcode = 99

        t.pbd.run()

        # adds startStatsLoop to reactor.callWhenRunning
        args, kwargs = t.reactor.callWhenRunning.call_args
        startStatsLoop = args[0]
        ret = startStatsLoop()
        task.LoopingCall.assert_called_with(t.pbd.postStatistics)
        loop = task.LoopingCall.return_value
        loop.start.assert_called_with(t.pbd.options.writeStatistics, now=False)
        daemonTags = {
            'zenoss_daemon': t.pbd.name,
            'zenoss_monitor': t.pbd.options.monitor,
            'internal': True
        }
        TwistedMetricReporter.assert_called_with(
            t.pbd.options.writeStatistics,
            t.pbd.metricWriter(),
            daemonTags,
        )
        t.assertEqual(
            t.pbd._metrologyReporter, TwistedMetricReporter.return_value
        )
        t.pbd._metrologyReporter.start.assert_called_with()

        # adds stopReporter (defined internally) to reactor before shutdown
        args, kwargs = t.reactor.addSystemEventTrigger.call_args
        stopReporter = args[2]
        t.assertEqual(args[0], 'before')
        t.assertEqual(args[1], 'shutdown')
        ret = stopReporter()
        t.assertEqual(ret, t.pbd._metrologyReporter.stop.return_value)
        t.pbd._metrologyReporter.stop.assert_called_with()

        t.pbd.rrdStats.config.assert_called_with(
            t.pbd.name,
            t.pbd.options.monitor,
            t.pbd.metricWriter(),
            t.pbd._getThresholdNotifier(),
            t.pbd.derivativeTracker(),
        )

        # returns a deferred, that has a callback added to it
        # but we have no access to it from outside the function
        t.pbd.connect.assert_called_with()

        t.reactor.run.assert_called_with()
        # only calls sys.exit if a custom exitcode is set, should probably
        # exit even if exitcode = 0
        sys.exit.assert_called_with(t.pbd._customexitcode)

    def test_setExitCode(t):
        exitcode = Mock()
        t.pbd.setExitCode(exitcode)
        t.assertEqual(t.pbd._customexitcode, exitcode)

    def test_stop(t):
        # stops the reactor and handles ReactorNotRunning
        t.reactor.running = True
        t.pbd.stop()
        t.reactor.stop.assert_called_with()

    def test__stopPbDaemon(t):
        # set stopped=True, and send a stopEvent
        t.assertFalse(t.pbd.stopped)
        t.pbd.services['EventService'] = True
        t.pbd.options.cycle = True
        t.pbd.sendEvent = Mock(t.pbd.sendEvent, name='sendEvent')
        t.pbd.pushEvents = Mock(t.pbd.pushEvents, name='pushEvents')

        ret = t.pbd._stopPbDaemon()

        t.assertTrue(t.pbd.stopped)

        # send a stopEvent if it has an EventService
        t.pbd.sendEvent.assert_called_with(t.pbd.stopEvent)
        t.assertEqual(ret, t.pbd.pushEvents.return_value)

    def test__stopPbDaemon_pushEventsDeferred(t):
        # if _pushEventsDeferred is set, append a new pushEvents deffered to it
        t.pbd._pushEventsDeferred = Mock(
            defer.Deferred, name='_pushEventsDeferred'
        )
        t.assertFalse(t.pbd.stopped)
        t.pbd.services['EventService'] = True
        t.pbd.options.cycle = True
        t.pbd.sendEvent = Mock(t.pbd.sendEvent, name='sendEvent')
        t.pbd.pushEvents = Mock(t.pbd.pushEvents, name='pushEvents')

        ret = t.pbd._stopPbDaemon()

        t.assertTrue(t.pbd.stopped)

        # send a stopEvent if it has an EventService
        t.pbd.sendEvent.assert_called_with(t.pbd.stopEvent)
        t.assertEqual(ret, t.pbd._pushEventsDeferred)
        # unable to test pushEvents added as callback
        # blocked by maybe unneccesary lambda

    def test_sendEvents(t):
        # simply maps events to sendEvent
        t.pbd.sendEvent = Mock(t.pbd.sendEvent, name='sendEvent')
        events = [{'name': 'evt_a'}, {'name': 'evt_b'}]

        t.pbd.sendEvents(events)

        t.pbd.sendEvent.assert_has_calls([call(event) for event in events])

    @patch('{src}.defer'.format(**PATH), autospec=True)
    def test_sendEvent(t, defer):
        # appends events to the in-memory outbound queue
        event = {'name': 'event'}
        generated_event = t.pbd.generateEvent(event, newkey='newkey')
        t.pbd.eventQueueManager.event_queue_length = 0
        t.assertEqual(t.pbd.counters['eventCount'], 0)
        t.pbd._eventHighWaterMark = False

        ret = t.pbd.sendEvent(event, newkey='newkey')

        t.pbd.eventQueueManager.addEvent.assert_called_with(generated_event)
        t.assertEqual(t.pbd.counters['eventCount'], 1)
        defer.succeed.assert_called_with(None)
        t.assertEqual(ret, defer.succeed.return_value)

    def test_generateEvent(t):
        # returns a dict with keyword args, and other values added
        event = {'name': 'event'}

        ret = t.pbd.generateEvent(event, newkey='newkey')

        t.assertEqual(
            ret,
            {
                'name': 'event',
                'newkey': 'newkey',
                'agent': t.pbd.name,
                'monitor': t.pbd.options.monitor,
                'manager': t.pbd.fqdn,
            },
        )

    def test_generateEvent_reactor_not_running(t):
        # returns nothing if reactor is not running
        t.reactor.running = False
        ret = t.pbd.generateEvent({'name': 'event'})
        t.assertEqual(ret, None)

    def test_pushEventsLoop(t):
        '''currently an old-style convoluted looping deferred
        this needs to be refactored to run in a task.loopingCall
        '''
        t.pbd.pushEvents = create_autospec(t.pbd.pushEvents, name='pushEvents')

        ret = t.pbd.pushEventsLoop()

        t.reactor.callLater.assert_called_with(
            t.pbd.options.eventflushseconds, t.pbd.pushEventsLoop
        )
        t.pbd.pushEvents.assert_called_with()

        t.assertEqual(ret.result, None)

    @patch('{src}.partial'.format(**PATH), autospec=True)
    @patch('{src}.defer'.format(**PATH), autospec=True)
    def test_pushEvents(t, defer, partial):
        '''Does excessive pre-checking, and book keeping before sending
        sending the Event Service remote procedure 'sendEvents'
        to the eventQueueManager.sendEvents function

        All of this event management work needs to be refactored into its own
        EventManager Class
        '''
        t.pbd.eventQueueManager.discarded_events = None
        t.reactor.running = True
        t.assertEqual(t.pbd._eventHighWaterMark, None)
        t.assertEqual(t.pbd._pushEventsDeferred, None)
        evtSvc = Mock(name='event_service', spec_set=['callRemote'])
        t.pbd.services['EventService'] = evtSvc

        t.pbd.pushEvents()

        partial.assert_called_with(evtSvc.callRemote, 'sendEvents')
        send_events_fn = partial.return_value
        t.pbd.eventQueueManager.sendEvents.assert_called_with(send_events_fn)

    def test_pushEvents_reactor_not_running(t):
        # do nothing if the reactor is not running
        t.reactor.running = False
        t.pbd.log = Mock(t.pbd.log, name='log')
        t.pbd.pushEvents()
        # really ugly way of checking we entered this block
        t.pbd.log.debug.assert_called_with(
            "Skipping event sending - reactor not running."
        )

    def test_heartbeat(t):
        t.pbd.options.cycle = True
        t.pbd.niceDoggie = create_autospec(t.pbd.niceDoggie, name='niceDoggie')

        t.pbd.heartbeat()

        heartbeat_event = t.pbd.generateEvent(
            t.pbd.heartbeatEvent, timeout=t.pbd.heartbeatTimeout
        )
        t.pbd.eventQueueManager.addHeartbeatEvent.assert_called_with(
            heartbeat_event
        )
        t.pbd.niceDoggie.assert_called_with(t.pbd.heartbeatTimeout / 3)

    def test_postStatisticsImpl(t):
        # does nothing, maybe implemented by subclasses
        t.pbd.postStatisticsImpl()

    def test_postStatistics(t):
        # sets rrdStats, then calls postStatisticsImpl
        t.pbd.rrdStats = Mock(name='rrdStats', spec_set=['counter'])
        ctrs = {'c1': 3, 'c2': 5}
        for k, v in ctrs.items():
            t.pbd.counters[k] = v

        t.pbd.postStatistics()

        t.pbd.rrdStats.counter.assert_has_calls(
            [call(k, v) for k, v in ctrs.items()]
        )

    @patch('{src}.os'.format(**PATH))
    def test__pickleName(t, os):
        # refactor as a property
        ret = t.pbd._pickleName()
        os.environ.get.assert_called_with('CONTROLPLANE_INSTANCE_ID')
        t.assertEqual(
            ret, 'var/{}_{}_counters.pickle'.format(
                t.pbd.name, os.environ.get.return_value
            )
        )

    def test_remote_getName(t):
        ret = t.pbd.remote_getName()
        t.assertEqual(ret, t.pbd.name)

    def test_remote_shutdown(t):
        t.pbd.stop = create_autospec(t.pbd.stop, name='stop')
        t.pbd.sigTerm = create_autospec(t.pbd.sigTerm, name='sigTerm')

        t.pbd.remote_shutdown('unused arg is ignored')

        t.pbd.stop.assert_called_with()
        t.pbd.sigTerm.assert_called_with()

    def test_remote_setPropertyItems(t):
        # does nothing
        t.pbd.remote_setPropertyItems('items arg is ignored')

    def test_remote_updateThresholdClasses(t):
        '''attempts to call importClass for all class names in classes arg
        currently imports the importClasses within the method its self,
        making patching and testing impossible

        used exclusively by Products.DataCollector.zenmodeler.ZenModeler
        '''
        pass
        # ret = t.pbd.remote_updateThresholdClasses(['class_a', 'class_b'])
        # t.assertEqual(ret, 'something')

    def test__checkZenHub(t):
        t.pbd._signalZenHubAnswering = create_autospec(
            t.pbd._signalZenHubAnswering, name='_signalZenHubAnswering'
        )
        perspective = Mock(name='perspective', spec_set=['callRemote'])
        t.pbd.perspective = perspective

        ret = t.pbd._checkZenHub()

        perspective.callRemote.assert_called_with('ping')
        t.assertEqual(ret, t.pbd.perspective.callRemote.return_value)
        # Get the internally defined callback to test it
        args, kwargs = ret.addCallback.call_args
        callback = args[0]
        # if perspective.callRemote('ping') returns 'pong'
        callback(result='pong')
        t.pbd._signalZenHubAnswering.assert_called_with(True)
        # any other result calls _signalZenHubAnswering(False)
        callback(result=None)
        t.pbd._signalZenHubAnswering.assert_called_with(False)

    def test__checkZenHub_without_perspective(t):
        t.pbd.perspective = False
        t.pbd._signalZenHubAnswering = create_autospec(
            t.pbd._signalZenHubAnswering, name='_signalZenHubAnswering'
        )

        t.pbd._checkZenHub()

        t.pbd._signalZenHubAnswering.assert_called_with(False)

    def test__checkZenHub_exception(t):
        perspective = Mock(name='perspective', spec_set=['callRemote'])
        perspective.callRemote.side_effect = Exception
        t.pbd.perspective = perspective

        t.pbd._signalZenHubAnswering = create_autospec(
            t.pbd._signalZenHubAnswering, name='_signalZenHubAnswering'
        )

        t.pbd._checkZenHub()

        t.pbd._signalZenHubAnswering.assert_called_with(False)

    @patch('{src}.zenPath'.format(**PATH), name='zenPath', autospec=True)
    @patch(
        '{src}.atomicWrite'.format(**PATH), name='atomicWrite', autospec=True
    )
    def test__signalZenHubAnswering_True(t, atomicWrite, zenPath):
        '''creates an empty file named zenhub_connected, if zenhub is answering
        removes it if zenhub is not answering
        '''
        filename = 'zenhub_connected'
        t.pbd._signalZenHubAnswering(True)
        zenPath.assert_called_with('var', filename)
        atomicWrite(filename, '')

    @patch('{src}.os'.format(**PATH), name='os', autospec=True)
    @patch('{src}.zenPath'.format(**PATH), name='zenPath', autospec=True)
    def test__signalZenHubAnswering_False(t, zenPath, os):
        '''creates an empty file named zenhub_connected, if zenhub is answering
        removes it if zenhub is not answering
        '''
        filename = 'zenhub_connected'
        t.pbd._signalZenHubAnswering(False)
        zenPath.assert_called_with('var', filename)
        os.remove.assert_called_with(zenPath.return_value)

    def test_buildOptions(t):
        '''After initialization, the InvalidationWorker instance should have
        options parsed from its buildOptions method
        assertions based on default options
        '''
        from Products.ZenHub.PBDaemon import (
            DEFAULT_HUB_HOST, DEFAULT_HUB_PORT, DEFAULT_HUB_USERNAME,
            DEFAULT_HUB_PASSWORD, DEFAULT_HUB_MONITOR
        )
        t.assertEqual(t.pbd.options.hubhost, DEFAULT_HUB_HOST)  # No default
        t.assertEqual(t.pbd.options.hubport, DEFAULT_HUB_PORT)
        t.assertEqual(t.pbd.options.hubusername, DEFAULT_HUB_USERNAME)
        t.assertEqual(t.pbd.options.hubpassword, DEFAULT_HUB_PASSWORD)
        t.assertEqual(t.pbd.options.monitor, DEFAULT_HUB_MONITOR)
        t.assertEqual(t.pbd.options.hubtimeout, 30)
        t.assertEqual(t.pbd.options.allowduplicateclears, False)
        t.assertEqual(t.pbd.options.duplicateclearinterval, 0)
        t.assertEqual(t.pbd.options.eventflushseconds, 5)
        t.assertEqual(t.pbd.options.eventflushseconds, 5.0)
        t.assertEqual(t.pbd.options.eventflushchunksize, 50)
        t.assertEqual(t.pbd.options.maxqueuelen, 5000)
        t.assertEqual(t.pbd.options.queueHighWaterMark, 0.75)
        t.assertEqual(t.pbd.options.zhPingInterval, 120)
        t.assertEqual(t.pbd.options.deduplicate_events, True)

        global_conf = getGlobalConfiguration()
        if "redis-url" in global_conf:
            expected_redisurl = global_conf["redis-url"]
        else:
            expected_redisurl = \
                'redis://localhost:%s/0' % t.publisher.defaultRedisPort
        t.assertEqual(t.pbd.options.redisUrl, expected_redisurl)

        t.assertEqual(
            t.pbd.options.metricBufferSize,
            t.publisher.defaultMetricBufferSize,
        )
        t.assertEqual(
            t.pbd.options.metricsChannel, t.publisher.defaultMetricsChannel,
        )
        t.assertEqual(
            t.pbd.options.maxOutstandingMetrics,
            t.publisher.defaultMaxOutstandingMetrics,
        )
        t.assertEqual(t.pbd.options.pingPerspective, True)
        t.assertEqual(t.pbd.options.writeStatistics, 30)
