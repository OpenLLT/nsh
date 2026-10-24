---
title: Performance report
description: Measured numbers of NSH apps - commit and frame costs from NSH's baselines, and the gallery's frame rate, CPU and memory page by page on Linux - with how to reproduce them.
order: 62.5
group: tools
---

# Performance report

What NSH apps cost, measured. How NSH keeps them fast and how to measure your own app is in [Performance](./performance.md).

## Baselines

From NSH's own baselines (Apple silicon unless noted):

| Scenario | Numbers |
|---|---|
| Counter app, headless (debug) | First frame ~0.5–0.65 ms (58 ops / 49 mount items); one tap ~0.15 ms |
| Counter app, Mac Catalyst (release) | First frame ~1.05–1.15 ms (about 0.7 ms of it lays out 10 texts with CoreText for the first time); one tap ~0.12 ms |
| Gallery photo list, headless (debug) | First frame 653 ops / 224 nodes, ~2.7 ms |
| Scrolling the photo list, Catalyst (release) | Rebinding one row while scrolling slowly ~0.4 ms; a whole screen of ~32 rows on a fast fling 0.9–1.6 ms |
| Scrolling the photo list, Android emulator (arm64, release) | Rebinding one row ~0.3–0.4 ms (JS ~60 µs) |
| Engine startup (release) | ~75–155 µs; the global APIs (`fetch`, `URL`, ...) cost nothing until first used, then ~90 µs |
| Hot reload | ~120 ms from saving a file to the new version running; applying the update 0.2–0.5 ms |

## Linux (GTK 4)

Measured on a Linux desktop (x86_64, 24 threads, NVIDIA GPU), release builds, the gallery in a 1896 × 1030 window on a
120 Hz display, every reading taken automatically by `examples/gallery/tools/perf.py` (`nsh test --target linux --fps`,
one line a second; CPU is the whole process, in percent of one core). *Frame p95* is the main thread's time per drawn
frame at the 95th percentile: under 8.3 ms, a frame fits a 120 Hz refresh.

### Animated demos

<div class="data-table">

| Demo | FPS | Frame p95 | CPU |
|---|---|---|---|
| Stocks: 22 live sparklines, an intraday chart, order book, tape | 117–120 | 5–6 ms | 29% (1200 × 800), 31–32% (1896 × 1030) |
| Canvas: a gauge, a clock, a dot matrix | 120 | 2.6–4.4 ms | 5–10% |
| Animations: three native loops, springs, sequences | 120 | 2.0 ms | 12–13% |

</div>

### Every page

NSH draws a frame only when something on screen changes, so FPS is the rate of change: a page at rest draws none,
an animation draws one per refresh, and a scroll draws one per scroll event the test sends. *Over 8.3 ms* is the share
of frames that missed a 120 Hz refresh; at 0% every change reached the screen in the next refresh.

<div class="data-table">

| Page | Frames come from | FPS | Frame p95 | Over 8.3 ms | CPU |
|---|---|---|---|---|---|
| Stocks | Live data, native loops | 118–120 | 4.2–4.9 ms | 0% | 28–33% |
| Stocks, scrolling | Live data, native loops | 119 | 5.8–6.8 ms | 1–2% | 32% |
| Gestures | Springs, a pulsing ring | 120 | 4.4–4.5 ms | 0–1% | 10% |
| Animations | Native loops | 120 | 2.0 ms | 0% | 13% |
| Canvas | Native loops | 120 | 2.8–4.3 ms | 0% | 8–10% |
| Styles, scrolling | Scroll events | 118 | 4.0 ms | 0% | 5% |
| Tailwind | `animate-*` utilities | 106–108 | 0.4–3.6 ms | 0–2% | 3–11% |
| Controls | Transitions, 800 ms apart | 102–110 | 0.3–1.3 ms | 0% | 3–5% |
| Web and video | Video frames, the page | 72–112 | 1.2–4.6 ms | 0% | 8–9% |
| Photos, scrolling | Scroll events | 62 | 5.7 ms | 1% | 12% |
| Text View, scrolling | Scroll events | 61 | 4.2 ms | 0% | 5% |
| Scrolling, scrolling | Scroll events | 48 | 3.0 ms | 2% | 5% |
| Lists, scrolling | Scroll events | 47 | 4.7 ms | 1% | 5% |
| Images | GIF and WebP frames | 42–46 | 1.4–3.7 ms | 0% | 4% |
| Form, scrolling | Scroll events | 41 | 4.6 ms | 0% | 3% |
| Text, scrolling | Scroll events | 37 | 4.7 ms | 2% | 4% |

