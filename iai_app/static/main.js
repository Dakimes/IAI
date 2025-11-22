document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('searchForm');
  const input = document.getElementById('companyInput');
  const modal = document.getElementById('pipelineModal');
  let stepTimer;

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = input.value.trim();
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

  function showModal() {
    if (modal) modal.classList.remove('hidden');
  }
  function hideModal() {
    if (modal) modal.classList.add('hidden');
  }
  function runSteps() {
    if (!modal) return;
    const steps = Array.from(modal.querySelectorAll('.pipeline-steps li'));
    let idx = 0;
    stepTimer = setInterval(() => {
      steps.forEach((el, i) => el.classList.toggle('active', i === idx % steps.length));
      idx += 1;
    }, 3000);
  }

  initRadar();
  decorateCards();
});

function initRadar() {
  const container = document.getElementById('radarContainer');
  const svg = document.getElementById('radar');
  if (!container || !svg) return;

  const axes = ['FSI', 'MPI', 'PTI', 'TMI', 'RRI', 'PI'];
  const values = axes.map(key => parseFloat(container.dataset[key.toLowerCase()]) || 0);
  const size = 320;
  const center = size / 2;
  const radius = 120;

  const rings = 5;
  const ns = 'http://www.w3.org/2000/svg';
  svg.innerHTML = '';

  for (let i = 1; i <= rings; i++) {
    const r = (radius / rings) * i;
    const circle = document.createElementNS(ns, 'circle');
    circle.setAttribute('cx', center);
    circle.setAttribute('cy', center);
    circle.setAttribute('r', r);
    circle.setAttribute('fill', 'none');
    circle.setAttribute('stroke', '#d8e2ff');
    svg.appendChild(circle);
  }

  const points = [];
  axes.forEach((axis, i) => {
    const angle = (Math.PI * 2 / axes.length) * i - Math.PI / 2;
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', center);
    line.setAttribute('y1', center);
    line.setAttribute('x2', center + radius * Math.cos(angle));
    line.setAttribute('y2', center + radius * Math.sin(angle));
    line.setAttribute('stroke', '#c3d2ff');
    svg.appendChild(line);

    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', center + (radius + 18) * Math.cos(angle));
    label.setAttribute('y', center + (radius + 18) * Math.sin(angle));
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('alignment-baseline', 'middle');
    label.setAttribute('font-size', '12');
    label.setAttribute('fill', '#0b1f3a');
    label.textContent = axis;
    svg.appendChild(label);

    const valueRadius = (values[i] / 10) * radius;
    points.push([
      center + valueRadius * Math.cos(angle),
      center + valueRadius * Math.sin(angle)
    ]);
  });

  const polygon = document.createElementNS(ns, 'polygon');
  polygon.setAttribute('points', points.map(p => p.join(',')).join(' '));
  polygon.setAttribute('fill', 'rgba(12,70,255,0.28)');
  polygon.setAttribute('stroke', '#0c46ff');
  polygon.setAttribute('stroke-width', '2');
  svg.appendChild(polygon);
}

function decorateCards() {
  const cards = document.querySelectorAll('.card');
  cards.forEach(card => {
    const score = parseFloat(card.dataset.score) || 0;
    const badge = card.querySelector('.badge');
    const progress = card.querySelector('.progress span');
    badge.textContent = labelForScore(score);
    progress.style.width = `${Math.min(Math.max(score * 10, 0), 100)}%`;
  });
}

function labelForScore(score) {
  if (score >= 9) return 'топ';
  if (score >= 7) return 'выше среднего';
  if (score >= 5) return 'средний';
  if (score >= 3) return 'ниже среднего';
  return 'низкий';
}
