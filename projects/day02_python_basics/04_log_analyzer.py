"""
Day 2 实战项目：日志文件分析器

功能：
1. 读取日志文件
2. 解析日志行（时间、级别、消息）
3. 统计各级别日志数量
4. 提取错误信息
5. 生成分析报告
"""

import re
from datetime import datetime
from pathlib import Path
from collections import Counter


class LogAnalyzer:
    """日志分析器"""

    def __init__(self, log_file):
        """
        初始化日志分析器

        Args:
            log_file: 日志文件路径
        """
        self.log_file = log_file
        self.logs = []
        self.stats = {
            'total': 0,
            'by_level': Counter(),
            'errors': [],
            'warnings': []
        }

    def parse_log_line(self, line):
        """
        解析单行日志

        日志格式示例：
        2026-04-23 10:30:15 [INFO] 服务启动成功
        2026-04-23 10:30:20 [ERROR] 数据库连接失败

        Args:
            line: 日志行

        Returns:
            dict: 解析后的日志信息，如果解析失败返回None
        """
        # 正则表达式匹配日志格式
        pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.+)'
        match = re.match(pattern, line.strip())

        if match:
            timestamp_str, level, message = match.groups()
            return {
                'timestamp': timestamp_str,
                'level': level,
                'message': message,
                'raw': line.strip()
            }
        return None

    def read_logs(self):
        """读取并解析日志文件"""
        print(f"📖 读取日志文件: {self.log_file}")

        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():  # 跳过空行
                    log_entry = self.parse_log_line(line)
                    if log_entry:
                        self.logs.append(log_entry)

        print(f"✅ 成功读取 {len(self.logs)} 条日志")

    def analyze(self):
        """分析日志"""
        print("\n📊 分析日志...")

        self.stats['total'] = len(self.logs)

        for log in self.logs:
            level = log['level']
            self.stats['by_level'][level] += 1

            # 收集错误和警告
            if level == 'ERROR':
                self.stats['errors'].append(log)
            elif level == 'WARNING':
                self.stats['warnings'].append(log)

        print("✅ 分析完成")

    def generate_report(self, output_file=None):
        """
        生成分析报告

        Args:
            output_file: 输出文件路径，如果为None则只打印到控制台
        """
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("日志分析报告")
        report_lines.append("=" * 70)
        report_lines.append(f"\n📁 日志文件: {self.log_file}")
        report_lines.append(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 总体统计
        report_lines.append(f"\n📊 总体统计:")
        report_lines.append(f"  总日志数: {self.stats['total']}")

        # 按级别统计
        report_lines.append(f"\n📈 按级别统计:")
        for level, count in self.stats['by_level'].most_common():
            percentage = (count / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
            report_lines.append(f"  {level:10s}: {count:5d} ({percentage:5.1f}%)")

        # 错误详情
        if self.stats['errors']:
            report_lines.append(f"\n❌ 错误详情 (共 {len(self.stats['errors'])} 条):")
            for i, error in enumerate(self.stats['errors'][:10], 1):  # 只显示前10条
                report_lines.append(f"  {i}. [{error['timestamp']}] {error['message']}")
            if len(self.stats['errors']) > 10:
                report_lines.append(f"  ... 还有 {len(self.stats['errors']) - 10} 条错误")

        # 警告详情
        if self.stats['warnings']:
            report_lines.append(f"\n⚠️  警告详情 (共 {len(self.stats['warnings'])} 条):")
            for i, warning in enumerate(self.stats['warnings'][:5], 1):  # 只显示前5条
                report_lines.append(f"  {i}. [{warning['timestamp']}] {warning['message']}")
            if len(self.stats['warnings']) > 5:
                report_lines.append(f"  ... 还有 {len(self.stats['warnings']) - 5} 条警告")

        report_lines.append("\n" + "=" * 70)

        # 打印到控制台
        report = '\n'.join(report_lines)
        print(report)

        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n💾 报告已保存到: {output_file}")

    def run(self, output_file=None):
        """运行完整分析流程"""
        self.read_logs()
        self.analyze()
        self.generate_report(output_file)


def create_sample_log(log_file):
    """创建示例日志文件"""
    sample_logs = """2026-04-23 09:00:00 [INFO] 系统启动
2026-04-23 09:00:05 [INFO] 加载配置文件
2026-04-23 09:00:10 [INFO] 连接数据库
2026-04-23 09:00:15 [INFO] 数据库连接成功
2026-04-23 09:00:20 [INFO] 启动Web服务器
2026-04-23 09:00:25 [INFO] Web服务器启动成功，监听端口 8000
2026-04-23 09:05:30 [INFO] 收到用户请求: GET /api/health
2026-04-23 09:05:35 [INFO] 返回响应: 200 OK
2026-04-23 09:10:00 [WARNING] 内存使用率达到 75%
2026-04-23 09:15:00 [INFO] 收到用户请求: POST /api/login
2026-04-23 09:15:05 [ERROR] 数据库查询失败: 连接超时
2026-04-23 09:15:10 [ERROR] 用户登录失败: 数据库错误
2026-04-23 09:20:00 [INFO] 收到用户请求: GET /api/data
2026-04-23 09:20:05 [WARNING] 查询响应时间过长: 3.5秒
2026-04-23 09:25:00 [INFO] 执行定时任务: 数据备份
2026-04-23 09:25:30 [INFO] 数据备份完成
2026-04-23 09:30:00 [ERROR] Redis连接失败: 连接被拒绝
2026-04-23 09:30:05 [WARNING] 降级使用本地缓存
2026-04-23 09:35:00 [INFO] 收到用户请求: GET /api/users
2026-04-23 09:35:05 [INFO] 返回响应: 200 OK
2026-04-23 09:40:00 [ERROR] 文件写入失败: 磁盘空间不足
2026-04-23 09:45:00 [INFO] 系统健康检查通过
"""

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(sample_logs)

    print(f"✅ 创建示例日志文件: {log_file}")


if __name__ == "__main__":
    print("=" * 70)
    print("Day 2 实战项目：日志文件分析器")
    print("=" * 70)

    # 创建测试目录
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)

    # 创建示例日志
    log_file = test_dir / "app.log"
    create_sample_log(log_file)

    print()

    # 运行分析
    analyzer = LogAnalyzer(log_file)
    report_file = test_dir / "log_report.txt"
    analyzer.run(output_file=report_file)

    print("\n" + "=" * 70)
    print("✅ 日志分析器项目完成！")
    print("=" * 70)
