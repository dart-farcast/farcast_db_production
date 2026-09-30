import React, { useState, useEffect, useMemo } from 'react'
import * as XLSX from 'xlsx'
import { useStore } from '../store'
import MultiSelect from './MultiSelect'

export default function PreRebootExplorer() {
  const {
    preRebootFilters, preRebootResults, preRebootTotal,
    preRebootPage, preRebootPageSize, preRebootTotalPages,
    preRebootSortCol, preRebootSortAsc, preRebootLoading,
    preRebootStats, setPreRebootFilter, setPreRebootSort,
    setPreRebootPage, runPreRebootSearch, clearPreRebootFilters,
    authFetch, setPreRebootStats, setCurrentView
  } = useStore()

  const [openRows, setOpenRows] = useState(new Set())
  const [downloadingExcel, setDownloadingExcel] = useState(false)

  // Load initial stats & search on mount
  useEffect(() => {
    authFetch('/api/pre_reboot/stats')
      .then(r => r.json())
      .then(setPreRebootStats)
      .catch(() => {})

    runPreRebootSearch()
  }, [])

  const toggleRow = (id) => {
    setOpenRows(prev => {
      const n = new Set(prev)
      n.has(id) ? n.delete(id) : n.add(id)
      return n
    })
  }

  const handleDownloadExcel = async () => {
    setDownloadingExcel(true)
    try {
      // Fetch up to 1000 matching rows for export
      const qs = new URLSearchParams()
      const arr = (k, v) => { if (v?.length) qs.set(k, v.join(',')) }
      if (preRebootFilters.mbt) qs.set('mbt', preRebootFilters.mbt)
      arr('main_cancer_type', preRebootFilters.main_cancer_type)
      arr('cancer_type', preRebootFilters.cancer_type)
      arr('primary_study', preRebootFilters.primary_study)
      arr('hospital', preRebootFilters.hospital)
      arr('year', preRebootFilters.year)
      if (preRebootFilters.ffpe_block) qs.set('ffpe_block', 'true')
      if (preRebootFilters.scored_only) qs.set('scored_only', 'true')
      qs.set('page', 0)
      qs.set('page_size', 500)

      const res = await authFetch(`/api/pre_reboot/search?${qs.toString()}`)
      const data = await res.json()
      const rows = data.results || []

      if (rows.length === 0) {
        alert("No samples match current filters to export.")
        return
      }

      const wb = XLSX.utils.book_new()
      const ws = XLSX.utils.json_to_sheet(rows)
      XLSX.utils.book_append_sheet(wb, ws, "Pre_Reboot_Biorepository")
      XLSX.writeFile(wb, `Pre_Reboot_Biorepository_${rows.length}_samples.xlsx`)
    } catch (err) {
      console.error("Export error:", err)
      alert("Failed to export Pre-Reboot data.")
    } finally {
      setDownloadingExcel(false)
    }
  }

  const stats = preRebootStats || {}
  const totalSamples = stats.total_samples?.toLocaleString() ?? '22,094'
  const ffpeCount = stats.ffpe_available_count?.toLocaleString() ?? '—'
  const scoredCount = stats.scored_samples_count?.toLocaleString() ?? '—'
  const imageCount = stats.image_samples_count?.toLocaleString() ?? '—'

  return (
    <div className="pre-reboot-layout">
      {/* ── Top Summary Header & Breadcrumbs ── */}
      <div className="pre-reboot-top-banner">
        <div className="banner-text-col">
          <div className="banner-breadcrumb">
            <span className="crumb-link" onClick={() => setCurrentView('hub')}>🏠 Hub</span>
            <span className="crumb-sep">/</span>
            <span className="crumb-active">Pre-Reboot Bio-Repository (2017–2020)</span>
          </div>
          <h2 className="banner-title">Historical Bio-Repository Explorer</h2>
          <p className="banner-desc">
            Archival repository of <b>22,094 legacy MBT samples</b> with pathology score availability, 
            FFPE block inventory, clinical relationships, and tissue metrics.
          </p>
        </div>

        <div className="banner-kpis">
          <div className="kpi-mini-card">
            <span className="kpi-mini-val">{totalSamples}</span>
            <span className="kpi-mini-label">Total MBT Samples</span>
          </div>
          <div className="kpi-mini-card">
            <span className="kpi-mini-val">{ffpeCount}</span>
            <span className="kpi-mini-label">FFPE Blocks Available</span>
          </div>
          <div className="kpi-mini-card">
            <span className="kpi-mini-val">{scoredCount}</span>
            <span className="kpi-mini-label">Pathology Scored</span>
          </div>
          <div className="kpi-mini-card">
            <span className="kpi-mini-val">{imageCount}</span>
            <span className="kpi-mini-label">Images Recorded</span>
          </div>
        </div>
      </div>

      {/* ── Main Explorer Workspace: Sidebar Filters + Results Table ── */}
      <div className="body-layout">
        <aside className="pre-reboot-sidebar">
          <div className="sb-section">
            <div className="sb-head">Pre-Reboot Filters</div>

            {/* MBT ID Search */}
            <div className="ff">
              <label>MBT Sample ID</label>
              <input
                className="ft-input"
                placeholder="e.g. 3107, MBRD, MBBP..."
                value={preRebootFilters.mbt}
                onChange={e => setPreRebootFilter('mbt', e.target.value)}
                onKeyDown={e => e.key === 'Enter' && runPreRebootSearch()}
              />
            </div>

            {/* Main Cancer Types */}
            <MultiSelect
              field="main_cancer_type"
              label="Main Cancer Type"
              placeholder="e.g. HNSCC, Ca CaBr, CRC..."
              selected={preRebootFilters.main_cancer_type}
              onChange={v => setPreRebootFilter('main_cancer_type', v)}
            />

            {/* Primary Study */}
            <MultiSelect
              field="primary_study"
              label="Primary Study"
              placeholder="e.g. 1st level attrition, Biopharma..."
              selected={preRebootFilters.primary_study}
              onChange={v => setPreRebootFilter('primary_study', v)}
            />

            {/* Hospital */}
            <MultiSelect
              field="hospital"
              label="Hospital"
              placeholder="e.g. KIDWAI, Manipal..."
              selected={preRebootFilters.hospital}
              onChange={v => setPreRebootFilter('hospital', v)}
            />

            {/* Collection Year */}
            <MultiSelect
              field="year"
              label="Collection Year"
              placeholder="e.g. 2017, 2018, 2019, 2020"
              selected={preRebootFilters.year}
              onChange={v => setPreRebootFilter('year', v)}
            />

            {/* Quick Toggles */}
            <div className="filter-toggle-box">
              <label className="filter-checkbox-label">
                <input
                  type="checkbox"
                  checked={Boolean(preRebootFilters.ffpe_block)}
                  onChange={e => {
                    setPreRebootFilter('ffpe_block', e.target.checked)
                    setTimeout(() => runPreRebootSearch(), 10)
                  }}
                />
                <span>FFPE Blocks Available Only</span>
              </label>

              <label className="filter-checkbox-label">
                <input
                  type="checkbox"
                  checked={Boolean(preRebootFilters.scored_only)}
                  onChange={e => {
                    setPreRebootFilter('scored_only', e.target.checked)
                    setTimeout(() => runPreRebootSearch(), 10)
                  }}
                />
                <span>Scored Samples Only (T0/T72)</span>
              </label>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <button className="btn-go" onClick={runPreRebootSearch}>🔍 Search</button>
              <button className="btn-clr" onClick={clearPreRebootFilters}>Clear</button>
            </div>
          </div>
        </aside>

        {/* ── Table Results ── */}
        <main className="pre-reboot-main">
          {/* Top Control & Results Count Bar */}
          <div className="ctx-bar">
            <span style={{ fontSize: 12, color: 'var(--txt)', fontWeight: 600 }}>
              Showing <b>{preRebootResults.length}</b> of <b>{preRebootTotal.toLocaleString()}</b> historical samples
            </span>

            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
              <button 
                className="dl-btn"
                style={{ background: 'var(--accent)', color: '#000', padding: '5px 12px', fontSize: 11, fontWeight: 700 }}
                onClick={handleDownloadExcel}
                disabled={downloadingExcel || preRebootTotal === 0}
              >
                {downloadingExcel ? 'Exporting...' : '↓ Export Pre-Reboot Data (.xlsx)'}
              </button>
            </div>
          </div>

          {preRebootLoading ? (
            <div className="spinner" style={{ margin: '40px auto' }} />
          ) : preRebootResults.length === 0 ? (
            <div className="empty">
              <div className="empty-icon">🏛️</div>
              <div>No historical samples match the selected criteria.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
              <div className="tbl-outer">
                <table className="res-table">
                  <thead>
                    <tr>
                      <th style={{ width: 30 }}></th>
                      <th onClick={() => setPreRebootSort('mbt')} style={{ width: 110, cursor: 'pointer' }}>
                        MBT ID {preRebootSortCol === 'mbt' ? (preRebootSortAsc ? '▲' : '▼') : '⇅'}
                      </th>
                      <th onClick={() => setPreRebootSort('year')} style={{ width: 80, cursor: 'pointer' }}>
                        Year {preRebootSortCol === 'year' ? (preRebootSortAsc ? '▲' : '▼') : '⇅'}
                      </th>
                      <th style={{ width: 100 }}>Date</th>
                      <th onClick={() => setPreRebootSort('main_cancer_type')} style={{ width: 120, cursor: 'pointer' }}>
                        Main Cancer {preRebootSortCol === 'main_cancer_type' ? (preRebootSortAsc ? '▲' : '▼') : '⇅'}
                      </th>
                      <th style={{ width: 130 }}>Specific Type</th>
                      <th style={{ width: 130 }}>Primary Study</th>
                      <th style={{ width: 130 }}>Hospital</th>
                      <th style={{ width: 90 }}>Age / Gender</th>
                      <th style={{ width: 90 }}>FFPE Block</th>
                      <th style={{ width: 110 }}>T0 / T72 Score</th>
                      <th style={{ width: 110 }}>Images</th>
                      <th style={{ width: 100 }}>Qualification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preRebootResults.map((r, idx) => {
                      const rowKey = r.id || `${r.mbt}_${idx}`
                      const isOpen = openRows.has(rowKey)

                      const hasT0Score = Boolean(r.t0_score && r.t0_score !== 'nan')
                      const hasT72Score = Boolean(r.t72_score && r.t72_score !== 'nan')
                      const hasFFPE = Boolean(r.ffpe_block_availability && r.ffpe_block_availability !== 'nan')

                      return (
                        <React.Fragment key={rowKey}>
                          <tr 
                            className={`data-row${isOpen ? ' row-open' : ''}`}
                            onClick={() => toggleRow(rowKey)}
                          >
                            <td className="td-toggle">
                              <span className="toggle-icon">›</span>
                            </td>
                            <td className="td-sid">{r.mbt || '—'}</td>
                            <td style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>
                              {r.year || '—'}
                            </td>
                            <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                              {r.collection_date || r.month || '—'}
                            </td>
                            <td>
                              {r.main_cancer_type ? (
                                <span className="ind-pill">{r.main_cancer_type}</span>
                              ) : (
                                <span style={{ color: 'var(--muted)' }}>—</span>
                              )}
                            </td>
                            <td style={{ fontSize: 11, color: 'var(--txt)' }}>
                              {r.cancer_type || '—'}
                            </td>
                            <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                              {r.primary_study || r.study_name || '—'}
                            </td>
                            <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                              {r.hospital || '—'}
                            </td>
                            <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                              {r.age ? `${r.age}y` : ''} {r.gender ? `/ ${r.gender[0]}` : '—'}
                            </td>
                            <td>
                              {hasFFPE ? (
                                <span className="badge-tag green">Available</span>
                              ) : (
                                <span style={{ color: 'var(--muted)' }}>—</span>
                              )}
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: 4 }}>
                                {hasT0Score && <span className="badge-tag blue" title={`T0: ${r.t0_score}`}>T0: {r.t0_score}</span>}
                                {hasT72Score && <span className="badge-tag purple" title={`T72: ${r.t72_score}`}>T72: {r.t72_score}</span>}
                                {!hasT0Score && !hasT72Score && <span style={{ color: 'var(--muted)' }}>—</span>}
                              </div>
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: 4 }}>
                                {r.t0_images ? <span className="badge-tag blue" title={`T0 Images: ${r.t0_images}`}>T0</span> : null}
                                {r.t72_images ? <span className="badge-tag purple" title={`T72 Images: ${r.t72_images}`}>T72</span> : null}
                                {!r.t0_images && !r.t72_images && <span style={{ color: 'var(--muted)' }}>—</span>}
                              </div>
                            </td>
                            <td>
                              {r.qualification_status ? (
                                <span className="badge-tag">{r.qualification_status}</span>
                              ) : (
                                <span style={{ color: 'var(--muted)' }}>—</span>
                              )}
                            </td>
                          </tr>

                          {/* Expanded Detail Row */}
                          {isOpen && (
                            <tr className="detail-row">
                              <td colSpan={13}>
                                <div className="detail-inner">
                                  <div className="meta-block">
                                    <div className="detail-title">Clinical & Institutional Details</div>
                                    <div className="meta-grid">
                                      <div className="mf"><span className="mk">MBT ID</span><span className="mv">{r.mbt}</span></div>
                                      <div className="mf"><span className="mk">Collection Year</span><span className="mv">{r.year}</span></div>
                                      <div className="mf"><span className="mk">Collection Date</span><span className="mv">{r.collection_date || r.month || '—'}</span></div>
                                      <div className="mf"><span className="mk">Hospital</span><span className="mv">{r.hospital || '—'}</span></div>
                                      <div className="mf"><span className="mk">Relationship Name</span><span className="mv">{r.relationship_name || '—'}</span></div>
                                      <div className="mf"><span className="mk">Type of Relationship</span><span className="mv">{r.type_of_relationship || '—'}</span></div>
                                      <div className="mf"><span className="mk">Physician</span><span className="mv">{r.physician || '—'}</span></div>
                                      <div className="mf"><span className="mk">Procedure Type</span><span className="mv">{r.procedure_type || '—'}</span></div>
                                      <div className="mf"><span className="mk">Sample Type</span><span className="mv">{r.sample_type || '—'}</span></div>
                                      <div className="mf"><span className="mk">pTNM</span><span className="mv">{r.ptnm || '—'}</span></div>
                                    </div>
                                  </div>

                                  <div className="meta-block">
                                    <div className="detail-title">Pathology Metrics, Images & Scoring</div>
                                    <div className="meta-grid">
                                      <div className="mf"><span className="mk">FFPE Block Availability</span><span className="mv">{r.ffpe_block_availability || '—'}</span></div>
                                      <div className="mf"><span className="mk">T0 Score</span><span className="mv">{r.t0_score || '—'}</span></div>
                                      <div className="mf"><span className="mk">T72 Score</span><span className="mv">{r.t72_score || '—'}</span></div>
                                      <div className="mf"><span className="mk">T0 Images</span><span className="mv">{r.t0_images || '—'}</span></div>
                                      <div className="mf"><span className="mk">T0 Markers</span><span className="mv">{r.markers_t0 || '—'}</span></div>
                                      <div className="mf"><span className="mk">T72 Images</span><span className="mv">{r.t72_images || '—'}</span></div>
                                      <div className="mf"><span className="mk">T72 Markers</span><span className="mv">{r.markers_t72 || '—'}</span></div>
                                      <div className="mf"><span className="mk">Qualification Status</span><span className="mv">{r.qualification_status || '—'}</span></div>
                                      <div className="mf"><span className="mk">Study Name / Code</span><span className="mv">{r.study_name || r.study_1 || r.study_2 || '—'}</span></div>
                                      <div className="mf"><span className="mk">Comments / Notes</span><span className="mv">{r.comments || r.column3 || '—'}</span></div>
                                    </div>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination Bar */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '8px 16px', borderTop: '1px solid var(--bdr)',
                background: 'var(--s2)', fontSize: 12, color: 'var(--muted)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button
                    className="btn-clr" style={{ width: 'auto', padding: '4px 12px' }}
                    disabled={preRebootPage === 0}
                    onClick={() => setPreRebootPage(preRebootPage - 1)}
                  >← Prev</button>
                  <span>Page <b style={{ color: 'var(--txt)' }}>{preRebootPage + 1}</b> of {preRebootTotalPages || 1}</span>
                  <button
                    className="btn-clr" style={{ width: 'auto', padding: '4px 12px' }}
                    disabled={preRebootPage >= preRebootTotalPages - 1}
                    onClick={() => setPreRebootPage(preRebootPage + 1)}
                  >Next →</button>
                </div>

                <span style={{ marginLeft: 'auto' }}>
                  Showing <b style={{ color: 'var(--accent)', fontFamily: 'var(--mono)' }}>{preRebootResults.length}</b> of <b style={{ color: 'var(--accent)', fontFamily: 'var(--mono)' }}>{preRebootTotal.toLocaleString()}</b>
                </span>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
