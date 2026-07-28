#!/usr/bin/env python3
"""
小林coding 微信公众号文章爬虫
==============================
三种方案:
  A) 从官网 xiaolincoding.com 抓取（无需登录，最稳定，但文章可能不全）
  B) 从搜狗微信搜索抓取（需要手动处理验证码，反爬严格）
  C) 从微信公众号 API 抓取（需要 Cookie，最完整，推荐✨）

使用方法:
  python wechat_scraper_xiaolincoding.py --method A
  python wechat_scraper_xiaolincoding.py --method B
  python wechat_scraper_xiaolincoding.py --method C --cookie "wap_sid2=xxx; wxuin=xxx; ..."

方案 C Cookie 获取:
  1. 微信里打开「小林coding」任意一篇历史文章
  2. 点右上角 "..." → 复制链接 → 发到电脑
  3. 浏览器打开该链接 → F12 → Application → Cookies
  4. 复制 mp.weixin.qq.com 下所有 Cookie，格式: "key1=val1; key2=val2"
"""

import requests
import time
import json
import os
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================
# 通用工具
# ============================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

OUTPUT_DIR = Path("xiaolincoding_articles")
OUTPUT_DIR.mkdir(exist_ok=True)


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()[:100]


def save_article(title: str, url: str, content: str, index: int):
    """保存单篇文章为 Markdown，文件名使用文章标题"""
    safe_title = sanitize_filename(title)
    if not safe_title:
        safe_title = f"article_{index:04d}"

    filename = f"{safe_title}.md"
    filepath = OUTPUT_DIR / filename

    # 如果重名，追加序号
    if filepath.exists():
        stem = safe_title
        counter = 2
        while filepath.exists():
            filename = f"{stem}_{counter}.md"
            filepath = OUTPUT_DIR / filename
            counter += 1

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"> 原文链接: {url}\n\n")
        f.write(f"> 抓取时间: {datetime.now().isoformat()}\n\n")
        f.write("---\n\n")
        f.write(content)

    print(f"  ✅ [{index}] {title}")
    return str(filepath)


def save_metadata(articles: list):
    """保存文章元数据索引"""
    index_path = OUTPUT_DIR / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"\n📋 索引已保存: {index_path} ({len(articles)} 篇)")


# ============================================================
# 方案 A：从小林coding 官网抓取
# ============================================================

def scrape_from_website():
    """
    从 xiaolincoding.com 抓取所有文章。
    该网站是作者将公众号文章整理后的在线版本，内容与公众号一致。
    """
    print("=" * 60)
    print("方案 A: 从官网 xiaolincoding.com 抓取")
    print("=" * 60)

    # 网站的主要页面
    urls_to_try = [
        "https://www.xiaolincoding.com/",
        "https://www.xiaolincoding.com/interview/",
        "https://www.xiaolincoding.com/network/",
        "https://www.xiaolincoding.com/os/",
        "https://www.xiaolincoding.com/mysql/",
        "https://www.xiaolincoding.com/redis/",
    ]

    articles = []
    index = 0

    for page_url in urls_to_try:
        try:
            print(f"\n🌐 访问: {page_url}")
            resp = SESSION.get(page_url, timeout=30)
            resp.raise_for_status()

            # 提取 Markdown 链接 [title](url)
            md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', resp.text)
            for title, link in md_links:
                if link.startswith("http") and "xiaolincoding" in link:
                    articles.append({
                        "title": title.strip(),
                        "url": link,
                        "source": "website"
                    })

            # 也提取 HTML 链接
            html_links = re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
                resp.text
            )
            for link, title in html_links:
                if "xiaolincoding" in link and title.strip():
                    articles.append({
                        "title": title.strip(),
                        "url": link,
                        "source": "website"
                    })

        except Exception as e:
            print(f"  ⚠️ 访问失败: {e}")
            continue

    # 去重
    seen = set()
    unique_articles = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique_articles.append(a)

    print(f"\n📊 共发现 {len(unique_articles)} 篇文章")

    # 下载每篇文章
    for i, article in enumerate(unique_articles, 1):
        try:
            resp = SESSION.get(article["url"], timeout=30)
            resp.raise_for_status()

            # 简单的 HTML to text 转换
            text = resp.text
            # 移除 script/style
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            # 提取 body 内容
            body_match = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL)
            content = body_match.group(1) if body_match else text
            # 基本标签清理
            content = re.sub(r'<[^>]+>', '\n', content)
            content = re.sub(r'\n{3,}', '\n\n', content)

            save_article(article["title"], article["url"], content[:50000], i)
            time.sleep(0.5)  # 礼貌延迟

        except Exception as e:
            print(f"  ❌ [{i}] 下载失败: {e}")

    save_metadata(unique_articles)
    return unique_articles


