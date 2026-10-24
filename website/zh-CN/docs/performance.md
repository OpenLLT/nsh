---
title: 性能
description: NSH 如何让应用保持高速（Rust 应用、原生运行时、批量跨线程、原生动画、虚拟化列表），这对你的代码意味着什么，以及如何在无界面环境和屏幕上测量。
order: 62
group: tools
---

# 性能

性能是 NSH 的第一优先级，而其中大部分由框架而非你的应用决定：运行时是原生的，每次更新只跨一次线程，动画和列表虚拟化
都无需 JS 参与，用 Rust 编写的应用则完全不运行 JS。本页介绍 NSH 遵循的规则、它们对你用 Rust 和 TSX 所写代码的意义，以及如何测量。

## 规则

### 1. JS 做得越少越好

**用 Rust 编写的应用从头到尾都是原生代码**：它的组件、状态和处理函数与 NSH 的引擎一起编译，没有任何解释器在运行
（[用 Rust 开发](./rust.md)）。这是编写应用最快的方式，也是业务逻辑繁重时应当选择的方式。

在 TSX 应用中，QuickJS 是一个解释器：体积小、启动快，但做重活时比原生代码慢得多。因此在 NSH 中，**只有你的应用代码是 JS**。响应式图
（signal、computed 值、effect）、编译后的 JSX 所调用的渲染器、布局引擎、列表虚拟化、动画以及
你导入的每个模块都是 Rust。解析、diff、布局和字符串处理都在原生侧完成。

效果是可以测量的。同一个计数器应用分别跑在 NSH 早先的 JS 运行时和原生运行时上（release 构建）：

| | 早先的 JS 运行时 | 原生运行时 |
|---|---|---|
| bundle 大小 | 14 KB JS / 19.6 KB 字节码 | 886 B JS / 1.7 KB 字节码 |
| 执行 bundle | ~390 µs | ~95 µs |
| 一次点击的 JS 耗时（中位数） | ~14 µs | ~5 µs |
| 一次点击的 commit | ~22 µs | ~15 µs |
| 滚动 1000 行列表，每个重新绑定帧的 JS 耗时 | ~150 µs | ~77 µs |

组件也是如此：用 Rust 组件编写的按钮与一个等价的 TSX 按钮对比，各 200 个：

| | Rust 按钮：JS / core | TSX 按钮：JS / core |
|---|---|---|
| 首帧（ops） | 1.32 ms / 0.77 ms (1015) | 2.32 ms / 0.70 ms (2415) |
| 更新全部 200 个标题（ops） | 0.42 ms / 0.42 ms (200) | 0.77 ms / 0.36 ms (600) |

（在 Apple silicon 上测得；第二张表基于早先的运行时。两者均出自 NSH 的性能基线。）

**对你的代码而言：** 让事件处理函数和 computed 值保持轻量。繁重的计算（解析大型数据、每次按键都对上千条数据排序）在
QuickJS 中的代价，比你在带 JIT 的 V8 或 JavaScriptCore 中习惯的要高。只做一次，用 `computed` 缓存，或者把它移出交互路径。

### 2. 批量跨线程

应用的代码（Rust 或 JS）运行在引擎线程上，从不在主线程上运行。一个轮次，例如一个事件处理函数及其引起的全部改动，会成为
**一次 commit**：运行时渲染组件、布局、diff，并生成一批原生视图操作，以**一次跳转**送达主线程。不存在每个视图一条的
bridge 消息，也没有每个 prop 一次的序列化。

**对你的代码而言：** 无需为了性能合并写入；一个处理函数里调用十次 `set` 仍然只产生一次 commit，Rust 和 TSX 都是如此。如果你希望 effect 和
computed 值一次性看到所有写入，而不是每次写入后都运行一遍，请使用 `batch`。

### 3. 细粒度更新

组件只运行**一次**，Rust 和 TSX 都一样。之后，当某个 signal 变化时，只有读取它的绑定会重新运行：一段文本、一个样式属性、
`when`（`<If>`）的一个分支、`each`（`<Each>`）的各行。不会为了找出变化而重新渲染整棵子树。

