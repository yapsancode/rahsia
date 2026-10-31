// Section entrances play once. Content stays visible if this script fails,
// because the hidden state only applies under html.js.
const seen = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add('in');
      seen.unobserve(entry.target);
    }
  },
  { threshold: 0.15 },
);

document.querySelectorAll('.columns, .mosaic').forEach((group) => {
  group.querySelectorAll('.reveal').forEach((item, i) => item.style.setProperty('--stagger', `${i * 80}ms`));
});
document.querySelectorAll('.how-steps .reveal').forEach((item, i) => item.style.setProperty('--stagger', `${i * 80}ms`));
document.querySelectorAll('.reveal, .how-diagram').forEach((item) => seen.observe(item));

// The match demo: a plain comparison of fake choices in the browser.
// The real check is a PSI run between two laptops, not this code.
const form = document.getElementById('check');
const verdict = document.getElementById('verdict');
const verdictText = document.getElementById('verdict-text');
const seekerLearned = document.getElementById('seeker-learned');
const providerLearned = document.getElementById('provider-learned');
const fieldsShown = document.getElementById('fields-shown');
const overlap = document.getElementById('overlap');
const openButton = document.getElementById('open');
const resetButton = document.getElementById('reset');

const tabs = [
  { tab: document.getElementById('tab-seeker'), panel: document.getElementById('panel-seeker') },
  { tab: document.getElementById('tab-provider'), panel: document.getElementById('panel-provider') },
];

function showTab(active) {
  for (const { tab, panel } of tabs) {
    const on = tab === active;
    tab.setAttribute('aria-selected', String(on));
    panel.hidden = !on;
  }
}

tabs.forEach(({ tab }) => tab.addEventListener('click', () => showTab(tab)));

const label = (name) => form.elements[name].selectedOptions[0].textContent;
const fits = (seeker, provider) => form.elements[provider].value.split(',').includes(form.elements[seeker].value);

function isMatch() {
  return fits('s-stage', 'p-stage') && fits('s-sector', 'p-sector') && fits('s-money', 'p-money');
}

function press() {
  verdict.classList.remove('pressed');
  void verdict.offsetWidth;
  verdict.classList.add('pressed');
}

function update() {
  const match = isMatch();
  const text = match ? 'Match' : 'No match';
  verdictText.textContent = text.toUpperCase();
  verdict.classList.toggle('is-match', match);
  seekerLearned.textContent = text;
  providerLearned.textContent = text;
  fieldsShown.textContent = '0';
  overlap.hidden = true;
  openButton.disabled = !match;
  press();
}

openButton.addEventListener('click', () => {
  fieldsShown.textContent = '3';
  overlap.textContent = `Overlap opened: ${label('s-stage')}, ${label('s-sector')}, ${label('s-money')}. Next: draft intro and receipt.`;
  overlap.hidden = false;
  openButton.disabled = true;
});

resetButton.addEventListener('click', () => {
  form.reset();
  showTab(tabs[0].tab);
  update();
});

form.addEventListener('change', update);
