import { usePlantData } from './hooks/usePlantData'
import SensorPanel   from './components/SensorPanel'
import ActivityLog   from './components/ActivityLog'
import ControlPanel  from './components/ControlPanel'
import './App.css'

function Header({ data, connected, post }) {
  const hour     = data?.hour         ?? 0
  const total    = data?.total_hours  ?? 168
  const cost     = data?.cost         ?? 0
  const saving   = data?.total_saving ?? 0
  const running  = data?.running      ?? false
  const paused   = data?.paused       ?? false
  const finished = data?.finished     ?? false
  const pct      = Math.round((hour / total) * 100)

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-wordmark">
          <h1 className="header-title">PlantMind</h1>
          <span className="header-tag">Autonomous Ops</span>
        </div>
      </div>

      <div className="header-stats">
        <div className="stat">
          <span className="stat-label">Operating Cost</span>
          <span className="stat-value">£{cost.toFixed(2)}/hr</span>
        </div>
        <div className="stat">
          <span className="stat-label">Total Saved</span>
          <span className="stat-value saving">£{saving.toFixed(2)}/hr</span>
        </div>
        <div className="stat">
          <span className="stat-label">Timeline</span>
          <span className="stat-value">h{hour} / {total}</span>
        </div>
      </div>

      <div className="header-controls">
        <div className="conn-indicator">
          <div className={`conn-dot ${connected ? 'connected' : 'disconnected'}`} />
          {connected ? 'Live' : 'Reconnecting'}
        </div>
        {!running || paused
          ? <button className="hbtn hbtn-start" onClick={() => post('/api/start')} disabled={finished}>
              {finished ? 'Finished' : 'Start'}
            </button>
          : <button className="hbtn hbtn-pause" onClick={() => post('/api/pause')}>Pause</button>
        }
        <button className="hbtn hbtn-reset" onClick={() => post('/api/reset')}>Reset</button>
      </div>

      <div className="progress-bar-wrap">
        <div className="progress-bar" style={{ width: `${pct}%` }} />
      </div>
    </header>
  )
}

export default function App() {
  const { data, connected, post, postForm } = usePlantData()

  return (
    <div className="app">
      <Header data={data} connected={connected} post={post} />
      <main className="main-grid">
        <aside className="col-sensors">
          <p className="col-heading">Live Sensors</p>
          <SensorPanel state={data?.state} />
        </aside>
        <section className="col-log">
          <p className="col-heading">Agent Activity</p>
          <ActivityLog decisions={data?.decisions} alerts={data?.alerts} />
        </section>
        <aside className="col-controls">
          <p className="col-heading">Controls</p>
          <ControlPanel
            overrides={data?.overrides}
            paused={data?.paused ?? false}
            running={data?.running ?? false}
            transcriptionSettings={data?.transcription_settings}
            optimizationSettings={data?.optimization_settings}
            objectiveLiveValues={data?.objective_live_values}
            sensorUnits={data?.sensor_units}
            zones={data?.zones}
            post={post}
            postForm={postForm}
          />
        </aside>
      </main>
    </div>
  )
}