```rust tabs
use nsh_core::ui::prelude::*;

#[derive(Clone, PartialEq)]
struct Quote {
    price: f64,
    change: f64,
}

fn price(quote: Signal<Quote>) -> impl IntoElement {
    // Runs once. When the quote changes, only the text and the color update.
    text(move || format!("{:.2}", quote.with(|q| q.price))).text_color(move || {
        if quote.with(|q| q.change < 0.0) { rgb(0xcf222e) } else { rgb(0x1a7f37) }
    })
}
```

```tsx tabs
import type { Accessor } from "nsh";
import { Text } from "nsh";

type Quote = { price: number; change: number };

function Price(props: { quote: Accessor<Quote> }) {
  // Runs once. When quote() changes, only the text and the color update.
  return (
    <Text style={{ color: props.quote().change < 0 ? "#cf222e" : "#1a7f37" }}>
      {props.quote().price.toFixed(2)}
    </Text>
  );
}
```

**对你的代码而言：**

- 在使用 signal 的地方读取它（绑定内部：Rust 中的 `move ||` 闭包、TSX 中的 JSX 表达式，以及 `computed`、`effect` 内部），
  而不是在组件顶部读取，这样更新的是范围最小的绑定。
- 集合使用 `each` / `<Each>`（按 key 保留行）或[虚拟列表](./lists.md)；由整个集合重新生成的行（Rust 中的 `dynamic`、JSX 中普通的 `.map()`）
  会在每次变化时全部重新创建。
- 当多个绑定用到同一个派生值时，用 `computed` 计算它，这样每次变化只计算一次。

向一个三项列表追加第四项，`nsh test --trace` 显示的结果如下：

```rust tabs
// 22 mount items: 3 views removed, 4 created
dynamic(move || items.get().into_iter().map(|n| text(format!("row {n}"))).collect::<Vec<_>>())
// 4 mount items: 1 view created
each(move || items.get(), |n: &u32| *n, |n, _| text(move || format!("row {}", n.get())))
```

```tsx tabs
{items().map((n) => <Text>{`row ${n}`}</Text>)}                   // 22 mount items: 3 views removed, 4 created
<Each of={items()}>{(n) => <Text>{`row ${n()}`}</Text>}</Each>      // 4 mount items: 1 view created
```

参见[响应式](./reactivity.md)。

### 4. 不发送不需要的内容

core 只发送变化的部分：新视图不带默认样式，也不带空的事件掩码；未变化的样式和 frame 不会发送；文本颜色的变化不会让文本
重新布局。一次只改变一个数字的点击只发送一个文本条目。你可以在 `nsh test --trace` 的输出中看到这一点（见下文）。

### 5. 原生执行动画

由引擎线程驱动的动画（每帧写入 signal）每帧都要付出一次 commit 的代价（TSX 中还有一次 JS 调用），而且引擎线程繁忙时会卡顿。
动画值（[动画](./animation.md)：Rust 中的 `animated_value`，TSX 中的 [`nsh/animated`](../modules/nsh-animated.md)）则以原生方式运行动画：

```rust tabs
use nsh_core::ui::prelude::*;

let scroll_y = animated_value(0.0);

view()
    .bind_opacity(&scroll_y.interpolate(&[0.0, 120.0], &[1.0, 0.35]))
    .bind_translate_y(&scroll_y.interpolate(&[0.0, 120.0], &[0.0, -6.0]));
virtual_list(move || photos.with(Vec::len), move |at| photo_row(photos, at))
    .scroll_value(&scroll_y)
    .estimated_item_size(px(64.0))
    .flex_1();
```

```tsx tabs
import { List, View } from "nsh";
import { createAnimatedValue } from "nsh/animated";

const scrollY = createAnimatedValue(0);

<View
  style={{
    opacity: scrollY.interpolate({ inputRange: [0, 120], outputRange: [1, 0.35] }),
    transform: [{ translateY: scrollY.interpolate({ inputRange: [0, 120], outputRange: [0, -6] }) }],
  }}
/>;
<List each={photos()} scrollValue={scrollY} estimatedItemSize={64} style={{ flex: 1 }}>
  {(photo) => <Row photo={photo()} />}
</List>;
```

