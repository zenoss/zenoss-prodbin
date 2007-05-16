Hotfix-20070320 README

    This hotfix corrects a cross-site scripting vulnerability in Zope2,
    where an attacker can use a hidden GET request to leverage a 
    authenticated user's credentials to alter security settings and/or
    user accounts.

    Note that this fix only protects against GET requests, any site that
    allows endusers to create auto-submitting forms (through javascript)
    will remain vulnerable.
    
    The hotfix may be removed after upgrading to a version of Zope2 more
    recent than this hotfix.

  Affected Versions

    - Zope 2.8.0 - 2.8.8

    - Zope 2.9.0 - 2.9.6

    - Zope 2.10.0 - 2.10.2
    
    - Earlier versions of Zope 2 are affected as well, but no new
      releases for older major Zope releases (Zope 2.7 and earlier) will
      be made. This Hotfix may work for older versions, but this has not
      been tested.
    
  Installing the Hotfix

    This hotfix is installed as a standard Zope2 product.  The following
    examples assume that your Zope instance is located at
    '/var/zope/instance':  please adjust according to your actual
    instance path.  Also note that hotfix products are *not* intended
    for installation into the "software home" of your Zope.

      1. Unpack the tarball / zipfile for the Hotfix into a temporary
         location::

          $ cd /tmp
          $ tar xzf ~/Hotfix_20070320.tar.gz

      2. Copy or move the product directory from the unpacked directory
         to the 'Products' directory of your Zope instance::

          $ cp -a /tmp/Hotfix_20070320/ /var/zope/instance/Products/

      3. Restart Zope::

          $ /var/zope/instance/bin/zopectl restart

  Uninstalling the Hotfix

    After upgrading Zope to one of the fixed versions, you should remove
    this hotfix product from your Zope instance.

      1. Remove the product directory from your instance 'Products'::

          $ rm -rf /var/zope/instance/Products/Hotfix_20070320/

      2. Restart Zope::

          $ /var/zope/instance/bin/zopectl restart

  References

    CVE -- "CVE-2007-0240":http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2007-0240
