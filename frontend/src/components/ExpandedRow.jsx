import React, { useState, useCallback } from 'react'
import * as XLSX from 'xlsx'/* ── Highlight helper ────────────────────────────────────────────────────── */
/**
 * Wraps substrings matching any of `terms` with <mark className="hl">.
 * Case-insensitive. If no terms, renders plain text.
 */
function Highlight({ text, terms }) {
  if (!terms?.length || !text) return <>{String(text ?? '')}</>
  const str = String(text)
  const escaped = terms
    .filter(Boolean)
    .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (!escaped.length) return <>{str}</>
  const regex = new RegExp(`(${escaped.join('|')})`, 'gi')
  const parts = str.split(regex)
  return (
    <>
      {parts.map((part, i) =>
        regex.test(part)
          ? <mark key={i} className="hl">{part}</mark>
          : <span key={i}>{part}</span>
      )}
    </>
  )
}

/* ── Download helper ─────────────────────────────────────────────────────── */
function downloadCSV(meta, sid) {
  const rows = Object.entries(meta)
    .filter(([, v]) => v !== '')
    .map(([k, v]) => `${k},${String(v).replace(/,/g, ';')}`)
  const blob = new Blob(['Field,Value\n' + rows.join('\n')], { type: 'text/csv' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = `${sid}_metadata.csv`; a.click()
  URL.revokeObjectURL(url)
}

import { useStore } from '../store'

async function downloadAssaysExcel(sid, meta, arms, authFetch) {
  try {
    const res = await authFetch(`/api/sample_assays?sample_id=${encodeURIComponent(sid)}`)
    const data = await res.json()
    
    const wb = XLSX.utils.book_new()
    
    // Add metadata sheet
    const metaRows = Object.entries(meta)
      .filter(([, v]) => v !== '')
      .map(([k, v]) => ({ Field: k, Value: v }))
    const wsMeta = XLSX.utils.json_to_sheet(metaRows)
    XLSX.utils.book_append_sheet(wb, wsMeta, 'Metadata')

    // Add Treatment Arm Details sheet
    if (arms && arms.length > 0) {
      const armRows = arms.map(a => ({
        Position: a.position,
        Arm_Code: a.arm_code,
        Drug_Treatment: a.drug || ''
      }))
      const wsArms = XLSX.utils.json_to_sheet(armRows)
      XLSX.utils.book_append_sheet(wb, wsArms, 'Treatment_Arm_Details')
    }
    
    // Add one sheet per assay
    for (const [assayName, entry] of Object.entries(data)) {
      if (entry && entry.rows && entry.rows.length > 0) {
        const sheetName = assayName.substring(0, 31).replace(/[\[\]\\\*\?\/]/g, '_')
        const wsAssay = XLSX.utils.json_to_sheet(entry.rows)
        XLSX.utils.book_append_sheet(wb, wsAssay, sheetName)
      }
    }
    
    XLSX.writeFile(wb, `${sid}_AssayData.xlsx`)
  } catch (err) {
    console.error('Error downloading Excel', err)
    alert('Failed to download Excel file.')
  }
}

/* ── ExpandedRow ─────────────────────────────────────────────────────────── */
export default function ExpandedRow({ row, assayCols, colSpan, selectedAssays = [], activeFilters = {} }) {
  const { authFetch } = useStore()
  const [clickedAssay, setClickedAssay] = useState(null)
  const [fetchedRows,  setFetchedRows]  = useState(null)
  const [fetchedCols,  setFetchedCols]  = useState([])
  const [fetchLoading, setFetchLoading] = useState(false)

  const meta          = row.metadata       || {}
  const arms          = row.arms           || []
  const assayRows     = row.assay_rows     || []
  const assaysPresent = row.assays_present || []
  const sid           = meta.Sample_ID     || ''

  // Collect all active search terms for highlighting
  const hlTerms = [
    ...(activeFilters.drug       || []),
    ...(activeFilters.arm        || []),
    ...(activeFilters.indication || []),
    ...(activeFilters.tumor_site || []),
    ...(activeFilters.study      || []),
    ...(activeFilters.project    || []),
    activeFilters.sample || '',
  ].filter(Boolean)

  // Click a badge → fetch that assay's rows on demand
  const loadAssay = useCallback((assayName) => {
    if (clickedAssay === assayName) {
      setClickedAssay(null); setFetchedRows(null); setFetchedCols([])
      return
    }
    setClickedAssay(assayName)
    setFetchLoading(true)
    authFetch(`/api/sample_assays?sample_id=${encodeURIComponent(sid)}`)
      .then(r => r.json())
      .then(data => {
        const entry = data[assayName]
        setFetchedRows(entry?.rows || [])
        setFetchedCols(entry?.columns || [])
        setFetchLoading(false)
      })
      .catch(() => setFetchLoading(false))
  }, [clickedAssay, sid, authFetch])

  // Which rows/cols to display in the assay table
  const showRows = fetchedRows !== null ? fetchedRows : []
  const showCols = fetchedRows !== null ? fetchedCols : []

  // Keep only columns that have at least one non-empty value across all rows.
  // Treats '', null, undefined, 'nan', 'NaN', 'None', 'NA', 'N/A' as empty.
  const EMPTY = new Set(['', 'nan', 'NaN', 'None', 'NA', 'N/A', 'null', 'undefined'])
  const isBlank = (v) => v === null || v === undefined || EMPTY.has(String(v).trim())
  const rawCols = showCols.length ? showCols : (showRows.length ? Object.keys(showRows[0]) : [])
  const activeCols = rawCols.filter(col => showRows.some(row => !isBlank(row[col])))

  const metaEntries = Object.entries(meta).filter(
    ([k, v]) => v && v !== '' && k !== 'Sample_ID'
  )

  return (
    <tr className="detail-row open">
      <td colSpan={colSpan}>
        <div className="detail-inner">

          {/* ── Metadata grid ──────────────────────────────────────── */}
          <div>
            <div className="detail-title">Sample Metadata</div>
            <div className="meta-grid">
              <div className="meta-cell">
                <div className="mc-label">Sample ID</div>
                <div className="mc-val blue">
                  <Highlight text={sid} terms={[activeFilters.sample]} />
                </div>
              </div>
              {metaEntries.map(([k, v]) => (
                <div className="meta-cell" key={k}>
                  <div className="mc-label">{k.replace(/([A-Z])/g, ' $1').trim()}</div>
                  <div className="mc-val">
                    <Highlight text={v} terms={hlTerms} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Treatment Arms table ───────────────────────────────── */}
          {arms.length > 0 && (
            <div>
              <div className="detail-title">Treatment Arms</div>
              <div className="arms-tbl-wrap">
                <table className="arms-tbl">
                  <thead>
                    <tr>
                      <th>Position</th>
                      <th>Arm Code</th>
                      <th>Drug / Treatment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {arms.map((a, i) => (
                      <tr key={i} className={a.matched ? 'arm-matched' : ''}>
                        <td className="arm-pos">{a.position}</td>
                        <td className="arm-code-cell">
                          <Highlight text={a.arm_code} terms={activeFilters.arm || []} />
                        </td>
                        <td className="arm-drug-cell">
                          {a.drug
                            ? <Highlight text={a.drug} terms={activeFilters.drug || []} />
                            : <span style={{ color: 'var(--muted)' }}>—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Assay badges (clickable) ───────────────────────────── */}
          {assaysPresent.length > 0 && (
            <div>
              <div className="detail-title">Assays For This Sample</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {assaysPresent.map(a => {
                  const isClicked  = clickedAssay === a
                  return (
                    <button
                      key={a}
                      className={`ap-badge${isClicked ? ' active' : ''}`}
                      onClick={() => loadAssay(a)}
                      title={`View ${a} data for this sample`}
                    >
                      <span className="ap-dot" />
                      {a}
                    </button>
                  )
                })}
              </div>
              {!clickedAssay && (
                <p style={{ marginTop: 6, fontSize: 11, color: 'var(--muted)', fontStyle: 'italic' }}>
                  ← Click an assay badge to view records for this sample
                </p>
              )}
              {clickedAssay && (
                <p style={{ marginTop: 6, fontSize: 11, color: 'var(--muted)' }}>
                  Showing <b style={{ color: 'var(--accent)' }}>{clickedAssay}</b>
                  {' · '}
                  <button
                    style={{
                      background: 'none', border: 'none', color: 'var(--muted)',
                      fontSize: 11, cursor: 'pointer', textDecoration: 'underline',
                    }}
                    onClick={() => { setClickedAssay(null); setFetchedRows(null); setFetchedCols([]) }}
                  >
                    clear
                  </button>
                </p>
              )}
            </div>
          )}

          {/* ── Assay data table ──────────────────────────────────── */}
          {fetchLoading && (
            <div style={{ color: 'var(--muted)', fontSize: 11 }}>Loading assay data…</div>
          )}
          {!fetchLoading && showRows.length > 0 && (
            <div>
              <div className="detail-title">
                Assay Rows
                {(clickedAssay || selectedAssays[0]) && (
                  <span style={{
                    color: 'var(--accent)', marginLeft: 8,
                    textTransform: 'none', fontWeight: 400, letterSpacing: 0,
                  }}>
                    — {clickedAssay || selectedAssays.join(', ')}
                  </span>
                )}
              </div>
              <div className="assay-tbl-wrap">
                <table className="assay-tbl">
                  <thead>
                    <tr>
                      {activeCols.map(c => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {showRows.map((r, i) => (
                      <tr key={i}>
                        {activeCols.map(c => (
                          <td key={c}>{isBlank(r[c]) ? '' : r[c]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {!fetchLoading && fetchedRows !== null && fetchedRows.length === 0 && (
            <div style={{ color: 'var(--muted)', fontSize: 11 }}>No rows found for this assay.</div>
          )}

          {/* ── Download ──────────────────────────────────────────── */}
          <div>
            <div className="detail-title">Download — {sid}</div>
            <div style={{ display: 'flex', gap: 12 }}>
              <button className="dl-btn" onClick={() => downloadCSV(meta, sid)}>
                ↓ Metadata CSV
              </button>
              <button className="dl-btn" style={{ background: 'var(--accent)', color: '#FFFFFF', border: 'none', fontWeight: 600 }} onClick={() => downloadAssaysExcel(sid, meta, arms, authFetch)}>
                ↓ Assay Data (Excel)
              </button>
            </div>
          </div>

        </div>
      </td>
    </tr>
  )
}
