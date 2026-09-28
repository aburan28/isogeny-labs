'use strict';

// Shared footer and optional learning-page interactions.
const year = document.getElementById('year');
if (year) year.textContent = String(new Date().getFullYear());

// Progressive enhancement for the curve traits reference.
if (document.getElementById("trait-search")) {
const search = document.getElementById('trait-search');
const origin = document.getElementById('trait-origin');
const traits = [...document.querySelectorAll('.trait')];
document.getElementById('filters').hidden = false;
function filterTraits() {
  const query = search.value.trim().toLocaleLowerCase();
  let count = 0;
  for (const trait of traits) {
    const matches = (origin.value === 'all' || trait.dataset.origin === origin.value) && trait.textContent.toLocaleLowerCase().includes(query);
    trait.hidden = !matches;
    count += Number(matches);
  }
  document.getElementById('trait-count').textContent = `${count} of 30 topics`;
  document.getElementById('no-results').hidden = count !== 0;
}
function resetFilters() { search.value = ''; origin.value = 'all'; filterTraits(); }
search.addEventListener('input', filterTraits);
origin.addEventListener('change', filterTraits);
document.getElementById('reset-traits').addEventListener('click', () => { resetFilters(); search.focus(); });
function revealLinkedTrait() {
  const trait = traits.find(item => `#${item.id}` === location.hash);
  if (trait) { resetFilters(); trait.open = true; trait.scrollIntoView({block: 'start'}); }
}
window.addEventListener('hashchange', revealLinkedTrait);
revealLinkedTrait();

}
