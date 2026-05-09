import { useState } from 'react'
import './ActivityLog.css'

function AlertBanner({ alerts }) {
  if (!alerts?.length) return null
  return (
    <div className="alert-banners">
      {alerts.map((a, i) => (
        <div key={i} className={`alert-banner alert-${a.severity}`}>
          <span className={`alert-pip alert-pip-${a.severity}`} />
          <span className="alert-text">
            <strong>{a.zone}</strong> — {a.sensor}: {a.value}
            {a.type === 'trend' && a.minutes_to_breach != null &&
              ` · breach in ${a.minutes_to_breach} min`}
            {a.type === 'spike' && a.rate_of_change != null &&
              ` · delta ${a.rate_of_change > 0 ? '+' : ''}${a.rate_of_change}`}
            <span className="alert-type"> [{a.type}]</span>
          </span>
        </div>
      ))}
    </div>
  )
}

function DecisionCard({ decision }) {
  const [expanded, setExpanded] = useState(false)
  const ctrl = decision.control_result

  const statusClass = ctrl?.status === 'executed' ? 'executed'
                    : ctrl?.status === 'rejected'  ? 'rejected'
                    : 'info'

  return (
    <div className={`decision-card decision-${statusClass}`}>
      <div className="decision-header">
        <div className="decision-status">
          <span className={`decision-dot dot-${statusClass}`} />
          <span className={`decision-label label-${statusClass}`}>
            {statusClass === 'executed' ? 'Executed'
           : statusClass === 'rejected' ? 'Rejected'
           : 'Logged'}
          </span>
        </div>
        {decision.cost_impact != null && decision.cost_impact !== 0 && (
          <span className="decision-saving">
            £{Math.abs(decision.cost_impact).toFixed(2)}/hr {decision.cost_impact > 0 ? 'saved' : 'added'}
          </span>
        )}
      </div>

      {decision.action_taken && decision.action_taken !== 'none' && (
        <div className="decision-action">{decision.action_taken}</div>
      )}

      {ctrl?.status === 'rejected' && ctrl.reason && (
        <div className="decision-rejection">{ctrl.reason}</div>
      )}

      {decision.reasoning && (
        <div className="decision-reasoning-wrap">
          <button className="reasoning-toggle" onClick={() => setExpanded(!expanded)}>
            <svg className={`reasoning-chevron ${expanded ? 'open' : ''}`} width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {expanded ? 'Hide reasoning' : 'Show reasoning'}
          </button>
          {expanded && (
            <pre className="decision-reasoning">{decision.reasoning.trim()}</pre>
          )}
        </div>
      )}
    </div>
  )
}

export default function ActivityLog({ decisions, alerts }) {
  const reversed = decisions ? [...decisions].reverse() : []
  return (
    <div className="activity-log">
      <AlertBanner alerts={alerts} />
      {reversed.length === 0 && (
        <div className="activity-empty">
          No agent decisions yet.
          <br />
          Press <strong>Start</strong> to begin autonomous operation.
        </div>
      )}
      {reversed.map((d, i) => (
        <DecisionCard key={i} decision={d} />
      ))}
    </div>
  )
}
