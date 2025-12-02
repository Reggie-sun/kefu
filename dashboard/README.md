# AI 工作台 - 前端优化版本

这是一个现代化的三页 Web 应用，基于 ChatGPT on WeChat 系统改造而来。

## 功能特性

### 第一页：介绍页面
- 📊 **系统监控** - 实时显示会话统计、知识库命中率等关键指标
- 📈 **可视化图表** - 工具使用分布、每日会话量趋势
- 📝 **最近会话日志** - 查看最新的对话记录
- 🎨 **现代化 UI** - 深色主题，响应式设计

### 第二页：LoRA 训练
- 📤 **数据集上传** - 支持拖拽上传 JSON、CSV、TXT 格式
- ⚙️ **训练配置** - 灵活设置训练参数（轮数、学习率、批大小等）
- 📊 **实时监控** - 训练进度、损失曲线、剩余时间
- 🗂️ **模型管理** - 查看、使用、删除已训练的 LoRA 模型

### 第三页：图片生成
- ✍️ **文本到图片** - 输入描述生成精美图片
- 🎛️ **高级参数** - 调整尺寸、采样步数、CFG Scale 等
- 🖼️ **模型选择** - 使用基础模型或自定义 LoRA 模型
- 📚 **历史记录** - 查看和复用之前的生成参数

## 快速开始

### 方法一：使用启动脚本（推荐）
```bash
cd dashboard
./run_dashboard.sh
```

### 方法二：手动启动
```bash
cd dashboard
pip install fastapi uvicorn python-multipart
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

然后在浏览器中访问：http://localhost:8000

## 技术架构

### 前端
- **框架**：原生 HTML/CSS/JavaScript (ES6+)
- **样式**：CSS Grid 和 Flexbox 布局
- **图表**：Chart.js
- **设计**：深色主题，现代化 UI

### 后端
- **框架**：FastAPI
- **存储**：内存存储（可扩展为数据库）
- **API**：RESTful API 设计
- **异步处理**：后台任务支持

## API 接口

### 系统监控
- `GET /api/stats` - 获取统计数据
- `GET /api/logs` - 获取会话日志

### LoRA 训练
- `POST /lora/train` - 启动训练任务
- `GET /lora/status/{task_id}` - 获取训练状态
- `GET /lora/models` - 获取模型列表
- `DELETE /lora/models/{model_id}` - 删除模型

### 图片生成
- `POST /image/generate` - 生成图片
- `GET /image/status/{task_id}` - 获取生成状态
- `GET /image/history` - 获取历史记录

## 项目结构
```
dashboard/
├── app.py              # FastAPI 后端
├── index.html           # 主页面（旧版）
├── static/
│   ├── index.html       # 主页面（新版）
│   ├── css/
│   │   └── style.css    # 样式文件
│   └── js/
│       ├── main.js      # 主逻辑
│       ├── intro.js     # 介绍页逻辑
│       ├── lora.js      # LoRA 训练页逻辑
│       └── generate.js  # 图片生成页逻辑
├── run_dashboard.sh     # 启动脚本
└── README.md           # 说明文档
```

## 注意事项

1. **数据存储**：当前版本使用内存存储，重启后会丢失数据。生产环境建议配置数据库。

2. **模拟功能**：LoRA 训练和图片生成为模拟实现，展示了完整的 UI/UX 流程。实际使用需要集成相应的 AI 服务。

3. **安全考虑**：生产环境需要添加用户认证、API 限流等安全措施。

4. **性能优化**：大量历史数据时建议实现分页加载和缓存机制。

## 开发说明

### 添加新功能
1. 在 `static/index.html` 中添加 UI 元素
2. 在相应的 `js/*.js` 文件中实现前端逻辑
3. 在 `app.py` 中添加 API 端点

### 自定义样式
修改 `static/css/style.css` 中的 CSS 变量：
```css
:root {
  --accent-primary: #0ea5e9;  /* 主色调 */
  --bg-primary: #0f172a;      /* 背景色 */
  /* ... */
}
```

## 许可证

本项目基于原 ChatGPT on WeChat 项目，遵循相同的开源协议。