##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase
from mock import patch, Mock, create_autospec, MagicMock, sentinel, call

from mock_interface import create_interface_mock

from Products.ZenHub.zenhub import ZenHub
from Products.ZenHub.invalidationmanager import (
    InvalidationManager,
    IInvalidationProcessor,
    IInvalidationFilter,
    PrimaryPathObjectManager,
    DeviceComponent,
    FILTER_INCLUDE,
    FILTER_EXCLUDE,
    POSKeyError,
    coroutine,
    iterate,
    oid_to_obj,
    filter_obj,
    transform_obj,
    InvalidationPipeline,
)


PATH = {'src': 'Products.ZenHub.invalidationmanager'}


class InvalidationManagerTest(TestCase):

    def setUp(t):
        t.get_utility_patcher = patch(
            '{src}.getUtility'.format(**PATH), autospec=True
        )
        t.getUtility = t.get_utility_patcher.start()
        t.addCleanup(t.get_utility_patcher.stop)

        t.dmd = Mock(
            name='dmd', spec_set=['getPhysicalRoot', 'pauseHubNotifications']
        )
        t.log = Mock(name='log', spec_set=['debug', 'warn'])
        t.syncdb = Mock(name='ZenHub.async_syncdb', spec_set=[])
        t.poll_invalidations = Mock(
            name='ZenHub.storage.poll_invalidations', spec_set=[]
        )

        t.send_event = Mock(ZenHub.sendEvent, name='ZenHub.sendEvent')
        t.im = InvalidationManager(
            t.dmd, t.log, t.syncdb, t.poll_invalidations, t.send_event
        )

    def test___init__(t):
        t.assertEqual(t.im._InvalidationManager__dmd, t.dmd)
        t.assertEqual(t.im.log, t.log)
        t.assertEqual(t.im._InvalidationManager__syncdb, t.syncdb)
        t.assertEqual(
            t.im._InvalidationManager__poll_invalidations,
            t.poll_invalidations
        )
        t.assertEqual(t.im._InvalidationManager__send_event, t.send_event)

        t.assertEqual(t.im._currently_paused, False)
        t.assertEqual(t.im.totalEvents, 0)
        t.assertEqual(t.im.totalTime, 0)
        t.getUtility.assert_called_with(IInvalidationProcessor)
        t.assertEqual(t.im.processor, t.getUtility.return_value)

    @patch('{src}.getUtilitiesFor'.format(**PATH), autospec=True)
    def test_initialize_invalidation_filters(t, getUtilitiesFor):
        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        filters = [MockIInvalidationFilter() for i in range(3)]
        # weighted in reverse order
        for i, filter in enumerate(filters):
            filter.weight = 10 - i
        getUtilitiesFor.return_value = [
            ('f%s' % i, f) for i, f in enumerate(filters)
        ]

        t.im.initialize_invalidation_filters()

        for filter in filters:
            filter.initialize.assert_called_with(t.dmd)

        # check sorted by weight
        filters.reverse()
        t.assertEqual(t.im._invalidation_filters, filters)

    @patch('{src}.time'.format(**PATH), autospec=True)
    def test_process_invalidations(t, time):
        '''synchronize with the database, and poll invalidated oids from it,
        filter the oids,  send them to the invalidation_processor
        '''
        timestamps = [10, 20]
        time.side_effect = timestamps
        t.im._paused = create_autospec(t.im._paused, return_value=False)
        t.poll_invalidations.return_value = [sentinel.oid]
        invalidation_pipeline = create_autospec(t.im.invalidation_pipeline)
        t.im.invalidation_pipeline = invalidation_pipeline

        t.im.process_invalidations()

        t.syncdb.assert_called_with()
        t.poll_invalidations.assert_called_with()
        t.im.invalidation_pipeline.run.assert_called_with(sentinel.oid)

        t.assertEqual(t.im.totalTime, timestamps[1] - timestamps[0])
        t.assertEqual(t.im.totalEvents, 1)

    def test__syncdb(t):
        t.im._syncdb()
        t.syncdb.assert_called_with()

    def test__paused_pause(t):
        t.im._currently_paused = False
        t.im._InvalidationManager__dmd.pauseHubNotifications = True

        ret = t.im._paused()

        t.assertEqual(ret, True)
        print(t.send_event)
        t.send_event.assert_called_with(t.im._invalidation_paused_event)

    def test__paused_currently_paused(t):
        t.im._currently_paused = True
        t.im._InvalidationManager__dmd.pauseHubNotifications = True

        ret = t.im._paused()

        t.assertEqual(ret, True)
        t.send_event.assert_not_called()

    def test__paused_unpause(t):
        t.im._currently_paused = True
        t.im._InvalidationManager__dmd.pauseHubNotifications = False

        ret = t.im._paused()

        t.assertEqual(ret, False)
        t.send_event.assert_called_with(t.im._invalidation_unpaused_event)

    def test_poll_invalidations(t):
        ret = t.im._poll_invalidations()
        t.assertEqual(ret, t.poll_invalidations.return_value)

    def test__send_event(t):
        t.im._send_event(sentinel.event)
        t.send_event.assert_called_with(sentinel.event)


