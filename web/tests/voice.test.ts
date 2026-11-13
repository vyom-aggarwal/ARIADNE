// Written with AI assistance (Claude Code). See AI_USE.md.
// Test G4: voice commands are recognised from plain phrases and only where the browser has speech.
import { describe, expect, it, vi } from "vitest";
import { listen, parseCommand, speechSupported } from "../src/core/eva/voice";

describe("voice commands", () => {
  it("maps the three commands and close variants", () => {
    expect(parseCommand("Distance home")).toBe("distance-home");
    expect(parseCommand("how far is it to home?")).toBe("distance-home");
    expect(parseCommand("Next station.")).toBe("next-station");
    expect(parseCommand("what's next")).toBe("next-station");
    expect(parseCommand("drop pin")).toBe("drop-pin");
    expect(parseCommand("Drop a pin here")).toBe("drop-pin");
    expect(parseCommand("mark this")).toBe("drop-pin");
  });

  it("ignores anything else", () => {
    for (const s of ["", "hello", "station keeping", "pineapple", "homeward"]) expect(parseCommand(s)).toBeNull();
  });

  it("listens only where the browser supports speech recognition", () => {
    expect(speechSupported({})).toBe(false);
    expect(listen(() => {}, () => {}, {})).toBeNull();
    const started = vi.fn();
    class FakeRecognition {
      continuous = false;
      interimResults = false;
      lang = "";
      onresult: ((e: { results: { transcript: string }[][] }) => void) | null = null;
      onend: (() => void) | null = null;
      start() {
        started();
        fake = this;
      }
      stop() {}
    }
    let fake: FakeRecognition | null = null;
    const win = { webkitSpeechRecognition: FakeRecognition };
    expect(speechSupported(win)).toBe(true);
    const got: string[] = [];
    const stop = listen((c) => got.push(c), () => got.push("other"), win);
    expect(stop).toBeTypeOf("function");
    expect(started).toHaveBeenCalledOnce();
    fake!.onresult!({ results: [[{ transcript: "next station" }]] });
    fake!.onresult!({ results: [[{ transcript: "nice view" }]] });
    expect(got).toEqual(["next-station", "other"]);
    stop!();
  });
});
