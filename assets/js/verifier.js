// Client-side exact verifier — a port of build/vendor/verify_exact.py.
// All coordinates are decimal literals,
// so scaling by 10^K (K = max decimal places) turns everything into BigInt
// integer arithmetic: cross products, hull, shoelace and the tie test are
// exact. The only rounding is the final 30-significant-digit display.
"use strict";

const TIE_NUM = 1000000001n, TIE_DEN = 1000000000n; // 1 + 1e-9, exact

function parsePoints(text) {
  const pts = [];
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line || line.startsWith("#")) continue;
    const parts = line.split(/[\s,;]+/).filter(Boolean);
    if (parts.length !== 2) throw new Error(`line ${i + 1}: expected 2 numbers, got ${parts.length}`);
    pts.push(parts.map(parseDec));
  }
  return pts;
}

function parseDec(s) {
  const m = /^([+-]?)(\d*)(?:\.(\d*))?$/.exec(s);
  if (!m || (!m[2] && !m[3])) throw new Error(`cannot parse number: ${s}`);
  const frac = m[3] || "";
  return { int: BigInt((m[1] === "-" ? "-" : "") + (m[2] || "0") + frac), dec: frac.length };
}

function scaleAll(pts, extra) {
  // Common scale 10^K across all coordinates (and any extra rationals).
  let K = 0;
  for (const p of pts) for (const c of p) K = Math.max(K, c.dec);
  for (const e of extra || []) K = Math.max(K, e.dec);
  const pow = (k) => 10n ** BigInt(k);
  return {
    K,
    pts: pts.map(p => p.map(c => c.int * pow(K - c.dec))),
    scale: (c) => c.int * pow(K - c.dec),
  };
}

const abs = (x) => (x < 0n ? -x : x);
function gcd(a, b) { a = abs(a); b = abs(b); while (b) { [a, b] = [b, a % b]; } return a || 1n; }

function cross(o, a, b) {
  return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
}

function convexHull(pts) {
  const s = [...new Set(pts.map(p => p.join(",")))].map(k => k.split(",").map(BigInt));
  s.sort((p, q) => (p[0] === q[0] ? (p[1] < q[1] ? -1 : p[1] > q[1] ? 1 : 0) : p[0] < q[0] ? -1 : 1));
  if (s.length <= 2) return s;
  const half = (arr) => {
    const h = [];
    for (const p of arr) {
      while (h.length >= 2 && cross(h[h.length - 2], h[h.length - 1], p) <= 0n) h.pop();
      h.push(p);
    }
    h.pop();
    return h;
  };
  const hull = half(s).concat(half([...s].reverse()));
  return hull.length < 3 ? s.slice(0, 2) : hull;
}

function shoelace2(vertices) { // twice the area, signed magnitude
  let t = 0n;
  const n = vertices.length;
  for (let i = 0; i < n; i++) {
    const [x1, y1] = vertices[i], [x2, y2] = vertices[(i + 1) % n];
    t += x1 * y2 - x2 * y1;
  }
  return abs(t);
}

// value as fraction num/den in lowest terms, plus 30-significant-digit decimal
function finish(num, den) {
  const g = gcd(num, den);
  num /= g; den /= g;
  return { fraction: `${num}/${den}`, decimal: sigDigits(num, den, 30) };
}

function sigDigits(num, den, sig) {
  if (num === 0n) return "0";
  let shift = 0;
  let n = abs(num);
  // position of first significant digit: find e with n*10^e >= den*10^(sig-1)
  while (n < den) { n *= 10n; shift++; }
  while (n >= den * 10n) { den *= 10n; shift--; }
  // now 1 <= n/den < 10; produce `sig` digits with half-even rounding
  let digits = "";
  let rem = n;
  for (let i = 0; i < sig + 1; i++) {
    const d = rem / den;
    digits += d.toString();
    rem = (rem - d * den) * 10n;
  }
  // round the sig+1-digit string to sig digits, half-even on the last digit
  let head = BigInt(digits.slice(0, sig));
  const nextDigit = BigInt(digits[sig]);
  if (nextDigit > 5n || (nextDigit === 5n && (rem !== 0n || head % 2n === 1n))) head += 1n;
  let hs = head.toString();
  if (hs.length > sig) { hs = hs.slice(0, sig); shift--; }
  // place the decimal point: value = 0.d1d2... * 10^(1-shift)
  const exp = 1 - shift;
  let out;
  if (exp > 0 && exp <= sig) {
    out = hs.slice(0, exp) + "." + hs.slice(exp);
  } else if (exp <= 0 && exp > -6) {
    out = "0." + "0".repeat(-exp) + hs;
  } else {
    out = hs[0] + "." + hs.slice(1) + "E" + (exp - 1);
  }
  out = out.replace(/\.?0+$/, "");
  return (num < 0n ? "-" : "") + out;
}

