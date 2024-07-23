##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from automat import MethodicalMachine
from twisted.internet.task import LoopingCall
from zope.event import notify

from ...priority import ModelingPaused, PrioritySelection, ServiceCallPriority
from ...utils import getLogger

from .event import received
from .scheduler import Scheduler
from .task import ServiceCallTask
from .worklist import ZenHubWorklist


def _first_item(iterable):
    return list(iterable)[0]


class _ExecutorMachine(object):
    _machine = MethodicalMachine()

    def __init__(self, name, worklist, pool, max_retries, log):
        """
        @type name: str
        @type worklist: WorkList
        @type pool: WorkerPool
        @type log: logging.Logger
        """
        self._name = name
        self._worklist = worklist
        self._pool = pool
        self._max_retries = max_retries
        self._log = log
        self._scheduler = None

    @property
    def scheduler(self):
        return self._scheduler

    @_machine.state()
    def _starting(self):
        """
        The executor is starting/initializing the scheduler.
        """

    @_machine.state()
    def _running(self):
        """
        The executor is running.
        """

    @_machine.state()
    def _stopping(self):
        """
        The executor is still running, but no longer accepts or
        schedules tasks.
        """

    @_machine.state(initial=True)
    def _stopped(self):
        """
        The executor is not running.
        """

    @_machine.input()
    def start(self, clock):
        # type: (Self, twisted.internet.interfaces.IReactorTime) -> None
        """
        Start this executor, using the given clock to schedule tasks.

        @type clock: twisted.internet.interfaces.IReactorTime
        """

    @_machine.input()
    def submit(self, call):
        # type: (Self, ServiceCall) -> twisted.internet.defer.Deferred
        """Submit a task for execution.

        Returns a deferred that will fire when execution completes.

        @type call: ServiceCall
        @rtype: twisted.internet.defer.Deferred
        """

    @_machine.input()
    def stop(self):
        """
        Stop this executor.  No more tasks are scheduled but existing
        tasks will run to completion.
        """

    @_machine.input()
    def _accept_tasks(self):
        """
        Accept tasks for this executor to schedule.
        """

    @_machine.output()
    def _begin_scheduler(self, clock):
        self._scheduler = Scheduler(
            clock, self._name, self._worklist, self._pool, self._log
        )
        self._loop = LoopingCall(self._scheduler)
        self._loopd = self._loop.start(0)
        self._log.info("started scheduler  worklist=%s", self._name)
        self._accept_tasks()

    @_machine.output()
    def _add_task_to_worklist(self, call):
        task = ServiceCallTask(self._name, call, self._max_retries)
        task.mark_received()
        notify(received(task))
        self._worklist.push(task.priority, task)
        return task.deferred

    @_machine.output()
    def _stop_scheduler(self):
        self._loop.stop()
        self._loop = self._loopd = self._scheduler = None

    @_machine.output()
    def _not_ready_error(self):
        raise RuntimeError("Executor not ready to accept tasks")

    # State Transitions

    _stopped.upon(start, enter=_starting, outputs=[_begin_scheduler])
    _stopped.upon(stop, enter=_stopped, outputs=[])
    _stopped.upon(submit, enter=_stopped, outputs=[_not_ready_error])

    _starting.upon(start, enter=_starting, outputs=[])
    _starting.upon(_accept_tasks, enter=_running, outputs=[])

    _running.upon(start, enter=_running, outputs=[])
    _running.upon(
        submit,
        enter=_running,
        outputs=[_add_task_to_worklist],
        collector=_first_item,
    )
    _running.upon(stop, enter=_stopped, outputs=[_stop_scheduler])


class WorkerPoolExecutor(object):
    """An executor that executes service calls using remote workers."""

    @classmethod
    def create(cls, name, config=None, pool=None):
        """Return a new executor instance.

        :param str name: The executor's name
        :param IHubServerConfig config: Configuration data
        :param WorkerPool pool: Where the zenhubworker references live
        :return: A new WorkerPoolExecutor instance.
        """
        if config is None:
            raise ValueError("Invalid value for 'config': None")
        if pool is None:
            raise ValueError("Invalid value for 'pool': None")
        modeling_paused = ModelingPaused(
            config.priorities["modeling"],
            config.modeling_pause_timeout,
        )
        selection = PrioritySelection(
            ServiceCallPriority, exclude=modeling_paused
        )
        worklist = ZenHubWorklist(selection)
        return cls(name, worklist, pool, max_retries=config.task_max_retries)

    def __init__(self, name, worklist, pool, max_retries=3):
        """
        Initialize a WorkerPoolExecutor instance.

        @type name: str
        @type worklist: WorkList
        @type pool: WorkerPool
        """
        self._name = name
        self._worklist = worklist
        self._pool = pool
        self._log = getLogger(self)
        self._machine = _ExecutorMachine(
            name, worklist, pool, max_retries, self._log
        )

    @property
    def name(self):
        """Return the name of this executor."""
        return self._name

    @property
    def pool(self):
        """Return the pool of workers available to this executor."""
        return self._pool

    @property
    def worklist(self):
        """Return the worklist of tasks this executor will execute."""
        return self._worklist

    @property
    def scheduler(self):
        """Return the scheduler that will dispatch the tasks to the workers."""
        return self._machine.scheduler

    def start(self, reactor):
        """Start the executor."""
        self._machine.start(reactor)

    def stop(self):
        self._machine.stop()

    def submit(self, call):
        """Submit a ServiceCall for execution.

        Returns a deferred that will fire when execution completes.
        """
        return self._machine.submit(call)

    def __repr__(self):
        return "<{0.__class__.__name__} '{1}'>".format(self, self.__name)
