# 业务工具系统使用指南

## 📋 概述

业务工具系统为 ChatGPT-on-WeChat 提供了实际的业务处理能力，包括：
- **订单管理** - 查询订单状态、历史、退款政策
- **物流跟踪** - 实时跟踪包裹位置、配送状态
- **产品信息** - 查询产品详情、规格、价格、库存
- **库存管理** - 批量检查库存，低库存预警
- **智能推荐** - 基于用户偏好和评分推荐产品

## 🚀 快速开始

### 1. 启用业务工具

在请求时设置 `use_enhanced_tools: true`：

```json
{
  "session_id": "user-session-001",
  "message": {
    "sender": "user",
    "receiver": "bot",
    "channel": "wechat",
    "message_type": "text",
    "content": "查询我的订单"
  },
  "tools_allowed": ["lookup_order", "check_logistics", "product_info"],
  "metadata": {
    "use_enhanced_tools": true,
    "routing_mode": "rule_based"
  }
}
```

### 2. 运行演示

```bash
cd chatgpt-on-wechat
python examples/business_tools_demo.py
```

## 🛠️ 工具列表

### 1. lookup_order - 订单查询

**功能**：查询用户的订单信息

**支持的查询方式**：
- 完整订单号：`ORD-202401001`
- 手机号后4位：`138****5678`
- 关键词：`我的订单`、`最近订单`、`购买记录`

**返回信息**：
```json
{
  "order_id": "ORD-202401001",
  "status": "shipped",
  "items": [
    {"sku": "SKU-001", "name": "智能手表", "quantity": 1, "price": 1299.00}
  ],
  "total_amount": 1497.00,
  "tracking_number": "SF1234567890",
  "estimated_delivery": "2024-01-18",
  "helpful_info": {
    "can_cancel": false,
    "can_track": true,
    "refund_days_left": 5
  }
}
```

### 2. check_logistics - 物流跟踪

**功能**：查询包裹的物流信息

**支持的查询方式**：
- 运单号：`SF1234567890`
- 订单号：会自动关联到运单号
- 关键词：`物流`、`快递`、`包裹`、`还没到`

**返回信息**：
```json
{
  "tracking_number": "SF1234567890",
  "carrier": "顺丰速运",
  "status": "运输中",
  "current_location": "上海转运中心",
  "updates": [
    {"time": "2024-01-16 14:20:00", "status": "已揽收", "location": "上海浦东营业部"},
    {"time": "2024-01-18 15:30:00", "status": "已签收", "location": "本人"}
  ],
  "estimated_delivery": "2024-01-18 18:00:00"
}
```

### 3. product_info - 产品信息查询

**功能**：查询产品的详细信息

**支持的查询方式**：
- SKU码：`SKU-001`
- 产品名称：`智能手表`
- 产品分类：`智能穿戴`

**返回信息**：
```json
{
  "sku": "SKU-001",
  "name": "智能手表 Pro Max",
  "category": "智能穿戴",
  "price": 1299.00,
  "stock": 50,
  "description": "旗舰级智能手表，支持心率监测、GPS定位、50米防水",
  "features": ["1.43英寸AMOLED屏幕", "心率血氧监测"],
  "specifications": {
    "屏幕": "1.43英寸 AMOLED",
    "电池": "450mAh",
    "防水": "5ATM"
  },
  "reviews": {
    "average_rating": 4.6,
    "total_reviews": 1280
  }
}
```

### 4. check_inventory - 库存检查

**功能**：批量检查多个产品的库存状态

**使用方式**：
```json
{
  "content": "检查库存 SKU-001,SKU-002,SKU-003",
  "tools_allowed": ["check_inventory"]
}
```

**返回信息**：
```json
{
  "inventory": {
    "SKU-001": {
      "sku": "SKU-001",
      "stock": 50,
      "status": "in_stock"
    },
    "SKU-002": {
      "sku": "SKU-002",
      "stock": 200,
      "status": "in_stock"
    }
  },
  "low_stock_alerts": [],
  "summary": {
    "total_items": 3,
    "in_stock": 2,
    "out_of_stock": 1
  }
}
```

### 5. get_product_recommendations - 产品推荐

**功能**：基于用户偏好和产品评分推荐产品

**使用方式**：
```json
{
  "content": "推荐一些智能手表",
  "tools_allowed": ["get_product_recommendations"]
}
```

**返回信息**：
```json
{
  "user_id": "user-001",
  "recommendations": [
    {
      "name": "智能手表 Pro Max",
      "sku": "SKU-001",
      "recommendation_reason": "热销产品",
      "match_score": 100
    }
  ],
  "total_products": 5
}
```

## 🔧 配置选项

