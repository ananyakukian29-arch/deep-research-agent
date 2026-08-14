import { useState } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Search, Loader2, Database, AlertCircle, History, Clock, Cpu, BarChart2, Download, Plus } from 'lucide-react'
import './App.css'

function App() {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('idle') 
  const [progressMsg, setProgressMsg] = useState('')
  const [report, setReport] = useState('')
  const [error, setError] = useState('')
  const [metrics, setMetrics] = useState(null)
  const [history, setHistory] = useState([])

  const API_BASE_URL = 'http://127.0.0.1:8000'

  const startResearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setStatus('loading')
    setProgressMsg('Initializing multi-agent workflow...')
    setReport('')
    setError('')
    setMetrics(null)

    try {
      const res = await axios.post(`${API_BASE_URL}/research`, { query })
      const taskId = res.data.task_id
      pollStatus(taskId, query)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to connect to FastAPI.')
      setStatus('error')
    }
  }

  const pollStatus = async (taskId, originalQuery) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/status/${taskId}`)
      const taskStatus = res.data.status

      if (taskStatus === 'SUCCESS') {
        const finalReport = res.data.result.report || res.data.report
        const finalLatency = res.data.result.latency || res.data.latency
        
        setReport(finalReport)
        setMetrics({
          latency: finalLatency,
          taskId: res.data.result.task_id || res.data.task_id,
          savedId: res.data.result.saved_id || res.data.saved_id
        })
        setStatus('success')
        
        setHistory(prev => {
          if (prev.find(item => item.id === taskId)) return prev;
          return [{ id: taskId, query: originalQuery, report: finalReport, metrics: { latency: finalLatency } }, ...prev]
        })
      } else if (taskStatus === 'FAILURE') {
        setError(res.data.error || 'The research task failed during execution.')
        setStatus('error')
      } else {
        setProgressMsg(res.data.details || 'Agents are processing...')
        setTimeout(() => pollStatus(taskId, originalQuery), 2000)
      }
    } catch (err) {
      setError('Connection lost while polling task status.')
      setStatus('error')
    }
  }

  const loadHistoryItem = (item) => {
    setQuery(item.query)
    setReport(item.report)
    setMetrics(item.metrics)
    setStatus('success')
    setError('')
  }

  // NEW: Export feature
  const handleExport = () => {
    if (!report) return;
    const blob = new Blob([report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research_${metrics?.taskId?.substring(0, 6) || 'export'}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const startNewSession = () => {
    setQuery('')
    setStatus('idle')
    setReport('')
    setMetrics(null)
  }

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <Database size={20} className="text-blue-500" />
          <span className="gradient-text">Sentinel Core</span>
          <button onClick={startNewSession} style={{marginLeft: 'auto', background: 'transparent', border: 'none', color: '#71717a', cursor: 'pointer'}}>
            <Plus size={18} />
          </button>
        </div>
        <div className="history-list">
          <div className="history-title">
            <History size={14} /> Session History
          </div>
          {history.length === 0 ? (
             <div className="empty-history">No active sessions.</div>
          ) : (
            history.map((item, index) => (
              <button 
                key={index} 
                className={`history-item ${metrics?.taskId === item.id ? 'active' : ''}`}
                onClick={() => loadHistoryItem(item)}
                title={item.query}
              >
                {item.query}
              </button>
            ))
          )}
        </div>
      </aside>

      <main className="main-content">
        <header className="search-header">
          <form onSubmit={startResearch} className="search-form">
            <div className="search-input-wrapper">
              <Search className="search-icon" size={20} />
              <input 
                type="text" 
                value={query} 
                onChange={(e) => setQuery(e.target.value)} 
                placeholder="Initialize Deep Research..." 
                disabled={status === 'loading'}
              />
            </div>
            <button type="submit" className="submit-btn glow-effect" disabled={status === 'loading' || !query.trim()}>
              {status === 'loading' ? (
                <><Loader2 className="spinner" size={18} /> Processing</>
              ) : 'Run Analysis'}
            </button>
          </form>
        </header>

        <section className="results-area">
          {status === 'idle' && (
             <div className="status-container">
               <div className="pulse-ring">
                 <Cpu size={48} className="idle-icon" />
               </div>
               <h2>System Ready</h2>
               <p>Enter a query above to initiate the LangGraph agent pipeline.</p>
             </div>
          )}

          {status === 'loading' && (
            <div className="status-container">
              <Loader2 className="spinner" size={48} />
              <h3 className="loading-text">Executing Pipeline</h3>
              <p className="loading-subtext">{progressMsg}</p>
            </div>
          )}

          {status === 'error' && (
            <div className="error-card">
              <AlertCircle size={24} />
              <div>
                <strong>Execution Failure:</strong> {error}
              </div>
            </div>
          )}

          {status === 'success' && report && (
            <div className="content-container">
              <div className="report-card markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {report}
                </ReactMarkdown>
              </div>

              <div className="meta-sidebar">
                <div className="meta-card">
                  <h3><BarChart2 size={16} /> Performance Metrics</h3>
                  <div className="metric-row">
                    <span className="metric-label">Total Latency</span>
                    <span className="metric-value">{metrics?.latency ? `${metrics.latency}s` : 'N/A'}</span>
                  </div>
                  <div className="metric-row">
                    <span className="metric-label">Execution DB ID</span>
                    <span className="metric-value text-xs">{metrics?.savedId ? `${metrics.savedId.substring(0,8)}...` : 'N/A'}</span>
                  </div>
                  {/* NEW: Export Button */}
                  <button onClick={handleExport} className="export-btn">
                    <Download size={16} /> Export Markdown
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App