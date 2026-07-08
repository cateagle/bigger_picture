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

export default function DatasetAdmin() {
  const [regions, setRegions] = useState<Region[] | null>(null)
  const [regionUuid, setRegionUuid] = useState('')
  const [dives, setDives] = useState<Dive[] | null>(null)
  const [diveUuid, setDiveUuid] = useState('')
  const [images, setImages] = useState<DatasetImage[] | null>(null)
  const [candidates, setCandidates] = useState<CandidatePairSummary[] | null>(null)
  const [pairs, setPairs] = useState<ImagePairSummary[] | null>(null)
  const [annotations, setAnnotations] = useState<AnnotationSummary[] | null>(null)
  const [loading, setLoading] = useState(false)
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
    setCandidates(null)
    setPairs(null)
    setAnnotations(null)
    if (!diveUuid) return
    setLoading(true)
    setError(null)
    Promise.all([
      fetchImagesForDive(diveUuid),
      fetchCandidatePairsForDive(diveUuid),
      fetchImagePairsForDive(diveUuid),
      fetchAnnotationsForDive(diveUuid),
    ])
      .then(([imagesRes, candidatesRes, pairsRes, annotationsRes]) => {
        setImages(imagesRes)
        setCandidates(candidatesRes)
        setPairs(pairsRes)
        setAnnotations(annotationsRes)
      })
      .catch(() => setError('Could not load images/pairs for this dive.'))
      .finally(() => setLoading(false))
  }, [diveUuid])

  const filenameFor = (uuid: string) => images?.find((img) => img.uuid === uuid)?.filename ?? uuid

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

      {loading && <p className="game-status">Loading…</p>}

      {diveUuid && !loading && images && (
        <>
          <section className="dataset-admin-section">
            <h3>Images ({images.length})</h3>
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
          </section>

          <section className="dataset-admin-section">
            <h3>Candidate pairs ({candidates?.length ?? 0})</h3>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Image A</th>
                  <th>Image B</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(candidates ?? []).map((pair) => (
                  <tr key={`${pair.image_a}:${pair.image_b}`}>
                    <td>{filenameFor(pair.image_a)}</td>
                    <td>{filenameFor(pair.image_b)}</td>
                    <td>{pair.status ?? '—'}</td>
                  </tr>
                ))}
                {(candidates ?? []).length === 0 && (
                  <tr>
                    <td colSpan={3}>No candidate pairs in this dive yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          <section className="dataset-admin-section">
            <h3>Image pairs ({pairs?.length ?? 0})</h3>
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
                {(pairs ?? []).map((pair) => {
                  const pairAnnotations = annotationsFor(pair)
                  return (
                    <tr key={`${pair.image_a}:${pair.image_b}`}>
                      <td>{filenameFor(pair.image_a)}</td>
                      <td>{filenameFor(pair.image_b)}</td>
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
                {(pairs ?? []).length === 0 && (
                  <tr>
                    <td colSpan={7}>No image pairs in this dive yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  )
}
