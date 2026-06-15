from app.config import Settings, get_settings
from app.domain.enums import ChannelType
from app.providers.base import NotificationProvider
from app.providers.mock_email import MockEmailProvider
from app.providers.mock_push import MockPushProvider
from app.providers.mock_sms import MockSMSProvider


class ProviderRegistry:
    def __init__(self, providers: dict[ChannelType, NotificationProvider] | None = None) -> None:
        self._providers: dict[ChannelType, NotificationProvider] = providers or {}

    def register(self, channel: ChannelType, provider: NotificationProvider) -> None:
        self._providers[channel] = provider

    def get(self, channel: ChannelType) -> NotificationProvider:
        try:
            return self._providers[channel]
        except KeyError as exc:
            raise KeyError(f"No provider registered for channel {channel.value}") from exc

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ProviderRegistry":
        settings = settings or get_settings()
        registry = cls()
        registry.register(
            ChannelType.EMAIL,
            MockEmailProvider(
                failure_rate=settings.mock_email_failure_rate,
                is_down=settings.mock_email_down,
                latency_ms=settings.mock_email_latency_ms,
            ),
        )
        registry.register(
            ChannelType.SMS,
            MockSMSProvider(
                failure_rate=settings.mock_sms_failure_rate,
                is_down=settings.mock_sms_down,
                latency_ms=settings.mock_sms_latency_ms,
            ),
        )
        registry.register(
            ChannelType.PUSH,
            MockPushProvider(
                failure_rate=settings.mock_push_failure_rate,
                is_down=settings.mock_push_down,
                latency_ms=settings.mock_push_latency_ms,
            ),
        )
        return registry
