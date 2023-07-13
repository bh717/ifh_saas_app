from django.core.management.base import BaseCommand

from apps.subscriptions.helpers import sync_subscription_model_with_stripe
from apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Syncs Stripe subscriptions for associated data models"

    def handle(self, **options):
        for user in CustomUser.get_items_needing_sync():
            print(f'syncing {user} with Stripe. Last synced: {user.last_synced_with_stripe or "never"}')
            sync_subscription_model_with_stripe(user)
