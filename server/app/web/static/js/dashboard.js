const themeToggle = document.getElementById('theme-toggle');
const liveRegion = document.getElementById('aria-live-region');
const refreshButton = document.getElementById('refresh-button');
const connectionBadge = document.getElementById('connection-badge');
const lastUpdatedEl = document.getElementById('last-updated');
const page = document.querySelector('[data-page]');

const state = {
  intervalId: null,
  retryDelay: 2000,
  pollMs: 2000,
  charts: {},
};

const notify = (message) => {
  if (liveRegion) {
    liveRegion.textContent = message;
  }
};

const updateConnectionState = (level) => {
  if (!connectionBadge) return;
  const map = {
    live: ['live', 'Live'],
    stale: ['stale', 'Stale'],
    offline: ['offline', 'Offline'],
  };
  const [className, label] = map[level] || map.live;
  connectionBadge.className = `status-badge ${className}`;
  connectionBadge.textContent = label;
};

const updateLastUpdated = () => {
  if (!lastUpdatedEl) return;
  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  lastUpdatedEl.textContent = `Last updated ${timestamp}`;
};

const fetchJson = async (url, options = {}) => {
  const response = await fetch(url, { headers: { Accept: 'application/json', ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(payload.error || 'Request failed');
  }
  return response.headers.get('content-type')?.includes('application/json') ? response.json() : response.text();
};

const isoToLocal = (value) => {
  if (!value) return '--';
  return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const renderSparkline = (selector, points) => {
  const svgPath = document.querySelector(selector);
  if (!svgPath) return;
  if (!points || points.length < 2) {
    svgPath.setAttribute('d', '');
    return;
  }
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const path = points.map((point, index) => {
    const x = (index / (points.length - 1)) * 100;
    const y = 36 - ((point - min) / range) * 30 - 3;
    return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');
  svgPath.setAttribute('d', path);
};

const renderOverview = (payload) => {
  const latest = payload.latest?.data || null;
  if (!latest) {
    return;
  }
  const temperature = Number(latest.temperature_c ?? 0);
  const gas = Number(latest.gas_voc ?? 0);
  const weight = Number(latest.weight_kg ?? 0);
  const doorOpen = Boolean(latest.door_open);
  const tempEl = document.getElementById('temperature-value');
  const gasEl = document.getElementById('gas-value');
  const weightEl = document.getElementById('weight-value');
  const doorEl = document.getElementById('door-value');

  if (tempEl) tempEl.textContent = temperature.toFixed(1);
  if (gasEl) gasEl.textContent = gas.toFixed(0);
  if (weightEl) weightEl.textContent = weight.toFixed(1);
  if (doorEl) doorEl.textContent = doorOpen ? 'Open' : 'Closed';

  document.getElementById('last-seen').textContent = isoToLocal(latest.timestamp);
  document.getElementById('system-state').textContent = doorOpen ? 'Door alert' : (temperature > 7 ? 'Warning' : 'Normal');
  document.getElementById('device-status-pill').textContent = doorOpen ? 'Door open' : 'Online';
  document.getElementById('device-status-pill').className = `pill ${doorOpen ? 'amber' : 'green'}`;

  const trendColors = ['up', 'neutral', 'down'];
  const tempTrend = document.getElementById('temperature-trend');
  if (tempTrend) tempTrend.textContent = `${temperature > 5 ? '+' : ''}${(temperature * 0.4).toFixed(1)}°`; tempTrend.className = `trend ${temperature > 5 ? 'up' : 'neutral'}`;
  const gasTrend = document.getElementById('gas-trend');
  if (gasTrend) gasTrend.textContent = `${gas > 120 ? '+' : ''}${(gas * 0.05).toFixed(0)} VOC`; gasTrend.className = `trend ${gas > 120 ? 'up' : 'neutral'}`;
  const weightTrend = document.getElementById('weight-trend');
  if (weightTrend) weightTrend.textContent = `${weight < 3 ? 'Low' : 'Stable'}`; weightTrend.className = `trend ${weight < 3 ? 'down' : 'neutral'}`;
  const doorTrend = document.getElementById('door-trend');
  if (doorTrend) doorTrend.textContent = doorOpen ? 'Open' : 'Closed'; doorTrend.className = `trend ${doorOpen ? 'amber' : 'neutral'}`;

  const tempPoints = payload.range?.data?.map((row) => Number(row.temperature_c ?? 0)) || [temperature];
  const gasPoints = payload.range?.data?.map((row) => Number(row.gas_voc ?? 0)) || [gas];
  const weightPoints = payload.range?.data?.map((row) => Number(row.weight_kg ?? 0)) || [weight];
  renderSparkline('#temp-spark', tempPoints);
  renderSparkline('#gas-spark', gasPoints);
  renderSparkline('#weight-spark', weightPoints);

  const events = payload.alerts?.data || [];
  const eventList = document.getElementById('event-list');
  if (eventList) {
    eventList.innerHTML = events.length ? events.slice(0, 4).map((event) => `
      <li><span>${event.message || event.alert_type}</span><strong>${event.status || 'active'}</strong></li>
    `).join('') : '<li class="empty-state">No recent events</li>';
  }

  const summary = document.getElementById('alert-summary');
  if (summary) {
    const activeCount = (payload.alerts?.data || []).filter((item) => item.status === 'active').length;
    summary.innerHTML = `
      <div class="summary-item"><strong>${activeCount}</strong> active alerts</div>
      <div class="summary-item"><strong>${doorOpen ? '1' : '0'}</strong> door warnings</div>
      <div class="summary-item"><strong>${temperature > 7 ? '1' : '0'}</strong> temp violations</div>
    `;
  }

  const timeline = document.getElementById('door-timeline');
  if (timeline) {
    const samples = payload.range?.data || [];
    const eventsList = samples.filter((row) => row.door_open).slice(0, 4);
    if (!eventsList.length) {
      timeline.innerHTML = '<div class="empty-state">No door events in selected range</div>';
    } else {
      timeline.innerHTML = eventsList.map((row) => `
        <div class="timeline-item">
          <span>${isoToLocal(row.timestamp)}</span>
          <strong>${row.door_open ? 'Open' : 'Closed'}</strong>
        </div>
      `).join('');
    }
  }
};

const renderAnalytics = (payload) => {
  const rows = payload.range?.data || [];
  const temps = rows.map((row) => Number(row.temperature_c || 0));
  const values = rows.map((row) => Number(row.weight_kg || 0));
  const gasValues = rows.map((row) => Number(row.gas_voc || 0));

  const tempMin = document.getElementById('temp-min');
  const tempAvg = document.getElementById('temp-avg');
  const tempMax = document.getElementById('temp-max');
  const doorDuration = document.getElementById('door-duration');

  if (tempMin) tempMin.textContent = temps.length ? Math.min(...temps).toFixed(1) : '--';
  if (tempAvg) tempAvg.textContent = temps.length ? (temps.reduce((sum, value) => sum + value, 0) / temps.length).toFixed(1) : '--';
  if (tempMax) tempMax.textContent = temps.length ? Math.max(...temps).toFixed(1) : '--';
  if (doorDuration) doorDuration.textContent = `${rows.filter((row) => row.door_open).length * 5 || 0}`;

  const doorChartCtx = document.getElementById('door-chart');
  if (doorChartCtx) {
    drawChart('door-chart', {
      labels: rows.map((row) => new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
      datasets: [{
        label: 'Door open',
        data: rows.map((row) => (row.door_open ? 1 : 0)),
        borderColor: '#d2a66d',
        backgroundColor: 'rgba(210, 166, 109, 0.2)',
        fill: true,
      }],
      type: 'line',
    });
  }

  const gasChartCtx = document.getElementById('gas-chart');
  if (gasChartCtx) {
    drawChart('gas-chart', {
      labels: rows.map((row) => new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
      datasets: [
        { label: 'Current gas', data: gasValues, borderColor: '#a0662a', backgroundColor: 'rgba(160, 102, 42, 0.15)', fill: true },
        { label: 'Baseline', data: gasValues.map(() => 120), borderColor: '#6b7280', borderDash: [5, 5], fill: false },
      ],
      type: 'line',
    });
  }

  const weightChartCtx = document.getElementById('weight-chart');
  if (weightChartCtx) {
    drawChart('weight-chart', {
      labels: rows.map((row) => new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
      datasets: [{
        label: 'Weight (kg)',
        data: values,
        borderColor: '#2d7a5d',
        backgroundColor: 'rgba(45, 122, 93, 0.15)',
        fill: true,
      }],
      type: 'line',
    });
  }
};

const renderAlerts = (payload) => {
  const tbody = document.getElementById('alerts-table-body');
  if (!tbody) return;
  const filter = document.getElementById('alert-status-filter')?.value || 'all';
  const items = (payload.alerts?.data || []).filter((item) => filter === 'all' || item.status === filter);
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No alerts in this view.</td></tr>';
    return;
  }
  tbody.innerHTML = items.map((item) => `
    <tr>
      <td><span class="pill ${item.severity === 'high' ? 'red' : item.severity === 'medium' ? 'amber' : 'green'}">${item.severity || 'warning'}</span></td>
      <td>${item.message || item.alert_type}</td>
      <td>${item.status}</td>
      <td>${isoToLocal(item.last_triggered)}</td>
      <td><button class="secondary-button" type="button" data-ack-id="${item.id}">${item.status === 'acknowledged' ? 'Acked' : 'Acknowledge'}</button></td>
    </tr>
  `).join('');

  tbody.querySelectorAll('[data-ack-id]').forEach((button) => {
    button.addEventListener('click', async () => {
      const alertId = Number(button.getAttribute('data-ack-id'));
      await fetchJson(`/api/v1/alerts/${alertId}/ack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acknowledged_by: 'dashboard' }),
      });
      notify(`Alert ${alertId} acknowledged.`);
      await refreshDashboard();
    });
  });
};

const renderDevicePanel = (payload) => {
  const device = payload.device?.data || {};
  document.getElementById('device-id').textContent = device.device_id || 'device-01';
  document.getElementById('device-last-seen').textContent = isoToLocal(device.last_seen);
  document.getElementById('firmware-version').textContent = device.firmware_version || 'unknown';
  document.getElementById('wifi-rssi').textContent = device.wifi_rssi_dbm != null ? `${device.wifi_rssi_dbm} dBm` : 'n/a';
  document.getElementById('uptime').textContent = device.uptime_s != null ? `${Math.floor(device.uptime_s / 60)} min` : 'n/a';
  document.getElementById('device-connection').textContent = device.status || 'offline';

  const thresholds = payload.thresholds?.data || {};
  const form = document.getElementById('threshold-form');
  if (form) {
    for (const [name, value] of Object.entries(thresholds)) {
      const input = form.querySelector(`[name="${name}"]`);
      if (input) input.value = value;
    }
  }
};

const drawChart = (elementId, config) => {
  if (!elementId || !document.getElementById(elementId)) return;
  const existing = state.charts[elementId];
  if (existing) existing.destroy();
  const chart = new Chart(document.getElementById(elementId), {
    type: config.type || 'line',
    data: config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' }, tooltip: { mode: 'index', intersect: false } },
      scales: { y: { beginAtZero: false } },
    },
  });
  state.charts[elementId] = chart;
};

const loadDashboardData = async () => {
  const pageId = page?.dataset?.page || 'overview';
  try {
    updateConnectionState('live');
    const latest = await fetchJson('/api/v1/readings/latest');
    const range = await fetchJson(`/api/v1/readings?from=${new Date(Date.now() - 3600000).toISOString()}&bucket=15m`);
    const alerts = await fetchJson('/api/v1/alerts');
    const settings = await fetchJson('/api/v1/settings/thresholds');
    const device = await fetchJson('/api/v1/device/status?device_id=device-01');

    const payload = { latest, range, alerts, settings, device };
    if (pageId === 'overview') renderOverview(payload);
    if (pageId === 'analytics') renderAnalytics(payload);
    if (pageId === 'alerts') renderAlerts(payload);
    if (pageId === 'device') renderDevicePanel(payload);

    updateLastUpdated();
    state.retryDelay = 2000;
    notify('Dashboard refreshed successfully.');
  } catch (error) {
    state.retryDelay = Math.min(state.retryDelay * 2, 30000);
    updateConnectionState('offline');
    notify(`Refresh failed: ${error.message}`);
  }
};

const bindRangeSelector = () => {
  document.querySelectorAll('.range-pill').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.range-pill').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      const range = button.dataset.range;
      const fromMap = { '15m': 15 * 60000, '1h': 60 * 60000, '6h': 360 * 60000, '24h': 1440 * 60000 };
      const from = new Date(Date.now() - fromMap[range]).toISOString();
      fetchJson(`/api/v1/readings?from=${from}&bucket=raw`).then((payload) => {
        const rangePayload = { data: payload.data || [] };
        const fresh = { latest: { data: payload.data?.slice(-1)[0] || null }, range: rangePayload, alerts: { data: [] }, settings: { data: {} }, device: { data: {} } };
        renderOverview(fresh);
      });
    });
  });
};

const bindFilter = () => {
  const statusFilter = document.getElementById('alert-status-filter');
  if (!statusFilter) return;
  statusFilter.addEventListener('change', async () => {
    const alerts = await fetchJson('/api/v1/alerts');
    renderAlerts({ alerts });
  });
};

const bindThresholdForm = () => {
  const form = document.getElementById('threshold-form');
  if (!form) return;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    const payload = {
      temperature_high_c: Number(values.temperature_high_c),
      gas_rise_delta: Number(values.gas_rise_delta),
      door_open_seconds: Number(values.door_open_seconds),
      low_inventory_kg: Number(values.low_inventory_kg),
      offline_seconds: Number(values.offline_seconds),
    };
    await fetchJson('/api/v1/settings/thresholds', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    notify('Thresholds updated.');
    await refreshDashboard();
  });
};

const bindResetBaseline = () => {
  const button = document.getElementById('reset-gas-baseline');
  if (!button) return;
  button.addEventListener('click', async () => {
    await fetchJson('/api/v1/settings/baseline/reset', { method: 'POST' });
    notify('Gas baseline reset.');
    await refreshDashboard();
  });
};

const bindExport = () => {
  const button = document.getElementById('export-alerts');
  if (!button) return;
  button.addEventListener('click', async () => {
    window.open('/api/v1/export.csv', '_blank');
  });
};

const run = () => {
  const theme = localStorage.getItem('smart-fridge-theme') || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  if (themeToggle) {
    themeToggle.textContent = theme === 'dark' ? 'Light mode' : 'Dark mode';
    themeToggle.addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('smart-fridge-theme', next);
      themeToggle.textContent = next === 'dark' ? 'Light mode' : 'Dark mode';
    });
  }

  bindRangeSelector();
  bindFilter();
  bindThresholdForm();
  bindResetBaseline();
  bindExport();

  if (refreshButton) {
    refreshButton.addEventListener('click', async () => {
      await loadDashboardData();
    });
  }

  loadDashboardData();
  state.intervalId = setInterval(() => { loadDashboardData(); }, state.pollMs);
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', run);
} else {
  run();
}
