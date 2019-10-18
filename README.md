# Zenoss Prodbin
A repository for several Zenoss Products, including the User Interface


## [Testing](tests/)


## Installation
The Zenoss Prodbin is not a standard Python package.  It is designed to work as Zope "local instance" Products, and as such, do not install into the site-packages directory like a normal Python distribution.  In addition, there is a binary executable, zensocket, provided by this package which does not conform to standard Python packaging conventions.

The included makefile provides the following targets:

   build - Build the distribution artifact (default)
   install - Configure the repository as an editable package.

NOTE: the *install* target assumes an environment where /opt/zenoss is the base path for where the Python installation lives.  Additionally, the 'Products' directory in this repo must be accessable as /opt/zenoss/Products.

See [Zenoss product-assembly](https://github.com/zenoss/product-assembly)
