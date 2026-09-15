import React, { useState } from 'react'

export const ASSAY_DATA_DETAILS = [
  {
    id: 'histopathology',
    category: 'Histopathology',
    excelFile: 'HnE and IHC explant level data for T72.xlsx and HnE and IHC explant level data for TBL.xlsx',
    badgeColor: '#10B981',
    description: 'Morphological and apoptotic tumor assessment at baseline (TBL) and 72-hour explant endpoints (T72).',
    subtypes: [
      {
        name: 'HnE (Hematoxylin and Eosin)',
        parameters: [
          { name: 'Tumor_%', desc: 'Percentage of viable tumor content in explant' },
          { name: 'Necrosis', desc: 'Measure of poor tumor morphology (Scale 1–5: 1 = <10%, 5 = 100%)' },
          { name: 'Discohesion', desc: 'Measure of poor tumor morphology (Scale 1–5: 1 = <10%, 5 = 100%)' },
          { name: 'Pyknosis', desc: 'Measure of poor tumor morphology (Scale 1–5: 1 = <10%, 5 = 100%)' },
          { name: 'Immune_component_%', desc: 'Overall immune cell percentage in tissue section' },
          { name: 'Tumor_infiltrated_immune (%)', desc: 'Percentage of immune cells infiltrating directly into the tumor core' }
        ]
      },
      {
        name: 'IHC (Immunohistochemistry)',
        parameters: [
          { name: 'Cas-3', desc: 'Cleaved Caspase-3 (Measure of tumor apoptosis measured as %)' }
        ]
      }
    ]
  },
  {
    id: 'cytokine',
    category: 'Cytokine Release Assay',
    excelFile: 'Cytokine data.xlsx',
    badgeColor: '#F59E0B',
    description: 'Multiplexed measurement of inflammatory, cytotoxic, and regulatory cytokines reflecting immune cell activity and microenvironment response.',
    subtypes: [
      {
        name: 'Secreted Cytokine & Chemokine Profile',
        parameters: [
          { name: 'IFN-γ', desc: 'Interferon gamma (Th1 response, cytotoxic T/NK activation)' },
          { name: 'Perforin', desc: 'Cytolytic pore-forming protein' },
          { name: 'Granzyme B', desc: 'Serine protease inducing apoptotic cell death' },
          { name: 'IL-10', desc: 'Anti-inflammatory immunosuppressive cytokine' },
          { name: 'TNF-α', desc: 'Tumor necrosis factor alpha (pro-inflammatory)' },
          { name: 'IL-1β', desc: 'Pro-inflammatory signaling cytokine' },
          { name: 'IL-2', desc: 'T cell proliferation and survival factor' },
          { name: 'MMP-9', desc: 'Matrix metallopeptidase 9 (tissue remodeling)' },
          { name: 'IP-10 (CXCL10)', desc: 'Interferon gamma-induced protein 10' },
          { name: 'IL-6', desc: 'Pro-inflammatory cytokine & STAT3 activator' },
          { name: 'IL-8 (CXCL8)', desc: 'Neutrophil chemotactic factor' },
          { name: 'Fractalkine (CX3CL1)', desc: 'Chemokine mediating leukocyte adhesion' },
          { name: 'G-CSF (CSF-3)', desc: 'Granulocyte colony-stimulating factor' },
          { name: 'GM-CSF', desc: 'Granulocyte-macrophage colony-stimulating factor' },
          { name: 'I-TAC (CXCL11)', desc: 'Interferon-inducible T-cell chemoattractant' },
          { name: 'MCP-1 (CCL2)', desc: 'Monocyte chemoattractant protein-1' },
          { name: 'MIG (CXCL9)', desc: 'Monokine induced by gamma interferon' },
          { name: 'M-CSF', desc: 'Macrophage colony-stimulating factor (Immune cell activity)' }
        ]
      }
    ]
  },
  {
    id: 'nanostring',
    category: 'NanoString',
    excelFile: 'NS normalised data.xlsx, NS GES data.xlsx, NS TBL data.xlsx',
    badgeColor: '#8B5CF6',
    description: 'Digital gene expression profiling quantifying mRNA abundance across targeted immuno-oncology panels and pathway gene signatures.',
    subtypes: [
      {
        name: 'IO360 Panel',
        parameters: [
          { name: 'IO360 panel', desc: 'Normalized mRNA expression data across 770 immuno-oncology genes' }
        ]
      },
      {
        name: 'Gene Expression Signatures (GES)',
        parameters: [
          { name: 'Gene Signature pathways data', desc: 'Standardized signature scores across immune, stromal, and tumor hallmark pathways' }
        ]
      },
      {
        name: 'Baseline Tissue (TBL)',
        parameters: [
          { name: 'NanoString TBL data', desc: 'Baseline tissue gene expression profile prior to drug culture' }
        ]
      }
    ]
  },
  {
    id: 'flowcytometry',
    category: 'Flow Cytometry',
    excelFile: 'FlowCytometry data.xlsx',
    badgeColor: '#3B82F6',
    description: 'Single-cell immunophenotyping quantifying frequencies of effector, memory, exhausted, and regulatory immune subpopulations.',
    subtypes: [
      {
        name: 'Immunophenotyping Panel',
        parameters: [
          { name: 'CD45+', desc: 'Total leukocyte population' },
          { name: 'Macrophage', desc: 'Total macrophage lineage' },
          { name: 'M2', desc: 'M2 immunosuppressive / pro-tumor macrophages' },
          { name: 'T cell', desc: 'Total T lymphocytes' },
          { name: 'CD4+', desc: 'T helper lymphocytes' },
          { name: 'Treg', desc: 'Regulatory T cells (CD4+FoxP3+)' },
          { name: 'CTL', desc: 'Cytotoxic T Lymphocytes (CD8+)' },
          { name: 'Non-T cell', desc: 'Non-T immune subsets' },
          { name: 'CD8+Ki67+', desc: 'Proliferating cytotoxic T cells' },
          { name: 'CD8+GranzymeB+', desc: 'Cytolytically active cytotoxic T cells' },
          { name: 'CD4+FoxP3+CTLA4+', desc: 'Suppressive / CTLA-4 checkpoint-expressing Tregs' },
          { name: 'CD4+FoxP3+Ki67+', desc: 'Proliferating regulatory T cells' },
          { name: 'Treg freq parent', desc: 'Treg frequency relative to parent CD4+ population' },
          { name: 'CTL freq parent', desc: 'CTL frequency relative to parent CD3+ population' },
          { name: 'Monocyte', desc: 'Circulating monocyte lineage' },
          { name: 'CD15', desc: 'Granulocyte / neutrophil marker' },
          { name: 'NK', desc: 'Natural Killer cells' },
          { name: 'B cell like', desc: 'B lymphocyte lineage subsets' }
        ]
      }
    ]
  },
  {
    id: 'mihc',
    category: 'mIHC (Multiplex Immunohistochemistry)',
    excelFile: 'mIHC image details With Treatment Details_SS 1.xlsx',
    badgeColor: '#EC4899',
    description: 'High-plex spatial biomarker imaging resolving cellular phenotypes, spatial distances, and neighborhood interactions.',
    subtypes: [
      {
        name: 'Spatial Tissue Profiling',
        parameters: [
          { name: 'Spatial Biomarkers & Treatment Details', desc: 'Multiplexed fluorescent biomarker image readouts mapped across treatment arms' }
        ]
      }
    ]
  },
  {
    id: 'metadata',
    category: 'Sample Metadata',
    excelFile: 'Metadata.xlsx / All sample details.xlsx',
    badgeColor: '#6366F1',
    description: 'Comprehensive patient demographics, clinical characteristics, tumor staging, pathology grades, and processing QC parameters.',
    subtypes: [
      {
        name: 'Clinical & Explant Parameters',
        parameters: [
          { name: 'Patient Demographics', desc: 'Patient age, gender, infection status' },
          { name: 'Tumor Staging & Pathology', desc: 'Cancer type, cancer sub type, tumor site, tumor stage and grade' },
          { name: 'Virological Status', desc: 'HPV status, infection status' },
          { name: 'Study & Registration', desc: 'Register Type (Study Type), Project (Study Code), Protocol, Hospital, Physician' }
        ]
      }
    ]
  }
]

