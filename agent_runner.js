#!/usr/bin/env node
/**
 * agent_runner.js
 * CLI & Agentic Bridge to AppController in ctf-tool
 * Allows Antigravity, terminal scripts, and automated agents to directly control the workbench.
 */

const fs = require('fs');
const path = require('path');

const STATE_FILE = path.join(__dirname, 'workbench_state.json');

// 1. Setup mock browser DOM & Storage environment
const storageMock = {};
if (fs.existsSync(STATE_FILE)) {
  try {
    const loaded = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
    Object.assign(storageMock, loaded);
  } catch (e) {}
}

global.localStorage = {
  getItem: (k) => storageMock[k] || null,
  setItem: (k, v) => {
    storageMock[k] = String(v);
    try {
      fs.writeFileSync(STATE_FILE, JSON.stringify(storageMock, null, 2), 'utf-8');
    } catch (e) {}
  },
  removeItem: (k) => {
    delete storageMock[k];
    try {
      fs.writeFileSync(STATE_FILE, JSON.stringify(storageMock, null, 2), 'utf-8');
    } catch (e) {}
  },
  clear: () => {
    Object.keys(storageMock).forEach(k => delete storageMock[k]);
    try {
      fs.writeFileSync(STATE_FILE, JSON.stringify(storageMock, null, 2), 'utf-8');
    } catch (e) {}
  }
};

const elements = {};
function createMockElement(id, tag = 'div') {
  return {
    id: id,
    tagName: tag.toUpperCase(),
    value: '',
    textContent: '',
    innerHTML: '',
    style: {},
    className: '',
    classList: {
      add: () => {},
      remove: () => {},
      toggle: () => {},
      contains: () => false
    },
    addEventListener: () => {},
    setAttribute: () => {},
    getAttribute: () => '',
    appendChild: () => {},
    remove: () => {},
    querySelectorAll: () => [],
    querySelector: () => null,
    focus: () => {}
  };
}

global.document = {
  getElementById: (id) => {
    if (!elements[id]) elements[id] = createMockElement(id);
    return elements[id];
  },
  querySelectorAll: (selector) => [],
  querySelector: (selector) => null,
  createElement: (tag) => createMockElement('dyn_' + Math.random(), tag),
  addEventListener: () => {}
};

global.window = {
  crypto: { subtle: {} },
  addEventListener: () => {},
  document: global.document,
  localStorage: global.localStorage
};

global.showToast = (msg, type) => {
  console.log(`  [Toast] ${type ? `[${type.toUpperCase()}] ` : ''}${msg}`);
};

// 2. Load app.js and AppController
const appExports = require('./app.js');
const appCtrl = window.AppController;
const parseAndExecuteAiActions = appExports.parseAndExecuteAiActions;
const executeActionList = appExports.executeActionList;

if (typeof appExports.loadCluesFromStorage === 'function') appExports.loadCluesFromStorage();
if (typeof appExports.loadCrimeScenesFromStorage === 'function') appExports.loadCrimeScenesFromStorage();

function printUsage() {
  console.log(`
Usage:
  node agent_runner.js state                  - Print current workbench state (JSON)
  node agent_runner.js execute '<action_json>' - Execute an action list (JSON array)
  node agent_runner.js parse '<llm_reply>'     - Parse \`\`\`action blocks from text and execute
  node agent_runner.js clue --title "..." ...  - Add a clue directly
  node agent_runner.js crypto --cipher ... --text "..."
  node agent_runner.js lock --code "..."
  node agent_runner.js report
`);
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    printUsage();
    process.exit(0);
  }

  const cmd = args[0];

  if (cmd === 'state') {
    const state = appCtrl.getState();
    console.log(JSON.stringify(state, null, 2));
  } else if (cmd === 'execute') {
    let jsonStr = args[1];
    if (jsonStr && fs.existsSync(jsonStr)) {
      jsonStr = fs.readFileSync(jsonStr, 'utf-8');
    }
    if (!jsonStr) {
      console.error('Error: Action JSON string or file path is required.');
      process.exit(1);
    }
    try {
      const actions = JSON.parse(jsonStr);
      const actionList = Array.isArray(actions) ? actions : [actions];
      const results = executeActionList(actionList);
      console.log(JSON.stringify({ success: true, results }, null, 2));
    } catch (e) {
      console.error('Error executing actions:', e.message);
      process.exit(1);
    }
  } else if (cmd === 'parse' || cmd === 'parse-file') {
    let text = '';
    if (args[1] && fs.existsSync(args[1])) {
      text = fs.readFileSync(args[1], 'utf-8');
    } else {
      text = args.slice(1).join(' ');
    }
    if (!text) {
      console.error('Error: LLM reply text or file path is required.');
      process.exit(1);
    }
    const { cleanText, actionsToRun } = parseAndExecuteAiActions(text);
    console.log('[Clean Text Response]:\n' + cleanText + '\n');
    console.log(`[Extracted Actions: ${actionsToRun.length}건]:`);
    const results = executeActionList(actionsToRun);
    console.log(JSON.stringify(results, null, 2));
  } else if (cmd === 'crypto') {
    let cipher = 'base64_decode';
    let text = '';
    for (let i = 1; i < args.length; i++) {
      if (args[i] === '--cipher' && args[i + 1]) cipher = args[++i];
      else if (args[i] === '--text' && args[i + 1]) text = args[++i];
    }
    const res = appCtrl.runCrypto({ text, cipher });
    console.log(JSON.stringify(res, null, 2));
  } else if (cmd === 'lock') {
    let code = '';
    for (let i = 1; i < args.length; i++) {
      if (args[i] === '--code' && args[i + 1]) code = args[++i];
      else if (!code) code = args[i];
    }
    const res = appCtrl.invertLock({ code });
    console.log(JSON.stringify(res, null, 2));
  } else if (cmd === 'report') {
    appCtrl.generateReport();
    const penalty = appCtrl.runPenaltyDefenseCheck();
    console.log('=== 수사보고서 미리보기 ===');
    console.log(document.getElementById('report-preview-text').value);
    console.log('\n=== 감점 방어 검사 결과 ===');
    console.log(JSON.stringify(penalty, null, 2));
  } else {
    printUsage();
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  appCtrl,
  parseAndExecuteAiActions,
  executeActionList
};
