/* 中英语言切换 — body class 控制，CSS !important 保证优先级 */
(function() {
  var STORAGE_KEY = 'dh-srd-lang';

  function getSavedLang() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      return (v === 'zh' || v === 'en') ? v : 'zh';
    } catch(e) { return 'zh'; }
  }

  function saveLang(lang) {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch(e) {}
  }

  function updateToggleBtn(lang) {
    var btn = document.getElementById('lang-toggle-btn');
    if (!btn) return;
    btn.innerHTML = (lang === 'zh')
      ? '<span class="lang-zh-active">中</span> <span class="lang-sep">|</span> <span class="lang-en-inactive">EN</span>'
      : '<span class="lang-zh-inactive">中</span> <span class="lang-sep">|</span> <span class="lang-en-active">EN</span>';
  }

  function rebuildSidebar(lang) {
    try {
      var menu = document.getElementById('sidemenu-topnav');
      if (!menu) return;
      menu.innerHTML = '';

      var h3 = document.querySelector('#sidemenu h3');
      if (!h3) {
        h3 = document.createElement('h3');
        menu.parentNode.insertBefore(h3, menu);
      }
      h3.textContent = lang === 'zh' ? '目录' : 'Contents';

      // 扫描 .content-area 内的标题，按语言过滤
      var wrap = document.querySelector('.content-area');
      if (!wrap) return;
      wrap.querySelectorAll('h1, h2, h3').forEach(function(el) {
        if (el.closest('#sidemenu')) return;
        // 内容页：h1/h2 在 .lang-zh/.lang-en div 内，只取当前语言
        var langParent = el.closest('.lang-zh, .lang-en');
        if (langParent) {
          var parentLang = langParent.classList.contains('lang-zh') ? 'zh' : 'en';
          if (parentLang !== lang) return;
        }
        // 首页：标题不在语言包装器内，直接加入
        var text = el.textContent.trim();
        if (!text) return;
        if (!el.id) {
          el.id = 't-' + lang + '-' + el.tagName.toLowerCase() + '-' +
                  Math.random().toString(36).substr(2, 4);
        }
        var li = document.createElement('li');
        li.className = 'currentli' + (el.tagName === 'H1' ? ' headli' : '');
        li.innerHTML = '<a href="#' + el.id + '">' + text + '</a>';
        menu.appendChild(li);
      });
    } catch(e) {}
  }

  function setLang(lang) {
    try {
      // 纯 body class 控制，CSS !important 处理显示隐藏
      document.body.classList.remove('show-en', 'show-zh');
      document.body.classList.add('show-' + lang);
      saveLang(lang);
      updateToggleBtn(lang);
      rebuildSidebar(lang);
    } catch(e) {
      document.body.classList.remove('show-en', 'show-zh');
      document.body.classList.add('show-zh');
    }
  }

  // 初始化
  try {
    var params = new URLSearchParams(window.location.search);
    var urlLang = params.get('lang');
    var savedLang = (urlLang === 'zh' || urlLang === 'en') ? urlLang : getSavedLang();
    setLang(savedLang);
    if (urlLang === 'zh' || urlLang === 'en') saveLang(urlLang);
  } catch(e) {}

  // 点击切换
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('#lang-toggle-btn');
    if (btn) {
      e.preventDefault();
      setLang(getSavedLang() === 'zh' ? 'en' : 'zh');
    }
  });
})();
