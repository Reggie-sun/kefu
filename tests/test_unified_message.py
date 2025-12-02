import unittest

from bridge.context import ContextType
from channel.chat_message import ChatMessage
from common.unified_message import UnifiedMessage


class StubChatMessage(ChatMessage):
    def __init__(self, raw_payload, ctype=ContextType.TEXT):
        super().__init__(raw_payload)
        self.msg_id = raw_payload.get("MsgId")
        self.create_time = raw_payload.get("CreateTime")
        self.ctype = ctype
        self.content = raw_payload.get("Content")
        self.from_user_id = raw_payload.get("FromUserName")
        self.from_user_nickname = "from_nick"
        self.to_user_id = raw_payload.get("ToUserName")
        self.to_user_nickname = "to_nick"
        self.other_user_id = self.from_user_id
        self.other_user_nickname = "other_nick"


class UnifiedMessageTests(unittest.TestCase):
    def test_maps_core_fields_and_unmapped_raw(self):
        raw_payload = {
            "MsgId": "123",
            "CreateTime": 1700000000,
            "FromUserName": "from",
            "ToUserName": "to",
            "Content": "hello",
            "Type": "Text",
            "UnusedField": "keep_me",
        }
        msg = StubChatMessage(raw_payload)
        unified = msg.to_unified_message(
            channel="wechat",
            mapped_keys=["MsgId", "CreateTime", "FromUserName", "ToUserName", "Content", "Type"],
        )

        self.assertEqual(unified.sender, "from")
        self.assertEqual(unified.receiver, "to")
        self.assertEqual(unified.channel, "wechat")
        self.assertEqual(unified.message_type, "text")
        self.assertEqual(unified.content, "hello")
        self.assertEqual(unified.timestamp, 1700000000)
        self.assertEqual(unified.message_id, "123")
        self.assertIn("raw_payload", unified.metadata)
        self.assertEqual(unified.metadata["raw_payload"]["UnusedField"], "keep_me")
        self.assertIn("UnusedField", unified.metadata["unmapped_fields"])

    def test_preserves_raw_object_via_dict(self):
        class RawObj:
            def __init__(self):
                self.foo = "bar"

        raw = RawObj()
        msg = StubChatMessage({"MsgId": "1", "CreateTime": 1, "FromUserName": "a", "ToUserName": "b", "Content": "c"})
        msg._rawmsg = raw
        unified = msg.to_unified_message(channel="wechat")

        self.assertEqual(unified.metadata["raw_payload"]["foo"], "bar")
        self.assertEqual(unified.metadata["unmapped_fields"], [])

    def test_validate_requires_content_or_media(self):
        with self.assertRaises(ValueError):
            UnifiedMessage(
                sender="a",
                receiver="b",
                channel="wechat",
                message_type="image",
                content=None,
                media_url=None,
            )


if __name__ == "__main__":
    unittest.main()
