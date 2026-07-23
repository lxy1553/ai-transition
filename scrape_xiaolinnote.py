#!/usr/bin/env python3
"""
爬取 xiaolinnote.com 所有 AI 面试题到本地 docs 目录

使用方法:
  pip install requests beautifulsoup4 markdownify
  python scrape_xiaolinnote.py
"""

import requests
import time
import re
import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("请先安装: pip install beautifulsoup4")
    exit(1)

try:
    from markdownify import markdownify as md_convert
except ImportError:
    md_convert = None
    print("⚠️  未安装 markdownify，将保留 HTML 格式")
    print("   建议安装: pip install markdownify")

# ============================================================
# 配置
# ============================================================

BASE_URL = "https://xiaolinnote.com"
START_URL = "https://xiaolinnote.com/ai/agent/agent_info.html"
OUTPUT_DIR = Path("/Users/lxy/Documents/ai_transition/docs")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://xiaolinnote.com/",
}

session = requests.Session()
session.headers.update(HEADERS)

# 已访问的 URL，防止重复
visited = set()
# 待访问队列
queue = []
# 收集的文章信息
all_articles = []


# ============================================================
# 工具函数
# ============================================================

def is_same_domain(url: str) -> bool:
    """检查 URL 是否属于 xiaolinnote.com"""
    parsed = urlparse(url)
    return parsed.netloc == "xiaolinnote.com" or parsed.netloc == "www.xiaolinnote.com"


def sanitize_filename(name: str) -> str:
    """清理文件名"""
    name = re.sub(r'[\\/*?:"<>|#&]', "_", name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:120]


def extract_text_from_html(html: str) -> str:
    """从 HTML 中提取正文内容"""
    soup = BeautifulSoup(html, "html.parser")

    # 移除不需要的元素
    for tag in soup.select(
        "script, style, nav, footer, header, .sidebar, .navbar, "
        ".nav, .footer, .header, .toc, .table-of-contents, "
        ".pagination, .prev-next, .edit-link, .last-updated, "
        ".page-meta, .comments, .advertisement, .ads, "
        '[role="navigation"], .VPSidebar, .VPNav, .VPFooter'
    ):
        tag.decompose()

    # 尝试找到主内容区域（VitePress / Docsify / 通用）
    content = None
    selectors = [
        ".VPContent", ".vp-doc", ".content", ".main-content",
        ".page-content", ".article-content", ".post-content",
        "article", "main", ".markdown-body", "#main-content",
        ".doc-content", ".theme-default-content",
    ]

    for selector in selectors:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 200:
            content = el
            break

    if content is None:
        # 降级：用 body
        content = soup.select_one("body") or soup

    # 提取文本
    if md_convert:
        text = md_convert(str(content), heading_style="ATX")
    else:
        text = content.get_text(separator="\n", strip=False)
        # 压缩空行
        text = re.sub(r'\n{4,}', '\n\n\n', text)

    return text.strip()


def extract_links(html: str, current_url: str) -> list:
    """从页面中提取同域链接"""
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # 跳过锚点、JS、邮件等
        if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
            continue

        full_url = urljoin(current_url, href)
        # 去掉 fragment
        full_url = full_url.split("#")[0]

        if is_same_domain(full_url) and full_url not in visited:
            links.append(full_url)

    return links


# ============================================================
# 核心爬取逻辑
# ============================================================

def fetch_page(url: str):
    """下载页面 HTML"""
    try:
        resp = session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()

        # 检查 Content-Type
        ct = resp.headers.get("Content-Type", "")
        if "text/html" not in ct:
            return None

        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.RequestException as e:
        print(f"  ❌ 请求失败: {url} — {e}")
        return None


