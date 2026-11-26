/** Direct MicroPython host for generated OmniPython hero applications. */
(function () {
  const state = { phase: "idle", heroes: [], errors: [] };
  window.__omnipythonHeroes = state;

  // Browsers require a user gesture before unlocking Web Audio. Most heroes
  // never touch audio and this is a no-op for them; the one that does (the
  // omnipython signal generator) just needs this armed so its first click
  // both unlocks audio and toggles the tone in the same gesture.
  let audioGestureArmed = false;
  function armAudioGesture() {
    if (audioGestureArmed) return;
    audioGestureArmed = true;
    // A gesture while the page is still loading finds no runtime to unlock, so
    // the listeners stay until one works.
    const tryEnable = () => {
      globalThis.Module?.omnipythonBridge?.enableAudio(false)?.then(() => {
        document.removeEventListener("pointerdown", tryEnable);
        document.removeEventListener("keydown", tryEnable);
      }).catch(() => {});
    };
    document.addEventListener("pointerdown", tryEnable);
    document.addEventListener("keydown", tryEnable);
  }
  armAudioGesture();
  // A hero names either one app (data-hero-app), which the shared runtime in
  // /vendor/micropython/ fetches and runs, or a home screen (data-hero-home),
  // which boots the apps repository's launcher from the all-apps runtime that
  // apps.omnipython.org publishes: every app is frozen into it, so nothing
  // else is fetched, and the hero always runs the newest published build.
  const HOME_RUNTIME = "https://apps.omnipython.org/micropython.mjs";
  const APP_NAME = /^[a-z0-9_]+$/;
  async function launch(container) {
    const canvasId = container.dataset.heroCanvas || "hero_canvas";
    const home = container.dataset.heroHome || "";
    const appName = home || container.dataset.heroApp || "watch";
    const canvas = container.querySelector("canvas");
    const canvasWidth = (canvas && canvas.width) || 240;
    const canvasHeight = (canvas && canvas.height) || 240;
    const status = container.querySelector(".hero-canvas-status");
    const setStatus = (text) => { if (status) status.textContent = text; };
    const record = { app: appName, home: home || null, canvas: canvasId, phase: "loading" };
    state.heroes.push(record); state.phase = "loading";
    try {
      if (!APP_NAME.test(appName)) throw new Error(`${appName} is not an app's name`);
      if (home) record.mp = await bootHome(container, canvasId, canvasWidth, canvasHeight, home, setStatus);
      else await bootApp(canvasId, canvasWidth, canvasHeight, appName, setStatus, record);
      record.phase = "ready";
      container.classList.add("active");
      if (status) status.remove();
      state.phase = state.heroes.every((hero) => hero.phase === "ready") ? "ready" : "loading";
      window.dispatchEvent(new CustomEvent("omnipython-heroes-ready", { detail: record }));
    } catch (error) {
      record.phase = "failed"; record.error = String(error && (error.stack || error));
      state.errors.push(record.error); state.phase = "failed";
      setStatus("Live preview offline"); console.error("Direct hero failed:", error);
      window.dispatchEvent(new CustomEvent("omnipython-heroes-failed", { detail: record }));
    }
  }
  function env(canvasId, width, height) {
    return `
from boarddev import env_set
env_set("OMNIPYTHON_CANVAS_ID", ${JSON.stringify(canvasId)})
env_set("OMNIPYTHON_WIDTH", ${JSON.stringify(String(width))})
env_set("OMNIPYTHON_HEIGHT", ${JSON.stringify(String(height))})
env_set("OMNIPYTHON_TZ_OFFSET_MIN", ${JSON.stringify(String(new Date().getTimezoneOffset()))})
`;
  }
  async function bootApp(canvasId, canvasWidth, canvasHeight, appName, setStatus, record) {
      setStatus("Booting direct MicroPython…");
      const { loadMicroPython } = await import("/vendor/micropython/micropython.mjs");
      const mp = await loadMicroPython({
        stdout: (line) => console.log(`[${appName}] ${line}`),
        stderr: (line) => console.error(`[${appName}] ${line}`),
        heapsize: 16 * 1024 * 1024
      });
      setStatus(`Loading ${appName}…`);
      const response = await fetch(`/assets/apps/${appName}.py`, { cache: "no-store" });
      if (!response.ok) throw new Error(`${response.status} fetching ${appName}.py`);
      mp.FS.writeFile(`/${appName}.py`, await response.text());
      await mp.runPythonAsync(`
import os, sys
if "/" not in sys.path: sys.path.insert(0, "/")
os.chdir("/")
# The OmniPython stack and the desktop board_config are frozen into the
# runtime; nothing is installed. A runtime without them fails right here.
${env(canvasId, canvasWidth, canvasHeight)}
__import__(${JSON.stringify(appName)})
`);
      record.mp = mp;
  }
  // The launcher as a board's main.py starts it, with *home* as its home
  // screen. data-hero-round="1" says the screen is round, as a round panel's
  // board config does. data-hero-apps, a list of names, is what the home
  // screen offers: every other app is hidden from it.
  async function bootHome(container, canvasId, canvasWidth, canvasHeight, home, setStatus) {
    const round = container.dataset.heroRound === "1";
    const apps = (container.dataset.heroApps || "").split(/[\s,]+/).filter((name) => APP_NAME.test(name));
    setStatus("Booting direct MicroPython…");
    const { loadMicroPython } = await import(HOME_RUNTIME);
    const mp = await loadMicroPython({
      stdout: (line) => console.log(`[${home}] ${line}`),
      stderr: (line) => console.error(`[${home}] ${line}`),
      heapsize: 32 * 1024 * 1024,
      pystack: 16 * 1024
    });
    await mp.runPythonAsync(`
import os
os.chdir("/")
${env(canvasId, canvasWidth, canvasHeight)}
import board_config
board_config.display_drv.round = ${round ? "True" : "False"}
import appkit
from display_driver import app
from touchkit import shell
shell.quiet_app_timers(app)
launcher = shell.TouchLauncher(app, home=${JSON.stringify(home)})
launcher.scan("apps")
if ${JSON.stringify(home)} not in launcher.names:
    raise ImportError("this runtime has no app called " + ${JSON.stringify(home)})
offered = ${JSON.stringify(apps)}
if offered:
    for name in launcher.names:
        if name not in offered and name != launcher.home:
            launcher.hide(name, "not on this page")
launcher.shell = shell.TouchShell(launcher)
shell.launcher = launcher
launcher.boot(launcher.home)
`);
    // The launcher's main loop runs on, and returns only if an app ends it.
    mp.runPythonAsync("appkit.serve()").catch((error) => console.error(`[${home}]`, error));
    return mp;
  }
  function start() { document.querySelectorAll("[data-hero-canvas]").forEach(launch); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
