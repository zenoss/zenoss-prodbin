#!/usr/bin/env python

import base64
import logging
import Globals
from twisted.internet import reactor
from Products.ZenUtils.Utils import xorCryptString
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.DataCollector.SshClient import SshClient
from Products.ZenUtils.Utils import DictAsObj
log = logging.getLogger("zen.SshClient")

def write(text):
    print text

class ExecuteSSH(ZenScriptBase):
    def run(self):
        ssh_options = DictAsObj(
            loginTries=self.options.login_tries,
            searchPath=self.options.search_path,
            existenceTest=self.options.existance_test,
            username=xorCryptString(self.options.username, decode=True),
            password=xorCryptString(self.options.password, decode=True),
            loginTimeout=self.options.login_timeout,
            commandTimeout=self.options.command_timeout,
            keyPath=self.options.key_path,
            concurrentSessions=self.options.concurrent_sessions,
        )
        connection = SshClient(self.options.device_name, #device.title
                               self.options.host,
                               self.options.port,
                               options=ssh_options)
        cmd = self.options.cmd
        connection.clientFinished = reactor.stop
        connection.workList.append(cmd)
        connection._commands.append(cmd)
        connection.run()
        reactor.run()
        for x in connection.getResults():
            [write(y) for y in x if y]

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('--cmd',
                               default=None,
                               help='command')
        self.parser.add_option('--device_name',
                               default=None,
                               help='device name')
        self.parser.add_option('--host',
                               default=None,
                               help='host')
        self.parser.add_option('--username',
                               default=None,
                               help='username')
        self.parser.add_option('--password',
                               default=None,
                               help='password')
        self.parser.add_option('--port',
                               type='int',
                               default=22,
                               help='port')
        self.parser.add_option('--login_tries',
                               type='int',
                               default=1,
                               help='login tries')
        self.parser.add_option('--search_path',
                               default=[],
                               help='search path')
        self.parser.add_option('--existance_test',
                               default=None,
                               help='existance test')
        self.parser.add_option('--login_timeout',
                               type='float',
                               default=10.0,
                               help='login timeout')
        self.parser.add_option('--command_timeout',
                               type='float',        	
                               default=15.0,
                               help='command timeout')
        self.parser.add_option('--key_path',
                               default='~/.ssh/id_dsa',
                               help='key path')
        self.parser.add_option('--concurrent_sessions',
                               type='int',        	
                               default=5,
                               help='concurrent sessions')


if __name__ == '__main__':
    ssh = ExecuteSSH()
    ssh.run()

