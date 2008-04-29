
class BaseClient(object):
    "Define the DataCollector Client interface"

    def __init__(self, device, datacollector):
        self.hostname = None
        if device:
            self.hostname = device.id
        self.device = device
        self.datacollector = datacollector
        self.timeout = None
        self.timedOut = False

    def run(self):
        pass

    def stop(self):
        pass

    def getResults(self):
        return []
    
