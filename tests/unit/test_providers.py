import random

import pytest

from app.domain.enums import ChannelType
from app.providers.mock_email import MockEmailProvider
from app.providers.mock_sms import MockSMSProvider
from app.providers.registry import ProviderRegistry


@pytest.mark.asyncio
async def test_mock_provider_success_when_configured() -> None:
    provider = MockEmailProvider(failure_rate=0.0, is_down=False, rng=random.Random(0))

    result = await provider.send(user_id="user-1", payload={"subject": "Hello"})

    assert result.success is True
    assert result.provider_ref is not None
    assert result.provider_ref.startswith("email-")


@pytest.mark.asyncio
async def test_mock_provider_failure_when_down() -> None:
    provider = MockSMSProvider(is_down=True)

    result = await provider.send(user_id="user-1", payload={"code": "123456"})

    assert result.success is False
    assert result.error == "sms provider is down"


@pytest.mark.asyncio
async def test_mock_provider_respects_failure_rate() -> None:
    provider = MockEmailProvider(failure_rate=1.0, rng=random.Random(0))

    result = await provider.send(user_id="user-1", payload={})

    assert result.success is False
    assert "simulated failure" in (result.error or "")


@pytest.mark.asyncio
async def test_provider_health_check() -> None:
    up = MockEmailProvider(is_down=False)
    down = MockSMSProvider(is_down=True)

    assert await up.health_check() is True
    assert await down.health_check() is False


def test_registry_returns_provider_by_channel() -> None:
    email = MockEmailProvider()
    sms = MockSMSProvider(is_down=True)
    registry = ProviderRegistry(
        {
            ChannelType.EMAIL: email,
            ChannelType.SMS: sms,
        }
    )

    assert registry.get(ChannelType.EMAIL) is email
    assert registry.get(ChannelType.SMS) is sms
