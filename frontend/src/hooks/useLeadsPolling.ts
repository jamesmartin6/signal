import { useCallback, useEffect, useRef, useState } from "react";
import { fetchLeads } from "../api/client";
import type { Lead } from "../types/lead";

const IN_FLIGHT_STATUSES = new Set(["pending", "extracting", "classifying", "enriching", "routing"]);

export function useLeadsPolling(intervalMs = 1500) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  const poll = useCallback(async () => {
    try {
      const page = await fetchLeads();
      if (!mountedRef.current) return;
      setLeads(page.items);
      setError(null);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err instanceof Error ? err.message : "Failed to load leads");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void poll();
    const timer = window.setInterval(() => void poll(), intervalMs);
    return () => {
      mountedRef.current = false;
      window.clearInterval(timer);
    };
  }, [poll, intervalMs]);

  const anyInFlight = leads.some((lead) => IN_FLIGHT_STATUSES.has(lead.status));

  return { leads, error, loading, anyInFlight, refetch: poll };
}
