import { useEffect, useState } from 'react'
import './ControlPanel.css'

const UNITS = {
  temperature:        '°C',
  pressure:           'bar',
  co2:                'ppm',
  flow_rate:          'L/min',
  ph:                 'pH',
  energy_consumption: 'kW',
}

function formatLabel(key) {
  return key.replace(/_/g, ' ')
}

export default function ControlPanel({ overrides, paused, running, voiceSettings, optimizationSettings, post }) {
  const hasOverrides = overrides && Object.keys(overrides).length > 0
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const [voiceId, setVoiceId] = useState('Rachel')
  const [summary, setSummary] = useState('')
  const [weights, setWeights] = useState({})
  const [targets, setTargets] = useState({})

  useEffect(() => {
    setVoiceEnabled(voiceSettings?.enabled ?? true)
    setVoiceId(voiceSettings?.voice_id ?? 'Rachel')
  }, [voiceSettings])

  useEffect(() => {
    setSummary(optimizationSettings?.summary ?? '')
    setWeights(optimizationSettings?.weights ?? {})
    setTargets(optimizationSettings?.targets ?? {})
  }, [optimizationSettings])

  const saveVoice = () => post('/api/settings', {
    voice: {
      enabled: voiceEnabled,
      voice_id: voiceId,
    },
  })

  const saveOptimization = () => post('/api/settings', {
    optimization: {
      summary,
      weights,
      targets,
    },
  })

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
        <p className="cp-label">Voice Output</p>
        <label className="cp-toggle">
          <input
            type="checkbox"
            checked={voiceEnabled}
            onChange={(e) => setVoiceEnabled(e.target.checked)}
          />
          <span className="cp-track">
            <span className="cp-thumb" />
          </span>
          <span className="cp-toggle-label">
            {voiceEnabled ? 'Speak aloud' : 'Muted'}
          </span>
        </label>
        <div className="cp-field">
          <label className="cp-field-label">Voice ID</label>
          <input
            className="cp-input"
            value={voiceId}
            onChange={(e) => setVoiceId(e.target.value)}
            placeholder="Rachel"
          />
        </div>
        <p className="cp-note">
          Announcements are queued to prevent overlap.
          {voiceSettings?.is_speaking ? ' Speaking now.' : ''}
          {typeof voiceSettings?.queued_messages === 'number' ? ` Queue: ${voiceSettings.queued_messages}.` : ''}
        </p>
        <button className="cp-action" onClick={saveVoice}>Apply Voice Settings</button>
      </section>

      <div className="cp-divider" />

      <section className="cp-section">
        <p className="cp-label">Optimisation Goals</p>
        <div className="cp-field">
          <label className="cp-field-label">Strategy</label>
          <textarea
            className="cp-textarea"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="Describe what the agent should prioritise."
            rows={4}
          />
        </div>

        <div className="cp-grid">
          {Object.entries(weights).map(([key, value]) => (
            <div key={key} className="cp-field">
              <label className="cp-field-label">{formatLabel(key)}</label>
              <input
                className="cp-input"
                type="number"
                min="0"
                max="10"
                step="0.5"
                value={value}
                onChange={(e) => setWeights((current) => ({
                  ...current,
                  [key]: e.target.value === '' ? '' : Number(e.target.value),
                }))}
              />
            </div>
          ))}
        </div>

        <p className="cp-subhead">Target Conditions</p>
        <div className="cp-grid">
          {Object.entries(targets).map(([key, value]) => (
            <div key={key} className="cp-field">
              <label className="cp-field-label">{formatLabel(key)}</label>
              <input
                className="cp-input"
                type="number"
                step="0.1"
                value={value ?? ''}
                onChange={(e) => setTargets((current) => ({
                  ...current,
                  [key]: e.target.value,
                }))}
              />
            </div>
          ))}
        </div>
        <p className="cp-note">Apply these while the simulation is running to change how the supervisor reasons in real time.</p>
        <button className="cp-action" onClick={saveOptimization}>Apply Optimisation Settings</button>
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
