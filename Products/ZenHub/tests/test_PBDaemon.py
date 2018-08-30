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

PATH = {'src': 'Products.ZenHub.PBDaemon'}


class RemoteExceptionsTest(TestCase):
    '''These excpetions can probably be moved into their own moduel
        '''

    def test_raise_RemoteException(self):
        with self.assertRaises(RemoteException):
            raise RemoteException('message', 'traceback')

    def test_RemoteException_is_pb_is_copyable(self):
        self.assertTrue(issubclass(RemoteException, pb.Copyable))
        self.assertTrue(issubclass(RemoteException, pb.RemoteCopy))

    def test_raise_RemoteConflictError(self):
        with self.assertRaises(RemoteConflictError):
            raise RemoteConflictError('message', 'traceback')

    def test_RemoteConflictError_is_pb_is_copyable(self):
        self.assertTrue(issubclass(RemoteConflictError, pb.Copyable))
        self.assertTrue(issubclass(RemoteConflictError, pb.RemoteCopy))

    def test_raise_RemoteBadMonitor(self):
        with self.assertRaises(RemoteBadMonitor):
            raise RemoteBadMonitor('message', 'traceback')

    def test_RemoteBadMonitor_is_pb_is_copyable(self):
        self.assertTrue(issubclass(RemoteBadMonitor, pb.Copyable))
        self.assertTrue(issubclass(RemoteBadMonitor, pb.RemoteCopy))

    def test_translateError_transforms_ConflictError(self):
        traceback = Mock(spec_set=['_p_oid'])

        @translateError
        def raise_conflict_error():
            raise ConflictError('message', traceback)

        with self.assertRaises(RemoteConflictError):
            raise_conflict_error()

    def test_translateError_transforms_Exception(self):

        @translateError
        def raise_error():
            raise Exception('message', 'traceback')

        with self.assertRaises(RemoteException):
            raise_error()


class DefaultFingerprintGeneratorTest(TestCase):

    def test_init(self):
        fingerprint_generator = DefaultFingerprintGenerator()

        # the class Implements the Interface
        self.assertTrue(
            ICollectorEventFingerprintGenerator.
            implementedBy(DefaultFingerprintGenerator)
        )
        # the object provides the interface
        self.assertTrue(
            ICollectorEventFingerprintGenerator.
            providedBy(fingerprint_generator)
        )
        # Verify the object implments the interface properly
        verifyObject(
            ICollectorEventFingerprintGenerator, fingerprint_generator
        )

    def test_generate(self):
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

        self.assertEqual(out, expected)


class load_utilities_Test(TestCase):

    @patch('{src}.getUtilitiesFor'.format(**PATH), autospec=True)
    def test_load_utilities(self, getUtilitiesFor):
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
        self.assertEqual(ret, [func2, func1])


class BaseEventQueueTest(TestCase):

    def setUp(self):
        self.beq = BaseEventQueue(maxlen=5)

    def test_init(self):
        base_event_queue = BaseEventQueue(maxlen=5)
        self.assertEqual(base_event_queue.maxlen, 5)

    def test_append(self):
        with self.assertRaises(NotImplementedError):
            self.beq.append('event')

    def test_popleft(self):
        with self.assertRaises(NotImplementedError):
            self.beq.popleft()

    def test_extendleft(self):
        with self.assertRaises(NotImplementedError):
            self.beq.extendleft(['event_a', 'event_b'])

    def test___len__(self):
        with self.assertRaises(NotImplementedError):
            len(self.beq)

    def test___iter__(self):
        with self.assertRaises(NotImplementedError):
            [i for i in self.beq]


class DequeEventQueueTest(TestCase):

    def setUp(self):
        self.deq = DequeEventQueue(maxlen=10)
        self.event_a, self.event_b = {'name': 'event_a'}, {'name': 'event_b'}

    def test_init(self):
        maxlen = 100
        deq = DequeEventQueue(maxlen=maxlen)
        self.assertEqual(deq.maxlen, maxlen)
        self.assertIsInstance(deq.queue, collections.deque)

    @patch('{src}.time'.format(**PATH))
    def test_append(self, time):
        event = {}
        deq = DequeEventQueue(maxlen=10)

        ret = deq.append(event)

        # append sets the time the event was added to the queue
        self.assertEqual(event['rcvtime'], time.time())
        self.assertEqual(ret, None)

    def test_append_pops_and_returns_leftmost_if_full(self):
        event_a, event_b = {'name': 'event_a'}, {'name': 'event_b'}
        deq = DequeEventQueue(maxlen=1)

        deq.append(event_a)
        ret = deq.append(event_b)

        self.assertIn(event_b, deq.queue)
        self.assertNotIn(event_a, deq.queue)
        self.assertEqual(ret, event_a)

    @patch('{src}.time'.format(**PATH))
    def test_popleft(self, time):
        self.deq.append(self.event_a)
        self.deq.append(self.event_b)

        ret = self.deq.queue.popleft()

        self.assertEqual(ret, self.event_a)

    def test_base_popleft(self):
        self.deq.queue.append('a')
        self.deq.queue.append('b')

        ret = self.deq.queue.popleft()
        self.assertEqual(ret, 'a')

    @patch('{src}.time'.format(**PATH))
    def test_extendleft(self, time):
        '''WARNING: extendleft does NOT add timestamps, as .append does
        is this behavior is intentional?
        '''
        event_c = {'name': 'event_c'}
        self.deq.append(event_c)
        self.assertEqual(list(self.deq), [event_c])
        events = [self.event_a, self.event_b]

        ret = self.deq.extendleft(events)

        self.assertEqual(ret, [])
        self.assertEqual(list(self.deq), [self.event_a, self.event_b, event_c])
        '''
        # to validate all events get timestamps
        self.assertEqual(
            list(self.deq),
            [{'name': 'event_a', 'rcvtime': time.time.return_value},
             {'name': 'event_b', 'rcvtime': time.time.return_value},
             {'name': 'event_c', 'rcvtime': time.time.return_value},
            ]
        '''

    def test_extendleft_returns_events_if_falsey(self):
        ret = self.deq.extendleft(False)
        self.assertEqual(ret, False)
        ret = self.deq.extendleft([])
        self.assertEqual(ret, [])
        ret = self.deq.extendleft(0)
        self.assertEqual(ret, 0)

    def test_extendleft_returns_extra_events_if_nearly_full(self):
        self.deq.maxlen = 3
        self.deq.extendleft([self.event_a, self.event_b])
        event_c, event_d = {'name': 'event_c'}, {'name': 'event_d'}
        events = [event_c, event_d]

        ret = self.deq.extendleft(events)

        self.assertEqual(list(self.deq), [event_d, self.event_a, self.event_b])
        self.assertEqual(ret, [event_c])

    def test___len__(self):
        ret = len(self.deq)
        self.assertEqual(ret, 0)
        self.deq.extendleft([self.event_a, self.event_b])
        self.assertEqual(len(self.deq), 2)

    def test___iter__(self):
        self.deq.extendleft([self.event_a, self.event_b])
        ret = [event for event in self.deq]
        self.assertEqual(ret, [self.event_a, self.event_b])


