from celery import shared_task
from stripe.error import StripeError

from apps.users.models import CustomUser

from .helpers import sync_subscription_model_with_stripe


@shared_task
def sync_subscriptions_task():
    for user in CustomUser.get_items_needing_sync():
        try:
            sync_subscription_model_with_stripe(user)
        except StripeError as e:
            raise  # you may want to swallow and log this error so it doesn't prevent other subscriptions from syncing
