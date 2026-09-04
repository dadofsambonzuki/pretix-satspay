from typing import Any

import requests

from pretix.base.payment import PaymentException


class SatspayError(PaymentException):
    pass


class SatspayAPI:
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = self.endpoint + path
        headers = {"X-Api-Key": self.api_key}
        try:
            response = requests.request(
                method, url, headers=headers, timeout=15, **kwargs
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise SatspayError(
                "We had trouble communicating with the payment provider. "
                "Please try again and get in touch with us if this problem persists."
            ) from e
        return response.json()

    def create_charge(
        self,
        *,
        description: str,
        expiry_minutes: int,
        currency: str,
        currency_amount: float,
        webhook: str,
        completelink: str,
        lnbits_wallet: str,
        onchain_wallet: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "description": description,
            "time": expiry_minutes,
            "currency": currency,
            "currency_amount": currency_amount,
            "webhook": webhook,
            "completelink": completelink,
            "completelinktext": "Back to your order",
            "lnbitswallet": lnbits_wallet,
        }
        if onchain_wallet:
            payload["onchainwallet"] = onchain_wallet
        return self._request("POST", "/charge", json=payload)

    def get_charge(self, charge_id: str) -> dict[str, Any]:
        return self._request("GET", f"/charge/{charge_id}")

    def charge_page_url(self, charge_id: str) -> str:
        return self.endpoint.rsplit("/api/v1", 1)[0] + f"/{charge_id}"

    def charge_public_status_url(self, charge_id: str) -> str:
        return self.endpoint + f"/charge/public/{charge_id}"