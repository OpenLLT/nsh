//! `Area`: a series drawn as the region between its line and a baseline.

use nsh_core::{SvgPaint, ui::prelude::*};

use super::{
    PlotContext, layer,
    line::{Curve, trace},
    scale::extent,
};

/// The props of [`Area`].
#[derive(Debug, Clone, PartialEq, Props)]
pub struct AreaProps {
    /// The field of the plot's rows that makes its top edge (`gpui-base`'s
    /// `y1`); the plot's `y` without one.
    pub y1: Prop<Option<SharedString>>,
    /// The value of its baseline on the y scale (`gpui-base`'s `y0`);
    /// without one, the bottom edge of the plot.
    pub y0: Prop<Option<f64>>,
    /// How its top edge connects its points: `natural` (the default, a
    /// smooth curve), `linear` or `stepAfter`.
    #[prop(default)]
    pub curve: Prop<Curve>,
}

/// A series of a [`Plot`](super::Plot) drawn as the region between its line and
/// a baseline (`gpui-base`'s `Area`): its top edge goes through one point
/// per row with a number in its field, placed by the plot's scales, as a
/// [`Line`](super::Line) does, and it closes down to `y0`. It fills with its
/// `fill` (`fill-*` classes; inherited from the plot as CSS inherits it),
/// `currentColor` where none is set, and strokes its top edge with its
/// `stroke` (`stroke-*`, `strokeWidth`, `strokeDasharray`), none where none
/// is set. Its values and baseline count in the y scale's domain when the
/// plot has none.
#[component]
pub fn Area(props: AreaProps, _cx: Scope<NoEvent>) -> impl IntoElement {
    let plot = PlotContext::of("Area");
    let (y1, y0, curve) = (props.y1, props.y0, props.curve);
    if let Some(plot) = plot {
        plot.add_extent(move || {
            let ys = plot.column(y1.get())?;
            extent(ys.iter().copied().chain(y0.get()))
        });
    }
    layer(move || {
        let p = Painter::new().fill_style_from_view(SvgPaint::CurrentColor);
        let Some(plot) = plot else { return p };
        let Some(ys) = plot.column(y1.get()) else {
            return p;
        };
        let points = plot.points(&ys);
        let (Some(first), Some(last)) = (points.first(), points.last()) else {
            return p;
        };
        let curve = curve.get();
        let base = match y0.get() {
            Some(v) => plot.y_map.get().tick(v).unwrap_or(0.0),
            None => plot.size.get().height.0,
        };
        let top = |p: Painter| trace(p.begin_path().move_to(first.x, first.y), &points, curve);
        let p = top(p)
            .line_to(last.x, px(base))
            .line_to(first.x, px(base))
            .close_path()
            .fill()
            .stroke_style_from_view(SvgPaint::None)
            .line_width_from_view()
            .line_dash_from_view();
        top(p).stroke()
    })
}
