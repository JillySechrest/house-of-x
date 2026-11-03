import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { Attribution, Character, Comic, Shelf } from './api'
import { useApi } from './api'
import { ComicList, Layout, Status, Thumb } from './components'

interface ComicsPayload { items: Comic[]; attribution: Attribution }

export function Landing() {
  const main = useApi<ComicsPayload>('/api/comics?shelf=main')
  const prior = useApi<ComicsPayload>('/api/comics?shelf=prior')
  const attribution = main.status === 'ok' ? main.data.attribution : prior.status === 'ok' ? prior.data.attribution : null
  return (
    <Layout attribution={attribution}>
      <h1>Hickman's X-Men, after House of X</h1>
      <p className="muted">Comics the Marvel API credits to Jonathan Hickman as writer. Results are what the API returns, not a complete run.</p>
      <Status state={main}>{(d) => <ComicList comics={d.items} />}</Status>
      <h2>House of X / Powers of X</h2>
      <Status state={prior}>{(d) => <ComicList comics={d.items} />}</Status>
    </Layout>
  )
}

export function Shelves() {
  const state = useApi<{ prior: Shelf; main: Shelf; attribution: Attribution }>('/api/shelves')
  return (
    <Layout attribution={state.status === 'ok' ? state.data.attribution : null}>
      <h1>Shelves</h1>
      <Status state={state}>
        {(d) => (
          <>
            {[d.main, d.prior].map((shelf) => (
              <section key={shelf.label}>
                <h2>{shelf.label}</h2>
                {shelf.series.length === 0 ? <p>The API returned none of these series.</p> : (
                  <ul>{shelf.series.map((s) => <li key={s.id}>{s.title} — {s.comic_count} Hickman-credited issues</li>)}</ul>
                )}
              </section>
            ))}
          </>
        )}
      </Status>
      <p><Link to="/">Back to the main shelf</Link></p>
    </Layout>
  )
}

export function ComicDetail() {
  const { id } = useParams()
  const state = useApi<{ comic: Comic; attribution: Attribution }>(`/api/comics/${id}`)
  return (
    <Layout attribution={state.status === 'ok' ? state.data.attribution : null}>
      <Status state={state}>
        {({ comic: c }) => (
          <article>
            <h1>{c.title}</h1>
            <Thumb src={c.thumbnail} alt={`Cover of ${c.title}`} large />
            <p>{c.description ?? 'No description from Marvel.'}</p>
            <dl>
              {c.series_name && (<><dt>Series</dt><dd>{c.series_name}</dd></>)}
              {c.issue_number != null && (<><dt>Issue</dt><dd>{c.issue_number}</dd></>)}
              {c.format && (<><dt>Format</dt><dd>{c.format}</dd></>)}
              <dt>On sale</dt><dd>{c.onsale_date ?? 'No date from Marvel'}</dd>
            </dl>
            {c.creators.length > 0 && (
              <>
                <h2>Credits</h2>
                <ul>{c.creators.map((cr, i) => <li key={i}>{cr.name}{cr.role ? ` (${cr.role})` : ''}</li>)}</ul>
              </>
            )}
          </article>
        )}
      </Status>
      <p><Link to="/">Back to the main shelf</Link></p>
    </Layout>
  )
}

export function CharacterDetail() {
  const { id } = useParams()
  const state = useApi<{ character: Character; comics: Comic[]; attribution: Attribution }>(`/api/characters/${id}`)
  return (
    <Layout attribution={state.status === 'ok' ? state.data.attribution : null}>
      <Status state={state}>
        {({ character: c, comics }) => (
          <>
            <h1>{c.name}</h1>
            <Thumb src={c.thumbnail} alt={c.name} large />
            <p>{c.description ?? 'No description from Marvel.'}</p>
            <h2>On the Hickman shelves</h2>
            <ComicList comics={comics} />
          </>
        )}
      </Status>
      <p><Link to="/">Back to the main shelf</Link></p>
    </Layout>
  )
}

export function Search() {
  const [input, setInput] = useState('')
  const [q, setQ] = useState('')
  const state = useApi<{ comics: Comic[]; characters: Character[]; attribution: Attribution }>(
    q.length >= 2 ? `/api/search?q=${encodeURIComponent(q)}` : null,
  )
  return (
    <Layout attribution={state.status === 'ok' ? state.data.attribution : null}>
      <h1>Search</h1>
      <form onSubmit={(e) => { e.preventDefault(); setQ(input.trim()) }}>
        <input aria-label="Search" value={input} onChange={(e) => setInput(e.target.value)} />
        <button type="submit">Search</button>
      </form>
      {q.length < 2 ? <p className="muted">Enter at least 2 characters.</p> : (
        <Status state={state}>
          {(d) => (
            <>
              <h2>Comics</h2>
              <ComicList comics={d.comics} />
              <h2>Characters</h2>
              {d.characters.length === 0 ? <p>No characters found.</p> : (
                <ul className="list">
                  {d.characters.map((c) => <li key={c.id}><Link to={`/characters/${c.id}`}>{c.name}</Link></li>)}
                </ul>
              )}
            </>
          )}
        </Status>
      )}
      <p><Link to="/">Back to the main shelf</Link></p>
    </Layout>
  )
}
