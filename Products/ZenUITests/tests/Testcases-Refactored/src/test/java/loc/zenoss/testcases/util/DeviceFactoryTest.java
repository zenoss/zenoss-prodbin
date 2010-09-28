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
package loc.zenoss.testcases.util;

import org.junit.Test;
import loc.zenoss.Device;
import loc.zenoss.util.DeviceFactory;
import static org.junit.Assert.*;
/**
 *
 * @author wquesada
 */
public class DeviceFactoryTest {

    @Test
    public void testGetDevice(){
      Device device = DeviceFactory.getInstance().getDevice("deviceCaso1");
      assertNotNull(device);
      assertEquals( "1",device.title);
    }

}
