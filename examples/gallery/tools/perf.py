#!/usr/bin/env python3
"""The gallery's frame rate, CPU and memory, page by page, on this desktop.

Opens the gallery in the platform's window (`nsh test --target <linux|macos>
--fps`), visits every demo, lets it run idle and scrolls it, and reads the
performance monitor's line of every second (`nsh::perf`). Prints a table per
scenario and writes the readings as JSON:

    cargo build --release -p nsh-cli
    python3 examples/gallery/tools/perf.py [--nsh target/release/nsh] [--only Stocks,Canvas]

Each scenario is measured for `--seconds` after a second of warm-up. `fps` is
the frames drawn per second (0 for a page with nothing moving), `moving` the
rate while something moves (one frame per median gap between drawn frames), `frame p95`
the main thread's time per drawn frame and `over` the share of frames longer
than a 120 Hz refresh (8.3 ms); `cpu` is the process' (percent of one core).
"""

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

GALLERY = Path(__file__).resolve().parent.parent

# The demos of the gallery's index (`App.tsx`), as their rows are labeled.
DEMOS = [
    "Stocks", "AI Chat", "Photos", "Lists", "Scrolling", "Navigation", "Form", "Resizable", "Dock",
    "Gestures", "Physics", "Animations", "Canvas", "Styles", "Tailwind", "Text", "Text View", "Images",
    "Components", "Overlays", "Menus", "Controls", "Web and video", "System", "Standard APIs", "Storage",
]

LINE = re.compile(
    r"fps (?P<fps>\d+)/(?P<hz>\d+) frame (?P<frame>[\d./]+) gap (?P<gap>[\d./]+) over (?P<over>\d+)% "
    r"update (?P<update>[\d./]+) layout (?P<layout>[\d./]+) paint (?P<paint>[\d./]+) snapshot (?P<snapshot>[\d./]+) canvas (?P<canvas>[\d./]+) "
    r"drain (?P<drain>[\d./]+) commits (?P<commits>\d+) js (?P<js>[\d./]+) core (?P<core>[\d./]+) "
    r"items (?P<items>\d+) engine (?P<engine>\d+)% cpu (?P<cpu>[\d-]+)%? rss (?P<rss>[\d.]+) MB"
)
MARK = re.compile(r"@@perf (?P<name>.+)$")


def steps(demos: list[str], seconds: int) -> str:
    ms = seconds * 1000
    names = json.dumps(demos)
    return f"""
const mark = (name: string) => console.log(`@@perf ${{name}}`);
const scroll = async () => {{
  // A text in the middle of the page, in the scroll view that holds it.
  const texts = app.texts();
  for (const text of texts.slice(Math.floor(texts.length / 3))) {{
    try {{
      await app.scroll(`text:${{text}}`, 3000);
      await app.scroll(`text:${{text}}`, -3000);
      return true;
    }} catch {{}}
  }}
  return false;
}};
mark("Home idle");
await app.wait({ms});
mark("Home scroll");
const until = Date.now() + {ms};
while (Date.now() < until && (await scroll())) {{}}
for (const demo of {names}) {{
  mark("-");
  await app.press(`label:${{demo}}`);
  await app.wait(1000);
  mark(`${{demo}} idle`);
  await app.wait({ms});
  mark(`${{demo}} scroll`);
  const end = Date.now() + {ms};
  while (Date.now() < end && (await scroll())) {{}}
  mark("-");
  await app.back();
  await app.wait(500);
}}
mark("-");
"""


