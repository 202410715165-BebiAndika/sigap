(() => {
  const search = document.getElementById('student-search');
  if (search) {
    const rows = [...document.querySelectorAll('[data-student-row]')];
    const names = rows.map(row => row.textContent.toLocaleLowerCase('id'));
    let page = 0;
    const size = 12;
    const previous = document.getElementById('previous-page');
    const next = document.getElementById('next-page');
    const render = () => {
      const query = search.value.trim().toLocaleLowerCase('id');
      const matching = rows.filter((row, index) => names[index].includes(query));
      const pages = Math.max(1, Math.ceil(matching.length / size));
      page = Math.min(page, pages - 1);
      rows.forEach(row => {row.hidden = true;});
      matching.slice(page * size, (page + 1) * size).forEach(row => {row.hidden = false;});
      document.getElementById('student-empty').hidden = matching.length !== 0;
      document.getElementById('student-range').textContent = matching.length
        ? `${page * size + 1}–${Math.min((page + 1) * size, matching.length)} dari ${matching.length} mahasiswa`
        : '0 mahasiswa ditemukan';
      document.getElementById('student-pagination').hidden = matching.length <= size;
      document.getElementById('page-label').textContent = `${page + 1} / ${pages}`;
      previous.disabled = page === 0;
      next.disabled = page === pages - 1;
    };
    search.addEventListener('input', () => {page = 0; render();});
    previous.addEventListener('click', () => {page--; render();});
    next.addEventListener('click', () => {page++; render();});
    render();
  }
  document.querySelectorAll('[data-busy-form]').forEach(form => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('button[type="submit"]');
      if (button) {button.disabled = true; button.textContent = button.dataset.busyLabel || 'Menyimpan…';}
    });
  });
  const taken = document.querySelector('[name="sks_diambil"]');
  const passed = document.querySelector('[name="sks_lulus"]');
  if (taken && passed) {
    const validate = () => passed.setCustomValidity(Number(passed.value) > Number(taken.value) ? 'SKS lulus tidak boleh melebihi SKS yang diambil.' : '');
    taken.addEventListener('input', validate);
    passed.addEventListener('input', validate);
  }
})();
