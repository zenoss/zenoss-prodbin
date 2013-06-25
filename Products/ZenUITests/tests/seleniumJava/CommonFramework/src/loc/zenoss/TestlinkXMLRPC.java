/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss;

import java.net.MalformedURLException;
import java.net.URL;
import java.util.ArrayList;
import java.util.Hashtable;
import java.util.Map;
import loc.zenoss.ZenossConstants;
import org.apache.xmlrpc.XmlRpcException;
import org.apache.xmlrpc.client.XmlRpcClient;
import org.apache.xmlrpc.client.XmlRpcClientConfigImpl;

public class TestlinkXMLRPC {

	

	/**
	 * 
	 * @param tcid Testcase ID
	 * @param tpid TestPlan ID
	 * @param status values are f = fail, b = blocked and p = pass
	 * @return
	 */
	public static boolean UpdateTestCaseResult(int tcid, int tpid, String status)
	{
		try 
		{
			XmlRpcClient rpcClient;
			XmlRpcClientConfigImpl config;
			
			config = new XmlRpcClientConfigImpl();
			config.setServerURL(new URL(ZenossConstants.TestLinkAPIURL));
			rpcClient = new XmlRpcClient();
			rpcClient.setConfig(config);		
			
			ArrayList<Object> params = new ArrayList<Object>();
			Hashtable<String, Object> executionData = new Hashtable<String, Object>();				
			executionData.put("devKey", ZenossConstants.TestLinkAPIKEY);
			executionData.put("tcid", tcid);
			executionData.put("tpid", tpid);
			executionData.put("status", status);
			params.add(executionData);
			
			Object[] result = (Object[]) rpcClient.execute("tl.reportTCResult", params);

			// Typically you'd want to validate the result here and probably do something more useful with it
			System.out.println("Result was:\n");				
			for (int i=0; i< result.length; i++)
			{
				Map item = (Map)result[i];
				System.out.println("Keys: " + item.keySet().toString() + " values: " + item.values().toString());
			}
			return true;
		}
		catch (MalformedURLException e)
		{
			e.printStackTrace();
		}
		catch (XmlRpcException e)
		{
			e.printStackTrace();
		}
		return false;
	}
	 
}
