from unittest import TestCase
from mock import Mock, patch

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
