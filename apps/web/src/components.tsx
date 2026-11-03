import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { Attribution, Comic, State } from './api'

export function attributionText(a?: Attribution | null): string | null {
  if (!a) return null
  if (a.text) return a.text
  if (a.html) return new DOMParser().parseFromString(a.html, 'text/html').body.textContent
  return null
}

export function AttributionLine({ attribution }: { attribution?: Attribution | null }) {
  const text = attributionText(attribution)
  return text ? <span className="attribution">{text}</span> : null
}

export function Layout({ attribution, children }: { attribution?: Attribution | null; children: ReactNode }) {
  return (
    <div className="page">
      <header>
        <span className="site-name">House of X</span>
        <AttributionLine attribution={attribution} />
        <nav>
          <Link to="/">Main shelf</Link>
          <Link to="/shelves">Shelves</Link>
          <Link to="/search">Search</Link>
        </nav>
      </header>
      <main>{children}</main>
      <footer>
        <span className="site-name">House of X</span>
        <AttributionLine attribution={attribution} />
      </footer>
    </div>
  )
}

export function Thumb({ src, alt, large }: { src: string | null; alt: string; large?: boolean }) {
  return <img className={large ? 'thumb large' : 'thumb'} src={src ?? '/placeholder.svg'} alt={alt} loading="lazy" />
}

export function Status<T>({ state, children }: { state: State<T>; children: (data: T) => ReactNode }) {
  if (state.status === 'loading') return <p role="status">Loading…</p>
  if (state.status === 'error') return <p role="alert" className="error">{state.message}</p>
  return <>{children(state.data)}</>
}

export function comicLabel(c: Comic) {
  return c.title
}

export function ComicList({ comics }: { comics: Comic[] }) {
  if (comics.length === 0) return <p>No comics on this shelf.</p>
  return (
    <ul className="list">
      {comics.map((c) => (
        <li key={c.id}>
          <Thumb src={c.thumbnail} alt="" />
          <div>
            <Link to={`/comics/${c.id}`}>{comicLabel(c)}</Link>
            <div className="muted">
              {c.onsale_date ?? 'No on-sale date from Marvel'}
              {!c.in_resolved_series && ' · API result from another series'}
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}
