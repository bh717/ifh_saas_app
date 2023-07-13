from celery.result import AsyncResult
from celery_progress.backend import Progress
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.chat.models import Chat, ChatMessage, MessageTypes
from apps.chat.serializers import ChatMessageSerializer, ChatSerializer
from apps.chat.tasks import get_chatgpt_response, set_chat_name


@login_required
def chat_home(request):
    chats = request.user.chats
    return TemplateResponse(
        request,
        "chat/chat_home.html",
        {
            "active_tab": "openai",
            "chats": chats,
        },
    )


@require_POST
@login_required
def start_chat(request):
    chat = Chat.objects.create(
        user=request.user,
    )
    return HttpResponseRedirect(reverse("chat:single_chat", args=[chat.id]))


@login_required
def single_chat(request, chat_id: int):
    chat = get_object_or_404(Chat, user=request.user, id=chat_id)
    return TemplateResponse(
        request,
        "chat/single_chat.html",
        {
            "active_tab": "openai",
            "chat": chat,
        },
    )


@require_POST
@login_required
def new_message(request, chat_id: int):
    # confirm user can access that chat
    chat = get_object_or_404(Chat, user=request.user, id=chat_id)
    message_text = request.POST["message"]
    is_first_message = not chat.messages.exists()
    ChatMessage.objects.create(
        chat_id=chat_id,
        message_type=MessageTypes.HUMAN,
        content=message_text,
    )
    result = get_chatgpt_response.delay(chat_id, message_text)
    if is_first_message:
        set_chat_name.delay(chat_id, message_text)

    return TemplateResponse(
        request,
        "chat/components/chat_message_from_user.html",
        {
            "message_text": message_text,
            "task_id": result.task_id,
            "chat": chat,
        },
    )


@login_required
def get_message_response(request, chat_id: int, task_id: str):
    chat = get_object_or_404(Chat, user=request.user, id=chat_id)
    progress = Progress(AsyncResult(task_id))
    progress_info = progress.get_info()
    return TemplateResponse(
        request,
        "chat/components/chat_message_response.html",
        {
            "task_id": task_id,
            "progress": progress_info,
            "chat": chat,
        },
    )
