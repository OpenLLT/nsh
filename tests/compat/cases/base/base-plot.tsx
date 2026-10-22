// A case of the API's test suite (docs/dev/compatibility.md): `nsh/base/plot`,
// the parts of a chart: a `Plot` of the app's rows (`data`, its `x` / `y`
// fields, the `xScale` / `yScale`), one image for screen readers
// (`accessibilityLabel`), the row nearest the pointer (`onHoverChange`), and
// its marks `Grid` (`x`, `y`), `Area` (`y1`, `y0`, `curve`) and `Line` (`y`,
// `curve`) in it, painted with the paint style keys. A headless run paints
// nothing, so the script checks the plot's layout, its role and label and
// what it reports.
import { Text, View, signal } from "nsh";
import { Area, Grid, Line, Plot } from "nsh/base/plot";

type Row = { t: number; price: number; avg: number };

function App() {
  const rows = signal<Row[]>([
    { t: 0, price: 10, avg: 12 },
    { t: 10, price: 30, avg: 18 },
    { t: 20, price: 20, avg: 22 },
  ]);
  const hovered = signal<number | null>(null);
  return (
    <View style={{ flex: 1, paddingTop: 20, gap: 4 }}>
      <Plot
        testID="plot"
        data={rows()}
        x="t"
        y="price"
        xScale={{ type: "linear", domain: [0, 40] }}
        yScale={{ type: "linear", domain: [0, 40] }}
        accessibilityLabel="Price"
        onHoverChange={(index) => hovered.set(index)}
        class="h-[100px] w-[200px] stroke-current"
        style={{ color: "#3366ff" }}
      >
        <Grid x={[0, 10, 20]} y={[0, 20, 40]} class="stroke-[#cccccc] stroke-1" style={{ strokeDasharray: "2 2" }} />
        <Area y1="price" y0={0} curve="linear" class="fill-[#3366ff]/20 stroke-none" />
        <Line y="avg" curve="stepAfter" style={{ stroke: "#ff0000", strokeWidth: 2 }} />
        <Line curve="natural" class="fill-none" />
      </Plot>
      <Text>{`hovered ${hovered()}`}</Text>
      <View
        testID="more"
        onPress={() => rows.set([...rows(), { t: 20, price: 35, avg: 25 }])}
        style={{ height: 20 }}
      />
      <Text>{`rows ${rows().length}`}</Text>
    </View>
  );
}

export default App;
