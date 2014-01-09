##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from celery.apps.worker import Worker
import signal

class CeleryZenWorker(Worker):
    """
    Extends Celery's Worker class to adjust some of the output
    during startup and to take control of signal handling.
    """

    # Create aliases to Worker's startup_info and extra_info so we can
    # invoke them in on_consumer_ready.
    _startupinfo = Worker.startup_info
    _extrainfo = Worker.extra_info

    # Override to disable base classes output
    def extra_info(self):
        pass

    # Override to disable base classes output
    def startup_info(self):
        return ''

    def on_consumer_ready(self, consumer):
        print ''.join([
                "Starting %s\n" % type(self).__name__,
                self._startupinfo(), (self._extrainfo() or '')
            ])
        super(CeleryZenWorker, self).on_consumer_ready(consumer)

    def install_platform_tweaks(self, worker):
        # This method installs the Celery's signal handling which conflicts
        # with Zenoss's signal handling.  Override it with so that the zenoss
        # USR1 handler is used
        #
        super(CeleryZenWorker, self).install_platform_tweaks(worker)
        signal.signal(signal.SIGUSR1, CeleryZenWorker.daemon.sighandler_USR1)
