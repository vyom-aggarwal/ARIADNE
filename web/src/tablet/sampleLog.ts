// Written with AI assistance (Claude Code). See AI_USE.md.
// The sample log (PROMPT.md section 6): entries with a note and a photo, stored only in this
// browser (IndexedDB), so it works offline. Nothing is sent anywhere. Where IndexedDB is missing
// (as in unit tests) the log lives in memory for the session.

export interface SampleEntry {
  id: string;
  created_utc: string;
  mission_min: number;
  station: string | null;
  preset: string;
  note: string;
  photo: Blob | null;
}

const DB = "ariadne-samples";
const STORE = "entries";

export interface SampleLog {
  add(e: SampleEntry): Promise<void>;
  all(): Promise<SampleEntry[]>;
  remove(id: string): Promise<void>;
}

function memoryLog(): SampleLog {
  const m = new Map<string, SampleEntry>();
  return {
    add: async (e) => void m.set(e.id, e),
    all: async () => [...m.values()].sort((a, b) => a.created_utc.localeCompare(b.created_utc)),
    remove: async (id) => void m.delete(id),
  };
}

function req<T>(r: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}

function idbLog(idb: IDBFactory): SampleLog {
  const open = new Promise<IDBDatabase>((resolve, reject) => {
    const r = idb.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(STORE, { keyPath: "id" });
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
  const store = async (mode: IDBTransactionMode) => (await open).transaction(STORE, mode).objectStore(STORE);
  return {
    add: async (e) => void (await req((await store("readwrite")).put(e))),
    all: async () => {
      const rows = (await req((await store("readonly")).getAll())) as SampleEntry[];
      return rows.sort((a, b) => a.created_utc.localeCompare(b.created_utc));
    },
    remove: async (id) => void (await req((await store("readwrite")).delete(id))),
  };
}

let shared: SampleLog | null = null;

export function sampleLog(): SampleLog {
  if (!shared) {
    try {
      shared = typeof indexedDB !== "undefined" ? idbLog(indexedDB) : memoryLog();
    } catch {
      shared = memoryLog();
    }
  }
  return shared;
}

export function newId(): string {
  return `s${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}
