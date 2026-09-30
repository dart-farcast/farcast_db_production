import React, { useEffect } from 'react'
import { useStore } from '../store'
import FarcastLogo from './FarcastLogo'

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

  const postSamples = stats?.samples?.toLocaleString() ?? '2,148'
  const postDrugs = stats?.drugs?.toLocaleString() ?? '83'
  const postAssays = Object.keys(stats?.assay_samples || {}).length || 4

  const preSamples = preRebootStats?.total_samples?.toLocaleString() ?? '22,094'
  const preYears = Object.keys(preRebootStats?.years || {}).length || 4
  const preFFPE = preRebootStats?.ffpe_available_count?.toLocaleString() ?? '11,540'
  const preScored = preRebootStats?.scored_samples_count?.toLocaleString() ?? '17,210'

  return (
    <div className="hub-container">
      {/* Hero Welcome Header */}
      <div className="hub-hero">
        <div className="hub-badge-pill">FARCAST DATA EXPLORER &bull; MULTI-ERA REPOSITORY</div>
        <h1 className="hub-title">Unified Clinical & Bio-Repository Portal</h1>
        <p className="hub-subtitle">
          Seamlessly access, search, and analyze Farcast's multi-omics clinical study database 
          alongside the comprehensive 2017–2020 Historical Bio-Repository.
        </p>
      </div>

      {/* Two Main Era Cards */}
      <div className="hub-cards-grid">
        {/* Card 1: Post-Reboot Multimodal Database */}
        <div className="hub-card post-reboot-card" onClick={handleSelectPostReboot}>
          <div className="hub-card-header">
            <div className="hub-card-tag active-tag">Active Study Platform</div>
            <div className="hub-era-badge">Post-Reboot (FarCast DB v2)</div>
          </div>
          
          <div className="hub-card-body">
            <div className="hub-card-icon">🔬</div>
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
                <span className="hub-kpi-num">{postAssays}</span>
                <span className="hub-kpi-label">Omics Assays</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{postDrugs}</span>
                <span className="hub-kpi-label">Tested Drugs</span>
              </div>
            </div>

            <div className="hub-feature-list">
              <div className="hub-feature-item">✓ Histopathology, Cytokines, mIHC & NanoString readouts</div>
              <div className="hub-feature-item">✓ Arm-level matched drug highlights & Strict RXA control filter</div>
              <div className="hub-feature-item">✓ Platform Response classification (Responder / Non-responder)</div>
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
            <div className="hub-card-tag legacy-tag">Historical Archive (2017–2020)</div>
            <div className="hub-era-badge">Pre-Reboot (MBT Registry)</div>
          </div>

          <div className="hub-card-body">
            <div className="hub-card-icon">🏛️</div>
            <h2 className="hub-card-title">Pre-Reboot Bio-Repository</h2>
            <p className="hub-card-desc">
              Extensive longitudinal cancer bio-repository capturing historical clinical cases, 
              legacy MBT sample codes, tissue metrics, FFPE block availability, and T0/T72 pathology scoring.
            </p>

            <div className="hub-kpi-row">
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{preSamples}</span>
                <span className="hub-kpi-label">Historical MBTs</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{preYears}</span>
                <span className="hub-kpi-label">Years (2017–2020)</span>
              </div>
              <div className="hub-kpi-item">
                <span className="hub-kpi-num">{preFFPE}</span>
                <span className="hub-kpi-label">FFPE Blocks</span>
              </div>
            </div>

            <div className="hub-feature-list">
              <div className="hub-feature-item">✓ 22,094 legacy MBT samples across 4 longitudinal years</div>
              <div className="hub-feature-item">✓ T0 & T72 digital pathology score availability & metrics</div>
              <div className="hub-feature-item">✓ Hospital relationships, physicians, and procedure types</div>
            </div>
          </div>

          <div className="hub-card-footer">
            <button className="hub-launch-btn pre-reboot-btn">
              Explore Pre-Reboot Bio-Repository →
            </button>
          </div>
        </div>
      </div>

      {/* Comparison Overview Bar */}
      <div className="hub-overview-section">
        <h3 className="hub-overview-title">Repository Comparison Overview</h3>
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
                <td><span className="mono-badge">FBR1K... / FBR1Q... / FBR2...</span></td>
                <td><span className="mono-badge">MBT3107 / MBRD6 / MBBP33...</span></td>
              </tr>
              <tr>
                <td><b>Total Cohort Size</b></td>
                <td>2,148 Samples (1,592 Qualified)</td>
                <td>22,094 Historical Bio-Repository Samples</td>
              </tr>
              <tr>
                <td><b>Collection Timeline</b></td>
                <td>Post-Reboot Production Era</td>
                <td>2017 &bull; 2018 &bull; 2019 &bull; 2020</td>
              </tr>
              <tr>
                <td><b>Integrated Assays</b></td>
                <td>Histopathology, Cytokine Release, mIHC, NanoString</td>
                <td>Pathology T0/T72 Scores, Images & Block Inventory</td>
              </tr>
              <tr>
                <td><b>Treatment & Drug Arms</b></td>
                <td>83 Drugs, Arm Codes (RXA, RXB, RXC, etc.)</td>
                <td>Primary Study Classification</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
