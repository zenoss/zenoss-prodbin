from Products.ZenHub.HubService import HubService

class TestService(HubService):

    def remote_echo(self, value):
        return value