class DeDupingEventQueueTest(TestCase):

    def setUp(self):
        self.ddeq = DeDupingEventQueue(maxlen=10)
        self.event_a, self.event_b = {'name': 'event_a'}, {'name': 'event_b'}

    @patch('{src}._load_utilities'.format(**PATH))
    def test_init(self, _load_utilities):
        ddeq = DeDupingEventQueue(maxlen=10)
        self.assertEqual(ddeq.maxlen, 10)

        self.assertIsInstance(
            ddeq.default_fingerprinter, DefaultFingerprintGenerator
        )
        self.assertEqual(ddeq.fingerprinters, _load_utilities.return_value)
        self.assertIsInstance(ddeq.queue, collections.OrderedDict)

    def test_event_fingerprint(self):
        self.ddeq.fingerprinters = []

        ret = self.ddeq._event_fingerprint(self.event_a)
        expected = DefaultFingerprintGenerator().generate(self.event_a)
        self.assertEqual(ret, expected)

        # Identical events generate the same fingerprint
        event_2 = self.event_a.copy()
        ret = self.ddeq._event_fingerprint(event_2)
        self.assertEqual(ret, expected)

    def test_event_fingerprint_fingerprinters_list(self):
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

        self.ddeq.fingerprinters = [fp1, fp2, fp3]

        ret = self.ddeq._event_fingerprint(self.event_a)

        fp1.generate.assert_called_with(self.event_a)
        fp2.generate.assert_called_with(self.event_a)
        fp3.generate.assert_not_called()
        self.assertEqual(ret, str(self.event_a))

    def test_first_time(self):
        '''given 2 events, retrun the earliest timestamp of the two
        use 'firstTime' if available, else 'rcvtime'
        '''
        event1 = {'firstTime': 1, 'rcvtime': 0}
        event2 = {'rcvtime': 2}

        ret = self.ddeq._first_time(event1, event2)
        self.assertEqual(ret, 1)

        event1 = {'firstTime': 3, 'rcvtime': 1}
        event2 = {'rcvtime': 2}

        ret = self.ddeq._first_time(event1, event2)
        self.assertEqual(ret, 2)

    @patch('{src}.time'.format(**PATH))
    def test_append_timestamp(self, time):
        '''Make sure every processed event specifies the time it was queued.
        '''
        self.ddeq.append(self.event_a)
        event = self.ddeq.popleft()

        self.assertEqual(event['rcvtime'], time.time.return_value)

    @patch('{src}.time'.format(**PATH))
    def test_append_deduplication(self, time):
        '''The same event cannot be added to the queue twice
        appending a duplicate event replaces the original
        '''
        event1 = {'data': 'some data'}
        event2 = {'data': 'some data'}
        self.assertEqual(event1, event2)

        self.ddeq.append(event1)
        self.ddeq.append(event2)

        self.assertEqual(len(self.ddeq), 1)

        ret = self.ddeq.popleft()
        # The new event replaces the old one
        self.assertIs(ret, event2)
        self.assertEqual(event2['count'], 2)

    @patch('{src}.time'.format(**PATH))
    def test_append_deduplicates_and_counts_events(self, time):
        time.time.side_effect = (t for t in range(100))
        self.ddeq.append({'name': 'event_a'})
        self.assertEqual(
            list(self.ddeq),
            [{'rcvtime': 0, 'name': 'event_a'}]
        )
        self.ddeq.append({'name': 'event_a'})
        self.assertEqual(
            list(self.ddeq),
            [{'rcvtime': 1, 'firstTime': 0, 'count': 2, 'name': 'event_a'}]
        )
        self.ddeq.append({'name': 'event_a'})
        self.assertEqual(
            list(self.ddeq),
            [{'rcvtime': 2, 'firstTime': 0, 'count': 3, 'name': 'event_a'}]
        )
        self.ddeq.append({'name': 'event_a'})
        self.assertEqual(
            list(self.ddeq),
            [{'rcvtime': 3, 'firstTime': 0, 'count': 4, 'name': 'event_a'}]
        )

    def test_append_pops_and_returns_leftmost_if_full(self):
        self.ddeq.maxlen = 1

        self.ddeq.append(self.event_a)
        ret = self.ddeq.append(self.event_b)

        # NOTE: events are stored in a dict, key=fingerprint
        self.assertIn(
            self.ddeq._event_fingerprint(self.event_b), self.ddeq.queue
        )
        self.assertNotIn(
            self.ddeq._event_fingerprint(self.event_a), self.ddeq.queue
        )
        self.assertEqual(ret, self.event_a)

    def test_popleft(self):
        self.ddeq.append(self.event_a)
        self.ddeq.append(self.event_b)

        ret = self.ddeq.popleft()

        self.assertEqual(ret, self.event_a)

    def test_popleft_raises_IndexError(self):
        '''Raises IndexError instead of KeyError, for api compatability
        '''
        with self.assertRaises(IndexError):
            self.ddeq.popleft()

    @patch('{src}.time'.format(**PATH))
    def test_extendleft(self, time):
        '''WARNING: extendleft does NOT add timestamps, as .append does
        is this behavior is intentional?
        '''
        event_c = {'name': 'event_c'}
        self.ddeq.append(event_c)
        self.assertEqual(list(self.ddeq), [event_c])
        events = [self.event_a, self.event_b]

        ret = self.ddeq.extendleft(events)

        self.assertEqual(ret, [])
        self.assertEqual(
            list(self.ddeq),
            [self.event_a, self.event_b, event_c]
        )
        '''
        # to validate all events get timestamps
        self.assertEqual(
            list(self.ddeq),
            [{'name': 'event_a', 'rcvtime': time.time.return_value},
             {'name': 'event_b', 'rcvtime': time.time.return_value},
             {'name': 'event_c', 'rcvtime': time.time.return_value},
            ]
        )
        '''

    @patch('{src}.time'.format(**PATH))
    def test_extendleft_counts_events_BUG(self, time):
        time.time.side_effect = (t for t in range(100))
        self.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        self.assertEqual(
            list(self.ddeq),
            # This should work
            #[{'rcvtime': 0, 'name': 'event_a'}]
            # current behavior
            [{'name': 'event_a'}, {'name': 'event_b'}]
        )
        # rcvtime is required, but is not set by extendleft
        with self.assertRaises(KeyError):
            self.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        '''
        Test Breaks Here due to missing rcvtime
        self.assertEqual(
            list(self.ddeq),
            [{'rcvtime': 1, 'firstTime': 0, 'count': 2, 'name': 'event_a'},
             {'rcvtime': 1, 'firstTime': 0, 'count': 2, 'name': 'event_b'}]
        )
        self.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        self.assertEqual(
            list(self.ddeq),
            [{'rcvtime': 2, 'firstTime': 0, 'count': 3, 'name': 'event_a'},
             {'rcvtime': 2, 'firstTime': 0, 'count': 3, 'name': 'event_b'}]
        )
        self.ddeq.extendleft([{'name': 'event_a'}, {'name': 'event_b'}])
        self.assertEqual(
            list(self.ddeq),
            [{'rcvtime': 3, 'firstTime': 0, 'count': 4, 'name': 'event_a'},
             {'rcvtime': 3, 'firstTime': 0, 'count': 4, 'name': 'event_b'}]
        )
        '''

    def test_extendleft_returns_events_if_empty(self):
        ret = self.ddeq.extendleft([])
        self.assertEqual(ret, [])

    def test_extendleft_returns_extra_events_if_nearly_full(self):
        self.ddeq.maxlen = 3
        self.ddeq.extendleft([self.event_a, self.event_b])
        event_c, event_d = {'name': 'event_c'}, {'name': 'event_d'}
        events = [event_c, event_d]

        ret = self.ddeq.extendleft(events)

        self.assertEqual(
            list(self.ddeq),
            [event_d, self.event_a, self.event_b]
        )
        self.assertEqual(ret, [event_c])

    def test___len__(self):
        ret = len(self.ddeq)
        self.assertEqual(ret, 0)
        self.ddeq.extendleft([self.event_a, self.event_b])
        self.assertEqual(len(self.ddeq), 2)

    def test___iter__(self):
        self.ddeq.extendleft([self.event_a, self.event_b])
        ret = [event for event in self.ddeq]
        self.assertEqual(ret, [self.event_a, self.event_b])


