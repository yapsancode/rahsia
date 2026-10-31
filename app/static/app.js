// One page, six steps. All text from the server goes in with textContent, never as HTML.
const $ = (id) => document.getElementById(id);

const NAMES = {
  funding: 'Funding', invest: 'Invest', partner: 'Partner', mentor: 'Mentor', hire_team: 'Hire the team',
  idea: 'Idea', 'pre-seed': 'Pre-seed', seed: 'Seed', 'series-a': 'Series A',
  agritech: 'Agritech', fintech: 'Fintech', logistics: 'Logistics', healthtech: 'Healthtech', edtech: 'Edtech',
  other: 'Other',
  'under-100k': 'Under RM100k', '100k-250k': 'RM100k to 250k', '250k-500k': 'RM250k to 500k',
  '500k-1m': 'RM500k to 1m', 'over-1m': 'Over RM1m',
  malaysia: 'Malaysia', singapore: 'Singapore', indonesia: 'Indonesia', thailand: 'Thailand',
  vietnam: 'Vietnam', philippines: 'Philippines', 'other-asean': 'Other ASEAN',
};
const FIELD_NAMES = { stage: 'Stage', sector: 'Sector', money_rm: 'Money', geography: 'Geography' };
const SAMPLE_NAMES = { seeker_en: 'English', seeker_mixed_injection: 'Mixed, with a hidden instruction', provider_ms: 'Malay' };
const SCREENS = ['side', 'notes', 'profile', 'match', 'share', 'receipt'];

const app = { config: null, side: null, profile: null, polling: null, buildTimer: null, shownPhase: null };

async function api(path, body) {
  const options = body === undefined
    ? { method: path === '/api/config' || path === '/api/state' ? 'GET' : 'POST' }
    : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error('The app has stopped. Start it again in the terminal.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Something went wrong (${response.status}).`);
  return data;
}

function show(name, focus = true) {
  SCREENS.forEach((screen) => { $(`s-${screen}`).hidden = screen !== name; });
  window.scrollTo(0, 0);
  if (focus) $('main').focus({ preventScroll: true });
}

function setStep(now) {
  [...$('steps').children].forEach((item, index) => {
    const number = index + 1;
    item.classList.toggle('now', number === now);
    item.classList.toggle('done', number < now);
    item.querySelector('.tick').textContent = number < now ? '✓' : number;
    if (number === now) item.setAttribute('aria-current', 'step');
    else item.removeAttribute('aria-current');
  });
}

function setError(id, message) {
  $(id).textContent = message || '';
  $(id).hidden = !message;
}

function button(label, onClick, primary = false) {
  const element = document.createElement('button');
  element.type = 'button';
  element.className = primary ? 'btn primary' : 'btn';
  element.textContent = label;
  element.addEventListener('click', onClick);
  return element;
}

/* Choose a side */

function chooseSide(side) {
  app.side = side;
  $('who').textContent = side === 'seeker' ? 'Startup laptop' : 'Investor laptop';
  const samples = $('samples');
  samples.replaceChildren();
  const list = app.config.samples[side];
  if (list.length) samples.append('Try a fake note:');
  list.forEach((sample) => {
    const link = document.createElement('button');
    link.type = 'button';
    link.className = 'link';
    link.textContent = SAMPLE_NAMES[sample.name] || sample.name;
    link.addEventListener('click', () => { $('notes').value = sample.text; setError('notes-error'); });
    samples.append(link);
  });
  $('notes').placeholder = side === 'seeker'
    ? 'kami buat sensor utk kebun sawit, tengah pre-seed. nak raise around RM300k…'
    : 'We write cheques of RM200k to RM500k, pre-seed to seed only…';
  setStep(1);
  show('notes');
  $('notes').focus();
}

/* Notes to profile */

async function buildProfile() {
  const notes = $('notes').value;
  if (!notes.trim()) {
    setError('notes-error', 'Write your notes first.');
    $('notes').focus();
    return;
  }
  setError('notes-error');
  const started = performance.now();
  const label = $('build-label');
  $('build').disabled = true;
  $('notes').readOnly = true;
  $('scanbox').classList.add('busy');
  app.buildTimer = setInterval(() => {
    label.textContent = `Gemma is reading… ${((performance.now() - started) / 1000).toFixed(1)}s`;
  }, 100);
  label.textContent = 'Gemma is reading…';
  try {
    const result = await api('/api/profile', { notes, side: app.side });
    if (!result.profile) {
      setError('notes-error', `Gemma could not build a valid profile. ${result.errors.join(' ')}`);
      return;
    }
    showProfile(result, notes);
  } catch (error) {
    setError('notes-error', error.message);
  } finally {
    clearInterval(app.buildTimer);
    label.textContent = 'Build profile';
    $('build').disabled = false;
    $('notes').readOnly = false;
    $('scanbox').classList.remove('busy');
  }
}

function showProfile(result, notes) {
  app.profile = result.profile;
  $('profile-lead').textContent = `Built in ${result.seconds} seconds on this laptop. Fix anything that is wrong.`;
  $('source-text').textContent = notes;

  const injected = result.warnings.filter((w) => w.includes('looks like an instruction'));
  const others = result.warnings.filter((w) => !w.includes('looks like an instruction'));
  $('injection').hidden = injected.length === 0;
  $('injection-text').textContent = injected.length
    ? 'A line in the notes tried to give the AI orders. Code cut it out before Gemma read the notes.'
    : '';
  $('checks').hidden = others.length === 0;
  $('checks-title').textContent = `${others.length} ${others.length === 1 ? 'fix' : 'fixes'} made in code`;
  $('checks-list').replaceChildren(...others.map((text) => {
    const item = document.createElement('li');
    item.textContent = text;
    return item;
  }));

  renderForm();
  setError('profile-error');
  setStep(2);
  show('profile');
}

function row(name, control, isBlank) {
  const wrap = document.createElement('div');
  wrap.className = 'row';
  const title = document.createElement('div');
  title.className = 'row-name';
  title.textContent = name;
  if (isBlank) {
    const blank = document.createElement('span');
    blank.className = 'blank';
    blank.textContent = 'Blank: no match';
    title.append(blank);
  }
  wrap.append(title, control);
  return wrap;
}

function chips(values, selected, onToggle, label) {
  const group = document.createElement('div');
  group.className = 'chips';
  group.setAttribute('role', 'group');
  group.setAttribute('aria-label', label);
  values.forEach((value) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'chip';
    chip.textContent = NAMES[value] || value;
    chip.setAttribute('aria-pressed', String(selected.includes(value)));
    chip.addEventListener('click', () => onToggle(value));
    group.append(chip);
  });
  return group;
}

