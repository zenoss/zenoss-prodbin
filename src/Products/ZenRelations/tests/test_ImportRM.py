from unittest import TestCase
from mock import Mock, create_autospec, patch

from ..ImportRM import ImportRM


PATH = {"src": "Products.ZenRelations.ImportRM"}


class TestImportRM_endElement(TestCase):
    def setUp(t):
        """instantiate with default kwargs"""
        patches = [
            "ZCmdBase",
        ]

        for target in patches:
            patcher = patch("{src}.{}".format(target, **PATH), autospec=True)
            setattr(t, target, patcher.start())
            t.addCleanup(patcher.stop)

        t.irm = ImportRM(noopts=0, app=None, keeproot=False)

        obj0 = Mock("obj0", id="obj0_id")

        # these should set to defaults in __init__
        t.irm.curattrs = {"id": "myid", "attr_a": "v1"}
        t.charvalue = "111"
        t.irm.charvalue = t.charvalue
        t.irm._locator = Mock("locator", getLineNumber=Mock(return_value=555))
        t.irm.setProperty = create_autospec(t.irm.setProperty)

        t.irm.options = Mock(noIncrementalCommit=True)
        t.irm.objstack = [
            obj0,
        ]

    def test_endElement_property(t):
        t.irm.endElement("property")

        t.irm.setProperty.assert_called_with(
            t.irm.context(), t.irm.curattrs, t.charvalue
        )
        t.assertEqual(t.irm.charvalue, "")

    def test_endElement_property_prodstate(t):
        """if the id is 'prodstate' cary its value over in context"""
        t.irm.context = create_autospec(t.irm.context)
        t.irm.curattrs["id"] = "prodstate"

        t.irm.endElement("property")

        t.irm.context.return_value.setProdState.assert_called_with(
            int(t.charvalue)
        )