class EventQueueManagerTest(TestCase):

    def setUp(self):
        options = Mock(
            name='options',
            spec_set=[
                'maxqueuelen', 'deduplicate_events', 'allowduplicateclears',
                'duplicateclearinterval', 'eventflushchunksize'
            ]
        )
        options.deduplicate_events = True
        log = Mock(name='logger.log', spec_set=['debug', 'warn'])

        self.eqm = EventQueueManager(options, log)
        self.eqm._initQueues()

    def test_initQueues(self):
        options = Mock(
            name='options',
            spec_set=['maxqueuelen', 'deduplicate_events']
        )
        options.deduplicate_events = True
        log = Mock(name='logger.log', spec_set=[])

        eqm = EventQueueManager(options, log)
        eqm._initQueues()

        self.assertIsInstance(eqm.event_queue, DeDupingEventQueue)
        self.assertEqual(eqm.event_queue.maxlen, options.maxqueuelen)
        self.assertIsInstance(eqm.perf_event_queue, DeDupingEventQueue)
        self.assertEqual(eqm.perf_event_queue.maxlen, options.maxqueuelen)
        self.assertIsInstance(eqm.heartbeat_event_queue, collections.deque)
        self.assertEqual(eqm.heartbeat_event_queue.maxlen, 1)

    def test_transformEvent(self):
        '''a transformer mutates and returns an event
        '''
        def transform(event):
            event['transformed'] = True
            return event

        transformer = Mock(name='transformer', spec_set=['transform'])
        transformer.transform.side_effect = transform
        self.eqm.transformers = [transformer]

        event = {}
        ret = self.eqm._transformEvent(event)

        self.assertEqual(ret, event)
        self.assertEqual(event, {'transformed': True})

    def test_transformEvent_drop(self):
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

        self.eqm.transformers = [transformer, transformer_2]

        event = {}
        ret = self.eqm._transformEvent(event)
        self.assertEqual(ret, None)

    def test_transformEvent_stop(self):
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

        self.eqm.transformers = [transformer, transformer_2]

        event = {}
        ret = self.eqm._transformEvent(event)
        self.assertIs(ret, event)

    def test_clearFingerprint(self):
        event = {k: k + '_v' for k in self.eqm.CLEAR_FINGERPRINT_FIELDS}

        ret = self.eqm._clearFingerprint(event)

        self.assertEqual(
            ret, ('device_v', 'component_v', 'eventKey_v', 'eventClass_v')
        )

    def test__removeDiscardedEventFromClearState(self):
        '''if the event's fingerprint is in clear_events_count
        decrement its value
        '''
        self.eqm.options.allowduplicateclears = False
        self.eqm.options.duplicateclearinterval = 0

        discarded = {'severity': Clear}
        clear_fingerprint = self.eqm._clearFingerprint(discarded)
        self.eqm.clear_events_count[clear_fingerprint] = 3

        self.eqm._removeDiscardedEventFromClearState(discarded)

        self.assertEqual(self.eqm.clear_events_count[clear_fingerprint], 2)

    def test__addEvent(self):
        '''remove the event from clear_events_count
        and append it to the queue
        '''
        self.eqm.options.allowduplicateclears = False

        queue = Mock(name='queue', spec_set=['append'])
        event = {}
        clear_fingerprint = self.eqm._clearFingerprint(event)
        self.eqm.clear_events_count = {clear_fingerprint: 3}

        self.eqm._addEvent(queue, event)

        self.assertNotIn(clear_fingerprint, self.eqm.clear_events_count)
        queue.append.assert_called_with(event)

    def test__addEvent_status_clear(self):
        self.eqm.options.allowduplicateclears = False
        self.eqm.options.duplicateclearinterval = 0

        queue = Mock(name='queue', spec_set=['append'])
        event = {'severity': Clear}
        clear_fingerprint = self.eqm._clearFingerprint(event)

        self.eqm._addEvent(queue, event)

        self.assertEqual(self.eqm.clear_events_count[clear_fingerprint], 1)
        queue.append.assert_called_with(event)

    def test__addEvent_drop_duplicate_clear_events(self):
        self.eqm.options.allowduplicateclears = False
        clear_count = 1

        queue = Mock(name='queue', spec_set=['append'])
        event = {'severity': Clear}
        clear_fingerprint = self.eqm._clearFingerprint(event)
        self.eqm.clear_events_count = {clear_fingerprint: clear_count}

        self.eqm._addEvent(queue, event)

        # non-clear events are not added to the clear_events_count dict
        self.assertNotIn(self.eqm.clear_events_count, clear_fingerprint)

        queue.append.assert_not_called()

    def test__addEvent_drop_duplicate_clear_events_interval(self):
        self.eqm.options.allowduplicateclears = False
        clear_count = 3
        self.eqm.options.duplicateclearinterval = clear_count

        queue = Mock(name='queue', spec_set=['append'])
        event = {'severity': Clear}
        clear_fingerprint = self.eqm._clearFingerprint(event)
        self.eqm.clear_events_count = {clear_fingerprint: clear_count}

        self.eqm._addEvent(queue, event)

        # non-clear events are not added to the clear_events_count dict
        self.assertNotIn(self.eqm.clear_events_count, clear_fingerprint)
        queue.append.assert_not_called()

    def test__addEvent_counts_discarded_events(self):
        queue = Mock(name='queue', spec_set=['append'])
        event = {}
        discarded_event = {'name': 'event'}
        queue.append.return_value = discarded_event

        self.eqm._removeDiscardedEventFromClearState = create_autospec(
            self.eqm._removeDiscardedEventFromClearState,
        )
        self.eqm._discardedEvents.mark = create_autospec(
            self.eqm._discardedEvents.mark
        )

        self.eqm._addEvent(queue, event)

        self.eqm._removeDiscardedEventFromClearState.assert_called_with(
            discarded_event
        )
        self.eqm._discardedEvents.mark.assert_called_with()
        self.assertEqual(self.eqm.discarded_events, 1)

    def test_addEvent(self):
        self.eqm._addEvent = create_autospec(self.eqm._addEvent)
        event = {}
        self.eqm.addEvent(event)

        self.eqm._addEvent.assert_called_with(self.eqm.event_queue, event)

    def test_addPerformanceEvent(self):
        self.eqm._addEvent = create_autospec(self.eqm._addEvent)
        event = {}
        self.eqm.addPerformanceEvent(event)

        self.eqm._addEvent.assert_called_with(self.eqm.perf_event_queue, event)

    def test_addHeartbeatEvent(self):
        self.eqm.heartbeat_event_queue = Mock(
            spec_set=self.eqm.heartbeat_event_queue
        )
        heartbeat_event = {}
        self.eqm.addHeartbeatEvent(heartbeat_event)

        self.eqm.heartbeat_event_queue.append.assert_called_with(
            heartbeat_event
        )

    def test_sendEvents(self):
        '''chunks events from EventManager's queues
        yields them to the event_sender_fn
        and returns a deffered with a result of events sent count
        '''
        self.eqm.options.eventflushchunksize = 3
        self.eqm.options.maxqueuelen = 5
        self.eqm._initQueues()
        heartbeat_events = [{'heartbeat': i} for i in range(2)]
        perf_events = [{'perf_event': i} for i in range(2)]
        events = [{'event': i} for i in range(2)]

        self.eqm.heartbeat_event_queue.extendleft(heartbeat_events)
        # heartbeat_event_queue set to static maxlen=1
        self.assertEqual(len(self.eqm.heartbeat_event_queue), 1)
        self.eqm.perf_event_queue.extendleft(perf_events)
        self.eqm.event_queue.extendleft(events)

        event_sender_fn = Mock(name='event_sender_fn')

        ret = self.eqm.sendEvents(event_sender_fn)

        # Priority: heartbeat, perf, event
        event_sender_fn.assert_has_calls([
            call([heartbeat_events[1], perf_events[0], perf_events[1]]),
            call([events[0], events[1]]),
        ])
        self.assertIsInstance(ret, defer.Deferred)
        self.assertEqual(ret.result, 5)

    def test_sendEvents_exception_handling(self):
        '''In case of exception, places events back in the queue,
        and remove clear state for any discarded events
        '''
        self.eqm.options.eventflushchunksize = 3
        self.eqm.options.maxqueuelen = 5
        self.eqm._initQueues()
        heartbeat_events = [{'heartbeat': i} for i in range(2)]
        perf_events = [{'perf_event': i} for i in range(2)]
        events = [{'event': i} for i in range(2)]

        self.eqm.heartbeat_event_queue.extendleft(heartbeat_events)
        self.eqm.perf_event_queue.extendleft(perf_events)
        self.eqm.event_queue.extendleft(events)

        def event_sender_fn(args):
            raise Exception('event_sender_fn failed')

        ret = self.eqm.sendEvents(event_sender_fn)
        # validate Exception was raised
        self.assertEqual(ret.result.check(Exception), Exception)
        # quash the unhandled error in defferd exception
        ret.addErrback(Mock())

        # Heartbeat events get dropped
        self.assertNotIn(heartbeat_events[1], self.eqm.heartbeat_event_queue)
        # events and perf_events are returned to the queues
        self.assertIn(perf_events[0], self.eqm.perf_event_queue)
        self.assertIn(events[0], self.eqm.event_queue)

    def test_sendEvents_exception_removes_clear_state_for_discarded(self):
        self.eqm.options.eventflushchunksize = 3
        self.eqm.options.maxqueuelen = 2
        self.eqm._initQueues()
        events = [{'event': i} for i in range(2)]

        self.eqm.event_queue.extendleft(events)

        def send(args):
            self.eqm.event_queue.append({'new_event': 0})
            raise Exception('event_sender_fn failed')

        event_sender_fn = Mock(name='event_sender_fn', side_effect=send)

        self.eqm._removeDiscardedEventFromClearState = create_autospec(
            self.eqm._removeDiscardedEventFromClearState,
            name='_removeDiscardedEventFromClearState'
        )

        ret = self.eqm.sendEvents(event_sender_fn)
        # validate Exception was raised
        self.assertEqual(ret.result.check(Exception), Exception)
        # quash the unhandled error in differd exception
        ret.addErrback(Mock())

        event_sender_fn.assert_called_with([events[0], events[1]])

        self.eqm._removeDiscardedEventFromClearState.assert_called_with(
            events[0]
        )