- `timing`、`spring` 和 `decay` 在平台的 UI 线程上逐帧运行，每帧不需要引擎线程做任何事。
- `scroll_value`（`scrollValue`）在同一帧内把滚动偏移写入动画值；拖拽手势（`pan={{ x, y }}`）让拖动直接移动视图。你的代码只在
  结束时得到通知（动画完成，拖拽结束时拿到速度）。
- `Animated.sequence` / `parallel` / `stagger` / `loop` 作为一棵原生树运行：每一步在上一步结束的瞬间开始，中间没有
  等待 JS 的间隙。
- `LayoutAnimation.configureNext` 以原生方式为下一次 commit 的 frame 变化、插入和删除添加动画。

### 6. 虚拟化长列表

[`List`](./lists.md) 只保留视口附近的行，复用它们的单元格，并在原生侧计算位置、多列布局、吸顶标题和可见性。没有露出新行
的滚动帧不会运行你的任何代码，也不会产生 batch；在 gallery 的照片列表中，绑定一个新行的帧只有 4 个操作和 4 个 mount item。

**对你的代码而言：**

- `estimated_item_size`（`estimatedItemSize`）要接近真实的行高。
- 把每个条目的状态放在数据里（按 id 存放），而不是放在行内创建的 signal 中：单元格会被复用给其他条目，复用时
  行的位置（`at.index()`；TSX 中的 `item()` / `index()`）会变化。
- 让行保持轻量：行在每次复用时绑定一次，所以它的代码是在用户滚动时运行的。
- 对跟随滚动位置的效果，使用 `scroll_value`（`scrollValue`）而不是 `on_scroll`（`onScroll`）。滚动监听每个引擎轮次最多收到一个事件，
  但每个事件仍然是一次对你代码的调用（TSX 中是对 JS 的调用）。

## 测量

### 无界面运行：`--trace`

