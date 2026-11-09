// Written with AI assistance (Claude Code). See AI_USE.md.
// 3D rehearsal (PROMPT.md section 6): chunked terrain with two levels of detail and the image
// texture, the selected route, and Curiosity Navcam photos as billboards at their capture
// points, facing their view direction. Orbit or ground mode; on the ground the camera walks the
// route at eye height (PLACEHOLDER 1.7 m) at a chosen speed.
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import LabelBadge from "../planner/LabelBadge";
import type { Manifest, Plan } from "../planner/types";
import {
  billboardPose,
  eyePosition,
  groundHeight,
  type HeightGrid,
  lodLevel,
  pointAlong,
  routeLength,
  toLocal,
} from "./geometry";

interface Props {
  manifest: Manifest;
  base: string;
  plan: Plan | null;
}

const LOD_SWITCH_M = 450;
const BILLBOARD_AHEAD_M = 30;
const BILLBOARD_WIDTH_M = 18;

async function loadHeights(manifest: Manifest, base: string, level: "fine" | "coarse") {
  const t = manifest.terrain;
  const k = level === "fine" ? 1 : t.coarse_factor;
  let rows = 0;
  let cols = 0;
  for (const ch of t.chunks) {
    rows = Math.max(rows, Math.ceil(ch.rows_cols[2] / k));
    cols = Math.max(cols, Math.ceil(ch.rows_cols[3] / k));
  }
  const heights = new Float32Array(rows * cols);
  await Promise.all(
    t.chunks.map(async (ch) => {
      const buf = await (await fetch(base + ch.files[level])).arrayBuffer();
      const codes = new Uint16Array(buf);
      const [h, w] = ch.shapes[level];
      const r0 = Math.floor(ch.rows_cols[0] / k);
      const c0 = Math.floor(ch.rows_cols[1] / k);
      for (let r = 0; r < h; r++)
        for (let c = 0; c < w; c++)
          if (r0 + r < rows && c0 + c < cols)
            heights[(r0 + r) * cols + (c0 + c)] = t.z0 + codes[r * w + c] * t.scale;
    }),
  );
  return { heights, rows, cols, cell: t.resolution_m * k };
}

function chunkMesh(g: HeightGrid, r0: number, c0: number, r1: number, c1: number, zRef: number,
  material: THREE.Material, win: { west: number; north: number; width: number; height: number },
  centre: [number, number]) {
  const rows = Math.min(r1 + 1, g.rows) - r0;
  const cols = Math.min(c1 + 1, g.cols) - c0;
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(rows * cols * 3);
  const uv = new Float32Array(rows * cols * 2);
  for (let r = 0; r < rows; r++)
    for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      const x = g.west + (c0 + c) * g.cell;
      const z = g.north + (r0 + r) * g.cell;
      pos[3 * i] = x - centre[0];
      pos[3 * i + 1] = g.heights[(r0 + r) * g.cols + (c0 + c)] - zRef;
      pos[3 * i + 2] = z - centre[1];
      uv[2 * i] = (x - win.west) / win.width;
      uv[2 * i + 1] = 1 - (z - win.north) / win.height;
    }
  const index: number[] = [];
  for (let r = 0; r + 1 < rows; r++)
    for (let c = 0; c + 1 < cols; c++) {
      const a = r * cols + c;
      index.push(a, a + cols, a + 1, a + 1, a + cols, a + cols + 1);
    }
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  geo.setIndex(index);
  geo.computeVertexNormals();
  return new THREE.Mesh(geo, material);
}

