---
title: Plot
description: "The Plot component of nsh/base/plot and its marks Line, Area and Grid: charts drawn natively from the app's rows, with the scales of the axes, the row under the pointer and no look of their own."
order: 20.9
group: base
demo: el-plot
---

# Plot

A plot is the frame of a chart: the rows of data it shows, the scales of its x and y axes and the pointer over it. Its
marks draw what it holds: a `Line` through a series, an `Area` between a series and a baseline, a `Grid` of lines
across. Each mark is one canvas filling the plot, drawn natively from the rows: the app's rows are read once when it
sets them, then scaled, recorded and drawn in Rust, so a chart of a thousand points runs no JS per point, and the
pointer is followed in Rust too (the app hears of a new row, nothing more). The look is the app's: marks paint with
CSS's paint properties of SVG shapes (`stroke-*`, `fill-*`), `currentColor` where none is set, and the tooltip, the
marker and the axis labels are the app's own elements.

```rust tabs
use nsh_base::{
    plot::{Curve, RowKey, area, grid, line, plot},
    theme,
};
use nsh_core::ui::{Rows, prelude::*};

fn week(visitors: Vec<f64>, hovered: Signal<Option<u32>>) -> impl IntoElement {
    let rows = Rows::from_columns(visitors.len(), [("visitors".into(), visitors)]);
    plot()
        .data(rows)
        .y(RowKey("visitors".into()))
        .accessibility_label("Visitors per day")
        .h(px(160.0))
        .on_hover_change(move |index: &Option<u32>| hovered.set(*index))
        .child(grid().y(vec![0.0, 1500.0, 3000.0]).stroke_color(move || theme().border))
        .child(area().curve(Curve::Linear).fill_color(move || theme().chart_1.opacity(0.2)))
        .child(
            line()
                .curve(Curve::Linear)
                .stroke_color(move || theme().chart_1)
                .stroke_width(px(2.0)),
        )
}
```

```tsx tabs
import { mount, signal, Text, View } from "nsh";
import { Area, Grid, Line, Plot } from "nsh/base/plot";

const rows = [
  { day: "Mon", visitors: 1820 },
  { day: "Tue", visitors: 2140 },
  { day: "Wed", visitors: 1960 },
  { day: "Thu", visitors: 2480 },
  { day: "Fri", visitors: 2310 },
];

function App() {
  const hovered = signal<number | null>(null);
  return (
    <View class="gap-2 p-4">
      <Text class="text-sm text-muted-foreground tabular-nums">
        {hovered() == null ? "Visitors" : `${rows[hovered()!].day}: ${rows[hovered()!].visitors}`}
      </Text>
      <Plot
        data={rows}
        y="visitors"
        yScale={{ type: "linear", domain: [0, 3000] }}
        accessibilityLabel="Visitors per day, highest on Thursday"
        onHoverChange={(index) => hovered.set(index)}
        class="h-40"
      >
        <Grid y={[0, 1500, 3000]} class="stroke-border" style={{ strokeDasharray: "3 3" }} />
        <Area curve="linear" class="fill-chart-1/20" />
        <Line curve="linear" class="stroke-chart-1 stroke-2" />
      </Plot>
    </View>
  );
}

mount(App);
```

`Plot`, `Line`, `Area` and `Grid` come from `nsh/base/plot`, a module of [`nsh/base`](../modules/nsh-base.md) of their
own (in Rust, `nsh_base::plot`). In TypeScript a plot's props are generic over the type of its rows: `x` and `y` are
checked against its fields. In Rust, `plot()` makes one with a setter per prop, the rows a `Rows` (columns of numbers
by key), and the marks take the typed paint methods (`.stroke_color(..)`, `.fill_color(..)`, `.stroke_width(..)`).

## Plot

| Prop | Rust | Type | Default | Description |
|---|---|---|---|---|
| `data` | `.data(..)` | `T[]` | (required) | The rows, one object per point. The marks read their number fields by name, once, when the app sets the rows; a field that is not a number on some row leaves a gap there. |
| `x` | `.x(..)` | `keyof T` | the row's index | The field that places a row along the x axis on a `linear` x scale. A `point` scale places the rows in order. |
| `y` | `.y(..)` | `keyof T` | none | The field the marks draw unless they name their own. |
| `xScale` | `.x_scale(..)` | `Scale` | `{ type: "point" }` | How the x axis places rows: `point` (in order, evenly from the left edge to the right one; one row in the middle) or `linear` with an optional `domain`. |
| `yScale` | `.y_scale(..)` | `Scale` | `{ type: "linear" }` | How the y axis places values: the domain's smallest value at the bottom edge, its largest at the top. Without a `domain`, the extent of what the marks draw. |
| `accessibilityLabel` | `.accessibility_label(..)` | `string` | none | What screen readers say of the chart: what it shows and what stands out. |
| `children` | `.child(..)` | `JSX.Element` | none | The marks, drawn in order over each other, and whatever the app lays over them. |
| `class`, `style` | style methods | `string`, `StyleProp<ViewStyle>` | none | The plot's size and look; the marks inherit its paint properties, as CSS inherits them. |

| Event | Rust | Payload | When |
|---|---|---|---|
| `onHoverChange` | `.on_hover_change(..)` | `index: number \| null` | The pointer came over another row: the index of the row nearest to it along the x axis; `null` once it leaves the plot. |

