"use client";

import { useEffect, useState } from "react";
import { getClients } from "@/lib/api";
import type { ClientItem } from "@/lib/types";

const STORAGE_KEY = "tb_client_id";

interface ClientSwitcherProps {
  onClientChange: (clientId: string, simulationToday: string) => void;
}

export function ClientSwitcher({ onClientChange }: ClientSwitcherProps) {
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [simToday, setSimToday] = useState<string>("");
  const [selected, setSelected] = useState<string>("");

  useEffect(() => {
    getClients().then(({ clients, simulation_today }) => {
      setClients(clients);
      setSimToday(simulation_today);
      const saved = localStorage.getItem(STORAGE_KEY) ?? clients[0]?.id ?? "";
      setSelected(saved);
      onClientChange(saved, simulation_today);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (id: string) => {
    setSelected(id);
    localStorage.setItem(STORAGE_KEY, id);
    onClientChange(id, simToday);
  };

  if (!clients.length) return null;

  return (
    <select
      value={selected}
      onChange={(e) => handleChange(e.target.value)}
      className="text-sm bg-tb-surface-2 border border-tb-border rounded-tb-md px-3 py-1.5 text-tb-text-primary focus:outline-none focus:ring-2 focus:ring-tb-accent max-w-[200px] truncate"
    >
      {clients.map(({ id, label }) => (
        <option key={id} value={id}>
          {label}
        </option>
      ))}
    </select>
  );
}
