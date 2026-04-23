# Day 4 - HTTP与API

## 项目说明

这是一个完整的HTTP与API学习项目，展示HTTP请求、API认证和JSON数据处理。

## 项目结构

```
day04_api_client/
├── main.py              # 主函数入口
├── utils/               # 工具类模块
│   ├── __init__.py
│   ├── http_client.py   # HTTP客户端
│   ├── api_auth.py      # API认证管理
│   └── json_parser.py   # JSON解析器
├── examples/            # 示例数据
│   └── sample_response.json
├── output/              # 产出报告
│   └── query_history.json
└── README.md            # 本文件
```

## 功能模块

### 1. HTTP客户端 (HTTPClient)

- 发送GET请求
- 发送POST请求
- 自动重试机制
- 超时控制
- 会话管理

### 2. API认证管理 (APIAuth)

- API Key认证
- Bearer Token认证
- Basic Auth认证
- 自定义请求头

### 3. JSON解析器 (JSONParser)

- JSON字符串解析
- 嵌套数据提取
- JSON文件读写
- 数据格式转换

## 运行方式

```bash
# 安装依赖
pip3 install requests

# 运行程序
python3 main.py
```

## 功能演示

### 1. HTTP请求方法

- GET请求：获取数据
- POST请求：提交数据
- 状态码处理
- 响应头解析

### 2. API认证方法

- API Key：`X-API-Key: your-key`
- Bearer Token：`Authorization: Bearer token`
- Basic Auth：`Authorization: Basic base64(user:pass)`

### 3. JSON数据处理

- 解析JSON字符串
- 提取嵌套值（如 `user.name`）
- 转换为JSON字符串
- 保存和加载JSON文件

### 4. 实战应用

- 调用天气API（wttr.in）
- 查询多个城市天气
- 格式化显示结果
- 保存查询历史

## 学习要点

1. **HTTP基础**
   - 请求方法（GET、POST）
   - 状态码（200、404、500等）
   - 请求头和响应头
   - URL参数和请求体

2. **API认证**
   - API Key认证方式
   - Bearer Token认证方式
   - Basic Auth认证方式
   - 请求头设置

3. **JSON处理**
   - JSON格式解析
   - 嵌套数据提取
   - 数据类型转换
   - 文件读写操作

4. **错误处理**
   - 请求超时控制
   - 自动重试机制
   - 异常捕获处理
   - 默认值设置

## 输出示例

### 天气查询结果

```
📍 城市: beijing
🕐 查询时间: 2026-04-25 10:30:00
--------------------------------------------------
🌡️  温度: 18°C
🤔 体感温度: 16°C
💧 湿度: 45%
☁️  天气: Partly cloudy
💨 风速: 15 km/h
```

### 查询历史

保存在 `output/query_history.json`，包含所有查询记录。

## 依赖库

- `requests`: HTTP请求库
- `json`: JSON处理（Python内置）

## 注意事项

- API Key要妥善保管，不要提交到Git
- 注意API限流（rate limit）
- 设置合理的超时时间
- 做好错误处理和重试
