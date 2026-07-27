(function () {
  "use strict";

  var palette = [
    "#4E8587",
    "#D39A4A",
    "#8C739B",
    "#C56E79",
    "#718F61",
    "#607F9D",
    "#A67D62",
    "#7C8588"
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

  function layerVisual(layer) {
    return layer && layer.visual && typeof layer.visual === "object" ? layer.visual : {};
  }

  function geometryFamily(feature) {
    var geometryType = feature && feature.geometry
      ? text(feature.geometry.type).toLocaleLowerCase()
      : "";
    if (geometryType.indexOf("point") !== -1) {
      return "point";
    }
    if (geometryType.indexOf("line") !== -1) {
      return "line";
    }
    if (geometryType.indexOf("polygon") !== -1) {
      return "polygon";
    }
    return "polygon";
  }

  function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, Number(value)));
  }

  function adjustColor(value, amount) {
    var source = text(value).trim();
    var match = /^#([0-9a-f]{6})$/i.exec(source);
    if (!match) {
      return source;
    }
    var channels = [0, 2, 4].map(function (offset) {
      return parseInt(match[1].slice(offset, offset + 2), 16);
    });
    var adjusted = channels.map(function (channel) {
      var resolved = amount >= 0
        ? channel + (255 - channel) * amount
        : channel * (1 + amount);
      return Math.max(0, Math.min(255, Math.round(resolved)));
    });
    return "#" + adjusted.map(function (channel) {
      return channel.toString(16).padStart(2, "0");
    }).join("").toUpperCase();
  }

  function familyVisual(visual, family) {
    var families = visual && visual.families && typeof visual.families === "object"
      ? visual.families
      : {};
    var resolved = families[family];
    return resolved && typeof resolved === "object" ? resolved : {};
  }

  function colorFor(spec, properties, visual, family) {
    var style = spec.style && typeof spec.style === "object" ? spec.style : {};
    var field = categoryField(spec);
    var category = field ? text(properties[field]) : "";
    var entries = categoryEntries(spec);
    for (var index = 0; index < entries.length; index += 1) {
      if (entries[index].value === category && entries[index].color) {
        return entries[index].color;
      }
    }
    var base = familyVisual(visual || {}, family || "polygon");
    return text(firstDefined(
      base.fill_color,
      base.color,
      style.fill_color,
      style.color,
      palette[hash(category || layerTitle({ spec: spec }, 0)) % palette.length]
    ));
  }

  function geometryStyle(spec, feature, visual) {
    var properties = feature && feature.properties ? feature.properties : {};
    var family = geometryFamily(feature);
    var base = familyVisual(visual || {}, family);
    var categoryColor = categoryField(spec)
      ? colorFor(spec, properties, visual, family)
      : "";
    var fillColor;
    var strokeColor;
    if (family === "line") {
      strokeColor = categoryColor || text(firstDefined(
        base.color,
        colorFor(spec, properties, visual, family)
      ));
      fillColor = strokeColor;
    } else {
      fillColor = categoryColor || text(firstDefined(
        base.fill_color,
        base.color,
        colorFor(spec, properties, visual, family)
      ));
      var strategy = text(firstDefined(base.category_stroke, "same"));
      if (categoryColor && strategy === "darken") {
        strokeColor = adjustColor(categoryColor, -0.24);
      } else if (categoryColor && strategy === "same") {
        strokeColor = categoryColor;
      } else {
        strokeColor = text(firstDefined(
          base.stroke_color,
          family === "point" ? "#FFFFFF" : adjustColor(fillColor, -0.24)
        ));
      }
    }
    return {
      color: strokeColor,
      weight: Number(firstDefined(base.weight, family === "line" ? 1.5 : 0.8)),
      opacity: clamp(firstDefined(base.opacity, 0.85), 0, 1),
      fillColor: fillColor,
      fillOpacity: clamp(
        firstDefined(base.fill_opacity, family === "polygon" ? 0.25 : 0.72),
        0,
        1
      ),
      radius: Number(firstDefined(base.radius, 4)),
      pane: text(firstDefined(base.pane, "overlayPane"))
    };
  }

  function stateStyle(baseStyle, visual, stateName) {
    var result = Object.assign({}, baseStyle || {});
    if (!stateName || stateName === "base") {
      return result;
    }
    var states = visual && visual.states && typeof visual.states === "object"
      ? visual.states
      : {};
    var state = states[stateName] && typeof states[stateName] === "object"
      ? states[stateName]
      : {};
    if (state.opacity_multiplier !== undefined) {
      result.opacity = clamp(
        Number(result.opacity || 0) * Number(state.opacity_multiplier),
        0,
        1
      );
    }
    if (state.fill_opacity_multiplier !== undefined) {
      result.fillOpacity = clamp(
        Number(result.fillOpacity || 0) * Number(state.fill_opacity_multiplier),
        0,
        1
      );
    }
    if (state.weight_multiplier !== undefined) {
      result.weight = Math.max(
        0,
        Number(result.weight || 0) * Number(state.weight_multiplier)
      );
    }
    if (state.weight_add !== undefined) {
      result.weight = Math.max(
        0,
        Number(result.weight || 0) + Number(state.weight_add)
      );
    }
    if (state.radius_multiplier !== undefined) {
      result.radius = Math.max(
        1.5,
        Number(result.radius || 4) * Number(state.radius_multiplier)
      );
    }
    if (state.stroke_color) {
      result.color = text(state.stroke_color);
    }
    return result;
  }

  function applyEntryState(entry, stateName) {
    if (!entry || !entry.leaflet || !entry.leaflet.setStyle) {
      return;
    }
    var visual = entry.visual || (entry.runtime && entry.runtime.visual) || {};
    var resolved = stateStyle(entry.baseStyle, visual, stateName);
    entry.leaflet.setStyle(resolved);
    if (entry.leaflet.setRadius && resolved.radius !== undefined) {
      entry.leaflet.setRadius(Number(resolved.radius));
    }
    entry.visualState = stateName || "base";
    if (
      (stateName === "hover" || stateName === "selected")
      && entry.leaflet.bringToFront
    ) {
      entry.leaflet.bringToFront();
    }
  }

  function orderGroups(runtimes) {
    (runtimes || []).slice().sort(function (left, right) {
      var leftOrder = Number(left.visual && left.visual.draw_order || 0);
      var rightOrder = Number(right.visual && right.visual.draw_order || 0);
      return leftOrder - rightOrder || Number(left.order || 0) - Number(right.order || 0);
    }).forEach(function (runtime) {
      if (!runtime.group || !runtime.group.eachLayer) {
        return;
      }
      runtime.group.eachLayer(function (leafletLayer) {
        if (leafletLayer && leafletLayer.bringToFront) {
          leafletLayer.bringToFront();
        }
      });
    });
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
      leafletLayer.bindPopup(
        buildDetailsNode(props, popup, "imb-tooltip"),
        { minWidth: 260, maxWidth: 340 }
      );
    }
  }

  function addBasemap(map, spec, messages) {
    var basemaps = spec && Array.isArray(spec.basemaps)
      ? spec.basemaps.filter(function (candidate) {
        return candidate && text(candidate.url);
      })
      : [];
    var labels = messages && typeof messages === "object" ? messages : {};
    var basemapLabel = text(firstDefined(labels.basemap, "Basemap"));
    var noBasemapLabel = text(firstDefined(labels.no_basemap, "No basemap"));
    var unavailableLabel = text(firstDefined(
      labels.basemap_unavailable,
      "Basemap tiles could not be loaded. Showing no basemap."
    ));
    var fullscreenLabel = text(firstDefined(labels.fullscreen, "Fullscreen map"));
    var activeLayer = null;
    var activeIndex = -1;
    var selectNode = null;
    var tileErrorCount = 0;
    var basemapWarningVisible = false;
    var attribution = document.getElementById("imb-map-attribution");
    var messageNode = document.getElementById("imb-map-message");
    var customMount = document.getElementById("imb-basemap-options");
    var customSection = document.getElementById("imb-basemap-control");
    var mapOptions = spec && spec.map && typeof spec.map === "object" ? spec.map : {};
    var controls = mapOptions.controls && typeof mapOptions.controls === "object"
      ? mapOptions.controls
      : {};

    function setAttribution(value) {
      if (!attribution) {
        return;
      }
      attribution.textContent = text(value);
      attribution.hidden = !attribution.textContent;
    }

    function activate(index, options) {
      var requestedIndex = Number(index);
      var basemap = requestedIndex >= 0 ? basemaps[requestedIndex] : null;
      if (requestedIndex >= 0 && !basemap) {
        return false;
      }
      if (activeLayer && map.hasLayer(activeLayer)) {
        map.removeLayer(activeLayer);
      }
      activeLayer = null;
      activeIndex = basemap ? requestedIndex : -1;
      tileErrorCount = 0;
      if (!(options && options.fallback)) {
        qa.basemapFallback = false;
        if (basemapWarningVisible && messageNode) {
          messageNode.textContent = "";
          messageNode.classList.remove("is-visible");
        }
        basemapWarningVisible = false;
      }
      if (basemap) {
        var requestedLayer = L.tileLayer(
          text(basemap.url),
          {
            minZoom: 0,
            maxZoom: Number(firstDefined(basemap.max_zoom, 19)),
            attribution: ""
          }
        );
        requestedLayer.on("tileerror", function () {
          if (activeLayer !== requestedLayer) {
            return;
          }
          tileErrorCount += 1;
          if (tileErrorCount < 3 || activeIndex < 0) {
            return;
          }
          activate(-1, { fallback: true });
        });
        activeLayer = requestedLayer;
        activeLayer.addTo(map);
        if (activeLayer.bringToBack) {
          activeLayer.bringToBack();
        }
        setAttribution(firstDefined(
          basemap.attribution,
          spec.static && spec.static.source_note,
          ""
        ));
      } else {
        setAttribution(firstDefined(spec.static && spec.static.source_note, ""));
      }
      if (selectNode) {
        selectNode.value = String(activeIndex);
      }
      qa.activeBasemap = basemap ? text(firstDefined(basemap.name, activeIndex)) : noBasemapLabel;
      if (options && options.fallback) {
        qa.basemapFallback = true;
        basemapWarningVisible = true;
        if (messageNode) {
          messageNode.textContent = unavailableLabel;
          messageNode.classList.add("is-visible");
        }
      }
      return true;
    }

    var requested = basemaps.findIndex(function (candidate) {
      return candidate.visible === true;
    });
    if (basemaps.length) {
      activate(requested >= 0 ? requested : 0);
    } else {
      activate(-1);
    }

    function buildSelect() {
      var select = document.createElement("select");
      select.className = customMount
        ? "imb-select imb-basemap-select"
        : "imb-map-tool-select";
      select.setAttribute("aria-label", basemapLabel);
      basemaps.forEach(function (candidate, index) {
        var option = document.createElement("option");
        option.value = String(index);
        option.textContent = text(firstDefined(candidate.name, "Basemap " + (index + 1)));
        select.appendChild(option);
      });
      var none = document.createElement("option");
      none.value = "-1";
      none.textContent = noBasemapLabel;
      select.appendChild(none);
      select.value = String(activeIndex);
      select.addEventListener("change", function () {
        activate(Number(select.value));
      });
      selectNode = select;
      return select;
    }

    if (controls.basemap_switcher === false || !basemaps.length) {
      if (customSection) {
        customSection.hidden = true;
      }
    } else if (customMount) {
      customMount.replaceChildren(buildSelect());
    } else {
      var basemapControl = L.control({ position: "topleft" });
      basemapControl.onAdd = function () {
        var container = element("div", undefined, "imb-leaflet-tool");
        container.appendChild(buildSelect());
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
        button.title = fullscreenLabel;
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
      if (target === "-1" || target.toLocaleLowerCase() === "none" || target === noBasemapLabel) {
        return activate(-1);
      }
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

  function markFeature(registry, identifier, state) {
    var stateName = state === true ? "selected" : state === false ? "base" : text(state || "base");
    var entries = registry.get(text(identifier)) || [];
    entries.forEach(function (entry) {
      applyEntryState(entry, stateName);
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
    var map = L.map("imb-map", {
      attributionControl: false,
      preferCanvas: true,
      zoomControl: true
    });
    [
      ["imb-context-polygon", 330],
      ["imb-supporting-polygon", 340],
      ["imb-primary-polygon", 350],
      ["imb-context-line", 410],
      ["imb-supporting-line", 420],
      ["imb-primary-line", 430],
      ["imb-context-point", 490],
      ["imb-supporting-point", 500],
      ["imb-primary-point", 510]
    ].forEach(function (definition) {
      var pane = map.createPane(definition[0]);
      pane.style.zIndex = String(definition[1]);
      pane.style.pointerEvents = "auto";
    });
    qa.visualPanes = [
      "imb-context-polygon",
      "imb-supporting-polygon",
      "imb-primary-polygon",
      "imb-context-line",
      "imb-supporting-line",
      "imb-primary-line",
      "imb-context-point",
      "imb-supporting-point",
      "imb-primary-point"
    ];
    return map;
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
    adjustColor: adjustColor,
    applyEntryState: applyEntryState,
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
    geometryFamily: geometryFamily,
    geometryStyle: geometryStyle,
    idField: idField,
    labelField: labelField,
    layerId: layerId,
    layerSpec: layerSpec,
    layerVisual: layerVisual,
    layerTitle: layerTitle,
    link_by_id: linkById,
    markFeature: markFeature,
    normalizedRecords: normalizedRecords,
    onReady: onReady,
    orderGroups: orderGroups,
    palette: palette.slice(),
    parsePayload: parsePayload,
    qa: qa,
    recordError: recordError,
    setupMap: setupMap,
    stateStyle: stateStyle,
    text: text
  };
}());
