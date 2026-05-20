"""工具类：数据分析器。

这个模块负责把清洗后的招聘数据变成可读结论。
它关注薪资、城市、岗位方向和技能词频，这些统计结果能帮助判断 AI 转型岗位应该重点补哪些能力。
"""

import pandas as pd
from collections import Counter
from datetime import datetime


class DataAnalyzer:
    """把多个分析维度封装到一起，并统一生成报告。"""

    def __init__(self, df):
        """初始化分析器，保存待分析数据和统计结果。

        `stats` 用来存放中间结果，后面生成报告时不需要重复计算。

        Args:
            df: pandas数据框
        """
        self.df = df
        self.stats = {}

    def analyze_salary(self):
        """分析薪资数据，判断岗位薪资的大致水平。

        这里看均值、中位数、最低和最高值。
        中位数通常比平均值更稳，因为少数高薪岗位会把平均值拉高。
        """
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
        """分析城市分布，判断岗位主要集中在哪些城市。

        求职时城市分布会直接影响投递策略和通勤成本。
        """
        print("\n📊 分析城市分布...")

        if 'city' in self.df.columns:
            city_counts = self.df['city'].value_counts()
            self.stats['city'] = city_counts.to_dict()

            print("  城市分布:")
            for city, count in city_counts.items():
                percentage = (count / len(self.df)) * 100
                print(f"    {city}: {count} ({percentage:.1f}%)")

    def analyze_direction(self):
        """分析岗位方向，判断市场更偏 RAG、NL2SQL、后端还是算法。

        这一步用于把学习路线和招聘需求对齐，避免只学自己感兴趣但市场不高频的方向。
        """
        print("\n📊 分析岗位方向...")

        if 'direction' in self.df.columns:
            direction_counts = self.df['direction'].value_counts()
            self.stats['direction'] = direction_counts.to_dict()

            print("  岗位方向:")
            for direction, count in direction_counts.items():
                percentage = (count / len(self.df)) * 100
                print(f"    {direction}: {count} ({percentage:.1f}%)")

    def analyze_skills(self):
        """分析技能词频，找出岗位描述里最常出现的能力要求。

        高频技能词可以反向指导简历关键词和后续学习重点。
        """
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
        """生成适合复盘和留档的分析报告。

        报告不是只给程序看，而是给自己做求职判断和复盘使用。
        因此这里会把统计结果整理成更容易阅读的文本格式。

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
        """运行完整分析流程。

        这个方法统一调度各个分析步骤，主程序只需要调用一次。
        后续要新增分析维度，也可以在这里扩展。

        Args:
            output_file: 输出报告文件路径
        """
        self.analyze_salary()
        self.analyze_city()
        self.analyze_direction()
        self.analyze_skills()
        self.generate_report(output_file)