class PBDaemonClassTest(TestCase):
    '''PBDaemon's __init__ modifies the class attribute heartbeatEvent
    so we have to test it separately
    '''

    # WARNING: this test fails when running all ZenHub tests together, needs investigation
    def test_class_attributes(self):
        from Products.ZenHub.PBDaemon import PBDaemon
        self.assertEqual(PBDaemon.name, 'pbdaemon')
        self.assertEqual(PBDaemon.initialServices, ['EventService'])
        # this is the problem line, heartbeatEvent differs
        # /opt/zenoss/bin/runtests --type=unit --name Products.ZenHub.tests.test_PBDaemon
        # self.assertEqual(PBDaemon.heartbeatEvent, {'eventClass': '/Heartbeat'})
        # /opt/zenoss/bin/runtests --type=unit --name Products.ZenHub
        # self.assertEqual(
        #    PBDaemon.heartbeatEvent,
        #    {'device': 'localhost', 'eventClass': '/Heartbeat', 'component': 'pbdaemon'}
        #)
        self.assertEqual(PBDaemon.heartbeatTimeout, 60 * 3)
        self.assertEqual(PBDaemon._customexitcode, 0)
        self.assertEqual(PBDaemon._pushEventsDeferred, None)
        self.assertEqual(PBDaemon._eventHighWaterMark, None)
        self.assertEqual(PBDaemon._healthMonitorInterval, 30)



