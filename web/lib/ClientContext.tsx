"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { getClients } from "@/lib/api";
import type { ClientItem } from "@/lib/types";

interface ClientContextValue {
  clientId: string;
  simulationToday: string;
  clients: ClientItem[];
  setClient: (id: string) => void;
}

const ClientContext = createContext<ClientContextValue>({
  clientId: "",
  simulationToday: "",
  clients: [],
  setClient: () => {},
});

// Demo clients shown in the switcher — in display order with friendly names.
const DEMO_CLIENTS: Record<string, string> = {
  scripted_01: "Алексей",
  scripted_03: "Марина",
  scripted_04: "Дмитрий",
  scripted_10: "Семья Ивановых",
};
const DEMO_ORDER = ["scripted_01", "scripted_03", "scripted_04", "scripted_10"];
const DEFAULT_CLIENT = "scripted_01";

export function ClientProvider({ children }: { children: ReactNode }) {
  const [clientId, setClientId] = useState("");
  const [simulationToday, setSimulationToday] = useState("");
  const [clients, setClients] = useState<ClientItem[]>([]);

  useEffect(() => {
    getClients().then(({ clients: all, simulation_today }) => {
      // Show only the curated demo clients in fixed order with friendly names.
      const allIds = new Set(all.map((c) => c.id));
      const demoClients = DEMO_ORDER
        .filter((id) => allIds.has(id))
        .map((id) => ({ id, label: DEMO_CLIENTS[id] }));

      setClients(demoClients);
      setSimulationToday(simulation_today);

      const saved = localStorage.getItem("tb_client_id");
      const valid = saved && demoClients.find((c) => c.id === saved);
      const id = valid ? saved : DEFAULT_CLIENT;
      setClientId(id);
      localStorage.setItem("tb_client_id", id);
    });
  }, []);

  const setClient = (id: string) => {
    setClientId(id);
    localStorage.setItem("tb_client_id", id);
  };

  return (
    <ClientContext.Provider value={{ clientId, simulationToday, clients, setClient }}>
      {children}
    </ClientContext.Provider>
  );
}

export function useClient() {
  return useContext(ClientContext);
}
