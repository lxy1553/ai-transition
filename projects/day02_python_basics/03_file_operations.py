"""
Day 2 - Python文件操作练习

学习内容：
1. 文件打开与关闭
2. with语句（上下文管理器）
3. 读取文件
4. 写入文件
5. 路径处理
"""

import os
from pathlib import Path


# ============ 1. 基础文件读写 ============

def read_file_basic(file_path):
    """基础方式读取文件（需要手动关闭）"""
    f = open(file_path, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    return content


def read_file_with(file_path):
    """推荐方式：使用with语句读取文件（自动关闭）"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content


def read_file_lines(file_path):
    """按行读取文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return lines


def write_file(file_path, content):
    """写入文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def append_file(file_path, content):
    """追加内容到文件"""
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(content)


# ============ 2. CSV文件处理 ============

def read_csv_simple(file_path):
    """简单读取CSV文件（不用csv模块）"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # 第一行是表头
        headers = lines[0].strip().split(',')
        # 读取数据行
        for line in lines[1:]:
            if line.strip():  # 跳过空行
                values = line.strip().split(',')
                row = dict(zip(headers, values))
                data.append(row)
    return data


def write_csv_simple(file_path, data, headers):
    """简单写入CSV文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        # 写入表头
        f.write(','.join(headers) + '\n')
        # 写入数据
        for row in data:
            values = [str(row.get(h, '')) for h in headers]
            f.write(','.join(values) + '\n')


# ============ 3. 路径处理 ============

def ensure_dir(dir_path):
    """确保目录存在，不存在则创建"""
    Path(dir_path).mkdir(parents=True, exist_ok=True)


def get_file_info(file_path):
    """获取文件信息"""
    path = Path(file_path)
    if not path.exists():
        return None

    return {
        'name': path.name,
        'stem': path.stem,  # 文件名（不含扩展名）
        'suffix': path.suffix,  # 扩展名
        'size': path.stat().st_size,  # 文件大小（字节）
        'is_file': path.is_file(),
        'is_dir': path.is_dir(),
        'parent': str(path.parent),
        'absolute': str(path.absolute())
    }


def list_files(dir_path, pattern='*'):
    """列出目录下的文件"""
    path = Path(dir_path)
    if not path.exists():
        return []
    return [str(f) for f in path.glob(pattern)]


# ============ 测试代码 ============

if __name__ == "__main__":
    print("=" * 60)
    print("Day 2 - Python文件操作练习")
    print("=" * 60)

    # 创建测试目录
    test_dir = "test_files"
    ensure_dir(test_dir)
    print(f"\n✅ 创建测试目录: {test_dir}")

    # 测试1：写入文本文件
    print("\n1. 写入文本文件：")
    text_file = f"{test_dir}/sample.txt"
    content = """这是第一行
这是第二行
这是第三行
"""
    write_file(text_file, content)
    print(f"✅ 写入文件: {text_file}")

    # 测试2：读取文本文件
    print("\n2. 读取文本文件：")
    read_content = read_file_with(text_file)
    print(f"文件内容:\n{read_content}")

    # 测试3：按行读取
    print("\n3. 按行读取文件：")
    lines = read_file_lines(text_file)
    for i, line in enumerate(lines, 1):
        print(f"第{i}行: {line.strip()}")

    # 测试4：追加内容
    print("\n4. 追加内容：")
    append_file(text_file, "这是追加的第四行\n")
    print(f"✅ 追加内容到: {text_file}")

    # 测试5：创建CSV文件
    print("\n5. 创建CSV文件：")
    csv_file = f"{test_dir}/jobs.csv"
    jobs_data = [
        {'company': '某互联网公司', 'position': 'AI工程师', 'salary': '20-35K', 'city': '北京'},
        {'company': '某AI公司', 'position': 'RAG工程师', 'salary': '25-40K', 'city': '上海'},
        {'company': '某数据公司', 'position': 'NL2SQL工程师', 'salary': '22-38K', 'city': '深圳'},
    ]
    headers = ['company', 'position', 'salary', 'city']
    write_csv_simple(csv_file, jobs_data, headers)
    print(f"✅ 创建CSV文件: {csv_file}")

    # 测试6：读取CSV文件
    print("\n6. 读取CSV文件：")
    csv_data = read_csv_simple(csv_file)
    for i, row in enumerate(csv_data, 1):
        print(f"岗位{i}: {row['position']} - {row['company']} - {row['salary']} - {row['city']}")

    # 测试7：获取文件信息
    print("\n7. 获取文件信息：")
    file_info = get_file_info(csv_file)
    for key, value in file_info.items():
        print(f"  {key:12s}: {value}")

    # 测试8：列出目录文件
    print("\n8. 列出目录文件：")
    files = list_files(test_dir)
    print(f"目录 {test_dir} 中的文件:")
    for f in files:
        print(f"  - {f}")

    print("\n" + "=" * 60)
    print("文件操作练习完成！")
    print("=" * 60)

    print("\n💡 学到的知识点：")
    print("1. 使用with语句自动管理文件")
    print("2. 读取和写入文本文件")
    print("3. 处理CSV文件")
    print("4. 使用pathlib处理路径")
    print("5. 获取文件信息和列出目录")
