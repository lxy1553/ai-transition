"""
Day 4 - HTTP与API
主函数：天气查询API调用器

项目结构：
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
"""

from pathlib import Path
from datetime import datetime
from utils import HTTPClient, APIAuth, JSONParser


def query_weather(city: str = "beijing") -> dict:
    """
    查询天气信息（使用免费的wttr.in服务）

    Args:
        city: 城市名称

    Returns:
        天气信息字典
    """
    print(f"\n🌤️  正在查询 {city} 的天气...")

    # 使用wttr.in的JSON API（无需API Key）
    client = HTTPClient()
    url = f"https://wttr.in/{city}?format=j1"

    response = client.get(url)

    if response is None:
        print("❌ 天气查询失败")
        return None

    # 解析JSON响应
    data = JSONParser.parse(response.text)

    if data is None:
        print("❌ JSON解析失败")
        return None

    # 提取关键信息
    current = data.get('current_condition', [{}])[0]
    weather_info = {
        'city': city,
        'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'temperature': current.get('temp_C', 'N/A'),
        'feels_like': current.get('FeelsLikeC', 'N/A'),
        'humidity': current.get('humidity', 'N/A'),
        'weather_desc': current.get('weatherDesc', [{}])[0].get('value', 'N/A'),
        'wind_speed': current.get('windspeedKmph', 'N/A'),
    }

    client.close()
    return weather_info


def display_weather(weather_info: dict):
    """
    格式化显示天气信息

    Args:
        weather_info: 天气信息字典
    """
    if weather_info is None:
        return

    print("\n" + "=" * 50)
    print(f"📍 城市: {weather_info['city']}")
    print(f"🕐 查询时间: {weather_info['query_time']}")
    print("-" * 50)
    print(f"🌡️  温度: {weather_info['temperature']}°C")
    print(f"🤔 体感温度: {weather_info['feels_like']}°C")
    print(f"💧 湿度: {weather_info['humidity']}%")
    print(f"☁️  天气: {weather_info['weather_desc']}")
    print(f"💨 风速: {weather_info['wind_speed']} km/h")
    print("=" * 50)


def save_query_history(weather_info: dict, history_file: Path):
    """
    保存查询历史

    Args:
        weather_info: 天气信息字典
        history_file: 历史文件路径
    """
    if weather_info is None:
        return

    # 加载现有历史
    history = JSONParser.load_from_file(history_file) or []

    # 添加新记录
    history.append(weather_info)

    # 保存
    if JSONParser.save_to_file(history, history_file):
        print(f"\n✅ 查询历史已保存到: {history_file}")


def demo_http_methods():
    """
    演示HTTP请求方法
    """
    print("\n" + "=" * 70)
    print("演示：HTTP请求方法")
    print("=" * 70)

    client = HTTPClient()

    # GET请求示例
    print("\n1️⃣ GET请求示例：")
    print("   URL: https://httpbin.org/get")
    response = client.get("https://httpbin.org/get", params={"key": "value"})
    if response:
        print(f"   状态码: {response.status_code}")
        print(f"   响应头: {dict(list(response.headers.items())[:3])}")

    # POST请求示例
    print("\n2️⃣ POST请求示例：")
    print("   URL: https://httpbin.org/post")
    response = client.post(
        "https://httpbin.org/post",
        json={"name": "测试", "value": 123}
    )
    if response:
        print(f"   状态码: {response.status_code}")

    client.close()


def demo_api_auth():
    """
    演示API认证方法
    """
    print("\n" + "=" * 70)
    print("演示：API认证方法")
    print("=" * 70)

    # API Key认证
    print("\n1️⃣ API Key认证：")
    headers = APIAuth.api_key_header("your-api-key-here")
    print(f"   请求头: {headers}")

    # Bearer Token认证
    print("\n2️⃣ Bearer Token认证：")
    headers = APIAuth.bearer_token_header("your-token-here")
    print(f"   请求头: {headers}")

    # Basic Auth认证
    print("\n3️⃣ Basic Auth认证：")
    headers = APIAuth.basic_auth_header("username", "password")
    print(f"   请求头: {headers}")


def demo_json_parser():
    """
    演示JSON解析
    """
    print("\n" + "=" * 70)
    print("演示：JSON解析")
    print("=" * 70)

    # 示例JSON数据
    json_str = '''
    {
        "user": {
            "name": "张三",
            "age": 25,
            "skills": ["Python", "SQL", "RAG"]
        },
        "status": "active"
    }
    '''

    print("\n1️⃣ 解析JSON字符串：")
    data = JSONParser.parse(json_str)
    print(f"   解析结果: {data}")

    print("\n2️⃣ 提取嵌套值：")
    name = JSONParser.get_value(data, "user.name")
    print(f"   user.name = {name}")

    first_skill = JSONParser.get_value(data, "user.skills.0")
    print(f"   user.skills.0 = {first_skill}")

    print("\n3️⃣ 转换为JSON字符串：")
    json_output = JSONParser.to_string(data)
    print(f"   输出:\n{json_output}")


def main():
    """主函数"""
    print("=" * 70)
    print("Day 4 - HTTP与API：天气查询API调用器")
    print("=" * 70)

    # 演示1：HTTP请求方法
    demo_http_methods()

    # 演示2：API认证方法
    demo_api_auth()

    # 演示3：JSON解析
    demo_json_parser()

    # 实战：天气查询
    print("\n" + "=" * 70)
    print("实战：天气查询API调用")
    print("=" * 70)

    # 查询多个城市
    cities = ["beijing", "shanghai", "shenzhen"]
    history_file = Path("output/query_history.json")
    history_file.parent.mkdir(exist_ok=True)

    for city in cities:
        weather_info = query_weather(city)
        display_weather(weather_info)
        save_query_history(weather_info, history_file)

    # 完成
    print("\n" + "=" * 70)
    print("✅ 所有演示完成！")
    print("=" * 70)

    print("\n📦 产出文件：")
    print(f"  - {history_file}  # 查询历史")

    print("\n💡 今日学习要点：")
    print("  1. HTTP请求：GET、POST方法")
    print("  2. API认证：API Key、Bearer Token、Basic Auth")
    print("  3. JSON处理：解析、提取、转换")
    print("  4. 错误处理：重试机制、异常捕获")
    print("  5. 实战应用：天气查询API调用")


if __name__ == "__main__":
    main()
