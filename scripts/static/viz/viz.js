/*
 * 每日一理 · 交互可视化框架
 * ---------------------------------------------------------------------------
 * 干什么:扫描页面里「每日一理」板块内的可视化容器,按声明的类型渲染成
 *         可交互的数学图形(基于自托管的 JSXGraph)。
 * 角色  :站点前端脚本,只在含 viz 的期次页面加载(见 base.html 的 foot 块)。
 * 输入  :DOM 里的 <div class="mathviz" data-viz='{"type":"cobweb","params":{...}}'>。
 * 输出  :在该容器内画出对应的 JSXGraph 画板,支持拖拽等交互。
 *
 * 扩展  :往 COMPONENTS 里加一个 `类型名: function(elId, params)` 即可新增组件;
 *         冷门定理走「custom」通道(模板直接内联 html+script,不经过这里)。
 */
(function () {
  "use strict";

  /* 从站点 CSS 变量取主题色,取不到时回落到钴蓝十六进制(保证断样式也能看)。 */
  function themeColor(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }

  var ACCENT = themeColor("--color-accent", "#3457d5"); // 主强调色(y=f(x) 曲线、起点)
  var COBWEB = "#c0392b"; // 迭代/下降路径(暖红,和主色区分)
  var GUIDE = "#9aa4b2"; // 辅助线(灰)

  /* 把表达式串编译成 JS 函数 f(x):解构 Math 让 cos/sin/exp 等可直接写。
   * 表达式来自本仓库(组件参数),非用户输入,new Function 可信。 */
  function makeFn(expr) {
    return new Function(
      "x",
      "var {sin,cos,tan,asin,acos,atan,exp,log,sqrt,cbrt,abs,pow,sign," +
        "sinh,cosh,tanh,floor,ceil,round,min,max,PI,E}=Math;" +
        "return (" + expr + ");"
    );
  }

  /* 同 makeFn,但支持双变量 g(x,y),给向量场 / 相图用。 */
  function makeFn2(expr) {
    return new Function(
      "x", "y",
      "var {sin,cos,tan,asin,acos,atan,exp,log,sqrt,cbrt,abs,pow,sign," +
        "sinh,cosh,tanh,floor,ceil,round,min,max,PI,E,hypot,atan2}=Math;" +
        "return (" + expr + ");"
    );
  }

  /* 在 [a,b] 上采样估计 f 的取值范围,用来自动定纵向视窗。 */
  function sampleRange(f, a, b, n) {
    var lo = Infinity, hi = -Infinity;
    for (var i = 0; i <= n; i++) {
      var y = f(a + ((b - a) * i) / n);
      if (isFinite(y)) { if (y < lo) lo = y; if (y > hi) hi = y; }
    }
    if (!isFinite(lo) || !isFinite(hi) || lo === hi) { lo = -1; hi = 1; }
    return [lo, hi];
  }

  /* ---- 组件:迭代蛛网图(cobweb / fixed-point iteration) -----------------
   * 画 y=f(x) 与 y=x,给一个可沿 x 轴拖动的起点 x₀,实时画出
   * x₀ → f(x₀) → f²(x₀) → … 的蛛网路径,直观看它收敛到不动点。
   * params: { fn:"cos(x)", x0:2.5, xmin:-0.2, xmax:3.3, iterations:14 }
   */
  function cobweb(elId, p) {
    p = Object.assign(
      { fn: "cos(x)", x0: 2.5, xmin: -0.2, xmax: 3.3, iterations: 14 },
      p || {}
    );

    var f = makeFn(p.fn);

    var pad = 0.6; // 纵向留白,别让曲线顶到边框
    var board = JXG.JSXGraph.initBoard(elId, {
      // boundingbox = [xmin, ymax, xmax, ymin]
      boundingbox: [p.xmin, p.xmax + pad, p.xmax, p.xmin - pad],
      keepaspectratio: false,
      axis: true,
      showCopyright: false,
      showNavigation: false,
      pan: { enabled: false },
      zoom: { enabled: false },
      defaultAxes: {
        x: { ticks: { majorHeight: 6, drawZero: true } },
        y: { ticks: { majorHeight: 6 } },
      },
    });

    // y = f(x) 曲线
    board.create(
      "functiongraph",
      [function (x) { return f(x); }, p.xmin, p.xmax],
      { strokeColor: ACCENT, strokeWidth: 2.5, highlight: false }
    );
    // 参考线 y = x(蛛网在它和曲线之间来回弹)
    board.create("line", [[0, 0], [1, 1]], {
      strokeColor: GUIDE, dash: 2, strokeWidth: 1.5,
      straightFirst: true, straightLast: true,
      fixed: true, highlight: false,
    });

    // 起点:约束在一条隐藏的 y=0 直线上,只能左右拖
    var axisLine = board.create("line", [[0, 0], [1, 0]], { visible: false });
    var start = board.create("glider", [p.x0, 0, axisLine], {
      name: "x₀", size: 5,
      fillColor: ACCENT, strokeColor: ACCENT,
      label: { offset: [8, -14], fontSize: 14 },
    });
    // 迭代路径(一条折线)+ 收敛点标记 x*
    var path = board.create("curve", [[], []], {
      strokeColor: COBWEB, strokeWidth: 1.6, highlight: false,
    });
    var star = board.create("point", [0, 0], {
      name: "x*", size: 3, strokeColor: COBWEB, fillColor: "#fff",
      label: { offset: [8, 10], fontSize: 13, strokeColor: COBWEB },
      fixed: true, highlight: false,
    });

    function redraw() {
      var x = start.X();
      var xs = [x], ys = [0]; // 从 (x₀, 0) 起步
      for (var i = 0; i < p.iterations; i++) {
        var y = f(x);
        xs.push(x); ys.push(y); // 竖线:上到曲线 (x, f(x))
        xs.push(y); ys.push(y); // 横线:平移到 y=x 上 (f(x), f(x))
        x = y;
      }
      path.dataX = xs;
      path.dataY = ys;
      star.moveTo([x, x]); // 最后落点 ≈ 不动点
      board.update();
    }

    start.on("drag", redraw);
    redraw();
    return board;
  }

  /* ---- 组件:傅里叶级数逼近(fourier) ------------------------------------
   * 画一个周期波(方波/锯齿/三角)及其前 N 项傅里叶级数部分和,拖滑块加项数,
   * 直观看级数如何收敛、以及跳变处的吉布斯过冲。
   * params: { wave:"square"|"sawtooth"|"triangle", terms:5, maxTerms:30 }
   */
  function fourier(elId, p) {
    p = Object.assign({ wave: "square", terms: 5, maxTerms: 30 }, p || {});

    var board = JXG.JSXGraph.initBoard(elId, {
      boundingbox: [-Math.PI * 1.15, 1.7, Math.PI * 1.15, -1.7],
      keepaspectratio: false,
      axis: true,
      showCopyright: false,
      showNavigation: false,
      pan: { enabled: false },
      zoom: { enabled: false },
    });

    // 各波形的部分和:传入 x 与项数 n,返回前 n 项之和
    function partial(x, n) {
      var s = 0, k;
      if (p.wave === "sawtooth") {
        for (k = 1; k <= n; k++) s += (k % 2 ? 1 : -1) * Math.sin(k * x) / k;
        return (2 / Math.PI) * s;
      }
      if (p.wave === "triangle") {
        for (k = 1; k <= n; k += 2) {
          s += (((k - 1) / 2) % 2 ? -1 : 1) * Math.sin(k * x) / (k * k);
        }
        return (8 / (Math.PI * Math.PI)) * s;
      }
      // square(默认)
      for (k = 1; k <= n; k += 2) s += Math.sin(k * x) / k;
      return (4 / Math.PI) * s;
    }
    // 理想波形(参考,虚线):用大项数近似,避免手写分段
    function ideal(x) { return partial(x, 199); }

    // 项数滑块 N
    var N = board.create(
      "slider",
      [[-Math.PI * 0.95, 1.45], [Math.PI * 0.15, 1.45], [1, p.terms, p.maxTerms]],
      { name: "项数 N", snapWidth: 1, precision: 0, fillColor: ACCENT, strokeColor: ACCENT }
    );

    board.create("functiongraph", [ideal], {
      strokeColor: GUIDE, strokeWidth: 1.4, dash: 2, highlight: false,
    });
    board.create(
      "functiongraph",
      [function (x) { return partial(x, Math.round(N.Value())); }],
      { strokeColor: ACCENT, strokeWidth: 2.5, highlight: false }
    );
    return board;
  }

  /* ---- 组件:梯度下降(gradient) ----------------------------------------
   * 在一维曲线 y=f(x) 上,从可拖动的起点按 xₙ₊₁=xₙ-η·f'(xₙ) 一步步下山,
   * 红色折线是下降轨迹。拖起点或调「学习率 η」滑块:η 太大就会震荡甚至发散。
   * 导数用数值差分,任意表达式都能跑;纵向视窗自动适配。
   * params: { fn:"0.5*x*x - cos(3*x)", x0:2.4, lr:0.1, maxLr:1.2, xmin:-3, xmax:3, steps:24 }
   */
  function gradient(elId, p) {
    p = Object.assign(
      { fn: "0.5*x*x - cos(3*x)", x0: 2.4, lr: 0.1, maxLr: 1.2, xmin: -3, xmax: 3, steps: 24 },
      p || {}
    );
    var f = makeFn(p.fn);
    var df = function (x) { var h = 1e-4; return (f(x + h) - f(x - h)) / (2 * h); };

    var r = sampleRange(f, p.xmin, p.xmax, 200);
    var pad = (r[1] - r[0]) * 0.15 || 0.5;
    var board = JXG.JSXGraph.initBoard(elId, {
      boundingbox: [p.xmin, r[1] + pad, p.xmax, r[0] - pad],
      keepaspectratio: false,
      axis: true,
      showCopyright: false,
      showNavigation: false,
      pan: { enabled: false },
      zoom: { enabled: false },
    });

    board.create("functiongraph", [f, p.xmin, p.xmax], {
      strokeColor: ACCENT, strokeWidth: 2.5, highlight: false,
    });
    var axisLine = board.create("line", [[0, 0], [1, 0]], { visible: false });
    var start = board.create("glider", [p.x0, 0, axisLine], {
      name: "x₀", size: 5, fillColor: ACCENT, strokeColor: ACCENT,
      label: { offset: [8, -14], fontSize: 14 },
    });
    var lr = board.create(
      "slider",
      [[p.xmin + (p.xmax - p.xmin) * 0.05, r[1] + pad * 0.4],
       [p.xmin + (p.xmax - p.xmin) * 0.45, r[1] + pad * 0.4],
       [0.01, p.lr, p.maxLr]],
      { name: "学习率 η", precision: 2, fillColor: ACCENT, strokeColor: ACCENT }
    );
    var path = board.create("curve", [[], []], {
      strokeColor: COBWEB, strokeWidth: 1.6, highlight: false,
    });
    var cur = board.create("point", [0, 0], {
      name: "", size: 3, fillColor: COBWEB, strokeColor: COBWEB, fixed: true, highlight: false,
    });

    function redraw() {
      var x = start.X(), eta = lr.Value();
      var xs = [x], ys = [f(x)];
      for (var i = 0; i < p.steps; i++) {
        x = x - eta * df(x);
        if (!isFinite(x)) break;
        xs.push(x); ys.push(f(x));
      }
      path.dataX = xs; path.dataY = ys;
      cur.moveTo([xs[xs.length - 1], ys[ys.length - 1]]);
      board.update();
    }
    start.on("drag", redraw);
    lr.on("drag", redraw);
    board.on("up", redraw); // 拖滑块释放后兜底重算
    redraw();
    return board;
  }

  /* ---- 组件:向量场 / 相图(vectorfield) --------------------------------
   * 画平面上的向量场 (ẋ,ẏ)=(fx,fy),并从一个可拖动的种子点用 RK4 积分出流线
   * (前向实线、后向虚线),直观看系统的相轨迹、平衡点与旋涡。
   * params: { fx:"y", fy:"-sin(x)-0.3*y", xmin,xmax,ymin,ymax, density, seedX, seedY, steps, dt }
   */
  function vectorfield(elId, p) {
    p = Object.assign(
      { fx: "y", fy: "-sin(x)-0.3*y", xmin: -3.6, xmax: 3.6, ymin: -3, ymax: 3,
        density: 15, seedX: -2.5, seedY: 2.5, steps: 700, dt: 0.02 },
      p || {}
    );
    var Fx = makeFn2(p.fx), Fy = makeFn2(p.fy);

    var board = JXG.JSXGraph.initBoard(elId, {
      boundingbox: [p.xmin, p.ymax, p.xmax, p.ymin],
      keepaspectratio: false,
      axis: true,
      showCopyright: false,
      showNavigation: false,
      pan: { enabled: false },
      zoom: { enabled: false },
    });

    board.create(
      "vectorfield",
      [[function (x, y) { return Fx(x, y); }, function (x, y) { return Fy(x, y); }],
       [p.density, p.xmin, p.xmax], [p.density, p.ymin, p.ymax]],
      { strokeColor: GUIDE, strokeWidth: 1, opacity: 0.7, scale: true }
    );

    var seed = board.create("point", [p.seedX, p.seedY], {
      name: "拖我", size: 5, fillColor: ACCENT, strokeColor: ACCENT,
      label: { offset: [8, -12], fontSize: 12 },
    });
    var fwd = board.create("curve", [[], []], { strokeColor: COBWEB, strokeWidth: 2, highlight: false });
    var bwd = board.create("curve", [[], []], { strokeColor: COBWEB, strokeWidth: 1.4, dash: 2, highlight: false });

    // 从种子点用 RK4 积分一条流线,sign=+1 前向、-1 后向;越出视窗即停。
    function streamline(sign) {
      var h = sign * p.dt, x = seed.X(), y = seed.Y();
      var xs = [x], ys = [y];
      for (var i = 0; i < p.steps; i++) {
        var k1x = Fx(x, y), k1y = Fy(x, y);
        var k2x = Fx(x + h / 2 * k1x, y + h / 2 * k1y), k2y = Fy(x + h / 2 * k1x, y + h / 2 * k1y);
        var k3x = Fx(x + h / 2 * k2x, y + h / 2 * k2y), k3y = Fy(x + h / 2 * k2x, y + h / 2 * k2y);
        var k4x = Fx(x + h * k3x, y + h * k3y), k4y = Fy(x + h * k3x, y + h * k3y);
        x += h / 6 * (k1x + 2 * k2x + 2 * k3x + k4x);
        y += h / 6 * (k1y + 2 * k2y + 2 * k3y + k4y);
        if (!isFinite(x) || !isFinite(y)) break;
        if (x < p.xmin - 1 || x > p.xmax + 1 || y < p.ymin - 1 || y > p.ymax + 1) break;
        xs.push(x); ys.push(y);
      }
      return [xs, ys];
    }
    function redraw() {
      var a = streamline(1), b = streamline(-1);
      fwd.dataX = a[0]; fwd.dataY = a[1];
      bwd.dataX = b[0]; bwd.dataY = b[1];
      board.update();
    }
    seed.on("drag", redraw);
    redraw();
    return board;
  }

  var COMPONENTS = { cobweb: cobweb, fourier: fourier, gradient: gradient, vectorfield: vectorfield };

  function boot() {
    var nodes = document.querySelectorAll(".mathviz[data-viz]");
    Array.prototype.forEach.call(nodes, function (el) {
      var spec;
      try {
        spec = JSON.parse(el.getAttribute("data-viz"));
      } catch (e) {
        console.error("[viz] data-viz 解析失败", e);
        return;
      }
      var make = COMPONENTS[spec.type];
      if (!make) {
        el.innerHTML = '<p class="mathviz__err">未知可视化类型:' + spec.type + "</p>";
        return;
      }
      if (!el.id) el.id = "mv-" + Math.random().toString(36).slice(2, 9);
      try {
        make(el.id, spec.params || {});
      } catch (e) {
        console.error("[viz] 渲染失败", spec.type, e);
        el.innerHTML = '<p class="mathviz__err">可视化渲染失败,已回落到文字说明。</p>';
      }
    });
  }

  if (document.readyState !== "loading") boot();
  else document.addEventListener("DOMContentLoaded", boot);
})();
