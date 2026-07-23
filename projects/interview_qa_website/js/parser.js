/**
 * Markdown 题库解析器
 *
 * 负责从 GitHub Raw 拉取并解析两份 md 文件，输出统一结构的题目数组。
 * 两份文件的格式不同，需要分别解析。
 */

const Parser = (() => {
  // GitHub Raw 地址（发布到 GitHub Pages 后也能拉取最新内容）
  const URL_MIANSHIYA =
    'https://raw.githubusercontent.com/lxy1553/ai-transition/main/docs/mianshiya_llm_interview_questions.md';
  const URL_CORE =
    'https://raw.githubusercontent.com/lxy1553/ai-transition/main/docs/interview_core_questions.md';
  const URL_XIAOLIN =
    'https://raw.githubusercontent.com/lxy1553/ai-transition/main/docs/xiaolinnote_questions.md';

  /**
   * 从 URL 拉取文本，支持本地缓存
   * 缓存 7 天，避免每次打开都重新下载（题库文件较大）
   * force=true 时跳过缓存强制拉取
   */
  async function fetchText(url, force) {
    const cacheKey = 'qa_cache_' + btoa(url).slice(0, 32);
    // 7 天内读缓存（除非强制刷新）
    if (!force) {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        try {
          const data = JSON.parse(cached);
          if (Date.now() - data.ts < 7 * 24 * 60 * 60 * 1000) {
            return data.text;
          }
        } catch (_) { /* ignore */ }
      }
    }
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);
    const text = await resp.text();
    localStorage.setItem(cacheKey, JSON.stringify({ ts: Date.now(), text }));
    return text;
  }

  /**
   * 获取缓存的更新时间
   */
  function getCacheTime(url) {
    try {
      const cacheKey = 'qa_cache_' + btoa(url).slice(0, 32);
      const data = JSON.parse(localStorage.getItem(cacheKey) || '{}');
      return data.ts || 0;
    } catch (_) { return 0; }
  }

  // ---- mianshiya 文件解析 ------------------------------------------------

  function parseMianshiya(text) {
    const questions = [];
    // 按 "### Q" 或 "### 附-" 分割条目
    const blocks = text.split(/\n(?=### (?:Q\d+|附-\d+))/);
    for (const block of blocks) {
      const q = parseMianshiyaBlock(block);
      if (q && q.title) questions.push(q);
    }
    return questions;
  }

  function parseMianshiyaBlock(block) {
    // 提取 ID
    const idMatch = block.match(/###\s+(Q\d+|附-\d+)/);
    if (!idMatch) return null;
    const id = idMatch[1];

    // 提取分类
    const catMatch = block.match(/\*\*分类：\*\*\s*(.+)/);
    const category = catMatch ? catMatch[1].trim() : '其他';

    // 提取题目
    const titleMatch = block.match(/\*\*题目：\*\*\s*(.+)/);
    if (!titleMatch) return null;
    const title = titleMatch[1].trim();

    // 提取参考答案（从 "**参考答案：**" 到下一个 --- 或结尾）
    const answerStart = block.indexOf('**参考答案：**');
    if (answerStart === -1) return null;
    let answer = block.slice(answerStart + '**参考答案：**'.length);

    // 清理答案：去掉尾部多余的分隔线和重复内容
    answer = answer
      .replace(/\n---\s*$/, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    return {
      id,
      source: 'mianshiya',
      category,
      title,
      answer,
      difficulty: 'medium',    // mianshiya 无原始难度，默认中等
      importance: 4,
      frequency: '',
      day: '',
      tags: extractTags(category)
    };
  }

  // ---- interview_core 文件解析 -------------------------------------------

  function parseInterviewCore(text) {
    const questions = [];
    // 按 <a id="q 分割
    const blocks = text.split(/(?=<a id="q\d+">)/);
    for (const block of blocks) {
      const q = parseCoreBlock(block);
      if (q && q.title) questions.push(q);
    }
    return questions;
  }

  function parseCoreBlock(block) {
    // 提取 ID
    const idMatch = block.match(/<a id="(q\d+)">/);
    if (!idMatch) return null;
    const id = idMatch[1].toUpperCase();

    // 提取标题: ## Qxxx：xxxx
    const titleMatch = block.match(/##\s+Q\d+\s*[：:]\s*(.+)/);
    if (!titleMatch) return null;
    const title = titleMatch[1].trim();

    // 提取来源 Day
    const dayMatch = block.match(/来源\s*Day\s*[：:]\s*(.+)/);
    const day = dayMatch ? dayMatch[1].trim() : '';

    // 提取重要程度
    const impMatch = block.match(/重要程度\s*[：:]\s*(\d+)\/5/);
    const importance = impMatch ? parseInt(impMatch[1]) : 4;

    // 提取回答（### 回答 之后的内容）
    const answerStart = block.indexOf('### 回答');
    if (answerStart === -1) return null;
    let answer = block.slice(answerStart + '### 回答'.length);

    // 清理
    answer = answer
      .replace(/\n---\s*$/, '')
      .replace(/\n<a id="[^"]*"><\/a>\s*$/, '')
      .trim();

    // 难度映射
    let difficulty = 'medium';
    if (importance >= 5) difficulty = 'hard';
    else if (importance <= 3) difficulty = 'easy';

    // 从标题推断分类标签
    const tags = inferTagsFromTitle(title, id);

    return {
      id,
      source: 'interview_core',
      category: tags[0] || '综合',
      title,
      answer,
      difficulty,
      importance,
      frequency: '',    // 需从索引表补充
      day,
      tags: tags.slice(0, 4)
    };
  }

  // ---- 辅助函数 ---------------------------------------------------------

  function extractTags(category) {
    // 从分类名拆解标签
    const map = {
      '微调与 PEFT': ['微调', 'PEFT', 'Fine-tuning', 'LoRA'],
      'RAG 检索增强': ['RAG', '检索', 'Embedding', '向量'],
      'Prompt 与结构化输出': ['Prompt', '结构化输出', '护栏'],
      'Agent 与框架': ['Agent', 'LangChain', 'LangGraph', 'ReAct'],
      'MCP 与协议': ['MCP', 'A2A', '协议', 'Function Calling'],
      '工程与场景': ['工程化', '生产', '优化', '架构'],
      '其他': ['综合'],
      '附录': ['附录']
    };
    return map[category] || [category];
  }

  function inferTagsFromTitle(title, id) {
    const tags = [];
    const t = title.toLowerCase();
    if (/rag|检索|召回|chunk|embed|向量|rerank|分块/i.test(t)) tags.push('RAG');
    if (/nl2sql|sql|查询|表|字段|schema|口径/i.test(t)) tags.push('NL2SQL');
    if (/agent|工具|编排|工作流|tool/i.test(t)) tags.push('Agent');
    if (/仓库|ods|dwd|dws|ads|离线|实时|分区/i.test(t)) tags.push('数据仓库');
    if (/微调|peft|lora|fine.tun/i.test(t)) tags.push('微调');
    if (/prompt|提示|结构化/i.test(t)) tags.push('Prompt');
    if (/权限|安全|敏感|脱敏|阻断|拒答/i.test(t)) tags.push('安全');
    if (/服务|api|docker|部署|配置/i.test(t)) tags.push('工程化');
    if (/血缘|指标|告警|监控/i.test(t)) tags.push('治理');
    if (/信贷|风控|授信|放款|还款|逾期/i.test(t)) tags.push('金融信贷');
    if (tags.length === 0) tags.push('综合');
    return tags;
  }

  // ---- xiaolinnote 文件解析 --------------------------------------------

  function parseXiaolin(text) {
    const questions = [];
    const blocks = text.split(/\n(?=### X\d+)/);
    for (const block of blocks) {
      const q = parseMianshiyaBlock(block);
      if (q && q.title) {
        q.source = 'xiaolinnote';
        // 根据分类调整难度
        if (q.category === '大模型工程') q.difficulty = 'hard';
        else if (q.category === 'LLM工具调用与协议') q.difficulty = 'medium';
        else if (q.category === 'Agent图解专栏' || q.category === 'Claude Code图解专栏') q.difficulty = 'easy';
        else q.difficulty = 'medium';
        questions.push(q);
      }
    }
    return questions;
  }

  // ---- 公开 API ---------------------------------------------------------

  /**
   * 拉取并解析所有题库
   * force=true 跳过缓存强制拉取
   * 返回 { questions, cacheTime }，cacheTime 为缓存中最旧的时间戳
   */
  async function loadAll(force) {
    const [text1, text2, text3] = await Promise.all([
      fetchText(URL_MIANSHIYA, force),
      fetchText(URL_CORE, force),
      fetchText(URL_XIAOLIN, force)
    ]);
    const q1 = parseMianshiya(text1);
    const q2 = parseInterviewCore(text2);
    const q3 = parseXiaolin(text3);
    const all = [...q1, ...q2, ...q3];

    const t1 = getCacheTime(URL_MIANSHIYA);
    const t2 = getCacheTime(URL_CORE);
    const t3 = getCacheTime(URL_XIAOLIN);
    const cacheTime = Math.min(t1, t2, t3) || Date.now();

    return { questions: all, cacheTime };
  }

  return { loadAll, URL_MIANSHIYA, URL_CORE, URL_XIAOLIN, getCacheTime };
})();
