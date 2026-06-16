/**
 * 数据状态管理 + localStorage 持久化
 *
 * 职责：
 *  - 题库存储和检索
 *  - 错题集管理（localStorage）
 *  - 练习进度记录（localStorage）
 *  - 分类、难度等元数据统计
 */

const Store = (() => {
  const LS_WRONG = 'qa_wrong_set';        // 错题 ID 集合
  const LS_PROGRESS = 'qa_progress';      // 练习进度 { questionId: 'mastered'|'review'|'skip' }
  const LS_SEQUENTIAL = 'qa_sequential';  // 顺序练习位置
  const LS_ANSWERS = 'qa_user_answers';   // 用户作答 { questionId: { answer, ts } }

  let questions = [];
  let wrongSet = new Set();
  let progress = {};
  let userAnswers = {};

  // ---- 初始化 -----------------------------------------------------------

  function init(allQuestions) {
    questions = allQuestions;
    wrongSet = loadWrongSet();
    progress = loadProgress();
    userAnswers = loadUserAnswers();
  }

  // ---- 错题集 -----------------------------------------------------------

  function loadWrongSet() {
    try {
      const raw = localStorage.getItem(LS_WRONG);
      return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch (_) { return new Set(); }
  }

  function saveWrongSet() {
    localStorage.setItem(LS_WRONG, JSON.stringify([...wrongSet]));
  }

  function addWrong(id) {
    wrongSet.add(id);
    saveWrongSet();
  }

  function removeWrong(id) {
    wrongSet.delete(id);
    saveWrongSet();
  }

  function isWrong(id) {
    return wrongSet.has(id);
  }

  function getWrongQuestions() {
    return questions.filter(q => wrongSet.has(q.id));
  }

  function getWrongCount() {
    return wrongSet.size;
  }

  // ---- 练习进度 ---------------------------------------------------------

  function loadProgress() {
    try {
      const raw = localStorage.getItem(LS_PROGRESS);
      return raw ? JSON.parse(raw) : {};
    } catch (_) { return {}; }
  }

  function saveProgress() {
    localStorage.setItem(LS_PROGRESS, JSON.stringify(progress));
  }

  function markQuestion(id, status) {
    // status: 'mastered' | 'review' | 'skip'
    progress[id] = { status, ts: Date.now() };
    if (status === 'review') {
      addWrong(id);
    } else if (status === 'mastered' && isWrong(id)) {
      removeWrong(id);
    }
    saveProgress();
  }

  function getProgress(id) {
    return progress[id] || null;
  }

  // ---- 顺序练习位置 -----------------------------------------------------

  function saveSequentialPos(index) {
    localStorage.setItem(LS_SEQUENTIAL, String(index));
  }

  function loadSequentialPos() {
    const v = localStorage.getItem(LS_SEQUENTIAL);
    return v ? parseInt(v) : 0;
  }

  // ---- 题库查询 ---------------------------------------------------------

  function getAll() {
    return questions;
  }

  function getById(id) {
    return questions.find(q => q.id === id);
  }

  function getCategories() {
    const cats = {};
    for (const q of questions) {
      const key = q.category;
      if (!cats[key]) cats[key] = { name: key, count: 0, sources: new Set() };
      cats[key].count++;
      cats[key].sources.add(q.source);
    }
    // 排序：题目数多的在前
    return Object.values(cats)
      .map(c => ({ name: c.name, count: c.count, sources: [...c.sources] }))
      .sort((a, b) => b.count - a.count);
  }

  function getStats() {
    const total = questions.length;
    const hard = questions.filter(q => q.difficulty === 'hard').length;
    const medium = questions.filter(q => q.difficulty === 'medium').length;
    const easy = questions.filter(q => q.difficulty === 'easy').length;
    const sources = {};
    for (const q of questions) {
      sources[q.source] = (sources[q.source] || 0) + 1;
    }
    return { total, hard, medium, easy, sources, wrong: wrongSet.size };
  }

  /**
   * 过滤和搜索
   * filters: { keyword, category, source, difficulty }
   */
  function filter(filters = {}) {
    let result = [...questions];
    const f = filters;

    if (f.keyword) {
      const kw = f.keyword.toLowerCase();
      result = result.filter(q =>
        q.title.toLowerCase().includes(kw) ||
        q.answer.toLowerCase().includes(kw) ||
        q.tags.some(t => t.toLowerCase().includes(kw)) ||
        q.category.toLowerCase().includes(kw)
      );
    }
    if (f.category) {
      result = result.filter(q => q.category === f.category);
    }
    if (f.source) {
      result = result.filter(q => q.source === f.source);
    }
    if (f.difficulty) {
      result = result.filter(q => q.difficulty === f.difficulty);
    }
    return result;
  }

  // ---- 用户作答 ---------------------------------------------------------

  function loadUserAnswers() {
    try {
      const raw = localStorage.getItem(LS_ANSWERS);
      return raw ? JSON.parse(raw) : {};
    } catch (_) { return {}; }
  }

  function saveUserAnswers() {
    localStorage.setItem(LS_ANSWERS, JSON.stringify(userAnswers));
  }

  function saveUserAnswer(id, answer) {
    if (!answer || !answer.trim()) return;
    userAnswers[id] = { answer: answer.trim(), ts: Date.now() };
    saveUserAnswers();
  }

  function getUserAnswer(id) {
    return userAnswers[id] || null;
  }

  function getAllUserAnswers() {
    return { ...userAnswers };
  }

  return {
    init, getAll, getById, getCategories, getStats, filter,
    addWrong, removeWrong, isWrong, getWrongQuestions, getWrongCount,
    markQuestion, getProgress,
    saveSequentialPos, loadSequentialPos,
    saveUserAnswer, getUserAnswer, getAllUserAnswers, loadUserAnswers
  };
})();
