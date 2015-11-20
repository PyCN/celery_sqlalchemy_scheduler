#-*- coding: utf-8 -*-
class View:
    """Родительский класс всех представлений, отдающих JSON. Работает следующим образом::
    
            class MyViews(View):
                def view1(self):
                    return ["olala"]
                def view_help(self):
                    pass      
        
        В main::
    
            config.add_route("my route", "/my_lovely_prefix/{olala}", view = MyViews(what = "olala"), renderer = "json")
        
        В результате этих действий путь /my_lovely_prefix/view1 будет обслуживаться функцией view1, а путь 
        /my_lovely_prefix/view_help будет обслуживаться функцией view_help.
        
        Переменная request доступна как атрибут self.request.
        """
        
    def __init__(self, what = "action"):
        self.what = what
    
    def __call__(self, request):
        self.request = request
        self.action = self.request.matchdict[self.what]
        self.request.response.headers.update({"Content-type": "application/json; charset=utf-8"})
        
        
        if len(self.request.GET.keys())>0:
            self.data = self.request.GET
        elif len(self.request.POST.keys())>=0:
            self.data = self.request.POST
        
        if self.action[0]!="_":
            if hasattr(self, self.action):
                if hasattr(getattr(self, self.action), "__call__"):
                    return getattr(self, self.action)()
        return NotFound()
