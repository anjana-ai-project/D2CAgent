import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState
} from 'reactflow'
import 'reactflow/dist/style.css'
import api from '../api/client'

const nodeStyle = (color) => ({
  background: color,
  color: 'white',
  border: 'none',
  borderRadius: '12px',
  padding: '12px 20px',
  fontSize: '13px',
  fontWeight: '600',
  minWidth: '160px',
  textAlign: 'center'
})

const ORDER_NODES = [
  {
    id: 'support', position: { x: 50, y: 150 },
    data: {
      label: '🤖 Support Agent',
      sublabel: 'Classifies intent'
    },
    style: nodeStyle('#7c3aed')
  },
  {
    id: 'shipping', position: { x: 300, y: 50 },
    data: {
      label: '🚚 Shipping Agent',
      sublabel: 'Checks orders'
    },
    style: nodeStyle('#059669')
  },
  {
    id: 'compensation', position: { x: 300, y: 250 },
    data: {
      label: '🎁 Compensation Agent',
      sublabel: 'Evaluates policy'
    },
    style: nodeStyle('#d97706')
  },
  {
    id: 'response', position: { x: 550, y: 150 },
    data: {
      label: '💬 Response Agent',
      sublabel: 'Sends reply'
    },
    style: nodeStyle('#2563eb')
  }
]

const ORDER_EDGES = [
  {
    id: 'e1', source: 'support', target: 'shipping',
    label: 'order_status', animated: true,
    style: { stroke: '#059669' },
    labelStyle: { fill: '#9ca3af', fontSize: 10 }
  },
  {
    id: 'e2', source: 'support', target: 'compensation',
    label: 'complaint/return', animated: true,
    style: { stroke: '#d97706' },
    labelStyle: { fill: '#9ca3af', fontSize: 10 }
  },
  {
    id: 'e3', source: 'support', target: 'response',
    label: 'faq/product', animated: true,
    style: { stroke: '#2563eb', strokeDasharray: '5,5' },
    labelStyle: { fill: '#9ca3af', fontSize: 10 }
  },
  {
    id: 'e4', source: 'shipping', target: 'compensation',
    label: 'issue found', animated: true,
    style: { stroke: '#d97706' },
    labelStyle: { fill: '#9ca3af', fontSize: 10 }
  },
  {
    id: 'e5', source: 'shipping', target: 'response',
    label: 'resolved', animated: true,
    style: { stroke: '#2563eb', strokeDasharray: '5,5' },
    labelStyle: { fill: '#9ca3af', fontSize: 10 }
  },
  {
    id: 'e6', source: 'compensation', target: 'response',
    label: 'resolution ready', animated: true,
    style: { stroke: '#2563eb' },
    labelStyle: { fill: '#9ca3af', fontSize: 10 }
  },
  {
    id: 'e7', source: 'response', target: 'compensation',
    label: 'insufficient', animated: true,
    style: { stroke: '#ef4444', strokeDasharray: '5,5' },
    labelStyle: { fill: '#9ca3af', fontSize: 10 },
    type: 'default'
  }
]

const DISCOVERY_NODES = [
  {
    id: 'support', position: { x: 100, y: 150 },
    data: { label: '🤖 Support Agent', sublabel: 'Classifies intent' },
    style: nodeStyle('#7c3aed')
  },
  {
    id: 'response', position: { x: 400, y: 150 },
    data: { label: '💬 Response Agent', sublabel: 'Recommends products' },
    style: nodeStyle('#2563eb')
  }
]

const DISCOVERY_EDGES = [
  {
    id: 'e1', source: 'support', target: 'response',
    label: 'product_query', animated: true,
    style: { stroke: '#2563eb' },
    labelStyle: { fill: '#9ca3af', fontSize: 10 }
  }
]

const CustomNode = ({ data }) => (
  <div>
    <div>{data.label}</div>
    {data.sublabel && (
      <div style={{
        fontSize: '10px',
        opacity: 0.7,
        marginTop: '2px'
      }}>
        {data.sublabel}
      </div>
    )}
  </div>
)

const nodeTypes = { custom: CustomNode }

export default function WorkflowCanvas() {
  const [activeTemplate, setActiveTemplate] = useState('order')
  const [nodes, setNodes, onNodesChange] = useNodesState(ORDER_NODES)
  const [edges, setEdges, onEdgesChange] = useEdgesState(ORDER_EDGES)
  const [workflows, setWorkflows] = useState([])

  useEffect(() => {
    api.getWorkflows().then(setWorkflows)
  }, [])

  const loadTemplate = (template) => {
    setActiveTemplate(template)
    if (template === 'order') {
      setNodes(ORDER_NODES)
      setEdges(ORDER_EDGES)
    } else {
      setNodes(DISCOVERY_NODES)
      setEdges(DISCOVERY_EDGES)
    }
  }

  const onConnect = useCallback(
    (params) => setEdges(eds => addEdge(params, eds)),
    [setEdges]
  )

  return (
    <div className="flex flex-col h-full">
      {/* Template selector */}
      <div className="bg-gray-900 border-b border-gray-800
        p-4 flex items-center gap-4">
        <span className="text-gray-400 text-sm">Templates:</span>
        {[
          { id: 'order', label: '📦 Order Support Flow' },
          { id: 'discovery', label: '🔍 Product Discovery Flow' }
        ].map(t => (
          <button
            key={t.id}
            onClick={() => loadTemplate(t.id)}
            className={`text-sm px-4 py-2 rounded-lg
              transition-colors font-medium ${
              activeTemplate === t.id
                ? 'bg-purple-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}>
            {t.label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <div className="w-2 h-2 bg-yellow-400 rounded-full"/>
          <span className="text-yellow-400 text-xs">
            Schedules & Triggers — Coming Soon
          </span>
        </div>
      </div>

      {/* React Flow Canvas */}
      <div className="flex-1 bg-gray-950">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          deleteKeyCode="Delete"
          fitView
          attributionPosition="bottom-left"
        >
          <Background color="#374151" gap={20}/>
          <Controls/>
          <MiniMap
            nodeColor={() => '#7c3aed'}
            maskColor="rgba(0,0,0,0.5)"
          />
        </ReactFlow>
      </div>

      {/* Legend */}
      <div className="bg-gray-900 border-t border-gray-800
        p-3 flex items-center gap-6">
        {[
          { color: '#059669', label: 'Order path' },
          { color: '#d97706', label: 'Compensation path' },
          { color: '#2563eb', label: 'Direct to response' },
          { color: '#ef4444', label: 'Feedback loop' }
        ].map(item => (
          <div key={item.label}
            className="flex items-center gap-2">
            <div className="w-6 h-0.5"
              style={{ background: item.color }}/>
            <span className="text-gray-400 text-xs">
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}