import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import en from './locales/en'
import zhCN from './locales/zh-CN'

export const SUPPORTED_LANGS = [
  { code: 'zh-CN', label: '简体中文' },
  { code: 'en', label: 'English' },
] as const

export type DocsLang = (typeof SUPPORTED_LANGS)[number]['code']

export const DEFAULT_LANG: DocsLang = 'zh-CN'

const resources = {
  en: { common: en },
  'zh-CN': { common: zhCN },
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: DEFAULT_LANG,
    defaultNS: 'common',
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'cni-docs-lang',
      caches: ['localStorage'],
    },
    interpolation: { escapeValue: false },
  })
  .then(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = i18n.resolvedLanguage || i18n.language || DEFAULT_LANG
    }
  })

i18n.on('languageChanged', (lng) => {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lng
  }
})

export function normalizeDocsLang(lng?: string | null): DocsLang {
  const raw = String(lng || '').trim()
  if (raw === 'zh-CN' || raw === 'en') return raw
  if (raw === 'zh' || raw.startsWith('zh-Hans') || raw.startsWith('zh')) return 'zh-CN'
  if (raw.startsWith('en')) return 'en'
  return DEFAULT_LANG
}

export default i18n
