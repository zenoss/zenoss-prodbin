##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenUtils.application import ApplicationState

_states = ApplicationState
_graph = {
    (_states.STOPPED,    'stop'): _states.STOPPED,
    (_states.RUNNING,    'stop'): _states.STOPPING,
    (_states.STOPPING,   'stop'): _states.STOPPING,
    (_states.RESTARTING, 'stop'): _states.STOPPING,
    (_states.STARTING,   'stop'): _states.STOPPING,

    (_states.STARTING,   'start'): _states.STARTING,
    (_states.RUNNING,    'start'): _states.RUNNING,
    (_states.STOPPED,    'start'): _states.STARTING,
    (_states.STOPPING,   'start'): _states.STARTING,
    (_states.RESTARTING, 'start'): _states.RESTARTING,

    (_states.STOPPED,    'restart'): _states.RESTARTING,
    (_states.RUNNING,    'restart'): _states.RESTARTING,
    (_states.STOPPING,   'restart'): _states.RESTARTING,
    (_states.STARTING,   'restart'): _states.STARTING,
    (_states.RESTARTING, 'restart'): _states.RESTARTING,

    (_states.STARTING,   'found'): _states.RUNNING,
    (_states.RESTARTING, 'found'): _states.RUNNING,
    (_states.STOPPED,    'found'): _states.RUNNING,
    (_states.STOPPING,   'found'): _states.STOPPING,
    (_states.RUNNING,    'found'): _states.RUNNING,

    (_states.RUNNING,    'lost'): _states.STOPPED,
    (_states.RESTARTING, 'lost'): _states.RESTARTING,
    (_states.STOPPING,   'lost'): _states.STOPPED,
    (_states.STOPPED,    'lost'): _states.STOPPED,
    (_states.STARTING,   'lost'): _states.STARTING,
}


class RunStates(ApplicationState):

    def __init__(self):
        self._state = self.STOPPED

    @property
    def state(self):
        return self._state

    def stop(self):
        self._state = _graph[(self._state, "stop")]

    def start(self):
        self._state = _graph[(self._state, "start")]

    def restart(self):
        self._state = _graph[(self._state, "restart")]

    def found(self):
        self._state = _graph[(self._state, "found")]

    def lost(self):
        self._state = _graph[(self._state, "lost")]
