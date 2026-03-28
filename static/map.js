/* global L, DATA */

(function () {
    "use strict";

    // Sidebar toggle.
    var sidebar = document.getElementById("sidebar");
    var toggle = document.getElementById("sidebar-toggle");
    if (window.innerWidth <= 600) {
        sidebar.classList.add("collapsed");
    }
    toggle.addEventListener("click", function () {
        sidebar.classList.toggle("collapsed");
        setTimeout(function () { map.invalidateSize(); }, 250);
    });

    const map = L.map("map", { zoomControl: true }).setView([52.2, 0.12], 12);

    // Tile layer.
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    // Grid overlay.
    const gridLayer = L.layerGroup().addTo(map);
    const gridRects = {};  // "gx,gy" -> rectangle

    DATA.grid_squares.forEach(function (sq) {
        const n = sq.quadrants_visited;
        const opacity = n === 0 ? 0 : 0.15 + (n / 4) * 0.45;
        const rect = L.polygon(sq.corners, {
            color: "#1864ab",
            weight: 0.5,
            fillColor: "#1864ab",
            fillOpacity: opacity,
        });

        // Tooltip.
        let tip = "<div class='grid-tooltip'><strong>" + n + "/4 quadrants</strong>";
        if (sq.walks.length > 0) {
            tip += "<div class='walks-list'>" + sq.walks.join(", ") + "</div>";
        }
        tip += "</div>";
        rect.bindTooltip(tip, { sticky: true });

        // Click: show walks for this square.
        rect.on("click", function () {
            clearHighlights();
            sq.walks.forEach(function (wname) {
                highlightWalk(wname);
            });
        });

        rect.addTo(gridLayer);
        gridRects[sq.gx + "," + sq.gy] = rect;
    });

    // Walk routes.
    const walkPolylines = {};
    const defaultColor = "#4263eb";
    const highlightColor = "#f03e3e";

    DATA.walks.forEach(function (w) {
        if (w.track_points.length === 0) return;
        const latlngs = w.track_points.map(function (p) {
            return [p[0], p[1]];
        });
        const polyline = L.polyline(latlngs, {
            color: defaultColor,
            weight: 2,
            opacity: 0.4,
        }).addTo(map);
        walkPolylines[w.name] = polyline;
    });

    // Fit map to grid bounds.
    if (DATA.grid_bounds) {
        map.fitBounds([
            [DATA.grid_bounds.sw_lat, DATA.grid_bounds.sw_lon],
            [DATA.grid_bounds.ne_lat, DATA.grid_bounds.ne_lon],
        ]);
    }

    // Sidebar walk list.
    const walkList = document.getElementById("walk-list");
    let activeWalk = null;

    DATA.walks.forEach(function (w) {
        const div = document.createElement("div");
        div.className = "walk-item";
        div.dataset.walkName = w.name;

        const nameEl = document.createElement("div");
        nameEl.className = "walk-name";
        nameEl.textContent = w.name;
        div.appendChild(nameEl);

        const metaEl = document.createElement("div");
        metaEl.className = "walk-meta";
        const parts = [];
        if (w.date) parts.push(w.date);
        parts.push((w.distance / 1000).toFixed(1) + " km");
        metaEl.textContent = parts.join(" · ");
        div.appendChild(metaEl);

        div.addEventListener("click", function () {
            if (activeWalk === w.name) {
                clearHighlights();
                activeWalk = null;
                div.classList.remove("active");
                return;
            }
            clearHighlights();
            activeWalk = w.name;
            document.querySelectorAll(".walk-item").forEach(function (el) {
                el.classList.remove("active");
            });
            div.classList.add("active");
            highlightWalk(w.name);

            // Fit to walk bounds.
            const pl = walkPolylines[w.name];
            if (pl) {
                map.fitBounds(pl.getBounds(), { padding: [40, 40] });
            }
        });

        walkList.appendChild(div);
    });

    function highlightWalk(name) {
        const pl = walkPolylines[name];
        if (pl) {
            pl.setStyle({ color: highlightColor, weight: 3, opacity: 0.9 });
            pl.bringToFront();
        }
        // Highlight sidebar item.
        document.querySelectorAll(".walk-item").forEach(function (el) {
            if (el.dataset.walkName === name) {
                el.classList.add("active");
            }
        });
    }

    function clearHighlights() {
        activeWalk = null;
        Object.values(walkPolylines).forEach(function (pl) {
            pl.setStyle({ color: defaultColor, weight: 2, opacity: 0.4 });
        });
        document.querySelectorAll(".walk-item.active").forEach(function (el) {
            el.classList.remove("active");
        });
    }

    // Stats.
    const visitedCount = DATA.grid_squares.filter(function (sq) {
        return sq.quadrants_visited > 0;
    }).length;
    const totalSquares = DATA.grid_squares.length;
    document.getElementById("stats").textContent =
        visitedCount + "/" + totalSquares + " squares visited · " + DATA.walks.length + " walks";
})();
