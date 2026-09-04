__version__ = "0.1.0"

try:
    from pretix.base.plugins import PluginType
except ImportError:
    PluginType = None


class PretixPluginMeta:
    name = "pretix Satspay"
    author = "Nathan Day"
    description = "Pay with Bitcoin (Lightning / on-chain) via the LNbits Satspay extension"
    visible = True
    version = __version__
    category = "PAYMENT"


if PluginType is not None:
    PretixPluginMeta.type = PluginType.PAYMENT