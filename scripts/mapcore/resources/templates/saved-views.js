(function () {
  "use strict";

  var IMB = window.InteractiveMapBuilder;
  if (!IMB || typeof IMB.setupMap !== "function" || typeof IMB.fitToGroups !== "function") {
    return;
  }

  var MAX_VIEWS = 8;
  var originalSetupMap = IMB.setupMap;
  var originalFitToGroups = IMB.fitToGroups;

  function numberOrNull(value) {
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function hash(value) {
    var result = 2166136261;
    String(value || "").split("").forEach(function (character) {
      result ^= character.charCodeAt(0);
      result = Math.imul(result, 16777619);
    });
    return (result >>> 0).toString(36);
  }

  function labels(payload) {
    var zh = IMB.text(document.documentElement.lang).toLocaleLowerCase().indexOf("zh") === 0;
    var fallback = zh ? {
      region: "保存视角",
      overview: "总览",
      save: "+ 保存视角",
      manage: "管理视角",
      close: "关闭",
      defaultName: "视角",
      empty: "暂无保存视角。",
      rename: "重命名",
      remove: "删除",
      renamePrompt: "重命名视角",
      deleteConfirm: "删除“{name}”吗？",
      goTo: "前往 {name}",
      limit: "最多保存 8 个视角。",
      saveHint: "保存当前地图中心和缩放级别。",
      invalidName: "请输入唯一且非空的视角名称。",
      savePrompt: "将当前视角保存为"
    } : {
      region: "Saved views",
      overview: "Overview",
      save: "+ Save view",
      manage: "Manage saved views",
      close: "Close",
      defaultName: "View",
      empty: "No saved views yet.",
      rename: "Rename",
      remove: "Delete",
      renamePrompt: "Rename view",
      deleteConfirm: "Delete “{name}”?",
      goTo: "Go to {name}",
      limit: "You can save up to 8 views.",
      saveHint: "Save the current map center and zoom.",
      invalidName: "Use a unique, non-empty view name.",
      savePrompt: "Save current view as"
    };
    var configured = payload.catalog && payload.catalog.saved_views
      ? payload.catalog.saved_views
      : {};
    Object.keys(configured).forEach(function (key) {
      fallback[key] = IMB.text(configured[key]);
    });
    return fallback;
  }

  function storageFor(payload) {
    var spec = payload.spec || {};
    var layers = Array.isArray(payload.layers) ? payload.layers : [];
    var identity = [
      window.location.pathname || "",
      IMB.text(payload.template || spec.template || ""),
      IMB.text(spec.title || ""),
      layers.map(function (layer, index) {
        return IMB.layerId(layer, index) + ":" + Number(layer && layer.count || 0);
      }).join("|")
    ].join("::");
    var key = "interactive-map-builder:saved-views:v1:" + hash(identity);
    var memory = null;
    try {
      var probe = key + ":probe";
      window.localStorage.setItem(probe, "1");
      window.localStorage.removeItem(probe);
      return {
        key: key,
        persistent: true,
        get: function () { return window.localStorage.getItem(key); },
        set: function (value) { window.localStorage.setItem(key, value); }
      };
    } catch (_error) {
      return {
        key: key,
        persistent: false,
        get: function () { return memory; },
        set: function (value) { memory = value; }
      };
    }
  }

  function normalizeViews(value) {
    if (!Array.isArray(value)) {
      return [];
    }
    return value.slice(0, MAX_VIEWS).map(function (item, index) {
      var center = item && Array.isArray(item.center) ? item.center : [];
      var latitude = numberOrNull(center[0]);
      var longitude = numberOrNull(center[1]);
      var zoom = numberOrNull(item && item.zoom);
      var name = IMB.text(item && item.name).trim();
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

  function readMapView(map) {
    try {
      var center = map.getCenter();
      return {
        center: [Number(center.lat), Number(center.lng)],
        zoom: Number(map.getZoom())
      };
    } catch (_error) {
      return null;
    }
  }

  function createController(map) {
    var payload = IMB.parsePayload();
    var text = labels(payload);
    var storage = storageFor(payload);
    var views = [];
    try {
      views = normalizeViews(JSON.parse(storage.get() || "[]"));
    } catch (_error) {
      views = [];
    }

    var overview = null;
    var activeId = "overview";
    var navigating = false;
    var sequence = views.length;
    var header = document.querySelector(".imb-header");
    var heading = header && header.querySelector(".imb-heading");
    if (!header || !heading) {
      return null;
    }

    var nav = IMB.element("nav", undefined, "imb-saved-views");
    nav.id = "imb-saved-views";
    nav.setAttribute("aria-label", text.region);
    var strip = IMB.element("div", undefined, "imb-saved-view-strip");
    var overviewButton = IMB.element("button", text.overview, "imb-saved-view-chip is-active");
    overviewButton.id = "imb-saved-view-overview";
    overviewButton.type = "button";
    overviewButton.dataset.viewId = "overview";
    overviewButton.setAttribute("aria-pressed", "true");
    var listNode = IMB.element("div", undefined, "imb-saved-view-list");
    listNode.id = "imb-saved-view-list";
    var addButton = IMB.element("button", text.save, "imb-saved-view-add");
    addButton.id = "imb-saved-view-add";
    addButton.type = "button";
    var manageButton = IMB.element("button", "⋯", "imb-saved-view-manage");
    manageButton.id = "imb-saved-view-manage";
    manageButton.type = "button";
    manageButton.title = text.manage;
    manageButton.setAttribute("aria-label", text.manage);
    strip.appendChild(overviewButton);
    strip.appendChild(listNode);
    strip.appendChild(addButton);
    strip.appendChild(manageButton);
    nav.appendChild(strip);
    heading.insertAdjacentElement("afterend", nav);

    var dialog = document.createElement("dialog");
    dialog.id = "imb-saved-view-dialog";
    dialog.className = "imb-saved-view-dialog";
    var dialogCard = IMB.element("div", undefined, "imb-saved-view-dialog-card");
    var dialogHeader = IMB.element("div", undefined, "imb-saved-view-dialog-header");
    dialogHeader.appendChild(IMB.element("h2", text.manage));
    var closeButton = IMB.element("button", "×", "imb-saved-view-dialog-close");
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", text.close);
    dialogHeader.appendChild(closeButton);
    var dialogList = IMB.element("div", undefined, "imb-saved-view-dialog-list");
    dialogCard.appendChild(dialogHeader);
    dialogCard.appendChild(dialogList);
    dialog.appendChild(dialogCard);
    document.body.appendChild(dialog);

    function syncQA() {
      var current = readMapView(map);
      IMB.qa.savedViews = {
        count: views.length,
        max: MAX_VIEWS,
        persistent: storage.persistent,
        storageKey: storage.key,
        activeId: activeId,
        overviewCaptured: Boolean(overview),
        currentCenter: current ? current.center.slice() : [null, null],
        currentZoom: current ? current.zoom : null,
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
      storage.set(JSON.stringify(views));
      syncQA();
    }

    function setActive(identifier) {
      activeId = IMB.text(identifier || "");
      overviewButton.classList.toggle("is-active", activeId === "overview");
      overviewButton.setAttribute("aria-pressed", activeId === "overview" ? "true" : "false");
      Array.prototype.forEach.call(listNode.querySelectorAll("[data-view-id]"), function (node) {
        var selected = node.dataset.viewId === activeId;
        node.classList.toggle("is-active", selected);
        node.setAttribute("aria-pressed", selected ? "true" : "false");
      });
      syncQA();
    }

    function uniqueName(name, exceptId) {
      var normalized = IMB.text(name).trim().toLocaleLowerCase();
      return Boolean(normalized) && !views.some(function (view) {
        return view.id !== exceptId && view.name.toLocaleLowerCase() === normalized;
      });
    }

    function nextName() {
      var used = new Set(views.map(function (view) { return view.name.toLocaleLowerCase(); }));
      var index = 1;
      while (used.has((text.defaultName + " " + index).toLocaleLowerCase())) {
        index += 1;
      }
      return text.defaultName + " " + index;
    }

    function renderManager() {
      dialogList.replaceChildren();
      if (!views.length) {
        dialogList.appendChild(IMB.element("p", text.empty, "imb-saved-view-empty"));
        return;
      }
      views.forEach(function (view) {
        var row = IMB.element("div", undefined, "imb-saved-view-dialog-row");
        row.appendChild(IMB.element("span", view.name, "imb-saved-view-dialog-name"));
        var actions = IMB.element("div", undefined, "imb-saved-view-dialog-actions");
        var rename = IMB.element("button", text.rename, "imb-button imb-button-quiet");
        rename.type = "button";
        rename.addEventListener("click", function () {
          var proposed = window.prompt(text.renamePrompt, view.name);
          if (proposed !== null) {
            renameView(view.id, proposed, true);
          }
        });
        var remove = IMB.element("button", text.remove, "imb-button imb-saved-view-delete");
        remove.type = "button";
        remove.addEventListener("click", function () {
          if (window.confirm(text.deleteConfirm.replace("{name}", view.name))) {
            deleteView(view.id);
          }
        });
        actions.appendChild(rename);
        actions.appendChild(remove);
        row.appendChild(actions);
        dialogList.appendChild(row);
      });
    }

    function render() {
      listNode.replaceChildren();
      views.forEach(function (view) {
        var button = IMB.element("button", view.name, "imb-saved-view-chip");
        button.type = "button";
        button.dataset.viewId = view.id;
        button.title = text.goTo.replace("{name}", view.name);
        button.addEventListener("click", function () { goToView(view.id); });
        listNode.appendChild(button);
      });
      addButton.disabled = views.length >= MAX_VIEWS;
      addButton.title = addButton.disabled ? text.limit : text.saveHint;
      manageButton.hidden = !views.length;
      renderManager();
      setActive(activeId);
    }

    function captureOverview() {
      if (overview) {
        return false;
      }
      var current = readMapView(map);
      if (!current) {
        return false;
      }
      overview = current;
      syncQA();
      return true;
    }

    function navigate(view, identifier) {
      if (!view) {
        return false;
      }
      navigating = true;
      setActive(identifier);
      map.flyTo(view.center, view.zoom, { animate: true, duration: 0.55 });
      window.setTimeout(function () {
        navigating = false;
        setActive(identifier);
      }, 620);
      return true;
    }

    function goToView(identifier) {
      var requested = IMB.text(identifier);
      if (requested === "overview" || requested === text.overview) {
        return navigate(overview, "overview");
      }
      var view = views.find(function (candidate) {
        return candidate.id === requested || candidate.name === requested;
      });
      return view ? navigate(view, view.id) : false;
    }

    function saveView(name, center, zoom, alertOnError) {
      if (views.length >= MAX_VIEWS) {
        if (alertOnError) { window.alert(text.limit); }
        return false;
      }
      var resolvedName = IMB.text(name).trim();
      if (!uniqueName(resolvedName, "")) {
        if (alertOnError) { window.alert(text.invalidName); }
        return false;
      }
      var current = readMapView(map);
      var requestedCenter = Array.isArray(center)
        ? [numberOrNull(center[0]), numberOrNull(center[1])]
        : (current && current.center);
      var requestedZoom = numberOrNull(zoom === undefined ? current && current.zoom : zoom);
      if (!requestedCenter || requestedCenter[0] === null || requestedCenter[1] === null || requestedZoom === null) {
        return false;
      }
      sequence += 1;
      var view = {
        id: "view-" + Date.now().toString(36) + "-" + sequence.toString(36),
        name: resolvedName,
        center: requestedCenter,
        zoom: requestedZoom
      };
      views.push(view);
      activeId = view.id;
      persist();
      render();
      return view.id;
    }

    function renameView(identifier, name, alertOnError) {
      var requested = IMB.text(identifier);
      var view = views.find(function (candidate) { return candidate.id === requested; });
      var resolvedName = IMB.text(name).trim();
      if (!view || !uniqueName(resolvedName, requested)) {
        if (alertOnError) { window.alert(text.invalidName); }
        return false;
      }
      view.name = resolvedName;
      persist();
      render();
      return true;
    }

    function deleteView(identifier) {
      var requested = IMB.text(identifier);
      var next = views.filter(function (view) { return view.id !== requested; });
      if (next.length === views.length) {
        return false;
      }
      views = next;
      if (activeId === requested) {
        activeId = "";
      }
      persist();
      render();
      return true;
    }

    function clearViews() {
      views = [];
      activeId = "";
      persist();
      render();
      return true;
    }

    overviewButton.addEventListener("click", function () { goToView("overview"); });
    addButton.addEventListener("click", function () {
      if (views.length >= MAX_VIEWS) {
        return;
      }
      var proposed = window.prompt(text.savePrompt, nextName());
      if (proposed !== null) {
        saveView(proposed, null, undefined, true);
      }
    });
    manageButton.addEventListener("click", function () {
      renderManager();
      if (typeof dialog.showModal === "function") {
        if (!dialog.open) { dialog.showModal(); }
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
    IMB.qa.actions.goToView = goToView;
    IMB.qa.actions.renameView = function (identifier, name) {
      return renameView(identifier, name, false);
    };
    IMB.qa.actions.deleteView = deleteView;
    IMB.qa.actions.clearSavedViews = clearViews;
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

    render();
    return {
      captureOverview: captureOverview,
      goToView: goToView
    };
  }

  IMB.setupMap = function () {
    var map = originalSetupMap.apply(IMB, arguments);
    map.__imbSavedViews = createController(map);
    return map;
  };

  IMB.fitToGroups = function (map, groups) {
    var result = originalFitToGroups.apply(IMB, arguments);
    if (map && map.__imbSavedViews) {
      window.setTimeout(function () {
        map.__imbSavedViews.captureOverview();
      }, 0);
    }
    return result;
  };
}());