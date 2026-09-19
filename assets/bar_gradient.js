(function () {
    'use strict';

    // Chart id -> vertical bar gradient stops (bottom -> top).
    // Applies linear-gradient(90deg, #054c76, #0c192a, #471c3a) as a real SVG
    // gradient painted directly on the bar shapes — no stacked bar segments,
    // so there are no visible seams/traces in the bars.
    var GRADIENTS = {
        'if-chart': ['#054c76', '#0c192a', '#d90a9b'],
        'if-ts-chart': ['#4139ad', '#384ac3', '#6b79ef']
    };

    var svgNS = 'http://www.w3.org/2000/svg';

    function ensureGradient(svg, gid, stops) {
        var defs = svg.querySelector('defs');
        if (!defs) {
            defs = document.createElementNS(svgNS, 'defs');
            svg.appendChild(defs);
        }
        var grad = defs.querySelector('#' + gid);
        if (!grad) {
            grad = document.createElementNS(svgNS, 'linearGradient');
            grad.setAttribute('id', gid);
            // Vertical: bottom (y1=1) -> top (y2=0), spanning each bar.
            grad.setAttribute('x1', '0');
            grad.setAttribute('y1', '1');
            grad.setAttribute('x2', '0');
            grad.setAttribute('y2', '0');
            stops.forEach(function (c, i) {
                var st = document.createElementNS(svgNS, 'stop');
                st.setAttribute('offset', (i / (stops.length - 1)) * 100 + '%');
                st.setAttribute('stop-color', c);
                grad.appendChild(st);
            });
            defs.appendChild(grad);
        }
        return gid;
    }

    function paint(id) {
        var stops = GRADIENTS[id];
        var el = document.getElementById(id);
        if (!el || !stops) return;
        var svgs = el.querySelectorAll('svg.main-svg');
        svgs.forEach(function (svg, si) {
            var gid = ensureGradient(svg, 'bargrad-' + id + '-' + si, stops);
            var want = 'url(#' + gid + ')';
            var bars = svg.querySelectorAll('.points path.point, g.points path, .bars path');
            bars.forEach(function (p) {
                // Compare the fill ATTRIBUTE (not style) — browsers normalise
                // style.fill with extra quotes, which broke the comparison.
                if (p.getAttribute('fill') !== want) {
                    p.setAttribute('fill', want);
                    // Drop any inline fill left from earlier attempts.
                    if (p.style && p.style.fill) {
                        p.style.removeProperty('fill');
                    }
                }
            });
        });
    }

    // Re-attach watchers periodically: dcc.Loading REMOUNTS the graph div on
    // every refresh (auto-refresh / filter change), creating a new element —
    // so we must keep watching for new elements instead of a one-shot setup.
    var watched = new WeakSet();
    function watch(id) {
        var el = document.getElementById(id);
        if (!el || watched.has(el)) return;
        watched.add(el);
        paint(id);
        var pending = null;
        // Debounce so the observer doesn't fight its own mutations.
        var mo = new MutationObserver(function () {
            if (pending) clearTimeout(pending);
            pending = setTimeout(function () { paint(id); }, 50);
        });
        mo.observe(el, { childList: true, subtree: true,
                         attributes: true, attributeFilter: ['d', 'fill'] });
        // Plotly fires this after every re-render — repaint immediately.
        el.on('plotly_afterplot', function () { paint(id); });
    }

    setInterval(function () {
        Object.keys(GRADIENTS).forEach(watch);
    }, 800);
})();