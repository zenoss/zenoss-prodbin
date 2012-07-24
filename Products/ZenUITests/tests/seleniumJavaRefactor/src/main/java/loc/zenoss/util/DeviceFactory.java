/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


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
