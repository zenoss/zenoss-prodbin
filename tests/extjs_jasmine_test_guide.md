# Prodbin ExtJS Unit Testing with Jasmine


## Run Unit Tests
1. Link /opt/zenoss to your zenhome directory

    `sudo ln -s <path to>/zenhome /opt/zenoss`

2. Open Jasmine/SpecRunner.html in a browser.

    `file:///<path to>/zenoss-prodbin/Products/ZenUI3/browser/resources/js/jasmine/SpecRunner.html?`


## Creating new Unit Tests
### Create or Update a spec.js
Jasmine Spec files should match 1to1 with the code-under-test.  If we are testing zenoss/date.js, its spec file will be zenoss/tests/date_spec.js

| Source                 | Spec
|------------------------|-----
| source_file.js         | source_file_spec.js
| Ext.namespace          | describe("Ext.namespace", function() {
| Ext.namespace.method() | it('.method behaves this way', function(){


### Add new spec files to SpecRunner.html
Using relative paths, add the file-under-test and its spec file to SpecRunner

```
  <!-- include source under test -->
  <script src="../zenoss/date.js"></script>
  <script src="../zenoss/<your source>.js"></script>

  <!-- include spec files here... -->
  <script src="../zenoss/tests/date_spec.js"></script>
  <script src="../zenoss/tests/<your source>_spec.js"></script>
```

Run your tests by refreshing the jasmine window in your browser.

If need be, add required js source under `<!-- include source files here... -->`

### Check for missing tests!
Its a good idea to run Jasmine with your browser console open, and look for messages that indicate load errors.

`Failed to load resource: net::ERR_FILE_NOT_FOUND ... missing_file.js`

Deprecation warnings also show up here.

## Reference
- [Step by Step Guide for Unit Testing ExtJS Application using Jasmine](https://www.codeproject.com/Articles/662832/Step-by-Step-Guide-for-Unit-Testing-ExtJS-Applicat)
- [Official ExtJS Guide](http://docs.sencha.com/extjs/4.1.3/#!/guide/testing)
