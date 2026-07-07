export interface ImagePair {
  pairId: string
  imageA: string
  imageB: string
}

/** A click location, normalized to the image's own [0, 1] x [0, 1] space. */
export interface NormalizedPoint {
  x: number
  y: number
}

export interface Correspondence {
  pointA: NormalizedPoint
  pointB: NormalizedPoint
}
