"""
Enhanced Tools Router - 增强的工具路由器
整合业务工具和原有工具系统
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from .business_tools import get_business_tools, BusinessTools
from .tools import ToolCallResult, rule_based_intent


class EnhancedToolsRouter:
    """增强的工具路由器"""

    def __init__(self):
        self.business_tools = get_business_tools()

    async def route_and_execute(
        self,
        user_input: str,
        tools_allowed: List[str],
        routing_mode: str = "rule_based",
        user_id: Optional[str] = None
    ) -> List[ToolCallResult]:
        """
        路由并执行工具

        Args:
            user_input: 用户输入
            tools_allowed: 允许的工具列表
            routing_mode: 路由模式
            user_id: 用户ID（用于个性化推荐）

        Returns:
            工具执行结果列表
        """
        start_time = time.perf_counter()

        # 检查业务工具
        business_result = await self._try_business_tools(
            user_input, tools_allowed, routing_mode, user_id
        )

        if business_result:
            business_result[0].latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )
            return business_result

        # 回退到原有工具
        return await self._fallback_to_legacy_tools(
            user_input, tools_allowed, routing_mode, start_time
        )

    async def _try_business_tools(
        self,
        user_input: str,
        tools_allowed: List[str],
        routing_mode: str,
        user_id: Optional[str]
    ) -> Optional[List[ToolCallResult]]:
        """尝试使用业务工具"""
        # 获取工具意图
        selected_tool = self._get_tool_intent(user_input, routing_mode)

        if not selected_tool or selected_tool not in tools_allowed:
            return None

        # 检查是否有对应的业务工具方法
        if not hasattr(self.business_tools, selected_tool):
            return None

        try:
            # 执行业务工具
            method = getattr(self.business_tools, selected_tool)
            result = await method(user_input)

            # 添加元数据
            result.payload["tool_type"] = "business"
            result.payload["routing_mode"] = routing_mode
            result.payload["user_id"] = user_id

            return [result]

        except Exception as e:
            return [ToolCallResult(
                name=selected_tool,
                status="error",
                payload={
                    "error": str(e),
                    "tool_type": "business",
                    "routing_mode": routing_mode
                },
                latency_ms=0,
                error=str(e)
            )]

    async def _fallback_to_legacy_tools(
        self,
        user_input: str,
        tools_allowed: List[str],
        routing_mode: str,
        start_time: float
    ) -> List[ToolCallResult]:
        """回退到原有工具系统"""
        from .tools import run_tool

        selected_tool = rule_based_intent(user_input)
        if selected_tool is None or selected_tool not in tools_allowed:
            return []

        try:
            result = run_tool(selected_tool, user_input)
            result.payload["tool_type"] = "legacy"
            result.payload["routing_mode"] = routing_mode
            result.latency_ms = int((time.perf_counter() - start_time) * 1000)
            return [result]
        except Exception as e:
            return [ToolCallResult(
                name=selected_tool,
                status="error",
                payload={
                    "error": str(e),
                    "tool_type": "legacy",
                    "routing_mode": routing_mode
                },
                latency_ms=int((time.perf_counter() - start_time) * 1000),
                error=str(e)
            )]

    def _get_tool_intent(self, user_input: str, routing_mode: str) -> Optional[str]:
        """增强的意图识别"""
        # 基础规则匹配
        intent = rule_based_intent(user_input)
        if intent:
            return intent

        # 增强的意图识别（考虑更多关键词）
        text_lower = user_input.lower()

        # 订单相关关键词
        order_keywords = [
            "订单", "ord", "购买", "付款", "交易", "账单",
            "购买记录", "消费记录", "我的订单", "查订单"
        ]
        if any(kw in text_lower for kw in order_keywords):
            return "lookup_order"

        # 物流相关关键词
        logistics_keywords = [
            "物流", "快递", "运送", "配送", "delivery", "tracking",
            "包裹", "收到", "发货", "还没到", "运单", "快递单",
            "顺丰", "京东", "圆通", "中通", "韵达", "ems"
        ]
        if any(kw in text_lower for kw in logistics_keywords):
            return "check_logistics"

        # 产品相关关键词
        product_keywords = [
            "产品", "商品", "item", "sku", "型号", "价格", "多少钱",
            "库存", "有货吗", "推荐", "建议", "买什么", "选哪个"
        ]
        if any(kw in text_lower for kw in product_keywords):
            return "product_info"

        # 库存检查关键词
        inventory_keywords = [
            "库存", "现货", "有货", "没货", "补货", "进货",
            "库存量", "剩余", "stock", "inventory"
        ]
        if any(kw in text_lower for kw in inventory_keywords):
            return "check_inventory"

        # 推荐关键词
        recommend_keywords = [
            "推荐", "建议", "哪个好", "选择哪个", "买哪个",
            "有什么好", "新品", "热销", "best seller"
        ]
        if any(kw in text_lower for kw in recommend_keywords):
            return "get_product_recommendations"

        return None

    async def health_check(self) -> Dict[str, Any]:
        """工具系统健康检查"""
        return {
            "business_tools_initialized": self.business_tools is not None,
            "available_tools": [
                "lookup_order",      # 订单查询
                "check_logistics",   # 物流跟踪
                "product_info",       # 产品信息
                "check_inventory",    # 库存检查
                "get_product_recommendations"  # 产品推荐
            ],
            "status": "healthy"
        }

    async def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具元数据"""
        metadata_map = {
            "lookup_order": {
                "name": "订单查询",
                "description": "查询用户的订单信息，包括状态、物流等",
                "parameters": {
                    "order_id": "订单号",
                    "phone": "手机号后4位",
                    "keywords": "订单相关关键词"
                },
                "examples": [
                    "查询订单 ORD-202401001",
                    "我的订单",
                    "最近买的订单"
                ]
            },
            "check_logistics": {
                "name": "物流跟踪",
                "description": "查询包裹的物流信息和配送状态",
                "parameters": {
                    "tracking_number": "运单号",
                    "order_id": "订单号（自动关联）"
                },
                "examples": [
                    "查询物流 SF1234567890",
                    "我的快递到哪了",
                    "包裹还没收到"
                ]
            },
            "product_info": {
                "name": "产品信息",
                "description": "查询产品的详细信息、规格、价格等",
                "parameters": {
                    "sku": "产品SKU码",
                    "name": "产品名称",
                    "category": "产品分类"
                },
                "examples": [
                    "查询产品 SKU-001",
                    "智能手表多少钱",
                    "蓝牙耳机怎么样"
                ]
            },
            "check_inventory": {
                "name": "库存检查",
                "description": "批量检查多个产品的库存状态",
                "parameters": {
                    "sku_list": "SKU列表"
                },
                "examples": [
                    "检查库存 SKU-001,SKU-002,SKU-003",
                    "智能手表还有货吗",
                    "充电宝库存怎么样"
                ]
            },
            "get_product_recommendations": {
                "name": "产品推荐",
                "description": "根据用户偏好和历史推荐产品",
                "parameters": {
                    "user_id": "用户ID",
                    "category": "产品分类（可选）"
                },
                "examples": [
                    "推荐一些智能手表",
                    "有什么新产品推荐",
                    "帮我选个耳机"
                ]
            }
        }

        return metadata_map.get(tool_name)


# 全局实例
_enhanced_router: Optional[EnhancedToolsRouter] = None


def get_enhanced_tools_router() -> EnhancedToolsRouter:
    """获取增强工具路由器实例"""
    global _enhanced_router
    if _enhanced_router is None:
        _enhanced_router = EnhancedToolsRouter()
    return _enhanced_router


async def cleanup_enhanced_tools():
    """清理资源"""
    global _enhanced_router
    if _enhanced_router:
        # 这里可以添加清理逻辑
        _enhanced_router = None