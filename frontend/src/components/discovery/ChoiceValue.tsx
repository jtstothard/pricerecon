import { useState } from 'react'

/** Presets never replace arbitrary persisted values. Custom input stays explicit. */
export function ChoiceValue({
  label,
  value,
  choices,
  onChange,
  required = false,
  name,
}: {
  label: string
  value: string
  choices: string[]
  onChange: (value: string) => void
  required?: boolean
  name?: string
}) {
  const [custom, setCustom] = useState(value !== '' && !choices.includes(value))
  const showCustom = custom || (value !== '' && !choices.includes(value))
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
        <option value="">Not set</option>
        {choices.map((choice) => (
          <option key={choice} value={choice}>
            {choice.replace(/_/g, ' ')}
          </option>
        ))}
        <option value="__custom">Other / custom</option>
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
