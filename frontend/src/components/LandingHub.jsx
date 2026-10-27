import React, { useEffect } from 'react'
import { useStore } from '../store'

function DiscoveryCrosshairIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      {/* Tissue section outline */}
      <path 
        d="M12 2.5C6.5 2.5 3 6 3 11.5c0 3.5 1.5 6 4 7.5 2 .8 3 3.5 5 3.5s3-2.7 5-3.5c2.5-1.5 4-4 4-7.5 0-5.5-3.5-9-9-9z" 
        fill="rgba(245, 158, 11, 0.12)" 
        stroke="rgba(245, 158, 11, 0.45)" 
        strokeWidth="1.2" 
        strokeDasharray="2 2" 
      />
      {/* Target crosshair */}
      <circle cx="12" cy="11.5" r="5" stroke="#F59E0B" strokeWidth="1.8" />
      <circle cx="12" cy="11.5" r="1.5" fill="#F59E0B" />
      <line x1="12" y1="3.5" x2="12" y2="7.5" stroke="#F59E0B" strokeWidth="1.8" />
      <line x1="12" y1="15.5" x2="12" y2="19.5" stroke="#F59E0B" strokeWidth="1.8" />
      <line x1="4" y1="11.5" x2="8" y2="11.5" stroke="#F59E0B" strokeWidth="1.8" />
      <line x1="16" y1="11.5" x2="20" y2="11.5" stroke="#F59E0B" strokeWidth="1.8" />
    </svg>
  )
}

function ResponseBranchingIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#818CF8" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      {/* Central live tumor fragment */}
      <circle cx="12" cy="16.5" r="3.5" fill="rgba(129, 140, 248, 0.25)" stroke="#818CF8" strokeWidth="1.8" />
      {/* Three branching arrows radiating outward */}
      {/* Left branch */}
      <path d="M10 14L5 8.5" stroke="#818CF8" strokeWidth="1.8" />
      <path d="M4 11.5V7.5h4" stroke="#818CF8" strokeWidth="1.8" />
      {/* Center branch */}
      <path d="M12 13V4" stroke="#818CF8" strokeWidth="1.8" />
      <path d="M9.5 6.5L12 4l2.5 2.5" stroke="#818CF8" strokeWidth="1.8" />
      {/* Right branch */}
      <path d="M14 14L19 8.5" stroke="#818CF8" strokeWidth="1.8" />
      <path d="M16 7.5h4v4" stroke="#818CF8" strokeWidth="1.8" />
    </svg>
  )
}