function textInput(name, label, value, type = 'text') {
  const input = document.createElement('input');
  input.type = type;
  input.value = value ?? '';
  input.setAttribute('aria-label', label);
  if (type === 'text') input.maxLength = app.config.limits.text;
  else { input.min = 1; input.max = 60; input.step = 1; }
  input.addEventListener('input', () => {
    if (type === 'text') app.profile[name] = input.value;
    else app.profile[name] = input.value === '' ? null : Number(input.value);
  });
  return input;
}

function renderForm() {
  const { choices } = app.config;
  const profile = app.profile;
  const form = $('form');
  const refocus = document.activeElement?.textContent;
  const toggleList = (name) => (value) => {
    const list = profile[name];
    profile[name] = list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
    renderForm();
  };
  const intentLabel = app.side === 'seeker' ? 'Looking for' : 'Offering';
  const pickIntent = (value) => {
    profile.intent = profile.intent === value ? null : value;
    renderForm();
  };
  form.replaceChildren(
    row(intentLabel, chips(choices[`${app.side}_intent`], profile.intent ? [profile.intent] : [], pickIntent, intentLabel), !profile.intent),
    ...['stage', 'sector', 'money_rm', 'geography'].map((name) => row(
      FIELD_NAMES[name] + (name === 'money_rm' ? ' (RM)' : ''),
      chips(choices[name], profile[name], toggleList(name), FIELD_NAMES[name]),
      profile[name].length === 0,
    )),
    row('Timeline', monthsInput(), false),
    row('Deal breakers', textInput('deal_breakers', 'Deal breakers', profile.deal_breakers), false),
    row('Disclosure', textInput('disclosure', 'Disclosure', profile.disclosure), false),
  );
  if (refocus) [...form.querySelectorAll('.chip')].find((chip) => chip.textContent === refocus)?.focus();
}

function monthsInput() {
  const wrap = document.createElement('div');
  wrap.style.display = 'flex';
  wrap.style.alignItems = 'center';
  wrap.style.gap = '10px';
  wrap.append(textInput('timeline_months', 'Timeline in months', app.profile.timeline_months, 'number'), 'months');
  return wrap;
}

/* Match */

const VAULT = { checking: 'vault checking', match: 'vault match', nomatch: 'vault nomatch' };

function matchWords() {
  return app.config.engine.private ? 'Private match check' : 'Match check';
}

