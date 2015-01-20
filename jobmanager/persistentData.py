import sqlitedict as sqd
from os.path import abspath, join, exists
import os
import shutil
import traceback

MAGIC_SIGN = 0xff4a87

KEY_COUNTER = '0'
KEY_SUB_DATA_KEYS = '1'

RESERVED_KEYS = (KEY_COUNTER, KEY_SUB_DATA_KEYS)

class PersistentDataStructure(object):
    """
        Note: avoid using pickled dictionaries as binary keys! The problem with dicts is
        that the order of the keys, when returned as list, depends on the hash value of
        the keys. If the keys are strings, the hash value will be randomly seeded for
        each python session, which may lead to different binary representations of the
        same dict. Therefore the same dict may actually be considered as distinct keys.
        
        The same hold true when using classes with default pickler routine as binary keys
        (because the pickler will essentially pickle the dictionary self.__dict__).
        If you want to use "complicated" python objects as binary keys make sure you
        implement your own pickle behavior without the need of dictionaries.   
    """
    def __init__(self, name, path="./", verbose=1):
        self._open = False
        self._name = name
        self._path = abspath(path)
        if not exists(self._path):
            raise RuntimeError("given path does not exists ({} -> {})".format(path, self._path))
        
        self.verbose = verbose
        
        # create directory to hold sub structures
        self._dir_name = join(self._path, "__" + self._name)
        if not exists(self._dir_name):
            os.mkdir(self._dir_name)
        
        # open actual sqltedict
        self._filename = join(self._dir_name, self._name + '.db')
        self.open()
        
        if KEY_COUNTER in self.db:
           self.counter = self.db[KEY_COUNTER] 
        else:
            self.counter = 0
            
        if KEY_SUB_DATA_KEYS in self.db:
            self.sub_data_keys = self.db[KEY_SUB_DATA_KEYS]
        else:
            self.sub_data_keys = set()
            
    def _consistency_check(self):
        self.need_open()
        
        c = 0
        
        for key in self.db:
            value = self.db[key]
            if self.__is_sub_data(value):
                c += 1
                assert key in self.sub_data_keys
        
        assert len(self.sub_data_keys) == c
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.verbose > 1:
            print("exit called for        {} in {}".format(self._name, self._dir_name))
        self.close()
        
    def open(self):
        """
            open the SQL database at self._filename = <path>/__<name>/<name>.db
            as sqlitedict
        """
        if self.verbose > 1:
            print("open db                {} in {}".format(self._name, self._dir_name))             
        self.db = sqd.SqliteDict(filename = self._filename, autocommit=False)
        self._open = True
        
    def is_open(self):
        return self._open
        
    def is_closed(self):
        return not self._open
    
    def need_open(self):
        if self.is_closed():
            raise RuntimeError("PersistentDataStructure needs to be open")
        
    def close(self):
        """
            close the sqligtedict ans therefore the SQL database
        """
        try:
            self.db.close()
            self._open = False
            if self.verbose > 1:
                print("closed db              {} in {}".format(self._name, self._dir_name))
        except:
            if self.verbose > 1:
                print("db seem already closed {} in {}".format(self._name, self._dir_name))
            
    def erase(self):
        """
            removed the database file from the disk
            
            this is called recursively for all sub PersistentDataStructure
        """
        if self.verbose > 1:
            print("erase db               {} in {}".format(self._name, self._dir_name))        

        if self.is_closed():
            self.open()
            
        try:

            if self.verbose > 1:
                print("sub_data_keys:", self.sub_data_keys)
            for key in self.sub_data_keys:
                if self.verbose > 1:
                    print("call erase for key:", key, "on file", self._filename)
                sub_data = self.getData(key)
                sub_data.erase()
        except:
            traceback.print_exc()
        finally:
            self.close()

        os.remove(path = self._filename)
        try:
            os.rmdir(path = self._dir_name)
        except OSError as e:
            if self.verbose > 0:
                print("Warning: directory structure can not be deleted")
                print("         {}".format(e))
       
    def __check_key(self, key):
        """
            returns True if the key does NOT collide with some reserved keys
            
            otherwise a RuntimeError will be raised
        """
        if key in RESERVED_KEYS:
            raise RuntimeError("key must not be in {} (reserved key)".format(RESERVED_KEYS))
        
        return True
    
    def __is_sub_data(self, value):
        """
            determine if the value gotten from the sqlitedict refers
            to a sub PersistentDataStructure
            
            this is considered the case if the value itself has an index 'magic'
            whose value matches a magic sign defined by MAGIC_SIGN 
        """
        try:
            assert value['magic'] == MAGIC_SIGN
            value.pop('magic')
            return True
        except:
            return False
    
    def has_key(self, key):
        self.need_open()
        return (key in self.db)
        
    def setData(self, key, value, overwrite=False):
        """
            write the key value pair to the data base
            
            if the key already exists, overwrite must be
            set True in oder to update the data for
            that key in the database 
        """
        self.need_open()
        if not self.__check_key(key):
            return False
        
        if overwrite or (not key in self.db):
            self.db[key] = value
            self.db.commit()
            return True
        
        return False
            
    def newSubData(self, key):
        """
            if key is not in database
            create a new database (sqlitedict)
            which can be queried from this one
            via the key specified 
            
            this will automatically create a new
            file where the filename is internally
            managed (simple increasing number)   
        """
        self.need_open()
        if not key in self.db:
            self.counter += 1
            self.sub_data_keys.add(key)
            if self.verbose > 1:
                print("new sub_data with key", key)
                print("sub_data_keys are now", self.sub_data_keys)

            new_name = "{}".format(self.counter)
            kwargs = {'name': new_name, 'magic': MAGIC_SIGN}
            
            self.db[KEY_COUNTER] = self.counter
            self.db[KEY_SUB_DATA_KEYS] = self.sub_data_keys
            self.db[key] = kwargs
            self.db.commit()

            kwargs.pop('magic')
            return PersistentDataStructure(name = new_name, path = os.path.join(self._dir_name) , verbose = self.verbose)
        else:
            raise RuntimeError("can NOT create new SubData, key already found!")
        
    def getData(self, key, create_sub_data = False):
        self.need_open()
        if key in self.db:
            if self.verbose > 1:
                print("getData key exists")
            value = self.db[key]
            if self.__is_sub_data(value):
                if self.verbose > 1:
                    print("return subData stored as key", key, "using name", value['name'])
                return PersistentDataStructure(name = value['name'], path = os.path.join(self._dir_name) , verbose = self.verbose)
            else:
                if self.verbose > 1:
                    print("return normal value")
                return value 
        else:
            if not create_sub_data:
                raise KeyError("key '{}' not found".format(key))
            else:
                if self.verbose > 1:
                    print("getData key does NOT exists -> create subData")
                return self.newSubData(key)
            
    def setDataFromSubData(self, key, subData):
        """
            set an entry of the PDS with data from an other PDS
            
            this means copying the appropirate file to the right place
            and rename them
        """
        self.need_open()
        self.__check_key(key)                                       # see if key is valid
        if (key in self.db) and (self.__is_sub_data(self.db[key])): # check if key points to existing PDS
            value = self.db[key]
            with self[key] as pds:                                  #
                name = pds._name                                    #    remember its name
                dir_name = pds._dir_name                            #    and the directory where it's in     
                pds.erase()                                         #    remove the existing subData from hdd  
        else:
            with self.newSubData(key) as new_sub_data:              #    create a new subData
                name = new_sub_data._name                           #    and remember name and directory
                dir_name = new_sub_data._dir_name
                new_sub_data.erase()
        
        shutil.copytree(src=subData._dir_name, dst=dir_name)
        os.rename(src=os.path.join(dir_name, subData._name+'.db'), dst=os.path.join(dir_name, name+'.db'))

    def __len__(self):
        self.need_open()
        return len(self.db) - 2
            
    # implements the iterator
    def __iter__(self):
        self.need_open()
        db_iter = self.db.__iter__()
        while True:
            next_item = db_iter.__next__()
            while next_item in RESERVED_KEYS: 
                next_item = db_iter.__next__()
            yield next_item 
    
    # implements the 'in' statement 
    def __contains__(self, key):
        self.need_open()
        return (key in self.db)
            
    # implements '[]' operator getter
    def __getitem__(self, key):
        self.need_open()
        self.__check_key(key)
        return self.getData(key, create_sub_data=False)
    
    # implements '[]' operator setter
    def __setitem__(self, key, value):
        self.need_open()
        self.__check_key(key)
#         if key in self.db:
#             if self.__is_sub_data(self.db[key]):
#                 raise RuntimeWarning("values which hold sub_data structures can not be overwritten!")
#                 return None
        
        if self.verbose > 1:
            print("set", key, "to", value, "in", self._filename)
            
        if isinstance(value, PersistentDataStructure):
            self.setDataFromSubData(key, value)
        else:
            self.db[key] = value
            self.db.commit()
        
        
    # implements '[]' operator deletion
    def __delitem__(self, key):
        self.need_open()
        self.__check_key(key)
        value = self.db[key]
        if self.__is_sub_data(value):
            with PersistentDataStructure(name = value['name'], path = os.path.join(self._dir_name) , verbose = self.verbose) as pds:
                pds.erase()
            
            self.sub_data_keys.remove(key)
            self.db[KEY_SUB_DATA_KEYS] = self.sub_data_keys
                
        del self.db[key]
        self.db.commit()
            
        
