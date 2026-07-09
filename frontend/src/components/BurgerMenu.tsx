import { useEffect, useRef, useState } from 'react'

/** Account-bar overflow menu: Admin (if applicable), My Stats, Log out. */
export default function BurgerMenu({
  showAdmin,
  onOpenAdmin,
  onOpenStats,
  onLogout,
}: {
  showAdmin: boolean
  onOpenAdmin: () => void
  onOpenStats: () => void
  onLogout: () => void
}) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const runAndClose = (action: () => void) => () => {
    setOpen(false)
    action()
  }

  return (
    <div className="burger-menu" ref={containerRef}>
      <button
        type="button"
        className="burger-menu-toggle"
        aria-label="Menu"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span />
        <span />
        <span />
      </button>
      {open && (
        <div className="burger-menu-dropdown" role="menu">
          {showAdmin && (
            <button type="button" role="menuitem" onClick={runAndClose(onOpenAdmin)}>
              Admin
            </button>
          )}
          <button type="button" role="menuitem" onClick={runAndClose(onOpenStats)}>
            My Stats
          </button>
          <button type="button" role="menuitem" onClick={runAndClose(onLogout)}>
            Log out
          </button>
        </div>
      )}
    </div>
  )
}
