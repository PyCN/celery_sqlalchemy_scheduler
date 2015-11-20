#-*- coding: utf-8 -*-
import logging
from sqlalchemy_admin.old import View
from sqlalchemy_admin.db_wrapper import ChooseMapper
from sqlalchemy_admin.servers import Context
import os
import wtforms
from wtforms.validators import ValidationError
from sqlalchemy_admin.security import Views
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy_admin.views import api_index
def singleton(clas, objects = {}):
    def _callback(*a, **k):
        if clas.__name__ not in objects:
            objects[clas.__name__] = clas(*a, **k)
        return objects[clas.__name__]
    return _callback

def get_or_none(cls, *attrs):
    res = None
    for attr in attrs:
        try:
            res = getattr(cls, attr)
        except:
            res = None
            break
    return res
        
    
@singleton
class Api(object):
    API_TABLES = {}
    """Тут хранятся инстансы потомков :clas:`sqlalchemy_admin.servers.AbstractRestServerTable`,
    :clas:`sqlalchemy_admin.servers.AbstraAbstractRestServerTableItem` в формате::
    
        {
            <tablename>:{
                table: <AbstractRestServerTable>,
                items: <AbstraAbstractRestServerTableItem>
            }
        }    

    """
    
    TABLES = []
    """
        Тут хранятся инстансы **WrappedTableClass**
    """
    def __init__(self,
                 orm_type = "sqlalchemy"):
        self.orm_type = orm_type
        self.serverClasses = Context("pyramid")
        self.route_prefix = "/admin"
        
    
    def __call__(self, tableClass):
        wrapper = ChooseMapper(self.orm_type, tableClass).get_mapper()
        
        #--------------------- creating table wrapper ----------------------------
        logging.warning("Create table wrapper for table %s", tableClass._name)
        for method in wrapper.__dict__:
            if hasattr(tableClass, method) or method in ["__init__", ]:
                continue
            setattr(tableClass, method, wrapper.__dict__[method])
            
        #-------------------- registering table api ---------------------------
        
        self.TABLES.append(tableClass)
        
        return tableClass
    
    def register_table(self, tableClass):
        tableApi = self.serverClasses.tableApiClass(tableClass,
                                                       "/admin",
                                                       self.server)
        
        tableItemApi = self.serverClasses.tableItemapiClass(tableClass,
                                                            "/admin",
                                                            self.server)
        self.API_TABLES[tableApi.name] = {"table": tableApi,
                                      "items": tableItemApi}
        tableApi.add_route()
        tableItemApi.add_route()
    
    def get_tables_meta_route(self):
        """
            Возвращает представление, возвращающее информацию о зарегестрированных таблицах. Для полноты 
            у всех таблиц можно устанавливать дополнительно атрибут **__meta__**::
            
                __meta__ = {
                                group: группа в которую относится таблица
                                description: описание таблицы
                            }
            
            * **Формат запроса: **
            
                * **url** <admin_prefix>/get_tables
            
            * **Формат ответа**
            
        """
        def _call(wrappedRequest):
            if Views().checkRequest(wrappedRequest) is False:
                return HTTPForbidden()
            return map(lambda x: {"name": x._name,
                                  "table_route": os.path.join(self.route_prefix, x._name),
                                  "meta":  get_or_none(x, "__meta__")}, self.TABLES)
        return _call
    
    def get_table_columns_meta_route(self):
        """
            Возвращает представление, возвращающее информацию по колонкам переданной таблицы.
            
            * **Формат запроса**:
                 * **url**: <admin_prefix>/get_columns
                 * **method**: GET
                 * **data**::
                 
                     table - название таблицы
        """
        def _call(wrappedRequest):
            if Views().checkRequest(wrappedRequest) is False:
                return HTTPForbidden()
            class _Form(wtforms.Form):
                table = wtforms.StringField()
                def validate_table(cls, field):
                    if field.data not in self.API_TABLES:
                        raise ValidationError("incorrect table")
            form = _Form(wrappedRequest.get_get())
            if form.validate():
                return map(lambda x: x.__json__(), self.API_TABLES[form.data["table"]]["table"].table._columns)
            else:
                return {"response": "validation error", "errors": form.errors}
        return _call
    
    def includeme(self, **k):
        """
            Используется для подключения Api к серверу приложения.
            Добавляет необходимые роуты для сервера.
        """
        config = k["config"]
        
        config.add_jinja2_search_path("sqlalchemy_admin/templates")
        
        self.server = self.serverClasses.serverClass(config)
        
        Views().includeme(self, config)
        
        config.add_route("admin_index", self.route_prefix, view = Views().authDecorator(api_index), renderer = "index.html.jinja2")
        config.add_static_view("admin_static", "sqlalchemy_admin/static")

        
        
        for table in self.TABLES:
            self.register_table(table)
            
        self.server.add_route("admin_tables_meta_info", os.path.join(self.route_prefix, "get_tables"), self.get_tables_meta_route())
        self.server.add_route("admin_columns_meta_info", os.path.join(self.route_prefix, "get_columns"), self.get_table_columns_meta_route())
        
        
        
        