from django.urls import include, path

from pretix.multidomain import event_url

from .views import webhook

event_patterns = [
    path(
        "satspay/",
        include(
            [
                path(
                    "webhook/<str:order>/<str:payment>/",
                    event_url(webhook, name="webhook", require_live=False),
                ),
            ]
        ),
    ),
]