// Written with AI assistance (Claude Code). See AI_USE.md.
// Voice commands (PROMPT.md section 6): "distance home", "next station", "drop pin", through the
// Web Speech API where the browser supports it. The same commands have buttons, so nothing
// depends on speech.

export type Command = "distance-home" | "next-station" | "drop-pin";

const PATTERNS: [Command, RegExp][] = [
  ["distance-home", /\b(distance (to )?home|how far (is it )?(to )?home|home distance|way home)\b/],
  ["next-station", /\b(next (station|stop)|where (is )?next|what'?s next)\b/],
  ["drop-pin", /\b(drop (a )?pin|pin (it|here|this)|mark (it|here|this))\b/],
];

/** The command a spoken phrase asks for, or null for anything else. */
export function parseCommand(text: string): Command | null {
  const s = text.toLowerCase().replace(/[^a-z' ]+/g, " ").replace(/\s+/g, " ").trim();
  for (const [cmd, re] of PATTERNS) if (re.test(s)) return cmd;
  return null;
}

interface RecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

type RecognitionCtor = new () => RecognitionLike;

function ctor(win: unknown): RecognitionCtor | null {
  const w = win as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function speechSupported(win: unknown = typeof window !== "undefined" ? window : {}): boolean {
  return ctor(win) !== null;
}

/** Listen for commands until stopped; returns null where speech recognition is missing. */
export function listen(
  onCommand: (c: Command, heard: string) => void,
  onHeard: (heard: string) => void,
  win: unknown = window,
): (() => void) | null {
  const C = ctor(win);
  if (!C) return null;
  const rec = new C();
  rec.continuous = true;
  rec.interimResults = false;
  rec.lang = "en-US";
  let stopped = false;
  rec.onresult = (e) => {
    const last = e.results[e.results.length - 1];
    const heard = last?.[0]?.transcript ?? "";
    const c = parseCommand(heard);
    if (c) onCommand(c, heard);
    else onHeard(heard);
  };
  rec.onend = () => {
    if (!stopped) rec.start();
  };
  rec.start();
  return () => {
    stopped = true;
    rec.stop();
  };
}

/** Speak a response where speech synthesis exists (the same text is also shown on screen). */
export function speak(text: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}