# ============================================================
# 方案 B：从搜狗微信搜索抓取
# ============================================================

def scrape_from_sogou():
    """
    从搜狗微信搜索 (weixin.sogou.com) 抓取。
    注意: 搜狗有较严格的反爬，可能需要手动处理验证码。
    如果遇到验证码，需要在浏览器中手动完成验证，然后复制 Cookie。
    """
    print("=" * 60)
    print("方案 B: 从搜狗微信搜索抓取")
    print("=" * 60)
    print("⚠️  搜狗微信搜索反爬严格，可能需要手动处理验证码")
    print("    如果失败，建议使用方案 A 或方案 C\n")

    # Step 1: 搜索公众号
    search_url = "https://weixin.sogou.com/weixin"
    params = {
        "type": 1,  # 搜索公众号
        "query": "小林coding",
        "ie": "utf8",
    }

    print("🔍 搜索公众号...")
    resp = SESSION.get(search_url, params=params, timeout=30)

    if "请输入验证码" in resp.text or "验证码" in resp.text:
        print("❌ 遇到验证码！请手动在浏览器访问:")
        print(f"   {search_url}?type=1&query=小林coding&ie=utf8")
        print("   完成验证后，将 Cookie 粘贴到这里，或使用 --cookie 参数重新运行")
        return []

    # 提取公众号主页链接
    account_link = re.search(
        r'href="([^"]*weixin\.sogou\.com[^"]*)"[^>]*>.*?小林coding.*?</a>',
        resp.text, re.DOTALL
    )

    if not account_link:
        # 尝试另一种模式
        account_link = re.search(
            r'href="([^"]+)"[^>]*>\s*<img[^>]*>.*?小林coding',
            resp.text, re.DOTALL
        )

    if not account_link:
        print("❌ 未找到公众号链接，可能遇到验证码")
        with open("sogou_debug.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("   响应已保存至 sogou_debug.html 供调试")
        return []

    profile_url = account_link.group(1)
    print(f"✅ 找到公众号主页: {profile_url}")

    # Step 2: 获取文章列表
    print("📋 获取文章列表...")
    resp = SESSION.get(profile_url, timeout=30)

    articles = []
    # 搜狗文章列表通常在 class="news-box" 或类似结构中
    article_pattern = re.findall(
        r'<a[^>]*href="([^"]*mp\.weixin\.qq\.com[^"]*)"[^>]*>(.*?)</a>',
        resp.text, re.DOTALL
    )

    for url, title_html in article_pattern:
        title = re.sub(r'<[^>]+>', '', title_html).strip()
        if title:
            articles.append({"title": title, "url": url, "source": "sogou"})

    print(f"📊 从当前页发现 {len(articles)} 篇文章")

    # 保存
    for i, article in enumerate(articles, 1):
        try:
            resp = SESSION.get(article["url"], timeout=30)
            text = resp.text
            # 提取文章内容
            content_match = re.search(
                r'id="js_content"[^>]*>(.*?)</div>',
                text, re.DOTALL
            )
            content = content_match.group(1) if content_match else text
            content = re.sub(r'<[^>]+>', '\n', content)
            content = re.sub(r'\n{3,}', '\n\n', content)

            save_article(article["title"], article["url"], content[:50000], i)
            time.sleep(1)
        except Exception as e:
            print(f"  ❌ [{i}] 下载失败: {e}")

    save_metadata(articles)
    return articles


# ============================================================
# 方案 C：通过微信公众平台 profile API 抓取（需 Cookie）
# ============================================================

def scrape_from_wechat_mp(cookie: str):
    """
    通过微信公众号 profile_ext 接口抓取任意公众号的全部历史文章。
    相比方案 B（搜狗），此方案更稳定，反爬限制少。

    获取 Cookie 的方法（任选一种）:

    方法1（推荐）：从微信文章页面获取
      1. 微信里打开「小林coding」任意一篇文章
      2. 点右上角 "..." → "复制链接" → 发到电脑
      3. 在电脑浏览器打开该链接
      4. F12 → Application → Cookies → mp.weixin.qq.com
      5. 复制所有 Cookie 的 name=value 串，格式: "name1=val1; name2=val2"

    方法2：从微信公众号后台获取
      1. 浏览器打开 https://mp.weixin.qq.com
      2. 微信扫码登录（你自己的账号即可，不需要是小林coding的）
      3. F12 → Application → Cookies → 复制所有 Cookie

    需要的关键 Cookie 字段：wap_sid2, wxuin, appmsg_token, pass_ticket
    """
    print("=" * 60)
    print("方案 C: 微信公众号 profile API 抓取（最完整）")
    print("=" * 60)

    # 设置 Cookie
    cookie_dict = {}
    for item in cookie.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookie_dict[k.strip()] = v.strip()

    SESSION.cookies.update(cookie_dict)

    BIZ_ID = "MzI1MjQ3MzU1Nw=="  # 小林coding 的 biz ID

    articles = []
    total_collected = 0

    # ================================================================
    # 第一步：通过 profile_ext getmsg 接口获取文章列表
    # 这是微信公众号历史文章列表的官方前端接口
    # ================================================================

    print("\n🔑 验证 Cookie...")
    test_url = f"https://mp.weixin.qq.com/mp/profile_ext?action=getmsg&__biz={BIZ_ID}&f=json&offset=0&count=1&is_ok=1"

    try:
        resp = SESSION.get(test_url, timeout=30)
        data = resp.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"❌ 请求失败: {e}")
        print("\n💡 可能的原因和解决方案:")
        print("   1. Cookie 已过期 → 重新获取")
        print("   2. 缺少关键 Cookie 字段（wap_sid2, pass_ticket 等）")
        print("   3. 网络环境问题，尝试使用代理")
        print("\n   请参考上面的 Cookie 获取方法，确保包含以下关键字段:")
        print("   wap_sid2, wxuin, appmsg_token, pass_ticket, devicetype")
        return []

    ret = data.get("base_resp", {}).get("ret", -1)
    if ret == -3 or ret == 302:
        print("❌ Cookie 已失效（ret=-3/302），需要重新获取")
        return []
    elif ret == 0 or ret == 200013:
        # 200013 表示 offset 超出范围，即没有更多文章
        # 0 表示请求成功
        print("✅ Cookie 验证成功！")
    else:
        print(f"⚠️  API 返回 ret={ret}，尝试继续...")
        err_msg = data.get("base_resp", {}).get("err_msg", "")
        if err_msg:
            print(f"   错误信息: {err_msg}")

    # ================================================================
    # 第二步：轮询获取所有文章
    # ================================================================

    print(f"\n📥 开始获取文章列表...")
    offset = 0
    count = 10  # 每次获取数量（5-10 较安全）
    max_pages = 2000  # 安全上限（防止无限循环）

    for page in range(max_pages):
        list_url = (
            f"https://mp.weixin.qq.com/mp/profile_ext?"
            f"action=getmsg&__biz={BIZ_ID}&f=json"
            f"&offset={offset}&count={count}&is_ok=1"
        )

        try:
            resp = SESSION.get(list_url, timeout=30)
            data = resp.json()
        except Exception as e:
            print(f"❌ 请求失败 (offset={offset}): {e}")
            break

        ret = data.get("base_resp", {}).get("ret", -1)
        if ret == 200013:
            # 已到达最后一页
            print("✅ 已到达最后一页")
            break
        elif ret != 0:
            print(f"⚠️  API 错误 (ret={ret})，停止")
            err_msg = data.get("base_resp", {}).get("err_msg", "")
            if err_msg:
                print(f"   错误信息: {err_msg}")
            break

        # 解析文章列表
        msg_list = data.get("general_msg_list")
        if not msg_list:
            print("⚠️  空响应，停止")
            break

        try:
            msg_data = json.loads(msg_list)
            msg_items = msg_data.get("list", [])
        except json.JSONDecodeError:
            print("⚠️  解析文章列表失败")
            break

        if not msg_items:
            print("✅ 没有更多文章了")
            break

        for item in msg_items:
            # 文章信息在 comm_msg_info 和 app_msg_ext_info 中
            comm_info = item.get("comm_msg_info", {})
            app_msg = item.get("app_msg_ext_info", {})

            # 主文章
            title = app_msg.get("title", "")
            content_url = app_msg.get("content_url", "")
            digest = app_msg.get("digest", "")
            create_time = comm_info.get("datetime", 0)

            if title and content_url:
                # 微信 API 返回的 content_url 缺少协议头
                if content_url.startswith("//"):
                    content_url = "https:" + content_url
                elif not content_url.startswith("http"):
                    content_url = "https://mp.weixin.qq.com" + content_url

                articles.append({
                    "title": title.replace("\\n", "").strip(),
                    "url": content_url,
                    "digest": digest.replace("\\n", "").strip(),
                    "create_time": datetime.fromtimestamp(create_time).isoformat()
                        if create_time else "未知",
                    "source": "wechat_mp",
                    "is_multi": app_msg.get("is_multi", 0),
                })
                total_collected += 1
                print(f"  📄 [{total_collected}] {title[:60]}")

            # 多图文消息的子文章
            if app_msg.get("is_multi", 0) == 1:
                for sub in app_msg.get("multi_app_msg_item_list", []):
                    sub_title = sub.get("title", "")
                    sub_url = sub.get("content_url", "")
                    if sub_title and sub_url:
                        if sub_url.startswith("//"):
                            sub_url = "https:" + sub_url
                        elif not sub_url.startswith("http"):
                            sub_url = "https://mp.weixin.qq.com" + sub_url

                        articles.append({
                            "title": sub_title.replace("\\n", "").strip(),
                            "url": sub_url,
                            "digest": sub.get("digest", "").replace("\\n", "").strip(),
                            "create_time": datetime.fromtimestamp(create_time).isoformat()
                                if create_time else "未知",
                            "source": "wechat_mp",
                            "is_multi": 0,
                        })
                        total_collected += 1
                        print(f"  📄 [{total_collected}] [多图] {sub_title[:55]}")

        # 更新 offset 为下一条的起始位置
        next_offset = data.get("next_offset", -1)
        if next_offset == -1 or next_offset == offset:
            # 如果 next_offset 没变化，手动 +count
            offset += count
        else:
            offset = next_offset

        print(f"    当前已收集 {total_collected} 篇，offset={offset}，继续...")
        time.sleep(1.5 + (1 if page % 10 == 0 else 0))  # 每10页多停1秒

    print(f"\n✅ 共发现 {total_collected} 篇文章")

    # ================================================================
    # 第三步：下载每篇文章的完整正文
    # ================================================================

    print(f"\n📝 开始下载文章正文（共 {len(articles)} 篇）...\n")

    for i, article in enumerate(articles, 1):
        try:
            resp = SESSION.get(article["url"], timeout=30,
                             headers={"Referer": "https://mp.weixin.qq.com/"})

            # 提取 rich_media_content 或 js_content
            content_match = re.search(
                r'id="(?:js_content|rich_media_content)"[^>]*>(.*?)</div>\s*(?:<script|</div>)',
                resp.text, re.DOTALL
            )

            if content_match:
                content = content_match.group(1)
                # 恢复懒加载的图片
                content = re.sub(
                    r'<img[^>]+data-src="([^"]+)"[^>]*>',
                    r'\n![图片](\1)\n', content
                )
                # 清理 HTML 标签
                content = re.sub(r'<br\s*/?>', '\n', content)
                content = re.sub(r'<p[^>]*>', '\n', content)
                content = re.sub(r'</p>', '\n', content)
                content = re.sub(r'</?section[^>]*>', '\n', content)
                content = re.sub(r'</?span[^>]*>', '', content)
                content = re.sub(r'<[^>]+>', '', content)
                # 恢复 HTML 实体
                content = re.sub(r'&nbsp;', ' ', content)
                content = re.sub(r'&amp;', '&', content)
                content = re.sub(r'&lt;', '<', content)
                content = re.sub(r'&gt;', '>', content)
                content = re.sub(r'&quot;', '"', content)
                content = re.sub(r'&#39;', "'", content)
                # 压缩空行
                content = re.sub(r'\n{3,}', '\n\n', content)
                content = content.strip()
            else:
                content = f"(未能提取正文，请查看原文)\n\n{resp.text[:2000]}"

            save_article(article["title"], article["url"], content, i)
            time.sleep(1)

        except Exception as e:
            print(f"  ❌ [{i}] 下载失败: {e}")

    save_metadata(articles)
    return articles


