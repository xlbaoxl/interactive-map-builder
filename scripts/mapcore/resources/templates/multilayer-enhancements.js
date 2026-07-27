(function () {
  "use strict";

  var IMB = window.InteractiveMapBuilder;
  if (!IMB) {
    return;
  }

  function populatedFamilies(visual) {
    var counts = visual && visual.geometry_counts && typeof visual.geometry_counts === "object"
      ? visual.geometry_counts
      : {};
    return ["point", "line", "polygon"].filter(function (family) {
      return Number(counts[family] || 0) > 0;
    });
  }

  function representativeFamily(visual) {
    var configured = IMB.text(
      visual && (visual.representative_family || visual.legend_family)
    ).toLocaleLowerCase();
    if (["point", "line", "polygon"].indexOf(configured) !== -1) {
      return configured;
    }
    var populated = populatedFamilies(visual || {});
    if (populated.length === 1) {
      return populated[0];
    }
    if (populated.length > 1) {
      var counts = visual.geometry_counts || {};
      return populated.slice().sort(function (left, right) {
        return Number(counts[right] || 0) - Number(counts[left] || 0);
      })[0];
    }
    var declared = IMB.text(visual && visual.geometry_family).toLocaleLowerCase();
    return ["point", "line", "polygon"].indexOf(declared) !== -1
      ? declared
      : "polygon";
  }

  var originalColorFor = IMB.colorFor;
  IMB.colorFor = function (spec, properties, visual, family) {
    var requested = IMB.text(family).toLocaleLowerCase();
    if (["point", "line", "polygon"].indexOf(requested) === -1) {
      requested = representativeFamily(visual || {});
    }
    return originalColorFor(spec, properties || {}, visual || {}, requested);
  };

  function primaryStyleColor(style) {
    var source = style && typeof style === "object" ? style : {};
    return IMB.text(IMB.firstDefined(source.fillColor, source.color, ""));
  }

  function unique(values) {
    return Array.from(new Set(values.filter(Boolean)));
  }

  function normalizeColor(value) {
    var probe = document.createElement("span");
    probe.style.color = IMB.text(value);
    if (!probe.style.color) {
      return IMB.text(value).trim().toLocaleLowerCase();
    }
    document.body.appendChild(probe);
    var resolved = window.getComputedStyle(probe).color;
    probe.remove();
    return IMB.text(resolved).replace(/\s+/g, "").toLocaleLowerCase();
  }

  function firstFeatureForFamily(layer, family) {
    var collection = layer && layer.feature_collection;
    var features = collection && Array.isArray(collection.features)
      ? collection.features
      : [];
    return features.find(function (feature) {
      return IMB.geometryFamily(feature) === family;
    }) || features[0] || null;
  }

  function expectedLegendColors(layer) {
    var spec = IMB.layerSpec(layer);
    var visual = IMB.layerVisual(layer);
    var entries = IMB.categoryEntries(spec);
    if (entries.length) {
      return entries.map(function (entry) { return entry.color; });
    }
    return [IMB.colorFor(spec, {}, visual, representativeFamily(visual))];
  }

  function collectVisualQA(details) {
    var payload = IMB.parsePayload();
    var layers = Array.isArray(payload.layers) ? payload.layers : [];
    var legendGroups = Array.prototype.slice.call(
      document.querySelectorAll("#imb-legend-groups > .imb-legend-group")
    );
    var layerSwatches = Array.prototype.slice.call(
      document.querySelectorAll("#imb-layer-options .imb-layer-option .imb-swatch")
    );
    var fillColors = {};
    var strokeColors = {};
    var representativeFamilies = {};
    var legendColors = {};
    var expectedColors = {};
    var layerControlColors = {};
    var mismatches = [];

    layers.forEach(function (layer, index) {
      var spec = IMB.layerSpec(layer);
      var visual = IMB.layerVisual(layer);
      var identifier = IMB.layerId(layer, index);
      var collection = layer && layer.feature_collection;
      var features = collection && Array.isArray(collection.features)
        ? collection.features
        : [];
      var representative = representativeFamily(visual);
      representativeFamilies[identifier] = representative;
      fillColors[identifier] = unique(features.map(function (feature) {
        return IMB.geometryStyle(spec, feature, visual).fillColor;
      }));
      strokeColors[identifier] = unique(features.map(function (feature) {
        return IMB.geometryStyle(spec, feature, visual).color;
      }));

      var expected = expectedLegendColors(layer);
      expectedColors[identifier] = expected;
      var group = legendGroups[index];
      var actual = group
        ? Array.prototype.map.call(group.querySelectorAll(".imb-swatch"), function (node) {
            return node.style.backgroundColor || window.getComputedStyle(node).backgroundColor;
          })
        : [];
      legendColors[identifier] = actual;
      if (
        expected.length !== actual.length
        || expected.some(function (color, colorIndex) {
          return normalizeColor(color) !== normalizeColor(actual[colorIndex]);
        })
      ) {
        mismatches.push(identifier + ":legend");
      }

      var representativeFeature = firstFeatureForFamily(layer, representative);
      var expectedLayerColor = representativeFeature
        ? primaryStyleColor(IMB.geometryStyle(spec, representativeFeature, visual))
        : IMB.colorFor(spec, {}, visual, representative);
      var actualLayerColor = layerSwatches[index]
        ? layerSwatches[index].style.backgroundColor
          || window.getComputedStyle(layerSwatches[index]).backgroundColor
        : "";
      layerControlColors[identifier] = actualLayerColor;
      if (normalizeColor(expectedLayerColor) !== normalizeColor(actualLayerColor)) {
        mismatches.push(identifier + ":layer-control");
      }
    });

    return Object.assign({}, details || {}, {
      representativeFamilies: representativeFamilies,
      layerFillColors: fillColors,
      layerStrokeColors: strokeColors,
      legendColors: legendColors,
      expectedLegendColors: expectedColors,
      layerControlColors: layerControlColors,
      legendStyleConsistent: mismatches.length === 0,
      legendStyleMismatches: mismatches
    });
  }

  var originalFinish = IMB.finish;
  IMB.finish = function (template, details) {
    var next = template === "multilayer" ? collectVisualQA(details) : details;
    return originalFinish(template, next);
  };

  IMB.onReady(function () {
    var app = document.getElementById("imb-app");
    if (!app || !app.classList.contains("multilayer-app")) {
      return;
    }

    var zh = String(document.documentElement.lang || "").toLocaleLowerCase().indexOf("zh") === 0;
    var sidebarToggle = document.getElementById("imb-collapse");
    if (sidebarToggle) {
      sidebarToggle.classList.add("imb-sidebar-edge-toggle");
      function syncSidebarTitle() {
        var expanded = sidebarToggle.getAttribute("aria-expanded") !== "false";
        sidebarToggle.title = expanded
          ? (zh ? "\u6536\u8d77\u641c\u7d22\u9762\u677f" : "Collapse search panel")
          : (zh ? "\u5c55\u5f00\u641c\u7d22\u9762\u677f" : "Expand search panel");
        sidebarToggle.setAttribute("aria-label", sidebarToggle.title);
      }
      syncSidebarTitle();
      new MutationObserver(syncSidebarTitle).observe(sidebarToggle, {
        attributes: true,
        attributeFilter: ["aria-expanded"]
      });
    }

    var host = document.getElementById("imb-map-controls");
    if (!host || document.getElementById("imb-controls-collapse")) {
      return;
    }
    var toggle = document.createElement("button");
    toggle.id = "imb-controls-collapse";
    toggle.className = "imb-controls-collapse";
    toggle.type = "button";
    toggle.setAttribute("aria-controls", "imb-map-controls");
    host.insertBefore(toggle, host.firstChild);

    function setControlsCollapsed(collapsed) {
      var next = Boolean(collapsed);
      app.classList.toggle("is-controls-collapsed", next);
      toggle.setAttribute("aria-expanded", next ? "false" : "true");
      toggle.textContent = next ? "\u2039" : "\u203a";
      toggle.title = next
        ? (zh ? "\u5c55\u5f00\u5730\u56fe\u63a7\u5236" : "Expand map controls")
        : (zh ? "\u6536\u8d77\u5730\u56fe\u63a7\u5236" : "Collapse map controls");
      toggle.setAttribute("aria-label", toggle.title);
      IMB.qa.controlsCollapsed = next;
      return true;
    }

    toggle.addEventListener("click", function () {
      setControlsCollapsed(!app.classList.contains("is-controls-collapsed"));
    });
    setControlsCollapsed(false);
    IMB.qa.actions.toggleControls = setControlsCollapsed;
  });
}());
