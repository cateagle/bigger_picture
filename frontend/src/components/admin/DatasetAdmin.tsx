import { useEffect, useState } from 'react'
import { assetUrl } from '../../api/client'
import {
  fetchAnnotationsForDive,
  fetchCandidatePairsForDive,
  fetchImagePairsForDive,
  fetchImagesForDive,
} from '../../api/datasetApi'
import { fetchDivesForRegion } from '../../api/diveApi'
import { fetchRegions } from '../../api/regionApi'
import type { AnnotationSummary, CandidatePairSummary, DatasetImage, Dive, ImagePairSummary, Region } from '../../api/types'
import '../admin/AdminPanels.css'
import './DatasetAdmin.css'

const PAGE_SIZE = 25

function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  if (pageCount <= 1) return null
  return (
    <div className="dataset-admin-pagination">
      <button type="button" className="btn" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
        Previous
      </button>
      <span>
        Page {page} of {pageCount} ({total} total)
      </span>
      <button type="button" className="btn" onClick={() => onPageChange(page + 1)} disabled={page >= pageCount}>
        Next
      </button>
    </div>
  )
}

export default function DatasetAdmin() {
  const [regions, setRegions] = useState<Region[] | null>(null)
  const [regionUuid, setRegionUuid] = useState('')
  const [dives, setDives] = useState<Dive[] | null>(null)
  const [diveUuid, setDiveUuid] = useState('')

  const [images, setImages] = useState<DatasetImage[] | null>(null)
  const [imagesTotal, setImagesTotal] = useState(0)
  const [imagesPage, setImagesPage] = useState(1)

  const [candidates, setCandidates] = useState<CandidatePairSummary[] | null>(null)
  const [candidatesTotal, setCandidatesTotal] = useState(0)
  const [candidatesPage, setCandidatesPage] = useState(1)

  const [pairs, setPairs] = useState<ImagePairSummary[] | null>(null)
  const [pairsTotal, setPairsTotal] = useState(0)
  const [pairsPage, setPairsPage] = useState(1)

  const [annotations, setAnnotations] = useState<AnnotationSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchRegions()
      .then(setRegions)
      .catch(() => setError('Could not load regions.'))
  }, [])

  useEffect(() => {
    setDives(null)
    setDiveUuid('')
    if (!regionUuid) return
    fetchDivesForRegion(regionUuid)
      .then(setDives)
      .catch(() => setError('Could not load dives for this region.'))
  }, [regionUuid])

  useEffect(() => {
    setImages(null)
    setImagesTotal(0)
    setImagesPage(1)
    setCandidates(null)
    setCandidatesTotal(0)
    setCandidatesPage(1)
    setPairs(null)
    setPairsTotal(0)
    setPairsPage(1)
    setAnnotations(null)
  }, [diveUuid])

  useEffect(() => {
    if (!diveUuid) return
    fetchImagesForDive(diveUuid, imagesPage, PAGE_SIZE)
      .then(({ items, total }) => {
        setImages(items)
        setImagesTotal(total)
      })
      .catch(() => setError('Could not load images for this dive.'))
  }, [diveUuid, imagesPage])

  useEffect(() => {
    if (!diveUuid) return
    fetchCandidatePairsForDive(diveUuid, candidatesPage, PAGE_SIZE)
      .then(({ items, total }) => {
        setCandidates(items)
        setCandidatesTotal(total)
      })
      .catch(() => setError('Could not load candidate pairs for this dive.'))
  }, [diveUuid, candidatesPage])

  useEffect(() => {
    if (!diveUuid) return
    fetchImagePairsForDive(diveUuid, pairsPage, PAGE_SIZE)
      .then(({ items, total }) => {
        setPairs(items)
        setPairsTotal(total)
      })
      .catch(() => setError('Could not load image pairs for this dive.'))
  }, [diveUuid, pairsPage])

  useEffect(() => {
    if (!diveUuid) return
    fetchAnnotationsForDive(diveUuid)
      .then(setAnnotations)
      .catch(() => setError('Could not load annotations for this dive.'))
  }, [diveUuid])

  const annotationsFor = (pair: ImagePairSummary) =>
    (annotations ?? []).filter((a) => a.image_a === pair.image_a && a.image_b === pair.image_b)

  return (
    <div className="dataset-admin">
      {error && <p className="game-status game-status-error">{error}</p>}

      <div className="dataset-admin-pickers">
        <label className="admin-form-field">
          Region
          <select value={regionUuid} onChange={(e) => setRegionUuid(e.target.value)}>
            <option value="">Select a region…</option>
            {(regions ?? []).map((region) => (
              <option key={region.uuid} value={region.uuid}>
                {region.title}
              </option>
            ))}
          </select>
        </label>

        <label className="admin-form-field">
          Dive
          <select
            value={diveUuid}
            onChange={(e) => setDiveUuid(e.target.value)}
            disabled={!regionUuid || dives === null || dives.length === 0}
          >
            <option value="">
              {!regionUuid
                ? 'Select a region first'
                : dives === null
                  ? 'Loading…'
                  : dives.length === 0
                    ? 'No dives in this region'
                    : 'Select a dive…'}
            </option>
            {(dives ?? []).map((dive) => (
              <option key={dive.uuid} value={dive.uuid}>
                {dive.title}
              </option>
            ))}
          </select>
        </label>
      </div>

      {diveUuid && (
        <>
          <section className="dataset-admin-section">
            <h3>Images ({imagesTotal})</h3>
            {images === null ? (
              <p className="game-status">Loading…</p>
            ) : (
              <>
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Preview</th>
                      <th>Filename</th>
                      <th>Status</th>
                      <th>Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {images.map((image) => (
                      <tr key={image.uuid}>
                        <td>
                          <img src={assetUrl(image.filepath)} alt={image.filename} className="dataset-admin-thumb" />
                        </td>
                        <td>{image.filename}</td>
                        <td>{image.status ?? '—'}</td>
                        <td>
                          {image.size_x} × {image.size_y}
                        </td>
                      </tr>
                    ))}
                    {images.length === 0 && (
                      <tr>
                        <td colSpan={4}>No images in this dive yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <Pagination page={imagesPage} pageSize={PAGE_SIZE} total={imagesTotal} onPageChange={setImagesPage} />
              </>
            )}
          </section>

          <section className="dataset-admin-section">
            <h3>Candidate pairs ({candidatesTotal})</h3>
            {candidates === null ? (
              <p className="game-status">Loading…</p>
            ) : (
              <>
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Image A</th>
                      <th>Image B</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((pair) => (
                      <tr key={`${pair.image_a}:${pair.image_b}`}>
                        <td>{pair.image_a_filename}</td>
                        <td>{pair.image_b_filename}</td>
                        <td>{pair.status ?? '—'}</td>
                      </tr>
                    ))}
                    {candidates.length === 0 && (
                      <tr>
                        <td colSpan={3}>No candidate pairs in this dive yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <Pagination
                  page={candidatesPage}
                  pageSize={PAGE_SIZE}
                  total={candidatesTotal}
                  onPageChange={setCandidatesPage}
                />
              </>
            )}
          </section>

          <section className="dataset-admin-section">
            <h3>Image pairs ({pairsTotal})</h3>
            {pairs === null ? (
              <p className="game-status">Loading…</p>
            ) : (
              <>
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Image A</th>
                      <th>Image B</th>
                      <th>Difficulty</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Annotations</th>
                      <th>Expert levels</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pairs.map((pair) => {
                      const pairAnnotations = annotationsFor(pair)
                      return (
                        <tr key={`${pair.image_a}:${pair.image_b}`}>
                          <td>{pair.image_a_filename}</td>
                          <td>{pair.image_b_filename}</td>
                          <td>{pair.difficulty ?? '—'}</td>
                          <td>{pair.priority ?? '—'}</td>
                          <td>{pair.status ?? '—'}</td>
                          <td>{pairAnnotations.length === 0 ? 'None' : pairAnnotations.length}</td>
                          <td>
                            {pairAnnotations.length === 0
                              ? '—'
                              : pairAnnotations.map((a) => a.expert_level).join(', ')}
                          </td>
                        </tr>
                      )
                    })}
                    {pairs.length === 0 && (
                      <tr>
                        <td colSpan={7}>No image pairs in this dive yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <Pagination page={pairsPage} pageSize={PAGE_SIZE} total={pairsTotal} onPageChange={setPairsPage} />
              </>
            )}
          </section>
        </>
      )}
    </div>
  )
}
