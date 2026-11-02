import { useState } from 'react'

/** Presets never replace arbitrary persisted values. Custom input stays explicit. */
export function ChoiceValue({
  label,
  value,
  choices,
  onChange,
  required = false,
  name,
  current,
  placeholder,
  customLabel = 'Type another value…',
}: {
  label: string
  value: string
  choices: string[]
  onChange: (value: string) => void
  required?: boolean
  name?: string
  /** Recorded value for this field, offered first and marked as current. */
  current?: string
  /** First option text for required selects; no silent "Not set" trap. */
  placeholder?: string
  /** Self-describing escape hatch so any value is obviously allowed. */
  customLabel?: string
}) {
  const [custom, setCustom] = useState(value !== '' && !choices.includes(value))
  const showCustom = custom || (value !== '' && !choices.includes(value))
  const suggestions =
    current && !choices.includes(current) ? [current, ...choices] : choices
  return (
    <label>
      {label}
      <select
        required={required && !showCustom}
        name={!showCustom ? name : undefined}
        aria-label={label}
        value={showCustom ? '__custom' : value}
        onChange={(event) => {
          const next = event.target.value
          setCustom(next === '__custom')
          if (next !== '__custom') onChange(next)
        }}
      >
        <option value="">
          {required ? (placeholder ?? 'Choose a value…') : 'Not set'}
        </option>
        {suggestions.map((choice) => (
          <option key={choice} value={choice}>
            {choice === current ? `${choice} (current)` : choice.replace(/_/g, ' ')}
          </option>
        ))}
        <option value="__custom">{customLabel}</option>
      </select>
      {showCustom && (
        <input
          aria-label={`${label} custom value`}
          name={name}
          required={required}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </label>
  )
}
