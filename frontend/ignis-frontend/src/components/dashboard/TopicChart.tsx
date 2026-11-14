"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/**
 * Horizontal bar chart: number of indexed records per topic.
 * Plan rule: every chart needs a title, axis labels, units and a short
 * explanation of what is counted (see the caption below).
 */
export function TopicChart({ data }: { data: { label: string; count: number }[] }) {
  return (
    <figure className="panel p-4">
      <figcaption className="mb-3">
        <p className="font-medium">Indexed records by research topic</p>
        <p className="text-xs text-space-400">
          Counts investigations in the indexed PSI subset that carry each topic tag. One record can have several tags.
        </p>
      </figcaption>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 24, right: 16, bottom: 20 }}>
            <CartesianGrid stroke="#182641" horizontal={false} />
            <XAxis type="number" allowDecimals={false} stroke="#7d8db0" label={{ value: "Number of records", position: "insideBottom", offset: -10, fill: "#a5b2cf", fontSize: 12 }} />
            <YAxis type="category" dataKey="label" width={170} stroke="#a5b2cf" fontSize={12} />
            <Tooltip contentStyle={{ background: "#0f1a30", border: "1px solid #26375a" }} cursor={{ fill: "#182641" }} />
            <Bar dataKey="count" name="Records" fill="#6bb8f5" radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
