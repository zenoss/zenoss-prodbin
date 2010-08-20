import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, aliased, exc
from sqlalchemy.sql import text
from sqlalchemy.ext.declarative import declarative_base
from ..nested_set import MultiTreeNestedSetItem

Base = declarative_base()

class TestItem(Base, MultiTreeNestedSetItem):
    __tablename__ = 'TestItem'
    def __init__(self, id):
        super(TestItem, self).__init__(id=id)
        self.category = 0


class TestNestedSets(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite://', echo=False)
        #self.engine = create_engine('mysql://root@localhost:3306/testing', echo=True)
        TestItem.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        albert = TestItem(1)
        bert = TestItem(2)
        chuck = TestItem(3)
        donna = TestItem(4)
        bert.parent = albert
        chuck.parent = albert
        donna.parent = chuck
        self.items = [albert, bert, chuck, donna]
        self.session.add_all(self.items)
        self.session.commit()

    def tearDown(self):
        delete = text('DROP TABLE TestItem;')
        connection = self.engine.connect()
        connection.execute(delete)

    def test_insert(self):
        result = self.session.query(TestItem).all()
        self.assertEqual(result, self.items)

    def test_categories(self):
        yvette = TestItem(0) # Same id as albert
        zuzana = TestItem(1) # Same id as bert
        yvette.category = 1
        zuzana.category = 1
        zuzana.parent = yvette
        self.session.add_all([yvette, zuzana])
        # Should commit fine because diff categories
        self.session.commit()

        xena = TestItem(0) # Same id as yvette
        xena.category = 1
        self.session.add_all([xena])
        # Make sure it fails due to primary key dupe
        self.assertRaises(exc.FlushError, self.session.commit)

    def test_parents(self):
        alias = aliased(TestItem)
        donna = self.items[-1]
        query = donna.parents()
        self.assertEqual(map(int, [x.id for x in query.all()]), [1, 3, 4])

    def test_parents_with_categories(self):
        xena = TestItem(1)
        yvette = TestItem(2)
        zuzana = TestItem(3)
        xena.category = 1
        yvette.category = 1
        zuzana.category = 1
        yvette.parent = xena
        zuzana.parent = yvette
        self.session.add_all([xena, yvette, zuzana])
        self.session.commit()

        alias1 = aliased(TestItem)
        alias2 = aliased(TestItem)

        # Test that category 0 lookup works
        donna = self.items[-1]
        query = donna.parents()
        self.assertEqual(map(int, [x.id for x in query.all()]), [1, 3, 4])

        # Test that category 1 lookup works
        query = zuzana.parents()
        self.assertEqual(map(int, [x.id for x in query.all()]), [1, 2, 3])

    def test_delete_subtree(self):
        chuck = self.items[2]
        self.session.delete(chuck)
        self.session.commit()

        # Make sure donna got deleted with chuck
        results = self.session.query(TestItem).all()
        self.assertEqual(results, self.items[:2])

        # Make sure the gaps got closed
        albert, bert = results
        self.assertEqual((albert.left, albert.right), (1, 4))
        self.assertEqual((bert.left, bert.right), (2, 3))

    def test_delete_subtree_with_categories(self):
        xena = TestItem(1)
        yvette = TestItem(2)
        zuzana = TestItem(3)
        xena.category = 1
        yvette.category = 1
        zuzana.category = 1
        yvette.parent = xena
        zuzana.parent = yvette
        self.session.add_all([xena, yvette, zuzana])
        self.session.commit()

        chuck = self.items[2]
        self.session.delete(chuck)
        self.session.commit()

        # Make sure donna got deleted with chuck
        results = self.session.query(TestItem).filter(TestItem.category==0).all()
        self.assertEqual(results, self.items[:2])

        # Make sure the gaps got closed
        albert, bert = results
        self.assertEqual((albert.left, albert.right), (1, 4))
        self.assertEqual((bert.left, bert.right), (2, 3))

        # Make sure everybody else is still there
        results = self.session.query(TestItem).filter(TestItem.category==1).all()
        self.assertEqual(results, [xena, yvette, zuzana])


def test_suite():
    return unittest.makeSuite(TestNestedSets)