`Scale` is `{ type: "point" } | { type: "linear"; domain?: [number, number] }`. A `domain` is the extent of its two
values, in either order; a domain of one value puts it in the middle.

## Line, Area and Grid

| Mark | Prop | Type | Default | Description |
|---|---|---|---|---|
| `Line` | `y` | `string` | the plot's `y` | The field it draws: one point per row with a number there, the rows without one skipped. |
| `Line` | `curve` | `"natural" \| "linear" \| "stepAfter"` | `"natural"` | How it connects its points: a smooth curve, straight segments, or steps that hold each value until the next row. |
| `Area` | `y1` | `string` | the plot's `y` | The field of its top edge. |
| `Area` | `y0` | `number` | the bottom edge | The value of its baseline on the y scale. |
| `Area` | `curve` | as `Line`'s | `"natural"` | How its top edge connects its points. |
| `Grid` | `x` | `number[]` | none | Where its vertical lines go, as values of the x scale (row indices on a `point` scale). |
| `Grid` | `y` | `number[]` | none | Where its horizontal lines go, as values of the y scale. |

Each mark fills the plot and paints with its [SVG paint properties](../modules/style-reference.md#svg-paint), its own
over those of the plot, as CSS inherits them:

| Mark | Paints with | Where none is set |
|---|---|---|
| `Line` | `stroke`, `strokeWidth`, `strokeDasharray` | `currentColor`, 1 wide, solid |
| `Area` | `fill`; its top edge `stroke`, `strokeWidth`, `strokeDasharray` | `fill` `currentColor`; no stroke |
| `Grid` | `stroke`, `strokeWidth`, `strokeDasharray` | `currentColor`, 1 wide, solid; each line on whole device pixels, so a thin one stays sharp |

The values a `Line` or an `Area` draws, an area's `y0` too, make the y scale's domain when the plot has none; a grid's
do not.

## Building charts

A chart is a plot, its marks and the app's own elements around them. Give the y scale a `domain` when the app labels
it: the labels then sit at the grid's values. The tooltip or marker of the row under the pointer is the app's: a
`Grid` at that row is a vertical rule, and the row's values go where the app shows them.

```tsx
import { signal, Text, View } from "nsh";
import { Area, Grid, Line, Plot } from "nsh/base/plot";

type Row = { time: string; price: number };

export function PriceChart(props: { rows: Row[]; low: number; high: number }) {
  const hovered = signal<number | null>(null);
  const shown = () => props.rows[hovered() ?? props.rows.length - 1];
  const middle = () => (props.low + props.high) / 2;
  return (
    <View class="gap-3 rounded-xl border border-border bg-card p-4">
      {/* The value of the row under the pointer, or the last one. */}
      <View class="flex-row items-baseline">
        <Text class="flex-1 text-sm text-muted-foreground">{shown().time}</Text>
        <Text class="text-right text-xl font-semibold tabular-nums text-foreground">{shown().price.toFixed(2)}</Text>
      </View>
      <View class="flex-row gap-2">
        <Plot
          data={props.rows}
          y="price"
          yScale={{ type: "linear", domain: [props.low, props.high] }}
          accessibilityLabel={`Price, from ${props.rows[0].price} to ${shown().price}`}
          onHoverChange={(index) => hovered.set(index)}
          class="h-48 flex-1"
        >
          <Grid y={[props.low, middle(), props.high]} class="stroke-border" style={{ strokeDasharray: "3 3" }} />
          <Area class="fill-chart-1/15" />
          <Line class="stroke-chart-1 stroke-2" />
          {/* The marker: a rule at the row under the pointer. */}
          <Grid x={hovered() == null ? [] : [hovered()!]} class="stroke-muted-foreground" />
        </Plot>
        {/* The y axis' labels, at the grid's values (Text until an axis mark lands). */}
        <View class="-my-2 w-8 justify-between">
          {[props.high, middle(), props.low].map((v) => (
            <Text class="text-right text-xs tabular-nums text-muted-foreground">{v.toFixed(0)}</Text>
          ))}
        </View>
      </View>
      <View class="mr-10 flex-row justify-between">
        <Text class="text-xs text-muted-foreground">{props.rows[0].time}</Text>
        <Text class="text-xs text-muted-foreground">{props.rows[props.rows.length - 1].time}</Text>
      </View>
    </View>
  );
}
```

When the app animates something it draws around the chart (a tooltip that fades in), `motion-reduce:` keeps it still
for people who ask for less motion; the marks draw each change at once.

## Accessibility

- A plot is one element for screen readers, with the image role and the app's `accessibilityLabel`; its marks are
  parts of it and say nothing themselves. Say in the label what the chart shows and what stands out (the range, the
  highest value), and offer the rows as text or a list where the numbers matter.
- The row under the pointer is reported with `onHoverChange` on platforms with a pointer (desktops, the web, an iPad
  with a trackpad). Touch screens report no hover: show the values a touch user needs in the app's own elements.
- A plot takes no presses and no keyboard focus.

See [Accessibility](../docs/accessibility.md) for labels and roles in general.

## Platform notes

- Every platform draws the marks the same way, from one drawing per mark recorded in Rust; a change of the rows
  draws the marks that read them again in one batch, and a change of a paint class (the appearance, `dark:`) sends
  the drawing again without recording it.
- The rows' number fields are read when the app sets `data`; derive a field in JS first (one `map`) to plot a computed
  value.