export default function Rehearsal({ manifest, base, plan }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<"orbit" | "ground">("orbit");
  const [speed, setSpeed] = useState(5);
  const [playing, setPlaying] = useState(true);
  const [status, setStatus] = useState("Loading terrain…");
  const [billboards, setBillboards] = useState(0);
  const modeRef = useRef(mode);
  const speedRef = useRef(speed);
  const playRef = useRef(playing);
  modeRef.current = mode;
  speedRef.current = speed;
  playRef.current = playing;
  const eye = manifest.eye_height_m.value;

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch {
      setStatus("The 3D view needs WebGL, which this browser does not provide.");
      return;
    }
    let disposed = false;
    const width = el.clientWidth || 800;
    const height = el.clientHeight || 480;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    renderer.domElement.setAttribute("aria-hidden", "true");
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xc9a98a);
    scene.fog = new THREE.Fog(0xc9a98a, 1500, 4000);
    scene.add(new THREE.HemisphereLight(0xfff4e6, 0x6b4f3a, 1.4));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(-500, 800, -300);
    scene.add(sun);
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.5, 6000);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    const origin: [number, number] = [manifest.bounds_m[0], manifest.bounds_m[1]];
    const t = manifest.terrain;
    const [tw, ts, te, tn] = t.bounds_m;
    const nw = toLocal([tw, tn], origin);
    const win = { west: nw[0], north: nw[1], width: te - tw, height: tn - ts };
    const stage = toLocal(manifest.staging_xy_m, origin);
    let grid: HeightGrid | null = null;
    let zRef = 0;
    let route: [number, number][] = [];
    let walked = 0;
    let frame = 0;

    (async () => {
      const [fine, coarse] = await Promise.all([
        loadHeights(manifest, base, "fine"),
        loadHeights(manifest, base, "coarse"),
      ]);
      if (disposed) return;
      const gFine: HeightGrid = { ...fine, west: win.west + t.resolution_m / 2,
        north: win.north + t.resolution_m / 2 };
      const gCoarse: HeightGrid = { ...coarse, west: win.west + coarse.cell / 2,
        north: win.north + coarse.cell / 2 };
      grid = gFine;
      zRef = groundHeight(gFine, stage[0], stage[1]);
      const tex = new THREE.TextureLoader().load(base + t.texture);
      tex.colorSpace = THREE.SRGBColorSpace;
      const mat = new THREE.MeshLambertMaterial({ map: tex });
      const k = t.coarse_factor;
      for (const ch of t.chunks) {
        const [r0, c0, r1, c1] = ch.rows_cols;
        // each chunk sits at its own centre, so the level of detail follows its distance
        const centre: [number, number] = [gFine.west + ((c0 + c1) / 2) * gFine.cell,
          gFine.north + ((r0 + r1) / 2) * gFine.cell];
        const lod = new THREE.LOD();
        lod.addLevel(chunkMesh(gFine, r0, c0, r1, c1, zRef, mat, win, centre), 0);
        lod.addLevel(chunkMesh(gCoarse, r0 / k, c0 / k, Math.ceil(r1 / k), Math.ceil(c1 / k), zRef,
          mat, win, centre), LOD_SWITCH_M);
        lod.position.set(centre[0], 0, centre[1]);
        scene.add(lod);
      }
      // the route, lifted half a metre above the ground
      if (plan) {
        route = plan.legs.flatMap((l) => l.path_xy_m.map((p) => toLocal(p, origin)));
        const pts = route.map(([x, z]) => new THREE.Vector3(x, groundHeight(gFine, x, z) - zRef + 0.5, z));
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
          new THREE.LineBasicMaterial({ color: 0xffffff }));
        scene.add(line);
        for (const s of plan.stations) {
          const [x, z] = toLocal(s.xy_m, origin);
          const m = new THREE.Mesh(new THREE.ConeGeometry(1.2, 4, 12),
            new THREE.MeshLambertMaterial({ color: s.role === "wall" ? 0xcc79a7 : s.role === "hollow"
              ? 0x56b4e9 : 0x0072b2 }));
          m.position.set(x, groundHeight(gFine, x, z) - zRef + 2, z);
          scene.add(m);
        }
      }
      // photo billboards at their capture points, facing their view direction
      const loader = new THREE.TextureLoader();
      for (const ph of manifest.photos) {
        const cap = toLocal(ph.xy_m, origin);
        const pose = billboardPose(cap, ph.view_azimuth_deg, BILLBOARD_AHEAD_M);
        const ptex = loader.load(base + ph.file);
        ptex.colorSpace = THREE.SRGBColorSpace;
        ptex.repeat.set(1, ph.show_top_fraction);
        ptex.offset.set(0, 1 - ph.show_top_fraction);
        const h = BILLBOARD_WIDTH_M * ph.show_top_fraction;
        const board = new THREE.Mesh(new THREE.PlaneGeometry(BILLBOARD_WIDTH_M, h),
          new THREE.MeshBasicMaterial({ map: ptex, side: THREE.DoubleSide }));
        board.position.set(pose.x, groundHeight(gFine, pose.x, pose.z) - zRef + h / 2 + 2, pose.z);
        board.rotation.y = pose.rotationY;
        board.name = `photo-${ph.imageid}`;
        scene.add(board);
        const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 3),
          new THREE.MeshLambertMaterial({ color: 0xffffff }));
        pole.position.set(cap[0], groundHeight(gFine, cap[0], cap[1]) - zRef + 1.5, cap[1]);
        scene.add(pole);
      }
      setBillboards(manifest.photos.length);
      camera.position.set(stage[0] + 300, 350, stage[1] + 450);
      controls.target.set(stage[0], 0, stage[1]);
      setStatus("Ready");
    })().catch(() => setStatus("Could not load the terrain."));

    let last = performance.now();
    const loop = (now: number) => {
      if (disposed) return;
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      if (modeRef.current === "ground" && grid && route.length > 1) {
        controls.enabled = false;
        const total = routeLength(route);
        if (playRef.current) walked = (walked + dt * 1.0 * speedRef.current) % total;
        const [x, z] = pointAlong(route, walked);
        const [ax, az] = pointAlong(route, Math.min(total, walked + 8));
        const p = eyePosition(grid, x, z, eye);
        camera.position.set(p.x, p.y - zRef, p.z);
        camera.lookAt(ax, groundHeight(grid, ax, az) - zRef + eye, az);
      } else {
        controls.enabled = true;
        controls.update();
      }
      scene.traverse((o) => {
        if (o instanceof THREE.LOD) o.update(camera);
      });
      renderer.render(scene, camera);
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    const onResize = () => {
      const w = el.clientWidth || width;
      const h = el.clientHeight || height;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [manifest, base, plan, eye]);

  return (
    <section className="rehearsal" aria-labelledby="rehearsal-heading">
      <h2 id="rehearsal-heading">3D rehearsal</h2>
      <div className="rehearsal-controls" role="group" aria-label="3D view controls">
        <button type="button" aria-pressed={mode === "orbit"} onClick={() => setMode("orbit")}>Orbit</button>
        <button type="button" aria-pressed={mode === "ground"} onClick={() => setMode("ground")}>Ground</button>
        <button type="button" aria-pressed={!playing} onClick={() => setPlaying((p) => !p)}
          disabled={mode !== "ground"}>
          {playing ? "Pause walk" : "Resume walk"}
        </button>
        <label>
          Walking speed {speed}× <input type="range" min={1} max={30} value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))} aria-label="Walking speed multiplier" />
        </label>
      </div>
      <div ref={host} className="rehearsal-canvas" data-mode={mode} data-billboards={billboards}
        data-status={status} />
      <p className="note" role="status">
        {status === "Ready"
          ? `${billboards} Curiosity Navcam photos placed at their capture points (Courtesy NASA/JPL-Caltech). `
          : `${status} `}
        Eye height {eye} m <LabelBadge label={manifest.eye_height_m.label} source={manifest.eye_height_m.source} />.
        Terrain <LabelBadge label={manifest.terrain.label} source="USGS 1 m DEM and 25 cm orthophoto" />,
        levels of detail switch at {LOD_SWITCH_M} m ({lodLevel(0, LOD_SWITCH_M)} near, {lodLevel(1e9, LOD_SWITCH_M)} far).
      </p>
    </section>
  );
}
