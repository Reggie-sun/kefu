from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

from bridge.context import ContextType


def map_ctype_to_message_type(ctype: Optional[ContextType]) -> str:
    """Map internal ContextType to a transport-friendly message_type string."""
    mapping = {
        ContextType.TEXT: "text",
        ContextType.VOICE: "voice",
        ContextType.IMAGE: "image",
        ContextType.FILE: "file",
        ContextType.VIDEO: "video",
        ContextType.SHARING: "sharing",
        ContextType.ACCEPT_FRIEND: "event.accept_friend",
        ContextType.JOIN_GROUP: "event.join_group",
        ContextType.EXIT_GROUP: "event.exit_group",
        ContextType.PATPAT: "event.patpat",
        ContextType.FUNCTION: "function",
        ContextType.IMAGE_CREATE: "command.image_create",
    }
    return mapping.get(ctype, "unknown")


def _safe_raw_payload(raw_payload: Any) -> Any:
    """Try to keep the raw payload for traceability; fall back to repr if not serialisable."""
    if isinstance(raw_payload, (str, int, float, bool)) or raw_payload is None:
        return raw_payload
    if isinstance(raw_payload, Mapping):
        return dict(raw_payload)
    try:
        return raw_payload.__dict__
    except Exception:
        return repr(raw_payload)


def _compute_unmapped_fields(raw_payload: Any, mapped_keys: Iterable[str]) -> List[str]:
    if not isinstance(raw_payload, Mapping):
        return []
    mapped = set(mapped_keys) if mapped_keys else set()
    return sorted([k for k in raw_payload.keys() if k not in mapped])


@dataclass
class UnifiedMessage:
    """Channel-agnostic message contract for upstream/downstream processing."""

    sender: str
    receiver: str
    channel: str
    message_type: str
    content: Any
    timestamp: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: Optional[str] = None
    media_url: Optional[str] = None

    def __post_init__(self):
        self.validate()

    def validate(self) -> "UnifiedMessage":
        if not self.sender:
            raise ValueError("UnifiedMessage.sender is required")
        if not self.receiver:
            raise ValueError("UnifiedMessage.receiver is required")
        if not self.channel:
            raise ValueError("UnifiedMessage.channel is required")
        if not self.message_type:
            raise ValueError("UnifiedMessage.message_type is required")
        has_articles = isinstance(self.metadata, dict) and bool(self.metadata.get("articles"))
        if self.content is None and self.media_url is None and not (self.message_type == "news" and has_articles):
            raise ValueError("UnifiedMessage.content or media_url must be provided")
        if not isinstance(self.metadata, dict):
            raise ValueError("UnifiedMessage.metadata must be a dictionary")
        return self

    @classmethod
    def from_chat_message(cls, chat_message: Any, channel: str, mapped_keys: Optional[Iterable[str]] = None) -> "UnifiedMessage":
        explicit_type = getattr(chat_message, "message_type", None)
        message_type = explicit_type or map_ctype_to_message_type(getattr(chat_message, "ctype", None))
        raw_payload = _safe_raw_payload(getattr(chat_message, "_rawmsg", None))
        inferred_mapped = mapped_keys
        if inferred_mapped is None and isinstance(raw_payload, Mapping):
            inferred_mapped = raw_payload.keys()
        metadata = {
            "raw_payload": raw_payload,
            "unmapped_fields": _compute_unmapped_fields(raw_payload, inferred_mapped or []),
        }
        content = getattr(chat_message, "content", None)
        media_url = getattr(chat_message, "media_url", None)
        if media_url is None and message_type in {"voice", "image", "video", "file"} and isinstance(content, str):
            media_url = content

        return cls(
            sender=getattr(chat_message, "from_user_id", ""),
            receiver=getattr(chat_message, "to_user_id", ""),
            channel=channel,
            message_type=message_type,
            content=content,
            timestamp=getattr(chat_message, "create_time", None),
            metadata=metadata,
            message_id=getattr(chat_message, "msg_id", None),
            media_url=media_url,
        )

    def to_channel_response(self, reply_text: str, success: bool = True, error: Optional[str] = None) -> Dict[str, Any]:
        """Render a reply back to the originating channel with a minimal, structured payload."""
        return {
            "channel": self.channel,
            "target": self.sender,
            "message_type": "text",
            "content": reply_text,
            "success": success,
            "error": error,
        }
