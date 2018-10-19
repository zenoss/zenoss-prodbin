##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase
from mock import patch, Mock, create_autospec, MagicMock, sentinel

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
    SEVERITY_CLEAR,
    INVALIDATIONS_PAUSED,
)


PATH = {'src': 'Products.ZenHub.invalidationmanager'}


class InvalidationManagerTest(TestCase):

    def setUp(t):
        t.get_utility_patcher = patch(
            '{src}.getUtility'.format(**PATH), autospec=True
        )
        t.getUtility = t.get_utility_patcher.start()
        t.addCleanup(t.get_utility_patcher.stop)

        t.dmd = Mock(name='dmd', spec_set=['getPhysicalRoot'])
        t.log = Mock(name='log', spec_set=['debug', 'warn'])
        t.syncdb = Mock(name='ZenHub.async_syncdb', spec_set=[])
        t.poll_invalidations = Mock(
            name='ZenHub.storage.poll_invalidations', spec_set=[]
        )
        t.send_event = create_autospec(ZenHub.sendEvent)

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

        t.assertEqual(t.im._invalidations_paused, False)
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
        t.im._filter_oids = create_autospec(t.im._filter_oids)
        timestamps = [10, 20]
        time.side_effect = timestamps

        t.im.process_invalidations()

        t.syncdb.assert_called_with()
        t.poll_invalidations.assert_called_with()
        t.im.processor.processQueue.assert_called_with(
            tuple(set(t.im._filter_oids(t.poll_invalidations.return_value)))
        )

        t.assertEqual(t.im.totalTime, timestamps[1] - timestamps[0])
        t.assertEqual(t.im.totalEvents, 1)

    def test__syncdb(t):
        t.im._syncdb()
        t.syncdb.assert_called_with()

    def test_poll_invalidations(t):
        ret = t.im._poll_invalidations()
        t.assertEqual(ret, t.poll_invalidations.return_value)

    def test__filter_oids(t):
        '''Configuration Invalidation Processing function
        yields a generator with the OID if the object has been deleted
        runs changed devices through invalidation_filters
        which may exclude them,
        and runs any included devices through _transformOid
        '''
        app = t.dmd.getPhysicalRoot.return_value

        device = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        device_obj = sentinel.device_obj
        device.__of__.return_value.primaryAq.return_value = device_obj
        component = MagicMock(DeviceComponent, __of__=Mock())
        component_obj = sentinel.component_obj
        component.__of__.return_value.primaryAq.return_value = component_obj
        excluded = Mock(DeviceComponent, __of__=Mock())
        excluded_obj = sentinel.excluded_obj
        excluded.__of__.return_value.primaryAq.return_value = excluded_obj
        excluded_type = Mock(name='ignored obj type', __of__=Mock())
        transformer = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        transf_obj = sentinel.transformer
        transformer.__of__.return_value.primaryAq.return_value = transf_obj

        app._p_jar = {
            111: device,
            222: component,
            333: excluded,
            444: excluded_type,
            555: transformer,
        }
        oids = app._p_jar.keys()

        def include(obj):
            if obj in [device_obj, component_obj]:
                return FILTER_INCLUDE
            if obj is sentinel.transformer:
                return FILTER_INCLUDE
            if obj == excluded_obj:
                return FILTER_EXCLUDE

        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        filter = MockIInvalidationFilter()
        filter.include = include
        t.im._invalidation_filters = [filter]

        def transform_oid(oid, obj):
            if oid in [111, 222]:
                return (oid,)
            if oid == 555:
                return {888, 999}

        t.im._transformOid = transform_oid

        ret = t.im._filter_oids(oids)
        out = {o for o in ret}  # unwind the generator

        t.assertEqual(out, {111, 222, 888, 999})

    def test__filter_oids_deleted(t):
        app = t.dmd.getPhysicalRoot.return_value = MagicMock(name='root')
        app._p_jar.__getitem__.side_effect = POSKeyError()

        ret = t.im._filter_oids([111])
        out = [o for o in ret]  # unwind the generator
        t.assertEqual(out, [111])

    def test__filter_oids_deleted_primaryaq(t):
        deleted = MagicMock(DeviceComponent, __of__=Mock())
        deleted.__of__.return_value.primaryAq.side_effect = KeyError
        with t.assertRaises(KeyError):
            deleted.__of__().primaryAq()

        app = t.dmd.getPhysicalRoot.return_value
        app._p_jar = {111: deleted}

        ret = t.im._filter_oids([111])
        out = [o for o in ret]
        t.assertEqual(out, [111])

    def test__oid_to_object(t):
        device = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        device_obj = sentinel.device_obj
        device.__of__.return_value.primaryAq.return_value = device_obj
        app = sentinel.dmd_root
        app._p_jar = {111: device}

        ret = t.im._oid_to_object(app, 111)

        t.assertEqual(ret, device_obj)

    def test__oid_to_object_poskeyerror(t):
        app = MagicMock(name='dmd.root', spec_set=['_p_jar'])
        app._p_jar.__getitem__.side_effect = POSKeyError()

        ret = t.im._oid_to_object(app, 111)

        t.assertEqual(ret, FILTER_INCLUDE)

    def test__oid_to_object_deleted_primaryaq_keyerror(t):
        deleted = MagicMock(DeviceComponent, __of__=Mock())
        deleted.__of__.return_value.primaryAq.side_effect = KeyError
        app = sentinel.dmd_root
        app._p_jar = {111: deleted}

        ret = t.im._oid_to_object(app, 111)

        t.assertEqual(ret, FILTER_INCLUDE)

    def test__oid_to_object_exclude_unsuported_types(t):
        unsuported = MagicMock(name='unsuported type', __of__=Mock())
        app = sentinel.dmd_root
        app._p_jar = {111: unsuported}

        ret = t.im._oid_to_object(app, 111)

        t.assertEqual(ret, FILTER_EXCLUDE)

    def test__apply_filters(t):
        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        filter = MockIInvalidationFilter()

        def include(obj):
            if obj is sentinel.included:
                return FILTER_INCLUDE
            elif obj is sentinel.excluded:
                return FILTER_EXCLUDE
            else:
                return "FILTER_CONTINUE"

        filter.include = include
        t.im._invalidation_filters = [filter]

        t.assertTrue(t.im._apply_filters(sentinel.included))
        t.assertFalse(t.im._apply_filters(sentinel.excluded))
        t.assertTrue(t.im._apply_filters(sentinel.other))

    @patch('{src}.IInvalidationOid'.format(**PATH), autospec=True)
    @patch('{src}.subscribers'.format(**PATH), autospec=True)
    def test__transformOid(t, subscribers, IInvalidationOid):
        '''Configuration Invalidation Processing function
        given an oid: object pair
        gets a list of transforms for the object
        executes the transforms given the oid
        returns a set of oids returned by the transforms
        '''
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

        ret = t.im._transformOid(oid, obj)

        t.assertEqual(ret, {'oid0', 'oid1', 'oid2'})

    def test__send_event(t):
        t.im._send_event(sentinel.event)
        t.send_event.assert_called_with(sentinel.event)

    def test__send_invalidations_unpaused_event(t):
        t.im._send_invalidations_unpaused_event(sentinel.msg)
        t.send_event.assert_called_with({
            'summary': sentinel.msg,
            'severity': SEVERITY_CLEAR,
            'eventkey': INVALIDATIONS_PAUSED
        })

    @patch('{src}.getUtility'.format(**PATH), autospec=True)
    def test__doProcessQueue(t, getUtility):
        '''Configuration Invalidation Processing function
        pulls in a dict of invalidations, and the IInvalidationProcessor
        and processes them, then sends an event
        refactor to use inline callbacks
        '''
        # storage is ZODB access inherited from a parent class
        t.im._filter_oids = create_autospec(t.im._filter_oids)

        t.im._doProcessQueue()

        getUtility.assert_called_with(IInvalidationProcessor)
        getUtility.return_value.processQueue.assert_called_with(
            tuple(set(t.im._filter_oids.return_value))
        )
