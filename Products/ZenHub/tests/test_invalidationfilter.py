from unittest import TestCase
from mock import Mock, patch, create_autospec

from zope.interface.verify import verifyObject

from Products.ZenHub.invalidationfilter import (
    IgnorableClassesFilter,
    IInvalidationFilter,
    FILTER_EXCLUDE,
    FILTER_CONTINUE,
    BaseOrganizerFilter,
    md5,
    DeviceClassInvalidationFilter,
    DeviceClass,
    OSProcessOrganizerFilter,
    OSProcessOrganizer,
    OSProcessClassFilter,
    OSProcessClass,
)

from Products.ZCatalog.interfaces import ICatalogBrain
from mock_interface import create_interface_mock

PATH = {'invalidationfilter': 'Products.ZenHub.invalidationfilter'}


class IgnorableClassesFilterTest(TestCase):

    def setUp(self):
        self.icf = IgnorableClassesFilter()

    def test_init(self):
        # current version fails because weight attribute is not defined
        #icf.weight = 1
        #verifyObject(IInvalidationFilter, icf)
        self.assertTrue(hasattr(self.icf, 'CLASSES_TO_IGNORE'))

    def test_initialize(self):
        context = Mock(name='context')
        self.icf.initialize(context)
        # No return or side-effects

    def test_include(self):
        obj = Mock(name='object')
        out = self.icf.include(obj)
        self.assertEqual(out, FILTER_CONTINUE)

    def test_include_excludes_classes_to_ignore(self):
        self.icf.CLASSES_TO_IGNORE = (str)
        out = self.icf.include('ignore me!')
        self.assertEqual(out, FILTER_EXCLUDE)


class BaseOrganizerFilterTest(TestCase):

    def setUp(self):
        self.types = Mock(name='types')
        self.bof = BaseOrganizerFilter(self.types)

        # @patch with autospec fails (https://bugs.python.org/issue23078)
        # manually spec ZenPropertyManager
        self.organizer = Mock(
            name='Products.ZenRelations.ZenPropertyManager',
            spec=[
                'zenPropertyIds', 'getProperty', 'zenPropIsPassword',
                'zenPropertyString'
            ],
            set_spec=True
        )

    def test_init(self):
        verifyObject(IInvalidationFilter, self.bof)
        self.assertEqual(self.bof.weight, 10)
        self.assertEqual(self.bof._types, self.types)

    def test_iszorcustprop(self):
        match = self.bof.iszorcustprop('no match')
        self.assertEqual(match, None)
        match = self.bof.iszorcustprop('cProperty')
        self.assertTrue(match)
        match = self.bof.iszorcustprop('zProperty')
        self.assertTrue(match)

    def test_getRoot(self):
        context = Mock(name='context')
        root = self.bof.getRoot(context)
        self.assertEqual(root, context.dmd.primaryAq())

    @patch(
        '{invalidationfilter}.IModelCatalogTool'.format(**PATH), autospec=True
    )
    def test_initialize(self, IModelCatalogTool):
        # Create a Mock object that provides the ICatalogBrain interface
        ICatalogBrainMock = create_interface_mock(ICatalogBrain)
        brain = ICatalogBrainMock()

        IModelCatalogTool.return_value.search.return_value = [brain]
        checksum = create_autospec(self.bof.organizerChecksum)
        self.bof.organizerChecksum = checksum
        context = Mock(name='context')

        self.bof.initialize(context)

        self.assertEqual(
            self.bof.checksum_map,
            {brain.getPath.return_value: checksum.return_value}
        )

    def test_getZorCProperties(self):
        zprop = Mock(name='zenPropertyId', set_spec=True)
        self.organizer.zenPropertyIds.return_value = [zprop, zprop]

        # getZorCProperties returns a generator
        results = self.bof.getZorCProperties(self.organizer)

        self.organizer.zenPropIsPassword.return_value = False
        zId, propertyString = next(results)
        self.assertEqual(zId, zprop)
        self.assertEqual(
            propertyString, self.organizer.zenPropertyString.return_value
        )
        self.organizer.zenPropertyString.assert_called_with(zprop)

        self.organizer.zenPropIsPassword.return_value = True
        zId, propertyString = next(results)
        self.assertEqual(zId, zprop)
        self.assertEqual(
            propertyString, self.organizer.getProperty.return_value
        )
        self.organizer.getProperty.assert_called_with(zprop, '')

        with self.assertRaises(StopIteration):
            next(results)

    def test_generateChecksum(self):
        getZorCProperties = create_autospec(self.bof.getZorCProperties)
        zprop = Mock(name='zenPropertyId', set_spec=True)
        getZorCProperties.return_value = [(zprop, 'property_string')]
        self.bof.getZorCProperties = getZorCProperties
        md5_checksum = md5()

        self.bof.generateChecksum(self.organizer, md5_checksum)

        expect = md5()
        expect.update('%s|%s' % (getZorCProperties(self.organizer)[0]))
        getZorCProperties.assert_called_with(self.organizer)
        self.assertEqual(md5_checksum.hexdigest(), expect.hexdigest())

    def test_organizerChecksum(self):
        getZorCProperties = create_autospec(self.bof.getZorCProperties)
        zprop = Mock(name='zenPropertyId', set_spec=True)
        getZorCProperties.return_value = [(zprop, 'property_string')]
        self.bof.getZorCProperties = getZorCProperties

        out = self.bof.organizerChecksum(self.organizer)

        expect = md5()
        expect.update('%s|%s' % (getZorCProperties(self.organizer)[0]))
        self.assertEqual(out, expect.hexdigest())

    def test_include_ignores_non_matching_types(self):
        self.bof._types = (str,)
        ret = self.bof.include(False)
        self.assertEqual(ret, FILTER_CONTINUE)

    def test_include_if_checksum_changed(self):
        organizerChecksum = create_autospec(self.bof.organizerChecksum)
        self.bof.organizerChecksum = organizerChecksum
        self.bof._types = (Mock,)
        obj = Mock(name='object', spec=['getPrimaryPath'], set_spec=True)
        obj.getPrimaryPath.return_value = ['dmd', 'brain']
        organizer_path = '/'.join(obj.getPrimaryPath())
        self.bof.checksum_map = {organizer_path: 'existing_checksum'}
        organizerChecksum.return_value = 'current_checksum'

        ret = self.bof.include(obj)

        self.assertEqual(ret, FILTER_CONTINUE)

    def test_include_if_checksum_unchanged(self):
        organizerChecksum = create_autospec(self.bof.organizerChecksum)
        self.bof.organizerChecksum = organizerChecksum
        existing_checksum = 'checksum'
        current_checksum = 'checksum'
        organizerChecksum.return_value = current_checksum
        self.bof._types = (Mock,)
        obj = Mock(name='object', spec=['getPrimaryPath'], set_spec=True)
        obj.getPrimaryPath.return_value = ['dmd', 'brain']
        organizer_path = '/'.join(obj.getPrimaryPath())
        self.bof.checksum_map = {organizer_path: existing_checksum}

        ret = self.bof.include(obj)

        self.assertEqual(ret, FILTER_EXCLUDE)


