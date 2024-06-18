# from django.urls import path
# from django.contrib.auth import views as auth_views
# from . import views

# urlpatterns = [
#     path("", views.home, name="home"),
#     path("home", views.home_engine, name="home_engine"),
# ]


 

# urls.py
from django.urls import path
from .views import home_engine, analyze_roi
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path('home', home_engine, name='home_engine'),  # Add this line for the empty path
    path('analyze-roi/', analyze_roi, name='analyze_roi'),
]



