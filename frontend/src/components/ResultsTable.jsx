import React, { useState, useMemo } from 'react'
import * as XLSX from 'xlsx'
import { useStore } from '../store'
import ExpandedRow from './ExpandedRow'

const COLS = [
  { key: 'toggle',       label: '',            w: 28   },
  { key: 'Sample_ID',    label: 'Sample ID',   w: 130  },
  { key: 'CancerType',   label: 'Indication',  w: 130  },
  { key: 'Study',        label: 'Study Type',  w: 120  },

  { key: 'TumorSite',    label: 'Tumor Site',  w: 110  },
  { key: 'Gender',       label: 'Gender',      w: 70   },
  { key: 'arms',         label: 'Arms / Drug', w: 160  },
  { key: 'assays',       label: 'Assays',      w: 180  },
]

export default function ResultsTable() {
  const { results, assayCols, total, loading, filters, authFetch } = useStore()
  const selectedAssays = filters?.assay || []
  const activeFilters  = filters || {}
  const [openRows, setOpenRows]   = useState(new Set())
  const [sortCol,  setSortCol]    = useState('Sample_ID')
  const [sortAsc,  setSortAsc]    = useState(true)
  const [page,     setPage]       = useState(0)
  const [downloadingCohort, setDownloadingCohort] = useState(false)
  const PAGE = 50

  const downloadCohortExcel = async () => {
    if (!results || results.length === 0) return
    setDownloadingCohort(true)
    try {
      const sids = results.map(r => r.metadata.Sample_ID)
      
      const res = await authFetch('/api/cohort_assays', {
        method: 'POST',
        body: JSON.stringify({ sample_ids: sids })
      })
      const data = await res.json()
      
      const wb = XLSX.utils.book_new()
      
      // 1. Cohort Metadata Sheet
      const metaRows = results.map(r => {
        const out = {}
        for (const [k, v] of Object.entries(r.metadata)) {
          if (v !== '') out[k] = v
        }
        return out
      })
      const wsMeta = XLSX.utils.json_to_sheet(metaRows)
      XLSX.utils.book_append_sheet(wb, wsMeta, 'Cohort_Metadata')

      // 2. Treatment Arm Details Sheet
      const armRows = []
      results.forEach(r => {
        const sid = r.metadata?.Sample_ID
        if (r.arms && r.arms.length > 0) {
          r.arms.forEach(a => {
            armRows.push({
              Sample_ID: sid,
              Position: a.position,
              Arm_Code: a.arm_code,
              Drug_Treatment: a.drug || ''
            })
          })
        }
      })
      if (armRows.length > 0) {
        const wsArms = XLSX.utils.json_to_sheet(armRows)
        XLSX.utils.book_append_sheet(wb, wsArms, 'Treatment_Arm_Details')
      }
      
      // 3. Assay Sheets
      for (const [assayName, entry] of Object.entries(data)) {
        if (entry && entry.rows && entry.rows.length > 0) {
          const sheetName = assayName.substring(0, 31).replace(/[\[\]\\\*\?\/]/g, '_')
          const wsAssay = XLSX.utils.json_to_sheet(entry.rows)
          XLSX.utils.book_append_sheet(wb, wsAssay, sheetName)
        }
      }
      
      XLSX.writeFile(wb, `Cohort_Export_${sids.length}_samples.xlsx`)
    } catch (err) {
      console.error('Error downloading cohort Excel', err)
      alert('Failed to download Cohort Data.')
    } finally {
      setDownloadingCohort(false)
    }
  }

  const toggleRow = (sid) =>
    setOpenRows(prev => {
      const n = new Set(prev)
      n.has(sid) ? n.delete(sid) : n.add(sid)
      return n
    })

  const sorted = useMemo(() => {
    return [...results].sort((a, b) => {
      const av = (a.metadata?.[sortCol] ?? a[sortCol] ?? '').toString().toLowerCase()
      const bv = (b.metadata?.[sortCol] ?? b[sortCol] ?? '').toString().toLowerCase()
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av)
    })
  }, [results, sortCol, sortAsc])

  const paged = sorted.slice(page * PAGE, (page + 1) * PAGE)
  const pages = Math.ceil(sorted.length / PAGE)

  const handleSort = (col) => {
    if (col === 'toggle' || col === 'arms' || col === 'assays') return
    if (col === sortCol) setSortAsc(a => !a)
    else { setSortCol(col); setSortAsc(true) }
  }

  if (loading) return <div className="spinner" />

  if (!results.length)
    return (
      <div className="empty">
        <div className="empty-icon">🔬</div>
        <div>Set filters and click <b>Search</b> to explore samples</div>
      </div>
    )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
      <div className="tbl-outer">
        <table className="res-table">
          <thead>
            <tr>
              {COLS.map(c => (
                <th
                  key={c.key}
                  className={sortCol === c.key ? 'sorted' : ''}
                  style={{ width: c.w }}
                  onClick={() => handleSort(c.key)}
                >
                  {c.label}
                  {c.key !== 'toggle' && c.key !== 'arms' && c.key !== 'assays' && (
                    <span className="sort-arrow">
                      {sortCol === c.key ? (sortAsc ? '▲' : '▼') : '⇅'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((row, i) => {
              const sid  = row.metadata?.Sample_ID ?? i
              const open = openRows.has(sid)
              return (
                <React.Fragment key={sid}>
                  <tr
                    className={`data-row${open ? ' row-open' : ''}`}
                    onClick={() => toggleRow(sid)}
                  >
                    <td className="td-toggle">
                      <span className="toggle-icon">›</span>
                    </td>
                    <td className="td-sid">{sid}</td>
                    <td>
                      {row.metadata?.CancerType
                        ? <span className="ind-pill">{row.metadata.CancerType}</span>
                        : <span style={{ color: 'var(--muted)' }}>—</span>}
                    </td>
                    <td style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 11 }}>
                      {row.metadata?.Study || '—'}
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {row.metadata?.TumorSite || '—'}
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {row.metadata?.Gender || '—'}
                    </td>
                    <td>
                      {row.arms?.filter(a => a.matched).map((a, j) => (
                        <span key={j} className="drug-tag">{a.drug || a.arm_code}</span>
                      ))}
                      {row.arms?.filter(a => !a.matched).slice(0, 2).map((a, j) => (
                        <span key={j} className="drug-tag" style={{ opacity: .5 }}>{a.arm_code}</span>
                      ))}
                    </td>
                    <td>
                      {(row.assays_present || []).map(a => (
                        <span key={a} className="assay-badge">{a}</span>
                      ))}
                    </td>
                  </tr>
                  {open && (
                    <ExpandedRow
                      row={row}
                      assayCols={assayCols}
                      colSpan={COLS.length}
                      selectedAssays={selectedAssays}
                      activeFilters={activeFilters}
                    />
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Footer / Pagination */}
      {results.length > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '8px 16px', borderTop: '1px solid var(--bdr)',
          background: 'var(--s2)', fontSize: 12, color: 'var(--muted)'
        }}>
          {pages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                className="btn-clr" style={{ width: 'auto', padding: '4px 12px' }}
                disabled={page === 0}
                onClick={() => setPage(p => p - 1)}
              >← Prev</button>
              <span>Page <b style={{ color: 'var(--txt)' }}>{page + 1}</b> / {pages}</span>
              <button
                className="btn-clr" style={{ width: 'auto', padding: '4px 12px' }}
                disabled={page >= pages - 1}
                onClick={() => setPage(p => p + 1)}
              >Next →</button>
            </div>
          )}

          <button 
             className="dl-btn" 
             style={{ marginLeft: pages > 1 ? 8 : 0, background: 'var(--accent)', color: '#000', border: 'none', padding: '4px 12px' }}
             onClick={downloadCohortExcel}
             disabled={downloadingCohort}
          >
            {downloadingCohort ? 'Downloading...' : '↓ Download Cohort Data (Assay Wise)'}
          </button>

          <span style={{ marginLeft: 'auto' }}>
            Showing <b style={{ color: 'var(--accent)', fontFamily: 'var(--mono)' }}>
              {paged.length}
            </b> of <b style={{ color: 'var(--accent)', fontFamily: 'var(--mono)' }}>
              {total}
            </b>
          </span>
        </div>
      )}
    </div>
  )
}
