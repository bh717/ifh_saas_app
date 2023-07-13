import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from djstripe.enums import PlanInterval, SubscriptionStatus
from stripe.error import InvalidRequestError

from ..decorators import active_subscription_required, redirect_subscription_errors
from ..forms import UsageRecordForm
from ..helpers import get_stripe_module, get_subscription_urls
from ..metadata import ACTIVE_PLAN_INTERVALS, get_active_plan_interval_metadata, get_active_products_with_metadata
from ..models import SubscriptionModelBase
from ..wrappers import InvoiceFacade, SubscriptionWrapper

log = logging.getLogger("ifh_saas_app.subscription")


@redirect_subscription_errors
@login_required
def subscription(request):
    subscription_holder = request.user
    if subscription_holder.has_active_subscription():
        return _view_subscription(request, subscription_holder)
    else:
        return _upgrade_subscription(request, subscription_holder)


def _view_subscription(request, subscription_holder: SubscriptionModelBase):
    """
    Show user's active subscription
    """
    assert subscription_holder.has_active_subscription()
    subscription = subscription_holder.active_stripe_subscription
    wrapped_subscription = SubscriptionWrapper(subscription)
    next_invoice = None
    if not subscription.cancel_at_period_end:
        stripe = get_stripe_module()
        try:
            next_invoice = stripe.Invoice.upcoming(
                subscription=subscription.id,
            )
        except InvalidRequestError:
            # this error is raised if you try to get an invoice but the subcription is canceled
            # check if this happened and redirect to the upgrade page if so
            stripe_subscription = stripe.Subscription.retrieve(subscription.id)
            if stripe_subscription.status != SubscriptionStatus.active:
                log.warning(
                    "A canceled subscription was not synced to your app DB. "
                    "Your webhooks may not be set up properly. "
                    "See: https://docs.saaspegasus.com/subscriptions.html#webhooks"
                )
                # update the subscription in the database and clear from the subscriptoin_holder
                subscription.sync_from_stripe_data(stripe_subscription)
                subscription_holder.refresh_from_db()
                subscription_holder.clear_cached_subscription()
                return _upgrade_subscription(request, subscription_holder)
            else:
                # failed for some other unexpected reason.
                raise

    return render(
        request,
        "subscriptions/view_subscription.html",
        {
            "active_tab": "subscription",
            "page_title": _("Subscription"),
            "subscription": wrapped_subscription,
            "next_invoice": InvoiceFacade(next_invoice) if next_invoice else None,
            "subscription_urls": get_subscription_urls(subscription_holder),
        },
    )


def _upgrade_subscription(request, subscription_holder):
    """
    Show subscription upgrade form / options.
    """
    assert not subscription_holder.has_active_subscription()

    active_products = list(get_active_products_with_metadata())
    default_products = [p for p in active_products if p.metadata.is_default]
    default_product = default_products[0] if default_products else active_products[0]

    return render(
        request,
        "subscriptions/upgrade_subscription.html",
        {
            "active_tab": "subscription",
            "default_product": default_product,
            "active_products": active_products,
            "active_plan_intervals": get_active_plan_interval_metadata(),
            "default_interval": ACTIVE_PLAN_INTERVALS[0],
            "subscription_urls": get_subscription_urls(subscription_holder),
        },
    )


@login_required
def subscription_demo(request):
    subscription_holder = request.user
    subscription = subscription_holder.active_stripe_subscription
    wrapped_subscription = SubscriptionWrapper(subscription) if subscription else None
    return render(
        request,
        "subscriptions/demo.html",
        {
            "active_tab": "subscription_demo",
            "subscription": wrapped_subscription,
            "subscription_urls": get_subscription_urls(subscription_holder),
            "page_title": _("Subscription Demo"),
        },
    )


@login_required
@active_subscription_required
def subscription_gated_page(request):
    return render(request, "subscriptions/subscription_gated_page.html")


@login_required
@active_subscription_required
def metered_billing_demo(request):
    subscription_holder = request.user
    if request.method == "POST":
        form = UsageRecordForm(subscription_holder, request.POST)
        if form.is_valid():
            usage_data = form.save()
            messages.info(request, _("Successfully recorded {} units for metered billing.").format(usage_data.quantity))
            return HttpResponseRedirect(reverse("subscriptions:subscription_demo"))
    else:
        form = UsageRecordForm(subscription_holder)

    if not form.is_usable():
        messages.info(
            request,
            _(
                "It looks like you don't have any metered subscriptions set up. "
                "Sign up for a subscription with metered usage to use this UI."
            ),
        )
    return render(
        request,
        "subscriptions/metered_billing_demo.html",
        {
            "subscription": subscription_holder.active_stripe_subscription,
            "form": form,
        },
    )
