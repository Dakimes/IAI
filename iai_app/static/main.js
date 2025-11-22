document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('searchForm');
  const input = document.getElementById('companyInput');
  const modal = document.getElementById('pipelineModal');
  const steps = modal ? Array.from(modal.querySelectorAll('.step')) : [];

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = (input?.value || '').trim();
      if (!name) return;
      resetPipeline();
      showModal();
      fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      })
        .then(res => safeParseResponse(res))
        .then(({ status, body }) => {
          setStepState('search', 'done');
          setStepState('scoring', 'active');
          setPipelineHint(body.status === 'exists' ? 'Карточка уже готова, открываем...' : 'Расчёт индекса завершён, формируем карточку');
          setTimeout(() => setStepState('scoring', 'done'), 150);
          setTimeout(() => setStepState('aggregation', 'done'), 300);
          setTimeout(() => setStepState('card', 'done'), 450);
          if (status === 200 && (body.status === 'exists' || body.status === 'created')) {
            window.location = `/company/${body.slug}`;
          } else {
            setStepState('aggregation', 'error');
            setPipelineHint(body.message || 'Не удалось завершить расчёт');
            hideModal();
            alert(body.message || 'Ошибка анализа');
          }
        })
        .catch(() => {
          setStepState('search', 'error');
          setPipelineHint('Ошибка сети или сервера');
          hideModal();
          alert('Ошибка сети или сервера');
        });
    });
  }

  function showModal() { modal?.classList.remove('hidden'); }
  function hideModal() { modal?.classList.add('hidden'); }

  function resetPipeline() {
    if (!steps.length) return;
    steps.forEach((node, idx) => {
      const key = node.dataset.step;
      const state = idx === 0 ? 'active' : 'pending';
      setStepState(key, state);
    });
    setPipelineHint('Ищем источники и факты через web-search...');
  }

  function setStepState(key, state) {
    const node = steps.find(n => n.dataset.step === key);
    if (!node) return;
    node.dataset.state = state;
  }

  function setPipelineHint(text) {
    const hint = modal?.querySelector('.pipeline-status');
    if (hint) hint.textContent = text;
  }

  async function safeParseResponse(res) {
    const raw = await res.text();
    let body = {};
    try {
      body = raw ? JSON.parse(raw) : {};
    } catch (err) {
      console.error('Не удалось распарсить ответ', err, raw);
    }
    return { status: res.status, body, raw };
  }

  if (modal) {
    resetPipeline();
  }

  renderRadar();
  decorateFactCards();
});

function renderRadar() {
  const svg = document.getElementById('radar');
  if (!svg) return;
  const axes = ['FSI', 'MPI', 'PTI', 'TMI', 'RRI', 'PI'];
  const values = axes.map(key => parseFloat(svg.dataset[key.toLowerCase()]) || 0);
  const ns = 'http://www.w3.org/2000/svg';
  svg.innerHTML = '';
  const size = 300;
  const center = size / 2;
  const radius = 110;
  const rings = 5;

  for (let k = 2; k <= 10; k += 2) {
    const ring = document.createElementNS(ns, 'polygon');
    const r = radius * (k / 10);
    ring.setAttribute('fill', 'none');
    ring.setAttribute('stroke', '#e5e7eb');
    ring.setAttribute('stroke-width', '1');
    ring.setAttribute('points', axes.map((_, i) => {
      const a = -Math.PI / 2 + i * 2 * Math.PI / axes.length;
      return `${center + r * Math.cos(a)},${center + r * Math.sin(a)}`;
    }).join(' '));
    svg.appendChild(ring);
  }

  axes.forEach((lab, i) => {
    const a = -Math.PI / 2 + i * 2 * Math.PI / axes.length;
    const x = center + radius * Math.cos(a);
    const y = center + radius * Math.sin(a);
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', center); line.setAttribute('y1', center);
    line.setAttribute('x2', x); line.setAttribute('y2', y);
    line.setAttribute('stroke', '#e5e7eb');
    svg.appendChild(line);

    const tx = document.createElementNS(ns, 'text');
    tx.setAttribute('x', center + (radius + 14) * Math.cos(a));
    tx.setAttribute('y', center + (radius + 14) * Math.sin(a));
    tx.setAttribute('text-anchor', 'middle');
    tx.setAttribute('dominant-baseline', 'middle');
    tx.setAttribute('font-size', '10');
    tx.setAttribute('fill', '#64748b');
    tx.textContent = lab;
    svg.appendChild(tx);
  });

  const polygon = document.createElementNS(ns, 'polygon');
  polygon.setAttribute('fill', '#0f172a22');
  polygon.setAttribute('stroke', '#0f172a');
  polygon.setAttribute('stroke-width', '2');
  polygon.setAttribute('points', values.map((val, i) => {
    const a = -Math.PI / 2 + i * 2 * Math.PI / axes.length;
    const rr = radius * (val / 10);
    return `${center + rr * Math.cos(a)},${center + rr * Math.sin(a)}`;
  }).join(' '));
  svg.appendChild(polygon);
}

function decorateFactCards() {
  const cards = document.querySelectorAll('.fact-card');
  cards.forEach(card => {
    const badge = card.querySelector('.badge');
    const score = parseFloat(card.dataset.score) || 0;
    if (badge) badge.textContent = labelForScore(score);
  });
}

function labelForScore(score) {
  if (score >= 9) return 'топ';
  if (score >= 7) return 'выше среднего';
  if (score >= 5) return 'средний';
  if (score >= 3) return 'ниже среднего';
  return 'низкий';
}
