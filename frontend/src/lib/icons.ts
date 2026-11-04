import { createLucideIcon } from "lucide-react";

/** The Coach: a light bulb drawn on a clipboard. Same grid and stroke as the Lucide set. */
export const CoachIcon = createLucideIcon("Coach", [
  ["rect", { x: "8", y: "2", width: "8", height: "4", rx: "1", key: "clip" }],
  ["path", { d: "M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2", key: "board" }],
  ["path", { d: "M10.25 15.5c0-1.1-1.75-2-1.75-3.75a3.5 3.5 0 0 1 7 0c0 1.75-1.75 2.65-1.75 3.75", key: "bulb" }],
  ["path", { d: "M10.25 15.5h3.5", key: "neck" }],
  ["path", { d: "M10.75 18.5h2.5", key: "base" }],
]);
