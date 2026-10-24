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

The demos that animate all the time:

| Demo | What moves | fps · frame p95 · CPU |
|---|---|---|
| Stocks | 22 live sparklines pulsing natively, an intraday chart redrawn on every 50 ms tick, order book, tape | 117–120 · 5–6 ms · 31–32% (29% in a 1200 × 800 window) |
| Canvas | A gauge, a clock's second hand and a dot matrix on native loops | 120 · 2.6–4.4 ms · 5–10% |
| Animations | Three native loops, springs, staggered sequences | 120 · 2.0 ms · 12–13% |

Every page of the gallery, idle (the page as it opens) and while the test scrolls it with the wheel. The frame rate
follows what moves: a page at rest draws no frames, and a scroll draws frames as the wheel events come:

| Page | fps | Frame p95 | Frames over 8.3 ms | CPU |
|---|---|---|---|---|
| Stocks, idle | 118–120 | 4.2–4.9 ms | 0% | 28–33% |
| Stocks, scrolling the watchlist | 119 | 5.8–6.8 ms | 1–2% | 32% |
| Photos, scrolling | 62 | 5.7 ms | 1% | 12% |
| Lists, scrolling | 47 | 4.7 ms | 1% | 5% |
| Scrolling, scrolling | 48 | 3.0 ms | 2% | 5% |
| Form, scrolling | 41 | 4.6 ms | 0% | 3% |
| Gestures (springs, a pulsing ring) | 120 | 4.4–4.5 ms | 0–1% | 10% |
| Animations | 120 | 2.0 ms | 0% | 13% |
| Canvas | 120 | 2.8–4.3 ms | 0% | 8–10% |
| Styles, scrolling | 118 | 4.0 ms | 0% | 5% |
| Tailwind (animated utilities) | 106–108 | 0.4–3.6 ms | 0–2% | 3–11% |
| Text, scrolling | 37 | 4.7 ms | 2% | 4% |
| Text View, scrolling | 61 | 4.2 ms | 0% | 5% |
| Images (GIF and WebP playing) | 42–46 | 1.4–3.7 ms | 0% | 4% |
| Controls | 102–110 | 0.3–1.3 ms | 0% | 3–5% |
| Web and video | 72–112 | 1.2–4.6 ms | 0% | 8–9% |

Memory at rest, 3 s after start (release runners, a 480 × 640 window). *Private* is the memory the process alone
owns (USS); *resident* adds the shared libraries' pages (GTK, the GPU driver), which every GTK app on the machine
shares:

| App | Renderer | Private (USS) | Resident (RSS) |
|---|---|---|---|
| Rust app (`nsh init --template rust`) | GL (`ngl`) | **~49 MB** | ~142 MB |
| Rust app | Cairo (`GSK_RENDERER=cairo`) | ~28 MB | ~95 MB |
| TSX counter (`examples/counter`) | GL | **~79 MB** | ~166 MB |
| A GTK 4 window with one label, for reference | Vulkan / Cairo | ~62 / ~40 MB | ~132 / ~109 MB |

Revisiting a page adds no memory; the first visit to a page grows the process by what it caches on purpose (decoded
images, bounded at 128 MB) and the libraries it loads on first use (WebKitGTK for web views).

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