// Equilateral frame apex height √3/2 to 30 decimals (rational stand-in; the
// induced relative error ~1e-30 is far below any displayed digit).
const EQ_S = "0.866025403784438646763723170753";

function verify(variantSel, rawPts) {
  const isEq = variantSel === "triangle-eq";
  const variant = isEq ? "triangle" : variantSel;
  const extra = isEq ? [parseDec(EQ_S)] : [];
  const { K, pts, scale } = scaleAll(rawPts, extra);
  const U = 10n ** BigInt(K); // the scaled "1"
  const n = pts.length;
  if (n < 3) throw new Error(`need at least 3 points, got ${n}`);
  if (n > 80) throw new Error(`n = ${n} is above this page's cap of 80`);

  // Feasibility. maxViolation tracks the worst overshoot as a relative
  // magnitude, so the UI can distinguish "outside by 1e-16" (a boundary
  // point rounded outward in published data) from genuinely infeasible.
  const violations = [];
  let maxViolation = 0;
  const overshoot = (c, D) => { maxViolation = Math.max(maxViolation, Number(c) / Number(D)); };
  if (variant === "square") {
    pts.forEach(([x, y], i) => {
      if (x < 0n || x > U) { violations.push(`point ${i}: x outside [0, 1]`); overshoot(x < 0n ? -x : x - U, U); }
      if (y < 0n || y > U) { violations.push(`point ${i}: y outside [0, 1]`); overshoot(y < 0n ? -y : y - U, U); }
    });
  } else if (variant === "triangle") {
    let V;
    if (isEq) {
      const s = scale(parseDec(EQ_S));
      V = [[0n, 0n], [U, 0n], [U / 2n, s]]; // U is even iff K>=1; enforce below
      if (U % 2n !== 0n) V[2][0] = U / 2n; // K=0 (integer coords) — degenerate anyway
    } else {
      V = [[0n, 0n], [U, 0n], [0n, U]];
    }
    const D = cross(V[0], V[1], V[2]); // > 0 for both frames
    // The right frame is exact. In the equilateral frame the apex height
    // √3/2 is necessarily a rational stand-in (30 digits), which tilts the
    // slanted edges by ~1e-30 — so accept boundary points to a documented
    // relative tolerance of 1e-24, far below coordinate precision.
    const tol = isEq ? D / 10n ** 24n : 0n;
    pts.forEach((p, i) => {
      const c0 = cross(V[0], V[1], p), c1 = cross(V[1], V[2], p), c2 = cross(V[2], V[0], p);
      const worst = [c0, c1, c2].reduce((a, b) => (b < a ? b : a));
      if (worst < -tol) { violations.push(`point ${i}: outside the triangle`); overshoot(-worst, D); }
    });
  }
  const feasible = violations.length === 0;

  // Minimum over all triples (twice-area, scaled by 10^2K)
  let minC = null, minTriple = null, count = 0;
  const crosses = [];
  for (let i = 0; i < n - 2; i++)
    for (let j = i + 1; j < n - 1; j++)
      for (let k = j + 1; k < n; k++) {
        const c = abs(cross(pts[i], pts[j], pts[k]));
        crosses.push(c);
        count++;
        if (minC === null || c < minC) { minC = c; minTriple = [i, j, k]; }
      }
  let ties = 0;
  for (const c of crosses) if (c * TIE_DEN <= minC * TIE_NUM) ties++;

  // Normalize. minC = 2 * area * 10^2K.
  let value, hullCount = null;
  const U2 = U * U;
  if (variant === "square") {
    value = finish(minC, 2n * U2);
  } else if (variant === "triangle") {
    if (isEq) {
      const s = scale(parseDec(EQ_S));
      const D = cross([0n, 0n], [U, 0n], [U / 2n, s]); // = U*s
      value = finish(minC, D);
    } else {
      value = finish(minC, U2);
    }
  } else {
    const hull = convexHull(pts);
    hullCount = hull.length;
    const h2 = shoelace2(hull);
    value = h2 === 0n ? { fraction: "0/1", decimal: "0" } : finish(minC, h2);
  }

  return {
    n,
    triples_checked: count,
    value: value.decimal,
    value_fraction: value.fraction,
    min_triple: minTriple,
    num_min_ties: ties,
    feasible,
    violations,
    violation_magnitude: feasible ? null : maxViolation,
    hull_vertex_count: hullCount,
  };
}

