import unittest
from unittest.mock import MagicMock, patch

from bot.smart_gateway.smart_gateway_bot import SmartGatewayBot
from bridge.context import Context, ContextType
from channel.chat_message import ChatMessage


class StubMsg(ChatMessage):
    def __init__(self):
        raw = {"MsgId": "m1", "CreateTime": 1, "FromUserName": "u1", "ToUserName": "bot", "Content": "hello"}
        super().__init__(raw)
        self.msg_id = raw["MsgId"]
        self.create_time = raw["CreateTime"]
        self.ctype = ContextType.TEXT
        self.content = raw["Content"]
        self.from_user_id = raw["FromUserName"]
        self.to_user_id = raw["ToUserName"]
        self.other_user_id = raw["FromUserName"]
        self.unified_message = self.to_unified_message(channel="wechat", mapped_keys=raw.keys())


class SmartGatewayBotTests(unittest.TestCase):
    @patch("bot.smart_gateway.gateway_client.requests.post")
    def test_builds_payload_and_parses_reply(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "reply_text": "ok",
            "kb_hit": True,
            "confidence": 0.9,
            "tool_calls": [{"name": "lookup_order"}],
            "latency": {"total": 120},
        }
        mock_post.return_value = mock_resp

        bot = SmartGatewayBot()
        context = Context(ContextType.TEXT, "hello", {"msg": StubMsg(), "session_id": "sess-1"})

        reply = bot.reply("hello", context)

        self.assertEqual(reply.type.name, "TEXT")
        self.assertEqual(reply.content, "ok")
        called_payload = mock_post.call_args[1]["json"]
        self.assertEqual(called_payload["session_id"], "sess-1")
        self.assertEqual(called_payload["message"]["content"], "hello")
        self.assertIn("rag", called_payload)
        self.assertIn("tools_allowed", called_payload)


if __name__ == "__main__":
    unittest.main()
