ESP Web Tools 10.4.0 (esp-web-tools on npm, Apache-2.0, LICENSE beside this file),
the dist/web/ folder as published, unmodified. It carries esptool-js 0.7.0 and the
stub loaders for each chip. The download page loads install-button.js from here, so
the browser flasher runs from this site and fetches no script from a CDN.
To update: npm pack esp-web-tools@<version>, replace the .js files with package/dist/web/*.js.
