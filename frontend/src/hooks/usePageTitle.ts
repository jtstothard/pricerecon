import { useEffect } from 'react'

export function usePageTitle(title: string) {
  useEffect(() => {
    const fullTitle = `${title} · PriceRecon`
    document.title = fullTitle

    // Cleanup to reset title when unmounting
    return () => {
      document.title = 'PriceRecon'
    }
  }, [title])
}