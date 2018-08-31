from unittest import TestCase
from mock import Mock, patch

from zope.interface.verify import verifyObject, DoesNotImplement

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
        worker_a = Mock(name='worker_a', spec_set=['busy'], busy=False)
        worker_b = Mock(name='worker_b', spec_set=['busy'], busy=True)
        worker_c = Mock(name='worker_c', spec_set=['busy'], busy=False)
        workers = [worker_a, worker_b, worker_c]

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

    @patch('{src}.getUtilitiesFor'.format(**PATH), autospec=True)
    def test__init__(t, getUtilitiesFor):
        getUtilitiesFor.return_value = [
            ('', t.default_selector), ('InOrderSelection', t.selector)
        ]

        ws = WorkerSelector(t.options)

        getUtilitiesFor.assert_called_with(IWorkerSelectionAlgorithm)
        t.assertEqual(
            ws.selectors,
            {'': t.default_selector, 'InOrderSelection': t.selector}
        )
        t.assertEqual(ws.defaultSelector, t.default_selector)

    @patch('{src}.getUtilitiesFor'.format(**PATH), autospec=True)
    def test_getCandidateWorkerIds(t, getUtilitiesFor):
        getUtilitiesFor.return_value = [
            ('', t.default_selector), ('InOrderSelection', t.selector)
        ]
        options = Mock(name='options', spec_set=[])
        ws = WorkerSelector(options)
        workerlist = []

        ret = ws.getCandidateWorkerIds(
            'InOrderSelection', workerlist=workerlist
        )

        t.selector.getCandidateWorkerIds.assert_called_with(
            workerlist, options
        )
        t.assertEqual(ret, t.selector.getCandidateWorkerIds.return_value)