</div>

### Memory

At rest, 3 s after start (release runners, a 480 × 640 window). *Private* is the memory the process alone owns (USS);
*resident* adds the shared libraries' pages (GTK, the GPU driver), which every GTK app on the machine shares:

<div class="data-table">

| App | Renderer | Private (USS) | Resident (RSS) |
|---|---|---|---|
| Rust app (`nsh init --template rust`) | GL (`ngl`) | ~49 MB | ~142 MB |
| Rust app | Cairo (`GSK_RENDERER=cairo`) | ~28 MB | ~95 MB |
| TSX counter (`examples/counter`) | GL | ~79 MB | ~166 MB |
| GTK 4 window with one label, for reference | Vulkan / Cairo | ~62 / ~40 MB | ~132 / ~109 MB |

</div>

Revisiting a page adds no memory; the first visit to a page grows the process by what it caches on purpose (decoded
images, bounded at 128 MB) and the libraries it loads on first use (WebKitGTK for web views).

### App size

A hello world app made by `nsh init` with each template, and two apps people use, as `nsh package --target linux`
builds them for x86_64. The runner is the app's one executable; the archive is the `.tar.gz` it ships as. The hello
worlds are built with link-time optimization and stripped (`CARGO_PROFILE_RELEASE_LTO=fat`,
`CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1`, `CARGO_PROFILE_RELEASE_STRIP=true`):

<div class="data-table">

| App | Written in | Runner | Archive |
|---|---|---|---|
| Hello world (`--template rust`) | Rust | 16.5 MB | 7.5 MB |
| Hello world (`--template ts`) | TSX, on QuickJS | 25.7 MB | 11.6 MB |
| Hello world (`--template mixed`) | TSX and a Rust crate | 25.8 MB | 11.7 MB |
| [sysmon](https://github.com/huacnlee/sysmon) 0.1.3 | Rust | 20.9 MB stripped | 9.7 MB |
| [Omasend](https://github.com/huacnlee/omasend) 0.2.0 | Rust | 22.3 MB | 9.8 MB |

</div>

The TSX runners hold the QuickJS runtime, the native modules and the renderer; an app's own code is its bundle beside
the runner, under 1 KB for a hello world.

What makes these numbers:

- **The renderer**: under NVIDIA's driver NSH draws with GSK's GL renderer, whose frames cost a fraction of the Vulkan
  renderer's there (the Animations demo: ~1 ms of drawing per frame instead of ~9.5 ms). `GSK_RENDERER` still chooses.
- **Canvas rasters**: each canvas is rasterized once into 256 px tiles kept on the GPU. An animated value redraws only
  the area the operations reading it cover, over the kept pixels of the drawing's static part; a canvas out of sight
  waits until it scrolls into view.
- **Paths set aside once**: `fillRect` and `fillText` after a long path leave it in place until it is used again (a
  400-point line then 240 bars: 0.63 ms).

To measure an app the same way, run its tests or steps with `--fps` and `-v`:

```sh
cargo build --release -p nsh-cli
python3 examples/gallery/tools/perf.py --only Stocks,Canvas     # the gallery, page by page
echo 'await app.wait(5000)' | nsh -v test App.tsx --target linux --fps   # any app
```

