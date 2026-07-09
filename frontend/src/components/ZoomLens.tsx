import type { RefObject } from 'react'
import type { NormalizedPoint } from '../api/types'
import './ZoomLens.css'

type Props = {
  imageRef: RefObject<HTMLImageElement | null>
  point: NormalizedPoint | null
  cursor: { x: number; y: number } | null
  zoom?: number
}

export function ZoomLens({
  imageRef,
  point,
  cursor,
  zoom = 4,
}: Props) {
  const image = imageRef.current

  if (!image || !point || !cursor) return null

  const size = 160

  const rect = image.getBoundingClientRect()

  // Punkt in echten Bildschirm-/Bildpixeln
     const x = point.x * rect.width
     const y = point.y * rect.height
    //  const x = cursor.x 
    //  const y = cursor.y 
     console.log(cursor.x, cursor.y, x, y);

  return (
    <div
      className="zoom-lens"
      style={{
        left: cursor.x + 20,
        top: cursor.y + 20,
        

        backgroundImage: `url(${image.src})`,

        backgroundSize: `
          ${rect.width * zoom}px
          ${rect.height * zoom}px
        `,
        // backgroundPosition: `
        //   ${-(x * zoom) + size / 2}px
        //   ${-(y * zoom) + size / 2}px
        backgroundPosition: `
          ${size / 2 - x * zoom}px
          ${size / 2 - y * zoom}px
        `,
      }}
    />
  )
}