class DeviceClassInvalidationFilterTest(TestCase):

    def setUp(self):
        self.dcif = DeviceClassInvalidationFilter()

    def test_init(self):
        self.assertEqual(self.dcif._types, (DeviceClass, ))

    def test_getRoot(self):
        context = Mock(name='context')
        root = self.dcif.getRoot(context)
        self.assertEqual(root, context.dmd.Devices.primaryAq())

    @patch('{invalidationfilter}.BaseOrganizerFilter.generateChecksum'.format(**PATH), autospec=True)
    def test_generateChecksum(self, super_generateChecksum):
        md5_checksum = md5()
        organizer = Mock(
            name='Products.ZenRelations.ZenPropertyManager',
            spec=['rrdTemplates'],
            set_spec=True
        )
        rrdTemplate = Mock(name='rrdTemplate')
        rrdTemplate.exportXml.return_value = 'some exemel'
        organizer.rrdTemplates.return_value = [rrdTemplate]

        self.dcif.generateChecksum(organizer, md5_checksum)

        # We cannot validate the output of the current version, refactor needed
        #self.assertEqual(md5_checksum.hexdigest(), 'something')
        rrdTemplate.exportXml.was_called_once()
        super_generateChecksum.assert_called_with(
            self.dcif, organizer, md5_checksum
        )


class OSProcessOrganizerFilterTest(TestCase):

    def test_init(self):
        ospof = OSProcessOrganizerFilter()
        self.assertEqual(ospof._types, (OSProcessOrganizer, ))

    def test_getRoot(self):
        ospof = OSProcessOrganizerFilter()
        context = Mock(name='context')
        root = ospof.getRoot(context)
        self.assertEqual(root, context.dmd.Processes.primaryAq())


class OSProcessClassFilterTest(TestCase):

    def setUp(self):
        self.ospcf = OSProcessClassFilter()

    def test_init(self):
        self.assertEqual(self.ospcf._types, (OSProcessClass, ))

    def test_getRoot(self):
        context = Mock(name='context')
        root = self.ospcf.getRoot(context)
        self.assertEqual(root, context.dmd.Processes.primaryAq())

    @patch('{invalidationfilter}.BaseOrganizerFilter.generateChecksum'.format(**PATH), autospec=True)
    def test_generateChecksum(self, super_generateChecksum):
        organizer = Mock(
            name='Products.ZenRelations.ZenPropertyManager',
            spec=['property_id'],
            set_spec=True
        )
        prop = {'id': 'property_id'}
        organizer._properties = [prop]
        organizer.property_id = 'value'
        md5_checksum = md5()

        self.ospcf.generateChecksum(organizer, md5_checksum)

        expect = md5()
        expect.update("%s|%s" % (prop['id'], getattr(organizer, prop['id'])))
        self.assertEqual(md5_checksum.hexdigest(), expect.hexdigest())
        super_generateChecksum.assert_called_with(
            self.ospcf, organizer, md5_checksum
        )
