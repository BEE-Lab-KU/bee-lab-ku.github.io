(function () {
  'use strict';

  var STORAGE_KEY = 'bee-lab-lang';
  var DEFAULT_LANGUAGE = 'ko';
  var SUPPORTED = { ko: true, en: true };
  var translations = {};
  var readyResolve;
  var ready = new Promise(function (resolve) { readyResolve = resolve; });

  function storedLanguage() {
    try {
      var value = window.localStorage.getItem(STORAGE_KEY);
      return SUPPORTED[value] ? value : DEFAULT_LANGUAGE;
    } catch (e) {
      return DEFAULT_LANGUAGE;
    }
  }

  var language = SUPPORTED[window._beePreferredLanguage]
    ? window._beePreferredLanguage
    : (SUPPORTED[document.documentElement.getAttribute('lang')]
      ? document.documentElement.getAttribute('lang')
      : storedLanguage());

  function rememberOriginal(el, name, value) {
    var key = 'i18nOriginal' + name.replace(/(^|-)([a-z])/g, function (_, dash, letter) {
      return letter.toUpperCase();
    });
    if (!(key in el.dataset)) el.dataset[key] = value;
    return key;
  }

  function translated(key) {
    if (Object.prototype.hasOwnProperty.call(translations, key)) {
      return typeof translations[key] === 'string' ? translations[key] : null;
    }
    var value = translations;
    var parts = key.split('.');
    for (var i = 0; i < parts.length; i += 1) {
      if (!value || typeof value !== 'object' ||
          !Object.prototype.hasOwnProperty.call(value, parts[i])) return null;
      value = value[parts[i]];
    }
    return typeof value === 'string' ? value : null;
  }

  function applyText(el, key, useHtml) {
    var property = useHtml ? 'innerHTML' : 'textContent';
    var originalKey = rememberOriginal(el, useHtml ? 'html' : 'text', el[property]);
    if (language === 'ko') {
      el[property] = el.dataset[originalKey];
      return;
    }
    var value = translated(key);
    if (value == null) {
      console.error('Missing English translation:', key);
      el[property] = el.dataset[originalKey];
      return;
    }
    el[property] = value;
  }

  function applyAttribute(el, attr, key) {
    var original = el.getAttribute(attr) || '';
    var originalKey = rememberOriginal(el, 'attr-' + attr, original);
    if (language === 'ko') {
      el.setAttribute(attr, el.dataset[originalKey]);
      return;
    }
    var value = translated(key);
    if (value == null) {
      console.error('Missing English translation:', key);
      el.setAttribute(attr, el.dataset[originalKey]);
      return;
    }
    el.setAttribute(attr, value);
  }

  function updateSwitches() {
    document.querySelectorAll('[data-set-language]').forEach(function (button) {
      var active = button.getAttribute('data-set-language') === language;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    var switcher = document.querySelector('.lang-switch');
    if (switcher) {
      switcher.setAttribute(
        'aria-label',
        language === 'en' ? 'Language selection' : '언어 선택'
      );
    }
  }

  function apply(root) {
    if (window._beeI18nFallbackTimer) {
      window.clearTimeout(window._beeI18nFallbackTimer);
      window._beeI18nFallbackTimer = null;
    }
    root = root || document;
    root.querySelectorAll('[data-i18n]').forEach(function (el) {
      applyText(el, el.getAttribute('data-i18n'), false);
    });
    root.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      applyText(el, el.getAttribute('data-i18n-html'), true);
    });
    ['aria-label', 'alt', 'placeholder', 'title'].forEach(function (attr) {
      root.querySelectorAll('[data-i18n-' + attr + ']').forEach(function (el) {
        applyAttribute(el, attr, el.getAttribute('data-i18n-' + attr));
      });
    });
    document.documentElement.lang = language;
    document.documentElement.setAttribute('data-lang', language);
    document.documentElement.setAttribute('data-i18n-ready', 'true');
    updateSwitches();
  }

  function setLanguage(next) {
    if (!SUPPORTED[next] || next === language) return;
    language = next;
    try { window.localStorage.setItem(STORAGE_KEY, language); } catch (e) {}
    apply(document);
    document.dispatchEvent(new CustomEvent('languagechange', { detail: { language: language } }));
  }

  function field(item, key) {
    if (!item) return '';
    if (language === 'en') {
      var englishKey = key + 'En';
      if (item[englishKey] != null && item[englishKey] !== '') return item[englishKey];
    }
    return item[key] == null ? '' : item[key];
  }

  function text(key, fallback) {
    if (language === 'en') {
      var value = translated(key);
      if (value != null) return value;
    }
    return fallback == null ? '' : fallback;
  }

  window.BeeI18n = {
    ready: ready,
    get language() { return language; },
    setLanguage: setLanguage,
    apply: apply,
    field: field,
    text: text
  };

  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-set-language]');
    if (!button) return;
    setLanguage(button.getAttribute('data-set-language'));
  });

  var translationTimeout;
  var translationController = window.AbortController ? new AbortController() : null;
  var translationOptions = { cache: 'no-cache' };
  if (translationController) translationOptions.signal = translationController.signal;
  var translationRequest = fetch('i18n/en.json', translationOptions).then(function (response) {
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.json();
  });
  var translationTimeoutPromise = new Promise(function (_, reject) {
    translationTimeout = window.setTimeout(function () {
      if (translationController) translationController.abort();
      reject(new Error('English translations timed out'));
    }, 2500);
  });

  Promise.race([translationRequest, translationTimeoutPromise])
    .then(function (data) {
      window.clearTimeout(translationTimeout);
      translations = data && typeof data === 'object' ? data : {};
      apply(document);
      readyResolve();
      document.dispatchEvent(new CustomEvent('languagechange', { detail: { language: language, initial: true } }));
    })
    .catch(function (error) {
      window.clearTimeout(translationTimeout);
      console.error('English translations failed to load:', error);
      language = DEFAULT_LANGUAGE;
      apply(document);
      readyResolve();
    });
})();