class InvalidationPipelineTest(TestCase):
    '''A Pipeline that filters and transforms an invalidated oid,
    before sending it to IInvalidationProcessor
    '''

    @patch('{src}.getUtility'.format(**PATH), autospec=True)
    def test_invalidation_pipeline(t, getUtility):
        # constructor parameters
        app = MagicMock(name='dmd.root', spec_set=['_p_jar'])
        filters = [sentinel.filter_a, sentinel.filter_b]
        mIInvalidationProcessor = create_interface_mock(IInvalidationProcessor)
        processor = mIInvalidationProcessor()
        # Environment, and args
        device = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        device_obj = sentinel.device_obj
        device.__of__.return_value.primaryAq.return_value = device_obj
        oid = 111
        app._p_jar = {oid: device}

        invalidation_pipeline = InvalidationPipeline(app, filters, processor)
        invalidation_pipeline.run(oid)

        processor.processQueue.assert_called_with([oid])


class coroutine_Test(TestCase):

    def test_coroutine_decorator(t):
        '''Used to create our pipe segments.
        parameters configure the segment
        call .send(<args>) to provide input through yield
        '''

        @coroutine
        def magnitude(mag, output):
            while True:
                input = (yield)
                output.send(mag * input)

        output = Mock(spec_set=['send'])
        mag10 = magnitude(10, output)

        mag10.send(1)
        output.send.assert_called_with(10)
        mag10.send(2)
        output.send.assert_called_with(20)

    def test_iterate(t):
        '''Used to feed an iterable to a coroutine/input-pipe
        one item at a time
        '''
        output_pipe = Mock(set_spec=['send'])
        input_pipe = iterate(output_pipe)
        iterable = (i for i in range(10))

        input_pipe.send(iterable)

        output_pipe.send.assert_has_calls([call(i) for i in range(10)])