function setMatchScreen({ step, eyebrow, title, lead, vault, zero = false, actions = [] }) {
  setStep(step);
  $('match-eyebrow').textContent = eyebrow;
  $('h-match').textContent = title;
  $('match-lead').textContent = lead;
  $('vault').className = VAULT[vault];
  $('zero').hidden = !zero;
  $('match-actions').replaceChildren(...actions);
}

async function confirmProfile() {
  setError('profile-error');
  try {
    await api('/api/match', { profile: app.profile });
  } catch (error) {
    setError('profile-error', error.message);
    return;
  }
  $('sq-you').textContent = app.side === 'seeker' ? 'Startup' : 'Investor';
  $('sq-them').textContent = app.side === 'seeker' ? 'Investor' : 'Startup';
  $('stand-in').hidden = app.config.engine.private;
  setError('match-error');
  app.shownPhase = null;
  show('match');
  drawPhase({ phase: 'matching' });
  startPolling();
}

function startPolling() {
  stopPolling();
  app.polling = setInterval(async () => {
    try {
      drawPhase(await api('/api/state'));
    } catch (error) {
      stopPolling();
      setError('match-error', error.message);
    }
  }, 500);
}

function stopPolling() {
  clearInterval(app.polling);
  app.polling = null;
}

function drawPhase(state) {
  if (state.phase === app.shownPhase) return;
  app.shownPhase = state.phase;
  const startOver = () => button('Start a new check', restart);

  if (state.phase === 'matching') {
    setMatchScreen({
      step: 3, eyebrow: `Step 3 · ${matchWords()}`, title: 'Checking with the other laptop',
      lead: 'Your profile stays here. Each side learns one thing only: match or no match.',
      vault: 'checking', actions: [button('Cancel', restart)],
    });
  } else if (state.phase === 'no_match') {
    stopPolling();
    setMatchScreen({
      step: 3, eyebrow: `Step 3 · ${matchWords()}`, title: 'No match.',
      lead: 'Nothing else is shown, on either side. You will not see why, and they will not see your profile.',
      vault: 'nomatch', zero: true, actions: [startOver()],
    });
  } else if (state.phase === 'matched') {
    stopPolling();
    setMatchScreen({
      step: 4, eyebrow: 'Step 4 · Both agree', title: 'It’s a match.',
      lead: 'Nothing has been shared yet. The overlap appears only if both sides press agree.',
      vault: 'match', actions: [button('Agree to share the overlap', agree, true), button('Decline', decline)],
    });
  } else if (state.phase === 'agreeing') {
    setMatchScreen({
      step: 4, eyebrow: 'Step 4 · Both agree', title: 'Waiting for the other side',
      lead: 'You agreed. The overlap appears when they agree too.',
      vault: 'match', actions: [button('Cancel', restart)],
    });
  } else if (state.phase === 'declined') {
    stopPolling();
    setMatchScreen({
      step: 4, eyebrow: 'Step 4 · Both agree', title: 'They declined.',
      lead: 'Nothing was shared, on either side.',
      vault: 'nomatch', zero: true, actions: [startOver()],
    });
  } else if (state.phase === 'revealed') {
    stopPolling();
    showOverlap(state.overlap);
  } else if (state.phase === 'error') {
    stopPolling();
    setMatchScreen({
      step: 3, eyebrow: `Step 3 · ${matchWords()}`, title: 'The check did not finish.',
      lead: 'Nothing was shared.', vault: 'nomatch',
      actions: [button('Try again', confirmProfile, true), button('Back to profile', backToProfile)],
    });
    setError('match-error', state.error);
  }
}

async function agree() {
  try {
    await api('/api/agree');
    drawPhase({ phase: 'agreeing' });
    startPolling();
  } catch (error) {
    setError('match-error', error.message);
  }
}

async function decline() {
  try {
    await api('/api/decline');
    drawPhase({ phase: 'declined' });
    $('h-match').textContent = 'You declined.';
  } catch (error) {
    setError('match-error', error.message);
  }
}

async function backToProfile() {
  await api('/api/reset').catch(() => {});
  setStep(2);
  show('profile');
}

/* Overlap and draft */

function showOverlap(overlap) {
  const fields = Object.entries(overlap).filter(([, values]) => values.length);
  $('overlap-count').textContent = `${fields.length} fields shared`;
  $('overlap').replaceChildren(...fields.map(([name, values], index) => {
    const tile = document.createElement('div');
    tile.className = 'tile';
    tile.style.animationDelay = `${index * 70}ms`;
    const label = document.createElement('span');
    label.className = 'tile-name';
    label.textContent = FIELD_NAMES[name] || name;
    const value = document.createElement('span');
    value.className = 'tile-value';
    value.textContent = values.map((v) => NAMES[v] || v).join(', ');
    tile.append(label, value);
    return tile;
  }));
  setError('share-error');
  setStep(5);
  show('share');
  writeDraft();
}

