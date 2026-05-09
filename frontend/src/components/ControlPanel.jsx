import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
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

function MicIcon({ recording }) {
  return (
    <svg className={`cp-mic-icon ${recording ? 'is-recording' : ''}`} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 15.5a3.5 3.5 0 0 0 3.5-3.5V7a3.5 3.5 0 1 0-7 0v5a3.5 3.5 0 0 0 3.5 3.5Z" fill="currentColor" />
      <path d="M18 11.75a.75.75 0 0 0-1.5 0 4.5 4.5 0 1 1-9 0 .75.75 0 0 0-1.5 0 6 6 0 0 0 5.25 5.95V20H9.75a.75.75 0 0 0 0 1.5h4.5a.75.75 0 0 0 0-1.5h-1.5v-2.3A6 6 0 0 0 18 11.75Z" fill="currentColor" />
    </svg>
  )
}

function Chevron({ open }) {
  return (
    <svg className={`cp-chevron ${open ? 'open' : ''}`} width="14" height="14" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Modal({ open, title, onClose, children }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previousOverflow
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="cp-modal-backdrop" onClick={onClose} role="presentation">
      <div className="cp-modal" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <header className="cp-modal-header">
          <h2 className="cp-modal-title">{title}</h2>
          <button type="button" className="cp-modal-close" onClick={onClose} aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M3.5 3.5L12.5 12.5M12.5 3.5L3.5 12.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </button>
        </header>
        <div className="cp-modal-body">{children}</div>
      </div>
    </div>,
    document.body,
  )
}

function ControlSection({ title, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <section className="cp-section">
      <button type="button" className="cp-section-header" onClick={() => setOpen((current) => !current)}>
        <span className="cp-label cp-label-no-margin">{title}</span>
        <Chevron open={open} />
      </button>
      <div className={`cp-section-body ${open ? 'cp-section-body-open' : ''}`}>
        <div className="cp-section-inner">
          {children}
        </div>
      </div>
    </section>
  )
}

function formatLiveValue(value) {
  if (value == null || Number.isNaN(value)) return '—'
  if (Math.abs(value) >= 100)  return value.toFixed(0)
  if (Math.abs(value) >= 1)    return value.toFixed(2)
  if (Math.abs(value) >= 0.01) return value.toFixed(3)
  if (value === 0)             return '0'
  return value.toExponential(1)
}

function OptimizationControls({ optimizationSettings, objectiveLiveValues, sensorUnits, zones, post, onSaved }) {
  const [summary, setSummary] = useState(optimizationSettings?.summary ?? '')
  const [weights, setWeights] = useState(optimizationSettings?.weights ?? {})
  const [objectives, setObjectives] = useState(optimizationSettings?.objectives ?? {})
  const [targets, setTargets] = useState(optimizationSettings?.targets ?? {})
  const [newObjectiveName, setNewObjectiveName] = useState('')
  const [newObjectiveDescription, setNewObjectiveDescription] = useState('')
  const [newObjectiveWeight, setNewObjectiveWeight] = useState('5')

  const saveOptimization = async () => {
    await post('/api/settings', {
      optimization: {
        summary,
        weights,
        objectives,
        targets,
      },
    })
    onSaved?.()
  }

  const addObjective = () => {
    const key = newObjectiveName.trim().toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_')
    if (!key) return

    setObjectives((current) => ({
      ...current,
      [key]: newObjectiveDescription.trim() || 'Custom optimisation objective.',
    }))
    setWeights((current) => ({
      ...current,
      [key]: newObjectiveWeight === '' ? 5 : Number(newObjectiveWeight),
    }))
    setNewObjectiveName('')
    setNewObjectiveDescription('')
    setNewObjectiveWeight('5')
  }

  return (
    <>
      <p className="cp-note">
        Set how much each objective matters (priority 0–10). The chip on the right shows the live reading
        from the plant in real units, so you can see what each priority is actually steering.
      </p>
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

      <p className="cp-subhead">Objectives</p>
      <div className="cp-objectives">
        {Object.entries(weights).map(([key, value]) => {
          const live = objectiveLiveValues?.[key]
          const numeric = value === '' ? 0 : Number(value)
          return (
            <div key={key} className="cp-objective">
              <div className="cp-objective-head">
                <span className="cp-objective-name">{formatLabel(key)}</span>
                {live ? (
                  <span className="cp-objective-live">
                    <span className="cp-objective-live-value">{formatLiveValue(live.value)}</span>
                    <span className="cp-objective-live-unit">{live.unit}</span>
                  </span>
                ) : (
                  <span className="cp-objective-live cp-objective-live-empty">no live reading</span>
                )}
              </div>
              <div className="cp-objective-priority">
                <input
                  className="cp-slider"
                  type="range"
                  min="0"
                  max="10"
                  step="0.5"
                  value={numeric}
                  onChange={(e) => setWeights((current) => ({
                    ...current,
                    [key]: Number(e.target.value),
                  }))}
                />
                <span className="cp-objective-prio">
                  Priority <strong>{numeric}</strong> / 10
                </span>
              </div>
              <input
                className="cp-input"
                value={objectives[key] ?? ''}
                onChange={(e) => setObjectives((current) => ({
                  ...current,
                  [key]: e.target.value,
                }))}
                placeholder="What this objective means"
              />
            </div>
          )
        })}
      </div>

      <p className="cp-subhead">Add Objective</p>
      <div className="cp-field">
        <label className="cp-field-label">Suggested ideas</label>
        <div className="cp-chip-row">
          {['co2_emissions', 'maintenance_risk', 'alarm_load', 'water_use', 'utility_efficiency', 'flaring_or_venting'].map((name) => (
            <button
              key={name}
              type="button"
              className="cp-chip"
              onClick={() => setNewObjectiveName(name)}
            >
              {formatLabel(name)}
            </button>
          ))}
        </div>
      </div>
      <div className="cp-grid cp-grid-3">
        <div className="cp-field">
          <label className="cp-field-label">Metric name</label>
          <input
            className="cp-input"
            value={newObjectiveName}
            onChange={(e) => setNewObjectiveName(e.target.value)}
            placeholder="co2_emissions"
          />
        </div>
        <div className="cp-field">
          <label className="cp-field-label">Weight</label>
          <input
            className="cp-input"
            type="number"
            min="0"
            max="10"
            step="0.5"
            value={newObjectiveWeight}
            onChange={(e) => setNewObjectiveWeight(e.target.value)}
          />
        </div>
        <div className="cp-field">
          <label className="cp-field-label">Description</label>
          <input
            className="cp-input"
            value={newObjectiveDescription}
            onChange={(e) => setNewObjectiveDescription(e.target.value)}
            placeholder="Reduce emissions-heavy decisions"
          />
        </div>
      </div>
      <button className="cp-action cp-action-secondary" onClick={addObjective}>Add Objective To Plan</button>

      <p className="cp-subhead">Target Conditions</p>
      <p className="cp-note">
        Target sensor values the supervisor steers each zone toward. Each zone has its own normal
        operating range, so e.g. R-101 runs much hotter than HX-01 — set targets accordingly.
      </p>
      <div className="cp-targets">
        {Object.entries(targets).map(([zoneKey, zoneTargets]) => {
          const zoneLabel = zones?.[zoneKey] || zoneKey
          return (
            <div key={zoneKey} className="cp-target-zone">
              <div className="cp-target-zone-head">
                <span className="cp-target-zone-name">{zoneLabel}</span>
                <span className="cp-target-zone-id">{zoneKey}</span>
              </div>
              <div className="cp-grid">
                {Object.entries(zoneTargets).map(([sensor, value]) => {
                  const unit = sensorUnits?.[sensor] || UNITS[sensor] || ''
                  return (
                    <div key={sensor} className="cp-field">
                      <label className="cp-field-label">
                        {formatLabel(sensor)}
                        {unit && <span className="cp-field-unit"> ({unit})</span>}
                      </label>
                      <input
                        className="cp-input"
                        type="number"
                        step="0.1"
                        value={value ?? ''}
                        onChange={(e) => setTargets((current) => ({
                          ...current,
                          [zoneKey]: { ...current[zoneKey], [sensor]: e.target.value },
                        }))}
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
      <p className="cp-note">Apply these while the simulation is running to change how the supervisor reasons in real time.</p>
      <button className="cp-action" onClick={saveOptimization}>Apply Optimisation Settings</button>
    </>
  )
}

function SpeechToTextControls({ transcriptionSettings, postForm }) {
  const [isRecording, setIsRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [transcriptStatus, setTranscriptStatus] = useState('')
  const [mediaRecorder, setMediaRecorder] = useState(null)

  const toggleRecording = async () => {
    if (isRecording && mediaRecorder) {
      mediaRecorder.stop()
      return
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setTranscriptStatus('Microphone recording is not supported in this browser.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const chunks = []
      const recorder = new MediaRecorder(stream)

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data)
      }

      recorder.onstop = async () => {
        setIsRecording(false)
        setTranscriptStatus('Transcribing...')

        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
        const extension = blob.type.includes('mp4') ? 'm4a' : 'webm'
        const formData = new FormData()
        formData.append('audio', blob, `recording.${extension}`)

        try {
          const result = await postForm('/api/transcribe', formData)
          setTranscript(result.text || '')
          setTranscriptStatus(result.text ? `Transcribed${result.language_code ? ` (${result.language_code})` : ''}.` : 'No speech detected.')
        } catch (error) {
          setTranscriptStatus(error.message || 'Transcription failed.')
        } finally {
          stream.getTracks().forEach((track) => track.stop())
          setMediaRecorder(null)
        }
      }

      recorder.start()
      setMediaRecorder(recorder)
      setIsRecording(true)
      setTranscriptStatus('Recording...')
    } catch {
      setTranscriptStatus('Microphone access was denied or unavailable.')
    }
  }

  const ready = !!transcriptionSettings?.configured
  const transcribing = transcriptStatus === 'Transcribing...'
  const callState = !ready ? 'off' : isRecording ? 'live' : transcribing ? 'busy' : 'idle'
  const callLabel = !ready ? 'Voice unavailable'
                  : isRecording ? 'Listening…'
                  : transcribing ? 'Transcribing…'
                  : transcript ? 'Tap to speak again'
                  : 'Tap to speak'
  const callHint  = !ready ? 'Add ELEVENLABS_API_KEY to enable'
                  : isRecording ? 'Tap mic to stop and send'
                  : transcribing ? 'Sending audio to ElevenLabs Scribe'
                  : 'ElevenLabs Scribe v2'

  const clearTranscript = () => {
    setTranscript('')
    setTranscriptStatus('')
  }

  return (
    <div className="cp-speech-section">
      <div className={`cp-call cp-call-${callState}`}>
        <button
          type="button"
          className={`cp-call-btn ${isRecording ? 'is-recording' : ''}`}
          onClick={toggleRecording}
          disabled={!ready || transcribing}
          aria-label={callLabel}
        >
          <MicIcon recording={isRecording} />
        </button>
        <div className="cp-call-meta">
          <p className="cp-call-status">{callLabel}</p>
          <p className="cp-call-hint">{callHint}</p>
        </div>
      </div>

      {transcript ? (
        <div className="cp-transcript-card">
          <div className="cp-transcript-head">
            <span className="cp-transcript-label">Captured message</span>
            <button type="button" className="cp-transcript-clear" onClick={clearTranscript}>Clear</button>
          </div>
          <textarea
            className="cp-transcript-edit"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            rows={3}
          />
        </div>
      ) : (
        !isRecording && !transcribing && ready && (
          <p className="cp-transcript-empty">Your message will appear here once transcribed.</p>
        )
      )}
    </div>
  )
}

export default function ControlPanel({ overrides, paused, transcriptionSettings, optimizationSettings, objectiveLiveValues, sensorUnits, zones, post, postForm }) {
  const hasOverrides = overrides && Object.keys(overrides).length > 0
  const [optModalOpen, setOptModalOpen] = useState(false)

  return (
    <div className="control-panel">
      <section className="cp-summary">
        <p className="cp-summary-title">Quick Status</p>
        <div className="cp-summary-pills">
          <div className="cp-status-pill">
            <span className={`cp-pill-dot ${paused ? 'amber' : 'green'}`} />
            <span className="cp-pill-label">Mode</span>
            <span className="cp-pill-value">{paused ? 'Manual' : 'Autonomous'}</span>
          </div>
          <div className="cp-status-pill">
            <span className={`cp-pill-dot ${transcriptionSettings?.configured ? 'green' : 'muted'}`} />
            <span className="cp-pill-label">Voice input</span>
            <span className="cp-pill-value">
              {transcriptionSettings?.configured ? 'Ready' : 'Off'}
            </span>
          </div>
        </div>
      </section>

      <ControlSection title="Applied Setpoints">
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
      </ControlSection>

      <div className="cp-divider" />



      <SpeechToTextControls
        transcriptionSettings={transcriptionSettings}
        postForm={postForm}
      />

      <div className="cp-divider" />

      <section className="cp-section">
        <span className="cp-label cp-label-no-margin">Optimisation Goals</span>
        <p className="cp-note">
          Edit the supervisor's strategy, weights, and target conditions in a focused dialog.
        </p>
        <button className="cp-action" onClick={() => setOptModalOpen(true)}>
          Edit Optimisation Goals
        </button>
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

      <Modal
        open={optModalOpen}
        title="Optimisation Goals"
        onClose={() => setOptModalOpen(false)}
      >
        <OptimizationControls
          key={JSON.stringify(optimizationSettings ?? {})}
          optimizationSettings={optimizationSettings}
          objectiveLiveValues={objectiveLiveValues}
          sensorUnits={sensorUnits}
          zones={zones}
          post={post}
          onSaved={() => setOptModalOpen(false)}
        />
      </Modal>
    </div>
  )
}
