import { useCallback, useEffect, useRef, useState } from "react";

export interface Poll<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => void;
}

export function usePoll<T>(
  fn: () => Promise<T>,
  intervalMs: number,
  opts: { key?: string; enabled?: boolean } = {},
): Poll<T> {
  const { key, enabled = true } = opts;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const load = useCallback(async () => {
    try {
      const d = await fnRef.current();
      setData(d);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const run = async () => {
      if (!alive) return;
      await load();
    };
    run();
    const timer = enabled ? setInterval(run, intervalMs) : null;
    return () => {
      alive = false;
      if (timer) clearInterval(timer);
    };
  }, [load, intervalMs, key, enabled]);

  return { data, error, loading, refresh: load };
}
