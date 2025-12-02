"""
Business Tools Demo - 业务工具使用示例
展示如何使用集成的业务工具系统
"""

import asyncio
import json
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from gateway.enhanced_tools import get_enhanced_tools_router
    from gateway.business_tools import get_business_tools
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在正确的目录运行脚本")
    sys.exit(1)


async def demo_order_lookup():
    """演示订单查询"""
    print("\n=== 订单查询演示 ===")

    router = get_enhanced_tools_router()

    # 测试用例
    test_cases = [
        "查询订单 ORD-202401001",
        "我的订单",
        "最近买的智能手表",
        "138****5678"  # 模拟手机号查询
    ]

    tools_allowed = ["lookup_order", "check_logistics", "product_info"]

    for query in test_cases:
        print(f"\n📝 用户输入: {query}")
        results = await router.route_and_execute(
            user_input=query,
            tools_allowed=tools_allowed,
            routing_mode="rule_based",
            user_id="demo-user-001"
        )

        if results:
            result = results[0]
            print(f"🔧 调用工具: {result.name}")
            print(f"✅ 执行状态: {result.status}")

            if result.status == "success":
                print("📋 查询结果:")
                print(json.dumps(result.payload, ensure_ascii=False, indent=2))
            elif result.error:
                print(f"❌ 错误信息: {result.error}")
        print("-" * 50)


async def demo_logistics_check():
    """演示物流跟踪"""
    print("\n=== 物流跟踪演示 ===")

    router = get_enhanced_tools_router()

    test_cases = [
        "查询物流 SF1234567890",
        "我的快递到哪了",
        "包裹还没收到",
        "ORD-202401001的物流"  # 通过订单号查询
    ]

    tools_allowed = ["check_logistics", "lookup_order"]

    for query in test_cases:
        print(f"\n📝 用户输入: {query}")
        results = await router.route_and_execute(
            user_input=query,
            tools_allowed=tools_allowed,
            routing_mode="rule_based",
            user_id="demo-user-001"
        )

        if results:
            result = results[0]
            print(f"🔧 调用工具: {result.name}")
            print(f"✅ 执行状态: {result.status}")

            if result.status == "success":
                print("📦 物流信息:")
                payload = result.payload
                print(f"  快递公司: {payload.get('carrier', 'N/A')}")
                print(f"  当前状态: {payload.get('status', 'N/A')}")
                print(f"  当前位置: {payload.get('current_location', 'N/A')}")

                if 'updates' in payload:
                    print("  最新动态:")
                    for update in payload['updates'][-2:]:  # 显示最近2条
                        print(f"    - {update['time']}: {update['status']} ({update.get('location', 'N/A')})")

                if 'estimated_delivery' in payload:
                    print(f"  预计送达: {payload['estimated_delivery']}")
            elif result.error:
                print(f"❌ 错误信息: {result.error}")
        print("-" * 50)


async def demo_product_info():
    """演示产品信息查询"""
    print("\n=== 产品信息查询演示 ===")

    router = get_enhanced_tools_router()

    test_cases = [
        "查询产品 SKU-001",
        "智能手表多少钱",
        "蓝牙耳机怎么样",
        "有什么智能穿戴设备"
    ]

    tools_allowed = ["product_info", "check_inventory", "get_product_recommendations"]

    for query in test_cases:
        print(f"\n📝 用户输入: {query}")
        results = await router.route_and_execute(
            user_input=query,
            tools_allowed=tools_allowed,
            routing_mode="rule_based",
            user_id="demo-user-001"
        )

        if results:
            result = results[0]
            print(f"🔧 调用工具: {result.name}")
            print(f"✅ 执行状态: {result.status}")

            if result.status == "success":
                print("🛍️ 产品信息:")
                payload = result.payload

                if 'query_type' in payload:
                    query_type = payload['query_type']

                    if query_type == "search":
                        print(f"  查询类型: 产品搜索")
                        print(f"  找到产品: {payload['total_found']}个")

                        if 'products' in payload:
                            for i, product in enumerate(payload['products'][:2], 1):
                                print(f"\n  产品 {i}:")
                                print(f"    SKU: {product.get('sku')}")
                                print(f"    名称: {product.get('name')}")
                                print(f"    价格: ¥{product.get('price', 0):.2f}")
                                print(f"    库存: {product.get('stock', 0)}件")
                                print(f"    评分: {product.get('reviews', {}).get('average_rating', 0)}⭐")
                    elif query_type == "recent_orders":
                        print(f"  查询类型: 最近订单产品推荐")

            elif result.error:
                print(f"❌ 错误信息: {result.error}")
        print("-" * 50)


