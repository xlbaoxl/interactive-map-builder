(function () {
  "use strict";

  var IMB = window.InteractiveMapBuilder;
  if (!IMB || typeof IMB.setupMap !== "function" || typeof IMB.fitToGroups !== "function") {
    return;
  }

  var MAX_VIEWS = 8;
  var originalSetupMap = IMB.setupMap;
  var originalFitToGroups = IMB.fitToGroups;

  function finiteNumber(value) {
    var numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  function hashString(value) {
    var hash = 2166136261;
    var source = String(value || "");
    for (var index = 0; index < source.length; index += 1) {
      hash ^= source.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(36);
  }

  function mapIdentity(payload) {
    var spec = payload && payload.spec && typeof payload.spec === "object" ? payload.spec : {};
    var layers = payload && Array.isArray(payload.layers) ? payload.layers : [];
    var layerSignature = layers.map(function (layer, index) {
      return IMB.layerId(layer, index) + ":" + Number(layer && layer.count || 0);
    }).join("|");
    return [
      window.location.pathname || "",
      IMB.text(payload && payload.template || spec.template || ""),
      IMB.text(spec.title || ""),
      layerSignature
    ].join("::");
  }

  function storageAdapter(key) {
    try {
      var probe = key + ":probe";
      window.localStorage.setItem(probe, "1");
      window.localStorage.removeItem(probe);
      return {
        persistent: true,
        read: function () { return window.localStorage.getItem(key); },
        write: function (value) { window.localStorage.setItem(key, value); }
      };
    } catch (_error) {
      var memory = null;
      return {
        persistent: false,
        read: function () { return memory; },
        write: function (value) { memory = value; }
      };
    }
  }

  function normalizeViews(raw) {
    if (!Array.isArray(raw)) {
      return [];
    }
    return raw.slice(0, MAX_VIEWS).map(function (item, index) {
      if (!item || typeof item !== "object") {
        return null;
      }
      var name = IMB.text(item.name).trim();
      var center = Array.isArray(item.center) ? item.center : [];
      var latitude = finiteNumber(center[0]);
      var longitude = finiteNumber(center[1]);
      var zoom = finiteNumber(item.zoom);
      if (!name || latitude === null || longitude === null || zoom === null) {
        return null;
      }
      return {
        id: IMB.text(item.id || ("view-" + (index + 1))),
        name: name,
        center: [latitude, longitude],
        zoom: zoom
      };
    }).filter(Boolean);
  }

  function createController(map) {
    var payload = IMB.parsePayload();
    var catalog = payload.catalog && payload.catalog.saved_views
      ? payload.catalog.saved_views
      : {};
    var zh = IMB.text(document.documentElement.lang).toLocaleLowerCase().indexOf("zh") === 0;
    var defaults = zh ? {
      region: "保存视角",
      overview: "总览",
      save: "+ 保存视角",
      manage: "管理视角",
      close: "关闭",
      default_name: "视角",
      empty: "暂无保存视角。",
      rename: "重命名",
      delete: "删除",
      rename_prompt: "重命名视角",
      delete_confirm: "删除“{name}”吗？",
      go_to: "前往 {name}",
      limit_reached: "最多保存 8 个视角。",
      save_hint: "保存当前地图中心和缩放级别。",
      duplicate_name: "请输入唯一且非空的视角名称。",
      save_prompt: "将当前视角保存为"
    } : {
      region: "Saved views",
      overview: "Overview",
      save: "+ Save view",
      manage: "Manage saved views",
      close: "Close",
      default_name: "View",
      empty: "No saved views yet.",
      rename: "Rename",
      delete: "Delete",
      rename_prompt: "Rename view",
      delete_confirm: "Delete “{name}”?",
      go_to: "Go to {name}",
      limit_reached: "You can save up to 8 views.",
      save_hint: "Save the current map center and zoom.",
      duplicate_name: "Use a unique, non-empty view name.",
      save_prompt: "Save current view as"
    };
    function label(key, fallback) {
      return IMB.text(catalog[key] || defaults[key] || fallback || key);
    }

    var header = document.querySelector(".imb-header");
    var heading = header && header.querySelector(".imb-heading");
    if (!header || !heading) {
      return null;
    }

    var storageKey = "interactive-map-builder:saved-views:v1:" + hashString(mapIdentity(payload));
    var storage = storageAdapter(storageKey);
    var views = [];
    try {
      views = normalizeViews(JSON.parse(storage.read() || "[]"));
    } catch (_error) {
      views = [];
    }

    var overview = null;
    var activeId = "overview";
    var navigating = false;
    var sequence = views.length;

    var root = IMB.element("nav", undefined, "imb-saved-views");
    root.id = "imb-saved-views";
    root.setAttribute("aria-label", label("region", "Saved views"));

    var strip = IMB.element("div", undefined, "imb-saved-view-strip");
    var overviewButton = IMB.element("button", label("overview", "Overview"), "imb-saved-view-chip is-active");
    overviewButton.id = "imb-saved-view-overview";
    overviewButton.type = "button";
    overviewButton.dataset.viewId = "overview";
    overviewButton.setAttribute("aria-pressed", "true");

    var listNode = IMB.element("div", undefined, "imb-saved-view-list");
    listNode.id = "imb-saved-view-list";

    var addButton = IMB.element("button", label("save", "+ Save view"), "imb-saved-view-add");
    addButton.id = "imb-saved-view-add";
    addButton.type = "button";

    var manageButton = IMB.element("button", "⋯", "imb-saved-view-manage");
    manageButton.id = "imb-saved-view-manage";
    manageButton.type = "button";
    manageButton.title = label("manage", "Manage saved views");
    manageButton.setAttribute("aria-label", manageButton.title);

    strip.appendChild(overviewButton);
    strip.appendChild(listNode);
    strip.appendChild(addButton);
    strip.appendChild(manageButton);
    root.appendChild(strip);
    heading.insertAdjacentElement("afterend", root);

    var dialog = document.createElement("dialog");
    dialog.id = "imb-saved-view-dialog";
    dialog.className = "imb-saved-view-dialog";
    var dialogCard = IMB.element("div", undefined, "imb-saved-view-dialog-card");
    var dialogHeader = IMB.element("div", undefined, "imb-saved-view-dialog-header");
    dialogHeader.appendChild(IMB.element("h2", label("manage", "Manage saved views")));
    var closeButton = IMB.element("button", "×", "imb-saved-view-dialog-close");
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", label("close", "Close"));
    dialogHeader.appendChild(closeButton);
    var dialogList = IMB.element("div", undefined, "imb-saved-view-dialog-list");
    dialogCard.appendChild(dialogHeader);
    dialogCard.appendChild(dialogList);
    dialog.appendChild(dialogCard);
    document.body.appendChild(dialog);

    function updateQA() {
      var center = map.getCenter();
      IMB.qa.savedViews = {
        count: views.length,
        max: MAX_VIEWS,
        persistent: storage.persistent,
        storageKey: storageKey,
        activeId: activeId,
        overviewCaptured: Boolean(overview),
        currentCenter: [Number(center.lat), Number(center.lng)],
        currentZoom: Number(map.getZoom()),
        views: views.map(function (view) {
          return {
            id: view.id,
            name: view.name,
            center: view.center.slice(),
            zoom: view.zoom
          };
        })
      };
    }

    function persist() {
      storage.write(JSON.stringify(views));
      updateQA();
    }

    function setActive(identifier) {
      activeId = IMB.text(identifier || "");
      overviewButton.classList.toggle("is-active", activeId === "overview");
      overviewButton.setAttribute("aria-pressed", activeId === "overview" ? "true" : "false");
      Array.prototype.forEach.call(listNode.querySelectorAll("[data-view-id]"), function (node) {
        var active = node.dataset.viewId === activeId;
        node.classList.toggle("is-active", active);
        node.setAttribute("aria-pressed", active ? "true" : "false");
      });
      updateQA();
    }

    function defaultName() {
      var base = label("default_name", "View");
      var number = 1;
      var existing = new Set(views.map(function (view) { return view.name.toLocaleLowerCase(); }));
      while (existing.has((base + " " + number).toLocaleLowerCase())) {
        number += 1;
      }
      return base + " " + number;
    }

    function nameAvailable(name, excludedId) {
      var normalized = IMB.text(name).trim().toLocaleLowerCase();
      return Boolean(normalized) && !views.some(function (view) {
        return view.id !== excludedId && view.name.toLocaleLowerCase() === normalized;
      });
    }

    function renderDialog() {
      dialogList.replaceChildren();
      if (!views.length) {
        dialogList.appendChild(IMB.element("p", label("empty", "No saved views yet."), "imb-saved-view-empty"));
        return;
      }
      views.forEach(function (view) {
        var row = IMB.element("div", undefined, "imb-saved-view-dialog-row");
        row.appendChild(IMB.element("span", view.name, "imb-saved-view-dialog-name"));
        var actions = IMB.element("div", undefined, "imb-saved-view-dialog-actions");
        var rename = IMB.element("button", label("rename", "Rename"), "imb-button imb-button-quiet");
        rename.type = "button";
        rename.addEventListener("click", function () {
          var proposed = window.prompt(label("rename_prompt", "Rename view"), view.name);
          if (proposed === null) {
            return;
          }
          renameView(view.id, proposed, true);
        });
        var remove = IMB.element("button", label("delete", "Delete"), "imb-button imb-saved-view-delete");
        remove.type = "button";
        remove.addEventListener("click", function () {
          var message = label("delete_confirm", "Delete this saved view?").replace("{name}", view.name);
          if (window.confirm(message)) {
            deleteView(view.id);
          }
        });
        actions.appendChild(rename);
        actions.appendChild(remove);
        row.appendChild(actions);
        dialogList.appendChild(row);
      });
    }

    function renderViews() {
      listNode.replaceChildren();
      views.forEach(function (view) {
        var button = IMB.element("button", view.name, "imb-saved-view-chip");
        button.type = "button";
        button.dataset.viewId = view.id;
        button.setAttribute("aria-pressed", activeId === view.id ? "true" : "false");
        button.classList.toggle("is-active", activeId === view.id);
        button.title = label("go_to", "Go to {name}").replace("{name}", view.name);
        button.addEventListener("click", function () {
          goToView(view.id);
        });
        listNode.appendChild(button);
      });
      addButton.disabled = views.length >= MAX_VIEWS;
      addButton.title = addButton.disabled
        ? label("limit_reached", "Saved-view limit reached.")
        : label("save_hint", "Save the current map center and zoom.");
      manageButton.hidden = !views.length;
      renderDialog();
      updateQA();
    }

    function captureOverview() {
      if (overview) {
        return false;
      }
      var center = map.getCenter();
      overview = {
        center: [Number(center.lat), Number(center.lng)],
        zoom: Number(map.getZoom())
      };
      updateQA();
      return true;
    }

    function navigate(center, zoom, identifier) {
      var latitude = finiteNumber(center && center[0]);
      var longitude = finiteNumber(center && center[1]);
      var targetZoom = finiteNumber(zoom);
      if (latitude === null || longitude === null || targetZoom === null) {
        return false;
      }
      navigating = true;
      setActive(identifier);
      map.flyTo([latitude, longitude], targetZoom, {
        animate: true,
        duration: 0.55
      });
      window.setTimeout(function () {
        navigating = false;
        setActive(identifier);
      }, 620);
      return true;
    }

    function goToView(identifier) {
      var requested = IMB.text(identifier);
      if (requested === "overview" || requested === label("overview", "Overview")) {
        return overview ? navigate(overview.center, overview.zoom, "overview") : false;
      }
      var view = views.find(function (candidate) {
        return candidate.id === requested || candidate.name === requested;
      });
      return view ? navigate(view.center, view.zoom, view.id) : false;
    }

    function saveView(name, center, zoom, alertOnError) {
      if (views.length >= MAX_VIEWS) {
        if (alertOnError) {
          window.alert(label("limit_reached", "Saved-view limit reached."));
        }
        return false;
      }
      var resolvedName = IMB.text(name).trim();
      if (!resolvedName || !nameAvailable(resolvedName, "")) {
        if (alertOnError) {
          window.alert(label("duplicate_name", "Use a unique, non-empty view name."));
        }
        return false;
      }
      var mapCenter = map.getCenter();
      var requestedCenter = Array.isArray(center) ? center : [mapCenter.lat, mapCenter.lng];
      var latitude = finiteNumber(requestedCenter[0]);
      var longitude = finiteNumber(requestedCenter[1]);
      var targetZoom = finiteNumber(zoom === undefined ? map.getZoom() : zoom);
      if (latitude === null || longitude === null || targetZoom === null) {
        return false;
      }
      sequence += 1;
      var view = {
        id: "view-" + Date.now().toString(36) + "-" + sequence.toString(36),
        name: resolvedName,
        center: [latitude, longitude],
        zoom: targetZoom
      };
      views.push(view);
      persist();
      setActive(view.id);
      renderViews();
      return view.id;
    }

    function renameView(identifier, name, alertOnError) {
      var view = views.find(function (candidate) { return candidate.id === IMB.text(identifier); });
      var resolvedName = IMB.text(name).trim();
      if (!view || !nameAvailable(resolvedName, view.id)) {
        if (alertOnError) {
          window.alert(label("duplicate_name", "Use a unique, non-empty view name."));
        }
        return false;
      }
      view.name = resolvedName;
      persist();
      renderViews();
      return true;
    }

    function deleteView(identifier) {
      var requested = IMB.text(identifier);
      var before = views.length;
      views = views.filter(function (view) { return view.id !== requested; });
      if (views.length === before) {
        return false;
      }
      if (activeId === requested) {
        setActive("");
      }
      persist();
      renderViews();
      return true;
    }

    function clearViews() {
      views = [];
      setActive("");
      persist();
      renderViews();
      return true;
    }

    overviewButton.addEventListener("click", function () {
      goToView("overview");
    });
    addButton.addEventListener("click", function () {
      if (views.length >= MAX_VIEWS) {
        return;
      }
      var proposed = window.prompt(label("save_prompt", "Save current view as"), defaultName());
      if (proposed === null) {
        return;
      }
      saveView(proposed, null, undefined, true);
    });
    manageButton.addEventListener("click", function () {
      renderDialog();
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        dialog.setAttribute("open", "open");
      }
    });
    closeButton.addEventListener("click", function () {
      if (typeof dialog.close === "function") {
        dialog.close();
      } else {
        dialog.removeAttribute("open");
      }
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog && typeof dialog.close === "function") {
        dialog.close();
      }
    });

    map.on("dragstart zoomstart", function () {
      if (!navigating) {
        setActive("");
      }
    });

    IMB.qa.actions.saveView = function (name, center, zoom) {
      return saveView(name, center, zoom, false);
    };
    IMB.qa.actions.goToView = function (identifier) {
      return goToView(identifier);
    };
    IMB.qa.actions.renameView = function (identifier, name) {
      return renameView(identifier, name, false);
    };
    IMB.qa.actions.deleteView = function (identifier) {
      return deleteView(identifier);
    };
    IMB.qa.actions.clearSavedViews = function () {
      return clearViews();
    };
    IMB.qa.actions.listSavedViews = function () {
      return views.map(function (view) {
        return {
          id: view.id,
          name: view.name,
          center: view.center.slice(),
          zoom: view.zoom
        };
      });
    };

    renderViews();
    updateQA();

    return {
      captureOverview: captureOverview,
      goToView: goToView,
      saveView: saveView,
      renameView: renameView,
      deleteView: deleteView
    };
  }

  IMB.setupMap = function () {
    var map = originalSetupMap.apply(IMB, arguments);
    map.__imbSavedViews = createController(map);
    return map;
  };

  IMB.fitToGroups = function (map, groups) {
    var result = originalFitToGroups.apply(IMB, arguments);
    if (map && map.__imbSavedViews && typeof map.__imbSavedViews.captureOverview === "function") {
      window.setTimeout(function () {
        map.__imbSavedViews.captureOverview();
      }, 0);
    }
    return result;
  };
}());