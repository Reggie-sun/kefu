# -*- coding: utf-8 -*-#

from types import SimpleNamespace
from typing import Optional

from wechatpy import parse_message
from wechatpy.replies import ArticlesReply, ImageReply, VoiceReply, create_reply

from bridge.context import ContextType
from channel.chat_message import ChatMessage
from common.log import logger
from common.tmp_dir import TmpDir
from common.unified_message import UnifiedMessage


class WeChatMPMessage(ChatMessage):
    def __init__(self, msg, client=None, raw_xml: Optional[bytes] = None):
        super().__init__(msg)
        self.msg_id = getattr(msg, "id", None)
        self.create_time = getattr(msg, "time", None)
        self.is_group = False
        self.message_type = None

        if msg.type == "text":
            self.ctype = ContextType.TEXT
            self.content = msg.content
        elif msg.type == "voice":
            if msg.recognition is None:
                self.ctype = ContextType.VOICE
                self.content = TmpDir().path() + msg.media_id + "." + msg.format  # content直接存临时目录路径

                def download_voice():
                    # 如果响应状态码是200，则将响应内容写入本地文件
                    response = client.media.download(msg.media_id)
                    if response.status_code == 200:
                        with open(self.content, "wb") as f:
                            f.write(response.content)
                    else:
                        logger.info(f"[wechatmp] Failed to download voice file, {response.content}")

                self._prepare_fn = download_voice
            else:
                self.ctype = ContextType.TEXT
                self.content = msg.recognition
        elif msg.type == "image":
            self.ctype = ContextType.IMAGE
            self.content = TmpDir().path() + msg.media_id + ".png"  # content直接存临时目录路径

            def download_image():
                # 如果响应状态码是200，则将响应内容写入本地文件
                response = client.media.download(msg.media_id)
                if response.status_code == 200:
                    with open(self.content, "wb") as f:
                        f.write(response.content)
                else:
                    logger.info(f"[wechatmp] Failed to download image file, {response.content}")

            self._prepare_fn = download_image
        elif msg.type == "event":
            self.ctype = None
            self.content = getattr(msg, "event", None)
            self.message_type = f"event.{getattr(msg, 'event', 'unknown')}"
        else:
            raise NotImplementedError("Unsupported message type: Type:{} ".format(msg.type))

        self.from_user_id = msg.source
        self.to_user_id = msg.target
        self.other_user_id = msg.source

        mapped_keys = ["id", "time", "source", "target", "type", "content", "media_id", "format", "recognition", "event"]
        self.unified_message = self.to_unified_message(channel="wechat-mp", mapped_keys=mapped_keys)
        self.unified_message.metadata.update(
            {
                "is_group": False,
                "raw_xml": raw_xml.decode("utf-8") if raw_xml else None,
            }
        )


def parse_wechatmp_xml_to_unified(xml_bytes: bytes, client=None) -> UnifiedMessage:
    """Parse raw XML payload from WeChat MP into UnifiedMessage with preserved raw data."""
    msg = parse_message(xml_bytes)
    msg.channel = "wechat-mp"
    wechat_msg = WeChatMPMessage(msg, client=client, raw_xml=xml_bytes)
    return wechat_msg.unified_message


def unified_to_wechatmp_reply_xml(unified: UnifiedMessage, to_user: Optional[str] = None, from_user: Optional[str] = None) -> str:
    """Map UnifiedMessage into WeChat MP reply XML using wechatpy replies."""

    class _ReplyStub(SimpleNamespace):
        pass

    target = to_user or unified.receiver
    source = from_user or unified.sender
    stub_msg = _ReplyStub(target=target, source=source)

    if unified.message_type == "text":
        reply_obj = create_reply(unified.content or "", stub_msg)
    elif unified.message_type == "image":
        reply_obj = ImageReply(message=stub_msg)
        reply_obj.media_id = unified.media_url or str(unified.content or "")
    elif unified.message_type == "voice":
        reply_obj = VoiceReply(message=stub_msg)
        reply_obj.media_id = unified.media_url or str(unified.content or "")
    elif unified.message_type == "news":
        reply_obj = ArticlesReply(message=stub_msg)
        articles = unified.metadata.get("articles", [])
        for article in articles:
            reply_obj.add_article(
                {
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "image": article.get("image", ""),
                }
            )
        if not reply_obj.articles:
            reply_obj.add_article({"title": str(unified.content or ""), "description": "", "url": "", "image": ""})
    else:
        reply_obj = create_reply(str(unified.content or ""), stub_msg)

    if unified.timestamp:
        reply_obj.create_time = int(unified.timestamp)

    return reply_obj.render()