### 环境变量

在 `.env` 文件中添加：

```bash
# 启用增强工具系统
USE_ENHANCED_TOOLS=true

# 配置允许的工具（逗号分隔）
ALLOWED_TOOLS=lookup_order,check_logistics,product_info

# 工具超时设置（毫秒）
TOOL_TIMEOUT_MS=5000

# 启用工具缓存
TOOL_CACHE_ENABLED=true
TOOL_CACHE_TTL=300
```

### 请求参数

在请求中控制工具行为：

```json
{
  "metadata": {
    "use_enhanced_tools": true,    // 启用业务工具
    "routing_mode": "rule_based",    // 路由模式
    "user_id": "user-123",        // 用户ID（用于个性化）
    "tool_timeout": 3000,          // 单个工具超时
    "enable_cache": true            // 启用缓存
  }
}
```

## 📝 开发自定义工具

### 1. 创建工具类

在 `gateway/business_tools.py` 中添加新工具：

```python
async def custom_tool(self, query: str) -> ToolCallResult:
    """
    自定义工具描述
    """
    start_time = time.time()

    try:
        # 实现工具逻辑
        result = your_custom_logic(query)

        return ToolCallResult(
            name="custom_tool",
            status="success",
            payload=result,
            latency_ms=int((time.time() - start_time) * 1000)
        )
    except Exception as e:
        return ToolCallResult(
            name="custom_tool",
            status="error",
            error=str(e),
            latency_ms=int((time.time() - start_time) * 1000)
        )
```

### 2. 更新路由器

在 `gateway/enhanced_tools.py` 的 `_get_tool_intent` 方法中添加关键词：

```python
def _get_tool_intent(self, user_input: str, routing_mode: str) -> Optional[str]:
    # 添加自定义工具的关键词
    custom_keywords = ["自定义", "特殊", "custom"]
    if any(kw in text_lower for kw in custom_keywords):
        return "custom_tool"

    # 现有逻辑...
```

### 3. 注册工具

在 `BusinessTools` 类中添加新方法：

```python
class BusinessTools:
    # ... 现有方法 ...

    async def custom_tool(self, query: str) -> ToolCallResult:
        """自定义工具实现"""
        return await custom_tool(self, query)
```

## 🔍 调试和监控

### 日志记录

系统会自动记录所有工具调用，包括：
- 工具名称
- 执行时间
- 成功/失败状态
- 错误信息
- 用户ID
- 会话ID

### 性能监控

查看工具性能：

```python
# 获取健康状态
router = get_enhanced_tools_router()
health = await router.health_check()
print(json.dumps(health, indent=2))
```

### 缓存管理

缓存会根据以下键存储：
```python
# 订单查询缓存
cache_key = f"order_{order_id}"

# 物流查询缓存
cache_key = f"logistics_{tracking_number}"

# 产品信息缓存
cache_key = f"product_{sku_or_name}"
```

## 📊 最佳实践

### 1. 工具使用提示

- **清晰的意图识别**：使用准确的关键词匹配
- **参数验证**：验证输入参数的有效性
- **错误处理**：提供有用的错误信息和建议
- **性能优化**：使用缓存减少数据库查询

### 2. 用户体验

- **提供示例**：在响应中包含查询示例
- **渐进式披露**：先返回摘要，再提供详细信息
- **操作建议**：提供下一步可执行的操作
- **多语言支持**：支持中英文混合查询

### 3. 数据管理

- **模拟数据**：开发环境使用模拟数据
- **真实数据**：生产环境连接真实数据库
- **数据同步**：定期同步库存和订单状态
- **备份策略**：实现数据备份和恢复

## 🛠️ 故障排除

### 常见问题

1. **工具不执行**
   - 检查 `use_enhanced_tools` 是否设置为 `true`
   - 确认工具名称在 `tools_allowed` 列表中

2. **缓存问题**
   - 检查 `TOOL_CACHE_ENABLED` 设置
   - 清理缓存：重启应用或等待TTL过期

3. **性能问题**
   - 检查 `TOOL_TIMEOUT_MS` 设置
   - 查看日志中的执行时间

4. **权限错误**
   - 确认用户有访问特定工具的权限
   - 检查用户ID是否正确传递

### 调试模式

启用调试日志：

```bash
export LOG_LEVEL=DEBUG
export BUSINESS_TOOLS_DEBUG=true
```

## 📚 扩展阅读

- [RAG Integration Guide](./RAG_INTEGRATION.md) - RAG系统集成
- [API Documentation](./API.md) - 完整API参考
- [Deployment Guide](./DEPLOYMENT.md) - 部署指南
- [Troubleshooting](./TROUBLESHOOTING.md) - 故障排除