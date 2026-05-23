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

export function ClientProvider({ children }: { children: ReactNode }) {
  const [clientId, setClientId] = useState("");
  const [simulationToday, setSimulationToday] = useState("");
  const [clients, setClients] = useState<ClientItem[]>([]);

  useEffect(() => {
    getClients().then(({ clients, simulation_today }) => {
      setClients(clients);
      setSimulationToday(simulation_today);
      const saved = localStorage.getItem("tb_client_id");
      const valid = saved && clients.find((c) => c.id === saved);
      const id = valid ? saved : (clients[0]?.id ?? "");
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
