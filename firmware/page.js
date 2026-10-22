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
  // ESP Web Tools' names for the chips, as the release manifests use them.
  var CHIP_FAMILY = { esp32s3: 'ESP32-S3', esp32p4: 'ESP32-P4', esp32: 'ESP32', esp32c3: 'ESP32-C3',
    esp32c6: 'ESP32-C6', esp32s2: 'ESP32-S2' };
  // Where a merged image, which starts with the bootloader, is written on each chip. A file
  // that does not start with an image header is a whole-flash image and goes at 0x0.
  var BOOT_OFFSET = { esp32s3: '0x0', esp32p4: '0x2000', esp32: '0x1000', esp32c3: '0x0',
    esp32c6: '0x0', esp32s2: '0x1000' };
  // The chip id an image header carries at byte 12 (esp_chip_id_t).
  var CHIP_ID = { 0: 'esp32', 2: 'esp32s2', 5: 'esp32c3', 9: 'esp32s3', 13: 'esp32c6', 18: 'esp32p4' };
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
    holder.appendChild(installButton('manifests/' + b.id + '.json', 'Install ' + kind(b)));
    var hint = 'If the board does not appear in the list, hold BOOT while pressing RESET, then try again. ';
    if (b.chip === 'esp32p4') {
      hint += 'The browser flasher knows the ESP32-P4 but is newer on it than on other chips. If it stops partway, the esptool steps below write the same file.';
    }
    $('fw-install-hint').textContent = hint;
  }

  function esptoolStep() {
    return h('li', {}, 'Install esptool in a virtual environment and activate it, so the ', code('esptool'),
      ' you run is the one you just installed. In each new terminal, activate it again before you run esptool.',
      pre('# Windows\npython -m venv v\nv\\Scripts\\activate\npip install esptool\n\n' +
          '# Linux and macOS\npython3 -m venv v\nsource v/bin/activate\npip install esptool'));
  }

  function installButton(manifest, label) {
    var btn = document.createElement('esp-web-install-button');
    btn.setAttribute('manifest', manifest);
    btn.appendChild(h('button', { slot: 'activate', class: 'btn primary', type: 'button', text: label }));
    btn.appendChild(h('span', { slot: 'unsupported', class: 'fw-muted',
      text: 'This browser can not write to a board. Use Chrome or Edge on a computer, or the esptool steps below.' }));
    btn.appendChild(h('span', { slot: 'not-allowed', class: 'fw-muted',
      text: 'Browsers only allow this on https pages or on localhost. Use the esptool steps below.' }));
    return btn;
  }

  function renderSteps(b) {
    var ol = clear($('fw-steps'));
    var f = mainFile(b);
    var name = f.name;
    var steps = [];
    $('fw-steps-title').textContent = canBrowser(b) ? 'Or with esptool, in any browser' : 'Steps';

    if (isEsp(b)) {
      steps.push(esptoolStep());
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

  // ---- install from a file -------------------------------------------------
  // The chosen file never leaves the computer: it becomes a Blob URL, and so does an
  // ESP Web Tools manifest whose one part names it. ESP Web Tools fetches both the way it
  // fetches a manifest and part from this site.

  var picked = null;   // { file, uf2, head }
  var pickSeq = 0;
  var blobs = [];

  function readHead(file) {
    return file.slice(0, 36).arrayBuffer().then(function (buf) {
      var b = new Uint8Array(buf);
      var image = b.length >= 14 && b[0] === 0xE9;
      var id = image ? b[12] | (b[13] << 8) : null;
      return {
        image: image,
        chip: image && CHIP_ID.hasOwnProperty(id) ? CHIP_ID[id] : '',
        // An application image (micropython.bin) has its descriptor right after the headers.
        app: image && b.length >= 36 && new DataView(buf).getUint32(32, true) === 0xABCD5432,
        padded: b.length > 0 && b[0] === 0xFF
      };
    });
  }

  function fileOffset(chip, head) { return head.image ? BOOT_OFFSET[chip] : '0x0'; }
  function shellName(n) { return /^[\w.+-]+$/.test(n) ? n : '"' + n.replace(/(["\\$`])/g, '\\$1') + '"'; }

  function fileManifest(file, chip, offset) {
    var part = URL.createObjectURL(file);
    var m = {
      name: file.name,
      version: 'from a file',
      new_install_prompt_erase: true,
      new_install_improv_wait_time: 0,
      builds: [{ chipFamily: CHIP_FAMILY[chip], parts: [{ path: part, offset: parseInt(offset, 16) }] }]
    };
    var url = URL.createObjectURL(new Blob([JSON.stringify(m)], { type: 'application/json' }));
    blobs.push(part, url);
    return url;
  }

  function fileNote(text) {
    var n = $('fw-file-note');
    n.textContent = text || '';
    n.hidden = !text;
  }

  function fileCli(text, line) {
    var box = clear($('fw-file-mpftp'));
    box.appendChild(h('p', {}, text));
    box.appendChild(pre(line));
  }

  function renderFile() {
    blobs.forEach(function (u) { URL.revokeObjectURL(u); });
    blobs = [];
    clear($('fw-file-install-button'));
    $('fw-file-out').hidden = true;
    $('fw-file-chip-row').hidden = true;
    fileNote('');
    if (!picked) return;
    var file = picked.file;
    var name = file.name;
    if (picked.uf2) {
      renderFileUf2(name);
      $('fw-file-out').hidden = false;
      return;
    }
    var head = picked.head;
    var chip = $('fw-file-chip').value;
    if (head.app) {
      fileNote(name + ' is an application image, not the merged firmware.bin. Written where the bootloader goes, ' +
        'it leaves the board restarting over and over. Pick the firmware.bin from the same build.');
      return;
    }
    if (head.image && !head.chip) {
      fileNote(name + ' is for a chip this page does not list. mpftp and esptool can write it: both read the chip from the file.');
      return;
    }
    if (!head.image && !head.padded) {
      fileNote(name + ' does not look like ESP32 firmware. Pick the firmware.bin from your build.');
      return;
    }
    $('fw-file-chip-row').hidden = false;
    if (!chip) { fileNote('Choose the chip on your board.'); return; }
    if (head.chip && head.chip !== chip) {
      fileNote(name + ' was built for the ' + CHIP_FAMILY[head.chip] + ', not the ' + CHIP_FAMILY[chip] +
        '. Choose the chip it was built for.');
      return;
    }
    var offset = fileOffset(chip, head);
    var arg = shellName(name);
    fileNote((head.chip ? 'The file says it is for the ' + CHIP_FAMILY[chip] + '. ' : '') +
      'It is written at ' + offset + '.');
    $('fw-file-out').hidden = false;

    var browser = BROWSER_INSTALL[chip] === true;
    $('fw-file-install').hidden = !browser;
    if (browser) {
      $('fw-file-install-text').textContent = 'Chrome or Edge on a computer. Plug the board in, press Install, ' +
        'pick its serial port and confirm. It asks whether to erase the board first: tick that when you come from another firmware. ' +
        'Writing ' + mb(file.size) + ' takes a few minutes; leave the board plugged in until it says it is done.';
      $('fw-file-install-button').appendChild(installButton(fileManifest(file, chip, offset), 'Install this file'));
      $('fw-file-install-hint').textContent = 'If the board does not appear in the list, hold BOOT while pressing RESET, then try again.' +
        (chip === 'esp32p4' ? ' If it stops partway on the ESP32-P4, the esptool steps below write the same file.' : '');
    }

    $('fw-file-steps-title').textContent = browser ? 'Or with esptool, in any browser' : 'Steps';
    var ol = clear($('fw-file-steps'));
    ol.appendChild(esptoolStep());
    ol.appendChild(h('li', {}, 'Write it, from the folder that holds ' + name + '. ' +
      'The port is COM3 or similar on Windows, /dev/ttyACM0 or /dev/ttyUSB0 on Linux, /dev/cu.usbmodem... on macOS. ' +
      'If esptool can not reach the board, put it in download mode: hold BOOT, press and release RESET, then release BOOT.',
      pre('esptool --chip ' + chip + ' --port COM3 write-flash ' + offset + ' ' + arg)));
    ol.appendChild(h('li', {}, 'Coming from another firmware, or want a clean board? Erase the flash first, then write as above (this removes your files):',
      pre('esptool --chip ' + chip + ' --port COM3 erase-flash')));
    fileCli('mpftp writes the same file from a terminal, and reads the chip and the offset from the file itself:',
      'mpftp firmware flash --port esp32 --artifact ' + arg + ' -d COM3');
  }

  function renderFileUf2(name) {
    $('fw-file-install').hidden = true;
    $('fw-file-steps-title').textContent = 'Steps';
    var ol = clear($('fw-file-steps'));
    ol.appendChild(h('li', {}, 'Put the board in its UF2 bootloader. On a Raspberry Pi Pico or another RP2040 or RP2350 board, ' +
      'hold BOOTSEL while you plug it into USB; on most other boards, double-tap RESET. ' +
      'A drive appears, named RPI-RP2, RP2350 or after the board.'));
    ol.appendChild(h('li', {}, 'Copy ' + name + ' onto that drive. The board restarts by itself when the copy finishes.'));
    fileCli('mpftp finds the bootloader drive and copies the file for you. Give your board\'s port: rp2, samd or esp32.',
      'mpftp firmware flash --port rp2 --uf2 --artifact ' + shellName(name));
  }

  function setupFile() {
    var sel = $('fw-file-chip');
    sel.appendChild(h('option', { value: '', text: 'Choose the chip' }));
    Object.keys(CHIP_FAMILY).forEach(function (c) { sel.appendChild(h('option', { value: c, text: CHIP_FAMILY[c] })); });
    sel.addEventListener('change', renderFile);
    $('fw-file-input').addEventListener('change', function (e) {
      var file = e.target.files && e.target.files[0];
      var seq = ++pickSeq;
      picked = null;
      if (!file) { renderFile(); return; }
      if (/\.uf2$/i.test(file.name)) { picked = { file: file, uf2: true }; renderFile(); return; }
      if (!/\.bin$/i.test(file.name)) { renderFile(); fileNote('Pick a .bin or a .uf2 file.'); return; }
      renderFile();
      readHead(file).then(function (head) {
        if (seq !== pickSeq) return;
        picked = { file: file, uf2: false, head: head };
        // A file whose header names no chip gets no choice carried over from an earlier pick.
        sel.value = head.chip || '';
        renderFile();
      }, function (err) {
        if (seq === pickSeq) fileNote('Could not read ' + file.name + ' (' + err.message + ').');
      });
    });
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

  setupFile();

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
