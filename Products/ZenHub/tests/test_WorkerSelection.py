from unittest import TestCase
from mock import Mock, patch

from zope.interface.verify import verifyObject

from Products.ZenHub.WorkerSelection import (
    InOrderSelection,
    IWorkerSelectionAlgorithm,
    ReservationAwareSelection,
    ReversedReservationAwareSelection,
    WorkerSelector,
)


PATH = {'src': 'Products.ZenHub.WorkerSelection'}


class InOrderSelectionTest(TestCase):

    def test_implements_IWorkerSelectionAlgorithm(t):
        ios = InOrderSelection()
        IWorkerSelectionAlgorithm.providedBy(ios)
        verifyObject(IWorkerSelectionAlgorithm, ios)

    def test_getCandidateWorkerIds(t):
        # returns a generator with the indices of the selected workers
        in_order_selection = InOrderSelection()
        workers = [
            Mock(name='worker_0', spec_set=['busy'], busy=False),
            Mock(name='worker_1', spec_set=['busy'], busy=True),
            Mock(name='worker_2', spec_set=['busy'], busy=False),
        ]

        ret = in_order_selection.getCandidateWorkerIds(workers, 'options')

        t.assertEqual(list(ret), [0, 2])


class ReservationAwareSelectionTest(TestCase):

    def test_implements_IWorkerSelectionAlgorithm(t):
        reservation_aware_select = ReservationAwareSelection()
        IWorkerSelectionAlgorithm.providedBy(reservation_aware_select)
        verifyObject(IWorkerSelectionAlgorithm, reservation_aware_select)

    def test_getCandidateWorkerIds(t):
        # returns a generator with the indices of the selected workers
        # reserves the first N workers returned by InOrderSelection
        ras = ReservationAwareSelection()
        workers = [
            Mock(name='worker_%s' % i, spec_set=['busy'], busy=False)
            for i in range(5)
        ]
        reserved = 3
        options = Mock(name='options', workersReservedForEvents=reserved)

        ret = ras.getCandidateWorkerIds(workers, options)

        t.assertEqual(list(ret), [3, 4])


class ReversedReservationAwareSelectionTest(TestCase):

    def test_implements_IWorkerSelectionAlgorithm(t):
        rras = ReversedReservationAwareSelection()
        IWorkerSelectionAlgorithm.providedBy(rras)
        verifyObject(IWorkerSelectionAlgorithm, rras)

    def test_getCandidateWorkerIds(t):
        # returns a generator with the indices of the selected workers
        # skips the first N workers returned by InOrderSelection, reversed
        rras = ReversedReservationAwareSelection()
        workers = [
            Mock(name='worker_%s' % i, spec_set=['busy'], busy=False)
            for i in range(5)
        ]
        reserved = 2
        options = Mock(name='options', workersReservedForEvents=reserved)

        ret = rras.getCandidateWorkerIds(workers, options)

        t.assertEqual(list(ret), [4, 3, 2])


class WorkerSelectorTest(TestCase):

    def setUp(t):
        t.default_selector = Mock(
            spec_set=InOrderSelection, name='default_selector'
        )
        t.selector = Mock(
            spec_set=InOrderSelection, name='InOrderSelection'
        )
        t.options = Mock(name='options', spec_set=[])
        t.get_utilities_patcher = patch(
            '{src}.getUtilitiesFor'.format(**PATH),
            autospec=True,
            return_value=[
                ('', t.default_selector), ('InOrderSelection', t.selector)
            ]
        )
        t.getUtilitiesFor = t.get_utilities_patcher.start()
        t.ws = WorkerSelector(t.options)

    def tearDown(t):
        t.get_utilities_patcher.stop()

    def test__init__(t):
        t.getUtilitiesFor.assert_called_with(IWorkerSelectionAlgorithm)
        t.assertEqual(
            t.ws.selectors,
            {'': t.default_selector, 'InOrderSelection': t.selector}
        )
        t.assertEqual(t.ws.defaultSelector, t.default_selector)

    def test_getCandidateWorkerIds(t):
        workerlist = []

        ret = t.ws.getCandidateWorkerIds(
            'InOrderSelection', workerlist=workerlist
        )

        t.selector.getCandidateWorkerIds.assert_called_with(
            workerlist, t.options
        )
        t.assertEqual(ret, t.selector.getCandidateWorkerIds.return_value)
