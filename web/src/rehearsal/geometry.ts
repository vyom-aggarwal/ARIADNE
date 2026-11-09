// Written with AI assistance (Claude Code). See AI_USE.md.
// Pure geometry for the 3D rehearsal. Scene axes: x east, y up, z south (three.js convention),
// in metres from the site origin, so float32 keeps centimetre precision.

/** Site metres (east, north) to scene (x, z) relative to an origin in site metres. */
export function toLocal(xy: [number, number], origin: [number, number]): [number, number] {
  return [xy[0] - origin[0], -(xy[1] - origin[1])];
}

/** Which heightmap to draw for a chunk at `distance` metres from the camera. */
export function lodLevel(distance: number, switchDistance: number): "fine" | "coarse" {
  return distance < switchDistance ? "fine" : "coarse";
}

/** A billboard `ahead` metres from the capture point along the view azimuth (clockwise from
 * north), turned so its face points back to the capture point. The plane's default normal is
 * +z; rotating by rotationY about y gives the normal (sin r, 0, cos r). */
export function billboardPose(capture: [number, number], azimuthDeg: number, ahead: number) {
  const a = (azimuthDeg * Math.PI) / 180;
  return {
    x: capture[0] + ahead * Math.sin(a),
    z: capture[1] - ahead * Math.cos(a),
    rotationY: -a,
  };
}

export interface HeightGrid {
  heights: ArrayLike<number>; // row-major posts, row 0 at `north`
  cols: number;
  rows: number;
  cell: number;
  west: number; // scene x of column 0
  north: number; // scene z of row 0 (z grows southward)
}

/** Bilinear height at scene (x, z) from posts `cell` metres apart. */
export function groundHeight(g: HeightGrid, x: number, z: number): number {
  const fc = Math.min(Math.max((x - g.west) / g.cell, 0), g.cols - 1);
  const fr = Math.min(Math.max((z - g.north) / g.cell, 0), g.rows - 1);
  const c0 = Math.min(Math.floor(fc), g.cols - 2);
  const r0 = Math.min(Math.floor(fr), g.rows - 2);
  const tc = fc - c0;
  const tr = fr - r0;
  const h = (r: number, c: number) => g.heights[r * g.cols + c];
  return (
    h(r0, c0) * (1 - tc) * (1 - tr) +
    h(r0, c0 + 1) * tc * (1 - tr) +
    h(r0 + 1, c0) * (1 - tc) * tr +
    h(r0 + 1, c0 + 1) * tc * tr
  );
}

export function eyePosition(g: HeightGrid, x: number, z: number, eyeHeight: number) {
  return { x, y: groundHeight(g, x, z) + eyeHeight, z };
}

/** The point `distance` metres along a polyline (clamped to its ends). */
export function pointAlong(route: [number, number][], distance: number): [number, number] {
  let left = Math.max(0, distance);
  for (let i = 0; i + 1 < route.length; i++) {
    const [ax, ay] = route[i];
    const [bx, by] = route[i + 1];
    const len = Math.hypot(bx - ax, by - ay);
    if (left <= len && len > 0) {
      const f = left / len;
      return [ax + f * (bx - ax), ay + f * (by - ay)];
    }
    left -= len;
  }
  return route[route.length - 1];
}

export function routeLength(route: [number, number][]): number {
  let s = 0;
  for (let i = 0; i + 1 < route.length; i++)
    s += Math.hypot(route[i + 1][0] - route[i][0], route[i + 1][1] - route[i][1]);
  return s;
}
