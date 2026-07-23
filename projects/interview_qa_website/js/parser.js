/**
 * 题库解析器 — 从 GitHub Raw 加载 interview/汇总/ 下 10 个分类文件
 */
const Parser = (() => {
  const BASE =
    'https://raw.githubusercontent.com/lxy1553/ai-transition/main/interview/%E6%B1%87%E6%80%BB/';

  // 分类文件名（GitHub URL 编码）
  const CATEGORIES = [
    'RAG%20%E6%A3%80%E7%B4%A2%E5%A2%9E%E5%BC%BA%E7%94%9F%E6%88%90.md',
    'Agent%20%E6%99%BA%E8%83%BD%E4%BD%93.md',
    '%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%B7%A5%E7%A8%8B%E4%B8%8E%E8%AE%AD%E7%BB%83.md',
    '%E7%BB%BC%E5%90%88.md',
    'NL2SQL%20%E8%87%AA%E7%84%B6%E8%AF%AD%E8%A8%80%E6%9F%A5%E8%AF%A2.md',
    'AI%20%E5%BA%94%E7%94%A8%E5%B7%A5%E7%A8%8B%E5%8C%96.md',
    '%E6%95%B0%E6%8D%AE%E4%BB%93%E5%BA%93%E4%B8%8E%E6%B2%BB%E7%90%86.md',
    '%E4%BF%A1%E8%B4%B7%E9%A3%8E%E6%8E%A7%E5%BB%BA%E6%A8%A1.md',
    'Claude%20Code%20%E5%BC%80%E5%8F%91%E5%AE%9E%E6%88%98.md',
    'MCP%20%E5%B7%A5%E5%85%B7%E8%B0%83%E7%94%A8%E4%B8%8E%E5%8D%8F%E8%AE%AE.md'
  ];

  // ---- 缓存 -----------------------------------------------------------

  function cacheKey(url) {
    return 'qa_cache_' + btoa(url).slice(0, 32);
  }

  async function fetchText(url, force) {
    if (!force) {
      const cached = localStorage.getItem(cacheKey(url));
      if (cached) {
        try {
          const data = JSON.parse(cached);
          if (Date.now() - data.ts < 7 * 24 * 60 * 60 * 1000) return data.text;
        } catch (_) { /* ignore */ }
      }
    }
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);
    const text = await resp.text();
    localStorage.setItem(cacheKey(url), JSON.stringify({ ts: Date.now(), text }));
    return text;
  }

  function getCacheTime(url) {
    try {
      return JSON.parse(localStorage.getItem(cacheKey(url)) || '{}').ts || 0;
    } catch (_) { return 0; }
  }

  // ---- 解析单个分类文件 -----------------------------------------------

  function parseCategoryFile(text, filename) {
    const questions = [];

    // 提取 frontmatter category
    const fmMatch = text.match(/^category:\s*(.+)$/m);
    const category = fmMatch ? fmMatch[1].trim() : filename.replace('.md', '');

    // 按 ## N. 题目 分割
    const re = /^## (\d+)\. (.+)$/gm;
    const matches = [...text.matchAll(re)];

    for (let i = 0; i < matches.length; i++) {
      const num = matches[i][1];
      const title = matches[i][2].trim();
      const start = matches[i].index + matches[i][0].length;
      const end = i + 1 < matches.length ? matches[i + 1].index : text.length;
      let answer = text.slice(start, end).trim();

      // 清理 > ID / > 📚 / > 来源 等元数据行
      answer = answer.replace(/^> .*\n?/gm, '');
      answer = answer.replace(/\n---\s*$/, '');
      answer = answer.trim();

      if (answer.length < 50) continue;

      // 难度判定
      let difficulty = 'medium';
      if (/RAG|Agent|大模型工程|信贷/.test(category)) difficulty = 'hard';
      else if (/综合|Claude/.test(category)) difficulty = 'easy';

      // 标签
      const tags = [category];

      questions.push({
        id: `M${questions.length + 1}`,
        source: 'merged',
        category,
        title,
        answer,
        difficulty,
        importance: difficulty === 'hard' ? 5 : difficulty === 'medium' ? 4 : 3,
        frequency: '',
        day: '',
        tags
      });
    }

    return questions;
  }

  // ---- 公开 API -------------------------------------------------------

  async function loadAll(force) {
    const urls = CATEGORIES.map(f => BASE + f);
    const texts = await Promise.all(urls.map(u => fetchText(u, force)));

    const all = [];
    for (let i = 0; i < texts.length; i++) {
      const qs = parseCategoryFile(texts[i], decodeURIComponent(CATEGORIES[i]));
      all.push(...qs);
    }

    // 重新分配 ID
    all.forEach((q, i) => { q.id = `M${String(i + 1).padStart(3, '0')}`; });

    const times = urls.map(u => getCacheTime(u));
    const cacheTime = Math.min(...times) || Date.now();

    return { questions: all, cacheTime };
  }

  return { loadAll, getCacheTime };
})();
