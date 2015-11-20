from pyramid.response import Response
from pyramid.httpexceptions import HTTPForbidden
import hashlib
import random
from pyramid.renderers import render_to_response
from pyramid.view import view_config
import wtforms


adminUsers = {"admin": "1379468250"}
adminSessions = {}

def singleton(clas, objects = {}):
    def _callback(*a, **k):
        if clas.__name__ not in objects:
            objects[clas.__name__] = clas(*a, **k)
        return objects[clas.__name__]
    return _callback

class LoginForm(wtforms.Form):
    login = wtforms.StringField(validators = [wtforms.validators.Required()])
    password = wtforms.PasswordField(validators = [wtforms.validators.Required()])



@singleton
class Views:
    def __init__(self):
        pass
    
    def includeme(self, app, config):
        self.app = app
        config.add_route( "login", self.app.route_prefix+"/api/login",  self.login, renderer = "json")
        config.add_route( "logout", self.app.route_prefix+"/api/logout",  self.logout, renderer = "json")
    
    @view_config(route_name = "admin_login")
    def login(self, request):
        form = LoginForm(request.POST)
        
        print request.GET, request.POST
        
        if form.validate():
        
            if adminUsers.get(form.data.get("login")) != form.data.get("password", None):
                return HTTPForbidden()
            
            session = hashlib.sha512(str(random.random())).hexdigest()
            adminSessions[form.data["login"]] = session
            request.response.set_cookie("admin_session", session)
            
            return {"response": "ok"}

        return form.errors
    
    def logout(self, wrappedRequest):
        return {}
    
    def checkRequest(self, wrappedRequest):

        wrappedRequest = getattr(wrappedRequest, "request", None) or wrappedRequest
            
        if wrappedRequest.cookies["admin_session"] in adminSessions.values():
            return True
        return False
    
    def authDecorator(self, func):
        def _c(wrappedRequest, *a, **k):
            if not self.checkRequest(wrappedRequest):
                return render_to_response("login.html.jinja2", {})
            return func(wrappedRequest, *a, **k)
        return _c
        
            
        
    
        
    
        
        