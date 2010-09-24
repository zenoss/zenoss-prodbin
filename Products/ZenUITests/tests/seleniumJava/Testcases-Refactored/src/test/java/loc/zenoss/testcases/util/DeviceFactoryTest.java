/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package loc.zenoss.testcases.util;

import org.junit.Test;
import loc.zenoss.Device;
import loc.zenoss.util.DeviceFactory;
import static org.junit.Assert.*;
/**
 *
 * @author bakeneko
 */
public class DeviceFactoryTest {

    @Test
    public void testGetDevice(){
      Device device = DeviceFactory.getInstance().getDevice("deviceCaso1");
      assertNotNull(device);
      assertEquals( "1",device.title);
    }

}
