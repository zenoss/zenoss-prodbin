from unittest import TestCase
from mock import Mock, patch, call, MagicMock, create_autospec

from Products.ZenHub.invalidations import (
    betterObjectEventNotify,
    defer,
    handle_oid,
    PrimaryPathObjectManager,
    DeviceComponent,
    DeletionEvent,
    UpdateEvent,
    InvalidationProcessor,
    IInvalidationProcessor,
    IITreeSet,
    IHubCreatedEvent,
    INVALIDATIONS_PAUSED,
)

from mock_interface import create_interface_mock

from zope.component import adaptedBy

"""
These tests are currently excellent examples of tests with excessive patching
and mocking, indicating a need to refactor the code under test.
Excessive patching indicates the function has too many side-effects
Complicated Mocks indicate it reaches too deeply into external objects
"""


class invalidationsTest(TestCase):
    @patch("Products.ZenHub.invalidations.getGlobalSiteManager", autospec=True)
    @patch("Products.ZenHub.invalidations.providedBy", autospec=True)
    @patch("Products.ZenHub.invalidations.giveTimeToReactor", autospec=True)
    def test_betterObjectEventNotify(
        self, giveTimeToReactor, providedBy, getGlobalSiteManager
    ):
        gsm = Mock(name="global_site_manager", spec_set=["adapters"])
        getGlobalSiteManager.return_value = gsm
        gsm.adapters = Mock(name="adapters", spec_set=["subscriptions"])
        subscriptions = [
            Mock(name="sub1", spec_set=[]),
            Mock(name="sub2", spec_set=[]),
        ]
        gsm.adapters.subscriptions.return_value = subscriptions

        event = Mock(name="event", spec_set=["object"])
        ret = betterObjectEventNotify(event)

        # Gets a list of subscriptions that adapt this event's interface
        gsm.adapters.subscriptions.assert_called_with(
            map(providedBy, (event.object, event)), None
        )
        # Call the subscription with the event, but wrap it in a deferred
        giveTimeToReactor.assert_has_calls(
            [
                call(subscription, event.object, event)
                for subscription in subscriptions
            ]
        )

        # InlineCallbacks return a Deferred
        self.assertIsInstance(ret, defer.Deferred)
        # Has no return value
        self.assertEqual(ret.result, None)

    def setUp(self):
        self.dmd = Mock(name="dmd", spec_set=["_p_jar"])
        # object must be of type PrimaryPathObjectManager or DeviceComponent
        self.obj = Mock(name="invalid type", spec_set=[])
        self.oid = "oid"
        self._p_jar = {self.oid: self.obj}
        self.dmd._p_jar = self._p_jar

    def test_handle_oid(self):
        """object must be of type PrimaryPathObjectManager or DeviceComponent
        or it will be dropped, and handle_oid returns None
        """
        self.assertFalse(isinstance(self.obj, PrimaryPathObjectManager))
        self.assertFalse(isinstance(self.obj, DeviceComponent))

        ret = handle_oid(self.dmd, self.oid)
        self.assertEqual(ret, None)

    @patch(
        "Products.ZenHub.invalidations.betterObjectEventNotify", autospec=True
    )
    def test_handle_oid_deletion(self, betterObjectEventNotify):
        # Replace test object with a valid type
        obj = MagicMock(
            PrimaryPathObjectManager,
            name="primary_path_object_manager",
        )
        self.dmd._p_jar = {self.oid: obj}
        self.assertEqual(obj, self.dmd._p_jar[self.oid])
        self.assertTrue(isinstance(obj, PrimaryPathObjectManager))

        # obj.__of__(dmd).primaryAq() ensures we get the primary path
        primary_aq = obj.__of__.return_value.primaryAq
        # raising a KeyError indicates a deleted object
        primary_aq.side_effect = KeyError()

        # Returns the result of betterObjectEventNotify(event)
        # where event is a new UpdateEvent or DeleteEvent instance
        # mock betterObjectEventNotify to pass back its one input
        betterObjectEventNotify.side_effect = lambda event: event

        # execute
        ret = handle_oid(self.dmd, self.oid)

        # validate side effects
        obj.__of__.assert_called_with(self.dmd)
        primary_aq.assert_called_once_with()

        # validate return value
        # should be a deferred wrapping a deletion event, yielded from BOEN
        # but we had to short-circut betterObjectEventNotify
        self.assertIsInstance(ret, DeletionEvent)

    @patch(
        "Products.ZenHub.invalidations.betterObjectEventNotify", autospec=True
    )
    def test_handle_oid_update(self, betterObjectEventNotify):
        # Replace test object with a valid type
        obj = MagicMock(
            PrimaryPathObjectManager,
            name="primary_path_object_manager",
        )
        self.dmd._p_jar = {self.oid: obj}

        # obj.__of__(dmd).primaryAq() ensures we get the primary path
        primary_aq = obj.__of__.return_value.primaryAq

        # Returns the result of betterObjectEventNotify(event)
        # where event is a new UpdateEvent or DeleteEvent instance
        # mock betterObjectEventNotify to pass back its one input
        betterObjectEventNotify.side_effect = lambda event: event

        # execute
        ret = handle_oid(self.dmd, self.oid)

        # validate side effects
        obj.__of__.assert_called_with(self.dmd)
        primary_aq.assert_called_once_with()

        # validate return value
        # should be a deferred wrapping a deletion event,
        # yielded from betterObjectEventNotify
        # but we had to short-circut betterObjectEventNotify
        self.assertIsInstance(ret, UpdateEvent)


