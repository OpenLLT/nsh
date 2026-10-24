---
title: 性能报告
description: NSH 应用的实测数据：NSH 基线中的提交与帧开销，以及 gallery 在 Linux 上逐页的帧率、CPU 和内存，并附复现方法。
order: 62.5
group: tools
---

# 性能报告

NSH 应用的实测开销。NSH 如何保持高速、如何测量你自己的应用，见[性能](./performance.md)。

## 基线

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

## Linux（GTK 4）

测量环境：Linux 桌面（x86_64，24 线程，NVIDIA GPU），release 构建，gallery 运行在 120 Hz 显示器上一个 1896 × 1030 的窗口里，
所有读数都由 `examples/gallery/tools/perf.py` 自动采集（`nsh test --target linux --fps`，每秒一行；CPU 指整个进程，以单核的百分比计）。
*帧 p95* 是主线程绘制一帧所用时间的第 95 百分位：低于 8.3 ms，一帧就能放进 120 Hz 的一次刷新。

### 动画演示

<div class="data-table">

| 演示 | FPS | 帧 p95 | CPU |
|---|---|---|---|
| Stocks：22 条实时走势线、分时图、盘口、逐笔成交 | 117–120 | 5–6 ms | 29%（1200 × 800）、31–32%（1896 × 1030） |
| Canvas：仪表盘、时钟、点阵 | 120 | 2.6–4.4 ms | 5–10% |
| Animations：三个原生循环、弹簧、序列 | 120 | 2.0 ms | 12–13% |

</div>

### 每个页面

NSH 只在屏幕上有内容变化时才绘制一帧，所以 FPS 就是变化的频率：静止的页面不绘制，动画每次刷新绘制一帧，滚动时测试每发一次滚动事件绘制一帧。
*超过 8.3 ms* 是错过 120 Hz 刷新的帧所占的比例；为 0% 时，每一次变化都在下一次刷新就显示到了屏幕上。

<div class="data-table">

| 页面 | 帧的来源 | FPS | 帧 p95 | 超过 8.3 ms | CPU |
|---|---|---|---|---|---|
| Stocks | 实时数据、原生循环 | 118–120 | 4.2–4.9 ms | 0% | 28–33% |
| Stocks，滚动 | 实时数据、原生循环 | 119 | 5.8–6.8 ms | 1–2% | 32% |
| Gestures | 弹簧、脉动的圆环 | 120 | 4.4–4.5 ms | 0–1% | 10% |
| Animations | 原生循环 | 120 | 2.0 ms | 0% | 13% |
| Canvas | 原生循环 | 120 | 2.8–4.3 ms | 0% | 8–10% |
| Styles，滚动 | 滚动事件 | 118 | 4.0 ms | 0% | 5% |
| Tailwind | `animate-*` 工具类 | 106–108 | 0.4–3.6 ms | 0–2% | 3–11% |
| Controls | 过渡动画，间隔 800 ms | 102–110 | 0.3–1.3 ms | 0% | 3–5% |
| Web and video | 视频帧、网页 | 72–112 | 1.2–4.6 ms | 0% | 8–9% |
| Photos，滚动 | 滚动事件 | 62 | 5.7 ms | 1% | 12% |
| Text View，滚动 | 滚动事件 | 61 | 4.2 ms | 0% | 5% |
| Scrolling，滚动 | 滚动事件 | 48 | 3.0 ms | 2% | 5% |
| Lists，滚动 | 滚动事件 | 47 | 4.7 ms | 1% | 5% |
| Images | GIF 和 WebP 的帧 | 42–46 | 1.4–3.7 ms | 0% | 4% |
| Form，滚动 | 滚动事件 | 41 | 4.6 ms | 0% | 3% |
| Text，滚动 | 滚动事件 | 37 | 4.7 ms | 2% | 4% |

</div>

### 内存

启动 3 秒后的静止内存（release 运行器，480 × 640 窗口）。*私有内存*是只属于这个进程的内存（USS）；*常驻内存*还包含共享库的页面
（GTK、GPU 驱动），这些页面由机器上所有 GTK 应用共享：

<div class="data-table">

| 应用 | 渲染器 | 私有内存（USS） | 常驻内存（RSS） |
|---|---|---|---|
| Rust 应用（`nsh init --template rust`） | GL（`ngl`） | ~49 MB | ~142 MB |
| Rust 应用 | Cairo（`GSK_RENDERER=cairo`） | ~28 MB | ~95 MB |
| TSX 计数器（`examples/counter`） | GL | ~79 MB | ~166 MB |
| 只有一个 label 的 GTK 4 窗口，作为参照 | Vulkan / Cairo | ~62 / ~40 MB | ~132 / ~109 MB |

</div>

再次访问同一页面不会增加内存；第一次访问某个页面时，进程增长的是它有意保留的缓存（解码后的图片，上限 128 MB）以及首次使用时加载的库（网页视图用的 WebKitGTK）。

### 应用体积

用 `nsh init` 的每种模板生成的 hello world 应用，以及两个实际在用的应用，由 `nsh package --target linux` 为 x86_64 构建。运行器是应用唯一的可执行文件；
压缩包是它发布用的 `.tar.gz`。hello world 都以链接时优化构建并去除符号（`CARGO_PROFILE_RELEASE_LTO=fat`、
`CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1`、`CARGO_PROFILE_RELEASE_STRIP=true`）：

<div class="data-table">

| 应用 | 编写语言 | 运行器 | 压缩包 |
|---|---|---|---|
| Hello world（`--template rust`） | Rust | 16.5 MB | 7.5 MB |
| Hello world（`--template ts`） | TSX，运行在 QuickJS 上 | 25.7 MB | 11.6 MB |
| Hello world（`--template mixed`） | TSX 加一个 Rust crate | 25.8 MB | 11.7 MB |
| [sysmon](https://github.com/huacnlee/sysmon) 0.1.3 | Rust | 20.9 MB（去除符号后） | 9.7 MB |
| [Omasend](https://github.com/huacnlee/omasend) 0.2.0 | Rust | 22.3 MB | 9.8 MB |

</div>

TSX 运行器包含 QuickJS 运行时、原生模块和渲染器；应用自己的代码是运行器旁边的 bundle，hello world 的不到 1 KB。

这些数字来自：

- **渲染器**：在 NVIDIA 驱动下，NSH 使用 GSK 的 GL 渲染器绘制，在那里它每帧的开销只是 Vulkan 渲染器的一小部分（Animations 演示：每帧绘制 ~1 ms，Vulkan 下约 9.5 ms）。仍可用 `GSK_RENDERER` 指定渲染器。
- **Canvas 栅格**：每个 canvas 只栅格化一次，分成保存在 GPU 上的 256 px 图块。动画值变化时，只重绘读取它的操作覆盖的区域，并叠加在绘制中静态部分保留下来的像素上；看不见的 canvas 会等到滚入视野再绘制。
- **路径只暂存一次**：长路径之后的 `fillRect` 和 `fillText` 会把路径留在原处，直到再次用到它（一条 400 点的折线加 240 根柱子：0.63 ms）。

用同样的方式测量一个应用，带上 `--fps` 和 `-v` 运行它的测试或步骤：

```sh
cargo build --release -p nsh-cli
python3 examples/gallery/tools/perf.py --only Stocks,Canvas     # gallery，逐页测量
echo 'await app.wait(5000)' | nsh -v test App.tsx --target linux --fps   # 任意应用
```

