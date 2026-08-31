import { create } from 'zustand'

const DEFAULT_FILTERS = {
  drug:           [],
  arm:            [],
  indication:     [],
  tumor_site:     [],
  study:          [],
  project:        [],
  sample:         '',
  assay:          [],
  timepoint:      '',
  qualified_only: false,
}

function buildQS(filters) {
  const p = new URLSearchParams()
  const arr = (k, v) => { if (v?.length) p.set(k, v.join(',')) }
  arr('drug',       filters.drug)
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
  currentView: savedToken && savedUser?.is_whitelisted ? 'database' : 'login', // 'database' | 'admin' | 'login'
  authError: null,

  setAuth: (user, token) => {
    if (token) localStorage.setItem('farcast_token', token)
    if (user) localStorage.setItem('farcast_user', JSON.stringify(user))
    set({
      user,
      token,
      currentView: user?.is_whitelisted ? 'database' : 'login',
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
      filters: { ...DEFAULT_FILTERS }
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

  // Search & database state
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
}))
