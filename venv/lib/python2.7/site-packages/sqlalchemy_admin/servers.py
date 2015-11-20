#-*- coding: utf-8 -*-
import os
import logging
import transaction
import json
from pprint import pformat
import pprint
import urllib
import urlparse
from sqlalchemy_admin.security import Views
from pyramid.httpexceptions import HTTPForbidden
class AbstractServer(object):
    """
        Обертка над веб-сервером
    """
    def add_route(self, name, route, function):
        """
            Добавляет обработчик пути route
            
            :param name: название route
            :param router: - путь
            :param function: - обработчик - инстанс :clas:`sqlalchemy_admin.servers.AbstractRestServerTable`
            
            .. note::
            
                Например, если мы хотим обрабатывать класс tables, должны быть добавлены роуты:
                * /tables, get, 
                * /tables/id
                
            .. note::
            
                представление роута принимает не request, а wrappedRequest
        """
        raise NotImplementedError

class AbstractRequest(object):
    """
        Обертка для запроса к серверу
    """
    def get_method(self):
        """
            Возвращает метод запроса
            
            :returns: get, post, put, delete
        """
        raise NotImplementedError()
    
    def get_route(self):
        """
            Возвращает текущий роут
        """
        raise NotImplementedError()
    
    def get_route_params(self):
        """
            Возвращает изменяемые параметры route
        """
        raise NotImplementedError()
    
    def get_get(self):
        """
            Возвращает GET данные
        """
        raise NotImplementedError()
        
    def get_post(self):
        """
            Возвращает POST, PUT данные
        """
        raise NotImplementedError()
    
    def get_delete(self):
        raise NotImplemented
    
    def get_put(self):
        raise NotImplemented
    

class AbstractRestServerTable(object):
    """
        Класс, реализующий get/post интерфейс для таблицы в целом.
    """
    def __init__(self, 
                 wrapped_table_class,
                 route_prefix,
                 server,
                 ):
        self.table = wrapped_table_class
        self.route = os.path.join(route_prefix, self.table.__tablename__)
        self.server = server
        self.name = self.table.__tablename__
        
    def add_route(self):
        """Добавляет роут"""
        self.server.add_route("table_"+self.name, self.route, self)
        
    def __call__(self, request):
        method = request.get_method()
        
        if hasattr(self, method):
            return getattr(self, method)(request)
    
    def get(self, request):
        data = request.get_get()
        return map(lambda x: x._json(), self.table._filter_by(**data))
    
    def post(self, request):
        raise NotImplementedError
    
    def delete(self, request):
        data = request.get_delete()
        
        print request.request.GET, request.request.POST, request.request.body
        
        print data
        data = json.loads(data["ids"])
        
        with transaction.manager:
            for id in data:
                db_item = self.table._get(id = id)
                if db_item is None:
                    raise ValueError()
                db_item._delete()
        return {"response": "ok"}
            
            
    

class AbstraAbstractRestServerTableItem():
    """
        Класс, реализующий get, put, delete интерфейс для объекта таблицы
    """
    def __init__(self, 
                 wrapped_table_class,
                 route_prefix,
                 server,
                 ):
        self.table = wrapped_table_class
        self.route = os.path.join(route_prefix, self.table.__tablename__)
        self.server = server
        self.name = self.table.__tablename__
        
    def add_route(self):
        raise NotImplementedError
        
    def __call__(self, request):
        method = request.get_method()
        
        if hasattr(self, method):
            if Views().checkRequest(request):
                return getattr(self, method)(request)
            else:
                return HTTPForbidden()
    
    def get(self, request):
        data = request.get_get()
        id = request.get_route_params()["id"]
        data.update({"id":id})
        return self.table._get(**data)._json()    
    
    def put(self, request):
        raise NotImplementedError
    
    def delete(self, request):
        id = request.get_route_params()["id"]
        with transaction.manager:
            self.table._get(id = id)._delete()
        return {"response": "ok"}

class PyramidRequest(AbstractRequest):
    def __init__(self, request):
        pprint.pprint(dict(request.headers))
        self.request = request
    
    def get_method(self):
        MAP = {"GET":"get",
               "POST": "post",
               "PUT": "put",
               "DELETE": "delete"}
        return MAP[self.request.method]
    
    def get_route(self):
        return self.request.matched_route
    
    def get_route_params(self):
        return self.request.matchdict
    
    def get_get(self):
        return self.request.GET
    
    def get_post(self):
        print "Returning POST", pformat(dict(self.request.POST))
        
        return self.request.POST
    
    def get_delete(self):
        data = urlparse.parse_qs(urllib.unquote(self.request.body))
        data = {key: value[0] for key, value in data.iteritems()}
        return data

class PyramidServer(AbstractServer):
    def __init__(self, config):
        self.config = config
    
    def add_route(self, name, path, function):
        def _view_wrapper(request):
            return function(PyramidRequest(request))
        logging.info("Adding REST route with name %s for path %s"%(name, path))
        self.config.add_route("admin_"+name, path, view = _view_wrapper, renderer = "json")
        

class PyramidRestServerTable(AbstractRestServerTable):
    pass

class PyramidRestServerTableItem(AbstraAbstractRestServerTableItem):
    def add_route(self):
        self.server.add_route(self.name+"_item", os.path.join(self.route, "{id}"), self)
        
class Context(object):
    """
        Возвращает все серверные классы, в зависимости от переданного type

    """
    def __init__(self, type):
        self.type = type
        if self.type == "pyramid":
            self.serverClass = PyramidServer
            self.requestClass = PyramidRequest
            self.tableApiClass = PyramidRestServerTable
            self.tableItemapiClass = PyramidRestServerTableItem
        else:
            logging.exception("Incorrect type %s"%self.type)
    
    
               
        