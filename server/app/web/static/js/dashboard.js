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
  settings: {},
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
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);

const renderRFIDInventory = (items = []) => {
  const container = document.getElementById('rfid-item-list');
  if (!container) return;
  if (container.contains(document.activeElement)) return;
  if (!items.length) {
    container.innerHTML = '<p class="empty-state">No RFID tags scanned yet. Scan a tag with the reader to add it here.</p>';
    return;
  }
  container.innerHTML = items.map((item) => `
    <form class="rfid-item-row" data-rfid-item-form data-uid="${escapeHtml(item.uid)}">
      <div class="rfid-item-tag"><strong>${escapeHtml(item.item_name || 'New tag — name this item')}</strong><code>${escapeHtml(item.uid)}</code></div>
      <label>Item name<input name="item_name" maxlength="80" required value="${escapeHtml(item.item_name || '')}" placeholder="e.g. Tomato" /></label>
      <label>Count<input name="quantity" type="number" min="0" step="1" value="${Number(item.quantity) || 0}" /></label>
      <button class="secondary-button" type="submit">Save</button>
    </form>
  `).join('');
};

document.addEventListener('submit', async (event) => {
  const form = event.target.closest('[data-rfid-item-form]');
  if (!form) return;
  event.preventDefault();
  const fields = new FormData(form);
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    await fetchJson(`/api/v1/rfid/items/${encodeURIComponent(form.dataset.uid)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_name: fields.get('item_name'), quantity: Number(fields.get('quantity')) }),
    });
    document.activeElement.blur();
    notify('RFID item saved.');
    await loadDashboardData();
  } catch (error) {
    notify(`Could not save RFID item: ${error.message}`);
  } finally {
    button.disabled = false;
  }
});

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
  renderRFIDInventory(payload.rfidItems?.data || []);
  const latest = payload.latest?.data || null;
  if (!latest) {
    return;
  }
  const temperature = latest.temperature_c == null ? null : Number(latest.temperature_c);
  const gasReading = latest.gas_adc_raw;
  const gas = gasReading == null ? null : Number(gasReading);
  const weight = latest.weight_kg == null ? null : Number(latest.weight_kg);
  const thresholds = payload.settings?.data || {};
  const temperatureThreshold = Number(thresholds.temperature_high_c);
  const gasBaseline = Number(thresholds.baseline_gas);
  const gasRiseThreshold = Number(thresholds.gas_rise_delta);
  const lowInventoryThreshold = Number(thresholds.low_inventory_kg);
  const doorOpen = Boolean(latest.door_open);
  const doorVerified = Boolean(latest.door_sensor_verified);
  const temperatureHealthy = latest.temperature_sensor_ok !== false && latest.temperature_sensor_ok !== 0 && temperature != null;
  const gasHealthy = latest.gas_sensor_ok !== false && latest.gas_sensor_ok !== 0 && gas != null;
  const tempEl = document.getElementById('temperature-value');
  const gasEl = document.getElementById('gas-value');
  const weightEl = document.getElementById('weight-value');
  const doorEl = document.getElementById('door-value');

  if (tempEl) tempEl.textContent = temperature == null ? '--' : temperature.toFixed(1);
  if (gasEl) gasEl.textContent = gas == null ? '--' : gas.toFixed(1);
  if (weightEl) weightEl.textContent = weight == null ? '--' : weight.toFixed(1);
  if (doorEl) doorEl.textContent = doorVerified ? (doorOpen ? 'Open' : 'Closed') : 'Unverified';

  document.getElementById('last-seen').textContent = isoToLocal(latest.timestamp);
  const doorAlert = doorVerified && doorOpen && Number(latest.door_open_seconds || 0) >= Number(thresholds.door_open_seconds || 180);
  const legacyGasValue = latest.gas_voc == null ? null : Number(latest.gas_voc);
  const gasAlert = legacyGasValue != null && Number.isFinite(gasBaseline) &&
    Number.isFinite(gasRiseThreshold) && legacyGasValue >= gasBaseline + gasRiseThreshold;
  const temperatureAlert = temperature != null && Number.isFinite(temperatureThreshold) &&
    temperature > temperatureThreshold;
  const hasWarning = temperatureAlert || gasAlert;
  document.getElementById('system-state').textContent = !temperatureHealthy ? 'Temperature sensor error' : (doorAlert ? 'Door alert' : (hasWarning ? 'Warning' : 'Normal'));
  document.getElementById('device-status-pill').textContent = !temperatureHealthy ? 'Sensor error' : (doorVerified ? (doorOpen ? 'Door open' : 'Door closed') : 'Door unverified');
  document.getElementById('device-status-pill').className = `pill ${!temperatureHealthy ? 'red' : (doorOpen && doorVerified ? 'amber' : 'green')}`;
  const setText = (id, value) => { const element = document.getElementById(id); if (element) element.textContent = value; };
  setText('temperature-health', temperatureHealthy ? 'OK' : 'SENSOR ERROR');
  setText('temperature-threshold', `${Number.isFinite(temperatureThreshold) ? temperatureThreshold.toFixed(1) : '22.0'} °C`);
  setText('gas-health', gasHealthy ? 'OK' : 'SENSOR ERROR');
  setText('door-health', doorVerified ? (doorOpen ? 'OPEN' : 'CLOSED') : 'SENSOR UNVERIFIED');
  setText('alarm-state', latest.alarm_active ? 'ACTIVE' : (!temperatureHealthy ? 'UNKNOWN (sensor error)' : 'CLEAR'));
  setText('mute-state', latest.alarm_muted ? `MUTED · ${Number(latest.mute_remaining_s || 0)}s remaining` : 'NOT MUTED');
  setText('fan-state', latest.fan_on == null ? 'No device report' : (latest.fan_on ? 'ON' : 'OFF'));
  setText('red-led-state', latest.red_led_on == null ? 'No device report' : (latest.red_led_on ? 'ON' : 'OFF'));
  setText('green-led-state', latest.green_led_on == null ? 'No device report' : (latest.green_led_on ? 'ON' : 'OFF'));
  setText('buzzer-state', latest.buzzer_on == null ? 'No device report' : (latest.buzzer_on ? 'ON' : 'OFF'));

  const tempTrend = document.getElementById('temperature-trend');
  if (tempTrend) {
    tempTrend.textContent = temperature == null ? '--' : 'Live reading';
    tempTrend.className = `trend ${temperatureAlert ? 'up' : 'neutral'}`;
  }
  const gasTrend = document.getElementById('gas-trend');
  if (gasTrend) {
    gasTrend.textContent = gas == null ? '--' : 'Live reading';
    gasTrend.className = `trend ${gasAlert ? 'up' : 'neutral'}`;
  }
  const weightTrend = document.getElementById('weight-trend');
  if (weightTrend) {
    weightTrend.textContent = weight == null ? 'Sensor not connected' : 'Live reading';
    weightTrend.className = `trend ${weight != null && Number.isFinite(lowInventoryThreshold) && weight < lowInventoryThreshold ? 'down' : 'neutral'}`;
  }
  const doorTrend = document.getElementById('door-trend');
  if (doorTrend) {
    doorTrend.textContent = doorVerified ? (doorOpen ? 'Open' : 'Closed') : 'Sensor unverified';
    doorTrend.className = `trend ${doorVerified && doorOpen ? 'amber' : 'neutral'}`;
  }

  const tempPoints = (payload.range?.data || []).map((row) => row.temperature_c).filter(Number.isFinite);
  const gasPoints = (payload.range?.data || []).map((row) => row.gas_voc).filter(Number.isFinite);
  const weightPoints = (payload.range?.data || []).map((row) => row.weight_kg).filter(Number.isFinite);
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
      <div class="summary-item"><strong>${doorAlert ? '1' : '0'}</strong> door warnings</div>
      <div class="summary-item"><strong>${temperatureAlert ? '1' : '0'}</strong> temp violations</div>
    `;
  }

  const scans = payload.rfidScans?.data || [];
  const scanList = document.getElementById('rfid-scan-list');
  if (scanList) {
    scanList.innerHTML = scans.length ? scans.slice(0, 8).map((scan) =>
      `<li><span>${escapeHtml(scan.item_name || 'Unmapped tag')} · ${isoToLocal(scan.timestamp)}${scan.quantity ? ` · count ${scan.quantity}` : ''}</span><strong>${escapeHtml(scan.uid)}</strong></li>`
    ).join('') : '<li class="empty-state">No RFID scans recorded</li>';
  }

  const timeline = document.getElementById('door-timeline');
  if (timeline) {
    const samples = payload.range?.data || [];
    const eventsList = samples.filter((row) => row.door_open).slice(0, 4);
    if (!doorVerified) {
      timeline.innerHTML = '<div class="empty-state">Door sensor unverified until magnet and switch polarity are checked.</div>';
    } else if (!eventsList.length) {
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

  const chartRows = payload.range?.data || [];
  const overviewChart = document.getElementById('overview-chart');
  if (overviewChart) {
    drawChart('overview-chart', {
      labels: chartRows.map((row) => new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })),
      datasets: [
        {
          label: 'Temperature (Ã‚Â°C)',
          data: chartRows.map((row) => row.temperature_c),
          borderColor: '#a0662a',
          backgroundColor: 'rgba(160, 102, 42, 0.12)',
          yAxisID: 'temperature',
          spanGaps: false,
        },
        {
          label: 'Temperature limit',
          data: chartRows.map(() => Number.isFinite(temperatureThreshold) ? temperatureThreshold : null),
          borderColor: '#b84a4a',
          borderDash: [5, 5],
          pointRadius: 0,
          yAxisID: 'temperature',
        },
        {
          label: 'MQ-135 raw ADC (not ppm)',
          data: chartRows.map((row) => row.gas_adc_raw),
          borderColor: '#2d7a5d',
          backgroundColor: 'rgba(45, 122, 93, 0.10)',
          yAxisID: 'gas',
          spanGaps: false,
        },
      ],
      options: {
        scales: {
          temperature: { type: 'linear', position: 'left', title: { display: true, text: 'Ã‚Â°C' } },
          gas: { type: 'linear', position: 'right', title: { display: true, text: 'Raw ADC (0–4095)' }, grid: { drawOnChartArea: false } },
        },
      },
      type: 'line',
    });
  }
};

const renderAnalytics = (payload) => {
  const rows = payload.range?.data || [];
  const temps = rows.map((row) => row.temperature_c).filter(Number.isFinite);

  const tempMin = document.getElementById('temp-min');
  const tempAvg = document.getElementById('temp-avg');
  const tempMax = document.getElementById('temp-max');
  const doorDuration = document.getElementById('door-duration');

  if (tempMin) tempMin.textContent = temps.length ? Math.min(...temps).toFixed(1) : '--';
  if (tempAvg) tempAvg.textContent = temps.length ? (temps.reduce((sum, value) => sum + value, 0) / temps.length).toFixed(1) : '--';
  if (tempMax) tempMax.textContent = temps.length ? Math.max(...temps).toFixed(1) : '--';
  if (doorDuration) {
    const latest = rows[rows.length - 1];
    doorDuration.textContent = latest?.door_open_seconds == null
      ? '--'
      : (Number(latest.door_open_seconds) / 60).toFixed(1);
  }

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
        { label: 'MQ-135 raw ADC (not ppm)', data: rows.map((row) => row.gas_adc_raw), borderColor: '#a0662a', backgroundColor: 'rgba(160, 102, 42, 0.15)', fill: true },
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
        data: rows.map((row) => row.weight_kg),
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
  document.getElementById('device-id').textContent = device.device_id || '--';
  document.getElementById('device-last-seen').textContent = isoToLocal(device.last_seen);
  document.getElementById('firmware-version').textContent = device.firmware_version || 'unknown';
  document.getElementById('wifi-rssi').textContent = device.wifi_rssi_dbm != null ? `${device.wifi_rssi_dbm} dBm` : 'n/a';
  document.getElementById('uptime').textContent = device.uptime_s != null ? `${Math.floor(device.uptime_s / 60)} min` : 'n/a';
  document.getElementById('device-connection').textContent = device.status || 'offline';

  const thresholds = payload.settings?.data || {};
  const form = document.getElementById('threshold-form');
  if (form) {
    for (const [name, value] of Object.entries(thresholds)) {
      const input = form.querySelector(`[name="${name}"]`);
      if (input) input.value = value;
    }
  }
};

const drawChart = (elementId, config) => {
  const canvas = document.getElementById(elementId);
  if (!canvas) return;
  const chartData = { labels: config.labels, datasets: config.datasets };
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' }, tooltip: { mode: 'index', intersect: false } },
    ...(config.options || {}),
  };
  const existing = state.charts[elementId];
  if (existing) {
    existing.data = chartData;
    existing.options = chartOptions;
    existing.update('none');
    return;
  }
  state.charts[elementId] = new Chart(canvas, {
    type: config.type || 'line',
    data: chartData,
    options: chartOptions,
  });
};
const loadDashboardData = async () => {
  const pageId = page?.dataset?.page || 'overview';
  try {
    updateConnectionState('live');
    const latest = await fetchJson('/api/v1/readings/latest');
    const range = await fetchJson(`/api/v1/readings?from=${new Date(Date.now() - 3600000).toISOString()}&bucket=15m`);
    const alerts = await fetchJson('/api/v1/alerts');
    const settings = await fetchJson('/api/v1/settings/thresholds');
    const device = await fetchJson('/api/v1/device/status');
    const rfidScans = await fetchJson('/api/v1/rfid/scans?limit=8');
    const rfidItems = pageId === 'overview' ? await fetchJson('/api/v1/rfid/items') : { data: [] };

    state.settings = settings.data || {};
    const payload = { latest, range, alerts, settings, device, rfidScans, rfidItems };
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
        const fresh = { latest: { data: payload.data?.slice(-1)[0] || null }, range: rangePayload, alerts: { data: [] }, settings: { data: state.settings }, device: { data: {} } };
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
