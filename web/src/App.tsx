// Written with AI assistance (Claude Code). See AI_USE.md.
// The app shell: a slim mission bar (wordmark, site, scenario clock, Earth light-time, storm
// replay, judge tour, project links), an icon rail for the surfaces, and the main canvas. A short
// intro overlays the live map on the first visit; the judge tour walks the surfaces in eight steps.
import {
  ClipboardCheck,
  Info,
  Map as MapIcon,
  PlayCircle,
  Printer,
  ScanEye,
  Tablet,
  Zap,
} from "lucide-react";
import { type KeyboardEvent, lazy, Suspense, useEffect, useRef, useState } from "react";
import Mark from "./brand/Mark";
import { endTime } from "./core/eva/sim";
import { getEva, runClock, useEva } from "./core/eva/store";
import { LIGHT_TIME_SOURCE, lightTimeAt, solClock } from "./core/lighttime";
import { loadSite, useSite } from "./core/site";
import { startReplay } from "./eva/replay";
import { AI_USE_URL, CREDITS_URL, REPO_URL } from "./links";
import LabelBadge from "./planner/LabelBadge";
import Planner from "./planner/Planner";
import type { Plan } from "./planner/types";
import ValidationView from "./validation/ValidationView";

const VisorHud = lazy(() => import("./hud/VisorHud"));
const CuffTablet = lazy(() => import("./tablet/CuffTablet"));
const CuffCard = lazy(() => import("./card/CuffCard"));
const About = lazy(() => import("./about/About"));

const TABS = [
  { id: "planner", title: "Habitat Planner", Icon: MapIcon },
  { id: "hud", title: "Visor HUD", Icon: ScanEye },
  { id: "tablet", title: "Cuff Tablet", Icon: Tablet },
  { id: "card", title: "Cuff card", Icon: Printer },
  { id: "validation", title: "Validation", Icon: ClipboardCheck },
  { id: "about", title: "About", Icon: Info },
] as const;
export type TabId = (typeof TABS)[number]["id"];

const INTRO_KEY = "ariadne-intro-dismissed";

function readDismissed(): boolean {
  try {
    return window.localStorage.getItem(INTRO_KEY) === "1";
  } catch {
    return false;
  }
}

function writeDismissed() {
  try {
    window.localStorage.setItem(INTRO_KEY, "1");
  } catch {
    // private windows and blocked storage: the intro simply shows again next time
  }
}

function panel(id: TabId) {
  switch (id) {
    case "planner":
      return <Planner />;
    case "hud":
      return <VisorHud />;
    case "tablet":
      return <CuffTablet />;
    case "card":
      return <CuffCard />;
    case "about":
      return <About />;
    default:
      return <ValidationView />;
  }
}

/** The one clock for the simulated EVA, whichever surface is showing. */
function EvaClock() {
  useEffect(() => {
    let plans: Record<string, Plan> | null = null;
    loadSite("boxwork").then((s) => (plans = s.plans)).catch(() => {});
    return runClock(() => {
      const p = plans?.[getEva().preset];
      return p ? endTime(p) : 0;
    });
  }, []);
  return null;
}

