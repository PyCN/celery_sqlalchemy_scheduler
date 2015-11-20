#-*- coding: utf-8 -*-
from pyramid.view import view_config, forbidden_view_config
from pyramid.exceptions import Forbidden
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy_admin.security import Views
from pyramid.renderers import render_to_response

@view_config(route_name = "admin_index", renderer = "index.html.jinja2")
def api_index(request):
    if not Views().checkRequest(request):
        return render_to_response({}, "login.html.jinja2")
    return {}