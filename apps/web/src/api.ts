import { useEffect, useState } from 'react'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000'

export interface Attribution { text?: string | null; html?: string | null }
export interface Creator { id?: number | null; name: string; role?: string | null }
export interface Comic {
  id: number; title: string; issue_number: number | null; series_name: string | null
  shelf: 'prior' | 'main'; in_resolved_series: boolean; onsale_date: string | null
  format: string | null; description: string | null; thumbnail: string | null
  creators: Creator[]
}
export interface Character { id: number; name: string; seed: boolean; description: string | null; thumbnail: string | null }
export interface SeriesRef { id: number; title: string; start_year: number | null; comic_count: number }
export interface Shelf { label: string; series: SeriesRef[] }

export type State<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ok'; data: T }

export function useApi<T>(path: string | null): State<T> {
  const [state, setState] = useState<{ path: string | null; value: State<T> }>({ path, value: { status: 'loading' } })
  useEffect(() => {
    if (path === null) return
    let cancelled = false
    fetch(`${API_BASE}${path}`)
      .then(async (r) => {
        const body = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${r.status}).`)
        return body as T
      })
      .then((data) => !cancelled && setState({ path, value: { status: 'ok', data } }))
      .catch((e: Error) => !cancelled && setState({ path, value: { status: 'error', message: e.message || 'Could not reach the House of X API.' } }))
    return () => { cancelled = true }
  }, [path])
  return state.path === path ? state.value : { status: 'loading' }
}

export interface RosterEntry {
  id: string; name: string; alias: string; council_seat?: string; role: string
  primary_power: string; krakoan_function: string; is_mutant: boolean; bio?: string; faction_name?: string
}
export interface RosterFaction { faction_name: string; description: string; characters: RosterEntry[] }
export interface Roster { era: string; total_characters: number; factions: RosterFaction[]; source_note: string }