class oid_to_obj_Test(TestCase):

    def setUp(t):
        t.processor = Mock(
            name='InvalidationProcessor', spec_set=['processQueue']
        )
        t.out_pipe = Mock(name='output_pipe', spec_set=['send'])

    def test_oid_to_obj(t):
        device = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        device_obj = sentinel.device_obj
        device.__of__.return_value.primaryAq.return_value = device_obj
        app = sentinel.dmd_root
        app.zport = sentinel.zport
        app.zport.dmd = sentinel.dmd_root
        app._p_jar = {111: device}

        oid_to_obj_pipe = oid_to_obj(app, t.processor, t.out_pipe)
        oid_to_obj_pipe.send(111)

        t.out_pipe.send.assert_called_with((111, device_obj))

    def test__oid_to_object_poskeyerror(t):
        '''oids not found in dmd are considered deletions,
        and sent straight to the InvalidationProcessor
        '''
        app = MagicMock(name='dmd.root', spec_set=['_p_jar'])
        app._p_jar.__getitem__.side_effect = POSKeyError()

        oid_to_obj_pipe = oid_to_obj(app, t.processor, t.out_pipe)
        oid_to_obj_pipe.send(111)

        t.processor.processQueue.assert_called_with([111])

    def test__oid_to_object_deleted_primaryaq_keyerror(t):
        '''objects without a primaryAq ar considered deletions,
        and sent straight to the InvalidationProcessor
        '''
        deleted = MagicMock(DeviceComponent, __of__=Mock())
        deleted.__of__.return_value.primaryAq.side_effect = KeyError
        app = sentinel.dmd_root
        app._p_jar = {111: deleted}

        oid_to_obj_pipe = oid_to_obj(app, t.processor, t.out_pipe)
        oid_to_obj_pipe.send(111)

        t.processor.processQueue.assert_called_with([111])

    def test__oid_to_object_exclude_unsuported_types(t):
        '''Exclude any unspecified object types
        '''
        unsuported = MagicMock(name='unsuported type', __of__=Mock())
        app = sentinel.dmd_root
        app._p_jar = {111: unsuported}

        oid_to_obj_pipe = oid_to_obj(app, t.processor, t.out_pipe)
        oid_to_obj_pipe.send(111)

        t.processor.processQueue.assert_not_called()
        t.out_pipe.send.assert_not_called()


class filter_obj_Test(TestCase):
    '''Run the given object through each registered IInvalidationFilter
    drop any that are specifically Excluded by a filter
    '''

    def setUp(t):
        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        t.filter = MockIInvalidationFilter()

        t.included = sentinel.included
        t.excluded = sentinel.excluded

        def include(obj):
            if obj is t.included:
                print('include: %s' % obj)
                return FILTER_INCLUDE
            elif obj is t.excluded:
                print('exclude: %s' % obj)
                return FILTER_EXCLUDE
            else:
                print('default include: %s' % obj)
                return "FILTER_CONTINUE"

        t.filter.include = include

        t.out_pipe = Mock(name='output_pipe', spec_set=['send'])
        t.filter_object_pipe = filter_obj([t.filter], t.out_pipe)

    def test__filters_object(t):
        t.filter_object_pipe.send((111, t.included))
        t.out_pipe.send.assert_called_with((111, t.included))

    def test__filters_object_exclude(t):
        t.filter_object_pipe.send((111, t.excluded))
        t.out_pipe.send.assert_not_called()

    def test__filters_object_fallthrough(t):
        t.filter_object_pipe.send((111, sentinel.other))
        t.out_pipe.send.assert_called_with((111, sentinel.other))


class transform_obj_Test(TestCase):

    @patch('{src}.IInvalidationOid'.format(**PATH), autospec=True)
    @patch('{src}.subscribers'.format(**PATH), autospec=True)
    def test__transform_obj(t, subscribers, IInvalidationOid):
        '''given an oid: object pair
        gets a list of transforms for the object
        executes the transforms given the oid
        returns a set of oids returned by the transforms
        '''
        processor = Mock(
            name='InvalidationProcessor', spec_set=['processQueue']
        )
        adapter_a = Mock(
            name='adapter_a', spec_set=['transformOid'],
            transformOid=lambda x: x + '0'
        )
        subscribers.return_value = [adapter_a]
        adapter_b = Mock(
            name='adapter_b', spec_set=['transformOid'],
            transformOid=lambda x: [x + '1', x + '2']
        )
        IInvalidationOid.return_value = adapter_b
        oid = 'oid'
        obj = sentinel.object

        transform_pipe = transform_obj(processor)
        transform_pipe.send((oid, obj))

        processor.processQueue.assert_called_with({'oid0', 'oid1', 'oid2'})
