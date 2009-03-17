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
    __call__ = ZopeTwoPageTemplateFile('templates/adddevice.pt')

    @json
    def default_communities(self):
        devclass = self.context.dmd.Devices.Discovered.primaryAq()
        return '\n'.join(devclass.zSnmpCommunities)

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
            'zSnmpCommunities': self.request.form.get('snmpcommunities')
        }
        # Split rows into networks and ranges
        nets = []
        ranges = []
        for row in submitted:
            if _is_network(row): nets.append(row)
            elif _is_range(row): ranges.append(row)
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
        # Create jobs based on info passed
        for k in devs:
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
                    'zSnmpCommunity': self.request.form.get(
                        'snmpcomm_%s' % idx
                    )
                }
            self.context.JobManager.addJob(DeviceCreationJob,
                deviceName=self.request.form.get(k),
                devicePath=devclass,
                zProperties = zProps)
        devnames = [self.request.form.get(dev) for dev in devs]
        IMessageSender(self.context).sendToUser(
            'Devices Added',
            'Modeling of the following devices has been scheduled: %s' % (
                ', '.join(devnames)
            )
        )
        response.redirect('/zport/dmd')
        return response


class OrganizeDevicesView(BrowserView):
    """
    Configure device classes.
    """
    __call__ = ZopeTwoPageTemplateFile('templates/organizedevices.pt')


class CreateCustomGroupsView(BrowserView):
    """
    Configure device groups.
    """
    __call__ = ZopeTwoPageTemplateFile('templates/customgroups.pt')

