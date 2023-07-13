from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_home, name="chat_home"),
    path("chat/new/", views.start_chat, name="start_chat"),
    path("chat/<int:chat_id>/", views.single_chat, name="single_chat"),
    path("chat/<int:chat_id>/new_message/", views.new_message, name="new_chat_message"),
    path("chat/<int:chat_id>/get_response/<slug:task_id>/", views.get_message_response, name="get_message_response"),
]
