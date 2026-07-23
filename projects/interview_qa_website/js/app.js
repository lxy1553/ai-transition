/**
 * 面试题网站主逻辑
 *
 * 功能：
 *  - 页面初始化，从 GitHub 加载题库
 *  - 浏览模式：分类树 + 列表 + 搜索 + 筛选
 *  - 顺序练习 / 随机练习 / 错题集
 *  - Markdown 渲染（marked + highlight.js + KaTeX）
 */

const App = (() => {
  // 当前模式: 'browse' | 'sequential' | 'random' | 'wrong'
  let mode = 'browse';
  let currentFilters = {};
  let randomQueue = [];       // 随机模式剩余题目
  let currentQuestion = null; // 当前展示的单题

  // ---- DOM 引用 ---------------------------------------------------------

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ---- 初始化 -----------------------------------------------------------

  async function init() {
    showLoading(true);
    try {
      const result = await Parser.loadAll();
      Store.init(result.questions);
      renderAll();
      bindEvents();
      updateCacheTime(result.cacheTime);
      // Ctrl+K 聚焦搜索
      document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
          e.preventDefault();
          $('#search-input').focus();
        }
      });
    } catch (err) {
      $('#loading-msg').textContent = '加载失败：' + err.message +
        '\n请确认题库文件已推送到 GitHub，或检查网络连接。';
    }
    showLoading(false);
  }

  async function refreshQuestions() {
    const btn = $('#btn-refresh');
    btn.textContent = '⏳ 刷新中…';
    btn.disabled = true;
    try {
      const result = await Parser.loadAll(true);
      Store.init(result.questions);
      renderAll();
      updateCacheTime(result.cacheTime);
    } catch (err) {
      alert('刷新失败：' + err.message);
    }
    btn.textContent = '🔄 刷新题库';
    btn.disabled = false;
  }

  function updateCacheTime(ts) {
    const d = new Date(ts);
    $('#cache-time').textContent = d.toLocaleString('zh-CN');
  }

  function showLoading(show) {
    $('#loading-overlay').style.display = show ? 'flex' : 'none';
  }

  // ---- 渲染 -------------------------------------------------------------

  function renderAll() {
    renderStats();
    renderCategoryTree();
    renderQuestionList();
  }

  // 侧边栏统计
  function renderStats() {
    const s = Store.getStats();
    $('#stat-total').textContent = s.total;
    $('#stat-hard').textContent = s.hard;
    $('#stat-medium').textContent = s.medium;
    $('#stat-easy').textContent = s.easy;
    $('#stat-wrong').textContent = s.wrong;
  }

  // 分类树
  function renderCategoryTree() {
    const cats = Store.getCategories();
    const el = $('#category-tree');
    el.innerHTML = '';

    // "全部"选项
    const allItem = ce('div', { class: 'cat-item active', 'data-cat': '' }, '全部题目');
    el.appendChild(allItem);

    for (const cat of cats) {
      const div = ce('div', { class: 'cat-item', 'data-cat': cat.name });
      div.innerHTML = `<span>${cat.name}</span><span class="cat-count">${cat.count}</span>`;
      el.appendChild(div);
    }
  }

  // 题目列表
  function renderQuestionList(questions) {
    const list = questions || Store.filter(currentFilters);
    const el = $('#question-list');
    const countEl = $('#result-count');

    if (list.length === 0) {
      el.innerHTML = '<div class="empty-state">没有匹配的题目，试试调整筛选条件</div>';
      countEl.textContent = '0 题';
      return;
    }

    countEl.textContent = list.length + ' 题';
    el.innerHTML = list.map(q => renderQuestionCard(q)).join('');
  }

  // 单题卡片 HTML
  function renderQuestionCard(q) {
    const diffLabel = { easy: '简单', medium: '中等', hard: '困难' };
    const diffClass = q.difficulty;
    const isW = Store.isWrong(q.id);
    const sourceLabel = q.category;
    const prevAnswer = Store.getUserAnswer(q.id);

    return `
      <div class="q-card" data-id="${q.id}" data-source="${q.source}" data-diff="${q.difficulty}" data-cat="${q.category}">
        <div class="q-header">
          <span class="q-id">${q.id}</span>
          <span class="q-badge difficulty-${diffClass}">${diffLabel[q.difficulty]}</span>
          <span class="q-badge source-${q.source}">${sourceLabel}</span>
          ${q.importance ? `<span class="q-badge importance">P${q.importance-2 > 0 ? q.importance-2 : 0} ${q.importance}/5</span>` : ''}
          ${isW ? '<span class="q-badge wrong-mark">错题</span>' : ''}
          <span class="q-tags">${(q.tags || []).slice(0, 3).map(t => `<span class="tag">${t}</span>`).join('')}</span>
        </div>
        <div class="q-title">${escapeHtml(q.title)}</div>
        ${q.day ? `<div class="q-meta">📅 ${q.day}</div>` : ''}
        <div class="q-user-section">
          <div class="q-user-label">✍️ 我的回答</div>
          <textarea class="q-user-input" placeholder="在此输入你的回答…">${prevAnswer ? escapeHtml(prevAnswer.answer) : ''}</textarea>
          <div class="q-user-display" style="display:none">
            <div class="q-user-label">✍️ 你的回答</div>
            <div class="q-user-content"></div>
          </div>
        </div>
        <div class="q-answer markdown-body" style="display:none"></div>
        <div class="q-ai-eval" style="display:none"></div>
        <div class="q-actions">
          <button class="btn-expand">展开答案 ▼</button>
        </div>
      </div>`;
  }

  // ---- 浏览模式事件 -----------------------------------------------------

  function bindEvents() {
    // 搜索框
    $('#search-input').addEventListener('input', debounce(() => {
      currentFilters.keyword = $('#search-input').value.trim() || null;
      mode = 'browse';
      renderQuestionList();
      updateModeBtns();
    }, 200));

    // 来源筛选
    $('#filter-source').addEventListener('change', () => {
      currentFilters.source = $('#filter-source').value || null;
      renderQuestionList();
    });

    // 难度筛选
    $('#filter-difficulty').addEventListener('change', () => {
      currentFilters.difficulty = $('#filter-difficulty').value || null;
      renderQuestionList();
    });

    // 分类树点击
    $('#category-tree').addEventListener('click', e => {
      const item = e.target.closest('.cat-item');
      if (!item) return;
      $$('#category-tree .cat-item').forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      currentFilters.category = item.dataset.cat || null;
      mode = 'browse';
      renderQuestionList();
      updateModeBtns();
    });

    // 题目列表点击（展开/收起答案）
    $('#question-list').addEventListener('click', e => {
      const card = e.target.closest('.q-card');
      if (!card) return;

      const btn = e.target.closest('.btn-expand');
      const answerEl = card.querySelector('.q-answer');
      const userInput = card.querySelector('.q-user-input');
      const userDisplay = card.querySelector('.q-user-display');
      const userContent = card.querySelector('.q-user-content');
      const aiEval = card.querySelector('.q-ai-eval');

      if (btn && answerEl) {
        const isHidden = answerEl.style.display === 'none';
        if (isHidden) {
          const id = card.dataset.id;
          // 保存并展示用户回答
          if (userInput && userInput.value.trim()) {
            Store.saveUserAnswer(id, userInput.value);
            userContent.textContent = userInput.value.trim();
            userDisplay.style.display = 'block';
          }
          // 懒渲染参考答案
          if (!answerEl.dataset.rendered) {
            const q = Store.getById(id);
            if (q) {
              answerEl.innerHTML = renderMarkdown(q.answer);
              answerEl.dataset.rendered = '1';
            }
          }
          answerEl.style.display = 'block';
          btn.textContent = '收起答案 ▲';
          btn.classList.add('expanded');
          // AI评价按钮：始终显示
          if (aiEval) {
            aiEval.style.display = 'block';
            aiEval.innerHTML = `<button class="btn-ai-eval" data-qid="${id}">🤖 AI 评价我的回答</button>`;
          }
        } else {
          answerEl.style.display = 'none';
          if (userDisplay) userDisplay.style.display = 'none';
          if (aiEval) aiEval.style.display = 'none';
          btn.textContent = '展开答案 ▼';
          btn.classList.remove('expanded');
        }
      }

      // AI 评价按钮
      if (e.target.closest('.btn-ai-eval')) {
        const qid = e.target.closest('.btn-ai-eval').dataset.qid;
        triggerAiEval(card, qid);
      }
    });

    // 模式切换按钮
    $('#btn-browse').addEventListener('click', () => switchMode('browse'));
    $('#btn-sequential').addEventListener('click', () => switchMode('sequential'));
    $('#btn-random').addEventListener('click', () => switchMode('random'));
    $('#btn-wrong').addEventListener('click', () => switchMode('wrong'));

    // 练习模式的题目操作
    $('#practice-area').addEventListener('click', e => {
      const btn = e.target.closest('button');
      if (!btn || !currentQuestion) return;
      const id = currentQuestion.id;

      if (btn.classList.contains('btn-mastered')) {
        Store.markQuestion(id, 'mastered');
        nextPracticeQuestion();
      } else if (btn.classList.contains('btn-review')) {
        Store.markQuestion(id, 'review');
        nextPracticeQuestion();
      } else if (btn.classList.contains('btn-skip')) {
        Store.markQuestion(id, 'skip');
        nextPracticeQuestion();
      } else if (btn.classList.contains('btn-show-answer')) {
        // 保存用户的回答
        const userInput = $('#user-answer-input').value;
        if (currentQuestion) {
          Store.saveUserAnswer(currentQuestion.id, userInput);
        }

        // 隐藏输入框
        $('#user-answer-input').style.display = 'none';
        $('#user-answer-section').style.display = 'none';

        // 显示用户回答
        if (userInput && userInput.trim()) {
          $('#user-answer-content').textContent = userInput.trim();
          $('#user-answer-display').style.display = 'block';
        }

        // 渲染参考答案
        const ansEl = $('#practice-answer');
        if (!ansEl.dataset.rendered) {
          ansEl.innerHTML = renderMarkdown(currentQuestion.answer);
          ansEl.dataset.rendered = '1';
        }
        ansEl.style.display = 'block';
        btn.style.display = 'none';
        $('#practice-actions').style.display = 'flex';
      }
    });
  }

  // 模式切换
  function switchMode(newMode) {
    mode = newMode;
    updateModeBtns();

    const browseArea = $('#browse-area');
    const practiceArea = $('#practice-area');

    if (mode === 'browse') {
      browseArea.style.display = 'block';
      practiceArea.style.display = 'none';
      renderQuestionList();
    } else if (mode === 'wrong') {
      browseArea.style.display = 'none';
      practiceArea.style.display = 'block';
      startWrongMode();
    } else if (mode === 'sequential') {
      browseArea.style.display = 'none';
      practiceArea.style.display = 'block';
      startSequentialMode();
    } else if (mode === 'random') {
      browseArea.style.display = 'none';
      practiceArea.style.display = 'block';
      startRandomMode();
    }
  }

  function updateModeBtns() {
    $$('.mode-btn').forEach(b => b.classList.remove('active'));
    const map = { browse: 'btn-browse', sequential: 'btn-sequential', random: 'btn-random', wrong: 'btn-wrong' };
    const btn = $('#' + map[mode]);
    if (btn) btn.classList.add('active');
  }

  // ---- 练习模式 ---------------------------------------------------------

  function showPracticeQuestion(q) {
    currentQuestion = q;
    $('#practice-id').textContent = q.id;
    $('#practice-title').textContent = q.title;
    $('#practice-meta').innerHTML = `
      <span class="q-badge difficulty-${q.difficulty}">${{easy:'简单',medium:'中等',hard:'困难'}[q.difficulty]}</span>
      <span class="q-badge source-${q.source}">${q.category}</span>
      <span class="q-tags">${(q.tags||[]).slice(0,3).map(t=>`<span class="tag">${t}</span>`).join('')}</span>
    `;

    // 重置答案区
    const ansEl = $('#practice-answer');
    ansEl.style.display = 'none';
    ansEl.dataset.rendered = '';
    ansEl.innerHTML = '';

    // 用户作答区
    const prevAnswer = Store.getUserAnswer(q.id);
    const inputEl = $('#user-answer-input');
    inputEl.value = prevAnswer ? prevAnswer.answer : '';
    inputEl.style.display = 'block';
    $('#user-answer-section').style.display = 'block';

    // 用户历史回答展示区
    $('#user-answer-display').style.display = 'none';
    $('#user-answer-content').textContent = '';

    $('#practice-show-btn').style.display = 'inline-block';
    $('#practice-actions').style.display = 'none';
  }

  function nextPracticeQuestion() {
    if (mode === 'sequential') {
      startSequentialMode();
    } else if (mode === 'random') {
      startRandomMode();
    } else if (mode === 'wrong') {
      startWrongMode();
    }
  }

  // 顺序练习
  function startSequentialMode() {
    const questions = Store.filter(currentFilters);
    if (questions.length === 0) {
      $('#practice-area').innerHTML = '<div class="empty-state">当前筛选条件下没有题目</div>';
      return;
    }
    let pos = Store.loadSequentialPos();
    if (pos >= questions.length) pos = 0; // 循环
    const q = questions[pos];
    Store.saveSequentialPos(pos + 1);
    showPracticeQuestion(q);
    updatePracticeProgress(pos + 1, questions.length);
  }

  // 随机练习
  function startRandomMode() {
    if (randomQueue.length === 0) {
      // 重新洗牌
      const questions = Store.filter(currentFilters);
      if (questions.length === 0) {
        $('#practice-area').innerHTML = '<div class="empty-state">当前筛选条件下没有题目</div>';
        return;
      }
      randomQueue = shuffle([...questions]);
    }
    const q = randomQueue.pop();
    const questions = Store.filter(currentFilters);
    showPracticeQuestion(q);
    updatePracticeProgress(questions.length - randomQueue.length, questions.length);
  }

  // 错题模式
  function startWrongMode() {
    const questions = Store.getWrongQuestions();
    if (questions.length === 0) {
      $('#practice-area').innerHTML = `
        <div class="empty-state" style="text-align:center;padding:60px;">
          <div style="font-size:48px;">🎉</div>
          <p>错题集为空，继续保持！</p>
          <button class="btn btn-primary" onclick="App.switchMode('browse')">去浏览题目</button>
        </div>`;
      return;
    }
    // 按顺序展示错题
    const q = questions[0]; // 取第一个
    showPracticeQuestion(q);
    updatePracticeProgress(1, questions.length);
  }

  function updatePracticeProgress(cur, total) {
    $('#practice-progress').textContent = `${cur} / ${total}`;
  }

  // ---- Markdown 渲染 ----------------------------------------------------

  function renderMarkdown(text) {
    // 预处理：清理文本
    let md = text || '';

    // 使用 marked 渲染（如果已加载）
    if (typeof marked !== 'undefined') {
      // 配置 marked
      if (!marked.getDefaults) {
        marked.setOptions = marked.setOptions || (() => {});
      }
      try {
        // 处理 KaTeX 数学公式：保护 $...$ 和 $$...$$
        md = md.replace(/\$\$([\s\S]*?)\$\$/g, (_, formula) => {
          return '<div class="math-block">' + (typeof katex !== 'undefined' ?
            katex.renderToString(formula.trim(), { throwOnError: false, displayMode: true }) :
            '$$' + formula + '$$') + '</div>';
        });
        md = md.replace(/\$([^\$]+?)\$/g, (_, formula) => {
          return typeof katex !== 'undefined' ?
            katex.renderToString(formula.trim(), { throwOnError: false, displayMode: false }) :
            '$' + formula + '$';
        });

        let html = marked.parse(md);
        return html;
      } catch (_) { /* fallback */ }
    }

    // 降级：基本 Markdown → HTML
    return basicMarkdownToHtml(md);
  }

  function basicMarkdownToHtml(text) {
    let html = text;
    // 代码块 ```
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g,
      (_, lang, code) => `<pre><code class="language-${lang}">${escapeHtml(code.trim())}</code></pre>`);
    // 行内代码 `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // 粗体 **text**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // 斜体 *text*
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // 标题 ###
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    // 无序列表
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    // 有序列表
    html = html.replace(/^\d+\)\s(.+)$/gm, '<li>$1</li>');
    // 段落：空行分隔
    const parts = html.split(/\n{2,}/);
    html = parts.map(p => {
      p = p.trim();
      if (!p) return '';
      if (p.startsWith('<h') || p.startsWith('<pre') || p.startsWith('<ul') || p.startsWith('<table')) return p;
      return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
    }).join('\n');

    return html;
  }

  // ---- 工具函数 ---------------------------------------------------------

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function ce(tag, attrs, text) {
    const el = document.createElement(tag);
    if (attrs) Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    if (text) el.textContent = text;
    return el;
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
  }

  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  // ---- AI 评价 (DeepSeek) -----------------------------------------------

  async function triggerAiEval(card, qid) {
    const userAnswer = card.querySelector('.q-user-content').textContent || '';
    if (!userAnswer.trim()) {
      const aiEval = card.querySelector('.q-ai-eval');
      aiEval.innerHTML = '<div class="ai-eval-error">请先在「我的回答」中输入你的答案，再点击 AI 评价。</div>';
      return;
    }

    const apiKey = localStorage.getItem('qa_deepseek_key');
    if (!apiKey) {
      showApiKeyPrompt(card, qid);
      return;
    }

    const aiEval = card.querySelector('.q-ai-eval');
    aiEval.innerHTML = '<div class="ai-eval-loading">🤖 AI 正在评价中…</div>';

    const q = Store.getById(qid);
    if (!q) return;

    const refAnswer = (card.querySelector('.q-answer')?.textContent || '').slice(0, 2000);

    try {
      const resp = await fetch('https://api.deepseek.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: 'deepseek-chat',
          messages: [
            { role: 'system', content: '你是一位资深面试官。请用中文按以下结构分步骤评价用户的面试回答：\n\n【知识点覆盖】\n- 用户是否覆盖了这道题的核心知识点？遗漏了哪些？\n\n【表述准确性】\n- 关键概念是否表述准确？有无明显错误？\n\n【改进建议】\n- 具体建议用户补充或修正什么内容。\n\n最后给出 1-10 分的评分。评价字数在 100-200 字之间，语气客观、有建设性。' },
            { role: 'user', content: `【面试题】${q.title}\n【参考答案】${refAnswer}\n【我的回答】${userAnswer}\n\n请按上面的结构评价我的回答。` }
          ],
          temperature: 0.3,
          max_tokens: 800
        })
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error.message || 'API错误');
      const evalText = data.choices?.[0]?.message?.content || '评价失败，请重试';
      aiEval.innerHTML = `<div class="ai-eval-result"><strong>🤖 AI 评价</strong><div class="ai-eval-body">${escapeHtml(evalText).replace(/\n/g, '<br>')}</div></div>`;
    } catch (err) {
      aiEval.innerHTML = `<div class="ai-eval-error">评价失败：${escapeHtml(err.message)}</div>`;
    }
  }

  function showApiKeyPrompt(card, qid) {
    const aiEval = card.querySelector('.q-ai-eval');
    aiEval.style.display = 'block';
    aiEval.innerHTML = `
      <div class="ai-eval-settings">
        <p>需要 DeepSeek API Key 才能使用 AI 评价（<a href="https://platform.deepseek.com/api_keys" target="_blank">获取 Key</a>）</p>
        <div style="display:flex;gap:8px;margin-top:8px;">
          <input type="password" class="api-key-input" placeholder="粘贴 API Key…" style="flex:1;padding:6px 10px;border:1px solid var(--border);border-radius:4px;">
          <button class="btn-save-key" style="padding:6px 12px;background:var(--primary);color:#fff;border:none;border-radius:4px;cursor:pointer;">保存</button>
        </div>
      </div>`;
    // 绑定保存事件
    const saveBtn = aiEval.querySelector('.btn-save-key');
    const input = aiEval.querySelector('.api-key-input');
    saveBtn.addEventListener('click', () => {
      const key = input.value.trim();
      if (key) {
        localStorage.setItem('qa_deepseek_key', key);
        triggerAiEval(card, qid);
      }
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') saveBtn.click();
    });
  }

  return { init, switchMode, refreshQuestions };
})();

// 页面加载完成后启动
document.addEventListener('DOMContentLoaded', () => App.init());
