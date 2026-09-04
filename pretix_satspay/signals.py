from django.dispatch import receiver

from pretix.base.signals import register_payment_providers


@receiver(register_payment_providers, dispatch_uid="pretix_satspay")
def register_payment_provider(sender, **kwargs):
    from .payment import Satspay

    return Satspay