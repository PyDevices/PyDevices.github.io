// The download page: reads firmware.json (and interpreters.json, when there is one)
// from this folder and writes the steps for the board you pick. No framework.
// Everything it fetches is relative, so the folder can move with the site.
(function () {
  'use strict';

  var RELEASES = 'https://github.com/PyDevices/micropython-pydevices/releases/download/';
  var REPO = 'PyDevices/micropython-pydevices';
  var INTERP_RELEASES = 'https://github.com/PyDevices/pydevices/releases/download/';
  var MIP = 'https://pydevices.github.io/mip/';
  // Chips the browser flasher (ESP Web Tools) can write. Set a chip to false to send its
  // boards to the esptool steps alone.
  var BROWSER_INSTALL = { esp32s3: true, esp32p4: true };
  var ROLES = {
    flash: 'Flash image: the file to write',
    uf2: 'UF2: the file to copy',
    app: 'App image only',
    partitions: 'Partition table',
    elf: 'ELF, for backtraces and core dumps',
    map: 'Link map'
  };

  var doc = null;
  var interp = null;

  function h(tag, props) {
    var e = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      if (k === 'text') e.textContent = props[k];
      else e.setAttribute(k, props[k]);
    });
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null) continue;
      e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return e;
  }
  function $(id) { return document.getElementById(id); }
  function clear(e) { while (e.firstChild) e.removeChild(e.firstChild); return e; }
  function link(href, text) { return h('a', { href: href }, text); }
  function code(text) { return h('code', {}, text); }
  function pre(text) { return h('pre', {}, h('code', {}, text)); }
  function mb(n) { return n >= 1048576 ? (n / 1048576).toFixed(2) + ' MB' : Math.round(n / 1024) + ' KB'; }
  function kind(b) { return b.interpreter === 'micropython' ? 'MicroPython' : 'CircuitPython-compatible'; }
  function modules(b) { return b.modules === 'all' ? 'every PyDevices module' : b.modules.replace(/@/g, '').split(',').join(', '); }
  function fileOf(b, role) { return b.files.filter(function (f) { return f.role === role; })[0]; }
  function mainFile(b) { return fileOf(b, 'flash') || fileOf(b, 'uf2'); }
  function isEsp(b) { return b.flash_offset != null && /^esp32/.test(b.chip); }
  function canBrowser(b) { return isEsp(b) && BROWSER_INSTALL[b.chip] === true; }
  function local(f) { return 'files/' + f.name; }
  function remote(f) { return RELEASES + doc.tag + '/' + f.name; }
  function fileHref(f) { return f.role === 'flash' || f.role === 'uf2' ? local(f) : remote(f); }

  function get(url, optional) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) {
      if (r.status === 404 && optional) return null;
      if (!r.ok) throw new Error(url + ' answered ' + r.status);
      return r.json();
    });
  }

  // ---- the set -------------------------------------------------------------

  function renderSet() {
    var box = $('fw-set');
    clear(box);
    box.hidden = false;
    box.className = 'fw-set' + (doc.preview ? ' staged' : '');
    if (doc.preview) {
      box.appendChild(h('p', {}, h('strong', {}, 'Staged preview, not a release. '),
        'This set is built from preview versions (' + doc.preview_reasons.join('; ') +
        '), so it is not released and its downloads may change or disappear.'));
    }
    box.appendChild(h('p', {}, 'Set ', code(doc.tag), ': MicroPython ' + doc.micropython +
      (doc.circuitpython ? ' and CircuitPython-compatible ' + doc.circuitpython : '') +
      ', built ' + doc.built.slice(0, 10) + ' by ', link(doc.run, 'this CI run'), '.'));
  }

  function renderPins() {
    var box = clear($('fw-pins'));
    var rows = [['MicroPython', doc.pins.UPSTREAM]];
    Object.keys(doc.pins['deps.lock']).forEach(function (k) { rows.push([k, doc.pins['deps.lock'][k]]); });
    Object.keys(doc.pins['modules.lock']).forEach(function (k) { rows.push([k + ' (module)', doc.pins['modules.lock'][k]]); });
    if (doc.pins['lvgl-circuitpython']) rows.push(['lvgl-circuitpython (module)', doc.pins['lvgl-circuitpython']]);
    var t = h('table', { class: 'fw-table' });
    rows.forEach(function (r) {
      t.appendChild(h('tr', {}, h('th', { text: r[0] }), h('td', { class: 'hash', text: r[1] })));
    });
    box.appendChild(h('p', { class: 'fw-muted' }, 'Every build in a set comes from the same checkout of ',
      link('https://github.com/' + REPO, REPO), '. These are the versions it pinned; ',
      link('firmware.json', 'firmware.json'), ' has the rest, including the commit of each module in each build.'));
    box.appendChild(t);
  }

  // ---- one board -----------------------------------------------------------

  function selectBuild(id, fromHash) {
    var b = doc.builds.filter(function (x) { return x.id === id; })[0] || doc.builds[0];
    $('fw-board').value = b.id;
    if (!fromHash) {
      try { history.replaceState(null, '', '#' + b.id); } catch (e) {}
    }
    renderBuild(b);
  }

  function renderBuild(b) {
    var f = mainFile(b);
    $('fw-out').hidden = false;
    $('fw-build-note').textContent = kind(b) + ' ' + b.interpreter_version.replace(/-dirty$/, '') +
      ' with ' + modules(b) + '. Flash image ' + mb(f.size) + '.';
    renderInstall(b);
    renderSteps(b);
    renderFiles(b);
  }

  function renderInstall(b) {
    var box = $('fw-install');
    var holder = clear($('fw-install-button'));
    if (!canBrowser(b)) { box.hidden = true; return; }
    box.hidden = false;
    var f = fileOf(b, 'flash');
    clear($('fw-install-text')).appendChild(document.createTextNode(
      'Chrome or Edge on a computer. Plug the board in, press Install, pick its serial port and confirm. ' +
      'It asks whether to erase the board first: tick that when you come from another firmware. ' +
      'Writing ' + mb(f.size) + ' takes a few minutes; leave the board plugged in until it says it is done.'));
    var btn = document.createElement('esp-web-install-button');
    btn.setAttribute('manifest', 'manifests/' + b.id + '.json');
    btn.appendChild(h('button', { slot: 'activate', class: 'btn primary', type: 'button', text: 'Install ' + kind(b) }));
    btn.appendChild(h('span', { slot: 'unsupported', class: 'fw-muted',
      text: 'This browser can not write to a board. Use Chrome or Edge on a computer, or the esptool steps below.' }));
    btn.appendChild(h('span', { slot: 'not-allowed', class: 'fw-muted',
      text: 'Browsers only allow this on https pages or on localhost. Use the esptool steps below.' }));
    holder.appendChild(btn);
    var hint = 'If the board does not appear in the list, hold BOOT while pressing RESET, then try again. ';
    if (b.chip === 'esp32p4') {
      hint += 'The browser flasher knows the ESP32-P4 but is newer on it than on other chips. If it stops partway, the esptool steps below write the same file.';
    }
    $('fw-install-hint').textContent = hint;
  }

  function renderSteps(b) {
    var ol = clear($('fw-steps'));
    var f = mainFile(b);
    var name = f.name;
    var steps = [];
    $('fw-steps-title').textContent = canBrowser(b) ? 'Or with esptool, in any browser' : 'Steps';

    if (isEsp(b)) {
      steps.push(h('li', {}, 'Install esptool in a virtual environment and activate it, so the ', code('esptool'),
        ' you run is the one you just installed. In each new terminal, activate it again before you run esptool.',
        pre('# Windows\npython -m venv v\nv\\Scripts\\activate\npip install esptool\n\n' +
            '# Linux and macOS\npython3 -m venv v\nsource v/bin/activate\npip install esptool')));
      steps.push(h('li', {}, link(local(f), 'Download ' + name), ' (' + mb(f.size) + '), then write it. ' +
        'The port is COM3 or similar on Windows, /dev/ttyACM0 or /dev/ttyUSB0 on Linux, /dev/cu.usbmodem... on macOS. ' +
        'On a board with two USB ports, use the one wired to the serial chip, usually marked UART. ',
        'If esptool can not reach the board and its USB port goes straight to the chip ' +
        '(the LilyGO T-Embed S3 and the native port of the ESP32-S3-Touch-LCD-7 do), put it in download mode first: ' +
        'hold BOOT, press and release RESET, then release BOOT. The port\'s COM number can change in download mode, so check which port it is now. ',
        'If your board\'s USB-serial bridge takes a faster speed, add ', code('--baud 921600'),
        ' after the port to shorten the write; the line below works without it, only slower.',
        pre('esptool --chip ' + b.chip + ' --port COM3 write-flash ' + b.flash_offset + ' ' + name)));
      steps.push(h('li', {}, 'Coming from another firmware, or want a clean board? Erase the flash first, then write as above (this removes your files):',
        pre('esptool --chip ' + b.chip + ' --port COM3 erase-flash')));
    } else {
      steps.push(h('li', {}, 'Put the board in its bootloader: hold BOOTSEL while you plug it into USB. ' +
        'A drive named RPI-RP2 appears.'));
      steps.push(h('li', {}, link(local(f), 'Download ' + name), ' (' + mb(f.size) + ') and copy it onto that drive. ' +
        'The board restarts by itself when the copy finishes.'));
    }
    if (b.interpreter === 'micropython') {
      steps.push(h('li', {}, 'Check it. Install mpremote, open the REPL and print the version:',
        pre('pip install mpremote\nmpremote\n>>> import sys; print(sys.version)'),
        'It starts with ', code('3.4.0; MicroPython ' + b.interpreter_version), ', then a build number and the commit, ',
        'for example ', code('v1.30.0-preview.160.gb70ae1aca6'), ', and the build date.'));
    } else {
      steps.push(h('li', {}, 'Check it. A drive named CIRCUITPY appears. Open the board\'s serial port in any terminal ' +
        '(Thonny, or ', code('python -m serial.tools.miniterm'), '), press a key, and print the version:',
        pre('>>> import sys; print(sys.version)'),
        'It starts with ', code('3.4.0; CircuitPython ' + b.interpreter_version), ' and ends with the build date.'));
    }
    steps.push(h('li', {}, 'Next, install your board\'s package from the ', link(MIP, 'mip index'), '.'));
    steps.forEach(function (s) { ol.appendChild(s); });
  }

  function renderFiles(b) {
    var t = clear($('fw-files'));
    t.appendChild(h('tr', {}, h('th', { text: 'What' }), h('th', { text: 'File' }),
      h('th', { text: 'Size' }), h('th', { text: 'sha256' })));
    var order = ['flash', 'uf2', 'app', 'partitions', 'elf', 'map'];
    var onRelease = false;
    order.forEach(function (role) {
      var f = fileOf(b, role);
      if (!f) return;
      var here = role === 'flash' || role === 'uf2';
      if (!here) onRelease = true;
      t.appendChild(h('tr', {}, h('td', { text: ROLES[role] }),
        h('td', {}, link(fileHref(f), f.name)),
        h('td', { class: 'num', text: mb(f.size) }), h('td', { class: 'hash', text: f.sha256 })));
    });
    var note = 'The flash image is served from this site. ';
    if (onRelease) {
      note += 'The rest are on the set\'s Release' + (doc.preview ? ', which is still a draft that only the maintainers can open' : '') + '.';
    }
    var app = fileOf(b, 'app');
    if (app && b.app_offset) {
      note += ' To update a board that already runs a build with this layout without touching its other partitions, write the app image alone: esptool --chip ' +
        b.chip + ' --port COM3 write-flash ' + b.app_offset + ' ' + app.name + '.';
    }
    $('fw-files-note').textContent = note;
    $('fw-verify').textContent = 'gh attestation verify ' + mainFile(b).name + ' --repo ' + REPO;
  }

  // ---- desktop interpreters ------------------------------------------------

  function renderInterp() {
    var box = clear($('fw-interp'));
    if (!interp) {
      box.appendChild(h('p', { class: 'fw-muted' }, 'The desktop interpreters go out with each final release of pydevices. ' +
        'The newest final does not carry them yet, so they appear here with the next one.'));
      return;
    }
    box.appendChild(h('p', { class: 'prose' }, 'From pydevices ', code(interp.tag), ', the newest final release with them. ',
      link('https://github.com/PyDevices/pydevices/releases/tag/' + interp.tag, 'Release notes'), '.'));
    var t = h('table', { class: 'fw-table' });
    t.appendChild(h('tr', {}, h('th', { text: 'File' }), h('th', { text: 'Platform' }), h('th', { text: 'Version' }),
      h('th', { text: 'Size' }), h('th', { text: 'sha256' })));
    Object.keys(interp.files).forEach(function (name) {
      var f = interp.files[name];
      t.appendChild(h('tr', {}, h('td', {}, link(INTERP_RELEASES + interp.tag + '/' + name, name)),
        h('td', { text: f.platform }), h('td', { text: f.version }),
        h('td', { class: 'num', text: mb(f.size) }), h('td', { class: 'hash', text: f.sha256 })));
    });
    box.appendChild(h('div', { class: 'fw-scroll' }, t));
  }

  // ---- start ---------------------------------------------------------------

  function fail(e) {
    var box = $('fw-set');
    box.hidden = false;
    box.className = 'fw-warn';
    box.textContent = 'Could not load the firmware list (' + e.message + '). Serve this folder over http, ' +
      'for example python3 -m http.server from the site\'s root, instead of opening the file directly.';
    $('fw-board').innerHTML = '';
  }

  Promise.all([get('firmware.json'), get('interpreters.json', true)]).then(function (r) {
    doc = r[0];
    interp = r[1];
    var sel = $('fw-board');
    clear(sel);
    doc.builds.slice().sort(function (a, b) {
      return a.label.localeCompare(b.label) || a.interpreter.localeCompare(b.interpreter);
    }).forEach(function (b) {
      sel.appendChild(h('option', { value: b.id, text: b.label + ' - ' + kind(b) }));
    });
    sel.disabled = false;
    sel.addEventListener('change', function () { selectBuild(sel.value, false); });
    renderSet();
    renderPins();
    renderInterp();
    selectBuild(location.hash.slice(1), true);
    window.addEventListener('hashchange', function () { selectBuild(location.hash.slice(1), true); });
  }).catch(fail);
})();
