import { assetUrl } from '../api/client'
import type { FunFact } from '../api/types'
import './FunFactModal.css'

/** A source is only useful if it carries a real http(s) URL. */
function isValidSource(source: { url?: unknown }): source is { url: string } {
  return typeof source.url === 'string' && /^https?:\/\//i.test(source.url)
}

/** Shows a URL's host as its link label, falling back to the raw URL. */
function sourceLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export default function FunFactModal({
  fact,
  onDismiss,
}: {
  fact: FunFact
  onDismiss: () => void
}) {
  const sources = (fact.fact.sources ?? []).filter(isValidSource)

  return (
    <div className="fun-fact-modal-backdrop" onClick={onDismiss}>
      <div
        className="fun-fact-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="fun-fact-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="fun-fact-modal-eyebrow">Did you know?</span>
        <h2 id="fun-fact-modal-title">{fact.title}</h2>
        {fact.image && (
          <img
            className="fun-fact-modal-image"
            src={assetUrl(fact.image.filepath)}
            alt={fact.image.filename}
          />
        )}
        <p className="fun-fact-modal-text">{fact.fact.fact}</p>
        {sources.length > 0 && (
          <div className="fun-fact-modal-sources">
            <span className="fun-fact-modal-sources-label">Sources</span>
            <ul>
              {sources.map((source) => (
                <li key={source.url}>
                  <a href={source.url} target="_blank" rel="noopener noreferrer">
                    {sourceLabel(source.url)}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        <button type="button" className="btn btn-primary" onClick={onDismiss}>
          Back to it
        </button>
      </div>
    </div>
  )
}
