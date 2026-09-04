import logging
from collections import OrderedDict

from django import forms
from django.template.loader import get_template
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from i18nfield.forms import I18nFormField, I18nTextInput
from i18nfield.strings import LazyI18nString

from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import OrderPayment
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.multidomain.urlreverse import build_absolute_uri, eventreverse

from .api import SatspayAPI, SatspayError

logger = logging.getLogger(__name__)


class Satspay(BasePaymentProvider):
    identifier = "satspay"
    verbose_name = _("Satspay (Bitcoin / Lightning)")
    execute_payment_needs_user = True
    abort_pending_allowed = True

    @property
    def public_name(self):
        return str(
            self.settings.get("public_name", as_type=LazyI18nString)
            or _("Bitcoin / Lightning Network")
        )

    @property
    def test_mode_message(self):
        if not self.settings.endpoint:
            return _("You have not yet configured your LNbits Satspay endpoint.")
        return None

    @cached_property
    def client(self) -> SatspayAPI:
        return SatspayAPI(
            endpoint=str(self.settings.endpoint),
            api_key=str(self.settings.api_key),
        )

    @property
    def settings_form_fields(self):
        d = OrderedDict(
            [
                (
                    "endpoint",
                    forms.URLField(
                        label=_("LNbits Satspay API endpoint"),
                        help_text=_(
                            "Base URL of the Satspay extension of your LNbits "
                            "instance, e.g. https://lnbits.example.com/satspay/api/v1"
                        ),
                    ),
                ),
                (
                    "api_key",
                    SecretKeySettingsField(
                        label=_("Satspay API key"),
                        help_text=_(
                            "The invoice key of the LNbits wallet that has the "
                            "Satspay extension enabled."
                        ),
                    ),
                ),
                (
                    "wallet_id",
                    forms.CharField(
                        label=_("LNbits wallet ID"),
                        help_text=_(
                            "The wallet that will receive the Lightning payments "
                            "(shown in the wallet URL of your LNbits wallet)."
                        ),
                    ),
                ),
                (
                    "onchain_wallet_id",
                    forms.CharField(
                        label=_("On-chain wallet ID (optional)"),
                        help_text=_(
                            "If you want to accept on-chain Bitcoin payments as well, "
                            "the ID of a watch-only wallet belonging to the same "
                            "LNbits user."
                        ),
                        required=False,
                    ),
                ),
                (
                    "expiry",
                    forms.IntegerField(
                        label=_("Payment link expiry (minutes)"),
                        min_value=1,
                        initial=30,
                    ),
                ),
                (
                    "public_name",
                    I18nFormField(
                        label=_("Payment method name"),
                        widget=I18nTextInput,
                        help_text=_(
                            "The name of the payment method that is shown to your "
                            "customers during checkout."
                        ),
                    ),
                ),
            ]
            + list(super().settings_form_fields.items())
        )
        d.move_to_end("public_name", last=False)
        d.move_to_end("_enabled", last=False)
        return d

    def settings_content_render(self, request) -> str:
        if not self.settings.endpoint or not self.settings.api_key:
            return """
<p>{}</p>
<p><b>{}</b></p>
<ul>
    <li>{}</li>
    <li>{}</li>
    <li>{}</li>
</ul>
""".format(
                _(
                    "To accept payments, you need an LNbits instance with the Satspay "
                    "extension enabled on the wallet that should receive the payments."
                ),
                _("You will need:"),
                _(
                    "The base URL of the Satspay extension (e.g. "
                    "https://lnbits.example.com/satspay/api/v1)"
                ),
                _(
                    "The invoice key of the receiving wallet (the link labelled "
                    "\"invoice\" in the wallet's API key section)"
                ),
                _(
                    "The wallet ID of the receiving wallet (can be found in the "
                    "wallet's URL, after /wallet/)"
                ),
            )
        return ""

    def payment_form_render(self, request) -> str:
        template = get_template("pretix_satspay/checkout_payment_form.html")
        ctx = {"request": request, "event": self.event, "settings": self.settings}
        return template.render(ctx)

    def checkout_confirm_render(self, request, order=None, info_data=None) -> str:
        template = get_template("pretix_satspay/checkout_payment_confirm.html")
        ctx = {"request": request, "event": self.event, "order": order}
        return template.render(ctx)

    def payment_is_valid_session(self, request) -> bool:
        return True

    def checkout_prepare(self, request, cart) -> bool:
        return True

    def execute_payment(self, request, payment: OrderPayment):
        webhook_url = build_absolute_uri(
            self.event,
            "plugins:pretix_satspay:webhook",
            kwargs={
                "order": payment.order.code,
                "payment": payment.pk,
            },
        )
        order_url = eventreverse(
            self.event,
            "presale:event.order",
            kwargs={
                "order": payment.order.code,
                "secret": payment.order.secret,
            },
        )
        try:
            charge = self.client.create_charge(
                description="{} - order {}".format(
                    self.event.name, payment.order.code
                ),
                expiry_minutes=int(self.settings.get("expiry", as_type=int) or 30),
                currency=self.event.currency,
                currency_amount=float(payment.amount),
                webhook=webhook_url,
                completelink=order_url,
                lnbits_wallet=str(self.settings.wallet_id),
                onchain_wallet=str(self.settings.onchain_wallet_id) or None,
            )
        except SatspayError:
            logger.exception("Satspay: could not create charge")
            raise PaymentException(
                _(
                    "We had trouble creating your payment. Please try again and get "
                    "in touch with us if this problem persists."
                )
            )
        payment.info_data = {
            "charge_id": charge["id"],
            "amount": charge.get("amount"),
        }
        payment.save(update_fields=["info"])
        payment.order.log_action(
            "pretix_satspay.charge.created",
            data={"charge_id": charge["id"]},
        )
        return self.client.charge_page_url(charge["id"])

    def payment_pending_render(self, request, payment: OrderPayment) -> str:
        template = get_template("pretix_satspay/pending.html")
        charge_id = payment.info_data.get("charge_id")
        ctx = {
            "request": request,
            "event": self.event,
            "settings": self.settings,
            "order": payment.order,
            "payment": payment,
            "charge_link": self.client.charge_page_url(charge_id),
            "status_url": self.client.charge_public_status_url(charge_id),
        }
        return template.render(ctx)

    def order_pending_mail_render(self, order, payment: OrderPayment) -> str:
        charge_id = payment.info_data.get("charge_id")
        return _("To pay for your order, please visit the following page: {url}").format(
            url=self.client.charge_page_url(charge_id)
        )

    def payment_control_render(self, request, payment: OrderPayment) -> str:
        template = get_template("pretix_satspay/control.html")
        charge_id = payment.info_data.get("charge_id")
        status = {}
        if charge_id:
            try:
                status = self.client.get_charge(charge_id)
            except Exception:
                status = {}
        ctx = {
            "request": request,
            "event": self.event,
            "payment": payment,
            "charge_id": charge_id,
            "status": status,
        }
        return template.render(ctx)

    def payment_control_render_short(self, payment: OrderPayment) -> str:
        charge_id = payment.info_data.get("charge_id")
        return "#" + charge_id if charge_id else self.verbose_name

    def payment_presale_render(self, payment: OrderPayment) -> str:
        return "Satspay"

    def matching_id(self, payment: OrderPayment) -> str:
        return payment.info_data.get("charge_id")

    def api_payment_details(self, payment: OrderPayment) -> dict:
        return {
            "charge_id": payment.info_data.get("charge_id"),
        }

    def payment_refund_supported(self, payment: OrderPayment) -> bool:
        return False

    def payment_partial_refund_supported(self, payment: OrderPayment) -> bool:
        return False

    def shred_payment_info(self, obj):
        info = obj.info_data
        info["charge_id"] = "█" if info.get("charge_id") else ""
        obj.info_data = info
        obj.save(update_fields=["info"])