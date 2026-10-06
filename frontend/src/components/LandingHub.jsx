import React, { useEffect } from 'react'
import { useStore } from '../store'

export default function LandingHub() {
  const { 
    setCurrentView, stats, preRebootStats, 
    authFetch, setPreRebootStats, runPreRebootSearch 
  } = useStore()

  useEffect(() => {
    authFetch('/api/pre_reboot/stats')
      .then(r => r.json())
      .then(setPreRebootStats)
      .catch(() => {})
  }, [])

  const handleSelectPostReboot = () => {
    setCurrentView('database')
  }

  const handleSelectPreReboot = () => {
    setCurrentView('pre_reboot')
    runPreRebootSearch()
  }

  // Calculate live and dynamic combined statistics directly from database state
  const postSamplesNum = Number(stats?.samples || 0)
  const preSamplesNum = Number(preRebootStats?.total_samples || 0)
  const combinedTotalNum = postSamplesNum + preSamplesNum

  const postSamples = stats?.samples != null ? Number(stats.samples).toLocaleString() : '...'
  const postQualified = stats?.qualified_samples != null ? Number(stats.qualified_samples).toLocaleString() : '...'
  const postDrugs = stats?.drugs != null ? Number(stats.drugs).toLocaleString() : '...'
  const postAssays = stats?.assay_samples ? Object.keys(stats.assay_samples).length : '...'

  const preSamples = preRebootStats?.total_samples != null ? Number(preRebootStats.total_samples).toLocaleString() : '...'
  const preYears = preRebootStats?.years ? Object.keys(preRebootStats.years).length : '...'
  const preFFPE = preRebootStats?.ffpe_available_count != null ? Number(preRebootStats.ffpe_available_count).toLocaleString() : (preRebootStats?.with_block_count != null ? Number(preRebootStats.with_block_count).toLocaleString() : '...')
  const preScored = preRebootStats?.scored_samples_count != null ? Number(preRebootStats.scored_samples_count).toLocaleString() : (preRebootStats?.scored_count != null ? Number(preRebootStats.scored_count).toLocaleString() : '...')

  return (
    <div className="hub-container">
      {/* ── Top Hero & Combined Repository KPI Banner ── */}
      <div className="hub-hero">
        <div className="hub-badge-pill">
          FARCAST DATA EXPLORER &bull; MULTI-ERA REPOSITORY
        </div>
        <h1 className="hub-title">Farcast Unified Data Portal</h1>
        <p className="hub-subtitle">
          Access Farcast's active multimodal clinical oncology database alongside 
          the comprehensive 2017–2020 Historical Bio-Repository.
        </p>

        {/* Prominent Combined Total Counter */}
        <div className="hub-combined-banner">
          <div className="combined-left">
            <span className="combined-kpi-num">{combinedTotalNum.toLocaleString()}</span>
            <div className="combined-label-group">
              <span className="combined-title">Total Farcast Repository Samples</span>
              <span className="combined-sub">Combining both Active Post-Reboot and Historical Pre-Reboot eras</span>
            </div>
          </div>
          <div className="combined-right-pills">
            <div className="combined-pill post">
              <span className="pill-dot post">●</span>
              <b>{postSamples}</b> Post-Reboot
            </div>
            <div className="combined-pill plus">+</div>
            <div className="combined-pill pre">
              <span className="pill-dot pre">●</span>
              <b>{preSamples}</b> Pre-Reboot (MBT)
            </div>
          </div>
        </div>
      </div>

      {/* ── Two Era Cards Grid ── */}
      <div className="hub-cards-grid">
        {/* Card 1: Post-Reboot Multimodal Database */}
        <div className="hub-card post-reboot-card" onClick={handleSelectPostReboot}>
          <div className="hub-card-header">
            <div className="hub-card-tag active-tag">Active Production DB</div>
            <div className="hub-era-badge">Post-Reboot (2021–Present)</div>
          </div>
          
          <div className="hub-card-body">
            <div className="hub-card-icon post-icon">🔬</div>
            <h2 className="hub-card-title">Post-Reboot Multimodal Portal</h2>
            <p className="hub-card-desc">
              Standardized clinical oncology database integrating multidimensional assay readouts, 
              drug combinations, treatment arm controls, and directional platform response categorization.
            </p>

            <div className="hub-kpi-row">
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{postSamples}</span>
                <span className="hub-kpi-label">Active Samples</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{postQualified}</span>
                <span className="hub-kpi-label">Qualified</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{postDrugs}</span>
                <span className="hub-kpi-label">Tested Drugs</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{postAssays}</span>
                <span className="hub-kpi-label">Assay Types</span>
              </div>
            </div>

            <div className="hub-feature-list">
              <div className="hub-feature-item">
                <span className="feat-check">✓</span>
                <span>Histopathology, Cytokines, mIHC & NanoString assays</span>
              </div>
              <div className="hub-feature-item">
                <span className="feat-check">✓</span>
                <span>Arm-level matched drug highlights & Strict RXA control filter</span>
              </div>
              <div className="hub-feature-item">
                <span className="feat-check">✓</span>
                <span>Platform Response classification (Responder / Non-responder)</span>
              </div>
            </div>
          </div>

          <div className="hub-card-footer">
            <button className="hub-launch-btn post-reboot-btn">
              Launch Post-Reboot Portal →
            </button>
          </div>
        </div>

        {/* Card 2: Pre-Reboot Historical Bio-Repository */}
        <div className="hub-card pre-reboot-card" onClick={handleSelectPreReboot}>
          <div className="hub-card-header">
            <div className="hub-card-tag legacy-tag">Historical Bio-Repository</div>
            <div className="hub-era-badge">Pre-Reboot (2017–2020 MBT)</div>
          </div>

          <div className="hub-card-body">
            <div className="hub-card-icon pre-icon">🏛️</div>
            <h2 className="hub-card-title">Pre-Reboot Bio-Repository</h2>
            <p className="hub-card-desc">
              Extensive longitudinal cancer bio-repository capturing historical clinical cases, 
              legacy MBT sample codes, tissue metrics, FFPE block inventory, and pathology scoring.
            </p>

            <div className="hub-kpi-row">
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{preSamples}</span>
                <span className="hub-kpi-label">Historical MBTs</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{preYears}</span>
                <span className="hub-kpi-label">Years (2017–20)</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{preFFPE}</span>
                <span className="hub-kpi-label">FFPE Blocks</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{preScored}</span>
                <span className="hub-kpi-label">Scored</span>
              </div>
            </div>

            <div className="hub-feature-list">
              <div className="hub-feature-item">
                <span className="feat-check pre">✓</span>
                <span>22,094 legacy MBT samples across 4 longitudinal years</span>
              </div>
              <div className="hub-feature-item">
                <span className="feat-check pre">✓</span>
                <span>T0 & T72 digital pathology score availability & tissue metrics</span>
              </div>
              <div className="hub-feature-item">
                <span className="feat-check pre">✓</span>
                <span>Hospital relationships, physicians, and procedure types</span>
              </div>
            </div>
          </div>

          <div className="hub-card-footer">
            <button className="hub-launch-btn pre-reboot-btn">
              Explore Pre-Reboot Bio-Repository →
            </button>
          </div>
        </div>
      </div>

      {/* ── Comparison Overview Matrix ── */}
      <div className="hub-overview-section">
        <h3 className="hub-overview-title">Repository Comparison Matrix</h3>
        <div className="hub-table-wrapper">
          <table className="hub-compare-table">
            <thead>
              <tr>
                <th>Feature / Characteristic</th>
                <th>Post-Reboot Database (Active)</th>
                <th>Pre-Reboot Bio-Repository (Historical)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><b>Sample ID Format</b></td>
                <td><span className="table-mono-pill post">FBR1K... / FBR1Q... / FBR2...</span></td>
                <td><span className="table-mono-pill pre">MBT3107 / MBRD6 / MBBP33...</span></td>
              </tr>
              <tr>
                <td><b>Total Cohort Size</b></td>
                <td><b>{postSamples}</b> Samples ({postQualified} Qualified)</td>
                <td><b>{preSamples}</b> Historical MBT Samples</td>
              </tr>
              <tr>
                <td><b>Collection Timeline</b></td>
                <td>2021 &bull; 2022 &bull; 2023 &bull; 2024 &bull; 2025 &bull; 2026</td>
                <td>2017 &bull; 2018 &bull; 2019 &bull; 2020</td>
              </tr>
              <tr>
                <td><b>Integrated Assays</b></td>
                <td>Histopathology, Cytokine Release, mIHC, NanoString</td>
                <td>Pathology Scores (T0/T72), Images & Block Inventory</td>
              </tr>
              <tr>
                <td><b>Treatment & Drug Arms</b></td>
                <td>{postDrugs} Drugs, Arm Codes (RXA, RXB, RXC, etc.)</td>
                <td>Primary Study Classification</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
