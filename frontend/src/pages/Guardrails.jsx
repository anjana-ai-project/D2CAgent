import { useState, useEffect } from 'react'
import api from '../api/client'

export default function Guardrails() {
  const [agents, setAgents] = useState([])

  useEffect(() => {
    api.getAgents().then(setAgents)
  }, [])

  const parseJSON = (val, fallback) => {
    if (!val) return fallback
    if (typeof val === 'object') return val
    try { return JSON.parse(val) } catch { return fallback }
  }

  const urgencyColor = (key) => {
    if (key.includes('max') || key.includes('require'))
      return 'text-red-400'
    if (key.includes('escalate') || key.includes('auto'))
      return 'text-yellow-400'
    return 'text-blue-400'
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">
          Guardrails & Limits
        </h2>
        <p className="text-gray-400 text-sm mt-1">
          Per-agent rules and limits enforced at runtime
        </p>
      </div>

      {/* Global Guardrail */}
      <div className="bg-purple-900/20 rounded-xl p-4 border
        border-purple-800">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-2xl">🛡️</span>
          <div>
            <p className="text-white font-medium">
              Global Compensation Limit
            </p>
            <p className="text-gray-400 text-sm">
              Applies to all agents
            </p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div>
            <p className="text-gray-500 text-xs">
              Max Auto-Approve
            </p>
            <p className="text-green-400 text-xl font-bold">
              ₹200
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">
              Max Compensation
            </p>
            <p className="text-yellow-400 text-xl font-bold">
              ₹500
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">
              Above Limit
            </p>
            <p className="text-red-400 text-xl font-bold">
              Human
            </p>
          </div>
        </div>
      </div>

      {/* Per Agent Guardrails */}
      <div className="space-y-4">
        {agents.map(agent => {
          const guardrails = parseJSON(agent.guardrails, {})
          const rules = parseJSON(agent.interaction_rules, [])
          const hasGuardrails =
            Object.keys(guardrails).length > 0 ||
            rules.length > 0

          if (!hasGuardrails) return null

          return (
            <div key={agent.agent_id}
              className="bg-gray-900 rounded-xl p-5 border
                border-gray-800">
              <h3 className="text-white font-medium mb-4 flex
                items-center gap-2">
                <span className="w-2 h-2 bg-purple-400
                  rounded-full"/>
                {agent.name}
              </h3>

              {Object.keys(guardrails).length > 0 && (
                <div className="mb-4">
                  <p className="text-gray-500 text-xs mb-2">
                    LIMITS
                  </p>
                  <div className="space-y-2">
                    {Object.entries(guardrails).map(
                      ([key, value]) => (
                      <div key={key}
                        className="flex items-center
                          justify-between bg-gray-800
                          rounded-lg px-3 py-2">
                        <span className="text-gray-400
                          text-xs font-mono">
                          {key}
                        </span>
                        <span className={`text-xs font-bold
                          ${urgencyColor(key)}`}>
                          {Array.isArray(value)
                            ? value.join(', ')
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {rules.length > 0 && (
                <div>
                  <p className="text-gray-500 text-xs mb-2">
                    INTERACTION RULES
                  </p>
                  <div className="space-y-1.5">
                    {rules.map((rule, idx) => (
                      <div key={idx}
                        className="flex items-start gap-2">
                        <span className="text-purple-400
                          text-xs mt-0.5">•</span>
                        <span className="text-gray-300 text-xs">
                          {rule}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}