// ---------------------------------------------------------------------------
// Page wiring (skipped when loaded under node --test)
if (typeof document !== "undefined" && document.getElementById("verify")) {
  const $ = (id) => document.getElementById(id);
  let siteValues = null;

  $("load-example").addEventListener("click", () => {
    $("variant").value = "triangle";
    $("input").value = [
      "# Heilbronn triangle n=5, A = 3 - 2*sqrt(2)  (Royce Peng)",
      "0.292893218813452\t0.000000000000000",
      "1.000000000000000\t0.000000000000000",
      "0.000000000000000\t0.292893218813452",
      "0.000000000000000\t1.000000000000000",
      "0.292893218813452\t0.292893218813452",
    ].join("\n");
  });

  $("verify").addEventListener("click", async () => {
    const verdict = $("verdict"), out = $("output");
    verdict.hidden = out.hidden = false;
    let res;
    try {
      res = verify($("variant").value, parsePoints($("input").value));
    } catch (err) {
      verdict.className = "verdict verdict-bad";
      verdict.textContent = String(err.message || err);
      out.hidden = true;
      return;
    }
    out.textContent = JSON.stringify(res, null, 1);

    let cls = res.feasible ? "verdict-ok" : "verdict-bad";
    let text = res.feasible
      ? `Feasible. Exact value ${res.value.slice(0, 17)}… over ${res.triples_checked} triples (${res.num_min_ties} minimal).`
      : `Infeasible: ${res.violations[0]}${res.violations.length > 1 ? ` (+${res.violations.length - 1} more)` : ""}.`;
    if (!res.feasible && res.violation_magnitude < 1e-12) {
      cls = "verdict-record";
      text = `Boundary-precision violation only (max ${res.violation_magnitude.toExponential(1)}): ` +
             `boundary points rounded outward, common in published float data. ` +
             `Exact value of these literals: ${res.value.slice(0, 17)}… ` +
             `(${res.num_min_ties} minimal triangles).`;
    }

    if (res.feasible || res.violation_magnitude < 1e-12) {
      try {
        if (!siteValues) siteValues = await (await fetch(window.HEILBRONN_VALUES_URL)).json();
        const vkey = $("variant").value.replace("-eq", "");
        const rec = siteValues[vkey] && siteValues[vkey][String(res.n)];
        if (rec && rec.decimal) {
          const mine = parseFloat(res.value), best = parseFloat(rec.decimal);
          const relDiff = (mine - best) / best;
          if (relDiff > 1e-12) {
            cls = "verdict-record";
            text += ` That beats this site's best known value ${rec.decimal.slice(0, 12)}… — please get in touch!`;
          } else if (relDiff > -1e-9) {
            text += ` Matches this site's best known value.`;
          } else {
            text += ` This site's best known value is ${rec.decimal.slice(0, 12)}… (${(-relDiff * 100).toPrecision(2)}% higher).`;
          }
        }
      } catch { /* comparison is best-effort */ }
    }
    verdict.className = "verdict " + cls;
    verdict.textContent = text;
  });
}

// Exported for node --test
if (typeof module !== "undefined") module.exports = { verify, parsePoints };
