import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const hooksPath = path.join(root, "scripts", "hooks.js");
const mainPath = path.join(root, "scripts", "main.js");

const hooks = fs.readFileSync(hooksPath, "utf8");
const main = fs.readFileSync(mainPath, "utf8");

const failures = [];
const requirePattern = (pattern, message) => {
  if (!pattern.test(hooks)) failures.push(message);
};
const rejectPattern = (pattern, message) => {
  if (pattern.test(hooks)) failures.push(message);
};

requirePattern(/Hooks\.on\(["']getChatMessageContextOptions["']/, "Foundry 14 ChatMessage context hook is not registered.");
rejectPattern(/getChatLogEntryContext/, "Legacy getChatLogEntryContext hook is still present.");
requirePattern(/name:\s*["']Spend 1 Edge["']/, "Spend 1 Edge context option is missing.");
requirePattern(/game\.user\.character/, "Edge spend no longer targets the user's assigned character.");
requirePattern(/getFlag\(EDGE_FLAG_SCOPE, EDGE_FLAG_KEY\)/, "Edge spend no longer reads flags.cybermancy.edge.");
requirePattern(/setFlag\(EDGE_FLAG_SCOPE, EDGE_FLAG_KEY, current - 1\)/, "Edge spend no longer decrements flags.cybermancy.edge by exactly 1.");
requirePattern(/current <= 0/, "Edge spend no longer blocks zero/negative Edge.");
requirePattern(/No Edge to spend\./, "No-Edge warning is missing.");
requirePattern(/ChatMessage\.create\(/, "Edge spend chat announcement is missing.");
requirePattern(/spends 1 Edge\./, "Edge spend chat announcement semantics changed.");

if (!/registerCybermancyHooks\(\)/.test(main)) {
  failures.push("scripts/main.js no longer registers Cybermancy runtime hooks.");
}

if (failures.length) {
  console.error("Cybermancy runtime hook validation FAILED:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Cybermancy runtime hook validation PASS");
console.log("- Foundry 14 getChatMessageContextOptions hook: PASS");
console.log("- legacy getChatLogEntryContext hook: absent");
console.log("- assigned-character Edge semantics: PASS");
console.log("- zero-Edge guard and warning: PASS");
console.log("- chat announcement: PASS");
