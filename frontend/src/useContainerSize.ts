import { useCallback, useRef, useState } from 'react'

/**
 * The observed element mounts only once its containing data has loaded (an
 * async, conditionally-rendered container), so a plain object ref + mount-time
 * effect would miss it - the effect runs before the element exists. A
 * callback ref re-fires whenever the node itself mounts/unmounts instead.
 */
export function useContainerSize() {
  const [size, setSize] = useState({ width: 0, height: 0 })
  const observerRef = useRef<ResizeObserver | null>(null)

  const ref = useCallback((el: HTMLDivElement | null) => {
    observerRef.current?.disconnect()
    observerRef.current = null
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize({ width, height })
    })
    observer.observe(el)
    observerRef.current = observer
  }, [])

  return { ref, size }
}
