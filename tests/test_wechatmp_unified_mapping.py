import unittest

try:
    import wechatpy  # noqa: F401

    WECHATPY_AVAILABLE = True
except ImportError:
    WECHATPY_AVAILABLE = False

from common.unified_message import UnifiedMessage

if WECHATPY_AVAILABLE:
    from channel.wechatmp.wechatmp_message import parse_wechatmp_xml_to_unified, unified_to_wechatmp_reply_xml
else:
    parse_wechatmp_xml_to_unified = None
    unified_to_wechatmp_reply_xml = None


TEXT_XML = b"""
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1700000000</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[hello]]></Content>
  <MsgId>1234567890123456</MsgId>
</xml>
"""

EVENT_XML = b"""
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1700000000</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[subscribe]]></Event>
  <EventKey><![CDATA[]]></EventKey>
</xml>
"""


@unittest.skipUnless(WECHATPY_AVAILABLE, "wechatpy not installed")
class WechatMpUnifiedMappingTests(unittest.TestCase):
    def test_parse_text_xml_to_unified_and_preserve_raw(self):
        unified = parse_wechatmp_xml_to_unified(TEXT_XML)
        self.assertEqual(unified.sender, "fromUser")
        self.assertEqual(unified.receiver, "toUser")
        self.assertEqual(unified.content, "hello")
        self.assertEqual(unified.message_id, "1234567890123456")
        self.assertEqual(unified.timestamp, 1700000000)
        self.assertEqual(unified.message_type, "text")
        self.assertIn("raw_xml", unified.metadata)
        self.assertIn("raw_payload", unified.metadata)

    def test_parse_event_subscribe_to_unified_message(self):
        unified = parse_wechatmp_xml_to_unified(EVENT_XML)
        self.assertEqual(unified.message_type, "event.subscribe")
        self.assertEqual(unified.content, "subscribe")
        self.assertEqual(unified.sender, "fromUser")
        self.assertEqual(unified.receiver, "toUser")

    def test_unified_reply_to_wechatmp_reply_xml(self):
        ts = 1700000000
        text_reply = UnifiedMessage(
            sender="bot",
            receiver="user",
            channel="wechat-mp",
            message_type="text",
            content="hi there",
            timestamp=ts,
        )
        xml = unified_to_wechatmp_reply_xml(text_reply)
        self.assertIn("<MsgType><![CDATA[text]]></MsgType>", xml)
        self.assertIn("<Content><![CDATA[hi there]]></Content>", xml)
        self.assertIn("<ToUserName><![CDATA[user]]></ToUserName>", xml)
        self.assertIn("<FromUserName><![CDATA[bot]]></FromUserName>", xml)

        image_reply = UnifiedMessage(
            sender="bot",
            receiver="user",
            channel="wechat-mp",
            message_type="image",
            content=None,
            media_url="MEDIA123",
            timestamp=ts,
        )
        xml_image = unified_to_wechatmp_reply_xml(image_reply)
        self.assertIn("<MsgType><![CDATA[image]]></MsgType>", xml_image)
        self.assertIn("<MediaId><![CDATA[MEDIA123]]></MediaId>", xml_image)

        news_reply = UnifiedMessage(
            sender="bot",
            receiver="user",
            channel="wechat-mp",
            message_type="news",
            content=None,
            timestamp=ts,
            metadata={
                "articles": [
                    {"title": "A", "description": "B", "url": "https://example.com", "image": "https://example.com/img.png"}
                ]
            },
        )
        xml_news = unified_to_wechatmp_reply_xml(news_reply)
        self.assertIn("<MsgType><![CDATA[news]]></MsgType>", xml_news)
        self.assertIn("<Title><![CDATA[A]]></Title>", xml_news)
        self.assertIn("<Description><![CDATA[B]]></Description>", xml_news)
        self.assertIn("<Url><![CDATA[https://example.com]]></Url>", xml_news)


if __name__ == "__main__":
    unittest.main()
