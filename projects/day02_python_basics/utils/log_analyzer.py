"""
工具类：日志分析器

提供日志文件分析功能
"""

import re
from datetime import datetime
from collections import Counter


class LogAnalyzer:
    """日志分析器类"""

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

        日志格式：2026-04-23 10:30:15 [INFO] 消息内容

        Args:
            line: 日志行

        Returns:
            dict: 解析后的日志信息
        """
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
                if line.strip():
                    log_entry = self.parse_log_line(line)
                    if log_entry:
                        self.logs.append(log_entry)

        print(f"✅ 成功读取 {len(self.logs)} 条日志")

    def analyze(self):
        """分析日志"""
        print("📊 分析日志...")

        self.stats['total'] = len(self.logs)

        for log in self.logs:
            level = log['level']
            self.stats['by_level'][level] += 1

            if level == 'ERROR':
                self.stats['errors'].append(log)
            elif level == 'WARNING':
                self.stats['warnings'].append(log)

        print("✅ 分析完成")

    def generate_report(self, output_file=None):
        """
        生成分析报告

        Args:
            output_file: 输出文件路径
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
            for i, error in enumerate(self.stats['errors'][:10], 1):
                report_lines.append(f"  {i}. [{error['timestamp']}] {error['message']}")
            if len(self.stats['errors']) > 10:
                report_lines.append(f"  ... 还有 {len(self.stats['errors']) - 10} 条错误")

        # 警告详情
        if self.stats['warnings']:
            report_lines.append(f"\n⚠️  警告详情 (共 {len(self.stats['warnings'])} 条):")
            for i, warning in enumerate(self.stats['warnings'][:5], 1):
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
        """
        运行完整分析流程

        Args:
            output_file: 输出报告文件路径
        """
        self.read_logs()
        self.analyze()
        self.generate_report(output_file)
