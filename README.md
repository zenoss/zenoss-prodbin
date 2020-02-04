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


## Python Package style installation

Zenoss Prodbin now behaves more like an installable python package, with a few eccentricities


### install pydeps package

  1. `wget http://zenpip.zenoss.eng/packages/pydeps-5.6.0-el7-1.tar.gz`

  2. `tar -xf pydeps-5.6.0-el7-1.tar.gz`

  3. `pip install --no-index --find-links=pydeps-5.6.0-el7-1/wheelhouse -r pydeps-5.6.0-el7-1/requirements.txt wheel`

### symlink Products in sys.prefix (virtualenv root)

  * `ln -s /mnt/src/zenoss-prodbin/Products/ Products`

### install missing packages

**zenoss.protocols**

  * wget or use product-assembly to pull the latest version
  1. `wget http://zenpip.zenoss.eng/packages/zenoss.protocols-2.1.8-py2-none-any.whl`
  2. `pip install zenoss.protocols-2.1.8-py2-none-any.whl`

**modelindex**

  1. `wget http://zenpip.zenoss.eng/packages/modelindex-1.0.5.tar.gz`
  2. `mkdir modelindex`
  3. `tar -xf modelindex-1.0.5.tar.gz --directory modelindex`
  4. `pip install modelindex/dist/zenoss.modelindex*`

**servicemigration**

  1. `wget http://zenpip.zenoss.eng/packages/servicemigration-1.1.15-py2-none-any.whl`
  2. `pip install servicemigration-1.1.15-py2-none-any.whl`

### fix the kombu/utils/__init__.py bug

  * edit `.../envs/zenoss-prodbin/lib/python2.7/site-packages/kombu/utils/__init__.py`
    ```
    # PATCH: Fix import error in tests
    #- from uuid import UUID, uuid4 as _uuid4, _uuid_generate_random
    from uuid import UUID as _uuid4, uuid4 as _uuid_generate_random
    ```

### set ZENHOME environment variable

  * `export ZENHOME='/your/zenhome'`

After this, you should be able to run unit tests successfully, and import Products from your python interpreter.

### known issues:

#### ModuleNotFoundError: No module named 'Globals'

Fix by adding `import Globals` to the `__init__.py` file
