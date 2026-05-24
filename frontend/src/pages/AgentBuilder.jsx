import { useState, useEffect } from 'react'
import api from '../api/client'

const AVAILABLE_TOOLS = [
  'read_history', 'save_conversation',
  'get_order_by_customer', 'get_order_status',
  'get_delivery_estimate', 'get_product_stock',
  'evaluate_compensation', 'generate_coupon',
  'raise_flag', 'check_guardrail',
  'send_telegram_message'
]

const AVAILABLE_SKILLS = [
  'conversation_management', 'intent_classification',
  'order_lookup', 'inventory_check',
  'refund_processing', 'escalation',
  'response_crafting', 'product_discovery'
]

const EMPTY_AGENT = {
  name: '',
  role: '',
  system_prompt: '',
  model: 'llama-3.1-70b-versatile',
  tools: [],
  skills: [],
  guardrails: {},
  interaction_rules: [],
  memory_enabled: false,
  channel: 'telegram',
  schedule: ''
}

export default function AgentBuilder() {
  const [agents, setAgents] = useState([])
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(EMPTY_AGENT)
  const [newRule, setNewRule] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => { loadAgents() }, [])

  const loadAgents = async () => {
    const data = await api.getAgents()
    setAgents(data)
  }

  const selectAgent = (agent) => {
    setSelected(agent.agent_id)
    setForm({
      ...agent,
      tools: parseJSON(agent.tools, []),
      skills: parseJSON(agent.skills, []),
      guardrails: parseJSON(agent.guardrails, {}),
      interaction_rules: parseJSON(agent.interaction_rules, [])
    })
    setMessage('')
  }

  const parseJSON = (val, fallback) => {
    if (!val) return fallback
    if (typeof val === 'object') return val
    try { return JSON.parse(val) } catch { return fallback }
  }

  const newAgent = () => {
    setSelected(null)
    setForm(EMPTY_AGENT)
    setMessage('')
  }

  const toggleTool = (tool) => {
    setForm(f => ({
      ...f,
      tools: f.tools.includes(tool)
        ? f.tools.filter(t => t !== tool)
        : [...f.tools, tool]
    }))
  }

  const toggleSkill = (skill) => {
    setForm(f => ({
      ...f,
      skills: f.skills.includes(skill)
        ? f.skills.filter(s => s !== skill)
        : [...f.skills, skill]
    }))
  }

  const addRule = () => {
    if (!newRule.trim()) return
    setForm(f => ({
      ...f,
      interaction_rules: [...f.interaction_rules, newRule.trim()]
    }))
    setNewRule('')
  }

  const removeRule = (idx) => {
    setForm(f => ({
      ...f,
      interaction_rules: f.interaction_rules.filter(
        (_, i) => i !== idx)
    }))
  }

  const save = async () => {
    setLoading(true)
    try {
      if (selected) {
        await api.updateAgent(selected, form)
        setMessage('Agent updated successfully')
      } else {
        await api.createAgent(form)
        setMessage('Agent created successfully')
      }
      loadAgents()
    } catch (e) {
      setMessage('Error saving agent')
    }
    setLoading(false)
  }

  const deleteAgent = async () => {
    if (!selected) return
    if (!confirm('Delete this agent?')) return
    await api.deleteAgent(selected)
    newAgent()
    loadAgents()
  }

  return (
    <div className="flex h-full">
      {/* Agent List */}
      <div className="w-56 bg-gray-900 border-r border-gray-800
        flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <button
            onClick={newAgent}
            className="w-full bg-purple-600 hover:bg-purple-500
              text-white text-sm font-medium py-2 px-3
              rounded-lg transition-colors">
            + New Agent
          </button>
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {agents.map(agent => (
            <button
              key={agent.agent_id}
              onClick={() => selectAgent(agent)}
              className={`w-full text-left px-3 py-2.5
                rounded-lg text-sm transition-colors ${
                selected === agent.agent_id
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800'
              }`}>
              <div className="font-medium">{agent.name}</div>
              <div className="text-xs opacity-60">{agent.role}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Agent Form */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-2xl space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">
              {selected ? 'Edit Agent' : 'New Agent'}
            </h2>
            {selected && (
              <button
                onClick={deleteAgent}
                className="text-red-400 hover:text-red-300
                  text-sm transition-colors">
                Delete Agent
              </button>
            )}
          </div>

          {message && (
            <div className="bg-green-900/30 border border-green-700
              text-green-400 text-sm px-4 py-2 rounded-lg">
              {message}
            </div>
          )}

          {/* Basic Fields */}
          <div className="bg-gray-900 rounded-xl p-5 border
            border-gray-800 space-y-4">
            <h3 className="text-white font-medium">
              Basic Configuration
            </h3>
            {[
              { key: 'name', label: 'Agent Name',
                placeholder: 'Support Agent' },
              { key: 'role', label: 'Role',
                placeholder: 'support' },
            ].map(field => (
              <div key={field.key}>
                <label className="text-gray-400 text-xs
                  block mb-1">
                  {field.label}
                </label>
                <input
                  value={form[field.key]}
                  onChange={e => setForm(f => ({
                    ...f, [field.key]: e.target.value }))}
                  placeholder={field.placeholder}
                  className="w-full bg-gray-800 border
                    border-gray-700 text-white text-sm
                    px-3 py-2 rounded-lg focus:outline-none
                    focus:border-purple-500"
                />
              </div>
            ))}
            <div>
              <label className="text-gray-400 text-xs
                block mb-1">
                System Prompt
              </label>
              <textarea
                value={form.system_prompt}
                onChange={e => setForm(f => ({
                  ...f, system_prompt: e.target.value }))}
                rows={4}
                placeholder="You are a helpful agent..."
                className="w-full bg-gray-800 border
                  border-gray-700 text-white text-sm
                  px-3 py-2 rounded-lg focus:outline-none
                  focus:border-purple-500 resize-none"
              />
            </div>
            <div className="flex items-center gap-3">
              <label className="text-gray-400 text-xs">
                Memory Enabled
              </label>
              <button
                onClick={() => setForm(f => ({
                  ...f, memory_enabled: !f.memory_enabled }))}
                className={`w-10 h-5 rounded-full transition-colors
                  relative ${form.memory_enabled
                  ? 'bg-purple-600' : 'bg-gray-700'}`}>
                <div className={`w-4 h-4 bg-white rounded-full
                  absolute top-0.5 transition-transform ${
                  form.memory_enabled
                    ? 'translate-x-5' : 'translate-x-0.5'
                }`}/>
              </button>
            </div>
          </div>

          {/* Skills / Tools */}
          <div className="bg-gray-900 rounded-xl p-5 border
            border-gray-800 space-y-4">
            <h3 className="text-white font-medium">
              Skills & Tools
            </h3>
            <div>
              <label className="text-gray-400 text-xs
                block mb-2">
                Skills
              </label>
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_SKILLS.map(skill => (
                  <button
                    key={skill}
                    onClick={() => toggleSkill(skill)}
                    className={`text-xs px-2 py-1 rounded-md
                      transition-colors ${
                      form.skills?.includes(skill)
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-800 text-gray-400'
                    }`}>
                    {skill}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-gray-400 text-xs
                block mb-2">
                Tools
              </label>
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_TOOLS.map(tool => (
                  <button
                    key={tool}
                    onClick={() => toggleTool(tool)}
                    className={`text-xs px-2 py-1 rounded-md
                      font-mono transition-colors ${
                      form.tools?.includes(tool)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-400'
                    }`}>
                    {tool}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Interaction Rules */}
          <div className="bg-gray-900 rounded-xl p-5 border
            border-gray-800 space-y-3">
            <h3 className="text-white font-medium">
              Interaction Rules
            </h3>
            <div className="space-y-2">
              {form.interaction_rules?.map((rule, idx) => (
                <div key={idx}
                  className="flex items-center gap-2
                    bg-gray-800 rounded-lg px-3 py-2">
                  <span className="text-gray-300 text-sm flex-1">
                    {rule}
                  </span>
                  <button
                    onClick={() => removeRule(idx)}
                    className="text-gray-600 hover:text-red-400
                      text-xs transition-colors">
                    ✕
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={newRule}
                onChange={e => setNewRule(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addRule()}
                placeholder="Add a rule..."
                className="flex-1 bg-gray-800 border border-gray-700
                  text-white text-sm px-3 py-2 rounded-lg
                  focus:outline-none focus:border-purple-500"
              />
              <button
                onClick={addRule}
                className="bg-gray-700 hover:bg-gray-600
                  text-white text-sm px-3 py-2 rounded-lg
                  transition-colors">
                Add
              </button>
            </div>
          </div>

          {/* Save */}
          <button
            onClick={save}
            disabled={loading}
            className="w-full bg-purple-600 hover:bg-purple-500
              disabled:opacity-50 text-white font-medium
              py-3 rounded-xl transition-colors">
            {loading ? 'Saving...' : 'Save Agent'}
          </button>
        </div>
      </div>
    </div>
  )
}