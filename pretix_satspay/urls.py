from pretix.multidomain import event_url

from .views import webhook

event_patterns = [
    event_url(r"^satspay/webhook/(?P<order>[^/]+)/(?P<payment>[^/]+)/$", webhook, name="webhook", require_live=False),
]
