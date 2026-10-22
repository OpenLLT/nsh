---
title: Plot
description: "nsh/base/plot 的 Plot 组件及其图形 Line、Area 和 Grid：根据应用的数据行原生绘制图表，负责坐标轴的比例尺和指针下的数据行，没有自己的外观。"
order: 20.9
group: base
demo: el-plot
---

# Plot

Plot 是图表的框架：它持有要显示的数据行、x 轴和 y 轴的比例尺，以及指针在它上面的位置。它的图形负责绘制这些内容：`Line` 是穿过一个系列的折线，`Area` 是系列与基线之间的区域，`Grid` 是横跨图表的网格线。每个图形都是一个铺满 plot 的画布，根据数据行原生绘制：应用设置数据行时只读取一次，之后在 Rust 中完成缩放、录制和绘制，所以一千个点的图表也不会为每个点运行 JS；指针同样在 Rust 中跟踪，应用只会在指针移到另一行时收到通知。外观由应用决定：图形使用 CSS 中 SVG 图形的绘制属性（`stroke-*`、`fill-*`），没有设置时使用 `currentColor`；提示框、标记和坐标轴标签都是应用自己的元素。

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
        .accessibility_label("每天的访客数")
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
        {hovered() == null ? "访客" : `${rows[hovered()!].day}: ${rows[hovered()!].visitors}`}
      </Text>
      <Plot
        data={rows}
        y="visitors"
        yScale={{ type: "linear", domain: [0, 3000] }}
        accessibilityLabel="每天的访客数，周四最多"
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

`Plot`、`Line`、`Area` 和 `Grid` 来自 `nsh/base/plot`，这是 [`nsh/base`](../modules/nsh-base.md) 中单独的一个模块（Rust 中是 `nsh_base::plot`）。在 TypeScript 中，plot 的属性对数据行的类型是泛型的：`x` 和 `y` 会按数据行的字段做类型检查。在 Rust 中，`plot()` 为每个属性提供一个 setter，数据行是 `Rows`（按键名存放的数字列），图形使用带类型的绘制方法（`.stroke_color(..)`、`.fill_color(..)`、`.stroke_width(..)`）。

## Plot

| 属性 | Rust | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `data` | `.data(..)` | `T[]` | （必填） | 数据行，每个点一个对象。图形按名称读取其中的数字字段，在应用设置数据行时读取一次；某一行的字段不是数字时，那里留空。 |
| `x` | `.x(..)` | `keyof T` | 行的序号 | 在 `linear` x 比例尺上决定一行沿 x 轴位置的字段。`point` 比例尺按顺序放置各行。 |
| `y` | `.y(..)` | `keyof T` | 无 | 图形没有指定自己的字段时绘制的字段。 |
| `xScale` | `.x_scale(..)` | `Scale` | `{ type: "point" }` | x 轴如何放置各行：`point`（按顺序从左边缘到右边缘均匀分布；只有一行时放在中间），或带可选 `domain` 的 `linear`。 |
| `yScale` | `.y_scale(..)` | `Scale` | `{ type: "linear" }` | y 轴如何放置数值：定义域的最小值在底边，最大值在顶边。没有 `domain` 时取各图形所绘制数值的范围。 |
| `accessibilityLabel` | `.accessibility_label(..)` | `string` | 无 | 屏幕阅读器对图表读出的内容：图表显示了什么，以及值得注意的地方。 |
| `children` | `.child(..)` | `JSX.Element` | 无 | 图形，按顺序叠加绘制，以及应用放在它们上面的内容。 |
| `class`、`style` | 样式方法 | `string`、`StyleProp<ViewStyle>` | 无 | plot 的尺寸和外观；图形会像 CSS 那样继承它的绘制属性。 |

| 事件 | Rust | 参数 | 触发时机 |
|---|---|---|---|
| `onHoverChange` | `.on_hover_change(..)` | `index: number \| null` | 指针移到另一行上：沿 x 轴离指针最近的那一行的序号；指针离开 plot 后为 `null`。 |

`Scale` 是 `{ type: "point" } | { type: "linear"; domain?: [number, number] }`。`domain` 取两个值构成的范围，顺序不限；只有一个值的定义域会把它放在中间。

## Line、Area 和 Grid

