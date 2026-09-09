(function () {
  "use strict";

  var IMB = window.InteractiveMapBuilder;
  var MAX_BYTES = 1024 * 1024;
  var pristineRoot = null;
  var originalReady = IMB.onReady;

  // Capture the parsed source before any ready callback constructs runtime DOM.
  // Export this clean source, never a running Leaflet tree or browser-local history.
  IMB.onReady = function (callback) {
    originalReady(function () {
      if (!pristineRoot) {
        pristineRoot = document.documentElement.cloneNode(true);
      }
      callback();
    });
  };

  function plain(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }
  function keys(value, names) {
    return plain(value) && Object.keys(value).length === names.length &&
      names.every(function (name) {
        return Object.prototype.hasOwnProperty.call(value, name);
      });
  }
  function finite(value) {
    return typeof value === "number" && Number.isFinite(value);
  }
  function string(value) {
    return typeof value === "string" && value.length <= 8192;
  }
  function options(node) {
    return Array.from(node.options).map(function (option) { return option.value; });
  }
  function safeJSON(value) {
    return JSON.stringify(value).replace(/&/g, "\\u0026").replace(/</g, "\\u003c")
      .replace(/>/g, "\\u003e").replace(/\u2028/g, "\\u2028").replace(/\u2029/g, "\\u2029");
  }
  function panelValue(id) {
    var node = document.getElementById(id);
    return Boolean(node && node.getAttribute("aria-expanded") === "false");
  }
  function setPanel(id, collapsed) {
    var node = document.getElementById(id);
    if (node && panelValue(id) !== collapsed) { node.click(); }
  }

  function captureView(api) {
    var view = { search: api.search.value, selected_id: api.state.selectedId };
    if (api.template === "multilayer") {
      view.active_layer = api.state.activeLayerId;
      view.layers = api.runtimeLayers.map(function (layer) {
        return { id: layer.id, visible: layer.enabled };
      });
    } else {
      view.sort_field = api.sortSelect.value;
      view.ascending = api.state.ascending;
      view.filters = api.filterModels.map(function (model) {
        var result = { field: model.field, type: model.type };
        if (model.type === "chips") { result.values = Array.from(model.selected); }
        else if (model.type === "select") { result.value = model.value; }
        else { result.low = model.low; result.high = model.high; }
        return result;
      });
    }
    return view;
  }

  function validView(view, api) {
    if (!plain(view) || !string(view.search) || !string(view.selected_id)) { return false; }
    if (api.template === "multilayer") {
      return keys(view, ["search", "selected_id", "active_layer", "layers"]) &&
        (view.selected_id === "" || api.registry.has(view.selected_id)) &&
        (view.active_layer === "" || api.runtimeLayers.some(function (layer) {
          return layer.id === view.active_layer;
        })) && Array.isArray(view.layers) && view.layers.length === api.runtimeLayers.length &&
        view.layers.every(function (layer, index) {
          return keys(layer, ["id", "visible"]) && layer.id === api.runtimeLayers[index].id &&
            typeof layer.visible === "boolean" && (layer.id !== view.active_layer || layer.visible);
        }) && (view.active_layer !== "" || view.search === "");
    }
    return keys(view, ["search", "selected_id", "sort_field", "ascending", "filters"]) &&
      (view.selected_id === "" || api.recordById.has(view.selected_id)) &&
      (options(api.sortSelect).indexOf(view.sort_field) !== -1 ||
        (!api.sortSelect.options.length && view.sort_field === "")) &&
      typeof view.ascending === "boolean" && Array.isArray(view.filters) &&
      view.filters.length === api.filterModels.length && view.filters.every(function (filter, index) {
        var model = api.filterModels[index];
        if (!plain(filter) || filter.field !== model.field || filter.type !== model.type) { return false; }
        if (model.type === "chips") {
          return keys(filter, ["field", "type", "values"]) && Array.isArray(filter.values) &&
            new Set(filter.values).size === filter.values.length && filter.values.every(function (value) {
              return model.values.indexOf(value) !== -1;
            });
        }
        if (model.type === "select") {
          return keys(filter, ["field", "type", "value"]) && options(model.node).indexOf(filter.value) !== -1;
        }
        return keys(filter, ["field", "type", "low", "high"]) &&
          finite(filter.low) && finite(filter.high) && filter.low <= filter.high;
      });
  }

  function applyView(view, api) {
    api.clearSelection();
    if (api.template === "multilayer") {
      api.setActiveLayer("");
      view.layers.forEach(function (layer, index) {
        var checkbox = Array.from(document.querySelectorAll("#imb-layer-options input")).find(function (node) {
          return node.dataset.layerId === layer.id;
        });
        if (checkbox) { checkbox.checked = layer.visible; }
        api.setLayerEnabled(api.runtimeLayers[index], layer.visible);
      });
      api.setActiveLayer(view.active_layer);
    } else {
      api.sortSelect.value = view.sort_field;
      api.state.ascending = view.ascending;
      view.filters.forEach(function (filter, index) {
        var model = api.filterModels[index];
        if (model.type === "chips") {
          model.selected = new Set(filter.values);
          model.active = model.selected.size !== model.values.length;
          Array.from(model.node.querySelectorAll(".imb-chip")).forEach(function (button) {
            var active = model.selected.has(button.dataset.value);
            button.classList.toggle("is-active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
          });
        } else if (model.type === "select") {
          model.value = filter.value;
          model.node.value = filter.value;
          model.active = Boolean(filter.value);
        } else {
          model.lowNode.value = String(filter.low);
          model.highNode.value = String(filter.high);
          // Reuse the existing range handler for its label and active-state rules.
          model.lowNode.dispatchEvent(new Event("change"));
        }
      });
    }
    api.search.value = view.search;
    api.refresh();
    if (view.selected_id) { api.select(view.selected_id); }
  }

  IMB.attachViewState = function (map, api) {
    var payload = IMB.parsePayload();
    var strings = payload.catalog.view_state;
    var status;
    var dialog;
    var stateQA = { version: 1, restored: false, error: "" };
    IMB.qa.viewState = stateQA;

    function capture() {
      var center = map.getCenter().wrap();
      return {
        format: "interactive-map-builder-view", version: 1,
        map_key: payload.view_state_key, template: api.template,
        map: { center: [center.lat, center.lng], zoom: map.getZoom(), basemap: api.basemap.getActiveIndex() },
        panels: {
          sidebar: panelValue("imb-collapse"), legend: panelValue("imb-legend-toggle"),
          controls: panelValue("imb-controls-collapse"),
          detail: Boolean(document.getElementById("imb-detail") && !document.getElementById("imb-detail").hidden)
        },
        view: captureView(api)
      };
    }

    function validate(value) {
      if (!keys(value, ["format", "version", "map_key", "template", "map", "panels", "view"]) ||
          value.format !== "interactive-map-builder-view" || value.version !== 1) {
        throw new Error(strings.invalid);
      }
      if (value.map_key !== payload.view_state_key || value.template !== api.template) {
        throw new Error(strings.mismatch);
      }
      var camera = value.map;
      if (!keys(camera, ["center", "zoom", "basemap"]) || !Array.isArray(camera.center) ||
          camera.center.length !== 2 || !camera.center.every(finite) ||
          Math.abs(camera.center[0]) > 90 || Math.abs(camera.center[1]) > 180 ||
          !finite(camera.zoom) || camera.zoom < 0 || camera.zoom > 30 ||
          !Number.isInteger(camera.basemap) || camera.basemap < -1 ||
          camera.basemap >= api.basemap.basemaps.length ||
          !keys(value.panels, ["sidebar", "legend", "controls", "detail"]) ||
          !Object.values(value.panels).every(function (value) { return typeof value === "boolean"; }) ||
          (value.panels.controls && !document.getElementById("imb-controls-collapse")) ||
          (value.panels.detail && (!api.closeDetail || !value.view.selected_id)) ||
          !validView(value.view, api)) {
        throw new Error(strings.invalid);
      }
      return value;
    }

    function parse(value) {
      var source = typeof value === "string" ? value : JSON.stringify(value);
      if (typeof source !== "string" || new Blob([source]).size > MAX_BYTES) {
        throw new Error(strings.oversized);
      }
      // Reconstruct plain JSON before validating; ignore no unknown fields or IDs.
      var decoded;
      try { decoded = JSON.parse(source); } catch (_error) { throw new Error(strings.invalid); }
      return validate(decoded);
    }

    function apply(value) {
      document.documentElement.dataset.imbRestoring = "true";
      try {
        map.stop();
        applyView(value.view, api);
        api.basemap.activate(value.map.basemap);
        if (!value.panels.detail && api.closeDetail) { api.closeDetail(); }
        setPanel("imb-collapse", value.panels.sidebar);
        setPanel("imb-legend-toggle", value.panels.legend);
        setPanel("imb-controls-collapse", value.panels.controls);
        // Resolve panel layout synchronously before restoring the camera.
        document.getElementById("imb-app").getBoundingClientRect();
        map.invalidateSize({ pan: false });
        map.setView(value.map.center, value.map.zoom, { animate: false });
      } finally {
        delete document.documentElement.dataset.imbRestoring;
      }
    }

    function restore(value) {
      var next;
      try { next = parse(value); }
      catch (error) {
        stateQA.error = error.message;
        if (status) { status.textContent = error.message; }
        return false;
      }
      var previous = capture();
      try {
        apply(next);
      } catch (error) {
        try { apply(previous); } catch (rollbackError) { IMB.recordError(rollbackError); }
        stateQA.error = strings.invalid;
        if (status) { status.textContent = strings.invalid; }
        return false;
      }
      stateQA.restored = true;
      stateQA.error = "";
      if (status) { status.textContent = strings.restored; }
      return true;
    }

    function htmlSnapshot() {
      var value = parse(capture());
      var root = pristineRoot.cloneNode(true);
      var old = root.querySelector("#imb-view-state");
      if (old) { old.remove(); }
      var node = document.createElement("script");
      node.id = "imb-view-state";
      node.type = "application/json";
      node.textContent = safeJSON(value);
      root.querySelector("body").appendChild(node);
      return new XMLSerializer().serializeToString(document.doctype) + "\n" + root.outerHTML;
    }

    function download(content, mime, name) {
      var url = URL.createObjectURL(new Blob([content], { type: mime }));
      var anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = name;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(function () { URL.revokeObjectURL(url); }, 30000);
      status.textContent = strings.downloaded;
    }

    var host = document.querySelector(".imb-header");
    var button = IMB.element("button", strings.share, "imb-button imb-share-view");
    button.type = "button";
    button.id = "imb-share-view";
    button.setAttribute("aria-haspopup", "dialog");
    button.setAttribute("aria-controls", "imb-share-dialog");
    host.appendChild(button);
    dialog = document.createElement("dialog");
    dialog.id = "imb-share-dialog";
    dialog.className = "imb-share-dialog";
    dialog.setAttribute("aria-labelledby", "imb-share-title");
    var header = IMB.element("div", undefined, "imb-share-header");
    var heading = IMB.element("h2", strings.share);
    heading.id = "imb-share-title";
    var close = IMB.element("button", strings.close, "imb-button");
    close.type = "button";
    close.addEventListener("click", function () { dialog.close(); });
    header.append(heading, close);
    var help = IMB.element("p", strings.help);
    var privacy = IMB.element("p", strings.privacy, "imb-share-notice");
    privacy.id = "imb-share-privacy";
    dialog.setAttribute("aria-describedby", privacy.id);
    var actions = IMB.element("div", undefined, "imb-share-actions");
    function action(id, label, handler) {
      var node = IMB.element("button", label, "imb-button");
      node.id = id;
      node.type = "button";
      node.addEventListener("click", function () {
        try { handler(); } catch (error) { status.textContent = error.message; }
      });
      actions.appendChild(node);
    }
    action("imb-download-view-html", strings.html, function () {
      download(htmlSnapshot(), "text/html;charset=utf-8", "map-view.html");
    });
    action("imb-export-view-json", strings.export, function () {
      download(JSON.stringify(parse(capture()), null, 2), "application/json", "map-view.json");
    });
    var file = document.createElement("input");
    file.id = "imb-import-view-file";
    file.type = "file";
    file.accept = ".json,application/json";
    file.hidden = true;
    action("imb-import-view-json", strings.import, function () { file.click(); });
    var importSequence = 0;
    file.addEventListener("change", async function () {
      var selected = file.files[0];
      var sequence = ++importSequence;
      file.value = "";
      if (!selected) { return; }
      if (selected.size > MAX_BYTES) { status.textContent = strings.oversized; return; }
      try {
        var contents = await selected.text();
        if (sequence === importSequence) { restore(contents); }
      } catch (_error) {
        if (sequence === importSequence) { status.textContent = strings.invalid; }
      }
    });
    status = IMB.element("p", "", "imb-share-status");
    status.id = "imb-share-status";
    status.setAttribute("role", "status");
    dialog.append(header, help, privacy, actions, file, status);
    document.body.appendChild(dialog);
    button.addEventListener("click", function () { dialog.showModal(); });
    dialog.addEventListener("close", function () { button.focus(); });

    // QA delegates to the product controller; product code never calls QA actions.
    IMB.qa.actions.captureViewState = capture;
    IMB.qa.actions.restoreViewState = restore;
    IMB.qa.actions.exportViewHTML = htmlSnapshot;
    var embedded = document.getElementById("imb-view-state");
    if (embedded) {
      if (map.__imbSavedViews) { map.__imbSavedViews.captureOverview(); }
      if (!restore(embedded.textContent)) { dialog.showModal(); }
    }
  };
}());
