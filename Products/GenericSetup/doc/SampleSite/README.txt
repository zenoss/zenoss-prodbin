Sample Zope Site

  This is just an example for setting up some basic Zope objects. It doesn't
  create a useful Zope site. If you want to give it a try you first have to
  install this demo product by copying it to the Products folder of your
  INSTANCE_HOME.

  Please note that the setup steps shipped with this sample product are not
  compatible with 'toolset' or many third party setup steps.

  Creating your sample site:

    1. Add a 'Folder' named 'mySite'.

    2. Add a 'Generic Setup Tool' inside of 'mySite'.

    3. Go to the Properties tab of 'setup_tool', select 'Sample Zope Site'
       site configuration and make it active by pushing 'Update'.

    4. Go to the Import tab  of 'setup_tool' and 'Import all steps'. Done.

  You can also use this to create a snapshot of an existing plain Zope site:

    1. Add a 'Generic Setup Tool' inside the root of your site.

    2. Go to the Properties tab of 'setup_tool', select 'Sample Zope Site'
       site configuration and make it active by pushing 'Update'.

    3. Go to the Snapshots tab and push 'Create a Snapshot'. Done.
