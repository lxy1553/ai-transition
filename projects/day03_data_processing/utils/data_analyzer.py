"""
工具类：数据分析器

提供数据分析和统计功能
"""

import pandas as pd
from collections import Counter
from datetime import datetime


class DataAnalyzer:
    """数据分析器类"""

    def __init__(self, df):
        """
        初始化数据分析器

        Args:
            df: pandas数据框
        """
        self.df = df
        self.stats = {}

    def analyze_salary(self):
        """分析薪资数据"""
        print("\n📊 分析薪资数据...")

        if 'salary_avg' in self.df.columns:
            salary_data = self.df['salary_avg'].dropna()

            self.stats['salary'] = {
                'count': len(salary_data),
                'mean': salary_data.mean(),
                'median': salary_data.median(),
                'min': salary_data.min(),
                'max': salary_data.max(),
                'std': salary_data.std()
            }

            print(f"  平均薪资: {self.stats['salary']['mean']:.1f}K")
            print(f"  中位数: {self.stats['salary']['median']:.1f}K")
            print(f"  范围: {self.stats['salary']['min']:.0f}K - {self.stats['salary']['max']:.0f}K")

    def analyze_city(self):
        """分析城市分布"""
        print("\n📊 分析城市分布...")

        if 'city' in self.df.columns:
            city_counts = self.df['city'].value_counts()
            self.stats['city'] = city_counts.to_dict()

            print("  城市分布:")
            for city, count in city_counts.items():
                percentage = (count / len(self.df)) * 100
                print(f"    {city}: {count} ({percentage:.1f}%)")

    def analyze_direction(self):
        """分析岗位方向"""
        print("\n📊 分析岗位方向...")

        if 'direction' in self.df.columns:
            direction_counts = self.df['direction'].value_counts()
            self.stats['direction'] = direction_counts.to_dict()

            print("  岗位方向:")
            for direction, count in direction_counts.items():
                percentage = (count / len(self.df)) * 100
                print(f"    {direction}: {count} ({percentage:.1f}%)")

    def analyze_skills(self):
        """分析技能词频"""
        print("\n📊 分析技能词频...")

        if 'skills_list' in self.df.columns:
            all_skills = []
            for skills in self.df['skills_list']:
                all_skills.extend(skills)

            skill_counter = Counter(all_skills)
            self.stats['skills'] = dict(skill_counter.most_common(15))

            print("  Top 15 技能词:")
            for i, (skill, count) in enumerate(skill_counter.most_common(15), 1):
                percentage = (count / len(self.df)) * 100
                print(f"    {i:2d}. {skill:20s}: {count:2d} ({percentage:5.1f}%)")

    def generate_report(self, output_file=None):
        """
        生成分析报告

        Args:
            output_file: 输出文件路径
        """
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("招聘数据分析报告")
        report_lines.append("=" * 70)
        report_lines.append(f"\n📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"📊 数据量: {len(self.df)} 条")

        # 薪资分析
        if 'salary' in self.stats:
            report_lines.append("\n" + "=" * 70)
            report_lines.append("💰 薪资分析")
            report_lines.append("=" * 70)
            s = self.stats['salary']
            report_lines.append(f"  样本数: {s['count']}")
            report_lines.append(f"  平均薪资: {s['mean']:.1f}K")
            report_lines.append(f"  中位数: {s['median']:.1f}K")
            report_lines.append(f"  最低: {s['min']:.0f}K")
            report_lines.append(f"  最高: {s['max']:.0f}K")
            report_lines.append(f"  标准差: {s['std']:.1f}K")

        # 城市分布
        if 'city' in self.stats:
            report_lines.append("\n" + "=" * 70)
            report_lines.append("🏙️  城市分布")
            report_lines.append("=" * 70)
            for city, count in self.stats['city'].items():
                percentage = (count / len(self.df)) * 100
                report_lines.append(f"  {city:10s}: {count:2d} ({percentage:5.1f}%)")

        # 岗位方向
        if 'direction' in self.stats:
            report_lines.append("\n" + "=" * 70)
            report_lines.append("🎯 岗位方向")
            report_lines.append("=" * 70)
            for direction, count in self.stats['direction'].items():
                percentage = (count / len(self.df)) * 100
                report_lines.append(f"  {direction:20s}: {count:2d} ({percentage:5.1f}%)")

        # 技能词频
        if 'skills' in self.stats:
            report_lines.append("\n" + "=" * 70)
            report_lines.append("🔥 Top 15 技能词")
            report_lines.append("=" * 70)
            for i, (skill, count) in enumerate(self.stats['skills'].items(), 1):
                percentage = (count / len(self.df)) * 100
                report_lines.append(f"  {i:2d}. {skill:20s}: {count:2d} ({percentage:5.1f}%)")

        report_lines.append("\n" + "=" * 70)

        # 打印到控制台
        report = '\n'.join(report_lines)
        print(report)

        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n💾 报告已保存到: {output_file}")

    def run_analysis(self, output_file=None):
        """
        运行完整分析流程

        Args:
            output_file: 输出报告文件路径
        """
        self.analyze_salary()
        self.analyze_city()
        self.analyze_direction()
        self.analyze_skills()
        self.generate_report(output_file)