# ============================================================
# 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="小林coding 微信公众号文章爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python wechat_scraper.py --method A              # 从官网抓取
  python wechat_scraper.py --method C --cookie "xxx"  # 微信平台完整抓取

获取微信公众号 Cookie:
  1. 打开浏览器访问 https://mp.weixin.qq.com
  2. 微信扫码登录
  3. F12 → Application → Cookies → 复制所有 Cookie
        """
    )
    parser.add_argument(
        "--method", choices=["A", "B", "C"], default="A",
        help="抓取方式: A=官网, B=搜狗搜索, C=微信平台(需Cookie)"
    )
    parser.add_argument(
        "--cookie", type=str, default="",
        help="微信公众号平台的 Cookie (方案 C 需要)"
    )

    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════╗
║       小林coding 微信公众号 · 文章爬虫              ║
╚══════════════════════════════════════════════════════╝
    """)

    if args.method == "A":
        scrape_from_website()
    elif args.method == "B":
        scrape_from_sogou()
    elif args.method == "C":
        if not args.cookie:
            print("❌ 方案 C 需要提供 --cookie 参数")
            print("   获取方式: 浏览器登录 mp.weixin.qq.com → F12 → 复制 Cookie")
            return
        scrape_from_wechat_mp(args.cookie)

    print(f"\n✨ 所有文章已保存到: {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
