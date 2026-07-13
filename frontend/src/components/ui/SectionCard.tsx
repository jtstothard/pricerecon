import type { ReactNode } from 'react'

interface SectionCardProps {
  title: string
  subtitle?: string
  eyebrow?: string
  action?: ReactNode
  children: ReactNode
  className?: string
  headingLevel?: 'h1' | 'h2' | 'h3'
  id?: string
}

export default function SectionCard({ title, subtitle, eyebrow, action, children, className = '', headingLevel = 'h2', id }: SectionCardProps) {
  const HeadingTag = headingLevel
  const isPageTitle = headingLevel === 'h1'

  return (
    <section className={`section-card ${className}`.trim()} id={isPageTitle ? undefined : id}>
      <header className="section-card__header">
        <div className="section-card__title">
          {eyebrow ? <div className="section-card__eyebrow">{eyebrow}</div> : null}
          <HeadingTag id={isPageTitle ? id : undefined} tabIndex={isPageTitle ? -1 : undefined}>{title}</HeadingTag>
          {subtitle ? <div className="section-card__subtitle">{subtitle}</div> : null}
        </div>
        {action ? <div>{action}</div> : null}
      </header>
      <div className="section-card__body">{children}</div>
    </section>
  )
}
