//! `Line`: a series drawn as a line through its points.

use nsh_core::{SvgPaint, ui::prelude::*};

use super::{PlotContext, layer, scale::extent};

/// How a [`Line`] or an [`Area`](super::Area) connects its points (`gpui-base`'s
/// `Curve`, d3's curve factories).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, PropEnum)]
pub enum Curve {
    /// A smooth curve through every point (`gpui-base`'s cubic Bézier
    /// segments between neighbours).
    #[default]
    Natural,
    /// Straight segments between points (`d3.curveLinear`).
    Linear,
    /// A step that holds each value until the next point
    /// (`d3.curveStepAfter`).
    StepAfter,
}

/// Records the path through `points` (already moved to the first one) as
/// `curve` connects them.
pub(super) fn trace(mut p: Painter, points: &[Point<Points>], curve: Curve) -> Painter {
    let n = points.len();
    match curve {
        Curve::Linear => {
            for q in &points[1..] {
                p = p.line_to(q.x, q.y);
            }
        }
        Curve::StepAfter => {
            for w in points.windows(2) {
                p = p.line_to(w[1].x, w[0].y).line_to(w[1].x, w[1].y);
            }
        }
        // Each segment a cubic through its neighbours' tangents, the end
        // points their own neighbours (`gpui-base`'s `Curve::Natural`).
        Curve::Natural => {
            for i in 0..n - 1 {
                let p0 = points[i.saturating_sub(1)];
                let (p1, p2) = (points[i], points[i + 1]);
                let p3 = points[(i + 2).min(n - 1)];
                let c1 = point(p1.x + (p2.x - p0.x) / 6.0, p1.y + (p2.y - p0.y) / 6.0);
                let c2 = point(p2.x - (p3.x - p1.x) / 6.0, p2.y - (p3.y - p1.y) / 6.0);
                p = p.bezier_curve_to(c1, c2, p2);
            }
        }
    }
    p
}

/// The props of [`Line`].
#[derive(Debug, Clone, PartialEq, Props)]
pub struct LineProps {
    /// The field of the plot's rows it draws (`gpui-base`'s `y`); the
    /// plot's `y` without one.
    pub y: Prop<Option<SharedString>>,
    /// How it connects its points: `natural` (the default, a smooth
    /// curve), `linear` or `stepAfter`.
    #[prop(default)]
    pub curve: Prop<Curve>,
}

/// A series of a [`Plot`](super::Plot) drawn as a line through its points
/// (`gpui-base`'s `Line`): one point per row with a number in its field,
/// placed by the plot's scales, the rows without one skipped. It strokes
/// with its paint properties (`stroke-*` classes, `strokeWidth`,
/// `strokeDasharray`; inherited from the plot as CSS inherits them),
/// `currentColor` where none is set, and has no look of its own beyond
/// that. Its values count in the y scale's domain when the plot has none.
#[component]
pub fn Line(props: LineProps, _cx: Scope<NoEvent>) -> impl IntoElement {
    let plot = PlotContext::of("Line");
    let (y, curve) = (props.y, props.curve);
    if let Some(plot) = plot {
        plot.add_extent(move || extent(plot.column(y.get())?.iter().copied()));
    }
    layer(move || {
        let p = Painter::new()
            .stroke_style_from_view(SvgPaint::CurrentColor)
            .line_width_from_view()
            .line_dash_from_view();
        let Some(plot) = plot else { return p };
        let Some(ys) = plot.column(y.get()) else {
            return p;
        };
        let points = plot.points(&ys);
        let Some(first) = points.first() else {
            return p;
        };
        trace(
            p.begin_path().move_to(first.x, first.y),
            &points,
            curve.get(),
        )
        .stroke()
    })
}
