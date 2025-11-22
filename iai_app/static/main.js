document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('searchForm');
  const input = document.getElementById('companyInput');
  const modal = document.getElementById('pipelineModal');
  let stepTimer;

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = (input?.value || '').trim();
      if (!name) return;
      showModal();
      runSteps();
      fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(({ status, body }) => {
          clearInterval(stepTimer);
          if (status === 200 && (body.status === 'exists' || body.status === 'created')) {
            window.location = `/company/${body.slug}`;
          } else {
            hideModal();
            alert(body.message || 'Ошибка анализа');
          }
        })
        .catch(() => {
          clearInterval(stepTimer);
          hideModal();
          alert('Ошибка сети или сервера');
        });
    });
  }

  function showModal() { modal?.classList.remove('hidden'); }
  function hideModal() { modal?.classList.add('hidden'); }

  function runSteps() {
    if (!modal) return;
    const nodes = Array.from(modal.querySelectorAll('.node'));
    let idx = 0;
    nodes.forEach((n, i) => n.classList.toggle('active', i === 0));
    stepTimer = setInterval(() => {
      nodes.forEach((n, i) => n.classList.toggle('active', i === idx % nodes.length));
      idx += 1;
    }, 1600);
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