async function writeDraft() {
  const started = performance.now();
  const hint = $('draft-hint');
  $('draft').value = '';
  $('draft').readOnly = true;
  $('draft-box').classList.add('busy');
  $('save-receipt').disabled = true;
  const timer = setInterval(() => {
    hint.textContent = `Gemma is writing… ${((performance.now() - started) / 1000).toFixed(1)}s`;
  }, 100);
  try {
    const draft = await api('/api/draft');
    $('draft').value = draft.text;
    hint.textContent = draft.source === 'gemma'
      ? `Written by Gemma in ${draft.seconds} seconds, then checked in code. You can edit it.`
      : `Gemma’s draft failed the check, so this one was built from the overlap in code. You can edit it.`;
  } catch (error) {
    hint.textContent = '';
    setError('share-error', error.message);
  } finally {
    clearInterval(timer);
    $('draft').readOnly = false;
    $('draft-box').classList.remove('busy');
    $('save-receipt').disabled = false;
  }
}

async function copyDraft() {
  const label = $('copy-draft');
  try {
    await navigator.clipboard.writeText($('draft').value);
    label.textContent = 'Copied';
  } catch {
    $('draft').select();
    label.textContent = 'Press Ctrl+C to copy';
  }
  setTimeout(() => { label.textContent = 'Copy draft'; }, 2000);
}

/* Receipt */

async function saveReceipt() {
  try {
    showReceipt(await api('/api/receipt'));
  } catch (error) {
    setError('share-error', error.message);
  }
}

function showReceipt(receipt) {
  const signed = Boolean(receipt.signature);
  const shared = Object.entries(receipt.fields_shared).filter(([, values]) => values.length);
  const rows = [
    ['Shared', shared.map(([name]) => FIELD_NAMES[name] || name).join(', ') || 'Nothing', false],
    ['Other party', receipt.other_party, false],
    ['Time', new Date(receipt.time).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }), false],
    ['Hash', receipt.hash, true],
    ['Signature', receipt.signature || 'Not signed yet', Boolean(receipt.signature)],
    ['File', receipt.file, true],
  ];
  $('receipt-rows').replaceChildren(...rows.map(([name, value, mono]) => {
    const wrap = document.createElement('div');
    const term = document.createElement('dt');
    term.textContent = name;
    const detail = document.createElement('dd');
    detail.textContent = value;
    if (mono) detail.className = 'mono';
    wrap.append(term, detail);
    return wrap;
  }));
  $('r-signed').textContent = signed ? 'Signed' : 'Not signed yet';
  $('r-signed').className = signed ? 'tag good' : 'tag';
  setStep(7);
  [...$('steps').children].at(-1).classList.add('done');
  show('receipt');
}

/* Start and restart */

async function restart() {
  stopPolling();
  await api('/api/reset').catch(() => {});
  app.profile = null;
  app.shownPhase = null;
  $('notes').value = '';
  setError('notes-error');
  setStep(1);
  show('notes');
}

async function start() {
  try {
    app.config = await api('/api/config');
    await api('/api/reset');
  } catch (error) {
    $('st-gemma').textContent = error.message;
    return;
  }
  const { engine, model, gemma_ready: ready } = app.config;
  $('st-gemma').textContent = ready ? model : 'Gemma is not running';
  $('st-gemma').classList.toggle('bad', !ready);
  $('st-engine').textContent = engine.private ? 'Private (PSI)' : 'Stand-in, not private';
  $('st-engine').classList.toggle('bad', !engine.private);
  $('step-match').textContent = matchWords();
}

document.querySelectorAll('[data-side]').forEach((card) => {
  card.addEventListener('click', () => { if (app.config) chooseSide(card.dataset.side); });
});
$('build').addEventListener('click', buildProfile);
$('notes').addEventListener('input', () => setError('notes-error'));
$('notes').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) buildProfile();
});
$('confirm').addEventListener('click', confirmProfile);
$('back-notes').addEventListener('click', () => { setStep(1); show('notes'); });
$('form').addEventListener('submit', (event) => event.preventDefault());
$('save-receipt').addEventListener('click', saveReceipt);
$('copy-draft').addEventListener('click', copyDraft);
$('again').addEventListener('click', restart);

start();
