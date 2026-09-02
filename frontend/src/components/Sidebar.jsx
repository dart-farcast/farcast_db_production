import React, { useEffect } from 'react'
import { useStore } from '../store'
import MultiSelect from './MultiSelect'

export default function Sidebar({ onSearch }) {
  const { filters, setFilter, clearFilters, stats, assayTypes } = useStore()

  const activeAssays = filters.assay

  const toggleAssay = (name) => {
    const cur = filters.assay
    if (cur.includes(name)) {
      setFilter('assay', cur.filter(a => a !== name))
    } else {
      setFilter('assay', [...cur, name])
    }
  }

  const assayCounts = stats?.assay_samples ?? {}

  return (
    <aside>
      {/* ── Qualification Status Toggle ────────────────────────────────── */}
      <div className="sb-section qual-toggle-section">
        <div className="qual-toggle-card">
          <div className="qual-toggle-text">
            <span className="qual-toggle-label">Qualified Samples Only</span>
            <span className="qual-toggle-sub">Based on Final Qualification</span>
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={filters.qualified_only}
              onChange={e => setFilter('qualified_only', e.target.checked)}
            />
            <span className="slider round"></span>
          </label>
        </div>
      </div>

      {/* ── Search filters ─────────────────────────────────────────── */}
      <div className="sb-section">
        <div className="sb-head">Filters</div>

        <MultiSelect
          field="drug"
          label="Drug"
          placeholder="e.g. Nivolumab_Cmax, Cisplatin…"
          selected={filters.drug}
          onChange={v => setFilter('drug', v)}
        />
        <MultiSelect
          field="arm"
          label="Arm Code"
          placeholder="e.g. ARM1, RXA, RXB…"
          selected={filters.arm}
          onChange={v => setFilter('arm', v)}
        />
        <MultiSelect
          field="indication"
          label="Indication (Cancer Type)"
          placeholder="e.g. HNSCC, Ca Breast, RCC, Ca Ovary…"
          selected={filters.indication}
          onChange={v => setFilter('indication', v)}
        />
        <MultiSelect
          field="tumor_site"
          label="Tumor Site"
          placeholder="e.g. Breast, Lung, Ovary…"
          selected={filters.tumor_site}
          onChange={v => setFilter('tumor_site', v)}
        />
        <MultiSelect
          field="study"
          label="Study Type"
          placeholder="e.g. BioBank, Biopharma, Internal R&D…"
          selected={filters.study}
          onChange={v => setFilter('study', v)}
        />
        <MultiSelect
          field="project"
          label="Project Code"
          placeholder="e.g. PRJ-001, 1K Study…"
          selected={filters.project}
          onChange={v => setFilter('project', v)}
        />


        <div className="ff">
          <label>Sample ID (partial match)</label>
          <input
            className="ft-input"
            placeholder="e.g. FBR1Q220065, FBR1W240055…"
            value={filters.sample}
            onChange={e => setFilter('sample', e.target.value)}
            onKeyDown={e => e.key === 'Enter' && onSearch()}
          />
        </div>
      </div>

      {/* ── Assay picker ───────────────────────────────────────────── */}
      <div className="sb-section">
        <div className="sb-head">Assay Data</div>
        <div className="assay-pick">
          {assayTypes.map(at => (
            <button
              key={at.name}
              className={`assay-btn${activeAssays.includes(at.name) ? ' active' : ''}`}
              onClick={() => toggleAssay(at.name)}
            >
              <span>{at.name}</span>
              <span className="acount">{assayCounts[at.name] ?? at.rows}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Actions ────────────────────────────────────────────────── */}
      <div className="sb-section">
        <button className="btn-go" onClick={onSearch}>🔍 Search</button>
        <button className="btn-clr" onClick={() => { clearFilters() }}>Clear All</button>
      </div>
    </aside>
  )
}
