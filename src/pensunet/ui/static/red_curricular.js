/* Visualizador propio de Pensunet con D3 v7. No usa código de Curricular Analytics. */
(function () {
  "use strict";

  function raizDesdeScript() {
    var script = document.currentScript;
    if (script && script.closest) {
      var cerca = script.closest(".pensunet-red");
      if (cerca) return cerca;
    }
    var todos = document.querySelectorAll(".pensunet-red");
    return todos.length ? todos[todos.length - 1] : null;
  }

  var raiz = raizDesdeScript();
  if (!raiz || typeof d3 === "undefined") return;

  var payload = JSON.parse(raiz.getAttribute("data-payload") || "{}");
  var meta = payload.meta || {};
  var nodos = payload.nodos || [];
  var aristas = payload.aristas || [];
  var semestres = payload.semestres || [];
  var embebido = raiz.classList.contains("embebido");
  var oscuro = raiz.classList.contains("oscuro");

  var W = meta.svg_ancho || 1000;
  var H = meta.svg_alto || 600;
  var escala = meta.escala || 70;
  var margen = meta.margen || 40;
  var maxFilas = meta.max_filas || 1;
  var anchoCaja = meta.ancho_caja || 1.2;
  var altoCaja = meta.alto_caja || 0.92;
  var gapX = meta.gap_x != null ? meta.gap_x : 0.55;
  var ySuperior = meta.y_superior != null ? meta.y_superior : (maxFilas - 1) * 1.18 / 2;
  var columnaAlpha = meta.columna_alpha != null ? meta.columna_alpha : 0.12;

  var colores = meta.colores || {};
  var colorArista = colores.arista || "#5C5657";
  var colorCamino = colores.camino || "#8C1919";
  var colorCuello = colores.cuello || "#FDB400";
  var colorHalo = colores.halo || "rgba(92, 86, 87, 0.2)";
  var colorTextoUi = colores.texto_ui || "#000000";
  var colorFondo = colores.fondo || "#F7F3EE";
  var paletaColumnas = colores.columnas || [
    "#8C1919",
    "#FDB400",
    "#1291C0",
    "#00A859",
  ];

  function hexARgba(hex, alpha) {
    var h = String(hex || "#98999A").replace("#", "");
    if (h.length === 3) {
      h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    }
    var r = parseInt(h.slice(0, 2), 16);
    var g = parseInt(h.slice(2, 4), 16);
    var b = parseInt(h.slice(4, 6), 16);
    return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
  }

  function sx(x) {
    return margen + (x + anchoCaja / 2) * escala;
  }
  function sy(y) {
    return margen + (ySuperior + 1.0 - y) * escala;
  }

  nodos.forEach(function (n) {
    n._w = anchoCaja * escala;
    n._h = altoCaja * escala;
    n._cx = sx(n.x);
    n._cy = sy(n.y);
    n._x = n._cx - n._w / 2;
    n._y = n._cy - n._h / 2;
  });

  var porId = {};
  nodos.forEach(function (n) {
    porId[n.id] = n;
  });

  var viewport = raiz.querySelector("#viewport");
  var detalle = raiz.querySelector("#detalle");
  var tooltip = raiz.querySelector("#tooltip");

  var svg = d3
    .select(raiz.querySelector("#red"))
    .attr("viewBox", "0 0 " + W + " " + H)
    .attr("preserveAspectRatio", "xMidYMid meet");

  var capa = svg.append("g").attr("class", "escena");

  var defs = svg.append("defs");
  var sombraCaja = defs
    .append("filter")
    .attr("id", "sombra-caja")
    .attr("x", "-20%")
    .attr("y", "-20%")
    .attr("width", "140%")
    .attr("height", "140%");
  sombraCaja
    .append("feDropShadow")
    .attr("dx", 0)
    .attr("dy", 1.2)
    .attr("stdDeviation", 1.4)
    .attr("flood-color", "#373435")
    .attr("flood-opacity", 0.22);
  defs
    .append("marker")
    .attr("id", "flecha")
    .attr("viewBox", "0 0 10 10")
    .attr("refX", 9)
    .attr("refY", 5)
    .attr("markerWidth", 7)
    .attr("markerHeight", 7)
    .attr("orient", "auto-start-reverse")
    .append("path")
    .attr("d", "M 0 0 L 10 5 L 0 10 z")
    .attr("fill", colorArista);
  defs
    .append("marker")
    .attr("id", "flecha-camino")
    .attr("viewBox", "0 0 10 10")
    .attr("refX", 9)
    .attr("refY", 5)
    .attr("markerWidth", 7)
    .attr("markerHeight", 7)
    .attr("orient", "auto-start-reverse")
    .append("path")
    .attr("d", "M 0 0 L 10 5 L 0 10 z")
    .attr("fill", colorCamino);
  defs
    .append("marker")
    .attr("id", "flecha-activa")
    .attr("viewBox", "0 0 10 10")
    .attr("refX", 9)
    .attr("refY", 5)
    .attr("markerWidth", 7)
    .attr("markerHeight", 7)
    .attr("orient", "auto-start-reverse")
    .append("path")
    .attr("d", "M 0 0 L 10 5 L 0 10 z")
    .attr("fill", colorCamino);

  var colW = (anchoCaja + gapX) * escala;
  var colPad = Math.max(4, escala * 0.06);
  var gColumnas = capa.append("g").attr("class", "columnas").attr("pointer-events", "none");
  gColumnas
    .selectAll("rect.columna")
    .data(semestres)
    .enter()
    .append("rect")
    .attr("class", "columna")
    .attr("x", function (d) {
      return sx(d.x) - colW / 2 + colPad;
    })
    .attr("y", margen * 0.25)
    .attr("width", Math.max(8, colW - colPad * 2))
    .attr("height", Math.max(40, H - margen * 0.55))
    .attr("rx", 14)
    .attr("ry", 14)
    .attr("fill", function (d, i) {
      var base = d.color || paletaColumnas[i % paletaColumnas.length];
      return hexARgba(base, columnaAlpha);
    });

  var yTitulo = sy(ySuperior + altoCaja * 0.92);
  var gTitulos = capa
    .append("g")
    .attr("class", "titulos-semestre")
    .attr("pointer-events", "none");
  var titulos = gTitulos
    .selectAll("g.titulo-semestre")
    .data(semestres)
    .enter()
    .append("g")
    .attr("class", "titulo-semestre")
    .attr("transform", function (d) {
      return "translate(" + sx(d.x) + "," + yTitulo + ")";
    });
  titulos
    .append("rect")
    .attr("class", "titulo-fondo")
    .attr("x", function () {
      return -Math.min(52, colW * 0.42);
    })
    .attr("y", -16)
    .attr("width", function () {
      return Math.min(104, colW * 0.84);
    })
    .attr("height", 28)
    .attr("rx", 14)
    .attr("ry", 14)
    .attr("fill", function (d, i) {
      var base = d.color || paletaColumnas[i % paletaColumnas.length];
      return hexARgba(base, oscuro ? 0.32 : 0.18);
    })
    .attr("stroke", function (d, i) {
      return d.color || paletaColumnas[i % paletaColumnas.length];
    })
    .attr("stroke-width", 1.4);
  titulos
    .append("text")
    .attr("class", "semestre")
    .attr("text-anchor", "middle")
    .attr("dominant-baseline", "central")
    .attr("y", -1)
    .attr("fill", function (d, i) {
      var base = d.color || paletaColumnas[i % paletaColumnas.length];
      // Dorado y verdes claros: texto oscuro para contraste.
      if (!oscuro && (base === "#FDB400" || base === "#00A859")) return "#1A1A1A";
      if (oscuro) return "#FFFFFF";
      return base === "#FDB400" ? "#1A1A1A" : base;
    })
    .text(function (d) {
      return "Sem. " + d.etiqueta;
    });
  titulos
    .append("line")
    .attr("class", "titulo-acento")
    .attr("x1", function () {
      return -Math.min(28, colW * 0.22);
    })
    .attr("x2", function () {
      return Math.min(28, colW * 0.22);
    })
    .attr("y1", 16)
    .attr("y2", 16)
    .attr("stroke", function (d, i) {
      return d.color || paletaColumnas[i % paletaColumnas.length];
    })
    .attr("stroke-width", 2.5)
    .attr("stroke-linecap", "round")
    .attr("opacity", 0.9);

  function rutaArista(a) {
    var o = porId[a.source];
    var t = porId[a.target];
    if (!o || !t) return "";
    var x0 = o._x + o._w;
    var y0 = o._cy;
    var x1 = t._x;
    var y1 = t._cy;
    var dy = y1 - y0;
    var ctrl = Math.abs(dy) < 8 ? 28 : dy > 0 ? 40 : -40;
    return (
      "M " +
      x0 +
      " " +
      y0 +
      " C " +
      (x0 + ctrl) +
      " " +
      y0 +
      ", " +
      (x1 - ctrl) +
      " " +
      y1 +
      ", " +
      x1 +
      " " +
      y1
    );
  }

  var gAristas = capa.append("g").attr("id", "aristas");
  gAristas
    .selectAll("path.halo")
    .data(aristas)
    .enter()
    .append("path")
    .attr("class", function (d) {
      return "arista halo" + (d.tipo === "debil" ? " debil" : "") + (d.en_camino ? " camino" : "");
    })
    .attr("data-from", function (d) {
      return d.source;
    })
    .attr("data-to", function (d) {
      return d.target;
    })
    .attr("d", rutaArista)
    .attr("stroke", colorHalo)
    .attr("stroke-width", function (d) {
      return d.en_camino ? 8 : 6;
    })
    .attr("opacity", 0.9);

  gAristas
    .selectAll("path.trazo")
    .data(aristas)
    .enter()
    .append("path")
    .attr("class", function (d) {
      return (
        "arista trazo" +
        (d.tipo === "debil" ? " debil" : "") +
        (d.en_camino ? " camino" : "")
      );
    })
    .attr("id", function (d) {
      return "e" + d.source + "-" + d.target;
    })
    .attr("data-from", function (d) {
      return d.source;
    })
    .attr("data-to", function (d) {
      return d.target;
    })
    .attr("d", rutaArista)
    .attr("stroke", function (d) {
      return d.en_camino ? colorCamino : colorArista;
    })
    .attr("stroke-width", function (d) {
      return d.en_camino ? 4.2 : 2.1;
    })
    .attr("opacity", function (d) {
      return d.en_camino ? 1 : 0.42;
    })
    .attr("marker-end", function (d) {
      return d.en_camino ? "url(#flecha-camino)" : "url(#flecha)";
    });

  function partirNombre(nombre) {
    var palabras = String(nombre || "").split(/\s+/);
    if (!palabras.length) return [""];
    var lineas = [];
    var actual = palabras[0];
    for (var i = 1; i < palabras.length; i++) {
      var cand = actual + " " + palabras[i];
      if (cand.length <= 15) actual = cand;
      else {
        lineas.push(actual);
        actual = palabras[i];
      }
    }
    lineas.push(actual);
    return lineas.slice(0, 4);
  }

  var gNodos = capa.append("g").attr("id", "nodos");
  var grupos = gNodos
    .selectAll("g.nodo")
    .data(nodos)
    .enter()
    .append("g")
    .attr("class", function (d) {
      var c = "nodo";
      if (d.cuello) c += " cuello";
      if (d.camino) c += " camino";
      return c;
    })
    .attr("id", function (d) {
      return "n" + d.id;
    })
    .attr("data-id", function (d) {
      return d.id;
    })
    .attr("transform", function (d) {
      return "translate(" + d._x + "," + d._y + ")";
    });

  // Hit area invisible un poco mayor: el panel lateral ya no tapa nodos.
  grupos
    .append("rect")
    .attr("class", "hit")
    .attr("x", -4)
    .attr("y", -4)
    .attr("width", function (d) {
      return d._w + 8;
    })
    .attr("height", function (d) {
      return d._h + 8;
    })
    .attr("fill", "transparent")
    .attr("stroke", "none");

  grupos
    .append("rect")
    .attr("class", "caja")
    .attr("width", function (d) {
      return d._w;
    })
    .attr("height", function (d) {
      return d._h;
    })
    .attr("rx", 9)
    .attr("ry", 9)
    .attr("filter", "url(#sombra-caja)")
    .attr("fill", function (d) {
      return d.color || "#8C1919";
    })
    .attr("stroke", function (d) {
      if (d.camino && d.cuello) return "#8C1919";
      if (d.camino) return colorCamino;
      if (d.cuello) return colorCuello;
      return "rgba(55, 52, 53, 0.55)";
    })
    .attr("stroke-width", function (d) {
      if (d.camino) return 3.6;
      if (d.cuello) return 3;
      return 1.15;
    });

  grupos.each(function (d) {
    var g = d3.select(this);
    var lineas = partirNombre(d.nombre);
    var startY = d._h * 0.22;
    lineas.forEach(function (linea, i) {
      g.append("text")
        .attr("class", "caja-nombre")
        .attr("x", d._w / 2)
        .attr("y", startY + i * 11)
        .attr("text-anchor", "middle")
        .text(linea);
    });
    var pie =
      d.creditos == null ? String(d.id) : d.id + " · " + d.creditos + " cr";
    g.append("text")
      .attr("class", "caja-pie")
      .attr("x", d._w / 2)
      .attr("y", d._h - 8)
      .attr("text-anchor", "middle")
      .text(pie);
  });

  function fmt(valor, digitos) {
    if (valor === null || valor === undefined) return "sin dato";
    if (typeof valor === "number") return Number(valor).toFixed(digitos);
    return String(valor);
  }

  var seleccionId = null;
  var TEXTO_HINT =
    '<div class="dato hint">Pasa el cursor o haz clic en una materia para ver ' +
    "solo sus prerrequisitos y las que habilita.</div>";

  function strokeBase(d) {
    if (d.camino && d.cuello) return "#8C1919";
    if (d.camino) return colorCamino;
    if (d.cuello) return colorCuello;
    return "#373435";
  }

  function strokeWidthBase(d) {
    if (d.camino) return 3.6;
    if (d.cuello) return 3;
    return 1.2;
  }

  function limpiarResaltado() {
    svg.classed("atenua", false);
    grupos
      .classed("activo", false)
      .classed("previo", false)
      .classed("siguiente", false);
    gAristas.selectAll("path.trazo").classed("activa", false);
    grupos.select("rect.caja").each(function (d) {
      d3.select(this)
        .attr("opacity", 1)
        .attr("stroke", strokeBase(d))
        .attr("stroke-width", strokeWidthBase(d));
    });
    gAristas.selectAll("path.trazo").attr("opacity", function (d) {
      return d.en_camino ? 1 : 0.42;
    });
    gAristas.selectAll("path.halo").attr("opacity", 0.9);
  }

  function ocultarTooltip() {
    if (!tooltip) return;
    tooltip.classList.remove("visible");
    tooltip.innerHTML = "";
  }

  function resaltarVecinos(nodo) {
    // Solo pre/pos directos (como al inicio): no ancestros ni descendientes.
    limpiarResaltado();
    svg.classed("atenua", true);
    grupos
      .filter(function (d) {
        return d.id === nodo.id;
      })
      .classed("activo", true)
      .raise();
    (nodo.previos || []).forEach(function (pid) {
      grupos
        .filter(function (d) {
          return d.id === pid;
        })
        .classed("previo", true)
        .raise();
      gAristas
        .selectAll("path.trazo")
        .filter(function (d) {
          return d.source === pid && d.target === nodo.id;
        })
        .classed("activa", true);
    });
    (nodo.siguientes || []).forEach(function (sid) {
      grupos
        .filter(function (d) {
          return d.id === sid;
        })
        .classed("siguiente", true)
        .raise();
      gAristas
        .selectAll("path.trazo")
        .filter(function (d) {
          return d.source === nodo.id && d.target === sid;
        })
        .classed("activa", true);
    });
  }

  function nombresDe(ids) {
    return (ids || [])
      .map(function (codigo) {
        return porId[codigo] ? porId[codigo].nombre : codigo;
      })
      .join(", ");
  }

  function pintarDetalle(nodo, fijado) {
    if (!detalle || !nodo) return;
    var prev = nombresDe(nodo.previos) || "ninguno";
    var sig = nombresDe(nodo.siguientes) || "ninguna";
    var meta =
      "código " +
      nodo.id +
      " · semestre " +
      nodo.semestre +
      (nodo.creditos == null ? "" : " · " + nodo.creditos + " cr") +
      (fijado ? " · fijada" : "");
    detalle.innerHTML =
      '<div class="dato titulo-materia"><strong>' +
      nodo.nombre +
      "</strong> · " +
      meta +
      "</div>" +
      '<div class="dato"><span class="etiqueta">Aprobación</span>' +
      '<span class="valor">' +
      fmt(nodo.tasa, 3) +
      "</span></div>" +
      '<div class="dato"><span class="etiqueta">Bloqueo</span>' +
      '<span class="valor">' +
      fmt(nodo.bloqueo, 0) +
      "</span></div>" +
      '<div class="dato"><span class="etiqueta">Criticidad</span>' +
      '<span class="valor">' +
      fmt(nodo.complejidad, 0) +
      "</span></div>" +
      '<div class="dato"><span class="etiqueta">Prerrequisitos</span>' +
      '<span class="valor">' +
      prev +
      "</span></div>" +
      '<div class="dato"><span class="etiqueta">Habilita</span>' +
      '<span class="valor">' +
      sig +
      "</span></div>";
  }

  function mostrarTooltip(nodo, evento) {
    if (!tooltip || !viewport) return;
    tooltip.innerHTML = "<strong>" + nodo.nombre + "</strong>";
    tooltip.classList.add("visible");
    var rect = viewport.getBoundingClientRect();
    var x = evento.clientX - rect.left + 12;
    var y = evento.clientY - rect.top + 12;
    if (x + 160 > rect.width) x = evento.clientX - rect.left - 140;
    if (y + 40 > rect.height) y = evento.clientY - rect.top - 36;
    tooltip.style.left = Math.max(8, x) + "px";
    tooltip.style.top = Math.max(8, y) + "px";
  }

  function limpiarHover() {
    if (seleccionId != null && porId[seleccionId]) {
      resaltarVecinos(porId[seleccionId]);
      pintarDetalle(porId[seleccionId], true);
    } else {
      limpiarResaltado();
      if (detalle) detalle.innerHTML = TEXTO_HINT;
    }
    ocultarTooltip();
  }

  function seleccionar(id) {
    var nodo = porId[id];
    if (!nodo) return;
    if (seleccionId === id) {
      seleccionId = null;
      limpiarResaltado();
      if (detalle) detalle.innerHTML = TEXTO_HINT;
      return;
    }
    seleccionId = id;
    resaltarVecinos(nodo);
    pintarDetalle(nodo, true);
  }

  function limpiarTodo() {
    seleccionId = null;
    limpiarResaltado();
    ocultarTooltip();
    if (detalle) detalle.innerHTML = TEXTO_HINT;
  }

  grupos
    .on("mouseenter", function (evento, d) {
      resaltarVecinos(d);
      pintarDetalle(d, false);
      mostrarTooltip(d, evento);
    })
    .on("mousemove", function (evento, d) {
      mostrarTooltip(d, evento);
    })
    .on("mouseleave", function () {
      limpiarHover();
    })
    .on("click", function (evento, d) {
      evento.stopPropagation();
      seleccionar(d.id);
    });

  var vb = { x: 0, y: 0, w: W, h: H };
  function aplicarVista() {
    svg.attr("viewBox", vb.x + " " + vb.y + " " + vb.w + " " + vb.h);
    var pct = raiz.querySelector("#z-pct");
    if (pct) pct.textContent = Math.round((100 * W) / vb.w) + "%";
  }
  function encajar() {
    vb = { x: 0, y: 0, w: W, h: H };
    aplicarVista();
  }
  function zoomEn(factor, cx, cy) {
    var nw = Math.min(W * 3, Math.max(W * 0.12, vb.w * factor));
    var nh = nw * (H / W);
    var px = (cx - vb.x) / vb.w;
    var py = (cy - vb.y) / vb.h;
    vb.w = nw;
    vb.h = nh;
    vb.x = cx - px * vb.w;
    vb.y = cy - py * vb.h;
    aplicarVista();
  }

  if (embebido && viewport) {
    var zIn = raiz.querySelector("#z-in");
    var zOut = raiz.querySelector("#z-out");
    var zFit = raiz.querySelector("#z-fit");
    if (zIn)
      zIn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        zoomEn(0.8, vb.x + vb.w / 2, vb.y + vb.h / 2);
      });
    if (zOut)
      zOut.addEventListener("click", function (ev) {
        ev.stopPropagation();
        zoomEn(1.25, vb.x + vb.w / 2, vb.y + vb.h / 2);
      });
    if (zFit)
      zFit.addEventListener("click", function (ev) {
        ev.stopPropagation();
        encajar();
      });

    var arrastrando = false;
    var moved = false;
    var lastX = 0;
    var lastY = 0;

    viewport.addEventListener(
      "wheel",
      function (ev) {
        ev.preventDefault();
        var rect = svg.node().getBoundingClientRect();
        var mx = vb.x + ((ev.clientX - rect.left) / rect.width) * vb.w;
        var my = vb.y + ((ev.clientY - rect.top) / rect.height) * vb.h;
        zoomEn(ev.deltaY < 0 ? 0.85 : 1.18, mx, my);
      },
      { passive: false }
    );

    viewport.addEventListener("pointerdown", function (ev) {
      if (ev.button !== 0) return;
      if (ev.target.closest && ev.target.closest(".nodo")) {
        moved = false;
        return;
      }
      arrastrando = true;
      moved = false;
      lastX = ev.clientX;
      lastY = ev.clientY;
      viewport.classList.add("arrastrando");
      viewport.setPointerCapture(ev.pointerId);
    });
    viewport.addEventListener("pointermove", function (ev) {
      if (!arrastrando) return;
      var rect = svg.node().getBoundingClientRect();
      var dx = ((ev.clientX - lastX) / rect.width) * vb.w;
      var dy = ((ev.clientY - lastY) / rect.height) * vb.h;
      if (Math.abs(ev.clientX - lastX) + Math.abs(ev.clientY - lastY) > 4) moved = true;
      vb.x -= dx;
      vb.y -= dy;
      lastX = ev.clientX;
      lastY = ev.clientY;
      aplicarVista();
    });
    viewport.addEventListener("pointerup", function (ev) {
      var hubo = moved;
      arrastrando = false;
      viewport.classList.remove("arrastrando");
      if (!hubo && !(ev.target.closest && ev.target.closest(".nodo"))) {
        limpiarTodo();
      }
      setTimeout(function () {
        moved = false;
      }, 40);
    });
    encajar();
  } else {
    svg.on("click", function (evento) {
      if (!evento.target.closest || !evento.target.closest(".nodo")) limpiarTodo();
    });
  }

  // Silenciar aviso de variable oscuro no usada (reservada para estilos futuros).
  void oscuro;
})();
