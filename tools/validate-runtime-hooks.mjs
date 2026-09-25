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
requirePattern(/current <= 0/, "Edge spend no longer blocks zero/negative Edge.");
requirePattern(/No Edge to spend\./, "No-Edge warning is missing.");
requirePattern(/ChatMessage\.create\(/, "Edge spend chat announcement is missing.");
requirePattern(/spends 1 Edge\./, "Edge spend chat announcement semantics changed.");

if (!/registerCybermancyHooks\(\)/.test(main)) {
  failures.push("scripts/main.js no longer registers Cybermancy runtime hooks.");
}

// Exercise the installed action so helper extraction and optional-call syntax
// do not create false failures in a source-text regex.
const originals = Object.fromEntries(
  ["Hooks", "ChatMessage", "game", "ui"].map(key => [key, globalThis[key]])
);
try {
  const registrations = [];
  const announcements = [];
  const warnings = [];
  const flagCalls = [];
  let balance = 2;
  const actor = {
    name: "Test Runner",
    getFlag(scope, key) {
      flagCalls.push(["get", scope, key]);
      return balance;
    },
    async setFlag(scope, key, value) {
      flagCalls.push(["set", scope, key, value]);
      balance = value;
    }
  };
  globalThis.Hooks = { on: (name, callback) => registrations.push([name, callback]) };
  globalThis.ChatMessage = { create: async data => announcements.push(data) };
  globalThis.game = { user: { character: actor } };
  globalThis.ui = { notifications: { warn: message => warnings.push(message) } };

  const { registerCybermancyHooks } = await import(
    `data:text/javascript,${encodeURIComponent(hooks)}`
  );
  registerCybermancyHooks();
  if (registrations.length !== 1 || registrations[0][0] !== "getChatMessageContextOptions") {
    failures.push("Edge context option is not registered through the Foundry 14 hook.");
  } else {
    const options = [];
    registrations[0][1](null, options);
    const spend = options.find(option => option.name === "Spend 1 Edge");
    if (!spend || !spend.condition() || typeof spend.callback !== "function") {
      failures.push("Spend 1 Edge option is unavailable to the assigned character.");
    } else {
      await spend.callback(null);
      if (balance !== 1 ||
          !flagCalls.some(call => call.join("/") === "get/cybermancy/edge") ||
          !flagCalls.some(call => call.join("/") === "set/cybermancy/edge/1")) {
        failures.push("Edge spend must read flags.cybermancy.edge and decrement it by 1.");
      }
      if (announcements.length !== 1 || !announcements[0].content.includes("spends 1 Edge.")) {
        failures.push("Successful Edge spend must announce the action once.");
      }

      balance = 0;
      await spend.callback(null);
      if (balance !== 0 || announcements.length !== 1 ||
          warnings.length !== 1 || warnings[0] !== "No Edge to spend.") {
        failures.push("Zero Edge must warn without decrementing or announcing.");
      }

      globalThis.game.user.character = null;
      if (spend.condition()) failures.push("Edge spend must require an assigned character.");
    }
  }
} catch (error) {
  failures.push(`Edge context behavior could not be validated: ${error.message}`);
} finally {
  for (const [key, value] of Object.entries(originals)) {
    if (value === undefined) delete globalThis[key];
    else globalThis[key] = value;
  }
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
