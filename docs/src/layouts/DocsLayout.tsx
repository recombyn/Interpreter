import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { DOC_GROUP_DEFS, withDocsBase } from '@/data/nav'
import { LangSwitcher } from '@/components/LangSwitcher'

const GITHUB_URL = 'https://github.com/recombyn/concept-network-interpreter'

type TocItem = { id: string; text: string; level: number }

const DOC_SCROLL_EXTRA_PX = 16

function groupHasActivePath(items: { path: string }[], pathname: string): boolean {
  return items.some((item) => {
    if (item.path.endsWith('/')) return pathname === item.path || pathname === item.path.slice(0, -1)
    return pathname === item.path
  })
}

function docsNavOffsetPx(): number {
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--docs-nav-h')
  const nav = Number.parseFloat(raw)
  return (Number.isFinite(nav) ? nav : 56) + DOC_SCROLL_EXTRA_PX
}

function findArticleHeading(id: string): HTMLElement | null {
  const article = document.querySelector('.docs-main .docs-article')
  if (!article) return document.getElementById(id)
  try {
    return article.querySelector<HTMLElement>(`#${CSS.escape(id)}`) ?? document.getElementById(id)
  } catch {
    return document.getElementById(id)
  }
}

/** Window scroll only — avoids scrollIntoView also nudging sidebar/toc scrollports. */
function scrollWindowToHeading(id: string): HTMLElement | null {
  const el = findArticleHeading(id)
  if (!el) return null
  const top = Math.max(0, window.scrollY + el.getBoundingClientRect().top - docsNavOffsetPx())
  // `smooth` is cancelled when React Router updates the hash; use instant + preventScrollReset.
  window.scrollTo({ top, behavior: 'auto' })
  return el
}

function collectTocItems(root: ParentNode | null): TocItem[] {
  if (!root) return []
  const nodes = root.querySelectorAll<HTMLElement>('.docs-article h2[id], .docs-article h3[id]')
  return Array.from(nodes).map((el) => ({
    id: el.id,
    text: (el.textContent || '').trim(),
    level: el.tagName === 'H3' ? 3 : 2,
  }))
}

