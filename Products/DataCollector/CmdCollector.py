from twisted.internet import reactor

import Globals

import SshClient
import TelnetClient

from DataCollector import DataCollector
from Exceptions import *

class CmdCollector(DataCollector):


    def collectDevice(self, device):
        device = self.resolveDevice(device)
        hostname = device.id
        commands = map(lambda x: x.command,self.selectPlugins(device,"command"))
        if not commands:
            self.log.warn("no commands found for %s" % hostname)
            return 
        protocol = getattr(device, 
                    'zCommandProtocol', defaultProtocol)
        commandPort = getattr(device, 'zCommandPort', defaultPort)
        if protocol == "ssh": 
            client = SshClient.SshClient(hostname, commandPort, 
                                options=self.options,
                                commands=commands, device=device, 
                                datacollector=self, log=self.log)
        elif protocol == 'telnet':
            if commandPort == 22: commandPort = 23 #set default telnet
            client = TelnetClient.TelnetClient(hostname, commandPort,
                                options=self.options,
                                commands=commands, device=device, 
                                datacollector=self, log=self.log)
        else:
            self.log.warn("unknown protocol %s for device %s",protocol,hostname)
        if not client: return
        self.clients[client] = 1
        client.run()
        if self.single:
            self.log.debug("reactor start single-device")
            reactor.run(False)




        


if __name__ == '__main__':
    cmdcoll = CmdCollector()
    cmdcoll.main()

