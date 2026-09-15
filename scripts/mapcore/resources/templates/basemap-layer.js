/* Basemap-only adapters; business features remain in Leaflet. */
(function () {
  "use strict";
  function policyIssue(config, protocol) {
    var url;
    try { url = new URL(config.url); } catch (_) { return "url"; }
    var host = url.hostname.toLowerCase();
    if (host === "basemaps.cartocdn.com" || host.endsWith(".basemaps.cartocdn.com")) {
      var key = (url.searchParams.get("key") || "").trim();
      if (!key || /^(your_key|your_api_key)$/i.test(key) || key.indexOf("{") >= 0) { return "key"; }
    }
    if ((host === "tile.openstreetmap.org" || host.endsWith(".tile.openstreetmap.org")) &&
        protocol !== "https:" && protocol !== "http:") { return "local"; }
    return "";
  }

  function create(map, config, notify) {
    var layer = null, gl = null, disposed = false, timer = null, ready = false, errors = 0;
    var start = performance.now();
    function state(status, code) {
      if (!disposed) { notify({ status: status, code: code || "", errors: errors,
        renderer: config.kind === "vector" ? "maplibre" : "leaflet",
        elapsed_ms: Math.round(performance.now() - start) }); }
    }
    function clearTimer() { if (timer !== null) { clearTimeout(timer); timer = null; } }
    function loaded() { if (disposed) { return; } ready = true; clearTimer(); state("ready"); }
    function failed(code) { clearTimer(); state("unavailable", code); }
    function resourceError(event) {
      if (disposed) { return; }
      errors += 1;
      var code = event && event.error && event.error.status;
      if (code === 401 || code === 403 || errors >= 3) { failed("network"); }
      else { state("degraded", "network"); }
    }
    function attach() {
      if (disposed) { return; }
      var issue = policyIssue(config, location.protocol);
      if (issue) { failed(issue); return; }
      state("loading");
      timer = setTimeout(function () { failed("timeout"); }, 20000);
      try {
        if (config.kind === "vector") {
          if (!window.maplibregl || !L.maplibreGL) { failed("renderer"); return; }
          layer = L.maplibreGL({style: config.url, pane: "tilePane", interactive: false,
            attributionControl: false, maxZoom: config.max_zoom || 20});
          // Leaflet must finish deregistering a layer even if WebGL construction fails.
          var removeVector = layer.onRemove;
          layer.onRemove = function (owner) {
            if (this.getMaplibreMap()) { removeVector.call(this, owner); }
            else {
              var container = this.getContainer();
              if (container && container.parentNode) { container.remove(); }
            }
          };
          layer.addTo(map);
          gl = layer.getMaplibreMap();
          gl.on("idle", function () {
            if (!ready && errors === 0 && gl.isStyleLoaded() && gl.loaded()) { loaded(); }
          });
          gl.on("error", resourceError);
          gl.on("webglcontextlost", function () { failed("webgl"); });
          layer.getContainer().style.pointerEvents = "none";
        } else {
          layer = L.tileLayer(config.url, {minZoom: 0, maxZoom: config.max_zoom || 19,
            attribution: "", referrerPolicy: "strict-origin-when-cross-origin"});
          layer.on("tileerror", resourceError);
          layer.on("tileload", function () { if (!ready) { loaded(); } });
          layer.addTo(map);
          if (layer.bringToBack) { layer.bringToBack(); }
        }
      } catch (_) { failed("renderer"); }
    }
    // Leaflet may not have a center until business-layer bounds are fitted.
    map.whenReady(attach);
    return {
      remove: function () {
        disposed = true; clearTimer(); map.off("load", attach);
        if (layer && map.hasLayer(layer)) {
          try { map.removeLayer(layer); } catch (_) {
            if (gl) { try { gl.remove(); } catch (ignored) {} }
            var node = layer.getContainer && layer.getContainer();
            if (node && node.parentNode) { node.remove(); }
          }
        }
        layer = null; gl = null;
      },
      summary: function () {
        if (!gl || disposed) { return null; }
        return {zoom: gl.getZoom(), center: gl.getCenter().toArray(),
          rendered_features: gl.queryRenderedFeatures().length, loaded: gl.loaded()};
      }
    };
  }
  window.IMBBasemapLayer = {create: create, policyIssue: policyIssue};
})();
