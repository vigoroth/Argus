// Feather-style inline SVGs, stroke 1.9 — paths lifted from Odysseus.dc.html
type P = { size?: number; color?: string }
const I = ({ size = 18, color = 'currentColor', children }: P & { children: React.ReactNode }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
       strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">{children}</svg>
)

export const Plus = (p: P) => <I {...p}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></I>
export const Search = (p: P) => <I {...p}><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></I>
export const ChatBubble = (p: P) => <I {...p}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></I>
export const Globe = (p: P) => <I {...p}><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></I>
export const Bars = (p: P) => <I {...p}><line x1="6" y1="20" x2="6" y2="13"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="18" y1="20" x2="18" y2="9"/></I>
export const Term = (p: P) => <I {...p}><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></I>
export const Menu = (p: P) => <I {...p}><path d="M3 6h18M3 12h18M3 18h18"/></I>
export const ChevronDown = (p: P) => <I {...p}><polyline points="6 9 12 15 18 9"/></I>
export const ChevronRight = (p: P) => <I {...p}><polyline points="9 18 15 12 9 6"/></I>
export const ChevronLeft = (p: P) => <I {...p}><polyline points="15 18 9 12 15 6"/></I>
export const ArrowUp = (p: P) => <I {...p}><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></I>
export const Key = (p: P) => <I {...p}><circle cx="8" cy="15" r="4"/><path d="M10.85 12.15 19 4"/><path d="M18 5l2 2"/><path d="M15 8l2 2"/></I>
export const Calendar = (p: P) => <I {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></I>
export const Bot = (p: P) => <I {...p}><rect x="4" y="8" width="16" height="12" rx="2"/><path d="M12 8V4"/><circle cx="12" cy="3" r="1"/><line x1="9" y1="13" x2="9" y2="15"/><line x1="15" y1="13" x2="15" y2="15"/></I>
export const Zap = (p: P) => <I {...p}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></I>
