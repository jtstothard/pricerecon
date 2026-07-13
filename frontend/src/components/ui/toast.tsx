import { useEffect, useState } from 'react'

export type ToastVariant = 'success' | 'error' | 'info' | 'warning'

interface ToastProps {
  message: string
  variant?: ToastVariant
  duration?: number
  onClose?: () => void
}

export default function Toast({ message, variant = 'info', duration = 3000, onClose }: ToastProps) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false)
      setTimeout(() => onClose?.(), 150)
    }, duration)

    return () => clearTimeout(timer)
  }, [duration, onClose])

  if (!visible) return null

  const variantStyles = {
    success: {
      background: 'rgba(52, 211, 153, 0.12)',
      borderColor: 'rgba(52, 211, 153, 0.24)',
      color: '#a7f3d0'
    },
    error: {
      background: 'rgba(248, 113, 113, 0.12)',
      borderColor: 'rgba(248, 113, 113, 0.24)',
      color: '#fecaca'
    },
    info: {
      background: 'rgba(56, 189, 248, 0.12)',
      borderColor: 'rgba(56, 189, 248, 0.24)',
      color: '#7dd3fc'
    },
    warning: {
      background: 'rgba(251, 191, 36, 0.12)',
      borderColor: 'rgba(251, 191, 36, 0.24)',
      color: '#fde68a'
    }
  }

  const style = variantStyles[variant]

  return (
    <div
      className="toast-notification"
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        padding: '14px 18px',
        borderRadius: '12px',
        border: `1px solid ${style.borderColor}`,
        background: style.background,
        color: style.color,
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.32)',
        zIndex: 9999,
        animation: 'slideIn 0.3s ease, fadeOut 0.15s ease forwards',
        animationDelay: '0s, 2.85s',
        maxWidth: 'min(400px, 90vw)',
        wordBreak: 'break-word'
      }}
      role="alert"
      aria-live="polite"
    >
      {message}
    </div>
  )
}