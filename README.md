# pretix Satspay

Accept Bitcoin Lightning and on-chain Bitcoin payments in [pretix](https://pretix.eu/) using the [Satspay](https://github.com/lnbits/satspay) extension of a self-hosted [LNbits](https://lnbits.com/) instance.

The customer pays on the Satspay payment page hosted by your LNbits instance. A webhook and a small polling script in the pending-payment page keep pretix in sync with the payment status.

## Requirements

- **pretix** ≥ 4.0 (Django-based event management platform)
- **Python** ≥ 3.11
- **LNbits** instance with the [Satspay extension](https://github.com/lnbits/satspay) enabled
- Django ≥ 4, requests, i18nfield

## Installation

```bash
# Install from source
pip install -e .
```

Then activate the plugin in the pretix "Plugins" settings page. You can also enable the plugin per event.

## Configuration

In the event's **Settings → Payment → Satspay (Bitcoin / Lightning)** you need to provide:

| Setting | Description |
|---|---|
| **LNbits Satspay API endpoint** | Base URL of the Satspay extension, e.g. `https://lnbits.example.com/satspay/api/v1` |
| **Satspay API key** | The **invoice key** of the LNbits wallet that has the Satspay extension enabled |
| **LNbits wallet ID** | The wallet that will receive the payments (shown in the wallet URL after `/wallet/`) |
| **On-chain wallet ID (optional)** | If you want to accept on-chain Bitcoin payments as well, the ID of a watch-only wallet belonging to the same LNbits user |
| **Payment link expiry** | How many minutes before the payment link expires (default: 30) |
| **Payment method name** | Custom name shown to customers during checkout |

### Webhook

The webhook endpoint is unique per order and payment to ensure secure matching:
- `https://yourpretix.example.com/{event}/satspay/webhook/{order_code}/{payment_id}/`

No external signature verification is needed because the webhook URL itself contains the order and payment identifiers, making it effectively a bearer token.

## How it works

1. Customer selects "Bitcoin / Lightning Network" during checkout
2. A charge is created on your LNbits Satspay extension
3. Customer is redirected to the Satspay payment page
4. Satspay sends a webhook callback to pretix when the payment is complete
5. The webhook handler verifies the charge, confirms the payment
6. While the payment is pending, the order page polls for status updates via the public Satspay status endpoint
7. On successful payment, the order is confirmed; on expiry, the payment is marked as failed

## Development

```bash
# Clone the repo
git clone https://github.com/dadofsambonzuki/pretix-satspay
cd pretix-satspay

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

## License

MIT