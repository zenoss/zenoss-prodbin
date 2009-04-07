###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import re
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.ZenModel.ZDeviceLoader import DeviceCreationJob
from Products.ZenModel.IpNetwork import AutoDiscoveryJob
from Products.ZenWidgets.messaging import IMessageSender
from Products.ZenUtils import Ext
from Products.ZenUtils.json import json

_is_network = lambda x: bool(re.compile(r'^(\d+\.){3}\d+\/\d+$').search(x))
_is_range = lambda x: bool(re.compile(r'^(\d+\.){3}\d+\-\d+$').search(x))

class QuickstartBase(BrowserView):
    """
    Standard macros for the quickstart.
    """
    template = ZopeTwoPageTemplateFile('templates/quickstart_macros.pt')

    def __getitem__(self, key):
        return self.template.macros[key]


class OutlineView(BrowserView):
    """
    Displays the steps the user will soon be completing. The anticipation!
    """
    __call__ = ZopeTwoPageTemplateFile('templates/outline.pt')


class CreateUserView(BrowserView):
    """
    Creates the initial user and sets the admin password.
    """
    __call__ = ZopeTwoPageTemplateFile('templates/createuser.pt')


class DeviceAddView(BrowserView):
    """
    Specify devices to be added.
    """
    @json
    def default_communities(self):
        """
        Format the value of Devices.Discovered.zSnmpCommunities for a textarea
        """
        devclass = self.context.dmd.Devices.Discovered.primaryAq()
        return '\n'.join(devclass.zSnmpCommunities)

    @json
    def device_types(self):
        """
        Build an object for populating an Ext ComboBox representing "device
        types," which should exactly correspond to DeviceClasses in the system.

        This method iterates over a predetermined list of types we might want
        to see and checks each DeviceClass for existence (i.e., is the
        appropriate ZenPack installed?).
        """
        # Build the list of all possible types
        types = dict(
            win = [
                ('/Server/Windows/WMI', 'Windows Server', 'WMI')
            ],
            snmp = [
                ('/Server/Windows', 'Windows Server', 'SNMP'),
                ('/Server/Linux', 'Linux Server', 'SNMP'),
                ('/Network', 'Generic Switch/Router', 'SNMP'),
                ('/Network/Cisco', 'Cisco Device', 'SNMP'),
                ('/Network/BIG-IP', 'BIG-IP Device', 'SNMP'),
                ('/Network/Firewall/NetScreen', 'NetScreen Firewall', 'SNMP'),
                ('/Network/Check Point', 'CheckPoint Firewall', 'SNMP'),
                ('/Storage/Brocade', 'Brocade Storage', 'SNMP'),
                ('/Storage', 'NetApp Filer', 'SNMP'),
            ],
            ssh = [
                ('/Server/SSH/Linux', 'Linux Server', 'SSH'),
                ('/Server/SSH/AIX', 'AIX Server', 'SSH'),
            ])

        def dev_class_exists(path):
            """
            Return a boolean indicating whether the specified DeviceClass
            exists.
            """
            try:
                self.context.unrestrictedTraverse(
                    '/zport/dmd/Devices' + path)
            except AttributeError:
                return False
            else:
                return True

        def format_type(credtype, classpath, description, protocol):
            """
            Turn information representing a device class into a dictionary of
            the format our ComboBox expects.
            """
            value = '%s_%s' % (classpath, credtype)
            return dict(value=value, 
                        shortdesc="%s (%s)" % (description, protocol),
                        description=description, protocol=protocol)

        # Iterate over all types
        response = []
        for credtype, devtypes in types.iteritems():
            for devtype in devtypes:
                # Check for existence
                if dev_class_exists(devtype[0]):
                    # Exists, so add it to the list
                    response.append(format_type(credtype, *devtype))

        # Sort alphabetically by description
        response.sort(key=lambda x:x['description'])

        # Final response needs an object under a defined root, in this case
        # "types"
        return dict(types=response)


    @Ext.form_action
    def autodiscovery(self):
        response = Ext.FormResponse()
        submitted = self.request.form.get('network', [])
        if isinstance(submitted, basestring):
            submitted = [submitted]
        zProperties = {
            'zCommandUsername': self.request.form.get('sshusername'),
            'zCommandPassword': self.request.form.get('sshpass'),
            'zWinUser': self.request.form.get('winusername'),
            'zWinPassword': self.request.form.get('winpass'),
            'zSnmpCommunities': self.request.form.get('snmpcommunities').splitlines()
        }
        # Split rows into networks and ranges
        nets = []
        ranges = []
        for row in submitted:
            if _is_network(row): nets.append(row)
            elif _is_range(row): ranges.append(row)
        if not nets and not ranges:
            response.error('network',
                           'You must enter at least one network or IP range.')
        if nets:
            for net in nets:
                # Make the network if it doesn't exist, so zendisc has
                # something to discover
                _n = self.context.dmd.Networks.createNet(net)
            try:
                self.context.JobManager.addJob(
                    AutoDiscoveryJob,
                    nets=nets,
                    zProperties=zProperties)
            except:
                response.error('network', 'There was an error scheduling this '
                               'job. Please check your installation and try '
                               'again.')
            else:
                IMessageSender(self.context).sendToUser(
                    'Autodiscovery Task Created',
                    'Discovery of the following networks is in progress: %s' % (
                        ', '.join(ranges))
                )
        if ranges:
            # Ranges can just be sent to zendisc, as they are merely sets of
            # IPs
            try:
                self.context.JobManager.addJob(
                    AutoDiscoveryJob,
                    ranges=ranges,
                    zProperties=zProperties)
            except:
                response.error('network', 'There was an error scheduling this '
                               'job. Please check your installation and try '
                               'again.')
            else:
                IMessageSender(self.context).sendToUser(
                    'Autodiscovery Task Created',
                    'Discovery of the following IP ranges is in progress: %s' % (
                        ', '.join(ranges))
                )


        response.redirect('/zport/dmd')
        return response


    @Ext.form_action
    def manual(self):
        # Pull all the device name keys
        response = Ext.FormResponse()
        devs = filter(lambda x:x.startswith('device_'), 
                      self.request.form.keys())
        # Make sure we have at least one device name
        devnames = filter(lambda x:bool(self.request.form.get(x)), devs)
        if not devnames:
            response.error('device_1', 
                           'You must enter at least one hostname/IP.')
            return response
        # Create jobs based on info passed
        for k in devs:
            # Ignore empty device names
            if not self.request.form.get(k): continue
            idx = k.split('_')[1]
            devclass, type_ = self.request.form.get(
                'deviceclass_%s' % idx).split('_')
            # Set zProps based on type
            if type_=='ssh':
                zProps = { 
                    'zCommandUsername': self.request.form.get('sshuser_%s' % idx),
                    'zCommandPassword': self.request.form.get(
                        'sshpass_%s' % idx),
                }
            elif type_=='win':
                zProps = { 
                    'zWinUser': self.request.form.get('winuser_%s' % idx),
                    'zWinPassword': self.request.form.get('winpass_%s' % idx),
                }
            elif type_=='snmp':
                zProps = {
                    'zSnmpCommunities': self.request.form.get(
                        'snmpcomm_%s' % idx
                    ).splitlines()
                }
            self.context.JobManager.addJob(DeviceCreationJob,
                deviceName=self.request.form.get(k),
                devicePath=devclass,
                zProperties = zProps)
        devnames = [self.request.form.get(dev) for dev in devs]
        IMessageSender(self.context).sendToUser(
            'Devices Added',
            'Modeling of the following devices has been scheduled: %s' % (
                ', '.join(filter(None, devnames))
            )
        )
        response.redirect('/zport/dmd')
        return response