| 图形 | 属性 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `Line` | `y` | `string` | plot 的 `y` | 要绘制的字段：每个在该字段上有数字的行对应一个点，没有的行跳过。 |
| `Line` | `curve` | `"natural" \| "linear" \| "stepAfter"` | `"natural"` | 点与点之间如何连接：平滑曲线、直线段，或保持每个值直到下一行的阶梯。 |
| `Area` | `y1` | `string` | plot 的 `y` | 顶边使用的字段。 |
| `Area` | `y0` | `number` | 底边 | 基线在 y 比例尺上的值。 |
| `Area` | `curve` | 同 `Line` | `"natural"` | 顶边的点如何连接。 |
| `Grid` | `x` | `number[]` | 无 | 竖线的位置，取 x 比例尺上的值（`point` 比例尺上是行的序号）。 |
| `Grid` | `y` | `number[]` | 无 | 横线的位置，取 y 比例尺上的值。 |

每个图形都铺满 plot，使用自己的 [SVG 绘制属性](../modules/style-reference.md#svg-绘制) 绘制；像 CSS 的继承一样，自己设置的值优先于 plot 上的值：

| 图形 | 使用的属性 | 没有设置时 |
|---|---|---|
| `Line` | `stroke`、`strokeWidth`、`strokeDasharray` | `currentColor`，宽 1，实线 |
| `Area` | `fill`；顶边使用 `stroke`、`strokeWidth`、`strokeDasharray` | `fill` 为 `currentColor`；没有描边 |
| `Grid` | `stroke`、`strokeWidth`、`strokeDasharray` | `currentColor`，宽 1，实线；每条线都落在整数设备像素上，细线也保持清晰 |

plot 没有设置定义域时，`Line` 和 `Area` 绘制的数值（包括 area 的 `y0`）构成 y 比例尺的定义域；grid 的数值不计入。

## 构建图表

一个图表由 plot、它的图形以及应用自己放在周围的元素组成。应用要给 y 轴加标签时，为 y 比例尺指定 `domain`，标签就能对齐网格线的数值。指针下那一行的提示框或标记由应用绘制：放在该行的 `Grid` 就是一条竖线，该行的数值显示在应用想放的地方。

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
      {/* 指针下那一行的数值，没有时取最后一行。 */}
      <View class="flex-row items-baseline">
        <Text class="flex-1 text-sm text-muted-foreground">{shown().time}</Text>
        <Text class="text-right text-xl font-semibold tabular-nums text-foreground">{shown().price.toFixed(2)}</Text>
      </View>
      <View class="flex-row gap-2">
        <Plot
          data={props.rows}
          y="price"
          yScale={{ type: "linear", domain: [props.low, props.high] }}
          accessibilityLabel={`价格，从 ${props.rows[0].price} 到 ${shown().price}`}
          onHoverChange={(index) => hovered.set(index)}
          class="h-48 flex-1"
        >
          <Grid y={[props.low, middle(), props.high]} class="stroke-border" style={{ strokeDasharray: "3 3" }} />
          <Area class="fill-chart-1/15" />
          <Line class="stroke-chart-1 stroke-2" />
          {/* 标记：指针下那一行处的竖线。 */}
          <Grid x={hovered() == null ? [] : [hovered()!]} class="stroke-muted-foreground" />
        </Plot>
        {/* y 轴标签，放在网格线的数值处（坐标轴图形推出之前先用 Text）。 */}
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

应用为图表周围的元素加动画（例如淡入的提示框）时，用 `motion-reduce:` 让偏好减少动态效果的用户看到静止的版本；图形本身在数据变化时立即重绘。

## 无障碍

- plot 对屏幕阅读器是一个元素，角色为图像，读出应用的 `accessibilityLabel`；图形是它的组成部分，自己不读出任何内容。在标签中说明图表显示了什么以及值得注意的地方（范围、最高值）；数字很重要时，再用文字或列表提供数据行。
- 在有指针的平台上（桌面、网页、配触控板的 iPad），指针下的行通过 `onHoverChange` 报告。触摸屏没有悬停：触摸用户需要的数值请用应用自己的元素显示。
- plot 不接收点按，也不获得键盘焦点。

关于标签和角色的一般说明，见 [无障碍](../docs/accessibility.md)。

## 平台说明

- 所有平台以相同的方式绘制图形：每个图形一份在 Rust 中录制的绘图。数据行变化时，读取它们的图形在一个批次中重绘；绘制类名的变化（外观、`dark:`）只会重新发送绘图，不需要重新录制。
- 数据行的数字字段在应用设置 `data` 时读取；要绘制计算出的值，先在 JS 中派生出一个字段（一次 `map`）。
