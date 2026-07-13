/* 「喜欢」功能：直写 thu-yn/frontier-notes 仓库的 data/likes.json。
 *
 * - 读：GitHub contents API 公开仓库无需 token。
 * - 写：需要 fine-grained PAT（仅 Contents 读写），存 localStorage。
 * - localStorage 里镜像一份收藏，页面加载即渲染，再后台对齐真实状态。
 * - 连续点击用 promise 队列串行化，409/422 冲突重取再试一次，失败回滚。
 */
(function () {
  "use strict";

  var REPO = "thu-yn/frontier-notes";
  var LIKES_PATH = "data/likes.json";
  var API = "https://api.github.com/repos/" + REPO + "/contents/" + LIKES_PATH;
  var LS_TOKEN = "fn_gh_token";
  var LS_STORE = "fn_likes_store"; // 本地镜像：数组，元素同 likes.json 的 item

  /* ---------- 工具：unicode 安全的 base64 ---------- */
  function utf8ToB64(str) {
    var bytes = new TextEncoder().encode(str);
    var bin = "";
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  }
  function b64ToUtf8(b64) {
    var bin = atob((b64 || "").replace(/\s/g, ""));
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }

  /* ---------- token ---------- */
  function getToken() {
    try { return localStorage.getItem(LS_TOKEN) || ""; } catch (e) { return ""; }
  }
  function setToken(t) {
    try {
      if (t) localStorage.setItem(LS_TOKEN, t);
      else localStorage.removeItem(LS_TOKEN);
    } catch (e) {}
  }

  /* ---------- 本地镜像 ---------- */
  function loadStore() {
    try {
      var raw = localStorage.getItem(LS_STORE);
      var arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) { return []; }
  }
  function saveStore(arr) {
    try { localStorage.setItem(LS_STORE, JSON.stringify(arr)); } catch (e) {}
  }
  function isLiked(id) {
    return loadStore().some(function (it) { return it.id === id; });
  }
  // 本地写入/删除一条，返回新数组
  function setLocal(meta, liked) {
    var arr = loadStore().filter(function (it) { return it.id !== meta.id; });
    if (liked) {
      arr.push({
        id: meta.id, date: meta.date, section: meta.section,
        domain: meta.domain, title: meta.title, url: meta.url,
        liked_at: new Date().toISOString()
      });
    }
    arr.sort(function (a, b) { return (b.liked_at || "").localeCompare(a.liked_at || ""); });
    saveStore(arr);
    return arr;
  }

  /* ---------- 按钮状态 ---------- */
  function readMeta(btn) {
    var d = btn.dataset;
    return { id: d.id, title: d.title || "", url: d.url || "", domain: d.domain || "ai", section: d.section || "", date: d.date || "" };
  }
  function applyBtn(btn, liked) {
    btn.classList.toggle("liked", !!liked);
    btn.setAttribute("aria-pressed", String(!!liked));
  }
  function applyAll(id, liked) {
    document.querySelectorAll('.like-btn[data-id="' + cssEsc(id) + '"]').forEach(function (b) {
      applyBtn(b, liked);
    });
  }
  function cssEsc(s) { return (s || "").replace(/["\\]/g, "\\$&"); }
  function refreshButtons() {
    document.querySelectorAll(".like-btn").forEach(function (b) {
      applyBtn(b, isLiked(b.dataset.id));
    });
  }

  /* ---------- 提示 ---------- */
  function notify(msg) {
    var el = document.getElementById("fn-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "fn-toast";
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.classList.remove("show"); }, 3200);
  }

  /* ---------- 远端写入 ---------- */
  function authHeaders(token) {
    var h = { "Accept": "application/vnd.github+json" };
    if (token) h["Authorization"] = "Bearer " + token;
    return h;
  }

  function writeRemote(meta, liked, isRetry) {
    var token = getToken();
    if (!token) return Promise.reject(new Error("缺少 token"));
    return fetch(API, { headers: authHeaders(token), cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("读取 likes.json 失败（" + r.status + "）");
        return r.json();
      })
      .then(function (data) {
        var sha = data.sha;
        var obj;
        try { obj = JSON.parse(b64ToUtf8(data.content)); } catch (e) { obj = { items: [] }; }
        if (!obj || !Array.isArray(obj.items)) obj = { items: [] };
        obj.items = obj.items.filter(function (it) { return it.id !== meta.id; });
        if (liked) {
          obj.items.push({
            id: meta.id, date: meta.date, section: meta.section,
            domain: meta.domain, title: meta.title, url: meta.url,
            liked_at: new Date().toISOString()
          });
        }
        obj.items.sort(function (a, b) { return (b.liked_at || "").localeCompare(a.liked_at || ""); });
        var body = {
          message: (liked ? "like: " : "unlike: ") + (meta.title || meta.id),
          content: utf8ToB64(JSON.stringify(obj, null, 2) + "\n"),
          sha: sha
        };
        return fetch(API, { method: "PUT", headers: authHeaders(token), body: JSON.stringify(body) })
          .then(function (r) {
            if ((r.status === 409 || r.status === 422) && !isRetry) {
              return writeRemote(meta, liked, true); // 冲突，重取再试一次
            }
            if (!r.ok) {
              return r.json().then(function (j) {
                throw new Error((j && j.message) || ("写入失败（" + r.status + "）"));
              });
            }
            return r.json();
          });
      });
  }

  /* ---------- 串行队列 ---------- */
  var chain = Promise.resolve();
  function enqueue(task) {
    chain = chain.then(task, task);
    return chain;
  }

  function toggle(btn) {
    var meta = readMeta(btn);
    if (!meta.id) return;
    if (!getToken()) { openTokenPanel(); return; }
    var liked = !isLiked(meta.id); // 目标状态

    // 乐观更新
    setLocal(meta, liked);
    applyAll(meta.id, liked);
    renderLikesPageFromLocal();

    enqueue(function () {
      return writeRemote(meta, liked, false).catch(function (err) {
        // 回滚
        setLocal(meta, !liked);
        applyAll(meta.id, !liked);
        renderLikesPageFromLocal();
        notify("同步失败，已回滚：" + err.message);
        if (/token|401|403/i.test(err.message)) openTokenPanel();
      });
    });
  }

  /* ---------- 后台对齐真实状态 ---------- */
  function alignFromRemote() {
    fetch(API, { headers: authHeaders(getToken()), cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !data.content) return;
        var obj = JSON.parse(b64ToUtf8(data.content));
        var items = (obj && Array.isArray(obj.items)) ? obj.items : [];
        saveStore(items);
        refreshButtons();
        renderLikesPage(items);
      })
      .catch(function () { /* 读失败就用本地镜像，静默 */ });
  }

  /* ---------- 「我的喜欢」页渲染 ---------- */
  function domainMeta(id) {
    var m = (window.FN_DOMAINS || {})[id];
    return m || [id, "#5c6871"];
  }
  function buildLikeCard(it) {
    var dm = domainMeta(it.domain || "ai");
    var art = document.createElement("article");
    art.className = "entry";
    art.setAttribute("data-domain", it.domain || "ai");

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "like-btn liked";
    btn.setAttribute("aria-pressed", "true");
    btn.setAttribute("aria-label", "取消喜欢");
    btn.title = "取消喜欢";
    btn.dataset.id = it.id;
    btn.dataset.title = it.title || "";
    btn.dataset.url = it.url || "";
    btn.dataset.domain = it.domain || "ai";
    btn.dataset.section = it.section || "";
    btn.dataset.date = it.date || "";
    btn.innerHTML = '<span class="heart" aria-hidden="true">♥</span>';
    art.appendChild(btn);

    var h = document.createElement("h3");
    if (it.url) {
      var a = document.createElement("a");
      a.href = it.url;
      a.textContent = it.title || it.id;
      h.appendChild(a);
    } else {
      h.appendChild(document.createTextNode(it.title || it.id));
    }
    var chip = document.createElement("span");
    chip.className = "domain-chip";
    chip.style.setProperty("--dot", dm[1]);
    chip.textContent = dm[0];
    h.appendChild(chip);
    art.appendChild(h);

    var meta = document.createElement("p");
    meta.className = "meta";
    var sectionCn = { papers: "论文", repos: "开源", news: "资讯", ideas: "研究点" }[it.section] || it.section || "";
    meta.textContent = [it.date, sectionCn].filter(Boolean).join(" · ");
    art.appendChild(meta);
    return art;
  }

  function renderLikesPage(items) {
    var list = document.getElementById("likes-list");
    if (!list) return;
    var empty = document.getElementById("likes-empty");
    var count = document.getElementById("likes-count");
    items = (items || []).slice().sort(function (a, b) {
      return (b.liked_at || "").localeCompare(a.liked_at || "");
    });
    if (count) count.textContent = items.length ? items.length + " 条" : "";
    list.innerHTML = "";
    if (!items.length) { if (empty) empty.hidden = false; return; }
    if (empty) empty.hidden = true;

    var byDate = {};
    items.forEach(function (it) { (byDate[it.date] = byDate[it.date] || []).push(it); });
    Object.keys(byDate).sort().reverse().forEach(function (date) {
      var head = document.createElement("h3");
      head.className = "likes-date";
      head.textContent = date;
      list.appendChild(head);
      byDate[date].forEach(function (it) { list.appendChild(buildLikeCard(it)); });
    });
  }
  function renderLikesPageFromLocal() { renderLikesPage(loadStore()); }

  /* ---------- token 设置浮层 ---------- */
  function openTokenPanel() {
    var back = document.getElementById("fn-token-back");
    if (back) { back.hidden = false; var inp = document.getElementById("fn-token-input"); if (inp) { inp.value = getToken(); inp.focus(); } return; }
    back = document.createElement("div");
    back.id = "fn-token-back";
    back.innerHTML =
      '<div id="fn-token-panel" role="dialog" aria-modal="true" aria-label="设置喜欢用的 GitHub Token">' +
      '  <h3>设置 GitHub Token</h3>' +
      '  <p>「喜欢」会把收藏直接写进仓库 <code>' + REPO + '</code> 的 <code>data/likes.json</code>。写操作需要一个细粒度个人访问令牌（fine-grained PAT）。</p>' +
      '  <ol>' +
      '    <li>打开 GitHub → Settings → Developer settings → Fine-grained tokens</li>' +
      '    <li>Repository access 只选 <code>' + REPO + '</code></li>' +
      '    <li>Permissions → Repository permissions → <b>Contents</b> 设为 <b>Read and write</b></li>' +
      '    <li>生成后把 token 粘贴到下面（只存在本机浏览器 localStorage，不会上传别处）</li>' +
      '  </ol>' +
      '  <input id="fn-token-input" type="password" placeholder="github_pat_..." autocomplete="off" spellcheck="false">' +
      '  <div class="fn-token-actions">' +
      '    <button type="button" id="fn-token-clear">清除</button>' +
      '    <span style="flex:1"></span>' +
      '    <button type="button" id="fn-token-cancel">取消</button>' +
      '    <button type="button" id="fn-token-save" class="primary">保存</button>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(back);
    var input = back.querySelector("#fn-token-input");
    input.value = getToken();
    function close() { back.hidden = true; }
    back.addEventListener("click", function (e) { if (e.target === back) close(); });
    back.querySelector("#fn-token-cancel").addEventListener("click", close);
    back.querySelector("#fn-token-clear").addEventListener("click", function () {
      setToken(""); input.value = ""; notify("已清除 token"); close();
    });
    back.querySelector("#fn-token-save").addEventListener("click", function () {
      setToken(input.value.trim());
      notify(input.value.trim() ? "token 已保存" : "已清除 token");
      close();
      alignFromRemote();
    });
    input.focus();
  }

  /* ---------- 初始化 ---------- */
  function init() {
    refreshButtons();
    renderLikesPageFromLocal();
    alignFromRemote();

    // 事件委托：卡片喜欢按钮
    document.addEventListener("click", function (e) {
      var btn = e.target.closest && e.target.closest(".like-btn");
      if (btn) { e.preventDefault(); toggle(btn); return; }
      var gear = e.target.closest && e.target.closest("#fn-token-gear");
      if (gear) { e.preventDefault(); openTokenPanel(); }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
