export type SectionOption<T extends string> = { id: T; label: string }

type Props<T extends string> = {
  label: string
  options: SectionOption<T>[]
  current: T
  onChange: (section: T) => void
}

export default function SectionNavigation<T extends string>({ label, options, current, onChange }: Props<T>) {
  return (
    <nav className="section-nav" aria-label={label}>
      {options.map((option) => (
        <button key={option.id} type="button"
          aria-current={option.id === current ? 'page' : undefined}
          onClick={() => onChange(option.id)}>
          {option.label}
        </button>
      ))}
    </nav>
  )
}
