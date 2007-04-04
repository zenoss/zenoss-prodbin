import Migrate

class HubQueue(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        if getattr(dmd, 'hubQueue', None) is None:
            from zc.queue import PersistentQueue
            dmd.hubQueue = PersistentQueue()

HubQueue()
