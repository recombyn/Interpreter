import type { DocsLang } from '@/i18n'

/** Prefix public asset / absolute path with Vite `base` (GitHub Pages). */
export function withDocsBase(path: string): string {
  const base = import.meta.env.BASE_URL || '/'
  if (/^https?:\/\//i.test(path)) return path
  const clean = path.startsWith('/') ? path.slice(1) : path
  return `${base}${clean}`
}

export type DocLink = {
  pageKey: string
  path: string
}

export type DocGroupDef = {
  groupKey: string
  items: DocLink[]
}

/** Help docs sidebar structure (titles come from i18n). */
export const DOC_GROUP_DEFS: DocGroupDef[] = [
  {
    groupKey: 'guide',
    items: [
      { pageKey: 'getting-started', path: '/guide/getting-started' },
      { pageKey: 'overview', path: '/guide/overview' },
      { pageKey: 'architecture', path: '/guide/architecture' },
      { pageKey: 'lexicon', path: '/guide/lexicon' },
      { pageKey: 'boundaries', path: '/guide/boundaries' },
    ],
  },
  {
    groupKey: 'rules',
    items: [
      { pageKey: 'layers', path: '/rules/layers' },
      { pageKey: 'catalog', path: '/rules/catalog' },
    ],
  },
]

const DOC_MODULES = {
  ...import.meta.glob('../../content/{zh-CN,en}/{guide,rules}/**/*.md', {
    query: '?raw',
    import: 'default',
    eager: true,
  }),
} as Record<string, string>

function filePathToRoute(file: string): { locale: DocsLang; path: string } | null {
  const normalized = file.replace(/\\/g, '/')
  const m = normalized.match(/\/content\/(zh-CN|en)\/(.+)\.md$/)
  if (!m) return null
  const locale = m[1] as DocsLang
  let rel = m[2]
  if (rel.endsWith('/index')) {
    rel = rel.slice(0, -'/index'.length)
    return { locale, path: `/${rel}/` }
  }
  return { locale, path: `/${rel}` }
}

/** locale → route path → markdown body */
export const DOC_CONTENT_BY_LOCALE: Record<DocsLang, Record<string, string>> = {
  'zh-CN': {},
  en: {},
}

for (const [file, raw] of Object.entries(DOC_MODULES)) {
  const parsed = filePathToRoute(file)
  if (!parsed) continue
  DOC_CONTENT_BY_LOCALE[parsed.locale][parsed.path] = stripFrontmatter(raw)
}

export function stripFrontmatter(raw: string): string {
  return raw.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n*/, '')
}

export function normalizePath(pathname: string): string {
  let p = pathname.replace(/\.html$/, '')
  if (p.length > 1 && p.endsWith('/')) {
    const without = p.slice(0, -1)
    for (const locale of Object.keys(DOC_CONTENT_BY_LOCALE) as DocsLang[]) {
      const map = DOC_CONTENT_BY_LOCALE[locale]
      if (map[p] || map[`${without}/`]) return map[p] ? p : `${without}/`
    }
    return without
  }
  for (const locale of Object.keys(DOC_CONTENT_BY_LOCALE) as DocsLang[]) {
    const map = DOC_CONTENT_BY_LOCALE[locale]
    if (map[p]) return p
    if (map[`${p}/`]) return `${p}/`
  }
  return p
}

const FALLBACK_ORDER: DocsLang[] = ['zh-CN', 'en']

export function getDocMarkdown(pathname: string, locale: DocsLang): string | undefined {
  const path = normalizePath(pathname)
  const primary = DOC_CONTENT_BY_LOCALE[locale]?.[path]
  if (primary) return primary
  for (const fb of FALLBACK_ORDER) {
    if (fb === locale) continue
    const hit = DOC_CONTENT_BY_LOCALE[fb]?.[path]
    if (hit) return hit
  }
  return undefined
}

export function findDocMeta(
  pathname: string,
): { groupKey: string; pageKey: string; path: string } | null {
  const path = normalizePath(pathname)
  for (const group of DOC_GROUP_DEFS) {
    for (const item of group.items) {
      if (item.path === path || item.path === `${path}/` || `${item.path}` === path) {
        return { groupKey: group.groupKey, pageKey: item.pageKey, path: item.path }
      }
    }
  }
  return null
}

export function listDocLinksFlat(): DocLink[] {
  return DOC_GROUP_DEFS.flatMap((g) => g.items)
}

export function findDocNeighbors(pathname: string): {
  prev: DocLink | null
  next: DocLink | null
  current: DocLink | null
} {
  const flat = listDocLinksFlat()
  const path = normalizePath(pathname)
  const index = flat.findIndex(
    (item) => item.path === path || item.path === `${path}/` || `${item.path}` === path,
  )
  if (index < 0) return { prev: null, next: null, current: null }
  return {
    current: flat[index],
    prev: index > 0 ? flat[index - 1] : null,
    next: index < flat.length - 1 ? flat[index + 1] : null,
  }
}

export function contentFileForDoc(pathname: string, locale: DocsLang): string | null {
  const path = normalizePath(pathname)
  const tryLocale = (lang: DocsLang): string | null => {
    const map = DOC_CONTENT_BY_LOCALE[lang]
    if (map[path] != null) {
      if (path.endsWith('/')) return `${lang}${path}index.md`
      return `${lang}${path}.md`
    }
    if (map[`${path}/`] != null) return `${lang}${path}/index.md`
    return null
  }
  const primary = tryLocale(locale)
  if (primary) return primary
  for (const fb of FALLBACK_ORDER) {
    if (fb === locale) continue
    const hit = tryLocale(fb)
    if (hit) return hit
  }
  return null
}

const DOCS_GITHUB_REPO = 'https://github.com/recombyn/concept-network-interpreter'

export function githubEditUrl(pathname: string, locale: DocsLang): string | null {
  const file = contentFileForDoc(pathname, locale)
  if (!file) return null
  return `${DOCS_GITHUB_REPO}/edit/main/docs/content/${file}`
}

export function isHelpDocPath(pathname: string): boolean {
  const p = normalizePath(pathname)
  return p.startsWith('/guide/') || p.startsWith('/rules/')
}
