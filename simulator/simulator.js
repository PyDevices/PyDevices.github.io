/**
 * simulator.js — Interactive PyDevices Python Simulator Engine
 *
 * Manages Monaco Editor, direct MicroPython runtime execution,
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
  const elRunBtn = document.getElementById("run-btn");
  const elResetVmBtn = document.getElementById("reset-vm");
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
    const direct = document.getElementById("direct-runtime-output");
    if (direct) direct.textContent = "";
  }

  function showToast(msg) {
    if (!elToast) return;
    elToast.textContent = msg;
    elToast.classList.add("is-active");
    setTimeout(() => elToast.classList.remove("is-active"), 2600);
  }

  function isInstalledPwa() {
    return window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true;
  }

  function showInstallHint() {
    const hint = document.getElementById("install-hint");
    if (hint && !isInstalledPwa() && sessionStorage.getItem("sim-install-hint-dismissed") !== "1") {
      hint.hidden = false;
    }
  }

  async function refreshApplication() {
    const button = document.getElementById("refresh-application");
    if (button) {
      button.disabled = true;
      button.textContent = "Refreshing…";
    }
    persistState();
    try {
      if ("caches" in window) {
        const names = await caches.keys();
        await Promise.all(names
          .filter((name) => name.startsWith("pydevices-simulator-"))
          .map((name) => caches.delete(name)));
      }
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        const simulatorScope = new URL("./", location.href).href;
        await Promise.all(registrations
          .filter((registration) => registration.scope === simulatorScope)
          .map((registration) => registration.unregister()));
      }
    } finally {
      const url = new URL(location.href);
      url.searchParams.set("app-refresh", Date.now().toString());
      location.replace(url.href);
    }
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
  // Direct MicroPython Runtime Mount
  // =========================================================================

  const RESOLUTION_STORAGE_KEY = "pydevices-simulator-resolution";

  let directMicroPython = null;
  let replInput = null;
  let replBusy = false;
  const replHistory = [];
  let replHistoryIndex = 0;

  async function sendReplText(text) {
    if (!directMicroPython || replBusy) return;
    replBusy = true;
    if (replInput) replInput.disabled = true;
    try {
      for (const character of text) {
        await directMicroPython.replProcessCharWithAsyncify(character.charCodeAt(0));
      }
    } finally {
      replBusy = false;
      if (replInput) {
        replInput.disabled = false;
        replInput.focus();
      }
    }
  }

  async function submitRepl(command) {
    if (!command.trim() && replBusy) return;
    if (command.trim()) {
      replHistory.push(command);
      replHistoryIndex = replHistory.length;
    }
    await sendReplText(command + "\r");
  }

  function mountReplControls(host, output) {
    const shell = document.createElement("div");
    shell.className = "sim-repl-shell";
    shell.appendChild(output);

    const form = document.createElement("form");
    form.className = "sim-repl-form";
    const label = document.createElement("label");
    label.htmlFor = "repl-input";
    label.textContent = ">";
    replInput = document.createElement("input");
    replInput.id = "repl-input";
    replInput.className = "sim-repl-input";
    replInput.type = "text";
    replInput.autocomplete = "off";
    replInput.autocapitalize = "off";
    replInput.spellcheck = false;
    replInput.disabled = true;
    replInput.setAttribute("aria-label", "MicroPython REPL command");
    form.append(label, replInput);
    shell.appendChild(form);
    host.replaceChildren(shell);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const command = replInput.value;
      replInput.value = "";
      await submitRepl(command);
    });
    replInput.addEventListener("keydown", (event) => {
      if (event.key === "ArrowUp") {
        event.preventDefault();
        if (replHistoryIndex > 0) replHistoryIndex -= 1;
        replInput.value = replHistory[replHistoryIndex] || "";
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        if (replHistoryIndex < replHistory.length) replHistoryIndex += 1;
        replInput.value = replHistory[replHistoryIndex] || "";
      } else if (event.ctrlKey && event.key.toLowerCase() === "c") {
        event.preventDefault();
        sendReplText("\x03");
      } else if (event.ctrlKey && event.key.toLowerCase() === "d") {
        event.preventDefault();
        sendReplText("\x04");
      }
    });
  }

  async function mountRuntime() {
    const host = document.getElementById("console-log");
    if (!host) return;

    setStatus("Refreshing environment…", "busy");
    const output = document.createElement("pre");
    output.id = "direct-runtime-output";
    output.className = "sim-direct-output";
    mountReplControls(host, output);
    const decoder = new TextDecoder();
    const write = (chunk, stream) => {
      const text = typeof chunk === "string" ? chunk : decoder.decode(chunk, { stream: true });
      output.textContent += text;
      output.scrollTop = output.scrollHeight;
      if (stream === "stderr") console.error(text);
    };
    try {
      const mipIndex = "https://PyDevices.github.io/mip";
      const { loadMicroPython } = await import("/vendor/micropython/micropython.mjs");
      directMicroPython = await loadMicroPython({
        stdout: (line) => write(line, "stdout"),
        stderr: (line) => write(line, "stderr"),
        heapsize: 16 * 1024 * 1024,
        linebuffer: false
      });
      await directMicroPython.runPythonAsync(`
import os, sys
from displaydev import env_set
env_set("PYDEVICES_WIDTH", ${Number(window.SIM_WIDTH)})
env_set("PYDEVICES_HEIGHT", ${Number(window.SIM_HEIGHT)})
sys.path[:] = [".", ".frozen", "lib", "utils"]
import mip
mip.install("pydevices-desktop", index=${JSON.stringify(mipIndex)}, target="lib")
os.chdir("/")
`);
      directMicroPython.replInit();
      replInput.disabled = false;
      replInput.focus();
      window.__pydevicesSimulator = {
        phase: "ready",
        runtime: "micropython",
        mp: directMicroPython,
        runEditor: runScript,
        sendRepl: submitRepl
      };
      setStatus("Ready", "ready");
    } catch (err) {
      write(String(err && (err.stack || err)), "stderr");
      window.__pydevicesSimulator = { phase: "failed", runtime: "micropython", error: String(err) };
      setStatus("Runtime error", "error");
    }
  }

  // Execute the editor through the REPL so it uses the persistent __main__
  // namespace. Imports and assignments remain available at the next prompt.
  async function runScript() {
    if (!directMicroPython || replBusy) return;
    persistState();
    const source = window.getEditorCode();
    directMicroPython.FS.writeFile("/main.py", source);
    setStatus("Running…", "busy");
    if (elRunBtn) elRunBtn.disabled = true;
    try {
      await submitRepl(
        "exec(compile(open('/main.py').read(), '/main.py', 'exec'), globals(), globals())"
      );
    } finally {
      if (elRunBtn) elRunBtn.disabled = false;
      setStatus("Ready", "ready");
    }
  }

  function resetVm() {
    persistState();
    window.location.reload();
  }

  async function enableAudio(microphone) {
    const button = document.getElementById(microphone ? "enable-microphone" : "enable-audio");
    if (!window.Module || !Module.pydevicesBridge) {
      showToast("Direct MicroPython must be running");
      return;
    }
    button.disabled = true;
    try {
      const permission = await Promise.race([
        Module.pydevicesBridge.enableAudio(microphone),
        new Promise((_, reject) => setTimeout(() => reject(new Error("Permission timed out")), 5000))
      ]);
      if (!permission.audio || (microphone && !permission.microphone)) throw new Error("Permission not granted");
      button.textContent = microphone ? "Microphone Enabled" : "Audio Enabled";
    } catch (err) {
      button.disabled = false;
      showToast(String(err.message || err));
    }
  }

  function persistState() {
    try {
      if (monacoEditor) localStorage.setItem("pydevices-simulator-code", monacoEditor.getValue());
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
    if (elResetVmBtn) elResetVmBtn.addEventListener("click", resetVm);
    if (elShareBtn) elShareBtn.addEventListener("click", shareCode);
    if (elClearConsoleBtn) elClearConsoleBtn.addEventListener("click", clearConsole);
    document.getElementById("refresh-application")?.addEventListener("click", refreshApplication);
    document.getElementById("dismiss-install-hint")?.addEventListener("click", () => {
      const hint = document.getElementById("install-hint");
      if (hint) hint.hidden = true;
      sessionStorage.setItem("sim-install-hint-dismissed", "1");
    });
    window.addEventListener("beforeinstallprompt", showInstallHint);
    window.addEventListener("appinstalled", () => {
      const hint = document.getElementById("install-hint");
      if (hint) hint.hidden = true;
    });
    document.getElementById("enable-audio")?.addEventListener("click", () => enableAudio(false));
    document.getElementById("enable-microphone")?.addEventListener("click", () => enableAudio(true));

    if (elTemplateSelect) {
      elTemplateSelect.addEventListener("change", (e) => loadTemplate(e.target.value));
    }

    if (elResolutionSelect) {
      elResolutionSelect.addEventListener("change", (e) => handleResolutionChange(e.target.value));
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
    // Register PWA Service Worker
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("./sw.js", { updateViaCache: "none" }).then((registration) => {
          registration.update();
        }).catch((err) => {
          console.warn("[Simulator] ServiceWorker registration failed:", err);
        });
      });
    }

    // Refresh the environment, then open a REPL before editor code is run.
    mountRuntime();
  });
})();
