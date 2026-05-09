import { useState } from 'react'
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

function VoiceControls({ voiceSettings, post }) {
  const [voiceEnabled, setVoiceEnabled] = useState(voiceSettings?.enabled ?? true)
  const [voiceId, setVoiceId] = useState(voiceSettings?.voice_id ?? 'Rachel')

  const saveVoice = () => post('/api/settings', {
    voice: {
      enabled: voiceEnabled,
      voice_id: voiceId,
    },
  })

  return (
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
  )
}

function OptimizationControls({ optimizationSettings, post }) {
  const [summary, setSummary] = useState(optimizationSettings?.summary ?? '')
  const [weights, setWeights] = useState(optimizationSettings?.weights ?? {})
  const [objectives, setObjectives] = useState(optimizationSettings?.objectives ?? {})
  const [targets, setTargets] = useState(optimizationSettings?.targets ?? {})
  const [newObjectiveName, setNewObjectiveName] = useState('')
  const [newObjectiveDescription, setNewObjectiveDescription] = useState('')
  const [newObjectiveWeight, setNewObjectiveWeight] = useState('5')

  const saveOptimization = () => post('/api/settings', {
    optimization: {
      summary,
      weights,
      objectives,
      targets,
    },
  })

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
        ))}
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
  )
}

function SpeechToTextControls({ postForm }) {
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

  return (
    <section className="cp-section">
      <p className="cp-label">Speech To Text</p>
      <button
        type="button"
        className={`cp-record ${isRecording ? 'is-recording' : ''}`}
        onClick={toggleRecording}
      >
        <MicIcon recording={isRecording} />
        <span>{isRecording ? 'Stop Recording' : 'Record Voice'}</span>
      </button>
      <p className="cp-note">
        Record from your microphone and transcribe it with ElevenLabs Scribe.
      </p>
      {transcriptStatus && <p className="cp-status">{transcriptStatus}</p>}
      <textarea
        className="cp-textarea cp-transcript"
        value={transcript}
        onChange={(e) => setTranscript(e.target.value)}
        placeholder="Transcript will appear here."
        rows={5}
      />
    </section>
  )
}

export default function ControlPanel({ overrides, paused, voiceSettings, optimizationSettings, post, postForm }) {
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

      <VoiceControls
        key={JSON.stringify(voiceSettings ?? {})}
        voiceSettings={voiceSettings}
        post={post}
      />

      <div className="cp-divider" />

      <SpeechToTextControls postForm={postForm} />

      <div className="cp-divider" />

      <OptimizationControls
        key={JSON.stringify(optimizationSettings ?? {})}
        optimizationSettings={optimizationSettings}
        post={post}
      />

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
