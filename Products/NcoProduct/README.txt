NcoProduct 1.0

NcoProduct is a Zope product that lets you build event lists for Micromuse's Omnibus event database (and with some extra work Oracle history server) from Zope.


Installation:

You will need (??) things to do the Omnibus Connectivity:
1. Latest version of NcoProduct
2. FreeTDS Stable Release (0.62.1)
	http://www.freetds.org 
3. Sybase Module for Python latest release (0.36)
	http://www.object-craft.com.au/projects/sybase/download.html
4. CFMCore from the CFM Zope framework. (1.3.3)
	http://cmf.zope.org/download/CMF-1.3.3/CMF-1.3.3.tar.gz


Build FreeTDS:

Use the normal configure, make, make install procedure to build freetds but you might want to add the --prefix option to configure so that it goes somewhere that you have defined.  You will need to set the SYBASE environment variable to point to this directory for the rest of the install to work.  Also you will need to setup your OS so that the runtime library loader knows how to find your SYBASE directory.  On linux you will need to modify /etc/ld.so.conf. On Solaris you will need to either set the LD_LIBRARY_PATH variable or run the crle command to change the search path.  On windows I have no idea!  If you figure it out let me know!


Building Python Module:

* Make sure that the SYBASE variable is pointing to your freetds directory.

* Make sure that you use the same python runtime that you use to run Zope (this will most likely not be a plain python command as shown below!!!).

* Build the C extension of the library by running this command:
    python setup.py build_ext -D HAVE_FREETDS -U WANT_BULKCOPY

* Install the library by running:
    python setup.py install
** Remember to use the version of python that you will use when running Zope, if you have the binary install this will be something like zope/bin/python.


Installing CMFCore:

* untar CMF-1.3.3

* copy the CMFCore directory to the zope products directory using something like:
    cp -r CMFCore ZOPEHOME/lib/python/Products


Installing NcoProduct:

* Untar NcoProduct in your Zope products directory (something like zope/lib/python/Products).
  
* Restart Zope so that it sees the package.  You can go to the Control Panel products directory and confirm that it loaded correctly.

* Now in the ZMI add an NcoProduct object  


Quick Guide to installing binary install of Zope:

* Download the binary install for your platform (Linux, Solaris, Windows) of Zope-2.6.x from http://zope.org/Products/Zope

* Untar 

* Install zope by running ./install

* copy the initial password that was assigned to the admin user

* Run zope by running ./start

* Login to zope with the url http://localhost:8080/manage using admin and your initial password

* Goto the acl_users folder and set the admin password to something you can remember!



Getting NcoProduct to work with Oracle History database:

Ok this is for the really ambitious!   
3. Oracle client libraries for the version of Oracle you are using 
4. DCOracle2
