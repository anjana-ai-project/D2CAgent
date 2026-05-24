import { useState, useEffect, useRef } from 'react'
import api from '../api/client'

export default function Monitor() {
  const [logs, setLogs] = useState([])
  const [conversations, setConversations] = useState([])
  const [flags, setFlags] = useState([])
  const [runs, setRuns] = useState([])
  const [liveLogs, setLiveLogs] = useState([])
  const [activeTab, setActiveTab] = useState('live')
  const wsRef = useRef(null)
  const liveRef = useRef(null)

  useEffect(() => {
    loadData()
    connectWebSocket()
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  const loadData = async () => {
    try {
      const [l, c, f, r] = await Promise.all([
        api.getLogs(),
        api.getConversations(),
        api.getFlags(),
        api.getRuns()
      ])
      setLogs(l)
      setConversations(c)
      setFlags(f)
      setRuns(r)
    } catch (e) {
      console.error('Load error:', e)
    }
  }

  const connectWebSocket = () => {
    wsRef.current = api.connectMonitor((data) => {
      setLiveLogs(prev => [{
        ...data,
        id: Date.now()
      }, ...prev].slice(0, 100))
      if (liveRef.current) {
        liveRef.current.scrollTop = 0
      }
    })
  }

  const resolveFlag = async (flagId) => {
    await api.resolveFlag(flagId)
    setFlags(prev => prev.filter(f => f.flag_id !== flagId))
  }

  const urgencyColor = (urgency) => {
    const colors = {
      critical: 'text-red-400 bg-red-900/30',
      high: 'text-orange-400 bg-orange-900/30',
      medium: 'text-yellow-400 bg-yellow-900/30',
      low: 'text-green-400 bg-green-900/30'
    }
    return colors[urgency] || 'text-gray-400 bg-gray-800'
  }

  const agentColor = (name) => {
    const colors = {
      'Support Agent': 'bg-blue-600',
      'Shipping Agent': 'bg-green-600',
      'Compensation Agent': 'bg-orange-600',
      'Response Agent': 'bg-purple-600'
    }
    return colors[name] || 'bg-gray-600'
  }

  const TABS = [
    { id: 'live', label: 'Live Feed' },
    { id: 'conversations', label: 'Conversations' },
    { id: 'flags', label: `Flags ${flags.length > 0 ? `(${flags.length})` : ''}` },
    { id: 'runs', label: 'Workflow Runs' },
    { id: 'logs', label: 'Agent Logs' }
  ]

  return (
    <div className="p-6 h-full flex flex-col gap-4">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Runs', value: runs.length },
          { label: 'Conversations', value: conversations.length },
          { label: 'Open Flags', value: flags.length },
          {
            label: 'Total Cost',
            value: `$${runs.reduce((s, r) =>
              s + (r.total_cost_usd || 0), 0).toFixed(4)}`
          }
        ].map(stat => (
          <div key={stat.label}
            className="bg-gray-900 rounded-xl p-4 border
              border-gray-800">
            <p className="text-gray-400 text-xs">{stat.label}</p>
            <p className="text-white text-2xl font-bold mt-1">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-800">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium
              border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-purple-500 text-purple-400'
                : 'border-transparent text-gray-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto">

        {/* Live Feed */}
        {activeTab === 'live' && (
          <div ref={liveRef}
            className="space-y-2 h-full overflow-auto">
            {liveLogs.length === 0 && (
              <div className="flex flex-col items-center
                justify-center h-64 text-gray-500">
                <div className="w-3 h-3 bg-green-400 rounded-full
                  animate-pulse mb-3"/>
                <p>Waiting for messages...</p>
                <p className="text-xs mt-1">
                  Send a message to your Telegram bot
                </p>
              </div>
            )}
            {liveLogs.map(log => (
              <div key={log.id}
                className="bg-gray-900 rounded-lg p-3 border
                  border-gray-800 flex items-start gap-3">
                <div className={`w-2 h-2 rounded-full mt-1.5
                  flex-shrink-0 ${
                  log.type === 'workflow_complete'
                    ? 'bg-green-400'
                    : log.type === 'workflow_error'
                    ? 'bg-red-400'
                    : 'bg-blue-400'
                }`}/>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono
                      text-purple-400">
                      {log.type}
                    </span>
                    {log.agent_name && (
                      <span className={`text-xs px-2 py-0.5
                        rounded-full text-white
                        ${agentColor(log.agent_name)}`}>
                        {log.agent_name}
                      </span>
                    )}
                  </div>
                  {log.message && (
                    <p className="text-gray-300 text-sm mt-1
                      truncate">
                      {log.message}
                    </p>
                  )}
                  {log.action && (
                    <p className="text-gray-400 text-xs mt-1">
                      Action: {log.action}
                    </p>
                  )}
                  {log.total_tokens > 0 && (
                    <p className="text-gray-500 text-xs">
                      Tokens: {log.total_tokens} |
                      Cost: ${log.total_cost_usd?.toFixed(6)}
                    </p>
                  )}
                </div>
                <span className="text-gray-600 text-xs
                  flex-shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Conversations */}
        {activeTab === 'conversations' && (
          <div className="space-y-2">
            {conversations.map(conv => (
              <div key={conv.conversation_id}
                className="bg-gray-900 rounded-lg p-3 border
                  border-gray-800 flex items-start gap-3">
                <span className={`text-xs px-2 py-0.5 rounded
                  flex-shrink-0 ${
                  conv.direction === 'inbound'
                    ? 'bg-blue-900 text-blue-300'
                    : 'bg-purple-900 text-purple-300'
                }`}>
                  {conv.direction}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 text-xs">
                      {conv.agent_name}
                    </span>
                    {conv.intent && (
                      <span className="text-gray-600 text-xs">
                        • {conv.intent}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-300 text-sm mt-0.5">
                    {conv.message}
                  </p>
                </div>
                <span className="text-gray-600 text-xs
                  flex-shrink-0">
                  {new Date(conv.timestamp)
                    .toLocaleTimeString()}
                </span>
              </div>
            ))}
            {conversations.length === 0 && (
              <p className="text-gray-500 text-center py-12">
                No conversations yet
              </p>
            )}
          </div>
        )}

        {/* Flags */}
        {activeTab === 'flags' && (
          <div className="space-y-3">
            {flags.map(flag => (
              <div key={flag.flag_id}
                className="bg-gray-900 rounded-xl p-4 border
                  border-gray-800">
                <div className="flex items-start
                  justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs px-2 py-0.5
                        rounded-full font-medium
                        ${urgencyColor(flag.urgency)}`}>
                        {flag.urgency.toUpperCase()}
                      </span>
                      <span className="text-gray-500 text-xs">
                        {flag.raised_by_agent}
                      </span>
                    </div>
                    <p className="text-white text-sm">
                      {flag.reason}
                    </p>
                    {flag.order_id && (
                      <p className="text-gray-500 text-xs mt-1">
                        Order: {flag.order_id}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => resolveFlag(flag.flag_id)}
                    className="bg-green-700 hover:bg-green-600
                      text-white text-xs px-3 py-1.5 rounded-lg
                      transition-colors flex-shrink-0">
                    Resolve
                  </button>
                </div>
              </div>
            ))}
            {flags.length === 0 && (
              <p className="text-gray-500 text-center py-12">
                No open flags
              </p>
            )}
          </div>
        )}

        {/* Workflow Runs */}
        {activeTab === 'runs' && (
          <div className="space-y-2">
            {runs.map(run => (
              <div key={run.run_id}
                className="bg-gray-900 rounded-lg p-3 border
                  border-gray-800">
                <div className="flex items-center
                  justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-300 text-sm truncate">
                      {run.trigger_message}
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-gray-500 text-xs">
                        {run.telegram_chat_id}
                      </span>
                      <span className="text-gray-600 text-xs">
                        {run.total_tokens} tokens
                      </span>
                      <span className="text-gray-600 text-xs">
                        ${run.total_cost_usd?.toFixed(6)}
                      </span>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-0.5
                    rounded-full flex-shrink-0 ${
                    run.status === 'completed'
                      ? 'bg-green-900 text-green-400'
                      : run.status === 'failed'
                      ? 'bg-red-900 text-red-400'
                      : 'bg-yellow-900 text-yellow-400'
                  }`}>
                    {run.status}
                  </span>
                </div>
              </div>
            ))}
            {runs.length === 0 && (
              <p className="text-gray-500 text-center py-12">
                No workflow runs yet
              </p>
            )}
          </div>
        )}

        {/* Agent Logs */}
        {activeTab === 'logs' && (
          <div className="space-y-2">
            {logs.map(log => (
              <div key={log.log_id}
                className="bg-gray-900 rounded-lg p-3 border
                  border-gray-800 flex items-center gap-3">
                <span className={`w-2 h-2 rounded-full
                  flex-shrink-0 ${
                  log.status === 'success'
                    ? 'bg-green-400'
                    : 'bg-red-400'
                }`}/>
                <span className={`text-xs px-2 py-0.5
                  rounded-full text-white flex-shrink-0
                  ${agentColor(log.agent_name)}`}>
                  {log.agent_name}
                </span>
                <span className="text-gray-300 text-sm flex-1
                  truncate">
                  {log.action}
                </span>
                {log.tool_called && (
                  <span className="text-gray-500 text-xs
                    flex-shrink-0">
                    {log.tool_called}
                  </span>
                )}
                <span className="text-gray-600 text-xs
                  flex-shrink-0">
                  {log.tokens_used}t
                </span>
                <span className="text-gray-600 text-xs
                  flex-shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
            {logs.length === 0 && (
              <p className="text-gray-500 text-center py-12">
                No agent logs yet
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}