#-*- coding: utf-8 -*-
from sqlalchemy import types

class NotOverloadedError(Exception):
    pass

class AbstractColumn(object):
    """
        Реализует обертку над объектом колонки таблицы. 
        Обязательные свойства, которые должны быть перегружены:
        
            * **name** - название колонки
            * **type** - Доступные типы::
            
                "string",  
                "boolean", 
                "int", 
                "date", 
                "datetime",
                "enum",
                "float",
                "text"
                
    """
    @staticmethod
    def get_type(col):
        raise NotImplementedError()
    
    def __json__(self):
        return {"name": self.name,
                "type": self.type}

class AbstractWrapper(object):
    """
        Абстрактная обертка на ORM-класс таблицы
    """
    __meta__ = {}
    
    def add(self):
        """Добавляет текущий элемент"""
        raise NotOverloadedError
        
    def delete(self):
        """Удаляет текущий элемент"""
        raise NotOverloadedError
    
    def flush(self):
        """Сбрасывает изменения в БД"""
        raise NotOverloadedError
    
    def update(self, **k):
        """Изменяет элемент согласно переданным ключам"""
        raise NotOverloadedError
    
    def json(self):
        """Возвращает JSON представление текущего элемента"""
        raise NotOverloadedError
    
    @staticmethod
    def get(**k):
        """Получает один элемент согласно переданным ключам"""
        raise NotOverloadedError
    
    @staticmethod
    def filter_by(**k):
        """Фильтрует элементы согласно переданным ключам"""
        raise NotOverloadedError
        
    @staticmethod
    def get_or_create(create = {}, **get):
        """Находит или создает элемент"""
        raise NotOverloadedError
    
    @staticmethod
    def all():
        """Возвращает все элементы коллекции"""
        raise NotOverloadedError
    
    @staticmethod
    def count():
        """Возвращает число элементов коллекции"""
        raise NotOverloadedError
    
import sqlahelper

class SQLAlchemy_column(AbstractColumn):
    @staticmethod
    def get_type(col):
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
    
    def __init__(self, name, column_clas):
        self.name = name
        self.key = column_clas.key
        self.type = self.get_type(column_clas.type)
    
def get_sqlalchemy_wrapper_on(clas):
    DBSession = sqlahelper.get_session()
    
    #------------ adding info about columns ------------------
    columns = []
    for attr in clas.__dict__:
        if attr[0] != "_":
            if hasattr(clas.__dict__[attr], "type"):    #может не быть такого свойста - тогда это, скорее всего, relationship
                col = SQLAlchemy_column(attr, clas.__dict__[attr])
                columns.append(col)
                
    setattr(clas, "_columns", columns)
    
    #----------- tablename -------------------------------------
    setattr(clas, "_name", clas.__tablename__)
                
    class SQLAlchemyWrapper(AbstractWrapper):
        """
            SQLAlchemy wrapper. Requires **sqlahelper**
        """
        
        def __init__(self):
            pass
            
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
        
        
        def _json(self):
            out = {}
            for key in self.__dict__:
                if key[0] != "_":
                    if hasattr(self, key):
                        if hasattr(self.__dict__[key], "__iter__"):            
                            value = self.__dict__[key]
                        elif isinstance(self.__dict__[key], bool):
                            value = str(self.__dict__[key]).lower()
                        else:
                            value = unicode(self.__dict__[key])
                        out[key] = value
            return out
        
        def __json__(self, a = 0):
            return self._json()
    
        @staticmethod
        def _get(**k):
            if k == {}:
                raise ValueError("must be")
            element = DBSession.query(clas).filter_by(**k).first()
            return element
            
        @staticmethod
        def _filter_by(**k):
            if k == {}:
                return DBSession.query(clas).all()
            element = DBSession.query(clas).filter_by(**k)
            return element
        
        @staticmethod
        def _filter(*a, **k):
            return DBSession.query(clas).filter(*a, **k)
            
        @staticmethod
        def _get_or_create(create = {}, **get):
            if get == {}:
                return clas(**create)._add()
            else:
                obj = clas._get(**get)
                if not obj:
                    obj = clas(**create)._add()
                return obj
        
        @staticmethod
        def _query():
            return DBSession.query(clas)
        
        @staticmethod
        def _all():
            return DBSession.query(clas).all()
        
        @staticmethod
        def _count():
            return DBSession.query(clas).count()
        
        @staticmethod
        def _getOrCreate(create = {}, **get):
            if get == {}:
                return clas(**create)._add()
            else:
                obj = clas._get(**get)
                if not obj:
                    obj = clas(**create)._add()
                return obj
        
    
    return SQLAlchemyWrapper


class ChooseMapper(object):
    """
        Strategy for choosing mapper by its type
        
        :param type: Mapper type. Now only sqlalchemy
        :param tableClass: ORM class which represent any table
        
        :returns: Mapper class, :class:`sqlalchemy_admin.db_wrapper.AbstractWrapper`
    """
    def __init__(self, type, tableClass):
        self.table = tableClass
        self.type = type
    
    def get_mapper(self):
        if self.type == "sqlalchemy":
            return get_sqlalchemy_wrapper_on(self.table)
        else:
            raise ValueError("Incorrect mapper type")
        
           
        
        
    