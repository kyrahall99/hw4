// Campus Customs crest: a navy shield with a collegiate "CC" monogram and a gold rule.
export default function Crest({ size = 40 }: { size?: number }) {
  return (
    <svg className="crest" width={size} height={size * 1.15} viewBox="0 0 40 46" aria-hidden="true">
      <path d="M20 1 L38 6 V22 C38 34 30 41 20 45 C10 41 2 34 2 22 V6 Z" fill="var(--navy)" stroke="var(--gold)" strokeWidth="1.5" />
      <path d="M8 13 H32" stroke="var(--gold)" strokeWidth="1.2" />
      <text x="20" y="31" textAnchor="middle" fontFamily="Fraunces Variable, Georgia, serif" fontWeight="800" fontSize="15" fill="#fff" letterSpacing="-0.5">CC</text>
    </svg>
  )
}