def scrape_site(start_url: str):
    """BFS 爬取整个网站"""
    print("=" * 60)
    print("🚀 开始爬取 xiaolinnote.com")
    print(f"   起始页: {start_url}")
    print(f"   输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    queue.append(start_url)
    visited.add(start_url)

    article_count = 0
    max_pages = 500  # 安全上限

    while queue and len(visited) < max_pages:
        url = queue.pop(0)

        # 跳过非文章页面（静态资源、API 等）
        path = urlparse(url).path
        skip_patterns = [".png", ".jpg", ".jpeg", ".gif", ".svg",
                        ".css", ".js", ".woff", ".ttf", ".pdf",
                        ".ico", ".xml", ".json", ".txt", ".map"]
        if any(path.endswith(p) for p in skip_patterns):
            continue

        print(f"\n🔗 [{len(visited)}/{len(visited) + len(queue)}] {path}")

        html = fetch_page(url)
        if html is None:
            continue

        # 提取新链接（在提取内容之前，以便发现更多页面）
        new_links = extract_links(html, url)
        for link in new_links:
            if link not in visited:
                queue.append(link)
                visited.add(link)

        # 提取文章内容
        title = extract_title(html, url)
        content = extract_text_from_html(html)

        if len(content) > 100:  # 过滤掉内容太少的页面
            article_count += 1
            all_articles.append({
                "title": title,
                "url": url,
                "path": path,
            })

            # 保存为 Markdown
            save_article(title, url, path, content, article_count)

        # 礼貌延迟
        time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print(f"✅ 爬取完成！共保存 {article_count} 篇文章")
    print(f"   输出目录: {OUTPUT_DIR.absolute()}")
    save_index()
    print(f"{'=' * 60}")


def extract_title(html: str, url: str) -> str:
    """从页面中提取标题"""
    soup = BeautifulSoup(html, "html.parser")

    # 尝试多个选择器
    title_selectors = [
        "h1", ".page-title", ".article-title", ".post-title",
        ".content h1", "article h1", "main h1",
        ".VPContent h1", ".vp-doc h1",
    ]

    for selector in title_selectors:
        el = soup.select_one(selector)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)

    # 降级：用 <title> 标签
    if soup.title:
        title = soup.title.get_text(strip=True)
        # 去掉站点名后缀
        title = re.sub(r'\s*[|–—-]\s*xiaolinnote.*$', '', title)
        title = re.sub(r'\s*[|–—-]\s*小林.*$', '', title)
        if title:
            return title

    # 最后的降级
    return urlparse(url).path.strip("/").split("/")[-1].replace(".html", "")


def save_article(title: str, url: str, path: str, content: str, index: int):
    """保存单篇文章"""
    safe_title = sanitize_filename(title) if title else f"page_{index:04d}"

    # 按原始路径结构组织子目录
    clean_path = path.strip("/")
    if "/" in clean_path:
        subdir = OUTPUT_DIR / "/".join(clean_path.split("/")[:-1])
        subdir.mkdir(parents=True, exist_ok=True)
        filename = subdir / f"{safe_title}.md"
    else:
        filename = OUTPUT_DIR / f"{safe_title}.md"

    # 如果文件名太长，简化
    if len(str(filename)) > 200:
        filename = OUTPUT_DIR / f"{index:04d}_{safe_title[:80]}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"---\n")
        f.write(f"title: {title}\n")
        f.write(f"url: {url}\n")
        f.write(f"scraped: {datetime.now().isoformat()}\n")
        f.write(f"---\n\n")
        f.write(f"# {title}\n\n")
        f.write(f"> 原文链接: {url}\n\n")
        f.write(content)

    print(f"  ✅ [{index}] {title[:70]}")


def save_index():
    """保存文章索引文件"""
    index_path = OUTPUT_DIR / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    # 也生成一个 Markdown 目录
    readme_path = OUTPUT_DIR / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# xiaolinnote.com 面试题合集\n\n")
        f.write(f"> 爬取时间: {datetime.now().isoformat()}\n")
        f.write(f"> 文章数量: {len(all_articles)}\n\n")
        f.write(f"---\n\n")
        f.write(f"## 目录\n\n")
        for i, article in enumerate(all_articles, 1):
            f.write(f"{i}. [{article['title']}]({article['url']})\n")


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════╗
║    xiaolinnote.com AI 面试题 · 全站爬虫        ║
╚══════════════════════════════════════════════════╝
    """)

    # 检查依赖
    try:
        import bs4
    except ImportError:
        print("❌ 缺少依赖，请运行:")
        print("   pip install requests beautifulsoup4")
        print()
        print("   推荐额外安装（获得更好的 Markdown 转换）:")
        print("   pip install markdownify")
        exit(1)

    scrape_site(START_URL)
