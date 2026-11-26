"use client";
import { useCallback, useEffect, useState } from "react";
import { BASE, DashboardData } from "@/lib/types";
export function useTelemetry(initial: DashboardData) {
  const [data, setData] = useState(initial),
    [apiOnline, setApiOnline] = useState(true),
    [socketOnline, setSocketOnline] = useState(false),
    [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setData(initial);
  }, [initial]);
  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const results = await Promise.all(
        ["/api/overview", "/api/readings?limit=200", "/api/v1/devices", "/api/lixeiras"].map(
          (p) =>
            fetch(BASE + p, {
              cache: "no-store",
              signal: signal || AbortSignal.timeout(10000),
            }),
        ),
      );
      if (results.some((r) => r.status === 401)) {
        window.location.assign(BASE + "/login");
        return;
      }
      if (results.some((r) => !r.ok)) throw Error();
      const [summary, readings, devices, bins] = await Promise.all(
        results.map((r) => r.json()),
      );
      if (!signal?.aborted) {
        setData({ summary, readings, devices, bins: bins.items });
        setApiOnline(true);
      }
    } catch {
      if (!signal?.aborted) setApiOnline(false);
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    let socket: WebSocket | undefined,
      timer: ReturnType<typeof setTimeout>,
      backoff = 1000,
      disposed = false;
    const connect = () => {
      if (disposed) return;
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}${BASE}/ws`,
      );
      socket.onopen = () => {
        setSocketOnline(true);
        backoff = 1000;
        void refresh(controller.signal);
      };
      socket.onmessage = () => void refresh(controller.signal);
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        setSocketOnline(false);
        if (!disposed) {
          timer = setTimeout(connect, backoff);
          backoff = Math.min(backoff * 2, 30000);
        }
      };
    };
    connect();
    setNow(Date.now());
    const interval = setInterval(() => {
      setNow(Date.now());
      if (socket?.readyState === WebSocket.OPEN) socket.send("ping");
    }, 10000);
    const polling = setInterval(() => void refresh(controller.signal), 30000);
    return () => {
      disposed = true;
      controller.abort();
      clearInterval(interval);
      clearInterval(polling);
      clearTimeout(timer);
      socket?.close();
    };
  }, [refresh]);
  const latest = data.summary.latest;
  const fresh =
    apiOnline &&
    now !== null &&
    !!latest &&
    latest.data_current !== false &&
    now - Date.parse(latest.timestamp) < 60000;
  return { data, apiOnline, socketOnline, fresh, refresh };
}
