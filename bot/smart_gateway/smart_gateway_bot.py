import os
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from bot.smart_gateway.gateway_client import GatewayClient, GatewayRagConfig, GatewayRequest
from bridge.context import Context
from bridge.reply import Reply, ReplyType
from common.log import logger
from common.unified_message import UnifiedMessage
from config import conf


class SmartGatewayBot:
    """Bot wrapper that forwards chat to external Smart Gateway /chat endpoint."""

    def __init__(self):
        cfg = conf()
        base_url = cfg.get("smart_gateway_base_url", "http://localhost:8000")
        timeout = cfg.get("smart_gateway_timeout", 15)
        tools_allowed = cfg.get("smart_gateway_tools_allowed", [])
        # 如果通过环境变量写成逗号分隔的字符串，转成列表
        if isinstance(tools_allowed, str):
            tools_allowed = [t.strip() for t in tools_allowed.split(",") if t.strip()]
        rag_config = GatewayRagConfig(
            top_k=cfg.get("smart_gateway_rag_top_k", 3),
            threshold=cfg.get("smart_gateway_rag_threshold", 0.3),
        )
        self.client = GatewayClient(
            base_url=base_url,
            timeout=timeout,
            default_tools=tools_allowed,
            default_rag=rag_config,
        )
        self.default_tools = tools_allowed
        self.default_rag = rag_config
        self.h5_url = os.environ.get("RAG_H5_URL") or "http://127.0.0.1:3000/static/user.html"

    def _maybe_handle_rag_command(self, content: Any, session_id: str) -> Optional[Reply]:
        """
        允许用户用简单指令调整 RAG 行为：
        - rag 本地     -> 仅用本地检索
        - rag 外部     -> 走外部/增强检索
        - rag topk=5   -> 设置 top_k
        - rag 阈值=0.2  -> 设置 threshold
        - rag reset    -> 清空偏好
        """
        if not isinstance(content, str):
            return None
        text = content.strip()
        lowered = text.lower()
        # 去掉可能的聊天前缀（如 bot、@bot）
        for p in conf().get("single_chat_prefix", []):
            if p:
                lp = p.lower()
                if lowered.startswith(lp):
                    text = text[len(p):].strip()
                    lowered = text.lower()
                    break
        if not (lowered.startswith("rag") or lowered.startswith("#rag")):
            return None

        # 解析命令
        prefs = conf().get_user_data(session_id).get("gateway_rag_pref", {})
        tokens = text.replace("#", "").split()
        if len(tokens) == 1 and tokens[0].lower() in {"rag", "rag帮助", "rag help"}:
            msg = (
                "RAG 设置指令：\n"
                "- rag 本地 : 强制本地检索\n"
                "- rag 外部 : 走外部/增强检索\n"
                "- rag topk=5 : 设置返回条数\n"
                "- rag 阈值=0.3 : 设置阈值\n"
                "- rag reset : 清空偏好"
            )
            if self.h5_url:
                msg += f"\nH5 指引: {self.h5_url}"
            return Reply(ReplyType.TEXT, msg)

        for tok in tokens[1:]:
            lt = tok.lower()
            if lt in {"本地", "local"}:
                prefs["use_enhanced_retrieval"] = False
            elif lt in {"外部", "external", "增强"}:
                prefs["use_enhanced_retrieval"] = True
            elif lt.startswith("topk="):
                try:
                    prefs["top_k"] = max(1, min(20, int(lt.split("=", 1)[1])))
                except Exception:
                    pass
            elif lt.startswith("阈值=") or lt.startswith("threshold="):
                try:
                    val = float(lt.split("=", 1)[1])
                    prefs["threshold"] = max(0.0, min(1.0, val))
                except Exception:
                    pass
            elif lt == "reset":
                prefs = {}
        conf().get_user_data(session_id)["gateway_rag_pref"] = prefs

        human = []
        if not prefs:
            human.append("已清空偏好，恢复默认")
        else:
            if "use_enhanced_retrieval" in prefs:
                human.append("模式: 外部" if prefs["use_enhanced_retrieval"] else "模式: 本地")
            if "top_k" in prefs:
                human.append(f"top_k={prefs['top_k']}")
            if "threshold" in prefs:
                human.append(f"阈值={prefs['threshold']}")
        return Reply(ReplyType.TEXT, "；".join(human) or "已更新设置")

    def _build_unified(self, context: Context) -> UnifiedMessage:
        cmsg = context.get("msg")
        if cmsg is None:
            raise ValueError("context missing msg for gateway")
        unified = getattr(cmsg, "unified_message", None)
        if unified is not None:
            return unified
        # Fallback minimal mapping
        return UnifiedMessage.from_chat_message(cmsg, channel=getattr(cmsg, "channel", "unknown"))

    def _build_request(self, context: Context, unified: UnifiedMessage) -> GatewayRequest:
        session_id = context.get("session_id") or getattr(context.get("msg"), "other_user_id", None) or unified.sender
        # Pydantic expects string ids; ensure message_id/trace_id are strings even if upstream gives int.
        if unified.message_id is not None:
            unified.message_id = str(unified.message_id)
        trace_id_val = getattr(context.get("msg"), "msg_id", None)
        trace_id = str(trace_id_val) if trace_id_val is not None else None
        user_prefs = conf().get_user_data(session_id).get("gateway_rag_pref", {})
        metadata: Dict[str, Any] = {
            "channel": unified.channel,
            "context_type": str(getattr(context.get("msg"), "ctype", "")),
        }
        if "use_enhanced_retrieval" in user_prefs:
            metadata["use_enhanced_retrieval"] = bool(user_prefs["use_enhanced_retrieval"])

        rag_config = GatewayRagConfig(
            top_k=user_prefs.get("top_k", self.default_rag.top_k),
            threshold=user_prefs.get("threshold", self.default_rag.threshold),
        )
        return GatewayRequest(
            session_id=session_id,
            message=unified,
            tools_allowed=self.default_tools,
            rag=rag_config,
            trace_id=trace_id,
            metadata=metadata,
        )

    def reply(self, query: Any, context: Context = None) -> Reply:
        try:
            unified = self._build_unified(context)
            # 用户指令优先处理
            cmd_reply = self._maybe_handle_rag_command(unified.content, unified.sender)
            if cmd_reply:
                return cmd_reply

            req = self._build_request(context, unified)
            resp = self.client.chat(req)
            content = resp.reply_text or ""
            if resp.fallback_reason:
                content = f"{content}\n(回退: {resp.fallback_reason})" if content else f"(回退: {resp.fallback_reason})"
            user_data = conf().get_user_data(unified.sender)
            # 仅首次提示 RAG 指令
            if not user_data.get("rag_hint_shown"):
                h5_part = f"，或打开 {self.h5_url}" if self.h5_url else ""
                hint = (
                    "提示：发送 rag 可查看/设置检索模式，如 “rag 本地”、“rag 外部”、“rag topk=5”、“rag 阈值=0.3”、“rag reset”"
                    f"{h5_part}。"
                )
                content = f"{hint}\n{content}" if content else hint
                user_data["rag_hint_shown"] = True

            return Reply(ReplyType.TEXT, content)
        except Exception as e:
            logger.error(f"[gateway] failed to fetch reply: {e}")
            return Reply(ReplyType.ERROR, f"[gateway] 请求失败: {e}")


def _run_forever():
    """Lightweight runner to keep the smart gateway bot process alive."""
    bot = SmartGatewayBot()
    logger.info("[gateway] SmartGatewayBot started with base_url=%s", bot.client.base_url)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("[gateway] SmartGatewayBot stopped")


if __name__ == "__main__":
    _run_forever()
