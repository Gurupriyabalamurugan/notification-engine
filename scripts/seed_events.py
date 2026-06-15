"""Send sample Order/Payment/Shipping notification events to the API."""

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLES = [
    {
        "idempotency_key": "seed-payment-otp-1",
        "source_service": "payment",
        "event_type": "otp",
        "user_id": "user-100",
        "channels": ["sms"],
        "payload": {"code": "654321", "phone": "+15551234567"},
    },
    {
        "idempotency_key": "seed-order-confirmed-1",
        "source_service": "order",
        "event_type": "confirmed",
        "user_id": "user-100",
        "channels": ["email", "push"],
        "payload": {"order_id": "O-12345", "total": 99.99},
    },
    {
        "idempotency_key": "seed-shipping-delivered-1",
        "source_service": "shipping",
        "event_type": "delivered",
        "user_id": "user-100",
        "channels": ["sms", "email"],
        "payload": {"tracking_id": "TRK-98765"},
    },
    {
        "idempotency_key": "seed-order-marketing-1",
        "source_service": "order",
        "event_type": "marketing",
        "user_id": "user-200",
        "channels": ["email"],
        "payload": {"campaign": "spring-sale"},
    },
]


async def seed(base_url: str) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        for event in SAMPLES:
            response = await client.post("/v1/notifications", json=event)
            print(f"{event['idempotency_key']}: HTTP {response.status_code} -> {response.json()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed sample notification events")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Notification API base URL",
    )
    args = parser.parse_args()
    asyncio.run(seed(args.base_url))


if __name__ == "__main__":
    main()
