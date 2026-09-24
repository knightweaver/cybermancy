(() => {
  "use strict";

  let cleanupAtlas = () => {};

  const initializeAtlas = () => {
    cleanupAtlas();
    document.body.classList.remove("atlas-fullscreen-page");

    const root = document.getElementById("cybermancy-atlas");
    if (!root || typeof maplibregl === "undefined") return;

    const isFullscreen = new URLSearchParams(window.location.search).get("atlas") === "fullscreen";
    document.body.classList.toggle("atlas-fullscreen-page", isFullscreen);
    const atlasMode = root.dataset.atlasMode === "gm" ? "gm" : "player";
    const atlasAssetRoot = new URL(root.dataset.assetRoot || "../../assets/", window.location.href);

    let destroyed = false;

  const BASEMAP = "https://tiles.openfreemap.org/styles/dark";
  const VIEW_CONFIG = {
    regional: {
      bounds: [[-122.82, 46.95], [-121.18, 48.25]],
      layer: "region",
      overview: {
        code: "SEA // 01",
        category: "Regional overview",
        name: "The Puget Sound Corridor",
        description: "Three surviving city-states and their contested approaches are linked by guarded roads, ferries, maritime trade, and corporate necessity.",
      },
    },
    seattle: {
      bounds: [[-122.445, 47.475], [-122.235, 47.705]],
      layer: "district",
      overview: {
        code: "SEA // CITY",
        category: "Seattle overview",
        name: "The Seattle Enclave",
        description: "Seattle's surviving districts are divided by corporate authority, infrastructure, old loyalties, and the hazards beyond defended streets.",
      },
    },
  };
  const CONTEXT_CATEGORIES = [
    { id: "landmark", label: "Landmark", symbol: "◆", color: "#b991ff" },
    { id: "transit", label: "Transit", symbol: "●", color: "#5adce4" },
    { id: "corporate", label: "Corporate", symbol: "■", color: "#ff8a55" },
    { id: "hazard", label: "Hazard", symbol: "▲", color: "#ff5b60" },
    { id: "settlement", label: "Settlement", symbol: "⬟", color: "#79df8a" },
    { id: "event", label: "Event", symbol: "✦", color: "#e95fd5" },
    { id: "route", label: "Route", symbol: "━", color: "#f1c96d" },
  ];

  const categoryExpression = (property, fallback) => [
    "match",
    ["get", "category"],
    ...CONTEXT_CATEGORIES.flatMap((category) => [category.id, category[property]]),
    fallback,
  ];

  const map = new maplibregl.Map({
    container: "cybermancy-atlas-map",
    style: BASEMAP,
    bounds: VIEW_CONFIG.regional.bounds,
    fitBoundsOptions: { padding: 36 },
    maxZoom: 14,
    minZoom: 7,
    attributionControl: true,
  });

  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

  const inset = new maplibregl.Map({
    container: "cybermancy-atlas-inset",
    style: BASEMAP,
    bounds: VIEW_CONFIG.seattle.bounds,
    fitBoundsOptions: { padding: 12 },
    interactive: false,
    attributionControl: false,
  });

  const panel = {
    name: document.getElementById("atlas-name"),
    category: document.getElementById("atlas-category"),
    description: document.getElementById("atlas-description"),
    facts: document.getElementById("atlas-facts"),
    heroCode: document.getElementById("atlas-hero-code"),
    heroImage: document.getElementById("atlas-hero-image"),
  };
  const legend = document.getElementById("cybermancy-atlas-legend");
  const poiKey = document.getElementById("cybermancy-atlas-poi-key");
  const note = root.querySelector(".atlas-map-note");
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
  let activeView = "regional";
  let selectedFeature = null;
  let hoveredFeature = null;
  let allFeatures = [];
  let atlasReady = false;
  let requestedView = "regional";

  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    })[character]);

  const renderHeroImage = (properties = {}) => {
    if (!panel.heroImage) return;

    const imageAsset = properties.image_asset;
    if (!imageAsset) {
      panel.heroImage.dataset.requestedSrc = "";
      panel.heroImage.hidden = true;
      panel.heroImage.removeAttribute("src");
      return;
    }

    const source = new URL(imageAsset, atlasAssetRoot).href;
    panel.heroImage.dataset.requestedSrc = source;
    panel.heroImage.hidden = true;

    panel.heroImage.onload = () => {
      if (panel.heroImage.dataset.requestedSrc === source) panel.heroImage.hidden = false;
    };
    panel.heroImage.onerror = () => {
      if (panel.heroImage.dataset.requestedSrc === source) {
        panel.heroImage.hidden = true;
        panel.heroImage.removeAttribute("src");
      }
    };
    panel.heroImage.src = source;
  };

  const featureBounds = (feature) => {
    const bounds = new maplibregl.LngLatBounds();
    const visit = (coordinates) => {
      if (typeof coordinates[0] === "number") bounds.extend(coordinates);
      else coordinates.forEach(visit);
    };
    visit(feature.geometry.coordinates);
    return bounds;
  };

  const sourceFor = (feature) => ({
    district: "districts",
    region: "regions",
    context: "context",
  })[feature.properties.map_layer];

  const categoryLabelFor = (feature) => {
    if (feature.properties.map_layer !== "context") return feature.properties.category;
    const category = CONTEXT_CATEGORIES.find((item) => item.id === feature.properties.category);
    const label = category
      ? feature.properties.category === "route"
        ? "Route"
        : `${category.label} point of interest`
      : "Map feature";
    return atlasMode === "gm" && feature.properties.audience === "gm"
      ? `${label} · GM only`
      : label;
  };

  const canonicalFeature = (feature) => allFeatures.find(
    (item) => item.id === feature.id
      && item.properties.map_layer === feature.properties.map_layer,
  ) || feature;

  const featureLabelPoint = (feature) => {
    if (feature.properties.label_coordinates) return feature.properties.label_coordinates;
    const bounds = featureBounds(feature);
    const southwest = bounds.getSouthWest();
    const northeast = bounds.getNorthEast();
    return [
      (southwest.lng + northeast.lng) / 2,
      (southwest.lat + northeast.lat) / 2,
    ];
  };

  const labelCollection = (data) => ({
    type: "FeatureCollection",
    features: data.features.map((feature) => ({
      type: "Feature",
      id: feature.id,
      properties: feature.properties,
      geometry: { type: "Point", coordinates: featureLabelPoint(feature) },
    })),
  });

  const setFeatureState = (feature, state) => {
    if (!feature || !map.getSource(sourceFor(feature))) return;
    map.setFeatureState({ source: sourceFor(feature), id: feature.id }, state);
  };

  const renderFacts = (properties = {}) => {
    const facts = [
      ["Status", properties.status],
      ["Known for", properties.known_for],
      ["Access", properties.access],
      ["Governance", properties.governance],
      ["Communities", properties.communities],
      ["Organizations", properties.organizations],
      ["Connections", properties.connections],
      ...(atlasMode === "gm" ? [
        ["Visibility", properties.audience === "gm" ? "GM only" : properties.audience === "player" ? "Player-visible" : null],
        ["GM notes", properties.gm_notes],
        ["Adventure hooks", properties.adventure_hooks],
        ["Events", properties.events],
      ] : []),
    ].filter(([, value]) => value);
    panel.facts.replaceChildren();
    facts.forEach(([label, value]) => {
      const term = document.createElement("dt");
      const detail = document.createElement("dd");
      term.textContent = label;
      detail.textContent = value;
      panel.facts.append(term, detail);
    });
  };

  const showOverview = () => {
    const overview = VIEW_CONFIG[activeView].overview;
    panel.name.textContent = overview.name;
    panel.category.textContent = overview.category;
    panel.description.textContent = overview.description;
    panel.heroCode.textContent = overview.code;
    renderHeroImage();
    renderFacts();
    const insetSource = inset.getSource("selection");
    if (insetSource) insetSource.setData({ type: "FeatureCollection", features: [] });
    inset.fitBounds(VIEW_CONFIG[activeView].bounds, { padding: 12, duration: 0 });
  };

  const updateLegendSelection = () => {
    legend.querySelectorAll("button").forEach((button) => {
      const matches = selectedFeature
        && button.dataset.featureId === String(selectedFeature.id)
        && button.dataset.featureLayer === selectedFeature.properties.map_layer;
      button.setAttribute("aria-current", String(Boolean(matches)));
    });
  };

  const showFeature = (feature, lock = false) => {
    if (!feature) return;
    const properties = feature.properties;
    panel.name.textContent = properties.name;
    panel.category.textContent = categoryLabelFor(feature);
    panel.description.textContent = properties.description;
    panel.heroCode.textContent = properties.code || "SEA // MAP";
    renderHeroImage(properties);
    renderFacts(properties);

    const bounds = featureBounds(feature);
    const insetSource = inset.getSource("selection");
    if (insetSource) insetSource.setData({ type: "FeatureCollection", features: [feature] });
    inset.fitBounds(bounds, { padding: 18, duration: 0, maxZoom: 12.5 });

    if (lock) {
      setFeatureState(selectedFeature, { selected: false });
      selectedFeature = feature;
      setFeatureState(feature, { selected: true });
      map.fitBounds(bounds, { padding: 55, duration: 700, maxZoom: 12.25 });
      updateLegendSelection();
    }
  };

  const featuresForActiveView = () => allFeatures.filter(
    (feature) => feature.properties.map_layer === VIEW_CONFIG[activeView].layer,
  );

  const renderLegend = () => {
    legend.replaceChildren();
    featuresForActiveView()
      .slice()
      .sort((a, b) => a.properties.legend_order - b.properties.legend_order)
      .forEach((feature) => {
        const button = document.createElement("button");
        const swatch = document.createElement("span");
        button.type = "button";
        button.dataset.featureId = feature.id;
        button.dataset.featureLayer = feature.properties.map_layer;
        button.style.setProperty("--legend-color", feature.properties.color);
        button.setAttribute("aria-current", "false");
        swatch.className = "atlas-swatch";
        swatch.setAttribute("aria-hidden", "true");
        button.append(swatch, document.createTextNode(feature.properties.name));
        button.addEventListener("click", () => showFeature(feature, true));
        legend.append(button);
      });
    updateLegendSelection();
  };

  const bindPolygonEvents = (sourceId) => {
    [`${sourceId}-fill`, `${sourceId}-label`].forEach((layerId) => {
      map.on("mouseenter", layerId, (event) => {
        map.getCanvas().style.cursor = "pointer";
        const feature = canonicalFeature(event.features[0]);
        if (hoveredFeature && (sourceFor(hoveredFeature) !== sourceId || hoveredFeature.id !== feature.id)) {
          setFeatureState(hoveredFeature, { hover: false });
        }
        hoveredFeature = feature;
        setFeatureState(feature, { hover: true });
        if (!selectedFeature) showFeature(feature, false);
        popup
          .setLngLat(event.lngLat)
          .setHTML(`<strong>${escapeHtml(feature.properties.name)}</strong>`)
          .addTo(map);
      });
      map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
        setFeatureState(hoveredFeature, { hover: false });
        hoveredFeature = null;
      });
      map.on("click", layerId, (event) => showFeature(canonicalFeature(event.features[0]), true));
    });
  };

  const bindContextEvents = () => {
    ["context-lines", "context-points", "context-point-symbols", "context-labels"].forEach((layerId) => {
      map.on("mouseenter", layerId, (event) => {
        const eventFeature = event.features[0];
        map.getCanvas().style.cursor = "pointer";
        const feature = canonicalFeature(eventFeature);
        setFeatureState(hoveredFeature, { hover: false });
        hoveredFeature = feature;
        setFeatureState(feature, { hover: true });
        if (!selectedFeature) showFeature(feature, false);
        popup
          .setLngLat(event.lngLat)
          .setHTML(`<strong>${escapeHtml(feature.properties.name)}</strong>`)
          .addTo(map);
      });
      map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
        setFeatureState(hoveredFeature, { hover: false });
        hoveredFeature = null;
      });
      map.on("click", layerId, (event) => {
        const eventFeature = event.features[0];
        const feature = canonicalFeature(eventFeature);
        const requestedScope = feature.properties.map_scope;
        const targetView = requestedScope === "regional" || requestedScope === "seattle"
          ? requestedScope
          : activeView;
        if (activeView !== targetView) applyView(targetView, false);
        showFeature(feature, true);
      });
    });
  };

  const contextFilter = (geometryType, viewName) => [
    "all",
    ["==", ["geometry-type"], geometryType],
    [
      "any",
      ["!", ["has", "map_scope"]],
      ["==", ["get", "map_scope"], "both"],
      ["==", ["get", "map_scope"], viewName],
    ],
  ];

  const contextScopeFilter = (viewName) => [
    "any",
    ["!", ["has", "map_scope"]],
    ["==", ["get", "map_scope"], "both"],
    ["==", ["get", "map_scope"], viewName],
  ];

  const addPolygonSource = (sourceId, data) => {
    map.addSource(sourceId, { type: "geojson", data, generateId: false });
    map.addSource(`${sourceId}-labels`, {
      type: "geojson",
      data: labelCollection(data),
      generateId: false,
    });
    map.addLayer({
      id: `${sourceId}-fill`,
      type: "fill",
      source: sourceId,
      paint: {
        "fill-color": ["get", "color"],
        "fill-opacity": [
          "case",
          ["boolean", ["feature-state", "selected"], false], 0.42,
          ["boolean", ["feature-state", "hover"], false], 0.30,
          0.16,
        ],
      },
    });
    map.addLayer({
      id: `${sourceId}-line`,
      type: "line",
      source: sourceId,
      paint: {
        "line-color": ["get", "color"],
        "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 3.2, 1.7],
        "line-opacity": 0.95,
      },
    });
    map.addLayer({
      id: `${sourceId}-label`,
      type: "symbol",
      source: `${sourceId}-labels`,
      layout: {
        "text-field": ["get", "name"],
        "text-size": sourceId === "districts"
          ? ["interpolate", ["linear"], ["zoom"], 8, 9, 10, 10.5, 12, 13]
          : ["interpolate", ["linear"], ["zoom"], 8, 10, 12, 15],
        "text-font": ["Noto Sans Bold"],
        "text-transform": "uppercase",
        "text-letter-spacing": 0.08,
        "text-max-width": sourceId === "districts" ? 9 : 12,
        "text-allow-overlap": sourceId === "districts",
        "text-ignore-placement": sourceId === "districts",
      },
      paint: {
        "text-color": "#ecf7f8",
        "text-halo-color": "#07131b",
        "text-halo-width": 1.4,
      },
    });
    bindPolygonEvents(sourceId);
  };

  const addContext = (data) => {
    map.addSource("context", { type: "geojson", data });
    map.addLayer({
      id: "context-lines",
      type: "line",
      source: "context",
      filter: contextFilter("LineString", "regional"),
      paint: {
        "line-color": ["coalesce", ["get", "color"], "#f7c65d"],
        "line-width": [
          "case",
          ["boolean", ["feature-state", "selected"], false], 4,
          ["boolean", ["feature-state", "hover"], false], 3,
          2,
        ],
        "line-dasharray": [2, 2],
        "line-opacity": 0.8,
      },
    });
    map.addLayer({
      id: "context-points",
      type: "circle",
      source: "context",
      filter: contextFilter("Point", "regional"),
      paint: {
        "circle-radius": [
          "case",
          ["boolean", ["feature-state", "selected"], false], 11,
          ["boolean", ["feature-state", "hover"], false], 10,
          8,
        ],
        "circle-color": [
          "case",
          ["==", ["get", "audience"], "gm"], "#25102d",
          "#07131b",
        ],
        "circle-stroke-color": categoryExpression("color", "#f7c65d"),
        "circle-stroke-width": [
          "case",
          ["boolean", ["feature-state", "selected"], false], 3.5,
          ["boolean", ["feature-state", "hover"], false], 3,
          ["==", ["get", "audience"], "gm"], 3,
          2,
        ],
      },
    });
    map.addLayer({
      id: "context-point-symbols",
      type: "symbol",
      source: "context",
      filter: contextFilter("Point", "regional"),
      layout: {
        "text-field": categoryExpression("symbol", "•"),
        "text-size": 13,
        "text-font": ["Noto Sans Bold"],
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": categoryExpression("color", "#f7c65d"),
      },
    });
    map.addLayer({
      id: "context-labels",
      type: "symbol",
      source: "context",
      minzoom: 7.5,
      filter: contextScopeFilter("regional"),
      layout: {
        "text-field": ["get", "name"],
        "text-size": 11,
        "text-font": ["Noto Sans Regular"],
        "text-offset": [0, 1.15],
        "text-anchor": "top",
      },
      paint: {
        "text-color": categoryExpression("color", "#f6d889"),
        "text-halo-color": "#07131b",
        "text-halo-width": 1.2,
      },
    });

    const presentCategories = new Set(data.features.map((feature) => feature.properties.category));
    poiKey.replaceChildren();
    CONTEXT_CATEGORIES
      .filter((category) => presentCategories.has(category.id))
      .forEach((category) => {
        const item = document.createElement("span");
        const symbol = document.createElement("span");
        item.className = "atlas-poi-key-item";
        symbol.className = "atlas-poi-key-symbol";
        symbol.style.setProperty("--poi-color", category.color);
        symbol.setAttribute("aria-hidden", "true");
        symbol.textContent = category.symbol;
        item.append(symbol, document.createTextNode(category.label));
        poiKey.append(item);
      });
    bindContextEvents();
  };

  const setLayerVisibility = (layerId, visible) => {
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
    }
  };

  const applyView = (viewName, animate = true) => {
    if (!VIEW_CONFIG[viewName]) return;
    requestedView = viewName;
    map.stop();
    inset.stop();
    setFeatureState(selectedFeature, { selected: false });
    setFeatureState(hoveredFeature, { hover: false });
    selectedFeature = null;
    hoveredFeature = null;
    popup.remove();
    activeView = viewName;

    root.querySelectorAll("[data-atlas-view]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.atlasView === activeView));
    });

    const showRegions = activeView === "regional";
    ["fill", "line", "label"].forEach((suffix) => {
      setLayerVisibility(`regions-${suffix}`, showRegions);
      setLayerVisibility(`districts-${suffix}`, !showRegions);
    });
    ["context-lines", "context-points", "context-point-symbols"].forEach((layerId) => {
      const geometryType = layerId === "context-lines" ? "LineString" : "Point";
      if (map.getLayer(layerId)) map.setFilter(layerId, contextFilter(geometryType, activeView));
    });
    if (map.getLayer("context-labels")) {
      map.setFilter("context-labels", contextScopeFilter(activeView));
      setLayerVisibility("context-labels", true);
    }
    if (note) {
      note.textContent = atlasMode === "gm"
        ? "Private GM atlas. Player-visible and unrevealed features may coexist here."
        : showRegions
          ? "Draft fictional boundaries. Select a colored region or use the legend for details."
          : "Draft fictional districts. Select a district, point of interest, or legend entry for details.";
    }

    showOverview();
    renderLegend();
    map.fitBounds(VIEW_CONFIG[activeView].bounds, {
      padding: 36,
      duration: animate ? 850 : 0,
      essential: true,
    });
  };

  const loadJson = async (path) => {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Unable to load ${path}: ${response.status}`);
    return response.json();
  };

  const mapLoaded = (target) => new Promise((resolve) => {
    if (target.loaded()) resolve();
    else target.once("load", resolve);
  });

  const showMapError = (message) => {
    root.classList.add("atlas-load-failed");
    panel.name.textContent = "Map unavailable";
    panel.category.textContent = "Atlas error";
    panel.description.textContent = message;
    panel.heroCode.textContent = "ERR // MAP";
    renderHeroImage();
    renderFacts();
    if (note) note.textContent = "The atlas could not finish loading. See the browser console for details.";
  };

  Promise.all([
    loadJson(root.dataset.regions),
    loadJson(root.dataset.districts),
    loadJson(root.dataset.context),
    mapLoaded(map),
    mapLoaded(inset),
  ])
    .then(([regions, districts, context]) => {
      if (destroyed) return;
      inset.addSource("selection", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      inset.addLayer({
        id: "selection-fill",
        type: "fill",
        source: "selection",
        paint: { "fill-color": ["get", "color"], "fill-opacity": 0.32 },
      });
      inset.addLayer({
        id: "selection-line",
        type: "line",
        source: "selection",
        paint: { "line-color": ["get", "color"], "line-width": 2.5 },
      });
      inset.addLayer({
        id: "selection-point",
        type: "circle",
        source: "selection",
        filter: ["==", ["geometry-type"], "Point"],
        paint: {
          "circle-radius": 7,
          "circle-color": categoryExpression("color", "#f7c65d"),
          "circle-stroke-color": "#07131b",
          "circle-stroke-width": 2,
        },
      });

      regions.features.forEach((feature) => { feature.properties.map_layer = "region"; });
      districts.features.forEach((feature) => { feature.properties.map_layer = "district"; });
      context.features.forEach((feature) => { feature.properties.map_layer = "context"; });
      allFeatures = [...regions.features, ...districts.features, ...context.features];
      addPolygonSource("regions", regions);
      addPolygonSource("districts", districts);
      addContext(context);
      map.moveLayer("regions-label");
      map.moveLayer("districts-label");
      atlasReady = true;
      applyView(requestedView, false);
    })
    .catch((error) => {
      if (destroyed) return;
      console.error("Cybermancy atlas failed to initialize:", error);
      showMapError(error.message);
    });

  map.on("error", (event) => {
    if (!atlasReady && event.error) console.error("Cybermancy atlas map error:", event.error);
  });

  const handleAtlasClick = (event) => {
    const button = event.target.closest("[data-atlas-view]");
    if (!button || !root.contains(button)) return;
    event.preventDefault();
    requestedView = button.dataset.atlasView;
    if (atlasReady) applyView(requestedView);
  };

  root.addEventListener("click", handleAtlasClick);

  const handleResize = () => {
    map.resize();
    inset.resize();
  };

  window.addEventListener("resize", handleResize);
  const resizeObserver = typeof ResizeObserver === "undefined"
    ? null
    : new ResizeObserver(handleResize);
  resizeObserver?.observe(root);

  cleanupAtlas = () => {
    destroyed = true;
    root.removeEventListener("click", handleAtlasClick);
    window.removeEventListener("resize", handleResize);
    resizeObserver?.disconnect();
    popup.remove();
    map.remove();
    inset.remove();
    cleanupAtlas = () => {};
  };
  };

  if (typeof document$ !== "undefined" && typeof document$.subscribe === "function") {
    document$.subscribe(initializeAtlas);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAtlas, { once: true });
  } else {
    initializeAtlas();
  }
})();
