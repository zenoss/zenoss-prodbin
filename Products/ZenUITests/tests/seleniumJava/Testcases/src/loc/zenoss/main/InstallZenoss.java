package loc.zenoss.main;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;

import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import ch.ethz.ssh2.Connection;
import ch.ethz.ssh2.Session;
import ch.ethz.ssh2.StreamGobbler;



public class InstallZenoss {
		
	
	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
				
	}

	@AfterClass
	public static void tearDownAfterClass() throws Exception {
		
	}

	@Before
	public void setUp() throws Exception {
	}

	@After
	public void tearDown() throws Exception {
	}
	
	
	
	@Test
	public void InstallZenossOnTargetMachine() throws Exception
	{
		String hostname = ZenossConstants.targetMachine;
		String username = ZenossConstants.sshUser;
		String password = ZenossConstants.sshPass;

		try
		{
			/* Create a connection instance */

			Connection conn = new Connection(hostname);

			/* Now connect */
			conn.connect();

			/* Authenticate.
			 */

			boolean isAuthenticated = conn.authenticateWithPassword(username, password);

			if (isAuthenticated == false)
				throw new IOException("Authentication failed.");

			/* Create a session */

			Session sess = conn.openSession();
			
			sess.execCommand("/bin/sh installZ.sh " + ZenossConstants.build +" "+ ZenossConstants.version + " " + ZenossConstants.installationPath);

			System.out.println("Waiting for Script execution");

			InputStream stdout = new StreamGobbler(sess.getStdout());
			InputStream stderr = new StreamGobbler(sess.getStderr());

			BufferedReader br = new BufferedReader(new InputStreamReader(stdout));
			BufferedReader brError = new BufferedReader(new InputStreamReader(stderr));
			while (true)
			{
				String line = br.readLine();
				String lineError = brError.readLine();
				if (line == null)
					break;
				if(line == "Installation of build " + ZenossConstants.build +" complete...")
					break;
				System.out.println("Normal: " + line);
				//System.out.println("Internal Console Log: " + lineError);
				
				if(sess.getExitStatus() != null)
					if(sess.getExitStatus() == 0)
						break;
			}

			//System.out.println("ExitCode: " + sess.getExitStatus());

			
			sess.close();

	
			conn.close();

		}
		catch (IOException e)
		{
			e.printStackTrace(System.err);
			System.exit(2);
		}
		
		
	}

	
	
	
	
	
	
}
