import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import Markdown from 'react-markdown'
import { clearChatHistory, fetchChatHistory, sendChat, type ChatTurn, type PageContext } from '../api'
import { useAuth } from '../AuthContext'
import { useChatResults } from '../ChatResultsContext'
import { OPEN_CHAT_EVENT } from '../chatEvents'
import Crest from './Crest'

interface Message extends ChatTurn {
  matchCount?: number // how many product cards this reply put on the page
}

function greeting(firstName?: string): Message {
  return {
    role: 'assistant',
    content: firstName
      ? `Hi ${firstName}! I'm the Campus Customs assistant. Ask me about hoodies, tees, sizes, or prices.`
      : "Hi! I'm the Campus Customs assistant. Ask me about hoodies, tees, sizes, or prices. Log in to have me remember our chat.",
  }
}

// Describe the current page so the agent knows what "this" means.
function pageContext(pathname: string, visibleProductIds: string[]): PageContext {
  const detail = pathname.match(/^\/products\/([^/]+)$/)
  const types: Record<string, PageContext['page_type']> = {
    '/': 'home', '/products': 'products', '/about': 'about', '/login': 'login', '/create-account': 'create_account',
  }
  return {
    path: pathname,
    page_type: detail ? 'product_detail' : types[pathname] ?? 'other',
    product_id: detail ? decodeURIComponent(detail[1]) : null,
    visible_product_ids: visibleProductIds,
  }
}

// One-tap starter questions, chosen for the page the shopper is on.
function suggestionsFor(page: PageContext, loggedIn: boolean, hasHistory: boolean): string[] {
  if (page.page_type === 'product_detail') {
    return ['Is this in stock in M?', 'Does this come in other colors?', 'How much is this?', 'Show me similar items']
  }
  const base = page.page_type === 'products'
    ? ['Show me hoodies', "What's under $40?", 'Gifts for a Yale parent', 'Bulldog gear']
    : ['What hoodies do you have?', 'Residential college gear', 'Show me navy crewnecks', "What's in stock in XL?"]
  return loggedIn && hasHistory ? ['What was I looking at last time?', ...base.slice(0, 3)] : base
}

export default function ChatWidget() {
  const { user, loading } = useAuth()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([greeting()])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const { pathname } = useLocation()
  const { results, showResults, clearResults } = useChatResults()

  // Logged in: reload the saved conversation (and the last product results) from the database.
  // Logged out / guest: start fresh.
  useEffect(() => {
    if (loading) return
    let cancelled = false
    if (!user) {
      setMessages([greeting()])
      clearResults()
      return
    }
    fetchChatHistory()
      .then((saved) => {
        if (cancelled) return
        setMessages([
          greeting(user.first_name),
          ...saved.map((m) => ({ role: m.role, content: m.content, matchCount: m.matches?.products.length ?? 0 })),
        ])
        const lastMatches = [...saved].reverse().find((m) => m.matches)?.matches
        if (lastMatches) showResults(lastMatches, { fresh: false })
      })
      .catch(() => !cancelled && setMessages([greeting(user.first_name)]))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, loading])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open, sending])

  // Any "Ask about this" button on the site can open the chat and send a question.
  const sendRef = useRef<(text: string) => void>(() => {})
  useEffect(() => {
    const onOpen = (e: Event) => {
      setOpen(true)
      const msg = (e as CustomEvent<string | undefined>).detail
      if (msg) setTimeout(() => sendRef.current(msg), 50)
    }
    window.addEventListener(OPEN_CHAT_EVENT, onOpen)
    return () => window.removeEventListener(OPEN_CHAT_EVENT, onOpen)
  }, [])

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return
    // Guests: send recent turns from the browser. Logged in: the server loads history from the DB.
    const history: ChatTurn[] = user ? [] : messages.slice(1).slice(-10).map(({ role, content }) => ({ role, content }))
    const page = pageContext(pathname, results?.products.map((p) => p.product_id) ?? [])
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setSending(true)
    try {
      const res = await sendChat(text, history, page)
      // API contract: structured matches go to the page; the text reply stays in the chat.
      if (res.matches && res.matches.products.length > 0) showResults(res.matches)
      setMessages((m) => {
        const next = [...m]
        // If the server removed a card number / password, show the redacted text in the shopper's bubble too.
        if (res.message_redacted) next[next.length - 1] = { role: 'user', content: res.message_redacted }
        return [...next, { role: 'assistant', content: res.reply, matchCount: res.matches?.products.length ?? 0 }]
      })
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: (err as Error).message }])
    } finally {
      setSending(false)
    }
  }

  async function onClearHistory() {
    if (!window.confirm('Delete your saved chat history? This cannot be undone.')) return
    await clearChatHistory()
    setMessages([greeting(user?.first_name)])
    clearResults()
  }

  sendRef.current = (text: string) => void send(text)

  return (
    <div className="chat-widget">
      {open && (
        <section className="chat-panel" aria-label="Campus Customs chat">
          <header className="chat-header">
            <Crest size={26} />
            <span className="chat-title">
              Ask a Bulldog
              <small className="chat-subtitle"><i className="online-dot" />{user ? `Chatting as ${user.first_name} · history saved` : 'Guest chat · not saved'}</small>
            </span>
            <span className="chat-header-actions">
              {user && messages.length > 1 && (
                <button type="button" className="chat-clear" onClick={onClearHistory} title="Delete saved chat history">Clear</button>
              )}
              <button type="button" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
            </span>
          </header>
          <div className="chat-messages" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`chat-turn ${m.role}`}>
                {m.role === 'assistant' && <span className="chat-avatar"><Crest size={18} /></span>}
                <div className={`chat-bubble ${m.role}`}>
                  {/* react-markdown never renders raw HTML, so model output can't inject scripts. */}
                  {m.role === 'assistant' ? <Markdown>{m.content}</Markdown> : m.content}
                </div>
                {!!m.matchCount && (
                  <span className="chat-page-note">🛍️ {m.matchCount} {m.matchCount === 1 ? 'item' : 'items'} shown on the page</span>
                )}
              </div>
            ))}
            {sending && (
              <div className="chat-turn assistant">
                <span className="chat-avatar"><Crest size={18} /></span>
                <div className="chat-bubble assistant typing" aria-label="Assistant is checking the shop">
                  <span className="dots"><i /><i /><i /></span> Checking the shelves…
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
          {!sending && (
            <div className="chat-suggestions" aria-label="Suggested questions">
              {suggestionsFor(pageContext(pathname, []), !!user, messages.length > 1).map((sug) => (
                <button key={sug} type="button" onClick={() => void send(sug)}>{sug}</button>
              ))}
            </div>
          )}
          <form className="chat-input" onSubmit={onSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={pathname.startsWith('/products/') ? 'Ask about this item…' : 'Ask about merch, sizes, prices…'}
              aria-label="Chat message"
              maxLength={1000}
            />
            <button type="submit" disabled={sending || !input.trim()}>Send</button>
          </form>
        </section>
      )}
      <button type="button" className={`chat-toggle${open ? ' is-open' : ''}`} onClick={() => setOpen((o) => !o)} aria-label={open ? 'Close chat' : 'Open chat'}>
        {open ? '×' : <><Crest size={22} /><span>Ask a Bulldog</span></>}
      </button>
    </div>
  )
}
