(function () {
  // An installed app runs in its own window; a tab reports 'browser'.
  // 'fullscreen' is left out on purpose: F11 in an ordinary tab matches it.
  var appWindow = ['standalone', 'minimal-ui', 'window-controls-overlay'].some(function (mode) {
    return window.matchMedia('(display-mode: ' + mode + ')').matches;
  }) || navigator.standalone === true;

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js', {scope: './'}).catch(console.error);
    // Hand the worker what this page already loaded (see sw.js 'message').
    // Twice: once when it is ready, and again after the app has had time to
    // pull its packages.
    var sendLoaded = function () {
      navigator.serviceWorker.ready.then(function (registration) {
        if (!registration.active) return;
        var urls = performance.getEntriesByType('resource').map(function (entry) {
          return entry.name;
        }).filter(function (url) {
          return url.indexOf('http') === 0;
        });
        urls.push(location.href);
        registration.active.postMessage({type: 'cache-urls', urls: urls});
      });
    };
    sendLoaded();
    window.addEventListener('load', function () { setTimeout(sendLoaded, 15000); });
  }

  // main.py may say what it is doing; if it does not (an example dropped in
  // as main.py), do not leave "Loading Python…" up once the script has run.
  window.addEventListener('py:all-done', function () {
    document.documentElement.classList.add('py-done');
    var status = document.getElementById('status');
    if (status && status.textContent === 'Loading Python…') status.textContent = 'Running.';
  });

  // ---- The app window matches the display -------------------------------
  //
  // In its own window (installed, launched from the dock, Start menu or
  // launcher) the page is just the canvas, so size the window to the display
  // that board_config asked for: the canvas size plus the window's own frame
  // and title bar. Chrome and Edge allow resizeTo() in an installed app's
  // window and refuse it in a tab, so a tab is left alone.
  //
  // It runs when the display first reports its size and again only if that
  // size changes (a rotation, say). Resizing the window yourself afterwards
  // is never undone, and a maximized window is left maximized.
  var fittedTo = null;

  function fitWindow() {
    var canvas = document.getElementById('display_canvas');
    if (!appWindow || !canvas || !window.resizeTo) return;
    var width = canvas.width, height = canvas.height;
    var key = width + 'x' + height;
    if (key === fittedTo) return;
    fittedTo = key;
    if (window.outerWidth >= screen.availWidth && window.outerHeight >= screen.availHeight) return;
    var frameW = window.outerWidth - window.innerWidth;
    var frameH = window.outerHeight - window.innerHeight;
    var outerW = Math.min(width + frameW, screen.availWidth);
    var outerH = Math.min(height + frameH, screen.availHeight);
    if (Math.abs(outerW - window.outerWidth) < 2 && Math.abs(outerH - window.outerHeight) < 2) return;
    try { window.resizeTo(outerW, outerH); } catch (err) { /* not allowed here */ }
  }

  if (appWindow) {
    var canvas = document.getElementById('display_canvas');
    var pending = false;
    var schedule = function () {
      if (pending) return;
      pending = true;
      requestAnimationFrame(function () { pending = false; fitWindow(); });
    };
    // PSDisplay writes the canvas's width and height when board_config
    // creates the display; that is the size to fit, not the size the
    // page starts with.
    if (canvas && window.MutationObserver) {
      new MutationObserver(schedule).observe(canvas, {attributes: true, attributeFilter: ['width', 'height']});
    }
    // A main.py that never builds a display still gets one fit.
    window.addEventListener('py:all-done', schedule);
  }

  // ---- A hint that points at the browser's own install control ----------
  //
  // Modelled on Chrome's address-bar install icon and on the per-platform
  // instructions of @khmyznikov/pwa-install (iOS/iPadOS Share > Add to Home
  // Screen, macOS Safari Add to Dock). Chromium only gets the hint after
  // 'beforeinstallprompt' fires, which is when its install icon appears.
  // Firefox on the desktop has nothing to point at, so it gets nothing.
  var DISMISSED = 'pydevices-install-hint-dismissed';
  var hint = null;

  function dismissed() {
    try { return localStorage.getItem(DISMISSED) === '1'; } catch (err) { return false; }
  }

  function showHint(mode, text) {
    if (appWindow || hint || dismissed()) return;
    hint = document.createElement('aside');
    hint.className = 'install-hint install-hint--' + mode;
    hint.setAttribute('aria-label', 'Install this app');
    var message = document.createElement('p');
    message.innerHTML = text;
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'install-hint__close';
    close.setAttribute('aria-label', 'Dismiss');
    close.textContent = '×';
    close.addEventListener('click', function () {
      try { localStorage.setItem(DISMISSED, '1'); } catch (err) { /* private mode */ }
      hideHint();
    });
    hint.appendChild(message);
    hint.appendChild(close);
    document.body.appendChild(hint);
  }

  function hideHint() {
    if (hint) hint.remove();
    hint = null;
  }

  var ua = navigator.userAgent;
  var android = /Android/i.test(ua);
  // iPadOS reports itself as a Mac; touch points give it away.
  var appleMobile = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  var safariVersion = /Version\/(\d+)[.\d]* (Mobile\/\S+ )?Safari\//.exec(ua);
  var macSafari = /Macintosh/.test(ua) && !appleMobile && safariVersion && Number(safariVersion[1]) >= 17;

  window.addEventListener('beforeinstallprompt', function () {
    // Not preventDefault(): the browser's own install UI stays as it is.
    if (android) {
      showHint('menu', 'Install this app: open the browser menu <b>⋮</b> and choose <b>Install app</b>.');
    } else {
      showHint('omnibox', 'Install this app with the install icon at the right of the address bar.');
    }
  });

  window.addEventListener('appinstalled', hideHint);

  if (!appWindow && (appleMobile || macSafari || (android && !('BeforeInstallPromptEvent' in window)))) {
    window.addEventListener('load', function () {
      setTimeout(function () {
        if (appleMobile) {
          // An iPhone's Share button lives in the bottom toolbar; an iPad's at the top.
          showHint(/iPhone|iPod/.test(ua) ? 'note install-hint--bottom' : 'note', 'Install this app: tap <b>Share</b> (under <b>⋯</b> if you don’t see it), then <b>Add to Home Screen</b>.');
        } else if (macSafari) {
          showHint('note', 'Install this app: choose <b>File › Add to Dock</b>.');
        } else {
          showHint('note', 'Install this app: open the browser menu and choose <b>Install</b> or <b>Add to Home screen</b>.');
        }
      }, 3000);
    });
  }
})();
