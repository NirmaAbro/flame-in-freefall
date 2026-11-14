"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ComparableParameter } from "@/lib/types";

/**
 * One chart per parameter that 2+ records report with the SAME name and unit.
 * The backend decides what is comparable; this component never converts units.
 */
export function ComparableChart({ parameter }: { parameter: ComparableParameter }) {
  return (
    <figure className="panel p-4">
      <figcaption className="mb-3">
        <p className="font-medium">{parameter.name}</p>
        <p className="text-xs text-space-400">Values exactly as reported in each record. Unit: {parameter.unit}.</p>
      </figcaption>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={parameter.values} margin={{ bottom: 24, left: 8 }}>
            <CartesianGrid stroke="#182641" vertical={false} />
            <XAxis dataKey="label" stroke="#a5b2cf" label={{ value: "Investigation", position: "insideBottom", offset: -12, fill: "#a5b2cf", fontSize: 12 }} />
            <YAxis stroke="#7d8db0" label={{ value: parameter.unit, angle: -90, position: "insideLeft", fill: "#a5b2cf", fontSize: 12 }} />
            <Tooltip contentStyle={{ background: "#0f1a30", border: "1px solid #26375a" }} cursor={{ fill: "#182641" }} />
            <Bar dataKey="value" name={parameter.unit} fill="#ff9650" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
