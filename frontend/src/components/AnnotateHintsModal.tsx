import './AnnotateHintsModal.css'

const HINTS = [
  'Match the same fixed point in both images (rock edge, coral tip, crack, bolt, etc.).',
  'Do not annotate moving things: fish, divers, plants swaying, floating particles, bubbles.',
  'Spread points across the whole image area, not just one corner.',
  'Prefer sharp, easy-to-recognize features over blurry areas.',
  'If a point is uncertain, skip it and choose a clearer one.',
  'Aim for quality over quantity.',
]

export default function AnnotateHintsModal({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div className="hints-modal-backdrop">
      <div className="hints-modal" role="dialog" aria-modal="true" aria-labelledby="hints-modal-title">
        <h2 id="hints-modal-title">Tips for good annotations</h2>
        <ul className="hints-modal-list">
          {HINTS.map((hint) => (
            <li key={hint}>{hint}</li>
          ))}
        </ul>
        <button type="button" className="btn btn-primary" onClick={onDismiss}>
          Got it
        </button>
      </div>
    </div>
  )
}
