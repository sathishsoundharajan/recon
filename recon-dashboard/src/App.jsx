import React, { useState, useEffect, useMemo } from 'react';
import Papa from 'papaparse';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import ReactMarkdown from 'react-markdown';
import { Search, Filter, AlertTriangle, CheckCircle, ChevronDown, Monitor, Truck, Package, X, HelpCircle, BookOpen, MessageCircle } from 'lucide-react';

// Samsung Brand Colors - Strictly Applied
const THEME = {
  blue: '#1428a0',     // Primary Brand Color
  black: '#000000',
  white: '#FFFFFF',
  error: '#de2f2f',    // Sharp Red
  gray: '#8f8f8f',
  savings: '#00c4b4',  // Teal (Good Variance)
};


// Simplified Status Config for Chart
const getStatusCategory = (status) => {
  if (status.includes('MATCH')) return 'Verified';
  if (status.includes('DISCREPANCY') || status.includes('OVERCHARGED')) return 'Overcharged';
  if (status.includes('UNDERCHARGED')) return 'Savings';
  return 'Review Needed';
};

const CHART_COLORS = {
  'Verified': THEME.blue,
  'Overcharged': THEME.error,
  'Savings': THEME.savings,
  'Review Needed': THEME.gray,
};

// Basic Questions for PandasAI
const SUGGESTED_QUESTIONS = [
  "What is the total overcharged amount?",
  "Show me the top 5 highest variances.",
  "How many orders were verified?",
  "List all savings by strategy.",
];