def summary(stat: str) -> list[float]:
    return [float(v) for v in stat.split("/")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nsh", default=str(GALLERY.parent.parent / "target/release/nsh"))
    parser.add_argument("--target", default="linux" if sys.platform.startswith("linux") else "macos")
    parser.add_argument("--only", help="comma-separated demos (default: all)")
    parser.add_argument("--seconds", type=int, default=4)
    parser.add_argument("--size", default="1200x800", help="the window, WxH in points")
    parser.add_argument("--out", help="the JSON file of the readings")
    args = parser.parse_args()
    demos = [d.strip() for d in args.only.split(",")] if args.only else DEMOS
    width, height = args.size.split("x")

    work = GALLERY / ".nsh" / "perf"
    work.mkdir(parents=True, exist_ok=True)
    test = work / "gallery.test.ts"
    test.write_text(
        'import { open, test } from "nsh/test";\n\n'
        'test("perf", async () => {\n'
        f'const app = await open("../../App.tsx", {{ width: {width}, height: {height}, network: "live" }});\n'
        "await app.wait(1500);\n"
        f"{steps(demos, args.seconds)}\n"
        "}, 3_600_000);\n"
    )
    command = [args.nsh, "-v", "test", str(test), "--target", args.target, "--fps"]
    print("$", " ".join(command), file=sys.stderr)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    scenario = None
    readings: dict[str, list[dict]] = {}
    skip = 0
    log = []
    assert proc.stdout
    for raw in proc.stdout:
        log.append(raw)
        if m := MARK.search(raw):
            name = m["name"].strip()
            scenario = None if name == "-" else name
            # The second the mark falls in is part the previous scenario's.
            skip = 1
            if scenario:
                readings.setdefault(scenario, [])
            continue
        if scenario and (m := LINE.search(raw)):
            if skip:
                skip -= 1
                continue
            readings[scenario].append(m.groupdict())
    code = proc.wait()
    if code != 0:
        sys.stdout.write("".join(log[-60:]))
        print(f"nsh test exited with {code}", file=sys.stderr)

    rows = []
    for name, lines in readings.items():
        if not lines:
            continue
        fps = [int(l["fps"]) for l in lines]
        frame_p95 = [summary(l["frame"])[2] for l in lines if int(l["fps"]) > 0]
        # While something moves: one frame per median gap between drawn frames.
        gaps = [summary(l["gap"])[1] for l in lines if int(l["fps"]) > 0 and summary(l["gap"])[1] > 0]
        over = [int(l["over"]) for l in lines]
        cpu = [int(l["cpu"]) for l in lines if l["cpu"] != "-"]
        rss = [float(l["rss"]) for l in lines]
        rows.append({
            "scenario": name,
            "seconds": len(lines),
            "fps": statistics.median(fps),
            "fps_min": min(fps),
            "moving_fps": min(1000 / statistics.median(gaps), float(lines[-1]["hz"])) if gaps else 0.0,
            "hz": int(lines[-1]["hz"]),
            "frame_p95": max(frame_p95) if frame_p95 else 0.0,
            "over": max(over),
            "cpu": statistics.mean(cpu) if cpu else 0.0,
            "cpu_max": max(cpu) if cpu else 0,
            "rss": max(rss),
            "commits": statistics.median(int(l["commits"]) for l in lines),
            "core_p95": max(summary(l["core"])[2] for l in lines),
            "js_p95": max(summary(l["js"])[2] for l in lines),
            # Means over the drawn frames' seconds.
            **{
                phase: statistics.mean(summary(l[phase])[0] for l in lines if int(l["fps"]) > 0) if frame_p95 else 0.0
                for phase in ("update", "layout", "paint", "snapshot", "canvas")
            },
        })
    print(f"{'scenario':<26}{'fps':>6}{'min':>5}{'moving':>8}{'frame p95':>11}{'over':>6}{'cpu':>7}{'max':>6}{'rss MB':>8}{'commits':>9}{'core p95':>10}{'js p95':>8}  update/layout/paint/snapshot/canvas")
    for r in rows:
        print(
            f"{r['scenario']:<26}{r['fps']:>6.0f}{r['fps_min']:>5}{r['moving_fps']:>8.0f}{r['frame_p95']:>9.2f}ms{r['over']:>5}%"
            f"{r['cpu']:>6.0f}%{r['cpu_max']:>5}%{r['rss']:>8.1f}{r['commits']:>9.0f}{r['core_p95']:>8.2f}ms{r['js_p95']:>6.2f}ms"
            f"  {r['update']:.2f}/{r['layout']:.2f}/{r['paint']:.2f}/{r['snapshot']:.2f}/{r['canvas']:.2f}"
        )
    (work / "log.txt").write_text("".join(log))
    out = Path(args.out) if args.out else work / "readings.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"readings: {out}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
