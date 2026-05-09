import './ControlPanel.css'

const UNITS = {
  temperature:        '°C',
  pressure:           'bar',
  co2:                'ppm',
  flow_rate:          'L/min',
  ph:                 'pH',
  energy_consumption: 'kW',
}

export default function ControlPanel({ overrides, paused, running, post }) {
  const hasOverrides = overrides && Object.keys(overrides).length > 0

  return (
    <div className="control-panel">

      <section className="cp-section">
        <p className="cp-label">Applied Setpoints</p>
        {!hasOverrides
          ? <p className="cp-empty">No overrides active.</p>
          : Object.entries(overrides).map(([zone, metrics]) => (
              <div key={zone} className="cp-zone">
                <p className="cp-zone-name">{zone}</p>
                {Object.entries(metrics).map(([metric, delta]) => (
                  <div key={metric} className="cp-override-row">
                    <span className="cp-metric">{metric.replace(/_/g, ' ')}</span>
                    <span className={`cp-delta ${delta >= 0 ? 'pos' : 'neg'}`}>
                      {delta >= 0 ? '+' : ''}{delta.toFixed(2)} {UNITS[metric] || ''}
                    </span>
                  </div>
                ))}
              </div>
            ))
        }
      </section>

      <div className="cp-divider" />

      <section className="cp-section">
        <p className="cp-label">Human Override</p>
        <label className="cp-toggle">
          <input
            type="checkbox"
            checked={paused}
            onChange={(e) => post('/api/override', { paused: e.target.checked })}
          />
          <span className="cp-track">
            <span className="cp-thumb" />
          </span>
          <span className="cp-toggle-label">
            {paused ? 'Manual mode' : 'Autonomous'}
          </span>
        </label>
        {paused && <p className="cp-warning">Agents paused — you have control.</p>}
      </section>

      <div className="cp-divider" />

      <section className="cp-section">
        <button
          className="cp-emergency"
          onClick={() => post('/api/emergency-stop')}
        >
          Emergency Stop
        </button>
      </section>

    </div>
  )
}
