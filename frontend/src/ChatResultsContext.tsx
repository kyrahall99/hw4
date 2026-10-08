import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ProductMatches } from './api'

// Holds the latest product matches from the chat so any page can render them.
// It lives above the router, so results survive navigating to a product page and back.
interface ChatResultsState {
  results: ProductMatches | null
  /** True when the latest results came from a live chat reply (scroll them into view), false when restored from history. */
  fresh: boolean
  showResults: (m: ProductMatches, opts?: { fresh?: boolean }) => void
  clearResults: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ProductMatches | null>(null)
  const [fresh, setFresh] = useState(false)
  const showResults = (m: ProductMatches, opts?: { fresh?: boolean }) => {
    setFresh(opts?.fresh ?? true)
    setResults(m)
  }
  return (
    <ChatResultsContext.Provider value={{ results, fresh, showResults, clearResults: () => setResults(null) }}>
      {children}
    </ChatResultsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
