// Types and fetch helpers for the FastAPI backend (proxied by Vite).

export interface SizeStock {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string
  price: number
  inventory: SizeStock[]
  total_stock: number
}

// Chat -> page contract: structured product matches the agent found this turn.
export interface ProductMatches {
  title: string
  query: string
  total_matches: number
  products: Product[]
}

export interface ChatResponse {
  reply: string
  message_redacted: string | null
  matches: ProductMatches | null
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<Product[]>('/api/products')

export const fetchProduct = (id: string) =>
  getJson<Product>(`/api/products/${encodeURIComponent(id)}`)

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface PageContext {
  path: string
  page_type: 'home' | 'products' | 'product_detail' | 'about' | 'login' | 'create_account' | 'other'
  product_id: string | null
  visible_product_ids: string[]
}

export interface HistoryMessage extends ChatTurn {
  created_at: string
  matches: ProductMatches | null
}

export const fetchChatHistory = () =>
  getJson<{ messages: HistoryMessage[] }>('/api/chat/history', { credentials: 'include' }).then((d) => d.messages)

export const clearChatHistory = () => fetch('/api/chat/history', { method: 'DELETE', credentials: 'include' })

export async function sendChat(message: string, history: ChatTurn[], page: PageContext): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ message, history, page }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : "Sorry, I can't reach the shop right now. Please try again.")
  return data as ChatResponse
}

export const formatPrice = (price: number) => `$${price.toFixed(2)}`

// ---- Accounts ----

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
}

export interface SignupData {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

async function postAuth<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.')
  return data as T
}

export const login = (email: string, password: string) => postAuth<User>('/api/login', { email, password })
export const signup = (data: SignupData) => postAuth<User>('/api/signup', data)
export const logout = () => fetch('/api/logout', { method: 'POST', credentials: 'include' })
export const fetchMe = () => getJson<User | null>('/api/me', { credentials: 'include' })
