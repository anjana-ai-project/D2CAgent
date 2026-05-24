import { useState } from 'react'
import AgentBuilder from './pages/AgentBuilder'
import WorkflowCanvas from './pages/WorkflowCanvas'
import Monitor from './pages/Monitor'
import KnowledgeBase from './pages/KnowledgeBase'
import Guardrails from './pages/Guardrails'

const PAGES = [
  { id: 'monitor', label: 'Monitor', icon: '📊' },
  { id: 'agents', label: 'Agents', icon: '🤖' },
  { id: 'workflows', label: 'Workflows', icon: '🔀' },
  { id: 'knowledge', label: 'Knowledge', icon: '📚' },
  { id: 'guardrails', label: 'Guardrails', icon: '🛡️' },
]

export default function App() {
  const [activePage, setActivePage] = useState('monitor')

  const renderPage = () => {
    switch (activePage) {
      case 'monitor': return <Monitor />
      case 'agents': return <AgentBuilder />
      case 'workflows': return <WorkflowCanvas />
      case 'knowledge': return <KnowledgeBase />
      case 'guardrails': return <Guardrails />
      default: return <Monitor />
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="bg-gray-900 border-b border-gray-800
        px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-purple-600 rounded-lg
              flex items-center justify-center text-sm font-bold">
              K
            </div>
            <div>
              <h1 className="text-white font-bold text-lg">
                Kreactive Toys
              </h1>
              <p className="text-gray-400 text-xs">
                AI Agent Platform
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-400 rounded-full
              animate-pulse"/>
            <span className="text-green-400 text-xs">Live</span>
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-65px)]">
        <nav className="w-48 bg-gray-900 border-r border-gray-800
          flex flex-col py-4 gap-1 px-2">
          {PAGES.map(page => (
            <button
              key={page.id}
              onClick={() => setActivePage(page.id)}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg
                text-sm font-medium transition-colors text-left
                ${activePage === page.id
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }
              `}
            >
              <span>{page.icon}</span>
              <span>{page.label}</span>
            </button>
          ))}
        </nav>

        <main className="flex-1 overflow-auto">
          {renderPage()}
        </main>
      </div>
    </div>
  )
}