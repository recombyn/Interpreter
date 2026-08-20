import { useMemo, useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSlug from 'rehype-slug'
import { Link } from 'react-router-dom'
import type { Components } from 'react-markdown'
import { withDocsBase } from '@/data/nav'

type Props = {
  markdown: string
  className?: string
}

function isInternal(href: string | undefined): href is string {
  return !!href && href.startsWith('/') && !href.startsWith('//')
}

function heading(Tag: 'h1' | 'h2' | 'h3' | 'h4') {
  return function Heading({
    id,
    children,
  }: {
    id?: string
    children?: ReactNode
  }) {
    return <Tag id={id}>{children}</Tag>
  }
}

function codeLanguage(className: string | undefined): string {
  if (!className) return ''
  const match = /language-([\w-]+)/.exec(className)
  return match?.[1] ?? ''
}

function CodeBlock({
  className,
  children,
}: {
  className?: string
  children?: ReactNode
}) {
  const [copied, setCopied] = useState(false)
  const lang = codeLanguage(className)
  const text = String(children ?? '').replace(/\n$/, '')

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1200)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="docs-codeblock">
      <div className="docs-codeblock-bar">
        {lang ? <span className="docs-codeblock-lang">{lang}</span> : <span />}
        <button
          type="button"
          className="docs-codeblock-copy"
          aria-label={copied ? 'Copied' : 'Copy'}
          title={copied ? 'Copied' : 'Copy'}
          onClick={() => {
            copyCode()
          }}
        >
          {copied ? (
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
              <path
                d="M3.5 8.5l3 3 6-7"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
              <rect x="5.5" y="5.5" width="7" height="7" rx="1.2" stroke="currentColor" strokeWidth="1.4" />
              <path
                d="M3.5 10.5V3.8A1.3 1.3 0 0 1 4.8 2.5H10.5"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
            </svg>
          )}
        </button>
      </div>
      <pre>
        <code className={className}>{children}</code>
      </pre>
    </div>
  )
}

export function MarkdownView({ markdown, className }: Props) {
  const components = useMemo<Components>(
    () => ({
      h1: heading('h1'),
      h2: heading('h2'),
      h3: heading('h3'),
      h4: heading('h4'),
      a({ href, children }) {
        if (isInternal(href)) {
          return <Link to={href}>{children}</Link>
        }
        return (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        )
      },
      img({ src, alt, ...rest }) {
        const resolved = src && src.startsWith('/') ? withDocsBase(src) : src
        return <img src={resolved} alt={alt ?? ''} {...rest} />
      },
      pre({ children }) {
        return <>{children}</>
      },
      code({ className: codeClass, children, ...rest }) {
        const isBlock = Boolean(codeClass) || String(children).includes('\n')
        if (!isBlock) {
          return (
            <code className={codeClass} {...rest}>
              {children}
            </code>
          )
        }
        return <CodeBlock className={codeClass}>{children}</CodeBlock>
      },
    }),
    [],
  )

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, rehypeSlug]}
        components={components}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  )
}
