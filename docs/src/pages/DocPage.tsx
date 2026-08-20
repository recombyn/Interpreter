import { useEffect } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  findDocMeta,
  findDocNeighbors,
  getDocMarkdown,
  githubEditUrl,
  normalizePath,
} from '@/data/nav'
import { MarkdownView } from '@/components/MarkdownView'
import { normalizeDocsLang } from '@/i18n'

export function DocPage() {
  const { pathname } = useLocation()
  const { t, i18n } = useTranslation()
  const path = normalizePath(pathname)
  const locale = normalizeDocsLang(i18n.resolvedLanguage || i18n.language)
  const markdown = getDocMarkdown(path, locale)
  const meta = findDocMeta(path)
  const { prev, next } = findDocNeighbors(path)
  const editUrl = githubEditUrl(path, locale)

  useEffect(() => {
    const title = meta ? t(`pages.${meta.pageKey}`) : null
    document.title = title ? `${title} · ${t('docTitleSuffix')}` : t('docTitleSuffix')
  }, [meta, t, i18n.language])

  if (!markdown) {
    return <Navigate to="/guide/getting-started" replace />
  }

  return (
    <div className="docs-page">
      <MarkdownView key={`${locale}:${path}`} className="docs-article" markdown={markdown} />

      <footer className="docs-page-footer">
        {editUrl ? (
          <a
            className="docs-edit-link"
            href={editUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
              <path d="M11.013 1.427a1.75 1.75 0 0 1 2.474 0l1.086 1.086a1.75 1.75 0 0 1 0 2.474l-8.61 8.61c-.21.21-.47.364-.752.453l-3.498 1.1a.75.75 0 0 1-.93-.93l1.1-3.498c.089-.282.244-.542.453-.752zM10.25 3.5l2.25 2.25" />
            </svg>
            {t('editOnGithub')}
          </a>
        ) : null}

        {prev || next ? (
          <nav className="docs-pager" aria-label={t('pagerAria')}>
            {prev ? (
              <Link to={prev.path} className="docs-pager-card prev">
                <span className="docs-pager-label">{t('pagerPrev')}</span>
                <span className="docs-pager-title">{t(`pages.${prev.pageKey}`)}</span>
              </Link>
            ) : (
              <span className="docs-pager-spacer" />
            )}
            {next ? (
              <Link to={next.path} className="docs-pager-card next">
                <span className="docs-pager-label">{t('pagerNext')}</span>
                <span className="docs-pager-title">{t(`pages.${next.pageKey}`)}</span>
              </Link>
            ) : (
              <span className="docs-pager-spacer" />
            )}
          </nav>
        ) : null}
      </footer>
    </div>
  )
}
