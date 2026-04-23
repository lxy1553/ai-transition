# Day 4 - 2026-04-25

## 今日主题

HTTP与API

## 今日目标

- 掌握HTTP请求基础
- 学会API认证方法
- 完成JSON数据处理
- 创建API调用脚本

## 今日任务拆解

### 任务 1：HTTP基础

**学习内容：**
- [ ] HTTP请求方法（GET、POST、PUT、DELETE）
- [ ] HTTP状态码
- [ ] 请求头和响应头
- [ ] URL参数和请求体

### 任务 2：API认证

**学习内容：**
- [ ] API Key认证
- [ ] Bearer Token认证
- [ ] OAuth2基础概念
- [ ] 请求头中的认证信息

### 任务 3：JSON处理

**学习内容：**
- [ ] JSON格式解析
- [ ] Python的json模块
- [ ] 嵌套JSON数据提取
- [ ] JSON数据转换

### 任务 4：实战项目

**项目：天气查询API调用器**

基于公开API，完成：
- [ ] 调用天气API获取数据
- [ ] 解析JSON响应
- [ ] 格式化输出结果
- [ ] 错误处理和重试机制
- [ ] 保存查询历史

## 项目结构

```
day04_api_client/
├── main.py              # 主函数入口
├── utils/               # 工具类模块
│   ├── http_client.py   # HTTP客户端
│   ├── api_auth.py      # API认证管理
│   └── json_parser.py   # JSON解析器
├── examples/            # 示例数据
│   └── sample_response.json
├── output/              # 产出报告
│   └── query_history.json
└── README.md            # 项目说明
```

## 建议时间安排

### 上午（09:30 - 12:00）

- 09:30 - 10:30：HTTP基础学习
- 10:30 - 11:30：API认证学习
- 11:30 - 12:00：整理笔记

### 下午（14:00 - 18:00）

- 14:00 - 15:00：JSON处理学习
- 15:00 - 17:00：开发API调用器
- 17:00 - 18:00：测试与优化

## 今日产出物

- [ ] HTTP请求示例代码
- [ ] API认证示例
- [ ] 天气查询API调用器项目
- [ ] 查询历史记录
- [ ] Day 4学习笔记

## 注意事项

⚠️ **今天的重点：**
- requests库是Python最常用的HTTP库
- API Key要妥善保管，不要提交到Git
- JSON数据要做好异常处理
- HTTP错误要有重试机制

⚠️ **避免的坑：**
- 请求超时设置
- 编码问题（UTF-8）
- API限流（rate limit）
- 敏感信息泄露

---

*开始时间：2026-04-25 上午*

---

## 📚 今日核心知识点详解

### 1️⃣ HTTP是什么？

**大白话：**
HTTP就是浏览器和服务器之间"说话"的规则。你在浏览器输入网址，浏览器就用HTTP向服务器"要"网页，服务器再把网页"给"你。

**HTTP请求方法：**

```python
# GET - 获取数据（就像"我要看这个页面"）
response = requests.get('https://api.example.com/users')

# POST - 提交数据（就像"我要提交这个表单"）
response = requests.post('https://api.example.com/users', json={'name': '张三'})

# PUT - 更新数据（就像"我要修改这条记录"）
response = requests.put('https://api.example.com/users/1', json={'name': '李四'})

# DELETE - 删除数据（就像"我要删除这条记录"）
response = requests.delete('https://api.example.com/users/1')
```

**HTTP状态码：**

| 状态码 | 含义 | 大白话 |
|---|---|---|
| 200 | OK | 成功了 |
| 201 | Created | 创建成功 |
| 400 | Bad Request | 你的请求有问题 |
| 401 | Unauthorized | 没有权限，需要登录 |
| 404 | Not Found | 找不到这个页面 |
| 500 | Internal Server Error | 服务器出错了 |

**请求头和响应头：**

```python
# 请求头 - 告诉服务器一些额外信息
headers = {
    'Content-Type': 'application/json',  # 我发的是JSON数据
    'User-Agent': 'MyApp/1.0',           # 我是谁
    'Accept': 'application/json'         # 我想要JSON格式的响应
}

response = requests.get(url, headers=headers)

# 响应头 - 服务器告诉你一些信息
print(response.headers['Content-Type'])  # 服务器返回的数据类型
print(response.headers['Date'])          # 服务器时间
```

