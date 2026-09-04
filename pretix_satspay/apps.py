from pretix.base.plugins import PluginConfig

from . import PretixPluginMeta


class SatspayAppConfig(PluginConfig):
    name = 'pretix_satspay'
    verbose_name = 'LNBits SatsPay Server'
    default = True

    PretixPluginMeta = PretixPluginMeta

    def ready(self):
        from . import signals  # NOQA
