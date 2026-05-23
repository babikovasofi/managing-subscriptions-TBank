"use client";

import { createContext, useContext, type ReactNode } from "react";

// Single fixed demo client — no switching needed.
const CLIENT_ID = "scripted_04";
const SIMULATION_TODAY = "2026-05-22";

interface ClientContextValue {
  clientId: string;
  simulationToday: string;
}

const ClientContext = createContext<ClientContextValue>({
  clientId: CLIENT_ID,
  simulationToday: SIMULATION_TODAY,
});

export function ClientProvider({ children }: { children: ReactNode }) {
  return (
    <ClientContext.Provider value={{ clientId: CLIENT_ID, simulationToday: SIMULATION_TODAY }}>
      {children}
    </ClientContext.Provider>
  );
}

export function useClient() {
  return useContext(ClientContext);
}
