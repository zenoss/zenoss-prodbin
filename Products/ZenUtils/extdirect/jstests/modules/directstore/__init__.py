from Products.ZenUtils.extdirect import router

class RecordCollection(object):
    
    def __init__(self):
        self.records = []
        
    def greatestId(self):
        self.sortRecordsBy('id', reverse=True)
        return self.records[0]['id']
        
    def sortRecordsBy(self, field, reverse=False):
        def key(record):
            return record[field]
        self.records.sort(key=key, reverse=reverse)
        
class CrudService(router.DirectRouter):
    
    """
    An in-memory DirectRouter that provides a CRUD API.  Make this as simple
    as possible.  The intension is to test the interaction between Extjs 
    DirectStore and the DirectRouter base class.
    """
    
    def __init__(self, *args, **kwargs):
        super(CrudService, self).__init__(*args, **kwargs)
        self._collection = RecordCollection()
        
    @property
    def _records(self):
        return self._collection.records
        
    def create(self, *args, **kwargs):
        if not args:
            args = [kwargs]
        for arg in args:
            if self._records:
                id = self._collection.greatestId() + 1
            else:
                id = 0
            arg['id'] = id
            self._records.append(arg)
        if len(args) == 1:
            args = args[0]
        return args
        
    def read(self, sort='id', dir='ASC'):
        reverse = dir == 'DESC'
        self._collection.sortRecordsBy(sort, reverse=reverse)
        return {'records': self._records}
        
    def update(self, *args, **kwargs):
        pass
        
    def destroy(self, *args, **kwargs):
        if not args:
            args = [kwargs]
        deletes = []
        for arg in args:
            for record in self._records:
                if record['id'] == arg['id']:
                    deletes.append(record)
                    break
        for delete in deletes:
            self._records.remove(delete)
            