function MissionBar({ onTab, onTour }: { onTab: (id: TabId) => void; onTour: () => void }) {
  const { site } = useSite();
  const eva = useEva();
  const plan = site?.plans[eva.preset];
  const clock = plan ? solClock(plan.scenario.start_note, eva.t) : null;
  const start = plan?.scenario.start_utc ? Date.parse(plan.scenario.start_utc) : NaN;
  const lt = eva.replay && site?.replay
    ? site.replay.light_time_min.value
    : Number.isFinite(start) ? lightTimeAt(new Date(start + eva.t * 60e3)) : null;
  return (
    <header className="mission-bar">
      <div className="wordmark">
        <Mark size={24} variant="glyph" className="wordmark-mark" />
        <h1 className="wordmark-name">ARIADNE</h1>
        <span className="tag">A thread home on Mars</span>
      </div>
      <div className="bar-meta">
        <span className="optional">Gale crater · Mount Sharp boxwork</span>
        {clock && (
          <span>
            Sol <span className="num">{clock.sol}</span> · <span className="num">{clock.hhmm}</span> LTST{" "}
            <LabelBadge label="PLACEHOLDER" source={`${plan?.scenario.start_note ?? ""}; advanced at the mean solar rate`} />
          </span>
        )}
        {lt !== null && (
          <span>
            Earth <span className="num">{lt.toFixed(1)}</span> light-min{" "}
            <LabelBadge label="DERIVED" source={eva.replay ? "JPL Horizons at the May 20, 2024 onset" : LIGHT_TIME_SOURCE} />
          </span>
        )}
      </div>
      <div className="bar-actions">
        {site?.replay && (
          <button
            type="button"
            onClick={() => {
              onTab("hud");
              startReplay(site.replay!, getEva().preset);
            }}
          >
            <Zap size={15} aria-hidden="true" /> Storm replay
          </button>
        )}
        <button type="button" onClick={onTour}>
          <PlayCircle size={15} aria-hidden="true" /> Judge tour
        </button>
        <nav aria-label="Project links">
          <h2 className="visually-hidden">Project links</h2>
          <ul className="links">
            <li>
              <a href={REPO_URL}>Source code</a>
            </li>
            <li>
              <a href={AI_USE_URL}>How we use SI</a>
            </li>
            <li>
              <a href={CREDITS_URL}>Credits</a>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}

function Intro({ onTour, onClose }: { onTour: () => void; onClose: () => void }) {
  const { site } = useSite();
  const first = useRef<HTMLButtonElement>(null);
  useEffect(() => first.current?.focus(), []);
  const r = site?.replay;
  const bal = site?.plans.balanced;
  return (
    <div className="intro" role="dialog" aria-modal="true" aria-labelledby="intro-title"
      onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <div className="intro-card">
        <Mark size={56} className="intro-mark" />
        <p className="kicker">NASA Space Apps 2026 · Interplanetary Survival Guide: Martian Map</p>
        <h2 id="intro-title">A thread home on Mars</h2>
        <p>
          ARIADNE plans, rehearses and guards a two-astronaut Marswalk through the boxwork ridges of
          Mount Sharp in Gale crater, keeping a safe way back to the rover at every step. It is built
          from openly published NASA and USGS data, and every number it shows is labeled as measured,
          derived, modeled or placeholder.
        </p>
        {r && bal && (
          <ul className="intro-facts">
            <li>
              <span className="num">{bal.totals.transects} transects</span>
              in {Math.round(bal.totals.minutes)} min, Balanced route <LabelBadge label="MODELED" source="ariadne plan" />
            </li>
            <li>
              <span className="num">{r.rad_dose_uGy.value.toLocaleString("en-US")} µGy</span>
              RAD, May 20, 2024 storm <LabelBadge label={r.rad_dose_uGy.label} source={`${r.rad_dose_uGy.meaning}. ${r.rad_dose_uGy.source}`} />
            </li>
            <li>
              <span className="num">{r.light_time_min.value.toFixed(1)} min</span>
              to Earth at light speed <LabelBadge label={r.light_time_min.label} source={r.light_time_min.source} />
            </li>
          </ul>
        )}
        <div className="intro-actions">
          <button ref={first} type="button" className="primary" onClick={onTour}>
            <PlayCircle size={16} aria-hidden="true" /> Start the 3-minute judge tour
          </button>
          <button type="button" onClick={onClose}>
            Explore
          </button>
        </div>
      </div>
    </div>
  );
}

interface TourStep {
  tab: TabId;
  title: string;
  text: string;
  view?: "map" | "3d";
  replay?: boolean;
}

const TOUR: TourStep[] = [
  { tab: "planner", view: "map", title: "The story", text: "In 1971 Apollo 14's moonwalkers turned back short of Cone Crater's rim. ARIADNE plans a Mars walk that always keeps a way home: the thread." },
  { tab: "planner", view: "map", title: "Layers from NASA data", text: "Each layer on the left shows its source, resolution, date and label. Turn on walkability or shielding to see what the planner sees." },
  { tab: "planner", view: "map", title: "Three plans", text: "Safest, Balanced and Most science, side by side on the right, with the price of safety. Every point keeps enough air to walk back to the rover." },
  { tab: "planner", view: "3d", title: "Rehearse in 3D", text: "Walk the route at eye height past Curiosity's own photos, placed where they were taken." },
  { tab: "hud", title: "The visor", text: "Never more than four things at once, in white and cyan, each with its own shape, checked against colour blindness." },
  { tab: "hud", replay: true, title: "May 20, 2024: storm replay", text: "A real solar storm starts mid-walk. The alert comes on cue and both walkers head for the rover; Curiosity's measured dose sits beside the modeled ones." },
  { tab: "validation", title: "Validation", text: "Every check, including the one that failed: slope from orbit is too cautious in the boxwork, so the planner stays conservative and says so." },
  { tab: "about", title: "Site 2 and the data", text: "The same pipeline built the Murray Buttes site, where the radiation shielding is calibrated. Every source is listed with its credit." },
];

function Tour({ step, onStep, onClose }: { step: number; onStep: (n: number) => void; onClose: () => void }) {
  const s = TOUR[step];
  return (
    <section className="tour" aria-label="Judge tour" aria-live="polite">
      <p className="step">Judge tour · step {step + 1} of {TOUR.length}</p>
      <h2>{s.title}</h2>
      <p>{s.text}</p>
      <div className="tour-actions">
        <button type="button" onClick={onClose}>End tour</button>
        <button type="button" disabled={step === 0} onClick={() => onStep(step - 1)}>Back</button>
        {step < TOUR.length - 1 ? (
          <button type="button" className="primary" onClick={() => onStep(step + 1)}>Next</button>
        ) : (
          <button type="button" className="primary" onClick={onClose}>Finish</button>
        )}
      </div>
    </section>
  );
}

export default function App() {
  const [active, setActive] = useState<TabId>("planner");
  const [seen, setSeen] = useState<Set<TabId>>(new Set(["planner"]));
  const [intro, setIntro] = useState(() => !readDismissed());
  const [tour, setTour] = useState<number | null>(null);
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const open = (id: TabId) => {
    setActive(id);
    setSeen((s) => new Set(s).add(id));
  };
  const goStep = (n: number) => {
    const s = TOUR[n];
    setTour(n);
    open(s.tab);
    if (s.view) window.dispatchEvent(new CustomEvent("ariadne:planner-view", { detail: s.view }));
    if (s.replay) loadSite("boxwork").then((site) => site.replay && startReplay(site.replay, getEva().preset)).catch(() => {});
  };
  const closeIntro = () => {
    writeDismissed();
    setIntro(false);
  };
  const startTour = () => {
    closeIntro();
    goStep(0);
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = TABS.findIndex((t) => t.id === active);
    const next =
      e.key === "ArrowDown" || e.key === "ArrowRight" ? (i + 1) % TABS.length
      : e.key === "ArrowUp" || e.key === "ArrowLeft" ? (i - 1 + TABS.length) % TABS.length
      : e.key === "Home" ? 0
      : e.key === "End" ? TABS.length - 1
      : -1;
    if (next < 0) return;
    e.preventDefault();
    open(TABS[next].id);
    refs.current[TABS[next].id]?.focus();
  };
  return (
    <div className="shell">
      <MissionBar onTab={open} onTour={startTour} />
      <div className="rail" role="tablist" aria-label="ARIADNE views" aria-orientation="vertical" onKeyDown={onKey}>
        {TABS.map(({ id, title, Icon }) => (
          <button
            key={id}
            ref={(el) => {
              refs.current[id] = el;
            }}
            type="button"
            role="tab"
            className="rail-tab"
            id={`tab-${id}`}
            aria-selected={active === id}
            aria-controls={`panel-${id}`}
            tabIndex={active === id ? 0 : -1}
            onClick={() => open(id)}
          >
            <Icon size={20} aria-hidden="true" />
            <span className="rail-tip">{title}</span>
          </button>
        ))}
      </div>
      <main className="canvas">
        <EvaClock />
        {TABS.map(({ id }) => (
          <div key={id} role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} hidden={active !== id}>
            {seen.has(id) && <Suspense fallback={<p role="status">Loading…</p>}>{panel(id)}</Suspense>}
          </div>
        ))}
        {intro && <Intro onTour={startTour} onClose={closeIntro} />}
        {tour !== null && <Tour step={tour} onStep={goStep} onClose={() => setTour(null)} />}
      </main>
      <footer className="footer">
        <p title="Code licensed under Apache-2.0. Concept and plan generated with Claude (claude.ai); software written with Claude Code (see How we use SI). Curiosity photos courtesy NASA/JPL-Caltech. No NASA logos are used. The ARIADNE mark was drawn as SVG code by Claude Code (no image generator); no other images are AI-made. All plans are modeled on placeholder settings and are not mission guidance.">
          Apache-2.0 · Concept and plan generated with Claude (claude.ai); software written with Claude Code · Curiosity photos courtesy NASA/JPL-Caltech · No NASA logos · Mark drawn as code by Claude Code; no other AI-made images · Plans are modeled on placeholder settings, not mission guidance
        </p>
      </footer>
    </div>
  );
}