---

### 2️⃣ API认证

**为什么需要认证？**
就像进小区要门禁卡一样，API也需要验证你的身份，防止随便谁都能访问。

**1. API Key认证（最简单）**

```python
# API Key就像一把钥匙，放在请求头里
headers = {
    'X-API-Key': 'your-secret-key-here'
}

response = requests.get('https://api.example.com/data', headers=headers)
```

**使用场景：**
- 天气API
- 地图API
- 翻译API

**2. Bearer Token认证（常用）**

```python
# Token就像一个临时通行证
headers = {
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
}

response = requests.get('https://api.example.com/data', headers=headers)
```

**使用场景：**
- OAuth2认证后获得的token
- JWT（JSON Web Token）
- 大部分现代API

**3. Basic Auth认证（传统方式）**

```python
# 用户名和密码，编码后放在请求头
import base64

credentials = f"username:password"
encoded = base64.b64encode(credentials.encode()).decode()

headers = {
    'Authorization': f'Basic {encoded}'
}

response = requests.get('https://api.example.com/data', headers=headers)

# 或者用requests的简化方式
response = requests.get(
    'https://api.example.com/data',
    auth=('username', 'password')
)
```

**使用场景：**
- 内部API
- 简单的认证需求

---

### 3️⃣ JSON数据处理

**JSON是什么？**
JSON就是一种数据格式，长得像Python的字典，但是是字符串。用来在网络上传输数据。

**JSON格式：**

```json
{
  "name": "张三",
  "age": 25,
  "skills": ["Python", "SQL"],
  "address": {
    "city": "北京",
    "district": "朝阳区"
  }
}
```

**Python处理JSON：**

```python
import json

# 1. JSON字符串 → Python对象（解析）
json_str = '{"name": "张三", "age": 25}'
data = json.loads(json_str)
print(data['name'])  # 张三

# 2. Python对象 → JSON字符串（序列化）
data = {'name': '张三', 'age': 25}
json_str = json.dumps(data, ensure_ascii=False)
print(json_str)  # {"name": "张三", "age": 25}

# 3. 从文件读取JSON
with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 4. 保存JSON到文件
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

**提取嵌套数据：**

```python
data = {
    "user": {
        "name": "张三",
        "skills": ["Python", "SQL", "RAG"]
    }
}

# 方法1：直接访问
name = data['user']['name']
first_skill = data['user']['skills'][0]

# 方法2：使用get（更安全，不会报错）
name = data.get('user', {}).get('name', '未知')

# 方法3：自定义路径提取函数（我们的JSONParser）
def get_value(data, path, default=None):
    keys = path.split('.')
    result = data
    for key in keys:
        if key.isdigit():
            result = result[int(key)]
        else:
            result = result[key]
    return result

name = get_value(data, 'user.name')           # 张三
skill = get_value(data, 'user.skills.0')      # Python
```

---

### 4️⃣ requests库详解

**requests是什么？**
Python最好用的HTTP库，比内置的urllib简单太多。

**基本用法：**

```python
import requests

# 1. 发送GET请求
response = requests.get('https://api.example.com/data')

# 2. 带参数的GET请求
params = {'city': 'beijing', 'date': '2026-04-25'}
response = requests.get('https://api.example.com/weather', params=params)
# 实际请求：https://api.example.com/weather?city=beijing&date=2026-04-25

# 3. 发送POST请求（JSON数据）
data = {'name': '张三', 'age': 25}
response = requests.post('https://api.example.com/users', json=data)

# 4. 发送POST请求（表单数据）
data = {'username': 'zhangsan', 'password': '123456'}
response = requests.post('https://api.example.com/login', data=data)

# 5. 自定义请求头
headers = {'Authorization': 'Bearer token123'}
response = requests.get('https://api.example.com/data', headers=headers)

# 6. 设置超时
response = requests.get('https://api.example.com/data', timeout=10)
```

**处理响应：**

```python
response = requests.get('https://api.example.com/data')

# 状态码
print(response.status_code)  # 200

# 响应内容（文本）
print(response.text)

# 响应内容（JSON）
data = response.json()

# 响应头
print(response.headers)

# 检查是否成功
if response.status_code == 200:
    print("成功")
else:
    print("失败")

