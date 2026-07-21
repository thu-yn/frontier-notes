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
  var COBWEB = "#c0392b"; // 蛛网迭代路径(暖红,和主色区分)
  var GUIDE = "#9aa4b2"; // 辅助线 y=x(灰)

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

    // 把表达式串编译成 JS 函数 f(x):解构 Math 让 cos/sin/exp 等可直接写。
    // 表达式来自本仓库(组件参数),非用户输入,new Function 可信。
    var f = new Function(
      "x",
      "var {sin,cos,tan,asin,acos,atan,exp,log,sqrt,cbrt,abs,pow,sign," +
        "sinh,cosh,tanh,floor,ceil,round,min,max,PI,E}=Math;" +
        "return (" + p.fn + ");"
    );

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

  var COMPONENTS = { cobweb: cobweb };

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
