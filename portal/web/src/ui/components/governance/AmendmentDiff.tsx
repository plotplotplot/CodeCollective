import { DiffView } from './DiffView'

type Props = {
  originalText: string
  proposedText: string
}

export function AmendmentDiff({ originalText, proposedText }: Props) {
  return (
    <DiffView 
      original={originalText} 
      proposed={proposedText}
      showUnchanged={true}
    />
  )
}
