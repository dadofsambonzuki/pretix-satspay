import json
import logging

from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt

from pretix.base.models import OrderPayment, Quota
from pretix.base.services.locking import LockTimeoutException

from .payment import Satspay

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request, *args, **kwargs):
    order_code = kwargs.get("order")
    payment_id = kwargs.get("payment")
    if not all((order_code, payment_id)):
        return HttpResponseBadRequest("Missing parameters")

    # Satspay sends the full charge JSON as the request body (both for the
    # default POST and the optional GET-with-body webhook method).
    try:
        payload = json.loads(request.body)
        charge_id = payload.get("id")
    except (ValueError, TypeError):
        charge_id = None
    if not charge_id:
        return HttpResponseBadRequest("Invalid payload")

    try:
        order = request.event.orders.get(code=order_code)
    except Exception:
        return HttpResponseNotFound("Order not found")

    if not order.payments.filter(pk=payment_id, provider="satspay").exists():
        return HttpResponseNotFound("Payment not found")

    payment = order.payments.get(pk=payment_id, provider="satspay")

    if payment.info_data.get("charge_id") != charge_id:
        return HttpResponseBadRequest("Charge does not match payment")

    prov = Satspay(order.event)
    try:
        charge = prov.client.get_charge(charge_id)
    except Exception:
        logger.exception("Satspay: charge lookup failed")
        return HttpResponse("Unavailable", status=503)

    order.log_action("pretix_satspay.webhook", data=charge)

    if not charge.get("paid"):
        return HttpResponse(status=200)

    if payment.state not in (
        OrderPayment.PAYMENT_STATE_CREATED,
        OrderPayment.PAYMENT_STATE_PENDING,
    ):
        return HttpResponse(status=200)

    with transaction.atomic():
        payment.refresh_from_db()
        if payment.state in (
            OrderPayment.PAYMENT_STATE_CREATED,
            OrderPayment.PAYMENT_STATE_PENDING,
        ):
            try:
                payment.confirm()
            except LockTimeoutException:
                return HttpResponse("Lock timeout, please try again.", status=503)
            except Quota.QuotaExceededException:
                return HttpResponse("Quota exceeded.", status=200)
    return HttpResponse(status=200)