在 Rust 测试中，`EngineConfig::trace` 记录同样的 `perf` 行，`Headless::observe` 能看到每个批次（[测试](./testing-and-trace.md#用-trace-跟踪)）。
`nsh test --trace` 为 TSX 打印它们：

```sh
echo 'await app.press("Add")' | nsh test App.tsx --trace                 # first frame + a press
echo 'await app.scroll("id:feed", 3000)' | nsh test App.tsx --trace       # scrolling, 10 pt per frame
```

```text
perf commit: 56 ops, 395µs (list js 6µs), 49 mount items, 21 nodes
perf first frame: eval 271µs, total 1235µs
perf event js: 88µs
perf commit: 10 ops, 151µs (list js 2µs), 8 mount items, 27 nodes
```

需要关注的指标：

- **ops**（你的 JS 排入队列的操作）和 **mount items**（原生视图操作）：这两者是确定性的。如果一次本应只改变一个标签的
  点击产生了 40 个条目，说明有地方在重新创建本应更新的视图。
- **event js**：一个处理函数及其触发内容的 JS 开销。
- **commit**：core 渲染组件、布局和 diff 的开销。
- **list js**：该次 commit 中绑定列表行所花费的 JS 时间。

完整指南：[测试](./testing-and-trace.md)。

### 在设备上：`--trace`

```sh
nsh run App.tsx --trace
nsh run App.tsx --target android --trace --release
```

会在 TSX 应用的真实宿主上输出同样的 commit 日志行，使用的是平台自己的文本引擎。在嵌入式应用中，`NshAppView(trace: true)` 和
`new NshView(context, true)` 的作用相同。

### 在屏幕上：`--fps`

```sh
nsh run App.tsx --target macos --fps --release
```

（Rust 应用在 `run_app` 中用 `AppOptions { fps: true, .. }`）会在运行中的应用上方显示帧率、每帧和每次 commit 的开销，以及 CPU、GPU 和内存（[macOS：性能监视器](./macos.md#性能监视器)）。在 Linux 上，`--target linux --fps` 每秒输出一行同样的读数，并给出一帧中每个阶段的耗时；
`nsh test --target linux --fps -v` 可以在测试驱动应用时采集这些读数。

> [!TIP]
> 单次测量主要受 CPU 时钟状态影响：刚刚休眠过的线程会在一段时间内运行得更慢。请在同一台机器上比较多次运行的最小值，
> 计时时优先使用 release 构建。

## 参考数据

来自 NSH 自己的基线（除特别注明外均为 Apple silicon）：

| 场景 | 数据 |
|---|---|
| 计数器应用，无界面（debug） | 首帧 ~0.5–0.65 ms（58 ops / 49 mount items）；一次点击 ~0.15 ms |
| 计数器应用，Mac Catalyst（release） | 首帧 ~1.05–1.15 ms（其中约 0.7 ms 用于首次用 CoreText 布局 10 段文本）；一次点击 ~0.12 ms |
| Gallery 照片列表，无界面（debug） | 首帧 653 ops / 224 nodes，~2.7 ms |
| 滚动照片列表，Catalyst（release） | 慢速滚动时重新绑定一行 ~0.4 ms；快速甩动时一整屏约 32 行 0.9–1.6 ms |
| 滚动照片列表，Android 模拟器（arm64，release） | 重新绑定一行 ~0.3–0.4 ms（JS ~60 µs） |
| 引擎启动（release） | ~75–155 µs；全局 API（`fetch`、`URL` 等）在首次使用前没有任何开销，首次使用后 ~90 µs |
| 热重载 | 从保存文件到新版本运行 ~120 ms；应用更新 0.2–0.5 ms |

### Linux（GTK 4）

测量环境：Linux 桌面（x86_64，24 线程，NVIDIA GPU），release 构建，gallery 运行在 120 Hz 显示器上一个 1896 × 1030 的窗口里，
所有读数都由 `examples/gallery/tools/perf.py` 自动采集（`nsh test --target linux --fps`，每秒一行；CPU 指整个进程，以单核的百分比计）。
*帧 p95* 是主线程绘制一帧所用时间的第 95 百分位：低于 8.3 ms，一帧就能放进 120 Hz 的一次刷新。

一直在动的演示，Linux 后端引入 canvas 栅格缓存并调整渲染器选择之前和之后：

| 演示 | 在动的内容 | 之前：fps · 帧 p95 · CPU | 现在：fps · 帧 p95 · CPU |
|---|---|---|---|
| Stocks | 22 条原生脉动的实时走势线、每 50 ms 一次 tick 都会重绘的分时图、盘口、逐笔成交 | 75–87 · 17–21 ms · 82–85% | **117–120 · 5–6 ms · 31–32%**（1200 × 800 窗口下 29%） |
| Canvas | 仪表盘、时钟秒针和点阵，都是原生循环动画 | 118–120 · 6–11 ms · 17–23% | **120 · 2.6–4.4 ms · 5–10%** |
| Animations | 三个原生循环、弹簧、交错序列 | 66–85 · 21–25 ms · 73% | **120 · 2.0 ms · 12–13%** |

gallery 的每个页面，分别在刚打开时（idle）和测试用滚轮滚动时测量。帧率随画面变化而定：静止的页面不绘制帧，滚动时帧随滚轮事件到来而绘制：

| 页面 | fps | 帧 p95 | 超过 8.3 ms 的帧 | CPU |
|---|---|---|---|---|
| Stocks，idle | 118–120 | 4.2–4.9 ms | 0% | 28–33% |
| Stocks，滚动自选列表 | 119 | 5.8–6.8 ms | 1–2% | 32% |
| Photos，滚动 | 62 | 5.7 ms | 1% | 12% |
| Lists，滚动 | 47 | 4.7 ms | 1% | 5% |
| Scrolling，滚动 | 48 | 3.0 ms | 2% | 5% |
| Form，滚动 | 41 | 4.6 ms | 0% | 3% |
| Gestures（弹簧、脉动的圆环） | 120 | 4.4–4.5 ms | 0–1% | 10% |
| Animations | 120 | 2.0 ms | 0% | 13% |
| Canvas | 120 | 2.8–4.3 ms | 0% | 8–10% |
| Styles，滚动 | 118 | 4.0 ms | 0% | 5% |
| Tailwind（动画类工具类） | 106–108 | 0.4–3.6 ms | 0–2% | 3–11% |
| Text，滚动 | 37 | 4.7 ms | 2% | 4% |
| Text View，滚动 | 61 | 4.2 ms | 0% | 5% |
| Images（GIF 和 WebP 播放中） | 42–46 | 1.4–3.7 ms | 0% | 4% |
| Controls | 102–110 | 0.3–1.3 ms | 0% | 3–5% |
| Web and video | 72–112 | 1.2–4.6 ms | 0% | 8–9% |

启动 3 秒后的静止内存（release 运行器，480 × 640 窗口）。*私有内存*是只属于这个进程的内存（USS）；*常驻内存*还包含共享库的页面
（GTK、GPU 驱动），这些页面由机器上所有 GTK 应用共享：

| 应用 | 渲染器 | 私有内存（USS） | 常驻内存（RSS） |
|---|---|---|---|
| Rust 应用（`nsh init --template rust`） | GL（`ngl`） | **~49 MB** | ~142 MB |
| Rust 应用 | Cairo（`GSK_RENDERER=cairo`） | ~28 MB | ~95 MB |
| TSX 计数器（`examples/counter`） | GL | **~79 MB** | ~166 MB |
| 只有一个 label 的 GTK 4 窗口，作为参照 | Vulkan / Cairo | ~62 / ~40 MB | ~132 / ~109 MB |

再次访问同一页面不会增加内存；第一次访问某个页面时，进程增长的是它有意保留的缓存（解码后的图片，上限 128 MB）以及首次使用时加载的库（网页视图用的 WebKitGTK）。

这些数字来自：

- **渲染器**：在 NVIDIA 驱动下，NSH 使用 GSK 的 GL 渲染器绘制，在那里它每帧的开销只是 Vulkan 渲染器的一小部分（Animations 演示：每帧绘制 ~1 ms，Vulkan 下约 9.5 ms）。仍可用 `GSK_RENDERER` 指定渲染器。
- **Canvas 栅格**：每个 canvas 只栅格化一次，分成保存在 GPU 上的 256 px 图块。动画值变化时，只重绘读取它的操作覆盖的区域，并叠加在绘制中静态部分保留下来的像素上；看不见的 canvas 会等到滚入视野再绘制。
- **路径只暂存一次**：长路径之后的 `fillRect` 和 `fillText` 会把路径留在原处，直到再次用到它（一条 400 点的折线加 240 根柱子：1.68 → 0.63 ms）。

用同样的方式测量一个应用，带上 `--fps` 和 `-v` 运行它的测试或步骤：

```sh
cargo build --release -p nsh-cli
python3 examples/gallery/tools/perf.py --only Stocks,Canvas     # gallery，逐页测量
echo 'await app.wait(5000)' | nsh -v test App.tsx --target linux --fps   # 任意应用
```

## 检查清单

- 语言：用 Rust 编写应用，或至少编写它最常用的部分（[用 Rust 开发](./rust.md)）；TSX 留给经常变化或在运行时下发的部分。
- 交互：一次点击只改变少量 mount item，而不是几十个。
- 列表：长列表一律用虚拟列表（`virtual_list`、`List`），并设置估计的行高；每个条目的状态放在数据里。
- 动画：使用动画值，而不是每帧写入的 signal。
- 滚动效果：使用 `scroll_value`（`scrollValue`），而不是滚动监听。
- 处理函数：不在每次按键或每个滚动事件中做繁重工作；用 `computed` 缓存。

## 另请参阅

- [架构](./architecture.md)
- [测试](./testing-and-trace.md)
- [列表](./lists.md)、[动画](./animation.md)、[响应式](./reactivity.md)