# 或者用raise_for_status（失败会抛异常）
response.raise_for_status()
```

---

### 5️⃣ 错误处理和重试

**为什么需要错误处理？**
网络请求可能失败：网络断了、服务器挂了、超时了...必须处理这些情况。

**基本错误处理：**

```python
import requests

try:
    response = requests.get('https://api.example.com/data', timeout=10)
    response.raise_for_status()  # 如果状态码不是200，抛异常
    data = response.json()
except requests.exceptions.Timeout:
    print("请求超时")
except requests.exceptions.ConnectionError:
    print("网络连接失败")
except requests.exceptions.HTTPError as e:
    print(f"HTTP错误: {e}")
except requests.exceptions.RequestException as e:
    print(f"请求失败: {e}")
```

**重试机制：**

```python
import time

def get_with_retry(url, retry=3):
    """带重试的GET请求"""
    for attempt in range(retry):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"请求失败 (尝试 {attempt + 1}/{retry}): {e}")
            if attempt < retry - 1:
                time.sleep(1)  # 等1秒再重试
            else:
                return None
```

**使用Session（保持连接）：**

```python
# Session可以复用连接，提高性能
session = requests.Session()

# 设置默认请求头
session.headers.update({'Authorization': 'Bearer token123'})

# 发送多个请求
response1 = session.get('https://api.example.com/data1')
response2 = session.get('https://api.example.com/data2')

# 关闭session
session.close()

# 或者用with（推荐）
with requests.Session() as session:
    response = session.get('https://api.example.com/data')
```

---

### 6️⃣ 实战：调用真实API

**完整流程：**

```python
import requests
import json

def query_weather(city):
    """查询天气"""
    # 1. 准备URL和参数
    url = f"https://wttr.in/{city}"
    params = {'format': 'j1'}
    
    # 2. 设置请求头
    headers = {
        'User-Agent': 'MyWeatherApp/1.0'
    }
    
    # 3. 发送请求
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        # 4. 解析JSON响应
        data = response.json()
        
        # 5. 提取需要的信息
        current = data['current_condition'][0]
        weather_info = {
            'city': city,
            'temperature': current['temp_C'],
            'weather': current['weatherDesc'][0]['value'],
            'humidity': current['humidity']
        }
        
        return weather_info
        
    except Exception as e:
        print(f"查询失败: {e}")
        return None

# 使用
weather = query_weather('beijing')
if weather:
    print(f"{weather['city']}: {weather['temperature']}°C, {weather['weather']}")
```

---

## 💡 关键概念总结

| 概念 | 大白话 | 代码示例 |
|---|---|---|
| HTTP GET | 获取数据 | `requests.get(url)` |
| HTTP POST | 提交数据 | `requests.post(url, json=data)` |
| 状态码 | 请求结果 | `response.status_code` |
| 请求头 | 额外信息 | `headers={'Key': 'value'}` |
| API Key | 访问钥匙 | `headers={'X-API-Key': 'key'}` |
| Bearer Token | 临时通行证 | `headers={'Authorization': 'Bearer token'}` |
| JSON解析 | 字符串→对象 | `json.loads(json_str)` |
| JSON序列化 | 对象→字符串 | `json.dumps(data)` |
| 超时 | 等待时间 | `timeout=10` |
| 重试 | 失败再试 | `for attempt in range(3)` |

---

## 📊 今日实战成果

### 项目：天气查询API调用器

**功能实现：**
- ✅ HTTP客户端封装（GET、POST、重试）
- ✅ API认证管理（API Key、Bearer Token、Basic Auth）
- ✅ JSON解析器（解析、提取、保存）
- ✅ 天气查询实战（调用wttr.in API）
- ✅ 查询历史保存

**查询结果：**
- 北京：25°C，晴天
- 上海：16°C，多云
- 深圳：24°C，雷阵雨

**产出文件：**
- `output/query_history.json` - 查询历史记录

---

## 🎯 今日收获

**技术能力：**
- ✅ 掌握HTTP请求基础（GET、POST）
- ✅ 学会API认证方法（3种）
- ✅ 完成JSON数据处理
- ✅ 实现错误处理和重试机制
- ✅ 调用真实API完成实战

**工程能力：**
- ✅ 封装HTTP客户端类
- ✅ 模块化设计（认证、解析分离）
- ✅ 异常处理和容错
- ✅ 数据持久化（JSON文件）

---

*完成时间：2026-04-25 下午*
