import unittest
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from Products.ZenUtils.orm import meta

class ORMTestCase(unittest.TestCase):

    _tables = ()

    def setUp(self):
        #self.engine = create_engine('sqlite://', echo=False)
        self.engine = create_engine('mysql://root@localhost:3306/events', echo=True)
        meta.metadata.bind = self.engine
        meta.Session.configure(autoflush=True, autocommit=True, binds={
            meta.metadata:self.engine
        })
        meta.Base.metadata.create_all(self.engine)
        self.session = meta.Session

    def tearDown(self):
        connection = self.engine.connect()
        for table in self._tables:
            delete = text('DROP TABLE %s;' % table.__tablename__)
            connection.execute(delete)
