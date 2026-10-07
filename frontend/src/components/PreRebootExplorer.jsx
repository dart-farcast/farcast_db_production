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
      arr('qualification_status', preRebootFilters.qualification_status)
      arr('final_qualification', preRebootFilters.final_qualification)
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
      XLSX.utils.book_append_sheet(wb, ws, "Bio_Repository")
      XLSX.writeFile(wb, `Bio_Repository_${rows.length}_samples.xlsx`)
    } catch (err) {
      console.error("Export error:", err)
      alert("Failed to export Bio-Repository data.")
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
    <div className="body-layout">
      {/* ── Left Sidebar Filters ── */}
      <aside>
        <div className="sb-section">
          <div className="sb-head">Bio-Repository Filters</div>

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
            apiEndpoint="/api/pre_reboot/autocomplete"
          />

          {/* Primary Study */}
          <MultiSelect
            field="primary_study"
            label="Primary Study"
            placeholder="e.g. NA, Biopharma..."
            selected={preRebootFilters.primary_study}
            onChange={v => setPreRebootFilter('primary_study', v)}
            apiEndpoint="/api/pre_reboot/autocomplete"
          />

          {/* Qualification Status */}
          <MultiSelect
            field="qualification_status"
            label="Qualification"
            placeholder="e.g. 1st level attrition, Q, NQ..."
            selected={preRebootFilters.qualification_status}
            onChange={v => setPreRebootFilter('qualification_status', v)}
            apiEndpoint="/api/pre_reboot/autocomplete"
          />

          {/* Final Qualification */}
          <MultiSelect
            field="final_qualification"
            label="Final Qualification"
            placeholder="Filter final qualification..."
            selected={preRebootFilters.final_qualification}
            onChange={v => setPreRebootFilter('final_qualification', v)}
            apiEndpoint="/api/pre_reboot/autocomplete"
          />

          {/* Hospital */}
          <MultiSelect
            field="hospital"
            label="Hospital"
            placeholder="e.g. KIDWAI, Manipal..."
            selected={preRebootFilters.hospital}
            onChange={v => setPreRebootFilter('hospital', v)}
            apiEndpoint="/api/pre_reboot/autocomplete"
          />

          {/* Collection Year */}
          <MultiSelect
            field="year"
            label="Collection Year"
            placeholder="e.g. 2017, 2018, 2019, 2020"
            selected={preRebootFilters.year}
            onChange={v => setPreRebootFilter('year', v)}
            apiEndpoint="/api/pre_reboot/autocomplete"
          />

          {/* Quick Toggles */}
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label className="qual-checkbox-label" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer', color: 'var(--txt)' }}>
              <input
                type="checkbox"
                checked={Boolean(preRebootFilters.ffpe_block)}
                onChange={e => {
                  setPreRebootFilter('ffpe_block', e.target.checked)
                  setTimeout(() => runPreRebootSearch(), 10)
                }}
              />
              <span style={{ fontWeight: 600 }}>FFPE Blocks Available Only</span>
            </label>

            <label className="qual-checkbox-label" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer', color: 'var(--txt)' }}>
              <input
                type="checkbox"
                checked={Boolean(preRebootFilters.scored_only)}
                onChange={e => {
                  setPreRebootFilter('scored_only', e.target.checked)
                  setTimeout(() => runPreRebootSearch(), 10)
                }}
              />
              <span style={{ fontWeight: 600 }}>Scored Samples Only (T0/T72)</span>
            </label>
          </div>

          {/* Search & Reset Buttons */}
          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button className="btn-go" onClick={runPreRebootSearch}>🔍 Search</button>
            <button className="btn-clr" onClick={clearPreRebootFilters}>Reset</button>
          </div>
        </div>
      </aside>

      {/* ── Main Data Workspace ── */}
      <main>
        {/* Context bar */}
        <div className="ctx-bar">
          <span className="ctx-tag" style={{ background: '#FEF3C7', borderColor: '#FDE68A' }}>
            <span className="label" style={{ color: '#92400E' }}>Repository</span>
            <span className="val" style={{ color: '#B45309', fontWeight: 700 }}>Bio-Repository Archive (2017–2020)</span>
          </span>

          {preRebootFilters.mbt && (
            <span className="ctx-tag">
              <span className="label">MBT</span>
              <span className="val">{preRebootFilters.mbt}</span>
            </span>
          )}
          {preRebootFilters.main_cancer_type?.map((v, i) => (
            <span className="ctx-tag" key={`mct-${i}`}><span className="label">Cancer</span><span className="val">{v}</span></span>
          ))}
          {preRebootFilters.primary_study?.map((v, i) => (
            <span className="ctx-tag" key={`ps-${i}`}><span className="label">Study</span><span className="val">{v}</span></span>
          ))}
          {preRebootFilters.qualification_status?.map((v, i) => (
            <span className="ctx-tag" key={`qs-${i}`}><span className="label">Qualification</span><span className="val">{v}</span></span>
          ))}
          {preRebootFilters.final_qualification?.map((v, i) => (
            <span className="ctx-tag" key={`fq-${i}`}><span className="label">Final Qual</span><span className="val">{v}</span></span>
          ))}
          {preRebootFilters.hospital?.map((v, i) => (
            <span className="ctx-tag" key={`h-${i}`}><span className="label">Hospital</span><span className="val">{v}</span></span>
          ))}
          {preRebootFilters.year?.map((v, i) => (
            <span className="ctx-tag" key={`y-${i}`}><span className="label">Year</span><span className="val">{v}</span></span>
          ))}
          {preRebootFilters.ffpe_block && (
            <span className="ctx-tag"><span className="label">Filter</span><span className="val">FFPE Blocks Only</span></span>
          )}
          {preRebootFilters.scored_only && (
            <span className="ctx-tag"><span className="label">Filter</span><span className="val">Scored Only</span></span>
          )}

          {preRebootTotal > 0 && (
            <span className="res-count">
              <b>{preRebootTotal.toLocaleString()}</b> result{preRebootTotal !== 1 ? 's' : ''}
            </span>
          )}

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
            <button 
              className="dl-btn"
              onClick={handleDownloadExcel}
              disabled={downloadingExcel || preRebootTotal === 0}
            >
              {downloadingExcel ? 'Exporting...' : '📥 Export to Excel'}
            </button>
          </div>
        </div>

        {preRebootLoading ? (
          <div className="spinner" style={{ margin: '60px auto' }} />
        ) : preRebootResults.length === 0 ? (
          <div className="empty">
            <div className="empty-icon">🏛️</div>
            <div>No historical samples match the selected filter criteria.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
            <div className="tbl-outer">
              <table className="res-table">
                <thead>
                  <tr>
                    <th style={{ width: 34 }}></th>
                    <th onClick={() => setPreRebootSort('mbt')} style={{ width: 120, cursor: 'pointer' }}>
                      MBT ID {preRebootSortCol === 'mbt' ? (preRebootSortAsc ? '▲' : '▼') : '⇅'}
                    </th>
                    <th onClick={() => setPreRebootSort('year')} style={{ width: 85, cursor: 'pointer' }}>
                      Year {preRebootSortCol === 'year' ? (preRebootSortAsc ? '▲' : '▼') : '⇅'}
                    </th>
                    <th style={{ width: 110 }}>Date / Month</th>
                    <th onClick={() => setPreRebootSort('main_cancer_type')} style={{ width: 140, cursor: 'pointer' }}>
                      Main Cancer {preRebootSortCol === 'main_cancer_type' ? (preRebootSortAsc ? '▲' : '▼') : '⇅'}
                    </th>
                    <th style={{ width: 140 }}>Specific Diagnosis</th>
                    <th style={{ width: 130 }}>Primary Study</th>
                    <th style={{ width: 130 }}>Hospital</th>
                    <th style={{ width: 90 }}>Age / Sex</th>
                    <th style={{ width: 100 }}>FFPE Block</th>
                    <th style={{ width: 120 }}>Pathology Scores</th>
                    <th style={{ width: 90 }}>Images</th>
                    <th onClick={() => setPreRebootSort('qualification_status')} style={{ width: 130, cursor: 'pointer' }}>
                      Qualification {preRebootSortCol === 'qualification_status' ? (preRebootSortAsc ? '▲' : '▼') : '⇅'}
                    </th>
                    <th onClick={() => setPreRebootSort('final_qualification')} style={{ width: 140, cursor: 'pointer' }}>
                      Final Qualification {preRebootSortCol === 'final_qualification' ? (preRebootSortAsc ? '▲' : '▼') : '⇅'}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {preRebootResults.map((r, idx) => {
                    const rowKey = r.id || `${r.mbt}_${idx}`
                    const isOpen = openRows.has(rowKey)

                    const hasT0Score = Boolean(r.t0_score && r.t0_score !== 'nan' && r.t0_score !== '')
                    const hasT72Score = Boolean(r.t72_score && r.t72_score !== 'nan' && r.t72_score !== '')
                    const hasFFPE = Boolean(r.ffpe_block_availability && r.ffpe_block_availability !== 'nan' && r.ffpe_block_availability !== '')

                    return (
                      <React.Fragment key={rowKey}>
                        <tr 
                          className={`data-row${isOpen ? ' row-open' : ''}`}
                          onClick={() => toggleRow(rowKey)}
                        >
                          <td className="td-toggle">
                            <span className="toggle-icon">{isOpen ? '▼' : '▶'}</span>
                          </td>
                          <td className="td-sid" style={{ color: '#D97706', fontWeight: 700 }}>
                            {r.mbt || '—'}
                          </td>
                          <td style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--txt)', fontWeight: 600 }}>
                            {r.year || '—'}
                          </td>
                          <td style={{ fontSize: 12, color: 'var(--muted)' }}>
                            {r.collection_date || r.month || '—'}
                          </td>
                          <td>
                            {r.main_cancer_type ? (
                              <span className="ind-pill">{r.main_cancer_type}</span>
                            ) : (
                              <span style={{ color: 'var(--muted)' }}>—</span>
                            )}
                          </td>
                          <td style={{ fontSize: 12, color: 'var(--txt)' }}>
                            {r.cancer_type || '—'}
                          </td>
                          <td style={{ fontSize: 12, color: 'var(--muted)' }}>
                            {r.primary_study || r.study_name || '—'}
                          </td>
                          <td style={{ fontSize: 12, color: 'var(--muted)' }}>
                            {r.hospital || '—'}
                          </td>
                          <td style={{ fontSize: 12, color: 'var(--muted)' }}>
                            {r.age ? `${r.age}y` : ''} {r.gender ? `/ ${r.gender[0]}` : '—'}
                          </td>
                          <td>
                            {hasFFPE ? (
                              <span className="scope-badge unrestricted" style={{ fontSize: 11, padding: '3px 8px' }}>Available</span>
                            ) : (
                              <span style={{ color: 'var(--muted)', fontSize: 12 }}>—</span>
                            )}
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: 4 }}>
                              {hasT0Score && <span className="scope-badge scoped" style={{ fontSize: 10, padding: '2px 6px' }} title={`T0: ${r.t0_score}`}>T0: {r.t0_score}</span>}
                              {hasT72Score && <span className="scope-badge sample-scoped" style={{ fontSize: 10, padding: '2px 6px' }} title={`T72: ${r.t72_score}`}>T72: {r.t72_score}</span>}
                              {!hasT0Score && !hasT72Score && <span style={{ color: 'var(--muted)', fontSize: 12 }}>—</span>}
                            </div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: 4 }}>
                              {r.t0_images ? <span className="scope-badge scoped" style={{ fontSize: 10, padding: '2px 6px' }} title={`T0 Images: ${r.t0_images}`}>T0</span> : null}
                              {r.t72_images ? <span className="scope-badge sample-scoped" style={{ fontSize: 10, padding: '2px 6px' }} title={`T72 Images: ${r.t72_images}`}>T72</span> : null}
                              {!r.t0_images && !r.t72_images && <span style={{ color: 'var(--muted)', fontSize: 12 }}>—</span>}
                            </div>
                          </td>
                          <td>
                            {r.qualification_status ? (
                              <span 
                                className="ind-pill" 
                                style={{ 
                                  background: r.qualification_status.toLowerCase().includes('attrition') ? '#FEF2F2' : '#F1F5F9', 
                                  color: r.qualification_status.toLowerCase().includes('attrition') ? '#B91C1C' : '#475569', 
                                  borderColor: r.qualification_status.toLowerCase().includes('attrition') ? '#FECACA' : '#CBD5E1' 
                                }}
                              >
                                {r.qualification_status}
                              </span>
                            ) : (
                              <span style={{ color: 'var(--muted)', fontSize: 12 }}>—</span>
                            )}
                          </td>
                          <td>
                            {r.final_qualification ? (
                              <span className="ind-pill" style={{ background: '#F0FDF4', color: '#166534', borderColor: '#BBF7D0' }}>
                                {r.final_qualification}
                              </span>
                            ) : (
                              <span style={{ color: 'var(--muted)', fontSize: 12 }}>—</span>
                            )}
                          </td>
                        </tr>

                        {/* Expanded Detail Row */}
                        {isOpen && (
                          <tr className="detail-row">
                            <td colSpan={14}>
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
                                    <div className="mf"><span className="mk">Final Qualification</span><span className="mv">{r.final_qualification || '—'}</span></div>
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
              padding: '10px 18px', borderTop: '1px solid var(--bdr)',
              background: 'var(--s1)', fontSize: 12, color: 'var(--muted)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button
                  className="btn-clr" style={{ width: 'auto', padding: '5px 14px', fontSize: 12 }}
                  disabled={preRebootPage === 0}
                  onClick={() => setPreRebootPage(preRebootPage - 1)}
                >← Prev</button>
                <span>Page <b style={{ color: 'var(--txt)' }}>{preRebootPage + 1}</b> of {preRebootTotalPages || 1}</span>
                <button
                  className="btn-clr" style={{ width: 'auto', padding: '5px 14px', fontSize: 12 }}
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
  )
}
