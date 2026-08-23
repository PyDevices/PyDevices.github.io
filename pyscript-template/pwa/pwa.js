(function () {
  var installButton = document.getElementById('install');
  var deferredPrompt = null;

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js', {scope: './'}).catch(console.error);
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    installButton.hidden = false;
  });

  installButton.addEventListener('click', function () {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    deferredPrompt.userChoice.finally(function () {
      deferredPrompt = null;
      installButton.hidden = true;
    });
  });

  window.addEventListener('appinstalled', function () {
    installButton.hidden = true;
  });
})();
