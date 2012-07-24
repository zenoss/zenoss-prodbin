/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


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