export default function AssayDetailsModal({ isOpen, onClose }) {
  const [search, setSearch] = useState('')
  const [selectedTab, setSelectedTab] = useState('all')

  if (!isOpen) return null

  const q = search.trim().toLowerCase()

  const filteredAssays = ASSAY_DATA_DETAILS.filter(assay => {
    if (selectedTab !== 'all' && assay.id !== selectedTab) return false
    if (!q) return true

    const inCat = assay.category.toLowerCase().includes(q)
    const inFile = assay.excelFile.toLowerCase().includes(q)
    const inDesc = assay.description.toLowerCase().includes(q)
    const inParams = assay.subtypes.some(sub =>
      sub.name.toLowerCase().includes(q) ||
      sub.parameters.some(p => p.name.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q))
    )
    return inCat || inFile || inDesc || inParams
  })

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div 
        className="modal-card assay-details-modal-card" 
        onClick={e => e.stopPropagation()}
        style={{ maxWidth: 940, maxHeight: '88vh' }}
      >
        {/* Header */}
        <div className="modal-header assay-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div className="assay-modal-icon">🔬</div>
            <div>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--txt)' }}>
                Assay Directory & Parameter Guide
              </h3>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                Comprehensive dictionary of multi-omics assays, file sources, sub-panels, and readout parameters
              </div>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} title="Close">×</button>
        </div>

        {/* Toolbar & Filter Tabs */}
        <div className="assay-modal-toolbar">
          <div className="assay-modal-search">
            <span>🔍</span>
            <input 
              type="text" 
              placeholder="Search parameters, biomarkers (e.g. Necrosis, IFN-γ, CD45+, IO360)..." 
              value={search}
              onChange={e => setSearch(e.target.value)}
              autoFocus
            />
            {search && <button className="clear-search-btn" onClick={() => setSearch('')}>×</button>}
          </div>

          <div className="assay-tab-bar">
            <button 
              className={`assay-tab-btn ${selectedTab === 'all' ? 'active' : ''}`}
              onClick={() => setSelectedTab('all')}
            >
              All Assays ({ASSAY_DATA_DETAILS.length})
            </button>
            {ASSAY_DATA_DETAILS.map(a => (
              <button 
                key={a.id}
                className={`assay-tab-btn ${selectedTab === a.id ? 'active' : ''}`}
                onClick={() => setSelectedTab(a.id)}
              >
                {a.category.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* Modal Body */}
        <div className="modal-body assay-modal-body">
          {filteredAssays.length === 0 ? (
            <div className="assay-empty-state">
              <div style={{ fontSize: 32 }}>🔍</div>
              <div style={{ fontWeight: 600, marginTop: 8, color: 'var(--txt)' }}>No matching assay parameters found</div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                Try searching for a different biomarker name or clear the search input.
              </div>
            </div>
          ) : (
            <div className="assay-cards-grid">
              {filteredAssays.map(assay => (
                <div className="assay-detail-card" key={assay.id}>
                  {/* Card Head */}
                  <div className="adc-header">
                    <div className="adc-title-wrap">
                      <span className="adc-badge" style={{ backgroundColor: `${assay.badgeColor}20`, color: assay.badgeColor, borderColor: `${assay.badgeColor}40` }}>
                        {assay.category}
                      </span>
                      <div className="adc-file">
                        <span className="adc-file-label">Source File:</span> 
                        <code>{assay.excelFile}</code>
                      </div>
                    </div>
                  </div>

                  <div className="adc-desc">{assay.description}</div>

                  {/* Subtypes & Parameter Tables */}
                  <div className="adc-subtypes-wrap">
                    {assay.subtypes.map((sub, sIdx) => (
                      <div className="adc-subtype-section" key={sIdx}>
                        <div className="adc-subtype-title">{sub.name}</div>
                        <div className="adc-param-table-wrap">
                          <table className="adc-param-table">
                            <thead>
                              <tr>
                                <th style={{ width: '28%' }}>Parameter / Biomarker</th>
                                <th style={{ width: '72%' }}>Biological Significance & Measurement Details</th>
                              </tr>
                            </thead>
                            <tbody>
                              {sub.parameters.map((p, pIdx) => {
                                const isMatch = q && (p.name.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q))
                                return (
                                  <tr key={pIdx} className={isMatch ? 'param-highlighted' : ''}>
                                    <td className="param-name-cell">
                                      <span className="param-tag">{p.name}</span>
                                    </td>
                                    <td className="param-desc-cell">{p.desc}</td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer assay-modal-footer">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>
            Showing <b>{filteredAssays.length}</b> of <b>{ASSAY_DATA_DETAILS.length}</b> assay categories
          </div>
          <button className="btn-go" onClick={onClose} style={{ padding: '8px 20px', borderRadius: 6 }}>
            Close Guide
          </button>
        </div>
      </div>
    </div>
  )
}
