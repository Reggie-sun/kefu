"""
Business Tools Implementation - 具体业务工具实现
包含订单查询、物流跟踪、产品信息等实际业务场景
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from .tools import ToolCallResult


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"          # 待处理
    CONFIRMED = "confirmed"        # 已确认
    PROCESSING = "processing"      # 处理中
    SHIPPED = "shipped"          # 已发货
    DELIVERED = "delivered"       # 已送达
    CANCELLED = "cancelled"       # 已取消
    REFUNDED = "refunded"        # 已退款
    RETURNED = "returned"          # 已退货


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DatabaseConfig:
    """数据库配置（模拟）"""
    # 在实际应用中，这些应该是真实的数据库连接
    orders_db: Optional[Any] = None
    logistics_db: Optional[Any] = None
    products_db: Optional[Any] = None
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5分钟


class BusinessTools:
    """业务工具管理器"""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._cache: Dict[str, tuple] = {}  # (timestamp, data)
        self._init_mock_data()

    def _init_mock_data(self):
        """初始化模拟数据"""
        # 模拟订单数据
        self._mock_orders = {
            "ORD-202401001": {
                "order_id": "ORD-202401001",
                "user_id": "user-001",
                "items": [
                    {"sku": "SKU-001", "name": "智能手表", "quantity": 1, "price": 1299.00},
                    {"sku": "SKU-002", "name": "保护壳", "quantity": 2, "price": 99.00}
                ],
                "total_amount": 1497.00,
                "status": OrderStatus.SHIPPED,
                "created_at": "2024-01-15 10:30:00",
                "shipped_at": "2024-01-16 14:20:00",
                "tracking_number": "SF1234567890",
                "estimated_delivery": "2024-01-18",
                "shipping_address": "上海市浦东新区张江高科技园区",
                "contact_phone": "138****5678"
            },
            "ORD-202401002": {
                "order_id": "ORD-202401002",
                "user_id": "user-002",
                "items": [
                    {"sku": "SKU-003", "name": "蓝牙耳机", "quantity": 1, "price": 399.00}
                ],
                "total_amount": 399.00,
                "status": OrderStatus.DELIVERED,
                "created_at": "2024-01-10 09:15:00",
                "delivered_at": "2024-01-12 16:30:00",
                "tracking_number": "JD9876543210",
                "shipping_address": "北京市朝阳区建国路88号",
                "contact_phone": "139****1234"
            },
            "ORD-202401003": {
                "order_id": "ORD-202401003",
                "user_id": "user-003",
                "items": [
                    {"sku": "SKU-004", "name": "充电宝", "quantity": 1, "price": 199.00}
                ],
                "total_amount": 199.00,
                "status": OrderStatus.CANCELLED,
                "created_at": "2024-01-08 15:45:00",
                "cancelled_at": "2024-01-09 11:20:00",
                "cancel_reason": "用户主动取消"
            }
        }

        # 模拟物流数据
        self._mock_logistics = {
            "SF1234567890": {
                "tracking_number": "SF1234567890",
                "carrier": "顺丰速运",
                "status": "运输中",
                "current_location": "上海转运中心",
                "updates": [
                    {"time": "2024-01-16 14:20:00", "status": "已揽收", "location": "上海浦东营业部"},
                    {"time": "2024-01-16 18:30:00", "status": "已发出", "location": "上海转运中心"},
                    {"time": "2024-01-17 06:00:00", "status": "运输中", "location": "上海转运中心"},
                    {"time": "2024-01-17 14:00:00", "status": "到达", "location": "北京转运中心"},
                    {"time": "2024-01-18 08:00:00", "status": "派送中", "location": "北京朝阳营业部"},
                    {"time": "2024-01-18 15:30:00", "status": "已签收", "location": "北京朝阳营业部", "recipient": "本人"}
                ],
                "estimated_delivery": "2024-01-18 18:00:00"
            },
            "JD9876543210": {
                "tracking_number": "JD9876543210",
                "carrier": "京东物流",
                "status": "已送达",
                "current_location": "北京朝阳区建国路88号",
                "updates": [
                    {"time": "2024-01-10 10:00:00", "status": "已揽收", "location": "北京仓库"},
                    {"time": "2024-01-11 02:00:00", "status": "分拣中", "location": "北京分拣中心"},
                    {"time": "2024-01-11 08:00:00", "status": "已发货", "location": "北京分拣中心"},
                    {"time": "2024-01-12 09:00:00", "status": "运输中", "location": "北京转运站"},
                    {"time": "2024-01-12 14:00:00", "status": "派送中", "location": "北京朝阳配送站"},
                    {"time": "2024-01-12 16:30:00", "status": "已送达", "location": "北京朝阳区建国路88号", "recipient": "前台代收"}
                ],
                "estimated_delivery": "2024-01-12 18:00:00",
                "actual_delivery": "2024-01-12 16:30:00"
            },
            "YTO7890123456": {
                "tracking_number": "YTO7890123456",
                "carrier": "圆通速递",
                "status": "异常",
                "current_location": "异常处理中心",
                "updates": [
                    {"time": "2024-01-20 10:00:00", "status": "已揽收", "location": "广州营业部"},
                    {"time": "2024-01-21 15:00:00", "status": "异常", "location": "异常处理中心", "reason": "包裹破损"}
                ],
                "exception_info": {
                    "type": "包裹破损",
                    "description": "包裹在运输过程中出现破损，已启动理赔流程",
                    "contact": "客服电话：400-123-4567",
                    "solution": "将重新发货或办理退款"
                }
            }
        }

        # 模拟产品数据
        self._mock_products = {
            "SKU-001": {
                "sku": "SKU-001",
                "name": "智能手表 Pro Max",
                "category": "智能穿戴",
                "brand": "TechBrand",
                "price": 1299.00,
                "stock": 50,
                "description": "旗舰级智能手表，支持心率监测、GPS定位、50米防水",
                "features": [
                    "1.43英寸AMOLED屏幕",
                    "心率血氧监测",
                    "GPS+北斗双模定位",
                    "50米深度防水",
                    "7天续航"
                ],
                "images": [
                    "https://example.com/watch-1.jpg",
                    "https://example.com/watch-2.jpg"
                ],
                "specifications": {
                    "屏幕": "1.43英寸 AMOLED",
                    "电池": "450mAh",
                    "防水": "5ATM",
                    "连接": "蓝牙5.0、WiFi、NFC"
                },
                "reviews": {
                    "average_rating": 4.6,
                    "total_reviews": 1280,
                    "recent_reviews": [
                        {"user": "小明", "rating": 5, "comment": "功能强大，续航不错！"},
                        {"user": "Amy", "rating": 4, "comment": "外观很漂亮，就是价格有点贵"}
                    ]
                }
            },
            "SKU-002": {
                "sku": "SKU-002",
                "name": "智能手表保护壳",
                "category": "配件",
                "brand": "TechBrand",
                "price": 99.00,
                "stock": 200,
                "description": "专为智能手表设计的TPU保护壳，防摔防刮",
                "features": [
                    "进口TPU材质",
                    "精准开孔设计",
                    "防摔防刮",
                    "多种颜色可选"
                ],
                "colors": ["透明黑", "星空蓝", "樱花粉"],
                "compatible_with": ["SKU-001"]
            },
            "SKU-003": {
                "sku": "SKU-003",
                "name": "无线蓝牙耳机 5.0",
                "category": "音频设备",
                "brand": "AudioBrand",
                "price": 399.00,
                "stock": 0,
                "description": "主动降噪蓝牙耳机，Hi-Res音质认证",
                "status": "out_of_stock",
                "restock_date": "2024-02-01",
                "features": [
                    "主动降噪技术",
                    "40dB降噪深度",
                    "30小时续航",
                    "快充15分钟使用3小时"
                ]
            }
        }

    def _get_cache(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if not self.config.cache_enabled:
            return None

        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self.config.cache_ttl:
                return data
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        """设置缓存数据"""
        if not self.config.cache_enabled:
            return
        self._cache[key] = (time.time(), data)

    def _log(self, level: LogLevel, message: str, extra: Optional[Dict] = None) -> None:
        """记录日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "message": message,
            "extra": extra or {}
        }
        print(f"[{log_entry['timestamp']}] {level.value.upper()}: {message}")
        # 在实际应用中，这里应该写入日志系统

    async def lookup_order(self, query: str, user_id: Optional[str] = None) -> ToolCallResult:
        """
        查询订单信息
        支持多种查询方式：
        1. 订单号：ORD-202401001
        2. 手机号：138****5678
        3. 关键词：最近订单
        """
        start_time = time.time()

        try:
            # 标准化查询
            query = query.strip()

            # 尝试订单号查询
            if query.startswith("ORD-"):
                order_id = query
                cache_key = f"order_{order_id}"
                cached = self._get_cache(cache_key)
                if cached:
                    self._log(LogLevel.DEBUG, f"Cache hit for order: {order_id}")
                    return ToolCallResult(
                        name="lookup_order",
                        status="success",
                        payload=cached,
                        latency_ms=int((time.time() - start_time) * 1000)
                    )

                if order_id in self._mock_orders:
                    order_data = self._mock_orders[order_id]
                    self._set_cache(cache_key, order_data)
                    self._log(LogLevel.INFO, f"Order found: {order_id}")

                    # 添加 helpful 信息
                    order_data["helpful_info"] = {
                        "can_cancel": order_data["status"] in [OrderStatus.PENDING, OrderStatus.CONFIRMED],
                        "can_track": order_data["status"] in [OrderStatus.PROCESSING, OrderStatus.SHIPPED],
                        "can_return": order_data["status"] in [OrderStatus.DELIVERED],
                        "refund_days_left": self._calculate_refund_days(order_data.get("delivered_at"))
                    }

                    return ToolCallResult(
                        name="lookup_order",
                        status="success",
                        payload=order_data,
                        latency_ms=int((time.time() - start_time) * 1000)
                    )

            # 尝试手机号查询（模糊匹配）
            if len(query) >= 4 and query.replace("-", "").replace(" ", "").isdigit():
                phone_last4 = query[-4:]
                matching_orders = [
                    order for order in self._mock_orders.values()
                    if phone_last4 in order.get("contact_phone", "")
                ]

                if matching_orders:
                    # 返回最近的订单
                    latest_order = max(matching_orders, key=lambda x: x.get("created_at", ""))
                    self._log(LogLevel.INFO, f"Orders found by phone: {len(matching_orders)}")

                    return ToolCallResult(
                        name="lookup_order",
                        status="success",
                        payload={
                            "query_type": "phone_search",
                            "phone_last4": phone_last4,
                            "matched_orders": len(matching_orders),
                            "latest_order": latest_order
                        },
                        latency_ms=int((time.time() - start_time) * 1000)
                    )

            # 关键词查询
            if any(keyword in query for keyword in ["最近", "latest", "订单", "order"]):
                # 返回最近的3个订单
                recent_orders = sorted(
                    self._mock_orders.values(),
                    key=lambda x: x.get("created_at", ""),
                    reverse=True
                )[:3]

                self._log(LogLevel.INFO, f"Recent orders query: {len(recent_orders)} orders")
                return ToolCallResult(
                    name="lookup_order",
                    status="success",
                    payload={
                        "query_type": "recent_orders",
                        "total_orders": len(self._mock_orders),
                        "recent_orders": recent_orders
                    },
                    latency_ms=int((time.time() - start_time) * 1000)
                )

            # 未找到订单
            return ToolCallResult(
                name="lookup_order",
                status="not_found",
                payload={
                    "message": "未找到相关订单",
                    "suggestions": [
                        "请提供完整的订单号（如：ORD-202401001）",
                        "请提供注册手机号的后4位",
                        "您可以在我的订单页面查看所有订单"
                    ]
                },
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self._log(LogLevel.ERROR, f"Order lookup error: {str(e)}")
            return ToolCallResult(
                name="lookup_order",
                status="error",
                payload={},
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _calculate_refund_days(self, delivered_at: Optional[str]) -> Optional[int]:
        """计算剩余退款天数"""
        if not delivered_at:
            return None

        try:
            delivery_date = datetime.fromisoformat(delivered_at.replace(" ", "T"))
            refund_deadline = delivery_date + timedelta(days=7)
            days_left = (refund_deadline - datetime.now()).days
            return max(0, days_left)
        except:
            return None

    async def check_logistics(self, query: str) -> ToolCallResult:
        """
        查询物流信息
        支持多种查询方式：
        1. 运单号：SF1234567890
        2. 订单号查询：ORD-202401001（会自动关联运单号）
        """
        start_time = time.time()

        try:
            query = query.strip()
            tracking_number = None

            # 直接查询运单号
            if len(query) >= 10 and query.replace(" ", "").isalnum():
                tracking_number = query.upper()

            # 通过订单号查询
            elif query.startswith("ORD-"):
                order = self._mock_orders.get(query)
                if order:
                    tracking_number = order.get("tracking_number")

            if not tracking_number:
                return ToolCallResult(
                    name="check_logistics",
                    status="invalid_query",
                    payload={
                        "message": "请提供有效的运单号或订单号",
                        "examples": [
                            "运单号查询：SF1234567890",
                            "订单号查询：ORD-202401001"
                        ]
                    },
                    latency_ms=int((time.time() - start_time) * 1000)
                )

            # 查询缓存
            cache_key = f"logistics_{tracking_number}"
            cached = self._get_cache(cache_key)
            if cached:
                self._log(LogLevel.DEBUG, f"Cache hit for logistics: {tracking_number}")
                return ToolCallResult(
                    name="check_logistics",
                    status="success",
                    payload=cached,
                    latency_ms=int((time.time() - start_time) * 1000)
                )

            # 查询物流信息
            if tracking_number in self._mock_logistics:
                logistics_data = self._mock_logistics[tracking_number]
                self._set_cache(cache_key, logistics_data)
                self._log(LogLevel.INFO, f"Logistics found: {tracking_number}")

                # 添加 helpful 信息
                logistics_data["helpful_info"] = {
                    "carrier_contact": self._get_carrier_contact(logistics_data.get("carrier")),
                    "can_complaint": logistics_data.get("status") in ["运输中", "已送达", "异常"],
                    "estimated_delivery": logistics_data.get("estimated_delivery"),
                    "has_exception": "exception_info" in logistics_data
                }

                return ToolCallResult(
                    name="check_logistics",
                    status="success",
                    payload=logistics_data,
                    latency_ms=int((time.time() - start_time) * 1000)
                )

            return ToolCallResult(
                name="check_logistics",
                status="not_found",
                payload={
                    "message": "未找到物流信息",
                    "suggestions": [
                        "请确认运单号是否正确",
                        "物流信息可能有24小时延迟",
                        "请联系客服获取帮助"
                    ]
                },
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self._log(LogLevel.ERROR, f"Logistics check error: {str(e)}")
            return ToolCallResult(
                name="check_logistics",
                status="error",
                payload={},
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _get_carrier_contact(self, carrier: Optional[str]) -> Optional[Dict[str, str]]:
        """获取快递公司联系方式"""
        contacts = {
            "顺丰速运": {"phone": "95338", "website": "www.sf-express.com"},
            "京东物流": {"phone": "950616", "website": "www.jdwl.com"},
            "圆通速递": {"phone": "95554", "website": "www.yto.net.cn"},
            "中通快递": {"phone": "95311", "website": "www.zto.com"},
            "韵达快递": {"phone": "95546", "website": "www.yundaex.com"}
        }
        return contacts.get(carrier)

    async def product_info(self, query: str, category: Optional[str] = None) -> ToolCallResult:
        """
        查询产品信息
        支持多种查询方式：
        1. SKU码：SKU-001
        2. 产品名称：智能手表
        3. 分类查询：智能穿戴
        """
        start_time = time.time()

        try:
            query = query.strip()

            # SKU查询
            if query.startswith("SKU-"):
                product = self._mock_products.get(query)
                if product:
                    self._log(LogLevel.INFO, f"Product found by SKU: {query}")
                    return ToolCallResult(
                        name="product_info",
                        status="success",
                        payload=product,
                        latency_ms=int((time.time() - start_time) * 1000)
                    )

            # 产品名称或分类查询
            matching_products = []
            query_lower = query.lower()

            for product in self._mock_products.values():
                # 检查名称匹配
                if query_lower in product.get("name", "").lower():
                    matching_products.append(product)
                    continue

                # 检查分类匹配
                if category and category.lower() == product.get("category", "").lower():
                    matching_products.append(product)
                    continue

                # 关键词匹配
                search_fields = [
                    product.get("name", ""),
                    product.get("description", ""),
                    " ".join(product.get("features", [])),
                    product.get("brand", "")
                ]
                if any(query_lower in field.lower() for field in search_fields):
                    matching_products.append(product)

            if matching_products:
                # 去重并按相关性排序
                unique_products = {p["sku"]: p for p in matching_products}.values()
                # 简单的排序：名称完全匹配 > 分类匹配 > 关键词匹配
                unique_products.sort(key=lambda p: (
                    0 if query_lower in p.get("name", "").lower() else
                    1 if category and category.lower() == p.get("category", "").lower() else
                    2
                ))

                self._log(LogLevel.INFO, f"Products found: {len(unique_products)}")
                return ToolCallResult(
                    name="product_info",
                    status="success",
                    payload={
                        "query": query,
                        "query_type": "search",
                        "total_found": len(unique_products),
                        "products": unique_products[:5]  # 限制返回5个结果
                    },
                    latency_ms=int((time.time() - start_time) * 1000)
                )

            # 未找到产品
            return ToolCallResult(
                name="product_info",
                status="not_found",
                payload={
                    "message": "未找到相关产品",
                    "suggestions": [
                        "请提供准确的SKU码（如：SKU-001）",
                        "请使用产品关键词搜索（如：智能手表）",
                        "可以浏览产品分类页面"
                    ],
                    "hot_products": list(self._mock_products.values())[:3]  # 推荐热门产品
                },
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self._log(LogLevel.ERROR, f"Product info error: {str(e)}")
            return ToolCallResult(
                name="product_info",
                status="error",
                payload={},
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    async def check_inventory(self, sku_list: List[str]) -> ToolCallResult:
        """
        批量检查库存
        """
        start_time = time.time()

        try:
            inventory_info = {}
            low_stock_items = []

            for sku in sku_list:
                product = self._mock_products.get(sku)
                if product:
                    inventory_info[sku] = {
                        "sku": sku,
                        "name": product.get("name"),
                        "stock": product.get("stock", 0),
                        "status": "in_stock" if product.get("stock", 0) > 0 else "out_of_stock",
                        "restock_date": product.get("restock_date")
                    }

                    if product.get("stock", 0) < 10:  # 库存低于10视为低库存
                        low_stock_items.append({
                            "sku": sku,
                            "name": product.get("name"),
                            "current_stock": product.get("stock", 0),
                            "suggested_reorder": 50
                        })
                else:
                    inventory_info[sku] = {
                        "sku": sku,
                        "status": "not_found"
                    }

            self._log(LogLevel.INFO, f"Inventory check: {len(inventory_info)} items")

            return ToolCallResult(
                name="check_inventory",
                status="success",
                payload={
                    "inventory": inventory_info,
                    "low_stock_alerts": low_stock_items,
                    "summary": {
                        "total_items": len(sku_list),
                        "in_stock": sum(1 for item in inventory_info.values() if item["status"] == "in_stock"),
                        "out_of_stock": sum(1 for item in inventory_info.values() if item["status"] == "out_of_stock")
                    }
                },
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self._log(LogLevel.ERROR, f"Inventory check error: {str(e)}")
            return ToolCallResult(
                name="check_inventory",
                status="error",
                payload={},
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    async def get_product_recommendations(self, user_id: str, category: Optional[str] = None) -> ToolCallResult:
        """
        获取产品推荐
        """
        start_time = time.time()

        try:
            # 基于用户历史和热门产品推荐
            all_products = list(self._mock_products.values())

            # 如果指定分类，筛选该分类产品
            if category:
                category_lower = category.lower()
                filtered_products = [
                    p for p in all_products
                    if p.get("category", "").lower() == category_lower
                ]
            else:
                filtered_products = all_products

            # 按评分和库存排序
            filtered_products.sort(key=lambda p: (
                -p.get("reviews", {}).get("average_rating", 0),  # 评分降序
                -p.get("stock", 0)  # 库存降序
            ))

            # 添加推荐原因
            recommendations = []
            for i, product in enumerate(filtered_products[:5]):
                reason = ""
                if i == 0:
                    reason = "热销产品"
                elif product.get("reviews", {}).get("average_rating", 0) >= 4.5:
                    reason = "高评分产品"
                elif product.get("stock", 0) >= 100:
                    reason = "库存充足"

                recommendations.append({
                    **product,
                    "recommendation_reason": reason,
                    "match_score": 100 - i * 20  # 简单的匹配分数
                })

            self._log(LogLevel.INFO, f"Product recommendations: {len(recommendations)} items")

            return ToolCallResult(
                name="product_recommendations",
                status="success",
                payload={
                    "user_id": user_id,
                    "category": category,
                    "recommendations": recommendations,
                    "total_products": len(filtered_products)
                },
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            self._log(LogLevel.ERROR, f"Product recommendation error: {str(e)}")
            return ToolCallResult(
                name="product_recommendations",
                status="error",
                payload={},
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )


# 全局业务工具实例
_business_tools: Optional[BusinessTools] = None


def get_business_tools() -> BusinessTools:
    """获取业务工具实例"""
    global _business_tools
    if _business_tools is None:
        _business_tools = BusinessTools()
    return _business_tools
