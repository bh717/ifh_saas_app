from django.urls import path

from . import views

app_name = "openai_example"

urlpatterns = [
    path("", views.home, name="openai_home"),
    path("images/", views.image_demo, name="image_demo"),
]
