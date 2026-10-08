// Lets any button on the site open the chat (optionally sending a question right away).
export const OPEN_CHAT_EVENT = 'cc:open-chat'

export function openChat(message?: string) {
  window.dispatchEvent(new CustomEvent<string | undefined>(OPEN_CHAT_EVENT, { detail: message }))
}
