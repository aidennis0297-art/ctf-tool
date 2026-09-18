// test_agent_tools.js
// Automated Integration Test Runner for CTF & Escape Room Toolkit v3.0 Agentic Tools

// 1. Setup mock browser DOM & Storage environment
const storageMock = {};
global.localStorage = {
  getItem: (k) => storageMock[k] || null,
  setItem: (k, v) => { storageMock[k] = String(v); },
  removeItem: (k) => { delete storageMock[k]; },
  clear: () => { Object.keys(storageMock).forEach(k => delete storageMock[k]); }
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

global.showToast = (msg, type) => {};

// 2. Load app.js and exported functions
const appExports = require('./app.js');
const appCtrl = window.AppController;
const parseAndExecuteAiActions = appExports.parseAndExecuteAiActions;
const executeActionList = appExports.executeActionList;

console.log('================================================================');
console.log('🤖 [CTF Workbench v3.0] AI 에이전트 내장 툴 조작 자동화 테스트');
console.log('================================================================\n');

let passCount = 0;
let totalTests = 0;

function assert(desc, condition) {
  totalTests++;
  if (condition) {
    console.log(`  ✅ [PASS] ${desc}`);
    passCount++;
  } else {
    console.error(`  ❌ [FAIL] ${desc}`);
  }
}

// Test 1: AppController.getState()
console.log('▶ [테스트 1] AppController.getState() 실시간 워크벤치 상태 쿼리');
const state1 = appCtrl.getState();
assert('기본 상태 객체 조회 성공', state1 && typeof state1 === 'object');
assert('5대 사건 현장 데이터 포함 확인', Array.isArray(state1.crimeScenes) && state1.crimeScenes.length === 5);
assert('15분 타이머 상태 포함 확인', state1.sceneTimer && typeof state1.sceneTimer.remainingSeconds === 'number');

// Test 2: switchTab
console.log('\n▶ [테스트 2] switchTab("investigation") 탭 전환 조작');
const tabRes = appCtrl.switchTab('investigation');
assert('수사추리보드 탭으로 전환 성공', tabRes.success && tabRes.activeTab === 'investigation');

// Test 3: addClue
console.log('\n▶ [테스트 3] addClue 수사 보드에 신규 단서 카드 등록');
const clueRes = appCtrl.addClue({
  title: '연구실 벽면 찢어진 메모',
  category: 'scenario',
  room: '자연과학관 103호',
  location: '칠판 뒤편 액자',
  assignee: '현장팀 1',
  solution: '4289',
  flagPart: 'SHA{lab_secret_',
  content: '벽면 액자 뒤에서 발견된 다이얼 비밀번호 메모',
  inference: '범인이 연구실 금고를 열기 위해 남겨둔 마스터 핀코드'
});
assert('단서 등록 성공', clueRes.success && clueRes.clue.title === '연구실 벽면 찢어진 메모');
assert('등록된 단서 속성(위치/방/플래그조각) 확인', clueRes.clue.room === '자연과학관 103호' && clueRes.clue.flagPart === 'SHA{lab_secret_');

// Test 4: runCrypto (Base64 Korean Decoding)
console.log('\n▶ [테스트 4] runCrypto Base64 한글 복호화 (67CY6rCR7Iq164uI64ukLiDrlpntgZB+)');
const b64Res = appCtrl.runCrypto({
  text: '67CY6rCR7Iq164uI64ukLiDrlpntgZB+',
  cipher: 'base64_decode'
});
assert('Base64 디코딩 실행 성공', b64Res.success);
assert('한글 UTF-8 정상 복원 ("반갑습니다. 떙큐~")', b64Res.result === '반갑습니다. 떙큐~');

// Test 5: runCrypto (Caesar Cipher All Shift)
console.log('\n▶ [테스트 5] runCrypto Caesar 암호 전수조사 (caesar_all)');
const caesarRes = appCtrl.runCrypto({
  text: 'Khoor',
  cipher: 'caesar_all'
});
assert('시저 25개 전수조사 생성 성공', caesarRes.success && caesarRes.result.includes('[Shift 23] Hello'));

// Test 6: invertLock (180° Inversion)
console.log('\n▶ [테스트 6] invertLock 공식 자물쇠 180° 상하 반전 (6890N ➔ u0689)');
const lockRes = appCtrl.invertLock({ code: '6890N' });
assert('180도 반전 분석 성공', lockRes.original === '6890N' && lockRes.inverted === 'u0689');
assert('완전 회전 가능(대칭 문자) 판정', lockRes.isStrictRotatable === true);

// Test 7: importDiscordNotes
console.log('\n▶ [테스트 7] importDiscordNotes 디스코드 수첩 메모 일괄 등록');
const discordRaw = `[현장 1 - 인문학관 201호]
- 단서: 의문의 책상 쪽지 / 위치: 서랍 안쪽 / 암호: 1984 / 플래그: SHA{humanities_vault_1984} / 추론: 1984년 설립일과 일치
- 단서: 벽면 액자 속 다이얼 / 위치: 액자 뒤편 / 정답: 1984 / 추론: 출입문 보조 잠금장치`;

const discordRes = appCtrl.importDiscordNotes({ text: discordRaw });
assert('디스코드 메모 파싱 및 일괄 등록 성공', discordRes.success && discordRes.addedCount === 2);

// Test 8: updateCrimeScene
console.log('\n▶ [테스트 8] updateCrimeScene 5대 사건현장 상태 & 1회 입장 규칙 설정');
const sceneRes = appCtrl.updateCrimeScene({
  index: 0,
  room: '인문학관 201호',
  flag: 'SHA{humanities_vault_1984}',
  entries: 1,
  hintUsed: false,
  status: 'solved'
});
assert('현장 1 상태 업데이트 성공', sceneRes.success && sceneRes.scene.flag === 'SHA{humanities_vault_1984}');
assert('단 1회 입장 규칙 준수 확인', sceneRes.scene.entries === 1 && sceneRes.scene.hintUsed === false);

// Test 9: controlSceneTimer
console.log('\n▶ [테스트 9] controlSceneTimer 15분 작전 타이머 제어');
const timerRes = appCtrl.controlSceneTimer({ action: 'start', seconds: 890 });
assert('15분 타이머 제어 성공', timerRes.success && timerRes.remaining === 890);
appCtrl.controlSceneTimer({ action: 'pause' });

// Test 10: generateReport & runPenaltyDefenseCheck
console.log('\n▶ [테스트 10] generateReport & runPenaltyDefenseCheck (제8조 3,000점 검증)');
appCtrl.generateReport({
  teamName: '시립수사대',
  members: '김철수, 이영희, 박민수',
  conclusion: '인문학관 201호 서랍에서 발견된 쪽지와 연구실 액자 속 비밀번호 4289를 종합하여 분석한 결과, 범인은 103호 서버실 백도어를 통해 도주하였음이 명백히 증명됨.'
});
const penaltyRes = appCtrl.runPenaltyDefenseCheck();
assert('제8조 감점 방어 사전 검사 실행 성공', penaltyRes && typeof penaltyRes.passed === 'boolean');
assert('팀명 및 40자 이상 추론 정상 통과', penaltyRes.passes.some(p => p.includes('시립수사대')));

// Test 11: setMemoText
console.log('\n▶ [테스트 11] setMemoText 메모장에 AI 작전 요약 기록');
const memoRes = appCtrl.setMemoText('# AI 수사관 작전 브리핑\n- 인문학관 201호 플래그 확보 완료\n- 자물쇠 반전 코드 u0689 확인됨', false);
assert('메모장 본문 기록 성공', memoRes.success && memoRes.length > 0);

// Test 12: parseAndExecuteAiActions (End-to-End LLM Action Block Parsing)
console.log('\n▶ [테스트 12] parseAndExecuteAiActions (LLM 응답 내 ```action 블록 자동 파싱 및 실행)');
const mockLlmResponse = `수사관님, 분석 결과를 안내해 드립니다.
180도 반전 코드와 새 단서를 보드에 등록하고 메모장에 기록하겠습니다.

\`\`\`action
[
  {
    "action": "addClue",
    "args": {
      "title": "LLM 자동 생성 단서",
      "category": "scenario",
      "room": "통제구역 404호",
      "location": "서버랙 3번",
      "solution": "9999",
      "flagPart": "SHA{server_pass}"
    }
  },
  {
    "action": "setMemoText",
    "args": {
      "text": "\\n\\n[AI 추가 브리핑] 404호 서버랙 플래그 SHA{server_pass} 확보",
      "append": true
    }
  }
]
\`\`\`

조치가 완료되었습니다.`;

const { cleanText, actionsToRun } = parseAndExecuteAiActions(mockLlmResponse);
assert('LLM 응답 텍스트에서 ```action 블록 분리 성공', !cleanText.includes('```action'));
assert('액션 블록 JSON 파싱 성공 (2건)', actionsToRun.length === 2);

const execResults = executeActionList(actionsToRun);
assert('액션 1 (addClue) 자동 실행 성공', execResults[0].success && execResults[0].action === 'addClue');
assert('액션 2 (setMemoText) 자동 실행 성공', execResults[1].success && execResults[1].action === 'setMemoText');

// Summary
console.log('\n================================================================');
console.log(`📊 테스트 결과: 총 ${totalTests}개 검증 중 ${passCount}개 통과 (성공률: ${Math.round((passCount / totalTests) * 100)}%)`);
console.log('================================================================\n');

if (passCount === totalTests) {
  console.log('🎉 모든 AI 에이전트 내장 툴 조작 테스트 완벽 통과!');
  process.exit(0);
} else {
  console.error('⚠️ 일부 테스트 실패!');
  process.exit(1);
}
