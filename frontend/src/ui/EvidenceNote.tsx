export function EvidenceNote({ evidence }: { evidence: string | null | undefined }) {
  if (!evidence) return null

  return <div className="evidence-note">Из вашего текста: «{evidence}»</div>
}
