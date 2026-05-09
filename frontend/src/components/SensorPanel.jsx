import { useState } from 'react'
import './SensorPanel.css'

const UNITS = {
  temperature:        '°C',
  pressure:           'bar',
  co2:                'ppm',
  flow_rate:          'L/min',
  ph:                 'pH',
  energy_consumption: 'kW',
}

const THRESHOLDS = {
  r101:      { temperature:[null,null,220,240], pressure:[1.5,1.0,6.5,8.0], co2:[null,null,680,900], flow_rate:[50,30,140,160], ph:[6.1,5.5,8.2,9.0], energy_consumption:[null,null,300,380] },
  r102:      { temperature:[null,null,215,235], pressure:[1.5,1.0,6.2,7.5], co2:[null,null,650,850], flow_rate:[45,25,135,155], ph:[6.2,5.5,8.3,9.0], energy_consumption:[null,null,280,350] },
  hx01:      { temperature:[null,null,75,90],   pressure:[0.5,0.3,3.5,4.5], flow_rate:[100,60,480,520], energy_consumption:[null,null,110,130] },
  'dist-c01':{ temperature:[null,null,148,165], pressure:[0.3,0.2,3.0,3.8], flow_rate:[25,15,115,130], energy_consumption:[null,null,360,420] },
  util:      { temperature:[null,null,180,200], pressure:[2.5,1.5,8.5,10.0], flow_rate:[200,120,1050,1150], energy_consumption:[null,null,240,280] },
}

const NORMAL = {
  r101:      { temperature:[160,200], pressure:[3.0,5.5], co2:[250,480], flow_rate:[85,110], ph:[6.9,7.4], energy_consumption:[180,230] },
  r102:      { temperature:[155,195], pressure:[2.8,5.2], co2:[230,460], flow_rate:[80,105], ph:[7.0,7.5], energy_consumption:[165,215] },
  hx01:      { temperature:[48,62],   pressure:[1.2,2.8], flow_rate:[200,350], energy_consumption:[45,85] },
  'dist-c01':{ temperature:[95,125],  pressure:[0.8,2.2], flow_rate:[60,90],   energy_consumption:[220,290] },
  util:      { temperature:[135,165], pressure:[4.0,7.0], flow_rate:[500,800], energy_consumption:[120,180] },
}

function sensorStatus(zone, sensor, value) {
  const t = THRESHOLDS[zone]?.[sensor]
  if (!t) return 'ok'
  const [loW, loC, hiW, hiC] = t
  if ((loC != null && value <= loC) || (hiC != null && value >= hiC)) return 'crit'
  if ((loW != null && value <= loW) || (hiW != null && value >= hiW)) return 'warn'
  return 'ok'
}

function zoneWorstStatus(zone, sensors) {
  let worst = 'ok'
  for (const [sensor, value] of Object.entries(sensors)) {
    const s = sensorStatus(zone, sensor, value)
    if (s === 'crit') return 'crit'
    if (s === 'warn') worst = 'warn'
  }
  return worst
}

function Chevron({ open }) {
  return (
    <svg className={`chevron ${open ? 'open' : ''}`} width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function SensorBar({ zone, sensor, value }) {
  const range = NORMAL[zone]?.[sensor]
  if (!range) return null
  const [lo, hi] = range
  const pct = Math.min(100, Math.max(0, ((value - lo) / (hi - lo)) * 100))
  return (
    <div className="sensor-bar-track">
      <div className="sensor-bar-fill" style={{ width: `${pct}%` }} />
    </div>
  )
}

function SensorRow({ zone, sensor, value }) {
  const status = sensorStatus(zone, sensor, value)
  const unit   = UNITS[sensor] || ''
  const label  = sensor.replace(/_/g, ' ')
  return (
    <div className={`sensor-row sensor-${status}`}>
      <span className="sensor-label">{label}</span>
      <div className="sensor-right">
        <span className="sensor-value">{typeof value === 'number' ? value.toFixed(2) : value}</span>
        <span className="sensor-unit">{unit}</span>
      </div>
      <SensorBar zone={zone} sensor={sensor} value={value} />
    </div>
  )
}

function ZoneCard({ zoneId, zoneData }) {
  const { display_name, sensors, is_working } = zoneData
  const [open, setOpen] = useState(true)
  const worst = is_working ? zoneWorstStatus(zoneId, sensors) : 'idle'

  return (
    <div className={`zone-card zone-${worst}`}>
      <button className="zone-header" onClick={() => setOpen(o => !o)}>
        <div className="zone-header-left">
          <span className={`zone-status-dot status-${worst}`} />
          <span className="zone-name">{display_name}</span>
        </div>
        <div className="zone-header-right">
          {!is_working && <span className="zone-badge-maint">Maintenance</span>}
          {is_working && worst === 'crit' && <span className="zone-badge-crit">Critical</span>}
          {is_working && worst === 'warn' && <span className="zone-badge-warn">Warning</span>}
          <Chevron open={open} />
        </div>
      </button>

      <div className={`zone-body ${open ? 'zone-body-open' : ''}`}>
        <div className="sensor-list">
          {Object.entries(sensors).map(([sensor, value]) => (
            <SensorRow key={sensor} zone={zoneId} sensor={sensor} value={value} />
          ))}
        </div>
      </div>
    </div>
  )
}

export default function SensorPanel({ state }) {
  if (!state) return <div className="sensor-panel-empty">Connecting to plant…</div>
  return (
    <div className="sensor-panel">
      {Object.entries(state).map(([zoneId, zoneData]) => (
        <ZoneCard key={zoneId} zoneId={zoneId} zoneData={zoneData} />
      ))}
    </div>
  )
}
