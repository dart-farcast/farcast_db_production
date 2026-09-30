import { create } from 'zustand'

const DEFAULT_FILTERS = {
  drug:           [],
  strict_drug:    false,
  arm:            [],
  indication:     [],
  tumor_site:     [],
  study:          [],
  project:        [],
  sample:         '',
  assay:          [],
  timepoint:      '',
  qualified_only: true,
}

function buildQS(filters) {
  const p = new URLSearchParams()
  const arr = (k, v) => { if (v?.length) p.set(k, v.join(',')) }
  arr('drug',       filters.drug)
  if (filters.strict_drug && filters.drug?.length) p.set('strict_drug', 'true')
  arr('arm',        filters.arm)
  arr('indication', filters.indication)
  arr('tumor_site', filters.tumor_site)
  arr('study',      filters.study)
  arr('project',    filters.project)
  arr('assay',      filters.assay)
  if (filters.sample)         p.set('sample',         filters.sample)
  if (filters.timepoint)      p.set('timepoint',      filters.timepoint)
  if (filters.qualified_only) p.set('qualified_only', 'true')
  return p.toString()
}


const DEFAULT_PRE_REBOOT_FILTERS = {
  mbt: '',
  main_cancer_type: [],
  cancer_type: [],
  primary_study: [],
  hospital: [],
  year: [],
  ffpe_block: false,
  scored_only: false,
}

function buildPreRebootQS(filters, page = 0, pageSize = 50, sortCol = 'mbt', sortAsc = true) {
  const p = new URLSearchParams()
  const arr = (k, v) => { if (v?.length) p.set(k, v.join(',')) }
  if (filters.mbt) p.set('mbt', filters.mbt)
  arr('main_cancer_type', filters.main_cancer_type)
  arr('cancer_type', filters.cancer_type)
  arr('primary_study', filters.primary_study)
  arr('hospital', filters.hospital)
  arr('year', filters.year)
  if (filters.ffpe_block) p.set('ffpe_block', 'true')
  if (filters.scored_only) p.set('scored_only', 'true')
  p.set('page', page)
  p.set('page_size', pageSize)
  p.set('sort_col', sortCol)
  p.set('sort_asc', sortAsc ? 'true' : 'false')
  return p.toString()
}

const savedToken = localStorage.getItem('farcast_token') || null
let savedUser = null
try {
  savedUser = JSON.parse(localStorage.getItem('farcast_user'))
} catch (e) {
  savedUser = null
}