async def demo_inventory_check():
    """演示库存检查"""
    print("\n=== 库存检查演示 ===")

    tools = get_business_tools()

    sku_list = ["SKU-001", "SKU-002", "SKU-003", "SKU-999"]

    print(f"\n📦 检查库存: {', '.join(sku_list)}")

    result = await tools.check_inventory(sku_list)

    if result.status == "success":
        print("✅ 库存信息:")
        payload = result.payload
        inventory = payload.get('inventory', {})

        for sku, info in inventory.items():
            status = info.get('status', 'unknown')
            stock = info.get('stock', 0)

            print(f"\n  {sku}:")
            print(f"    名称: {info.get('name', 'N/A')}")
            print(f"    状态: {status}")
            print(f"    库存: {stock}件")

            if status == "low_stock":
                print(f"    ⚠️  库存不足，建议订货: {info.get('suggested_order', 0)}件")
            elif status == "not_found":
                print(f"    ❌ 产品不存在")

        # 打印汇总
        summary = payload.get('summary', {})
        print(f"\n📊 库存汇总:")
        print(f"  总检查: {summary.get('total_items', 0)}个产品")
        print(f"  有库存: {summary.get('in_stock', 0)}个")
        print(f"  无库存: {summary.get('out_of_stock', 0)}个")
        print(f"  低库存警告: {summary.get('low_stock_alerts', 0)}个")
    else:
        print(f"❌ 库存检查失败: {result.error}")


async def demo_product_recommendations():
    """演示产品推荐"""
    print("\n=== 产品推荐演示 ===")

    router = get_enhanced_tools_router()

    test_cases = [
        ("推荐一些智能手表", "智能穿戴"),
        ("推荐蓝牙耳机", "音频设备"),
        ("推荐充电宝", None)  # 不指定分类
    ]

    for query, category in test_cases:
        print(f"\n📝 用户输入: {query}")
        print(f"🏷️  产品分类: {category or '全部'}")

        results = await router.route_and_execute(
            user_input=query,
            tools_allowed=["get_product_recommendations"],
            routing_mode="rule_based",
            user_id="demo-user-002"
        )

        if results:
            result = results[0]
            print(f"🔧 调用工具: {result.name}")
            print(f"✅ 执行状态: {result.status}")

            if result.status == "success":
                print("🎯 推荐结果:")
                payload = result.payload

                if 'recommendations' in payload:
                    for i, rec in enumerate(payload['recommendations'], 1):
                        product = rec.get('product', {})
                        print(f"\n  推荐 {i}: {product.get('name')}")
                        print(f"    SKU: {product.get('sku')}")
                        print(f"    价格: ¥{product.get('price', 0):.2f}")
                        print(f"    推荐理由: {rec.get('recommendation_reason', 'N/A')}")
                        print(f"    匹配度: {rec.get('match_score', 0)}%")

                print(f"\n📊 推荐统计:")
                print(f"  总产品数: {payload.get('total_products', 0)}")
                print(f"  推荐数: {len(payload.get('recommendations', []))}")
            elif result.error:
                print(f"❌ 错误信息: {result.error}")
        print("-" * 50)


async def demo_tool_metadata():
    """演示工具元数据查询"""
    print("\n=== 工具元数据查询演示 ===")

    router = get_enhanced_tools_router()

    tools = ["lookup_order", "check_logistics", "product_info", "check_inventory", "get_product_recommendations"]

    for tool_name in tools:
        print(f"\n🔧 工具: {tool_name}")
        metadata = await router.get_tool_metadata(tool_name)

        if metadata:
            print(f"  名称: {metadata.get('name')}")
            print(f"  描述: {metadata.get('description')}")
            print(f"  参数: {list(metadata.get('parameters', {}).keys())}")
            print(f"  示例:")
            for example in metadata.get('examples', [])[:2]:
                print(f"    - {example}")
        else:
            print("  ⚠️  元数据未找到")


async def main():
    """主演示函数"""
    print("🚀 业务工具系统演示")
    print("=" * 60)

    # 健康检查
    router = get_enhanced_tools_router()
    health = await router.health_check()
    print(f"\n🏥 系统健康状态: {json.dumps(health, ensure_ascii=False, indent=2)}")

    # 运行各种演示
    await demo_order_lookup()
    await demo_logistics_check()
    await demo_product_info()
    await demo_inventory_check()
    await demo_product_recommendations()
    await demo_tool_metadata()

    print("\n✨ 演示完成！")
    print("\n💡 提示:")
    print("1. 订单查询支持订单号、手机号、关键词等多种方式")
    print("2. 物流查询支持运单号查询，也可通过订单号自动关联")
    print("3. 产品查询支持SKU、名称、分类等多种查询方式")
    print("4. 库存检查支持批量查询，会给出低库存警告")
    print("5. 产品推荐基于评分、库存和用户偏好智能推荐")
    print("6. 所有工具都包含详细的帮助信息和错误处理")


if __name__ == "__main__":
    asyncio.run(main())