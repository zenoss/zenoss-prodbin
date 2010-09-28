/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
 */

package loc.zenoss.util;

import java.util.Properties;
import java.util.logging.Level;
import java.util.logging.Logger;
import loc.zenoss.Device;
import org.apache.commons.beanutils.BeanUtils;
import org.apache.commons.configuration.Configuration;
import org.apache.commons.configuration.ConfigurationException;
import org.apache.commons.configuration.PropertiesConfiguration;

/**
 *
 * @author wquesada
 */
public class DeviceFactory {

    private static DeviceFactory deviceFactory;
    private Configuration config;

    private DeviceFactory() {
        try {
            config = new PropertiesConfiguration("devices.properties");
        } catch (ConfigurationException ex) {
            Logger.getLogger(DeviceFactory.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

    public static DeviceFactory getInstance() {
        if (deviceFactory == null) {
            deviceFactory = new DeviceFactory();
        }
        return deviceFactory;
    }

    public Device getDevice(String deviceCase) {
        Device device = new Device();

        Properties prop = config.getProperties(deviceCase);
        try {
            BeanUtils.populate(device,prop);
        } catch (Exception ex) {
            Logger.getLogger(DeviceFactory.class.getName()).log(Level.SEVERE, null, ex);
        }
        return device;

    }
}
