(() => {
  "use strict";

  const root = document.getElementById("cybermancy-atlas");
  if (!root || typeof maplibregl === "undefined") return;

  const VIEWS = {
    regional: { center: [-122.18, 47.43], zoom: 8.05 },
    seattle: { center: [-122.326, 47.601], zoom: 10.55 },
  };

  const BASEMAP = "https://tiles.openfreemap.org/styles/dark";

  const map = new maplibregl.Map({
    container: "cybermancy-atlas-map",
    style: BASEMAP,
    ...VIEWS.regional,
    maxZoom: 14,
    minZoom: 7,
    attributionControl: true,
  });

  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

  const inset = new maplibregl.Map({
    container: "cybermancy-atlas-inset",
    style: BASEMAP,
    ...VIEWS.seattle,
    interactive: false,
    attributionControl: false,
  });

  const panel = {
    name: document.getElementById("atlas-name"),
    category: document.getElementById("atlas-category"),
    description: document.getElementById("atlas-description"),
    facts: document.getElementById("atlas-facts"),
    heroCode: document.getElementById("atlas-hero-code"),
  };
  const legend = document.getElementById("cybermancy-atlas-legend");
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
  let selectedId = null;
  let hoveredId = null;
  let allFeatures = [];

  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    })[character]);

  const featureBounds = (feature) => {
    const bounds = new maplibregl.LngLatBounds();
    const visit = (coordinates) => {
      if (typeof coordinates[0] === "number") bounds.extend(coordinates);
      else coordinates.forEach(visit);
    };
    visit(feature.geometry.coordinates);
    return bounds;
  };

  const sourceFor = (feature) => feature.properties.map_layer === "district" ? "districts" : "regions";

  const setFeatureState = (feature, state) => {
    if (!feature) return;
    map.setFeatureState({ source: sourceFor(feature), id: feature.id }, state);
  };

  const renderFacts = (properties) => {
    const facts = [
      ["Status", properties.status],
      ["Known for", properties.known_for],
      ["Access", properties.access],
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

  const showFeature = (feature, lock = false) => {
    if (!feature) return;
    const properties = feature.properties;
    panel.name.textContent = properties.name;
    panel.category.textContent = properties.category;
    panel.description.textContent = properties.description;
    panel.heroCode.textContent = properties.code || "SEA // MAP";
    renderFacts(properties);

    const bounds = featureBounds(feature);
    const insetSource = inset.getSource("selection");
    if (insetSource) {
      insetSource.setData({ type: "FeatureCollection", features: [feature] });
    }
    inset.fitBounds(bounds, { padding: 18, duration: 0, maxZoom: 12.5 });

    if (lock) {
      if (selectedId !== null) {
        const old = allFeatures.find((item) => item.id === selectedId);
        setFeatureState(old, { selected: false });
      }
      selectedId = feature.id;
      setFeatureState(feature, { selected: true });
      map.fitBounds(bounds, { padding: 55, duration: 700, maxZoom: 12.25 });
      updateLegendSelection();
    }
  };

  const updateLegendSelection = () => {
    legend.querySelectorAll("button").forEach((button) => {
      button.setAttribute("aria-current", String(button.dataset.featureId === String(selectedId)));
    });
  };

  const renderLegend = () => {
    legend.replaceChildren();
    allFeatures
      .slice()
      .sort((a, b) => a.properties.legend_order - b.properties.legend_order)
      .forEach((feature) => {
        const button = document.createElement("button");
        const swatch = document.createElement("span");
        button.type = "button";
        button.dataset.featureId = feature.id;
        button.style.setProperty("--legend-color", feature.properties.color);
        button.setAttribute("aria-current", "false");
        swatch.className = "atlas-swatch";
        swatch.setAttribute("aria-hidden", "true");
        button.append(swatch, document.createTextNode(feature.properties.name));
        button.addEventListener("click", () => showFeature(feature, true));
        legend.append(button);
      });
  };

  const addPolygonSource = (sourceId, data, minZoom, maxZoom) => {
    map.addSource(sourceId, { type: "geojson", data, generateId: false });
    map.addLayer({
      id: `${sourceId}-fill`,
      type: "fill",
      source: sourceId,
      minzoom: minZoom,
      maxzoom: maxZoom,
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
      minzoom: minZoom,
      maxzoom: maxZoom,
      paint: {
        "line-color": ["get", "color"],
        "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 3.2, 1.7],
        "line-opacity": 0.95,
      },
    });
    map.addLayer({
      id: `${sourceId}-label`,
      type: "symbol",
      source: sourceId,
      minzoom: minZoom,
      maxzoom: maxZoom,
      layout: {
        "text-field": ["get", "name"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 8, 10, 12, 15],
        "text-font": ["Open Sans Bold"],
        "text-transform": "uppercase",
        "text-letter-spacing": 0.08,
      },
      paint: {
        "text-color": "#ecf7f8",
        "text-halo-color": "#07131b",
        "text-halo-width": 1.4,
      },
    });

    [`${sourceId}-fill`, `${sourceId}-label`].forEach((layerId) => {
      map.on("mouseenter", layerId, (event) => {
        map.getCanvas().style.cursor = "pointer";
        const feature = event.features[0];
        if (hoveredId !== null && hoveredId !== feature.id) {
          const old = allFeatures.find((item) => item.id === hoveredId);
          setFeatureState(old, { hover: false });
        }
        hoveredId = feature.id;
        setFeatureState(feature, { hover: true });
        if (selectedId === null) showFeature(feature, false);
        popup
          .setLngLat(event.lngLat)
          .setHTML(`<strong>${escapeHtml(feature.properties.name)}</strong>`)
          .addTo(map);
      });
      map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
        if (hoveredId !== null) {
          const old = allFeatures.find((item) => item.id === hoveredId);
          setFeatureState(old, { hover: false });
          hoveredId = null;
        }
      });
      map.on("click", layerId, (event) => showFeature(event.features[0], true));
    });
  };

  const addContext = (data) => {
    map.addSource("context", { type: "geojson", data });
    map.addLayer({
      id: "context-lines",
      type: "line",
      source: "context",
      filter: ["==", ["geometry-type"], "LineString"],
      paint: {
        "line-color": ["coalesce", ["get", "color"], "#f7c65d"],
        "line-width": 2,
        "line-dasharray": [2, 2],
        "line-opacity": 0.8,
      },
    });
    map.addLayer({
      id: "context-points",
      type: "circle",
      source: "context",
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-radius": 5,
        "circle-color": ["coalesce", ["get", "color"], "#f7c65d"],
        "circle-stroke-color": "#07131b",
        "circle-stroke-width": 2,
      },
    });
    map.addLayer({
      id: "context-labels",
      type: "symbol",
      source: "context",
      minzoom: 9,
      layout: {
        "text-field": ["get", "name"],
        "text-size": 11,
        "text-offset": [0, 1.15],
        "text-anchor": "top",
      },
      paint: {
        "text-color": "#f6d889",
        "text-halo-color": "#07131b",
        "text-halo-width": 1.2,
      },
    });
  };

  const loadJson = async (path) => {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Unable to load ${path}: ${response.status}`);
    return response.json();
  };

  Promise.all([
    loadJson(root.dataset.regions),
    loadJson(root.dataset.districts),
    loadJson(root.dataset.context),
    new Promise((resolve) => map.on("load", resolve)),
    new Promise((resolve) => inset.on("load", resolve)),
  ])
    .then(([regions, districts, context]) => {
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
      regions.features.forEach((feature) => { feature.properties.map_layer = "region"; });
      districts.features.forEach((feature) => { feature.properties.map_layer = "district"; });
      allFeatures = [...regions.features, ...districts.features];
      addPolygonSource("regions", regions, 0, 10.4);
      addPolygonSource("districts", districts, 9.2, 24);
      addContext(context);
      renderLegend();
    })
    .catch((error) => {
      panel.name.textContent = "Map unavailable";
      panel.description.textContent = error.message;
    });

  root.querySelectorAll("[data-atlas-view]").forEach((button) => {
    button.addEventListener("click", () => {
      const viewName = button.dataset.atlasView;
      root.querySelectorAll("[data-atlas-view]").forEach((item) => {
        item.setAttribute("aria-pressed", String(item === button));
      });
      if (selectedId !== null) {
        const old = allFeatures.find((item) => item.id === selectedId);
        setFeatureState(old, { selected: false });
      }
      selectedId = null;
      updateLegendSelection();
      map.flyTo({ ...VIEWS[viewName], duration: 850, essential: true });
    });
  });

  window.addEventListener("resize", () => {
    map.resize();
    inset.resize();
  });
})();
