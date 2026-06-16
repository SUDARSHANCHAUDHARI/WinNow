import { spawn } from "node:child_process";
import path from "node:path";
import { NextResponse } from "next/server";

const ENGINE = path.join(process.cwd(), "..", "engine", "winnow.py");
const TRENDS = path.join(process.cwd(), "..", "engine", "trends.py");
const DEMO_TOPIC = "Acme Notes";

export const runtime = "nodejs";
export const maxDuration = 60;

function run(script: string, args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn("python3", [script, ...args], { cwd: path.dirname(script) });
    let out = "";
    let err = "";
    proc.stdout.on("data", (d) => (out += d));
    proc.stderr.on("data", (d) => (err += d));
    proc.on("error", reject);
    proc.on("close", (code) => (code === 0 ? resolve(out) : reject(new Error(err || `exit ${code}`))));
  });
}

// POST /api/demo - seed the store with backdated runs, then return the demo
// brief + its trend. No network, no credentials: pure POC seed data.
export async function POST() {
  try {
    await run(ENGINE, ["--seed-store"]); // backdated runs for the trend chart
    const briefJson = await run(ENGINE, ["--demo", "--emit", "json"]);
    const trendJson = await run(TRENDS, [DEMO_TOPIC]);
    return NextResponse.json({
      brief: JSON.parse(briefJson),
      trend: JSON.parse(trendJson).series,
      topic: DEMO_TOPIC,
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "demo failed" },
      { status: 500 },
    );
  }
}
