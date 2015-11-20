#-*- coding: utf-8 -*-
import sqlahelper
from sqlalchemy import types
FlAG_PRIMARY_KEY = "primary key"
FLAG_UNIQUE = "unique"

def json_map(request, arr):
    return map(lambda x: x.__json__(request), arr)


def getType(col):
    """Функция, используется для определения типа объекта :class:`Column`"""
    TYPES = {
                types.String: "string",
                types.Boolean: "boolean",
                types.BigInteger: "int",
                types.Date: "date",
                types.DateTime: "datetime",
                types.Enum: "enum",
                types.Float: "float",
                types.Integer: "int",
                types.Numeric: "float",
                types.Text: "text"
             }
    return TYPES.get(type(col), "unknown")

class column:
    """Основной класс столбца. """
    def __init__(self, name, column_clas, __meta__ = {}):
        self.name = name
        self.key = column_clas.key
        self.type = getType(column_clas.type)
        self.flags = []
        self.metadata = {}
        
        if self.name == "id":
            self.flags.append("noneditable")
            self.flags.append("id")
            
        if column_clas.nullable:
            self.flags.append("nullable")
            
        
        if "acl" in __meta__:
            if "show" in __meta__["acl"].get(self.name, []) and not "update" in __meta__["acl"].get(self.name, []):
                self.flags.append("noneditable")
        
        if self.type == "enum":
            self.flags.append("select")
            self.metadata["select"] = map(lambda x: {self.name:x}, column_clas.type.enums)
            self.metadata["fields"] = [self.name]
            self.metadata["valueField"] = self.name
            self.metadata["displayField"] = self.name
        
        if len(column_clas.foreign_keys) >0:
            fks = column_clas.foreign_keys.copy()
            if len(fks)>1:
                raise ValueError("Only 1 FK allow in current version")
            fk = fks.pop()
            
            table, column = str(fk._colspec).split(".")
            
            self.flags.append("foreign_key")
            self.flags.append("select")
            self.metadata["fk_table"] = table
            self.metadata["fk_column"] = column
            self.metadata["fields"] = ["id", self.name]
            self.metadata["valueField"] = "id"
            self.metadata["displayField"] = self.name
        
    def __json__(self, request):
        return self.__dict__

def json(self, request):
    def _is_jsonable(obj):
        import json
        try:
            json.dumps(obj)
        except TypeError:
            return False
        return True

    out = {}
    for key in self.__dict__:
        value = self.__dict__[key]
        if key[0] != "_":
            if not _is_jsonable(value):
                value = unicode(value)
            out[key] = value
    return out

def constructSuperModel(clas):
    DBSession = sqlahelper.get_session()
    attrs = clas.__dict__
    _columns = []
    
    __meta__ = {}
    if hasattr(clas, "__meta__"): __meta__ = getattr(clas, "__meta__")
    
        
    class relationship(column):
        def __init__(self, name, rel_clas):
            self.type = "RELATIONSHIP"
            self.name = name
            self.key = rel_clas.key
            
    relationships = []
    for attr in attrs:
        if attr[0] != "_":
            if hasattr(attrs[attr], "type"):    #может не быть такого свойста - тогда это, скорее всего, relationship
                col = column(attr, attrs[attr], __meta__= __meta__)
                #Если явно не указали исключить данную column
                if col.name not in __meta__.get("exclude", []): _columns.append(col)

    class _helper:
        
        def _add(self):
            DBSession.add(self)
            return self
        
        def _delete(self):
            DBSession.delete(self)
            return None
        
        def _flush(self):
            DBSession = sqlahelper.get_session()
            DBSession.flush()
            DBSession.refresh(self)
            return self
        
        def _update(self, **k):
            for key in k:
                if not hasattr(self, key):
                    raise AttributeError("No such atribute like %s"%(key))
                setattr(self, key, k[key])
            return self

    def _get(**k):
        if k == {}:
            raise ValueError("must be")
        element = DBSession.query(clas).filter_by(**k).first()
        return element
        
    def _filter_by(**k):
        if k == {}:
            return DBSession.query(clas).all()
        element = DBSession.query(clas).filter_by(**k)
        return element
    
    def _filter(*a, **k):
        return DBSession.query(clas).filter(*a, **k)
        
    
    def _getOrCreate(create = {}, **get):
        if get == {}:
            return clas(**create)._add()
        else:
            obj = clas._get(**get)
            if not obj:
                obj = clas(**create)._add()
            return obj
    
    def _query():
        return DBSession.query(clas)
    
    def _all():
        return DBSession.query(clas).all()
    
    
    for key in _helper.__dict__:
        setattr(clas, key, _helper.__dict__[key])
    
    setattr(clas, "_get", staticmethod(_get))
    setattr(clas, "_filter_by", staticmethod(_filter_by))
    setattr(clas, "_filter", staticmethod(_filter))
    setattr(clas, "_getOrCreate", staticmethod(_getOrCreate))
    setattr(clas, "_all", staticmethod(_all))
    setattr(clas, "_columns", _columns)
    setattr(clas, "_is_futured", True)
    setattr(clas, "_query", staticmethod(_query))
    
    if not hasattr(clas, "__json__"):
        setattr(clas, "__json__", json)
    
    if __meta__.has_key("str_fields"):
        keys_to_unicode = __meta__["str_fields"]
    else:
        keys_to_unicode = map(lambda x: x.name, _columns)
        
    def my_unicode(self):
        s = self.__tablename__ + " object. "
        for key in keys_to_unicode:
            if key in self.__dict__:
                s += "%s:%s "%(unicode(key), unicode(self.__dict__[key]))
        return s 
    setattr(clas, "__unicode__", my_unicode)
    
    return clas