class PBDaemonTest(TestCase):

    def setUp(self):
        # Patch external dependencies
        # current version touches the reactor directly
        self.reactor_patcher = patch(
            '{src}.reactor'.format(**PATH), autospec=True
        )
        self.reactor = self.reactor_patcher.start()

        self.name = 'pb_daemon_name'
        self.pbd = PBDaemon(name=self.name)

        self.pbd.eventQueueManager = Mock(
            EventQueueManager, name='eventQueueManager'
        )

    def tearDown(self):
        self.reactor_patcher.stop()

    @patch('{src}.task.LoopingCall'.format(**PATH),
           name='task.LoopingCall', autospec=True)
    @patch('{src}.stopEvent'.format(**PATH),
           name='stopEvent', autospec=True)
    @patch('{src}.startEvent'.format(**PATH),
           name='startEvent', autospec=True)
    @patch('{src}.DaemonStats'.format(**PATH),
           name='DaemonStats', autospec=True)
    @patch('{src}.EventQueueManager'.format(**PATH),
           name='EventQueueManager', autospec=True)
    @patch('{src}.ZenDaemon.__init__'.format(**PATH),
           name='ZenDaemon.__init__', autospec=True)
    def test___init__(
        self,
        ZenDaemon_init,
        EventQueueManager,
        DaemonStats,
        startEvent,
        stopEvent,
        LoopingCall
    ):
        noopts = 0,
        keeproot = False
        # attributes set by parent class
        options = Mock(name='options', spec_set=['monitor'])
        log = Mock(name='log', spec_set=['debug'])
        PBDaemon.options = options
        PBDaemon.log = log

        pbd = PBDaemon(noopts=noopts, keeproot=keeproot, name=self.name)

        # runs parent class init
        # this should really be using super(
        ZenDaemon_init.assert_called_with(pbd, noopts, keeproot)

        self.assertEqual(pbd.name, self.name)
        self.assertEqual(pbd.mname, self.name)

        EventQueueManager.assert_called_with(options, log)

        # Check lots of attributes, should verify that they are needed
        self.assertEqual(pbd._thresholds, None)
        self.assertEqual(pbd._threshold_notifier, None)
        self.assertEqual(pbd.rrdStats, DaemonStats.return_value)
        self.assertEqual(pbd.lastStats, 0)
        self.assertEqual(pbd.perspective, None)
        self.assertEqual(pbd.services, {})
        self.assertEqual(pbd.eventQueueManager, EventQueueManager.return_value)
        self.assertEqual(pbd.startEvent, startEvent.copy())
        self.assertEqual(pbd.stopEvent, stopEvent.copy())

        # appends name and device to start, stop, and heartbeat events
        details = {'component': self.name, 'device': options.monitor}
        pbd.startEvent.update.assert_called_with(details)
        pbd.stopEvent.update.assert_called_with(details)
        self.assertEqual(
            pbd.heartbeatEvent,
            {
                'device': options.monitor,
                'eventClass': '/Heartbeat',
                'component': 'pb_daemon_name'
            }
        )

        # more attributes
        self.assertIsInstance(pbd.initialConnect, defer.Deferred)
        self.assertEqual(pbd.stopped, False)
        self.assertIsInstance(pbd.counters, collections.Counter)
        self.assertEqual(pbd._pingedZenhub, None)
        self.assertEqual(pbd._connectionTimeout, None)
        self.assertEqual(pbd._publisher, None)  # should be a property
        self.assertEqual(pbd._internal_publisher, None)
        self.assertEqual(pbd._metric_writer, None)
        self.assertEqual(pbd._derivative_tracker, None)
        self.assertEqual(pbd._metrologyReporter, None)

        # Add a shutdown trigger to send a stop event and flush the event queue
        self.reactor.addSystemEventTrigger.assert_called_with(
            'before', 'shutdown', pbd._stopPbDaemon
        )

        # Set up a looping call to support the health check.
        self.assertEqual(pbd.healthMonitor, LoopingCall.return_value)
        LoopingCall.assert_called_with(pbd._checkZenHub)
        pbd.healthMonitor.start.assert_called_with(pbd._healthMonitorInterval)

    @patch('{src}.ZenDaemon.__init__'.format(**PATH), side_effect=IOError)
    def test__init__exit_on_ZenDaemon_IOError(self, ZenDaemon):
        # self.log is set by a parent class
        PBDaemon.log = Mock(name='log')
        with self.assertRaises(SystemExit):
            PBDaemon()

    # this should be a property
    @patch('{src}.publisher'.format(**PATH), autospec=True)
    def test_publisher(self, publisher):
        pbd = PBDaemon(name=self.name)
        host = 'localhost'
        port = 9999
        pbd.options.redisUrl = 'http://{}:{}'.format(host, port)

        ret = pbd.publisher()

        self.assertEqual(ret, publisher.RedisListPublisher.return_value)
        publisher.RedisListPublisher.assert_called_with(
            host, port, pbd.options.metricBufferSize,
            channel=pbd.options.metricsChannel,
            maxOutstandingMetrics=pbd.options.maxOutstandingMetrics
        )

    @patch('{src}.publisher'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    def test_internalPublisher(self, os, publisher):
        # All the methods with this pattern need to be converted to properties
        self.assertEqual(self.pbd._internal_publisher, None)
        url = Mock(name='url', spec_set=[])
        username = 'username'
        password = 'password'
        os.environ = {
            'CONTROLPLANE_CONSUMER_URL': url,
            'CONTROLPLANE_CONSUMER_USERNAME': username,
            'CONTROLPLANE_CONSUMER_PASSWORD': password,
        }

        ret = self.pbd.internalPublisher()

        self.assertEqual(ret, publisher.HttpPostPublisher.return_value)
        publisher.HttpPostPublisher.assert_called_with(username, password, url)

        self.assertEqual(self.pbd._internal_publisher, ret)

    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.MetricWriter'.format(**PATH), autospec=True)
    def test_metricWriter_legacy(self, MetricWriter, os):
        self.assertEqual(self.pbd._metric_writer, None)

        self.pbd.publisher = create_autospec(self.pbd.publisher)
        self.pbd.internalPublisher = create_autospec(
            self.pbd.internalPublisher
        )
        os.environ = {'CONTROLPLANE': '0'}

        ret = self.pbd.metricWriter()

        MetricWriter.assert_called_with(self.pbd.publisher())
        self.assertEqual(ret, MetricWriter.return_value)
        self.assertEqual(self.pbd._metric_writer, ret)

    @patch('{src}.AggregateMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.FilteredMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.MetricWriter'.format(**PATH), autospec=True)
    def test_metricWriter_controlplane(
        self, MetricWriter, os, FilteredMetricWriter, AggregateMetricWriter
    ):
        self.assertEqual(self.pbd._metric_writer, None)

        self.pbd.publisher = create_autospec(
            self.pbd.publisher, name='publisher'
        )
        self.pbd.internalPublisher = create_autospec(
            self.pbd.internalPublisher, name='internalPublisher'
        )
        os.environ = {'CONTROLPLANE': '1'}

        ret = self.pbd.metricWriter()

        MetricWriter.assert_called_with(self.pbd.publisher())
        AggregateMetricWriter.assert_called_with([
            MetricWriter.return_value,
            FilteredMetricWriter.return_value
        ])
        self.assertEqual(ret, AggregateMetricWriter.return_value)
        self.assertEqual(self.pbd._metric_writer, ret)

    @patch('{src}.DerivativeTracker'.format(**PATH), autospec=True)
    def test_derivativeTracker(self, DerivativeTracker):
        self.assertEqual(self.pbd._derivative_tracker, None)

        ret = self.pbd.derivativeTracker()

        self.assertEqual(ret, DerivativeTracker.return_value)
        self.assertEqual(self.pbd._derivative_tracker, ret)

    def test_connecting(self):
        # logs a message, noop
        self.pbd.connecting()

    def test_getZenhubInstanceId(self):
        # returns a deferred, should be replaced with inlineCallbacks
        perspective = Mock(name='perspective', spec_set=['callRemote'])
        self.pbd.perspective = perspective

        ret = self.pbd.getZenhubInstanceId()

        self.assertEqual(ret, perspective.callRemote.return_value)
        perspective.callRemote.assert_called_with('getHubInstanceId')

    def test_gotPerspective(self):
        perspective = Mock(name='perspective', spec_set=['callRemote'])
        _connectionTimeout = Mock(
            spec_set=self.pbd._connectionTimeout, name='_connectionTimeout'
        )
        self.pbd._connectionTimeout = _connectionTimeout
        getInitialServices = Mock(name='getInitialServices', spec_set=[])
        self.pbd.getInitialServices = getInitialServices
        initialConnect = Mock(name='initialConnect', spec_set=[])
        self.pbd.initialConnect = initialConnect

        self.pbd.gotPerspective(perspective)

        # sets the perspective attribute
        self.assertEqual(self.pbd.perspective, perspective)
        #  if _connectionTimeoutcall is set call _connectionTimeout.cancel()
        _connectionTimeout.cancel.assert_called_with()
        self.assertEqual(self.pbd._connectionTimeout, None)
        # if initialConnect is set, it is set to None,
        # and executed after getInitialServices as a deferred
        getInitialServices.assert_called_with()
        d2 = getInitialServices.return_value
        self.assertEqual(self.pbd.initialConnect, None)
        d2.chainDeferred.assert_called_with(initialConnect)

    @patch(
        '{src}.credentials'.format(**PATH), name='credentials', autospec=True
    )
    @patch(
        '{src}.ReconnectingPBClientFactory'.format(**PATH),
        name='ReconnectingPBClientFactory', autospec=True
    )
    def test_connect(self, ReconnectingPBClientFactory, credentials):
        factory = ReconnectingPBClientFactory.return_value
        options = self.pbd.options
        connectTimeout = Mock(self.pbd.connectTimeout, name='connectTimeout')
        self.pbd.connectTimeout = connectTimeout

        ret = self.pbd.connect()

        # ensure the connection factory is setup properly
        factory.connectTCP.assert_called_with(
            options.hubhost, options.hubport
        )
        self.assertEqual(factory.gotPerspective, self.pbd.gotPerspective)
        self.assertEqual(factory.connecting, self.pbd.connecting)
        credentials.UsernamePassword.assert_called_with(
            options.hubusername, options.hubpassword
        )
        factory.setCredentials.assert_called_with(
            credentials.UsernamePassword.return_value
        )

        # connectionTimeout is set
        self.assertEqual(
            self.pbd._connectionTimeout, self.reactor.callLater.return_value
        )

        # returns pbd.initialconnect, not sure where the factory goes
        self.assertEqual(ret, self.pbd.initialConnect)

        # test timeout method passed to reactor.callLater
        # unpack the args to get the timeout function
        args, kwargs = self.reactor.callLater.call_args
        timeout = args[1]
        d = Mock(defer.Deferred, name='initialConnect.result')
        d.called = False
        timeout(d)
        connectTimeout.assert_called_with()

    def test_connectTimeout(self):
        '''logs a message and passes,
        not to be confused with _connectionTimeout, which is set to a deferred
        '''
        self.pbd.connectTimeout()

    def test_eventService(self):
        # alias for getServiceNow
        self.pbd.getServiceNow = create_autospec(self.pbd.getServiceNow)
        self.pbd.eventService()
        self.pbd.getServiceNow.assert_called_with('EventService')

    def test_getServiceNow(self):
        svc_name = 'svc_name'
        self.pbd.services[svc_name] = 'some service'
        ret = self.pbd.getServiceNow(svc_name)
        self.assertEqual(ret, self.pbd.services[svc_name])

    @patch('{src}.FakeRemote'.format(**PATH), autospec=True)
    def test_getServiceNow_FakeRemote_on_missing_service(self, FakeRemote):
        ret = self.pbd.getServiceNow('svc_name')
        self.assertEqual(ret, FakeRemote.return_value)

    def test_getService_known_service(self):
        self.pbd.services['known_service'] = 'service'
        ret = self.pbd.getService('known_service')

        self.assertIsInstance(ret, defer.Deferred)
        self.assertEqual(ret.result, self.pbd.services['known_service'])

    def test_getService(self):
        '''this is going to be ugly to test,
        and badly needs to be rewritten as an inlineCallback
        '''
        perspective = Mock(name='perspective', spec_set=['callRemote'])
        serviceListeningInterface = Mock(
            name='serviceListeningInterface', spec_set=[]
        )
        self.pbd.perspective = perspective
        service_name = 'service_name'

        ret = self.pbd.getService(service_name, serviceListeningInterface)

        perspective.callRemote.assert_called_with(
            'getService', service_name, self.pbd.options.monitor,
            serviceListeningInterface, self.pbd.options.__dict__
        )
        self.assertEqual(ret, perspective.callRemote.return_value)

        # Pull the callbacks out of ret, to make sure they work as intended
        args, kwargs = ret.addCallback.call_args
        callback = args[0]
        # callback adds the service to pbd.services
        ret_callback = callback(ret.result, service_name)
        self.assertEqual(self.pbd.services[service_name], ret.result)
        # the service (result) has notifyOnDisconnect called with removeService
        args, kwargs = ret_callback.notifyOnDisconnect.call_args
        removeService = args[0]
        # removeService
        removeService(service_name)
        self.assertNotIn(service_name, self.pbd.services)

    @patch('{src}.defer'.format(**PATH), autospec=True)
    def test_getInitialServices(self, defer):
        '''execute getService(svc_name) for every service in initialServices
        in parallel deferreds
        '''
        getService = create_autospec(self.pbd.getService, name='getService')
        self.pbd.getService = getService
        ret = self.pbd.getInitialServices()

        defer.DeferredList.assert_called_with(
            [self.pbd.getService.return_value
             for svc in self.pbd.initialServices],
            fireOnOneErrback=True,
            consumeErrors=True
        )
        getService.assert_has_calls(
            [call(svc) for svc in self.pbd.initialServices]
        )

        self.assertEqual(ret, defer.DeferredList.return_value)

    def test_connected(self):
        # does nothing
        self.pbd.connected()

    @patch('{src}.ThresholdNotifier'.format(**PATH), autospec=True)
    def test__getThresholdNotifier(self, ThresholdNotifier):
        # refactor to be a property
        self.assertEqual(self.pbd._threshold_notifier, None)
        ret = self.pbd._getThresholdNotifier()

        ThresholdNotifier.assert_called_with(
            self.pbd.sendEvent, self.pbd.getThresholds()
        )
        self.assertEqual(ret, ThresholdNotifier.return_value)
        self.assertEqual(self.pbd._threshold_notifier, ret)

    @patch('{src}.Thresholds'.format(**PATH), autospec=True)
    def test_getThresholds(self, Thresholds):
        # refactor to be a property
        self.assertEqual(self.pbd._thresholds, None)

        ret = self.pbd.getThresholds()

        Thresholds.assert_called_with()
        self.assertEqual(ret, Thresholds.return_value)
        self.assertEqual(self.pbd._thresholds, ret)

    @patch('{src}.sys'.format(**PATH), autospec=True)
    @patch('{src}.task'.format(**PATH), autospec=True)
    @patch('{src}.TwistedMetricReporter'.format(**PATH), autospec=True)
    def test_run(self, TwistedMetricReporter, task, sys):
        '''Starts up all of the internal loops,
        does not return until reactor.run() completes (reactor is shutdown)
        '''
        self.pbd.rrdStats = Mock(spec_set=self.pbd.rrdStats)
        self.pbd.connect = create_autospec(self.pbd.connect)
        self.pbd._customexitcode = 99

        self.pbd.run()

        # adds startStatsLoop to reactor.callWhenRunning
        args, kwargs = self.reactor.callWhenRunning.call_args
        startStatsLoop = args[0]
        ret = startStatsLoop()
        task.LoopingCall.assert_called_with(self.pbd.postStatistics)
        loop = task.LoopingCall.return_value
        loop.start.assert_called_with(
            self.pbd.options.writeStatistics, now=False
        )
        daemonTags = {
            'zenoss_daemon': self.pbd.name,
            'zenoss_monitor': self.pbd.options.monitor,
            'internal': True
        }
        TwistedMetricReporter.assert_called_with(
            self.pbd.options.writeStatistics,
            self.pbd.metricWriter(),
            daemonTags
        )
        self.assertEqual(
            self.pbd._metrologyReporter, TwistedMetricReporter.return_value
        )
        self.pbd._metrologyReporter.start.assert_called_with()

        # adds stopReporter (defined internally) to reactor before shutdown
        args, kwargs = self.reactor.addSystemEventTrigger.call_args
        stopReporter = args[2]
        self.assertEqual(args[0], 'before')
        self.assertEqual(args[1], 'shutdown')
        ret = stopReporter()
        self.assertEqual(ret, self.pbd._metrologyReporter.stop.return_value)
        self.pbd._metrologyReporter.stop.assert_called_with()

        self.pbd.rrdStats.config.assert_called_with(
            self.pbd.name,
            self.pbd.options.monitor,
            self.pbd.metricWriter(),
            self.pbd._getThresholdNotifier(),
            self.pbd.derivativeTracker()
        )

        # returns a deferred, that has a callback added to it
        # but we have no access to it from outside the function
        self.pbd.connect.assert_called_with()

        self.reactor.run.assert_called_with()
        # only calls sys.exit if a custom exitcode is set, should probably
        # exit even if exitcode = 0
        sys.exit.assert_called_with(self.pbd._customexitcode)

    def test_setExitCode(self):
        exitcode = Mock()
        self.pbd.setExitCode(exitcode)
        self.assertEqual(self.pbd._customexitcode, exitcode)

    def test_stop(self):
        # stops the reactor and handles ReactorNotRunning
        self.reactor.running = True
        self.pbd.stop()
        self.reactor.stop.assert_called_with()

    def test__stopPbDaemon(self):
        # set stopped=True, and send a stopEvent
        self.assertFalse(self.pbd.stopped)
        self.pbd.services['EventService'] = True
        self.pbd.options.cycle = True
        self.pbd.sendEvent = Mock(self.pbd.sendEvent, name='sendEvent')
        self.pbd.pushEvents = Mock(self.pbd.pushEvents, name='pushEvents')

        ret = self.pbd._stopPbDaemon()

        self.assertTrue(self.pbd.stopped)

        # send a stopEvent if it has an EventService
        self.pbd.sendEvent.assert_called_with(self.pbd.stopEvent)
        self.assertEqual(ret, self.pbd.pushEvents.return_value)

    def test__stopPbDaemon_pushEventsDeferred(self):
        # if _pushEventsDeferred is set, append a new pushEvents deffered to it
        self.pbd._pushEventsDeferred = Mock(
            defer.Deferred, name='_pushEventsDeferred'
        )
        self.assertFalse(self.pbd.stopped)
        self.pbd.services['EventService'] = True
        self.pbd.options.cycle = True
        self.pbd.sendEvent = Mock(self.pbd.sendEvent, name='sendEvent')
        self.pbd.pushEvents = Mock(self.pbd.pushEvents, name='pushEvents')

        ret = self.pbd._stopPbDaemon()

        self.assertTrue(self.pbd.stopped)

        # send a stopEvent if it has an EventService
        self.pbd.sendEvent.assert_called_with(self.pbd.stopEvent)
        self.assertEqual(ret, self.pbd._pushEventsDeferred)
        # unable to test pushEvents added as callback
        # blocked by maybe unneccesary lambda

    def test_sendEvents(self):
        # simply maps events to sendEvent
        self.pbd.sendEvent = Mock(self.pbd.sendEvent, name='sendEvent')
        events = [{'name': 'evt_a'}, {'name': 'evt_b'}]

        self.pbd.sendEvents(events)

        self.pbd.sendEvent.assert_has_calls(
            [call(event) for event in events]
        )

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
                'manager': t.pbd.fqdn
            }
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
            ret,
            'var/{}_{}_counters.pickle'.format(
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
        #ret = t.pbd.remote_updateThresholdClasses(['class_a', 'class_b'])
        #t.assertEqual(ret, 'something')

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

    @patch('{src}.publisher'.format(**PATH), autospec=True)
    def test_buildOptions(t, publisher):
        '''After initialization, the InvalidationWorker instance should have
        options parsed from its buildOptions method
        assertions based on default options
        '''
        # rebuild pbd with patched publisher
        t.pbd = PBDaemon()
        from Products.ZenHub.PBDaemon import (
            DEFAULT_HUB_HOST, DEFAULT_HUB_PORT,
            DEFAULT_HUB_USERNAME, DEFAULT_HUB_PASSWORD,
            DEFAULT_HUB_MONITOR
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
        t.assertEqual(
            t.pbd.options.redisUrl,
            'redis://localhost:{default}/0'.format(
                default=publisher.defaultRedisPort)
        )
        t.assertEqual(
            t.pbd.options.metricBufferSize, publisher.defaultMetricBufferSize
        )
        t.assertEqual(
            t.pbd.options.metricsChannel, publisher.defaultMetricsChannel
        )
        t.assertEqual(
            t.pbd.options.maxOutstandingMetrics,
            publisher.defaultMaxOutstandingMetrics
        )
        t.assertEqual(t.pbd.options.pingPerspective, True)
        t.assertEqual(t.pbd.options.writeStatistics, 30)
