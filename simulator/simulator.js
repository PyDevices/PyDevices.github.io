/**
 * simulator.js — Interactive PyDevices Python Simulator Engine
 *
 * Manages Monaco Editor, Pyodide/MicroPython runtime execution,
 * synthetic board_config binding, LZ-string sharing, and split layout.
 */

(function () {
  const MONACO_CDN = "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/";

  let monacoEditor = null;
  let currentResolution = { width: 320, height: 240, shape: "rectangle" };

  // DOM Elements
  const elStatusDot = document.getElementById("status-dot");
  const elStatusText = document.getElementById("status-text");
  const elTemplateSelect = document.getElementById("template-select");
  const elResolutionSelect = document.getElementById("resolution-select");
  const elRuntimeSelect = document.getElementById("runtime-select");
  const elRunBtn = document.getElementById("run-btn");
  const elShareBtn = document.getElementById("share-btn");
  const elClearConsoleBtn = document.getElementById("clear-console-btn");
  const elDeviceBezel = document.getElementById("device-bezel");
  const elCanvas = document.getElementById("display_canvas");
  const elToast = document.getElementById("sim-toast");


  // =========================================================================
  // Status & Console Helpers
  // =========================================================================

  function setStatus(text, state = "ready") {
    if (elStatusText) elStatusText.textContent = text;
    if (elStatusDot) {
      elStatusDot.className = "sim-status-dot";
      if (state === "ready") elStatusDot.classList.add("is-ready");
      else if (state === "busy") elStatusDot.classList.add("is-busy");
      else if (state === "error") elStatusDot.classList.add("is-error");
    }
  }

  function clearConsole() {
    const script = document.querySelector('#console-log script[terminal]');
    const term = script && script.terminal;
    if (term && typeof term.clear === "function") {
      term.clear();
      term.write(">>> ");
    }
  }

  function showToast(msg) {
    if (!elToast) return;
    elToast.textContent = msg;
    elToast.classList.add("is-active");
    setTimeout(() => elToast.classList.remove("is-active"), 2600);
  }

  // =========================================================================
  // Monaco Editor Initialization
  // =========================================================================

  function initMonaco() {
    if (typeof require === "undefined") {
      console.error("Monaco loader not found.");
      return;
    }

    require.config({ paths: { vs: MONACO_CDN + "vs" } });
    require(["vs/editor/editor.main"], function () {
      const isLight = document.documentElement.getAttribute("data-theme") === "light";
      const initialCode = loadInitialCode();

      monacoEditor = monaco.editor.create(document.getElementById("editor-container"), {
        value: initialCode,
        language: "python",
        theme: isLight ? "vs" : "vs-dark",
        fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace",
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 4,
        insertSpaces: true,
        wordWrap: "on",
        lineNumbers: "on",
        renderLineHighlight: "all",
        padding: { top: 12, bottom: 12 }
      });
      window.monacoEditor = monacoEditor;

      // Shortcut: Ctrl+Enter / Cmd+Enter to Run
      monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, function () {
        runScript();
      });

      // Auto-save code edits to localStorage
      monacoEditor.onDidChangeModelContent(() => {
        try {
          localStorage.setItem("pydevices-simulator-code", monacoEditor.getValue());
        } catch (e) {}
      });

    });
  }

  // =========================================================================
  // PyScript Runtime Mount
  //
  // The runtime <script> tag is built here rather than written into index.html
  // because PyScript only honours an `interpreter` override supplied as an
  // inline JSON `config` attribute at the moment it processes the tag; an
  // external config file on a dynamically inserted tag is ignored outright.
  // The Python itself lives in the <template> blocks in index.html, so mip and
  // micropip installs stay in the page and never reach the REPL.
  // =========================================================================

  const RUNTIME_STORAGE_KEY = "pydevices-simulator-runtime";
  const RESOLUTION_STORAGE_KEY = "pydevices-simulator-resolution";

  const RUNTIMES = {
    mpy: { type: "mpy", config: "./micropython.json", template: "bootstrap-mpy" },
    pyodide: { type: "py", config: "./pyodide.json", template: "bootstrap-py" }
  };

  let pyscriptCoreLoaded = false;
  let mountGeneration = 0;

  function templateSource(id) {
    const el = document.getElementById(id);
    return el ? el.innerHTML : "";
  }

  async function loadInterpreterConfig(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Unable to load ${url}: HTTP ${res.status}`);
    return res.json();
  }

  // Mount the runtime for this page load. PyScript caches one interpreter per
  // script type and ignores config differences when deciding whether to reuse
  // it, so re-mounting cannot give a fresh VM -- see runScript() for how RESET
  // handles that. `generation` is only a race guard against overlapping mounts.
  async function mountRuntime(runtimeKey) {
    const runtime = RUNTIMES[runtimeKey] || RUNTIMES.mpy;
    const host = document.getElementById("console-log");
    if (!host) return;

    const generation = ++mountGeneration;
    setStatus("Refreshing environment…", "busy");

    // Tear down the previous runtime and its terminal.
    host.querySelectorAll("script, .xterm, py-terminal, mpy-terminal").forEach((el) => el.remove());

    let config;
    try {
      config = await loadInterpreterConfig(runtime.config);
    } catch (err) {
      console.error(err);
      setStatus("Config error", "error");
      return;
    }
    if (generation !== mountGeneration) return; // a newer mount superseded us
    config.generation = generation;

    // In worker mode the interpreter is imported from worker scope, where a
    // root-relative path is not a resolvable module specifier. Absolutise it
    // here so the stub files can stay written against the site root.
    if (config.interpreter) {
      config.interpreter = new URL(config.interpreter, window.location.href).href;
    }

    const script = document.createElement("script");
    script.type = runtime.type;
    script.setAttribute("config", JSON.stringify(config));
    script.setAttribute("terminal", "");
    // Deliberately NOT `worker`. A worker would make Pyodide's REPL interactive
    // (main-thread input() raises, so code.interact() cannot read a prompt), and
    // cross-origin isolation for it is arrangeable on Pages via a service
    // worker. But psdisplay cannot run in a worker: it stores a Python object on
    // the canvas element (`canvas._ps_devices = self`) and attaches create_proxy
    // callbacks to main-thread DOM events, and a PyProxy cannot be structured-
    // cloned across the worker boundary -- it fails with DataCloneError, so the
    // display never comes up. Main thread keeps the display working on both
    // runtimes; see the notes on making the Pyodide REPL interactive.
    script.textContent = templateSource(runtime.template) + templateSource("bootstrap-tail");
    host.appendChild(script);

    // core.js scans on import and observes the DOM afterwards, so it is safe to
    // import once, lazily, only after the first tag exists.
    if (!pyscriptCoreLoaded) {
      pyscriptCoreLoaded = true;
      await import("https://pyscript.net/releases/2024.11.1/core.js");
    }

    setStatus("Ready", "ready");
  }

  // RESET. PyScript caches one interpreter per script type, so re-mounting the
  // tag re-runs the bootstrap but keeps sys.modules -- stale LVGL objects, live
  // timers and half-torn-down displays all survive. Reloading the page is the
  // only way to get a genuinely fresh VM, and it is cheap: the editor contents,
  // runtime and resolution are all persisted below, and every asset is cached.
  // This mirrors sim.lvgl.io, whose Restart tears down and rebuilds its iframe.
  function runScript() {
    persistState();
    window.location.reload();
  }

  function persistState() {
    try {
      if (monacoEditor) localStorage.setItem("pydevices-simulator-code", monacoEditor.getValue());
      localStorage.setItem(RUNTIME_STORAGE_KEY, currentRuntime());
      localStorage.setItem(RESOLUTION_STORAGE_KEY, JSON.stringify(currentResolution));
    } catch (e) {}
  }

  function restoreResolution() {
    try {
      const saved = JSON.parse(localStorage.getItem(RESOLUTION_STORAGE_KEY) || "null");
      if (saved && saved.width > 0 && saved.height > 0) {
        setCanvasResolution(saved.width, saved.height, saved.shape || "rectangle");
        return true;
      }
    } catch (e) {}
    return false;
  }

  function currentRuntime() {
    return elRuntimeSelect && elRuntimeSelect.value === "pyodide" ? "pyodide" : "mpy";
  }

  // Called from the Python bootstrap. Monaco loads asynchronously, so fall back
  // to the same hash/localStorage/template resolution the editor itself uses --
  // otherwise an early mount would silently run the default template instead of
  // the user's shared or saved code.
  window.getEditorCode = function() {
    if (monacoEditor) return monacoEditor.getValue();
    try {
      return loadInitialCode();
    } catch (e) {
      return "";
    }
  };

  // =========================================================================
  // Canvas Resolution & Device Presets
  // =========================================================================

  function clearCanvas() {
    if (!elCanvas) return;
    const ctx = elCanvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, elCanvas.width, elCanvas.height);
    }
  }

  function setCanvasResolution(width, height, shape = "rectangle") {
    currentResolution = { width, height, shape };
    // Read by the Python bootstrap to pin the panel size; see _set_board_size().
    window.SIM_WIDTH = width;
    window.SIM_HEIGHT = height;
    if (!elCanvas) return;

    elCanvas.width = width;
    elCanvas.height = height;
    clearCanvas();

    if (elDeviceBezel) {
      if (shape === "round") {
        elDeviceBezel.classList.add("is-round");
      } else {
        elDeviceBezel.classList.remove("is-round");
      }
    }
  }

  function syncResolutionSelect() {
    if (!elResolutionSelect) return;
    const { width, height, shape } = currentResolution;
    const suffix = shape === "round" ? "-round" : shape === "square" ? "-square" : "";
    const key = `${width}x${height}${suffix}`;
    if (elResolutionSelect.querySelector(`option[value="${key}"]`)) elResolutionSelect.value = key;
  }

  function handleResolutionChange(val) {
    if (val === "320x240") setCanvasResolution(320, 240, "rectangle");
    else if (val === "240x320") setCanvasResolution(240, 320, "rectangle");
    else if (val === "240x240-square") setCanvasResolution(240, 240, "square");
    else if (val === "240x240-round") setCanvasResolution(240, 240, "round");
    else if (val === "480x320") setCanvasResolution(480, 320, "rectangle");
    else if (val === "320x480") setCanvasResolution(320, 480, "rectangle");
    else if (val === "800x480") setCanvasResolution(800, 480, "rectangle");
    else if (val === "custom") {
      const customW = prompt("Enter display width (px):", currentResolution.width);
      const customH = prompt("Enter display height (px):", currentResolution.height);
      const w = parseInt(customW, 10);
      const h = parseInt(customH, 10);
      if (w > 0 && h > 0) setCanvasResolution(w, h, "rectangle");
    }
  }

  // =========================================================================
  // Templates & Code Sharing (LZ-String)
  // =========================================================================

  function loadInitialCode() {
    // 1. Check URL hash (#code=... or #template=...)
    const hash = window.location.hash.substring(1);
    if (hash) {
      const params = new URLSearchParams(hash);
      const compressedCode = params.get("code");
      if (compressedCode && typeof LZString !== "undefined") {
        try {
          const decompressed = LZString.decompressFromEncodedURIComponent(compressedCode);
          if (decompressed) return decompressed;
        } catch (e) {}
      }

      const templateKey = params.get("template");
      if (templateKey && SIMULATOR_TEMPLATES[templateKey]) {
        if (elTemplateSelect) elTemplateSelect.value = templateKey;
        const tpl = SIMULATOR_TEMPLATES[templateKey];
        setCanvasResolution(tpl.width, tpl.height, tpl.shape);
        return tpl.code;
      }
    }

    // 2. Check localStorage saved draft
    try {
      const saved = localStorage.getItem("pydevices-simulator-code");
      if (saved) return saved;
    } catch (e) {}

    // 3. Default to LVGL counter template
    const def = SIMULATOR_TEMPLATES["lvgl-counter"];
    if (def) {
      setCanvasResolution(def.width, def.height, def.shape);
      return def.code;
    }
    return "# PyDevices Simulator\nprint('Hello from PyDevices Simulator!')\n";
  }

  function loadTemplate(key) {
    if (!SIMULATOR_TEMPLATES[key] || !monacoEditor) return;
    const tpl = SIMULATOR_TEMPLATES[key];
    monacoEditor.setValue(tpl.code);
    setCanvasResolution(tpl.width, tpl.height, tpl.shape);

    // Update select dropdowns
    if (elResolutionSelect) {
      const resKey = `${tpl.width}x${tpl.height}` + (tpl.shape === "round" ? "-round" : tpl.shape === "square" ? "-square" : "");
      if (elResolutionSelect.querySelector(`option[value="${resKey}"]`)) {
        elResolutionSelect.value = resKey;
      }
    }

  }

  function shareCode() {
    if (!monacoEditor || typeof LZString === "undefined") return;
    const code = monacoEditor.getValue();
    const compressed = LZString.compressToEncodedURIComponent(code);
    const shareUrl = `${window.location.origin}${window.location.pathname}#code=${compressed}`;

    navigator.clipboard.writeText(shareUrl).then(() => {
      window.location.hash = `code=${compressed}`;
      showToast("✓ Link copied to clipboard!");
    }).catch(() => {
      prompt("Copy this share URL:", shareUrl);
    });
  }

  // =========================================================================
  // Resizable Split Panes
  // =========================================================================

  function initSplitters() {
    const splitterV = document.getElementById("splitter-v");
    const editorPane = document.getElementById("editor-pane");
    const previewPane = document.getElementById("preview-pane");

    if (splitterV && editorPane && previewPane) {
      let isDragging = false;
      splitterV.addEventListener("mousedown", (e) => {
        isDragging = true;
        splitterV.classList.add("is-dragging");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      });

      window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const totalW = window.innerWidth;
        const newLeftW = Math.max(260, Math.min(e.clientX, totalW - 320));
        const pct = (newLeftW / totalW) * 100;
        editorPane.style.flex = `0 0 ${pct}%`;
        previewPane.style.flex = `0 0 ${100 - pct}%`;
        if (monacoEditor) monacoEditor.layout();
      });

      window.addEventListener("mouseup", () => {
        if (isDragging) {
          isDragging = false;
          splitterV.classList.remove("is-dragging");
          document.body.style.cursor = "";
          document.body.style.userSelect = "";
          if (monacoEditor) monacoEditor.layout();
        }
      });
    }
  }

  // =========================================================================
  // Theme Switching (Dark / Light)
  // =========================================================================

  const THEME_STORAGE_KEY = "pydevices-theme";

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function updateThemeUI(theme) {
    const isLight = theme === "light";
    const themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) {
      themeBtn.innerHTML = isLight
        ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
        : '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
      themeBtn.title = isLight ? "Switch to Dark Theme" : "Switch to Light Theme";
    }
    if (monacoEditor && typeof monaco !== "undefined") {
      monaco.editor.setTheme(isLight ? "vs" : "vs-dark");
    }
  }

  function applyTheme(theme) {
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (e) {}
    updateThemeUI(theme);
  }

  function toggleTheme() {
    const next = currentTheme() === "light" ? "dark" : "light";
    applyTheme(next);
  }

  // =========================================================================
  // DOM Event Bindings
  // =========================================================================

  window.addEventListener("DOMContentLoaded", () => {
    initMonaco();
    initSplitters();

    if (elRunBtn) elRunBtn.addEventListener("click", runScript);
    if (elShareBtn) elShareBtn.addEventListener("click", shareCode);
    if (elClearConsoleBtn) elClearConsoleBtn.addEventListener("click", clearConsole);

    if (elTemplateSelect) {
      elTemplateSelect.addEventListener("change", (e) => loadTemplate(e.target.value));
    }

    if (elResolutionSelect) {
      elResolutionSelect.addEventListener("change", (e) => handleResolutionChange(e.target.value));
    }

    // Switching runtime means a different interpreter, so it is a full remount.
    if (elRuntimeSelect) {
      elRuntimeSelect.addEventListener("change", runScript);
      try {
        const saved = localStorage.getItem(RUNTIME_STORAGE_KEY);
        if (saved && RUNTIMES[saved]) elRuntimeSelect.value = saved === "pyodide" ? "pyodide" : "mpy";
      } catch (e) {}
    }

    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
      themeToggle.addEventListener("click", toggleTheme);
    }
    updateThemeUI(currentTheme());

    window.addEventListener("resize", () => {
      if (monacoEditor) monacoEditor.layout();
    });

    // Always apply a resolution, so window.SIM_WIDTH/SIM_HEIGHT are set before
    // the bootstrap reads them -- the saved-draft path through loadInitialCode()
    // returns without touching the canvas.
    if (!restoreResolution()) {
      const { width, height, shape } = currentResolution;
      setCanvasResolution(width, height, shape);
    }
    syncResolutionSelect();

    // Refresh the environment, run the editor's code, then open the REPL.
    mountRuntime(currentRuntime());
  });
})();
