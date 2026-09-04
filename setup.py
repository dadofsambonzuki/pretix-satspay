from setuptools import find_packages, setup

setup(
    name="pretix-satspay",
    version="0.1.0",
    description="Accept Bitcoin payments in pretix via the LNbits Satspay extension",
    long_description="""# pretix Satspay

Accept Bitcoin Lightning and on-chain Bitcoin payments in [pretix](https://pretix.eu/) using the [Satspay](https://github.com/lnbits/satspay) extension of a self-hosted [LNbits](https://lnbits.com/) instance.

The customer pays on the Satspay payment page hosted by your LNbits instance. A webhook and a small polling script in the pending-payment page keep pretix in sync with the payment status.
""",
    long_description_content_type="text/markdown",
    author="Nathan Day",
    author_email="nathan@day.ag",
    url="https://github.com/dadofsambonzuki/pretix-satspay",
    license="MIT",
    install_requires=["django>=4", "i18nfield>=0.6", "requests>=2"],
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    entry_points="""
[pretix.plugin]
pretix_satspay=pretix_satspay:PretixPluginMeta
""",
    python_requires=">=3.11",
)