export default function LandingHub() {
  const { 
    setCurrentView, stats, preRebootStats, 
    authFetch, setPreRebootStats, setPreRebootFilter, runPreRebootSearch 
  } = useStore()

  useEffect(() => {
    authFetch('/api/pre_reboot/stats')
      .then(r => r.json())
      .then(setPreRebootStats)
      .catch(() => {})
  }, [])

  const handleSelectResponseCohort = () => {
    setCurrentView('database')
  }

  const handleSelectDiscoveryCohort = (indication = null) => {
    if (indication) {
      setPreRebootFilter('main_cancer_type', [indication])
    }
    setCurrentView('pre_reboot')
    setTimeout(() => runPreRebootSearch(), 10)
  }

  // Calculate live and dynamic combined statistics directly from database state
  const postSamplesNum = Number(stats?.samples || 0)
  const preSamplesNum = Number(preRebootStats?.total_samples || 0)
  const combinedTotalNum = postSamplesNum + preSamplesNum

  const postSamples = stats?.samples != null ? Number(stats.samples).toLocaleString() : '2,191'
  const postQualified = stats?.qualified_samples != null ? Number(stats.qualified_samples).toLocaleString() : '1,605'
  const postDrugs = stats?.drugs != null ? Number(stats.drugs).toLocaleString() : '80'

  const preSamples = preRebootStats?.total_samples != null ? Number(preRebootStats.total_samples).toLocaleString() : '22,094'

  return (
    <div className="hub-container">
      {/* ── Top Hero & Combined Repository KPI Banner ── */}
      <div className="hub-hero">
        <div className="hub-badge-pill">
          FARCAST DATA EXPLORER &bull; MULTI-ERA REPOSITORY
        </div>
        <h1 className="hub-title">Farcast Unified Data Portal</h1>
        <p className="hub-subtitle">
          Access Farcast's active clinical oncology database alongside the comprehensive archival Discovery Cohort.
        </p>

        {/* Prominent Combined Total Counter */}
        <div className="hub-combined-banner">
          <div className="combined-left">
            <span className="combined-kpi-num">{combinedTotalNum > 0 ? combinedTotalNum.toLocaleString() : '24,285'}</span>
            <div className="combined-label-group">
              <span className="combined-title">Total Farcast Repository Samples</span>
              <span className="combined-sub">Combining Discovery Cohort and Response Cohort collections</span>
            </div>
          </div>
          <div className="combined-right-pills">
            <div className="combined-pill pre">
              <span className="pill-dot pre">●</span>
              <b>{preSamples}</b> Discovery Cohort
            </div>
            <div className="combined-pill plus">+</div>
            <div className="combined-pill post">
              <span className="pill-dot post">●</span>
              <b>{postSamples}</b> Response Cohort
            </div>
          </div>
        </div>
      </div>

      {/* ── Two Cards Grid with Split Headlines (Discovery Left, Response Right) ── */}
      <div className="hub-cards-grid">
        {/* CARD 1 (LEFT): Discovery Cohort */}
        <div className="hub-card-wrapper">
          <div className="split-headline discovery">Is the target there?</div>
          <div className="hub-card discovery-card" onClick={() => handleSelectDiscoveryCohort()}>
            <div className="hub-card-header">
              <div className="hub-card-tag discovery-tag">TARGET &amp; MARKER VALIDATION</div>
              <div className="hub-era-badge">FFPE Archive</div>
            </div>
            
            <div className="hub-card-body">
              <div className="hub-card-icon pre-icon" style={{ background: 'rgba(245, 158, 11, 0.08)', borderColor: 'rgba(245, 158, 11, 0.25)' }}>
                <DiscoveryCrosshairIcon />
              </div>
              <h2 className="hub-card-title">Discovery Cohort</h2>
              <p className="hub-card-desc">
                Interrogate targets and markers across thousands of tumors per indication.
              </p>

              {/* Discovery Graphic: The Indication Ladder */}
              <div className="indication-ladder" onClick={e => e.stopPropagation()}>
                <div className="ladder-header">Cohort size by indication (FFPE blocks)</div>
                
                <div className="ladder-row" onClick={() => handleSelectDiscoveryCohort('HNSCC')} title="Filter Discovery Cohort by Head and Neck (HNSCC)">
                  <span className="ladder-label">Head and neck</span>
                  <div className="ladder-bar-bg">
                    <div className="ladder-bar-fill" style={{ width: '100%' }}></div>
                  </div>
                  <span className="ladder-count">8,000+</span>
                </div>

                <div className="ladder-row" onClick={() => handleSelectDiscoveryCohort('Ca CaBr')} title="Filter Discovery Cohort by Breast Cancer">
                  <span className="ladder-label">Breast</span>
                  <div className="ladder-bar-bg">
                    <div className="ladder-bar-fill" style={{ width: '65%' }}></div>
                  </div>
                  <span className="ladder-count">5,000+</span>
                </div>

                <div className="ladder-row" onClick={() => handleSelectDiscoveryCohort('CRC')} title="Filter Discovery Cohort by Colorectal (CRC)">
                  <span className="ladder-label">Colorectal</span>
                  <div className="ladder-bar-bg">
                    <div className="ladder-bar-fill" style={{ width: '22%' }}></div>
                  </div>
                  <span className="ladder-count">1,400+</span>
                </div>

                <div className="ladder-row" onClick={() => handleSelectDiscoveryCohort('Ca Lung')} title="Filter Discovery Cohort by Lung Cancer">
                  <span className="ladder-label">Lung</span>
                  <div className="ladder-bar-bg">
                    <div className="ladder-bar-fill" style={{ width: '10%' }}></div>
                  </div>
                  <span className="ladder-count">500+</span>
                </div>

                <div className="ladder-row" onClick={() => handleSelectDiscoveryCohort('Ca Brain')} title="Filter Discovery Cohort by GBM / Brain">
                  <span className="ladder-label">GBM</span>
                  <div className="ladder-bar-bg">
                    <div className="ladder-bar-fill" style={{ width: '5%' }}></div>
                  </div>
                  <span className="ladder-count">100+</span>
                </div>

                <div className="ladder-more" onClick={() => handleSelectDiscoveryCohort()}>
                  + 10 more indications →
                </div>
              </div>

              {/* Assay Chips & Caption */}
              <div className="assay-chips-container">
                <div className="assay-chips-list">
                  <span className="assay-badge-chip">H&amp;E</span>
                  <span className="assay-badge-chip">IHC</span>
                  <span className="assay-badge-chip">NanoString</span>
                  <span className="assay-badge-chip">RNA expression</span>
                </div>
                <p className="chips-caption-note">Assays run on demand on archived FFPE blocks</p>
              </div>

              {/* Stat Line */}
              <div className="hub-stat-line">
                About 22,000 tumors &bull; 15+ indications &bull; 4 assays
              </div>
            </div>

            <div className="hub-card-footer">
              <button className="hub-launch-btn pre-reboot-btn">
                Explore Discovery Cohort →
              </button>
            </div>
          </div>
        </div>

        {/* CARD 2 (RIGHT): Response Cohort */}
        <div className="hub-card-wrapper">
          <div className="split-headline response">What if we treat it?</div>
          <div className="hub-card response-card" onClick={handleSelectResponseCohort}>
            <div className="hub-card-header">
              <div className="hub-card-tag response-tag">FUNCTIONAL DRUG RESPONSE</div>
              <div className="hub-era-badge">Live Tumor Library</div>
            </div>

            <div className="hub-card-body">
              <div className="hub-card-icon post-icon" style={{ background: 'rgba(99, 102, 241, 0.08)', borderColor: 'rgba(99, 102, 241, 0.25)' }}>
                <ResponseBranchingIcon />
              </div>
              <h2 className="hub-card-title">Response Cohort</h2>
              <p className="hub-card-desc">
                Every tumor, every arm: the what-if answers the clinic cannot give.
              </p>

              {/* Response Graphic: Clinic vs. Every Arm Panel */}
              <div className="clinic-compare-box">
                <div className="compare-banner-text">
                  A patient gets one treatment. Each Response Cohort tumor gets them all.
                </div>
                
                <div className="compare-cols-grid">
                  <div className="compare-card-col clinic">
                    <div className="compare-card-title">Clinic</div>
                    <div className="compare-line">Drug A &rarr; one outcome</div>
                    <div className="compare-line" style={{ color: '#94A3B8' }}>Drug B &rarr; never known</div>
                    <div className="compare-line" style={{ color: '#94A3B8' }}>Combo &rarr; never known</div>
                  </div>

                  <div className="compare-card-col response">
                    <div className="compare-card-title">Response Cohort</div>
                    <div className="compare-line">Control &rarr; baseline</div>
                    <div className="compare-line"><b style={{ color: '#34D399' }}>Drug A &rarr; Responder</b></div>
                    <div className="compare-line"><b style={{ color: '#F87171' }}>Drug B &rarr; Non-responder</b></div>
                    <div className="compare-line"><b style={{ color: '#34D399' }}>Combo &rarr; Responder</b></div>
                  </div>
                </div>

                <div className="compare-mini-cards">
                  <div className="mini-response-card">
                    <div className="mini-response-title">Activity</div>
                    <div className="mini-response-desc">Cytokine readouts, NanoString IO 360</div>
                  </div>
                  <div className="mini-response-card">
                    <div className="mini-response-title">Cytotoxic response</div>
                    <div className="mini-response-desc">Cleaved caspase-3 IHC, H&amp;E</div>
                  </div>
                </div>
              </div>

              {/* Assay Chips & Caption */}
              <div className="assay-chips-container">
                <div className="assay-chips-list">
                  <span className="assay-badge-chip">H&amp;E</span>
                  <span className="assay-badge-chip">Cytokines</span>
                  <span className="assay-badge-chip">mIHC</span>
                  <span className="assay-badge-chip">NanoString IO 360</span>
                </div>
                <p className="chips-caption-note">Labels: pathologist H&amp;E + cleaved caspase-3</p>
              </div>

              {/* Stat Line */}
              <div className="hub-stat-line">
                <b>{postSamples}</b> profiled &bull; <b>{postQualified}</b> qualified &bull; <b>{postDrugs}</b> drugs
              </div>
            </div>

            <div className="hub-card-footer">
              <button className="hub-launch-btn post-reboot-btn">
                Explore Response Cohort →
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Flow Strip Under Cards ── */}
      <div className="hub-flow-strip">
        <span className="flow-step-pill">Validate</span>
        <span className="flow-step-arrow">&rarr;</span>
        <span className="flow-step-pill highlight">Test</span>
        <span className="flow-step-arrow">&rarr;</span>
        <span className="flow-step-pill">Extend: sponsored study</span>
      </div>

      {/* ── Comparison Overview Matrix ── */}
      <div className="hub-overview-section">
        <h3 className="hub-overview-title">Cohort Comparison Matrix</h3>
        <div className="hub-table-wrapper">
          <table className="hub-compare-table">
            <thead>
              <tr>
                <th>Feature / Characteristic</th>
                <th>Discovery Cohort (Target Validation)</th>
                <th>Response Cohort (Functional Response)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><b>Clinical Objective</b></td>
                <td><span style={{ color: '#FBBF24', fontWeight: 600 }}>Target &amp; Biomarker Validation</span></td>
                <td><span style={{ color: '#A5B4FC', fontWeight: 600 }}>Functional Ex-Vivo Drug Response</span></td>
              </tr>
              <tr>
                <td><b>Specimen Format</b></td>
                <td>Archived FFPE Blocks (Tissue sections)</td>
                <td>Fresh Viable Tumor Micro-Explants</td>
              </tr>
              <tr>
                <td><b>Cohort Size</b></td>
                <td><b>{preSamples}</b> Archived Tumors (15+ Indications)</td>
                <td><b>{postSamples}</b> Tumors Profiled ({postQualified} Qualified)</td>
              </tr>
              <tr>
                <td><b>Integrated Assays</b></td>
                <td>Target &amp; marker interrogation (H&amp;E, IHC, NanoString, RNA expression)</td>
                <td>H&amp;E, Cytokine Release, mIHC, NanoString IO 360</td>
              </tr>
              <tr>
                <td><b>Treatment Readouts</b></td>
                <td>Clinical site and procedure metadata</td>
                <td>{postDrugs} Drugs &bull; Multi-arm testing with matched-control</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