export const useStore = create((set, get) => ({
  // Auth state
  token: savedToken,
  user: savedUser,
  currentView: savedToken && savedUser?.is_whitelisted ? 'hub' : 'login', // 'hub' | 'database' | 'pre_reboot' | 'admin' | 'login'
  authError: null,

  setAuth: (user, token) => {
    if (token) localStorage.setItem('farcast_token', token)
    if (user) localStorage.setItem('farcast_user', JSON.stringify(user))
    set({
      user,
      token,
      currentView: user?.is_whitelisted ? 'hub' : 'login',
      authError: null
    })
  },

  updateUser: (partialUser) => {
    const updated = { ...get().user, ...partialUser }
    localStorage.setItem('farcast_user', JSON.stringify(updated))
    set({ user: updated })
  },

  logout: () => {
    localStorage.removeItem('farcast_token')
    localStorage.removeItem('farcast_user')
    set({
      user: null,
      token: null,
      currentView: 'login',
      results: [],
      total: 0,
      filters: { ...DEFAULT_FILTERS },
      preRebootResults: [],
      preRebootTotal: 0,
      preRebootFilters: { ...DEFAULT_PRE_REBOOT_FILTERS }
    })
  },

  setCurrentView: (view) => set({ currentView: view }),

  // Authenticated fetch wrapper
  authFetch: async (url, options = {}) => {
    const { token, logout } = get()
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(url, { ...options, headers })
    if (res.status === 401) {
      logout()
      throw new Error("Session expired or unauthorized. Please sign in again.")
    }
    return res
  },

  // Post-Reboot Search & database state
  filters:    { ...DEFAULT_FILTERS },
  results:    [],
  assayCols:  [],
  total:      0,
  loading:    false,
  stats:      null,
  assayTypes: [],

  setFilter: (key, value) =>
    set(s => ({ filters: { ...s.filters, [key]: value } })),

  setFilterAndSearch: (field, value) => {
    const { filters, authFetch } = get()
    const current = Array.isArray(filters[field]) ? filters[field] : []
    const newVal  = current.includes(value) ? current : [...current, value]
    const newFilters = { ...filters, [field]: newVal }
    set({ filters: newFilters, loading: true })
    
    authFetch(`/api/search?${buildQS(newFilters)}`)
      .then(r => r.json())
      .then(data => set({
        results:   data.results || [],
        total:     data.total || 0,
        assayCols: data.assay_cols || [],
        loading:   false,
      }))
      .catch(() => set({ loading: false }))
  },

  runSearch: () => {
    const { filters, authFetch } = get()
    set({ loading: true })
    authFetch(`/api/search?${buildQS(filters)}`)
      .then(r => r.json())
      .then(data => set({
        results:   data.results || [],
        total:     data.total || 0,
        assayCols: data.assay_cols || [],
        loading:   false,
      }))
      .catch(() => set({ loading: false }))
  },

  clearFilters: () =>
    set({ filters: { ...DEFAULT_FILTERS }, results: [], total: 0, assayCols: [] }),

  setResults: (data) =>
    set({ results: data.results, total: data.total, assayCols: data.assay_cols || [] }),

  setLoading: (v) => set({ loading: v }),
  setStats:   (v) => set({ stats: v }),
  setAssayTypes: (v) => set({ assayTypes: v }),

  // ── Pre-Reboot Bio-Repository State (2017–2020 MBT) ─────────────────────────
  preRebootFilters: { ...DEFAULT_PRE_REBOOT_FILTERS },
  preRebootStats: null,
  preRebootResults: [],
  preRebootTotal: 0,
  preRebootTotalPages: 0,
  preRebootPage: 0,
  preRebootPageSize: 50,
  preRebootSortCol: 'mbt',
  preRebootSortAsc: true,
  preRebootLoading: false,

  setPreRebootFilter: (key, value) =>
    set(s => ({ preRebootFilters: { ...s.preRebootFilters, [key]: value }, preRebootPage: 0 })),

  setPreRebootSort: (col) => {
    const { preRebootSortCol, preRebootSortAsc, runPreRebootSearch } = get()
    if (preRebootSortCol === col) {
      set({ preRebootSortAsc: !preRebootSortAsc, preRebootPage: 0 })
    } else {
      set({ preRebootSortCol: col, preRebootSortAsc: true, preRebootPage: 0 })
    }
    setTimeout(() => runPreRebootSearch(), 10)
  },

  setPreRebootPage: (p) => {
    set({ preRebootPage: p })
    setTimeout(() => get().runPreRebootSearch(), 10)
  },

  setPreRebootStats: (v) => set({ preRebootStats: v }),

  runPreRebootSearch: () => {
    const { preRebootFilters, preRebootPage, preRebootPageSize, preRebootSortCol, preRebootSortAsc, authFetch } = get()
    set({ preRebootLoading: true })
    const qs = buildPreRebootQS(preRebootFilters, preRebootPage, preRebootPageSize, preRebootSortCol, preRebootSortAsc)
    authFetch(`/api/pre_reboot/search?${qs}`)
      .then(r => r.json())
      .then(data => set({
        preRebootResults:    data.results || [],
        preRebootTotal:      data.total || 0,
        preRebootTotalPages: data.total_pages || 0,
        preRebootLoading:    false,
      }))
      .catch(() => set({ preRebootLoading: false }))
  },

  clearPreRebootFilters: () => {
    set({ preRebootFilters: { ...DEFAULT_PRE_REBOOT_FILTERS }, preRebootPage: 0 })
    setTimeout(() => get().runPreRebootSearch(), 10)
  }
}))