// Chat Widget Component
const ChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Hello! I am your Reconciliation Assistant. Ask me anything about the data or strategies.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  // Auto-scroll to bottom
  const messagesEndRef = React.useRef(null);
  useEffect(() => {
    if (isOpen) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  const handleSend = async (text = null) => {
    const queryText = text || input;
    if (!queryText.trim()) return;

    setMessages(prev => [...prev, { role: 'user', text: queryText }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', text: data.response }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Error: Could not connect to the local AI server. Please ensure chat_server.py is running.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-8 right-8 z-[100] font-sans">
      {/* Chat Window */}
      {isOpen && (
        <div className="mb-4 w-[400px] h-[600px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden animate-in slide-in-from-bottom-10 fade-in duration-300">
          {/* Header */}
          <div className="bg-black text-white p-4 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Monitor className="w-4 h-4" /> {/* Using Monitor as generic AI icon if custom unavailable */}
              <span className="font-bold text-sm">Recon AI Assistant</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: THEME.blue, color: 'white' }}>BETA</span>
            </div>
            <button onClick={() => setIsOpen(false)} className="hover:bg-gray-800 p-1 rounded transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#f9f9f9]">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed shadow-sm ${msg.role === 'user' ? 'text-white rounded-br-none' : 'bg-white border border-gray-200 text-black rounded-bl-none'}`}
                  style={{ backgroundColor: msg.role === 'user' ? THEME.blue : undefined }}
                >
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                </div>
              </div>
            ))}

            {/* Suggested Questions (Only show if few messages) */}
            {messages.length < 3 && !loading && (
              <div className="flex flex-col gap-2 mt-4 px-2">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Suggested Questions</span>
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    className="text-left text-xs p-3 bg-white border border-gray-200 rounded-xl hover:border-black hover:shadow-sm transition-all text-gray-700 font-medium"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 p-3 rounded-2xl rounded-bl-none shadow-sm">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-75"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-150"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 bg-white border-t border-gray-100">
            <div className="relative">
              <input
                className="w-full bg-[#f0f0f0] rounded-full pl-5 pr-12 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-black transition-all"
                placeholder="Ask about discrepancies, totals..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                disabled={loading}
              />
              <button
                onClick={() => handleSend()}
                disabled={loading || !input.trim()}
                className={`absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full transition-colors ${loading || !input.trim() ? 'bg-gray-300 cursor-not-allowed' : 'bg-black text-white hover:bg-[#333]'}`}
              >
                <div className="w-4 h-4 flex items-center justify-center">➜</div>
              </button>
            </div>
            <div className="text-[10px] text-center text-gray-400 mt-2">
              AI can make mistakes. Verify important data.
            </div>
          </div>
        </div>
      )}

      {/* FAB */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-black text-white p-4 rounded-full shadow-2xl hover:scale-110 transition-all duration-300 group flex items-center justify-center gap-2"
        style={{ width: isOpen ? '60px' : 'auto', height: '60px' }}
      >
        <div className="relative flex items-center justify-center">
          {isOpen ? <X className="w-6 h-6" /> : <MessageCircle className="w-6 h-6" />}
        </div>
        {!isOpen && <span className="font-bold pr-2 whitespace-nowrap overflow-hidden max-w-0 group-hover:max-w-xs transition-all duration-500 ease-in-out">Chat with Data</span>}
      </button>
    </div>
  );
};

function App() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('All');
  const [showStats, setShowStats] = useState(true);
  // View Mode: 'all', 'verified', 'overcharged', 'savings'
  const [viewMode, setViewMode] = useState('all');

  // Strategy Modal State
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [strategyDocs, setStrategyDocs] = useState({});

  useEffect(() => {
    // 1. Load CSV Data
    Papa.parse('/recon_final_v2.csv', {
      download: true, header: true, skipEmptyLines: true,
      complete: (results) => { setData(results.data); setLoading(false); }
    });

    // 2. Load Strategy Markdown
    fetch('/reconciliation_strategies.md')
      .then(r => r.text())
      .then(text => {
        const sections = text.split(/^## /gm);
        const docs = {};
        sections.forEach(section => {
          // Look for Strategy Key logic added in MD
          // Format: * **Strategy Key**: `KEY` or * **Strategy Key**: KEY
          const keyMatch = section.match(/\*\s+\*\*Strategy Key\*\*: [`"]?(.*?)[`"]?(\r|\n|$)/);
          if (keyMatch) {
            const key = keyMatch[1].trim();
            docs[key] = "## " + section; // Re-add header
          }
        });
        setStrategyDocs(docs);
      })
      .catch(err => console.error("Could not load strategy docs:", err));
  }, []);

  const groupedData = useMemo(() => {
    const groups = {};
    data.forEach(row => {
      const doId = row.Related_Doc ? String(row.Related_Doc).replace('.0', '') : 'Unknown DO';
      if (!groups[doId]) groups[doId] = { id: doId, products: row.Family || 'Unknown', sku: row.SKUs || '', charges: [], totalAmount: 0 };
      groups[doId].charges.push(row);
      groups[doId].totalAmount += parseFloat(row.Amount || 0);
    });
    return Object.values(groups).sort((a, b) => b.totalAmount - a.totalAmount);
  }, [data]);

  const chartData = useMemo(() => {
    const s = { 'Verified': 0, 'Overcharged': 0, 'Savings': 0, 'Review Needed': 0 };
    data.forEach(row => {
      if (strategyFilter !== 'All' && row.Strategy !== strategyFilter) return;
      const cat = getStatusCategory(row.Status || '');
      s[cat] = (s[cat] || 0) + parseFloat(row.Amount || 0);
    });
    return Object.keys(s).filter(k => s[k] > 0).map(k => ({ name: k, value: s[k], color: CHART_COLORS[k] }));
  }, [data, strategyFilter]);

  const strategies = useMemo(() => ['All', ...Array.from(new Set(data.map(r => r.Strategy).filter(Boolean))).sort()], [data]);

  // Counts for Tabs
  const counts = useMemo(() => {
    return {
      all: groupedData.length,
      verified: groupedData.filter(g => g.charges.every(c => c.Status && c.Status.includes('MATCH'))).length,
      overcharged: groupedData.filter(g => g.charges.some(c => c.Status && (c.Status.includes('DISCREPANCY') || c.Status.includes('OVER')))).length,
      savings: groupedData.filter(g => g.charges.some(c => c.Status && c.Status.includes('UNDER'))).length
    };
  }, [groupedData]);

  const filteredGroups = useMemo(() => {
    let result = groupedData;
    if (searchTerm) {
      const lower = searchTerm.toLowerCase();
      result = result.filter(g => g.id.toLowerCase().includes(lower) || g.products.toLowerCase().includes(lower) || g.sku.toLowerCase().includes(lower));
    }

    // View Mode Filter
    if (viewMode === 'verified') {
      result = result.filter(g => g.charges.every(c => c.Status && c.Status.includes('MATCH')));
    } else if (viewMode === 'overcharged') {
      result = result.filter(g => g.charges.some(c => c.Status && (c.Status.includes('DISCREPANCY') || c.Status.includes('OVER'))));
    } else if (viewMode === 'savings') {
      result = result.filter(g => g.charges.some(c => c.Status && c.Status.includes('UNDER')));
    }

    if (strategyFilter !== 'All') result = result.filter(g => g.charges.some(c => c.Strategy === strategyFilter));
    return result.slice(0, 50);
  }, [groupedData, searchTerm, strategyFilter, viewMode]);

  const formatCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

  if (loading) return <div className="h-screen flex items-center justify-center font-bold text-xl tracking-tight">LOADING DATA...</div>;

  return (
    <div className="min-h-screen bg-white text-black font-sans selection:bg-black selection:text-white relative">
      {/* Universal Nav - Black Bar */}
      <div className="bg-black text-white h-14 flex items-center px-8 justify-between sticky top-0 z-50">
        <div className="font-bold text-xl tracking-tighter">SAMSUNG <span className="font-normal opacity-70 text-sm ml-2">Reconciliation</span></div>
        <div className="text-xs font-bold tracking-widest uppercase opacity-80">Confidential • For Internal Use Only</div>
      </div>

      <div className="max-w-[1600px] mx-auto p-8">

        {/* Hero / Header Section */}
        <div className="mb-12 border-b border-black pb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-5xl font-bold tracking-tight mb-4">Invoice Analytics</h1>
              <div className="flex flex-col md:flex-row justify-between items-end gap-6">
                <p className="text-gray-600 max-w-xl text-lg leading-relaxed">
                  Analysis of <strong>{data.length}</strong> line items across {groupedData.length} delivery orders.
                  Identifying variances against XPO 2017 Contract & 2025 Amendments.
                </p>
              </div>
            </div>
            <div></div>
          </div>

          <div className="flex gap-4 mt-8 justify-end">
            <div className="text-right">
              <div className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-1">Total Verified</div>
              <div className="text-3xl font-bold">{formatCurrency(chartData.find(c => c.name === 'Verified')?.value || 0)}</div>
            </div>
            <div className="w-px bg-gray-300 mx-2"></div>
            <div className="text-right">
              <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: THEME.error }}>Overcharged</div>
              <div className="text-3xl font-bold" style={{ color: THEME.error }}>{formatCurrency(chartData.find(c => c.name === 'Overcharged')?.value || 0)}</div>
            </div>
            <div className="w-px bg-gray-300 mx-2"></div>
            <div className="text-right">
              <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: THEME.savings }}>Savings</div>
              <div className="text-3xl font-bold" style={{ color: THEME.savings }}>{formatCurrency(chartData.find(c => c.name === 'Savings')?.value || 0)}</div>
            </div>
          </div>

        </div>

        {/* Filters & Controls - Clean & Minimal */}
        <div className="flex flex-col md:flex-row gap-6 mb-8 sticky top-14 bg-white/95 backdrop-blur py-4 z-40 border-b border-gray-100 items-center">
          <div className="relative flex-1">
            <Search className="absolute left-0 top-1/2 -translate-y-1/2 w-6 h-6" />
            <input
              className="w-full bg-transparent border-b-2 border-gray-200 focus:border-black py-3 pl-10 pr-4 text-xl outline-none placeholder-gray-400 font-medium transition-colors"
              placeholder="Search Order ID or Product..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-4">
            {/* View Mode Tabs */}
            <div className="flex bg-[#f7f7f7] p-1 rounded-full">
              <button
                onClick={() => setViewMode('all')}
                className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${viewMode === 'all' ? 'bg-black text-white shadow-md' : 'text-gray-500 hover:text-black'}`}
              >
                All <span className="opacity-70 text-xs ml-1">({counts.all})</span>
              </button>
              <button
                onClick={() => setViewMode('verified')}
                className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${viewMode === 'verified' ? 'text-white shadow-md' : 'text-gray-500'}`}
                style={{
                  backgroundColor: viewMode === 'verified' ? THEME.blue : undefined,
                  color: viewMode !== 'verified' ? undefined : 'white'
                }}
              >
                Verified <span className="opacity-70 text-xs ml-1">({counts.verified})</span>
              </button>
              <button
                onClick={() => setViewMode('overcharged')}
                className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${viewMode === 'overcharged' ? 'text-white shadow-md' : 'text-gray-500'}`}
                style={{
                  backgroundColor: viewMode === 'overcharged' ? THEME.error : undefined,
                  color: viewMode !== 'overcharged' ? undefined : 'white'
                }}
              >
                Overcharged <span className="opacity-70 text-xs ml-1">({counts.overcharged})</span>
              </button>
              <button
                onClick={() => setViewMode('savings')}
                className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${viewMode === 'savings' ? 'text-white shadow-md' : 'text-gray-500'}`}
                style={{
                  backgroundColor: viewMode === 'savings' ? THEME.savings : undefined,
                  color: viewMode !== 'savings' ? undefined : 'white'
                }}
              >
                Savings <span className="opacity-70 text-xs ml-1">({counts.savings})</span>
              </button>
            </div>

            <div className="w-px h-8 bg-gray-300 mx-2"></div>
            <div className="relative">
              <select
                className="appearance-none bg-[#f7f7f7] hover:bg-[#e5e5e5] px-6 py-3 pr-12 rounded-full font-bold text-sm cursor-pointer transition-colors outline-none"
                value={strategyFilter}
                onChange={e => setStrategyFilter(e.target.value)}
              >
                {strategies.map(s => <option key={s} value={s}>{s === 'All' ? 'All Strategies' : s}</option>)}
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" />
            </div>
            <button
              onClick={() => setShowStats(!showStats)}
              className="bg-black text-white hover:bg-[#333] px-6 py-3 rounded-full font-bold text-sm transition-colors"
            >
              {showStats ? 'Hide Charts' : 'Show Charts'}
            </button>
          </div>
        </div>

        {/* Analytics Module */}
        {showStats && (
          <div className="mb-16 bg-[#f7f7f7] p-8 md:p-12 animate-in slide-in-from-top-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 items-center">
              <div className="lg:col-span-1">
                <h3 className="text-2xl font-bold mb-4">Cost Distribution</h3>
                <p className="text-gray-600 mb-8 leading-relaxed">
                  Breakdown of invoiced amounts categorized by verification status.
                  Green indicates contract alignment. Red indicates billable variances requiring claim submission.
                </p>
                <div className="space-y-4">
                  {chartData.map(d => (
                    <div key={d.name} className="flex items-center justify-between border-b border-gray-300 pb-2">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full" style={{ background: d.color }}></div>
                        <span className="font-medium">{d.name}</span>
                      </div>
                      <div className="font-bold">{formatCurrency(d.value)}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="lg:col-span-2 h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData} innerRadius={80} outerRadius={120} paddingAngle={2} dataKey="value" stroke="none"
                    >
                      {chartData.map((entry, index) => <Cell key={index} fill={entry.color} />)}
                    </Pie>
                    <RechartsTooltip
                      contentStyle={{ background: '#000', border: 'none', color: '#fff', padding: '12px 20px' }}
                      itemStyle={{ color: '#fff' }}
                      formatter={(val) => formatCurrency(val)}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* Results Data Grid - Flat & Sharp */}
        <div className="space-y-8">
          {filteredGroups.map(group => (
            <div key={group.id} className="border-t-4 border-black pt-6 group">
              {/* Row Header */}
              <div className="flex flex-col md:flex-row justify-between md:items-end mb-6 gap-4">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <h2 className="text-3xl font-bold tracking-tight">{group.id}</h2>
                    <span className="text-white text-[10px] font-bold px-2 py-1 uppercase tracking-widest" style={{ backgroundColor: THEME.blue }}>DO ID</span>
                  </div>
                  <div className="flex items-center gap-6 text-sm font-medium text-gray-500">
                    <span className="flex items-center gap-2"><Package className="w-4 h-4 text-black" /> {group.products}</span>
                    <span className="flex items-center gap-2"><div className="w-4 h-4 flex items-center justify-center font-serif italic text-black font-bold">#</div> {group.sku}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-4xl font-bold tracking-tight">{formatCurrency(group.totalAmount)}</div>
                </div>
              </div>

              {/* Minimal Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-black">
                      <th className="py-3 pr-6 text-xs font-bold uppercase tracking-widest w-40">Status</th>
                      <th className="py-3 px-6 text-xs font-bold uppercase tracking-widest w-48">Strategy</th>
                      <th className="py-3 px-6 text-xs font-bold uppercase tracking-widest">Description / Contract Ref</th>
                      <th className="py-3 pl-6 text-xs font-bold uppercase tracking-widest text-right w-32">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm">
                    {group.charges.map((charge, idx) => (
                      <tr key={idx} className="border-b border-gray-100 group-hover:bg-gray-50 transition-colors">
                        <td className="py-4 pr-6 align-top">
                          <div className="flex items-start gap-2">
                            <div
                              className="mt-1 w-2 h-2 rounded-full"
                              style={{
                                backgroundColor: charge.Status.includes('MATCH') ? THEME.blue :
                                  charge.Status.includes('UNDER') ? THEME.savings :
                                    (charge.Status.includes('DISC') || charge.Status.includes('OVER')) ? THEME.error :
                                      '#D1D5DB' // gray-300
                              }}
                            ></div>
                            <span className="font-bold text-xs uppercase leading-relaxed tracking-wide">
                              {charge.Status.replace(/MATCH|DISCREPANCY|\(|\)/g, '').trim() || (charge.Status.includes('MATCH') ? 'VERIFIED' : 'REVIEW')}
                            </span>
                          </div>
                        </td>
                        <td className="py-4 px-6 align-top font-mono text-xs">
                          {/* Clickable Strategy Link */}
                          {charge.Strategy ? (
                            <button
                              onClick={() => setSelectedStrategy(charge.Strategy)}
                              className="hover:underline hover:text-black transition-colors text-left flex items-center gap-1"
                              style={{ color: THEME.blue }}
                            >
                              {charge.Strategy}
                              <HelpCircle className="w-3 h-3 opacity-50" />
                            </button>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="py-4 px-6 align-top">
                          <div className="font-medium text-black mb-1">{charge.Description}</div>
                          <div className="text-xs text-gray-500 mb-2">{charge.Contract_Ref}</div>
                          {charge.Note && (
                            <div className="bg-[#f0f0f0] p-3 text-xs font-mono text-gray-600 inline-block max-w-xl">
                              {charge.Note}
                              {charge.Diff && Math.abs(parseFloat(charge.Diff)) > 0.01 && (
                                <span
                                  className="block mt-1 font-bold"
                                  style={{ color: parseFloat(charge.Diff) < 0 ? THEME.savings : THEME.error }}
                                >
                                  VARIANCE: {formatCurrency(parseFloat(charge.Diff))}
                                  {parseFloat(charge.Diff) < 0 ? ' (SAVINGS)' : ''}
                                </span>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="py-4 pl-6 align-top text-right font-bold text-lg">
                          {formatCurrency(charge.Amount)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>

        {/* Strategy Documentation Modal */}
        {selectedStrategy && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/20 backdrop-blur-sm"
              onClick={() => setSelectedStrategy(null)}
            ></div>

            {/* Side Panel */}
            <div className="relative w-full max-w-md bg-white shadow-2xl h-full p-8 overflow-y-auto animate-in slide-in-from-right duration-300 border-l border-gray-200">
              <button
                onClick={() => setSelectedStrategy(null)}
                className="absolute top-6 right-6 p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="w-6 h-6 text-gray-500" />
              </button>

              <div className="mt-12">
                <span className="text-xs font-bold uppercase tracking-widest mb-2 block" style={{ color: THEME.blue }}>Strategy Documentation</span>
                <h2 className="text-3xl font-bold mb-6 break-words">{selectedStrategy}</h2>
                <div className="bg-[#f7f7f7] p-6 rounded-none border-l-4 border-black text-sm leading-relaxed text-black markdown-content">
                  <ReactMarkdown>{strategyDocs[selectedStrategy] || "Documentation not found for this strategy."}</ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* AI Chat Widget */}
        <ChatWidget />

      </div>
    </div >
  );
}

export default App;
