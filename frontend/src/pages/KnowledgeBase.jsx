import { useState, useEffect } from 'react'
import api from '../api/client'

export default function KnowledgeBase() {
  const [products, setProducts] = useState([])

  useEffect(() => {
    api.getProducts().then(setProducts)
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">
          Knowledge Base
        </h2>
        <p className="text-gray-400 text-sm mt-1">
          Product catalog loaded into ChromaDB for
          semantic search
        </p>
      </div>

      {/* ChromaDB Status */}
      <div className="bg-gray-900 rounded-xl p-4 border
        border-gray-800 flex items-center gap-4">
        <div className="w-10 h-10 bg-green-900/50 rounded-lg
          flex items-center justify-center text-xl">
          🧠
        </div>
        <div>
          <p className="text-white font-medium">
            ChromaDB — Vector Store
          </p>
          <p className="text-green-400 text-sm">
            {products.length} products embedded and ready
          </p>
        </div>
        <div className="ml-auto">
          <span className="bg-green-900/30 text-green-400
            text-xs px-3 py-1 rounded-full">
            Active
          </span>
        </div>
      </div>

      {/* Coming Soon */}
      <div className="bg-gray-900 rounded-xl p-4 border
        border-gray-800 border-dashed flex items-center gap-4">
        <div className="w-10 h-10 bg-gray-800 rounded-lg
          flex items-center justify-center text-xl">
          📄
        </div>
        <div>
          <p className="text-gray-400 font-medium">
            Upload Documents
          </p>
          <p className="text-gray-600 text-sm">
            Upload FAQs, policies and brand docs — Coming Soon
          </p>
        </div>
      </div>

      {/* Product Catalog */}
      <div>
        <h3 className="text-white font-medium mb-3">
          Product Catalog — {products.length} items
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {products.map(p => (
            <div key={p.product_id}
              className="bg-gray-900 rounded-xl p-4 border
                border-gray-800">
              <div className="flex items-start
                justify-between gap-2">
                <div>
                  <p className="text-white font-medium text-sm">
                    {p.name}
                  </p>
                  <p className="text-gray-500 text-xs mt-0.5">
                    {p.category} • {p.age_group}
                  </p>
                </div>
                <span className="text-purple-400 text-sm
                  font-bold flex-shrink-0">
                  ₹{p.price}
                </span>
              </div>
              <p className="text-gray-400 text-xs mt-2 line-clamp-2">
                {p.description}
              </p>
              <div className="flex items-center gap-2 mt-3">
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  p.stock_quantity > 0
                    ? 'bg-green-900/30 text-green-400'
                    : 'bg-red-900/30 text-red-400'
                }`}>
                  {p.stock_quantity > 0
                    ? `${p.stock_quantity} in stock`
                    : 'Out of stock'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}