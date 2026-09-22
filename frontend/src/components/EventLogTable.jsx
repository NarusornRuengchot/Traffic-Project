import React, { useState } from 'react';
import { api } from '../services/api';

export function EventLogTable({ eventLogs }) {
  const [filterType, setFilterType] = useState('All');
  const [filterDir, setFilterDir] = useState('All');

  const filteredLogs = eventLogs.filter((ev) => {
    const matchType = filterType === 'All' || ev.Type === filterType;
    const matchDir = filterDir === 'All' || ev.Direction === filterDir;
    return matchType && matchDir;
  });

  const handleExportCSV = () => {
    if (eventLogs.length === 0) {
      alert('No events recorded yet.');
      return;
    }

    const headers = ['Timestamp (s)', 'Real-world Time', 'Vehicle ID', 'Type', 'Direction', 'Traffic Level'];
    const rows = eventLogs.map((ev) => [
      ev['Timestamp (s)'],
      ev['Real-world Time'],
      ev['Vehicle ID'],
      ev['Type'],
      ev['Direction'],
      `"${ev['Traffic Level']}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `traffic_events_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '_')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
          📋 Live Vehicle Crossing Events ({eventLogs.length})
        </h3>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Vehicle Type Filter */}
          <select
            className="form-select"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{ width: 'auto', padding: '4px 8px', fontSize: '0.8rem' }}
          >
            <option value="All">All Types</option>
            <option value="Car">Car</option>
            <option value="Motorcycle">Motorcycle</option>
            <option value="Bus">Bus</option>
            <option value="Truck">Truck</option>
          </select>

          {/* Direction Filter */}
          <select
            className="form-select"
            value={filterDir}
            onChange={(e) => setFilterDir(e.target.value)}
            style={{ width: 'auto', padding: '4px 8px', fontSize: '0.8rem' }}
          >
            <option value="All">All Lanes</option>
            <option value="Inbound">Inbound</option>
            <option value="Outbound">Outbound</option>
          </select>

          <button onClick={handleExportCSV} className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }}>
            📥 Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ maxHeight: '240px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
          <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-input)', borderBottom: '1px solid var(--border-color)', zIndex: 1 }}>
            <tr>
              <th style={{ padding: '8px 12px' }}>Time</th>
              <th style={{ padding: '8px 12px' }}>Vehicle ID</th>
              <th style={{ padding: '8px 12px' }}>Type</th>
              <th style={{ padding: '8px 12px' }}>Direction</th>
              <th style={{ padding: '8px 12px' }}>Traffic Level</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.length > 0 ? (
              filteredLogs.map((ev, idx) => (
                <tr
                  key={idx}
                  style={{
                    borderBottom: '1px solid var(--border-color)',
                    transition: 'background 0.1s ease',
                    backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.02)'
                  }}
                >
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)' }}>{ev['Real-world Time'] || `${ev['Timestamp (s)']}s`}</td>
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontWeight: '600' }}>#{ev['Vehicle ID']}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      background: ev.Type === 'Car' ? 'rgba(59, 130, 246, 0.15)' : ev.Type === 'Motorcycle' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: ev.Type === 'Car' ? '#60a5fa' : ev.Type === 'Motorcycle' ? '#34d399' : '#fbbf24'
                    }}>
                      {ev.Type}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      fontWeight: '600',
                      color: ev.Direction === 'Inbound' ? '#06b6d4' : '#f97316'
                    }}>
                      {ev.Direction === 'Inbound' ? '⬅️ Inbound' : '➡️ Outbound'}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px' }}>{ev['Traffic Level']}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No vehicle crossings recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
