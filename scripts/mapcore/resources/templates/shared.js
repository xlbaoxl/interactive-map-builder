(function () {
  "use strict";

  var palette = [
    "#1668dc",
    "#dc5a2a",
    "#16856b",
    "#8957c7",
    "#c43d70",
    "#99721d",
    "#337a9e",
    "#6b7280"
  ];

  var qa = {
    ready: false,
    template: null,
    recordCount: 0,
    visibleRecordCount: 0,
    renderedListCount: 0,
    layerCounts: {},
    errors: [],
    actions: {}
  };
  window.__interactiveMapBuilderQA = qa;

  function recordError(error) {
    var message = error && error.message ? error.message : String(error);
    qa.errors.push(message);
    var target = document.getElementById("imb-map-message");
    if (target) {
      target.textContent = message;
      target.classList.add("is-visible");
    }
  }

  window.addEventListener("error", function (event) {
    recordError(event.error || event.message || "Unknown map error");
  });
  window.addEventListener("unhandledrejection", function (event) {
    recordError(event.reason || "Unhandled map promise rejection");
  });

  function parsePayload() {
    var node = document.getElementById("imb-data");
    if (!node) {
      throw new Error("Map payload is missing.");
    }
    return JSON.parse(node.textContent);
  }

  function text(value) {
    if (value === null || value === undefined) {
      return "";
    }
    if (typeof value === "object") {
      try {
        return JSON.stringify(value);
      } catch (_error) {
        return String(value);
      }
    }
    return String(value);
  }

  function displayValue(value) {
    var rendered = text(value);
    return rendered.trim() ? rendered : "—";
  }

  function element(tagName, value, className) {
    var node = document.createElement(tagName);
    if (className) {
      node.className = className;
    }
    if (value !== undefined) {
      node.textContent = text(value);
    }
    return node;
  }

  function list(value) {
    if (Array.isArray(value)) {
      return value;
    }
    if (value === null || value === undefined || value === "") {
      return [];
    }
    return [value];
  }

  function firstDefined() {
    for (var index = 0; index < arguments.length; index += 1) {
      if (arguments[index] !== undefined && arguments[index] !== null) {
        return arguments[index];
      }
    }
    return undefined;
  }

  function layerSpec(layer) {
    return layer && layer.spec && typeof layer.spec === "object" ? layer.spec : {};
  }

  function layerId(layer, index) {
    var spec = layerSpec(layer);
    return text(firstDefined(spec.id, "layer-" + (index + 1)));
  }

  function layerTitle(layer, index) {
    var spec = layerSpec(layer);
    return text(firstDefined(spec.name, spec.id, "Layer " + (index + 1)));
  }

  function idField(spec) {
    return text(firstDefined(spec.id_field, "__map_id"));
  }

  function labelField(spec) {
    return text(firstDefined(spec.label_field, "__label"));
  }

  function categoryField(spec) {
    var style = spec.style && typeof spec.style === "object" ? spec.style : {};
    return text(firstDefined(style.color_field, ""));
  }

  function featureId(feature, spec, fallback) {
    var props = feature && feature.properties && typeof feature.properties === "object"
      ? feature.properties
      : {};
    var configured = idField(spec || {});
    return text(firstDefined(
      props[configured],
      props.__map_id,
      feature && feature.id,
      fallback
    ));
  }

  function recordProperties(record) {
    if (record && record.properties && typeof record.properties === "object") {
      return record.properties;
    }
    return record && typeof record === "object" ? record : {};
  }

  function normalizedRecords(layer) {
    var spec = layerSpec(layer);
    var features = layer && layer.feature_collection && Array.isArray(layer.feature_collection.features)
      ? layer.feature_collection.features
      : [];
    var sourceRecords = layer && Array.isArray(layer.records) && layer.records.length
      ? layer.records
      : features.map(function (feature) { return feature.properties || {}; });
    return sourceRecords.map(function (record, index) {
      var props = recordProperties(record);
      var feature = features[index] || null;
      var fallback = layerId(layer, 0) + "-" + (index + 1);
      var identifier = text(firstDefined(
        props[idField(spec)],
        props.__map_id,
        featureId(feature, spec, fallback)
      ));
      return {
        id: identifier,
        properties: props,
        feature: feature,
        sourceIndex: index
      };
    });
  }

  function fieldDefinitions(value, fallback, spec) {
    var definitions = list(value);
    if (!definitions.length) {
      definitions = list(fallback);
    }
    return definitions.map(function (definition) {
      definition = text(definition);
      return {
        field: definition,
        label: fieldLabel(spec || {}, definition)
      };
    }).filter(function (definition) {
      return Boolean(definition.field);
    });
  }

  function fieldLabel(spec, field) {
    var labels = spec.field_labels && typeof spec.field_labels === "object" ? spec.field_labels : {};
    return text(firstDefined(labels[field], field));
  }

  function contentFields(spec, kind) {
    var direct = spec[kind + "_fields"];
    return fieldDefinitions(direct, [labelField(spec)], spec);
  }

  function buildDetailsNode(properties, definitions, className) {
    var container = element("div", undefined, className || "imb-tooltip");
    definitions.forEach(function (definition) {
      var row = element("div", undefined, "imb-detail-row");
      row.appendChild(element("span", definition.label, "imb-detail-key"));
      row.appendChild(element("span", displayValue(properties[definition.field]), "imb-detail-value"));
      container.appendChild(row);
    });
    return container;
  }

  function categoryEntries(spec) {
    var style = spec.style && typeof spec.style === "object" ? spec.style : {};
    var categories = style.categories;
    var output = [];
    if (categories && typeof categories === "object") {
      Object.keys(categories).forEach(function (key) {
        var item = categories[key];
        if (item && typeof item === "object") {
          output.push({
            value: text(key),
            label: text(firstDefined(item.label, key)),
            color: text(item.color)
          });
        } else {
          output.push({ value: text(key), label: text(key), color: text(item) });
        }
      });
    }
    return output;
  }

  function hash(value) {
    var result = 0;
    var source = text(value);
    for (var index = 0; index < source.length; index += 1) {
      result = ((result << 5) - result + source.charCodeAt(index)) | 0;
    }
    return Math.abs(result);
  }

  function colorFor(spec, properties) {
    var style = spec.style && typeof spec.style === "object" ? spec.style : {};
    var field = categoryField(spec);
    var category = field ? text(properties[field]) : "";
    var entries = categoryEntries(spec);
    for (var index = 0; index < entries.length; index += 1) {
      if (entries[index].value === category && entries[index].color) {
        return entries[index].color;
      }
    }
    return text(firstDefined(
      style.fill_color,
      style.color,
      palette[hash(category || layerTitle({ spec: spec }, 0)) % palette.length]
    ));
  }

  function geometryStyle(spec, feature) {
    var properties = feature && feature.properties ? feature.properties : {};
    var style = spec.style && typeof spec.style === "object" ? spec.style : {};
    var color = colorFor(spec, properties);
    return {
      color: text(firstDefined(style.color, color)),
      weight: Number(firstDefined(style.weight, 2)),
      opacity: Number(firstDefined(style.opacity, 0.9)),
      fillColor: text(firstDefined(style.fill_color, color)),
      fillOpacity: Number(firstDefined(style.fill_opacity, 0.55)),
      radius: Number(firstDefined(style.radius, 7))
    };
  }

  function attachFeatureContent(leafletLayer, feature, spec) {
    var props = feature && feature.properties ? feature.properties : {};
    var tooltip = contentFields(spec, "tooltip");
    var popup = contentFields(spec, "popup");
    if (tooltip.length && leafletLayer.bindTooltip) {
      leafletLayer.bindTooltip(buildDetailsNode(props, tooltip, "imb-tooltip"), {
        sticky: true,
        direction: "top"
      });
    }
    if (popup.length && leafletLayer.bindPopup) {
      leafletLayer.bindPopup(buildDetailsNode(props, popup, "imb-tooltip"));
    }
  }

  function addBasemap(map, spec) {
    var basemaps = spec && Array.isArray(spec.basemaps)
      ? spec.basemaps.filter(function (candidate) {
        return candidate && text(candidate.url);
      })
      : [];
    var activeLayer = null;
    var activeIndex = -1;
    var attribution = document.getElementById("imb-map-attribution");

    function activate(index) {
      var basemap = basemaps[index];
      if (!basemap) {
        return false;
      }
      if (activeLayer && map.hasLayer(activeLayer)) {
        map.removeLayer(activeLayer);
      }
      activeLayer = L.tileLayer(
        text(basemap.url),
        {
          minZoom: 0,
          maxZoom: Number(firstDefined(basemap.max_zoom, 19)),
          attribution: ""
        }
      ).addTo(map);
      if (activeLayer.bringToBack) {
        activeLayer.bringToBack();
      }
      activeIndex = index;
      if (attribution) {
        attribution.textContent = text(firstDefined(
          basemap.attribution,
          spec.static && spec.static.source_note,
          ""
        ));
        attribution.hidden = !attribution.textContent;
      }
      return true;
    }

    if (basemaps.length) {
      var requested = basemaps.findIndex(function (candidate) {
        return candidate.visible === true;
      });
      activate(requested >= 0 ? requested : 0);
    } else if (attribution) {
      attribution.textContent = text(firstDefined(
        spec && spec.static && spec.static.source_note,
        ""
      ));
      attribution.hidden = !attribution.textContent;
    }

    var mapOptions = spec && spec.map && typeof spec.map === "object" ? spec.map : {};
    var controls = mapOptions.controls && typeof mapOptions.controls === "object"
      ? mapOptions.controls
      : {};
    if (basemaps.length > 1 && controls.basemap_switcher !== false) {
      var basemapControl = L.control({ position: "topleft" });
      basemapControl.onAdd = function () {
        var container = element("div", undefined, "imb-leaflet-tool");
        var select = document.createElement("select");
        select.className = "imb-map-tool-select";
        select.setAttribute("aria-label", "底图");
        basemaps.forEach(function (candidate, index) {
          var option = document.createElement("option");
          option.value = String(index);
          option.textContent = text(firstDefined(candidate.name, "Basemap " + (index + 1)));
          option.selected = index === activeIndex;
          select.appendChild(option);
        });
        select.addEventListener("change", function () {
          activate(Number(select.value));
        });
        container.appendChild(select);
        if (L.DomEvent && L.DomEvent.disableClickPropagation) {
          L.DomEvent.disableClickPropagation(container);
        }
        return container;
      };
      basemapControl.addTo(map);
    }

    if (controls.scale !== false && L.control && L.control.scale) {
      L.control.scale({ imperial: false }).addTo(map);
    }

    if (controls.fullscreen !== false) {
      var fullscreenControl = L.control({ position: "topleft" });
      var fullscreenButtonNode = null;
      fullscreenControl.onAdd = function () {
        var container = element("div", undefined, "imb-leaflet-tool");
        var button = element("button", "⛶", "imb-map-tool-button");
        fullscreenButtonNode = button;
        button.type = "button";
        button.title = "全屏地图";
        button.setAttribute("aria-label", button.title);
        function toggleFallback(target) {
          var active = target.classList.toggle("is-imb-fullscreen");
          button.setAttribute("aria-pressed", active ? "true" : "false");
          window.setTimeout(function () { map.invalidateSize(); }, 50);
        }
        button.addEventListener("click", function () {
          var target = document.querySelector(".imb-map-wrap");
          if (target) {
            toggleFallback(target);
          }
        });
        container.appendChild(button);
        if (L.DomEvent && L.DomEvent.disableClickPropagation) {
          L.DomEvent.disableClickPropagation(container);
        }
        return container;
      };
      fullscreenControl.addTo(map);
      document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
          return;
        }
        var target = document.querySelector(".imb-map-wrap.is-imb-fullscreen");
        if (target) {
          target.classList.remove("is-imb-fullscreen");
          if (fullscreenButtonNode) {
            fullscreenButtonNode.setAttribute("aria-pressed", "false");
          }
          window.setTimeout(function () { map.invalidateSize(); }, 50);
        }
      });
    }

    qa.actions.setBasemap = function (value) {
      var target = text(value);
      var index = basemaps.findIndex(function (candidate, candidateIndex) {
        return text(firstDefined(candidate.name, candidateIndex)) === target
          || String(candidateIndex) === target;
      });
      return index >= 0 ? activate(index) : false;
    };
    return { basemaps: basemaps, activate: activate };
  }

  function fitToGroups(map, groups) {
    var combined = L.featureGroup();
    groups.forEach(function (group) {
      if (group && group.eachLayer) {
        group.eachLayer(function (leafletLayer) {
          combined.addLayer(leafletLayer);
        });
      }
    });
    var bounds = combined.getBounds();
    if (bounds && bounds.isValid && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [22, 22], maxZoom: 16 });
    } else {
      map.setView([20, 0], 2);
    }
  }

  function markFeature(registry, identifier, active) {
    var entries = registry.get(text(identifier)) || [];
    entries.forEach(function (entry) {
      if (!entry.leaflet || !entry.leaflet.setStyle) {
        return;
      }
      if (active) {
        entry.leaflet.setStyle({
          color: "#0b3a75",
          weight: Math.max(4, Number(entry.baseStyle.weight || 2) + 2),
          fillOpacity: Math.max(0.78, Number(entry.baseStyle.fillOpacity || 0))
        });
        if (entry.leaflet.bringToFront) {
          entry.leaflet.bringToFront();
        }
      } else {
        entry.leaflet.setStyle(entry.baseStyle);
      }
    });
  }

  var eventTarget = document.createElement("span");
  var listeners = [];
  var linkById = {
    emit: function (type, identifier, detail) {
      var id = text(identifier);
      if (!id) {
        return;
      }
      eventTarget.dispatchEvent(new CustomEvent("imb:" + type, {
        detail: Object.assign({ id: id }, detail || {})
      }));
    },
    on: function (type, callback) {
      var eventName = "imb:" + type;
      var handler = function (event) {
        callback(event.detail || {});
      };
      eventTarget.addEventListener(eventName, handler);
      listeners.push({ eventName: eventName, handler: handler });
      return function () {
        eventTarget.removeEventListener(eventName, handler);
      };
    },
    clear: function (identifier, detail) {
      this.emit("clear", identifier, detail);
    },
    destroy: function () {
      listeners.forEach(function (item) {
        eventTarget.removeEventListener(item.eventName, item.handler);
      });
      listeners = [];
    }
  };
  window.link_by_id = linkById;

  function bindLinkedElements(root) {
    var scope = root || document;
    Array.prototype.forEach.call(scope.querySelectorAll("[data-feature-id]"), function (node) {
      if (node.dataset.imbLinkBound === "true") {
        return;
      }
      node.dataset.imbLinkBound = "true";
      node.addEventListener("pointerenter", function () {
        linkById.emit("highlight", node.dataset.featureId, { source: "dom" });
      });
      node.addEventListener("pointerleave", function () {
        linkById.clear(node.dataset.featureId, { source: "dom" });
      });
      node.addEventListener("focus", function () {
        linkById.emit("highlight", node.dataset.featureId, { source: "dom" });
      });
      node.addEventListener("blur", function () {
        linkById.clear(node.dataset.featureId, { source: "dom" });
      });
      node.addEventListener("click", function () {
        linkById.emit("select", node.dataset.featureId, { source: "dom" });
      });
      node.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          linkById.emit("select", node.dataset.featureId, { source: "keyboard" });
        }
      });
    });
  }

  function applyLinkedDomState(identifier, active, selected) {
    var id = text(identifier);
    Array.prototype.forEach.call(document.querySelectorAll("[data-feature-id]"), function (node) {
      if (node.dataset.featureId !== id) {
        return;
      }
      node.classList.toggle("is-linked-active", Boolean(active));
      if (selected && node.hasAttribute("aria-selected")) {
        node.setAttribute("aria-selected", "true");
      }
    });
  }

  function setupMap() {
    if (!window.L || typeof window.L.map !== "function") {
      throw new Error("Leaflet runtime was not loaded.");
    }
    return L.map("imb-map", {
      attributionControl: false,
      preferCanvas: true,
      zoomControl: true
    });
  }

  function finish(template, details) {
    qa.template = template;
    Object.keys(details || {}).forEach(function (key) {
      qa[key] = details[key];
    });
    qa.ready = true;
    document.documentElement.dataset.imbReady = "true";
  }

  function onReady(callback) {
    function run() {
      try {
        callback();
      } catch (error) {
        recordError(error);
      }
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", run, { once: true });
    } else {
      run();
    }
  }

  window.InteractiveMapBuilder = {
    addBasemap: addBasemap,
    applyLinkedDomState: applyLinkedDomState,
    attachFeatureContent: attachFeatureContent,
    bindLinkedElements: bindLinkedElements,
    buildDetailsNode: buildDetailsNode,
    categoryEntries: categoryEntries,
    categoryField: categoryField,
    colorFor: colorFor,
    contentFields: contentFields,
    displayValue: displayValue,
    element: element,
    featureId: featureId,
    fieldDefinitions: fieldDefinitions,
    fieldLabel: fieldLabel,
    finish: finish,
    firstDefined: firstDefined,
    fitToGroups: fitToGroups,
    geometryStyle: geometryStyle,
    idField: idField,
    labelField: labelField,
    layerId: layerId,
    layerSpec: layerSpec,
    layerTitle: layerTitle,
    link_by_id: linkById,
    markFeature: markFeature,
    normalizedRecords: normalizedRecords,
    onReady: onReady,
    palette: palette.slice(),
    parsePayload: parsePayload,
    qa: qa,
    recordError: recordError,
    setupMap: setupMap,
    text: text
  };
}());