function SearchIcon() {
  return (
    <svg className="docs-search-icon" width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
      <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function DocsPageToc() {
  const { pathname, search } = useLocation()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [items, setItems] = useState<TocItem[]>([])
  const [activeId, setActiveId] = useState('')
  const clickLockUntilRef = useRef(0)
  const itemsRef = useRef<TocItem[]>([])

  useEffect(() => {
    let cancelled = false
    let mo: MutationObserver | null = null

    const sync = () => {
      if (cancelled) return
      const article = document.querySelector('.docs-main .docs-article')
      const next = collectTocItems(article)
      itemsRef.current = next
      setItems(next)
      setActiveId((prev) => {
        if (next.some((i) => i.id === prev)) return prev
        return next[0]?.id ?? ''
      })
    }

    const updateActiveFromScroll = () => {
      if (cancelled) return
      if (Date.now() < clickLockUntilRef.current) return
      const list = itemsRef.current
      if (!list.length) return
      const offset = docsNavOffsetPx()
      let current = list[0].id
      for (const item of list) {
        const el = findArticleHeading(item.id)
        if (!el) continue
        if (el.getBoundingClientRect().top - offset <= 8) current = item.id
      }
      setActiveId((prev) => (prev === current ? prev : current))
    }

    sync()
    const boot = window.setTimeout(() => {
      sync()
      updateActiveFromScroll()
      const hashId = decodeURIComponent(window.location.hash.replace(/^#/, ''))
      if (hashId && itemsRef.current.some((i) => i.id === hashId)) {
        clickLockUntilRef.current = Date.now() + 1200
        setActiveId(hashId)
        scrollWindowToHeading(hashId)
        window.setTimeout(() => {
          clickLockUntilRef.current = 0
        }, 1200)
      }
    }, 50)

    let debounce: number | undefined
    const main = document.querySelector('.docs-main')
    if (main) {
      mo = new MutationObserver(() => {
        window.clearTimeout(debounce)
        debounce = window.setTimeout(() => {
          sync()
          updateActiveFromScroll()
        }, 30)
      })
      mo.observe(main, { childList: true, subtree: true })
    }

    window.addEventListener('scroll', updateActiveFromScroll, { passive: true })

    return () => {
      cancelled = true
      window.clearTimeout(boot)
      window.clearTimeout(debounce)
      mo?.disconnect()
      window.removeEventListener('scroll', updateActiveFromScroll)
    }
  }, [pathname])

  if (!items.length) return null

  return (
    <aside className="docs-toc" aria-label={t('tocAria')}>
      <p className="docs-toc-title">{t('onThisPage')}</p>
      <nav className="docs-toc-list">
        {items.map((item, index) => (
          <a
            key={`${item.id}-${index}`}
            href={`#${item.id}`}
            className={`docs-toc-link level-${item.level}${activeId === item.id ? ' active' : ''}`}
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              clickLockUntilRef.current = Date.now() + 1500
              setActiveId(item.id)
              scrollWindowToHeading(item.id)
              navigate(
                { pathname, search, hash: item.id },
                { replace: true, preventScrollReset: true },
              )
              // RR hash updates can still nudge scroll after navigate — re-assert.
              window.setTimeout(() => {
                scrollWindowToHeading(item.id)
              }, 0)
              window.setTimeout(() => {
                scrollWindowToHeading(item.id)
                clickLockUntilRef.current = 0
              }, 50)
            }}
          >
            {item.text}
          </a>
        ))}
      </nav>
    </aside>
  )
}

type SearchHit = { path: string; title: string; group: string }

function DocsSearch() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const catalog = useMemo<SearchHit[]>(
    () =>
      DOC_GROUP_DEFS.flatMap((group) =>
        group.items.map((item) => ({
          path: item.path,
          title: t(`pages.${item.pageKey}`),
          group: t(`groups.${group.groupKey}`),
        })),
      ),
    [t],
  )

  const hits = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return catalog.slice(0, 8)
    return catalog.filter((hit) => {
      const hay = `${hit.title} ${hit.group} ${hit.path}`.toLowerCase()
      return hay.includes(q)
    }).slice(0, 12)
  }, [catalog, query])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey
      if (meta && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen(true)
      }
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (!open) return
    setQuery('')
    setActive(0)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const id = window.setTimeout(() => inputRef.current?.focus(), 0)
    return () => {
      window.clearTimeout(id)
      document.body.style.overflow = prev
    }
  }, [open])

  useEffect(() => {
    setActive(0)
  }, [query])

  function go(path: string) {
    setOpen(false)
    navigate(path)
  }

  function close() {
    setOpen(false)
  }

  const dialog =
    open && typeof document !== 'undefined'
      ? createPortal(
          <div
            className="docs-search-overlay"
            role="dialog"
            aria-modal="true"
            aria-label={t('searchAria')}
            onMouseDown={(e) => {
              if (e.target === e.currentTarget) close()
            }}
          >
            <div className="docs-search-panel">
              <div className="docs-search-input-wrap">
                <SearchIcon />
                <input
                  ref={inputRef}
                  className="docs-search-input"
                  value={query}
                  placeholder={t('searchPlaceholder')}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'ArrowDown') {
                      e.preventDefault()
                      setActive((i) => Math.min(i + 1, Math.max(hits.length - 1, 0)))
                      return
                    }
                    if (e.key === 'ArrowUp') {
                      e.preventDefault()
                      setActive((i) => Math.max(i - 1, 0))
                      return
                    }
                    if (e.key === 'Enter' && hits[active]) {
                      e.preventDefault()
                      go(hits[active].path)
                    }
                  }}
                />
                <button
                  type="button"
                  className="docs-search-close"
                  aria-label={t('searchClose')}
                  title={t('searchClose')}
                  onClick={close}
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
                    <path
                      d="M3 3l8 8M11 3L3 11"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                    />
                  </svg>
                </button>
              </div>
              <div className="docs-search-results">
                {hits.length === 0 ? (
                  <p className="docs-search-empty">{t('searchEmpty')}</p>
                ) : (
                  hits.map((hit, index) => (
                    <button
                      key={hit.path}
                      type="button"
                      className={`docs-search-hit${index === active ? ' active' : ''}`}
                      onMouseEnter={() => setActive(index)}
                      onClick={() => go(hit.path)}
                    >
                      <span className="docs-search-hit-title">{hit.title}</span>
                      <span className="docs-search-hit-group">{hit.group}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>,
          document.body,
        )
      : null

  return (
    <>
      <button type="button" className="docs-search" onClick={() => setOpen(true)}>
        <SearchIcon />
        <span className="docs-search-label">{t('searchPlaceholder')}</span>
        <kbd className="docs-search-kbd">Ctrl K</kbd>
      </button>
      {dialog}
    </>
  )
}

export function DocsLayout() {
  const { pathname } = useLocation()
  const { t } = useTranslation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(DOC_GROUP_DEFS.map((g) => [g.groupKey, true])),
  )

  useEffect(() => {
    setSidebarOpen(false)
  }, [pathname])

  useEffect(() => {
    const metaGroup = DOC_GROUP_DEFS.find((g) => groupHasActivePath(g.items, pathname))?.groupKey
    if (!metaGroup) return
    setOpenGroups((prev) => (prev[metaGroup] ? prev : { ...prev, [metaGroup]: true }))
  }, [pathname])

  function toggleGroup(groupKey: string) {
    setOpenGroups((prev) => ({ ...prev, [groupKey]: !prev[groupKey] }))
  }

  return (
    <div className={`docs-shell${sidebarOpen ? ' sidebar-open' : ''}`}>
      <aside className="docs-sidebar" aria-label={t('sidebarAria')}>
        <div className="docs-sidebar-brand">
          <Link to="/guide/getting-started" className="docs-brand">
            <img src={withDocsBase('/logo-mark.png')} width={20} height={20} alt="" />
            <span className="docs-brand-name">CNI</span>
            <span className="docs-brand-sub">{t('brandDocs')}</span>
          </Link>
        </div>
        <nav className="docs-sidebar-nav">
          {DOC_GROUP_DEFS.map((group) => {
            const open = openGroups[group.groupKey] ?? true
            const active = groupHasActivePath(group.items, pathname)
            return (
              <div key={group.groupKey} className={`docs-group${active ? ' has-active' : ''}`}>
                <button
                  type="button"
                  className="docs-group-toggle"
                  aria-expanded={open}
                  onClick={() => toggleGroup(group.groupKey)}
                >
                  <span className="docs-group-title">{t(`groups.${group.groupKey}`)}</span>
                  <svg
                    className={`docs-group-chevron${open ? ' open' : ''}`}
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="none"
                    aria-hidden
                  >
                    <path
                      d="M4 6l4 4 4-4"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                {open ? (
                  <div className="docs-group-list">
                    {group.items.map((item) => (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) => (isActive ? 'active' : undefined)}
                        end={item.path.endsWith('/')}
                      >
                        {t(`pages.${item.pageKey}`)}
                      </NavLink>
                    ))}
                  </div>
                ) : null}
              </div>
            )
          })}
        </nav>
      </aside>

      <div className="docs-right">
        <header className="docs-top">
          <button
            type="button"
            className="docs-mobile-toggle"
            aria-label={t('openMenu')}
            onClick={() => setSidebarOpen((v) => !v)}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
              <path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </button>

          <Link to="/guide/getting-started" className="docs-brand docs-brand-mobile">
            <img src={withDocsBase('/logo-mark.png')} width={20} height={20} alt="" />
            <span className="docs-brand-name">CNI</span>
          </Link>

          <DocsSearch />
          <div className="docs-top-spacer" />

          <nav className="docs-top-nav" aria-label={t('navAria')}>
            <Link
              to="/guide/getting-started"
              className={pathname.startsWith('/guide') ? 'active' : undefined}
            >
              {t('navGuide')}
            </Link>
            <Link
              to="/rules/layers"
              className={pathname.startsWith('/rules') ? 'active' : undefined}
            >
              {t('navRules')}
            </Link>
          </nav>

          <div className="docs-top-actions">
            <LangSwitcher />
            <a
              className="docs-icon-btn"
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="GitHub"
              title="GitHub"
            >
              <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.19 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
              </svg>
            </a>
          </div>
        </header>

        <div className="docs-body">
          <main className="docs-main">
            <div className="docs-main-inner">
              <Outlet />
            </div>
          </main>
          <DocsPageToc />
        </div>
      </div>

      {sidebarOpen ? (
        <button
          type="button"
          className="docs-sidebar-backdrop"
          aria-label={t('openMenu')}
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
    </div>
  )
}