class InvalidationProcessorTest(TestCase):
    def setUp(self):
        self.patch_getGlobalSiteManager = patch(
            "Products.ZenHub.invalidations.getGlobalSiteManager", autospec=True
        )
        self.getGlobalSiteManager = self.patch_getGlobalSiteManager.start()

        self.ip = InvalidationProcessor()
        self.ip._hub = Mock(name="zenhub", spec_set=["dmd"])
        self.ip._hub_ready = Mock(name="_hub_ready_deferred")
        self.ip._invalidation_queue = Mock(spec_set=IITreeSet)

    def tearDown(self):
        self.patch_getGlobalSiteManager.stop()

    def test_init(self):
        IInvalidationProcessor.implementedBy(InvalidationProcessor)

        ip = InvalidationProcessor()

        IInvalidationProcessor.providedBy(ip)
        # current version cannot be verified, setHub attribute not provided
        # verifyObject(IInvalidationProcessor, processor)

        self.assertIsInstance(ip._invalidation_queue, IITreeSet)
        self.assertIsInstance(ip._hub_ready, defer.Deferred)
        # Registers its onHubCreated trigger, to wait for a HubCreated event
        gsm = self.getGlobalSiteManager.return_value
        gsm.registerHandler.assert_called_with(ip.onHubCreated)

    def test_onHubCreated(self):
        """this method gets triggered by a IHubCreatedEvent event"""
        # Is an adapter for IHubCreatedEvent type events
        self.assertEqual(
            list(adaptedBy(InvalidationProcessor.onHubCreated)),
            [IHubCreatedEvent],
        )

        IHubCreatedEventMock = create_interface_mock(IHubCreatedEvent)
        event = IHubCreatedEventMock()
        self.ip._hub_ready = Mock(spec_set=defer.Deferred)

        self.ip.onHubCreated(event)

        # _hub is set to the hub specified in the IHubCreatedEvent
        self.assertEqual(self.ip._hub, event.hub)
        # the _hub_ready deffered gets called back / triggered
        self.ip._hub_ready.callback.assert_called_with(self.ip._hub)

    @patch("Products.ZenHub.invalidations.u64", autospec=True)
    def test_processQueue(self, u64):
        self.ip._hub.dmd.pauseHubNotifications = False
        self.ip._dispatch = create_autospec(self.ip._dispatch)

        oids = ["oid1", "oid2", "oid3"]
        ret = self.ip.processQueue(oids)

        u64.assert_has_calls([call(oid) for oid in oids])
        self.ip._invalidation_queue.insert.assert_has_calls(
            [call(u64.return_value) for _ in oids]
        )
        # WARNING: intended to return i>0 if successful, will currently
        # reutrn 0 if a single oid passed in, even if successful
        self.assertEqual(ret.result, len(oids) - 1)

    def test_processQueue_paused(self):
        self.ip._hub.dmd.pauseHubNotifications = True

        ret = self.ip.processQueue("oids")

        self.assertEqual(ret.result, INVALIDATIONS_PAUSED)

    @patch("Products.ZenHub.invalidations.handle_oid", autospec=True)
    def test_dispatch(self, handle_oid):
        handle_oid.fail = "derp"

        dmd = self.ip._hub.dmd
        oid = "oid"
        ioid = "ioid"
        queue = self.ip._invalidation_queue

        ret = self.ip._dispatch(dmd, oid, ioid, queue)

        handle_oid.assert_called_with(dmd, oid)
        queue.remove.assert_called_with(ioid)

        self.assertEqual(ret, handle_oid.return_value)
