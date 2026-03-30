import { useMemo } from 'react'

interface UnifiedDiffProps {
  original: string
  amendments: Array<{
    id: string
    title: string
    body: string
    proposedBodyDiff?: string
    proposerName: string
    status: string
  }>
}

interface Change {
  amendmentId: string
  amendmentTitle: string
  color: string
  lineNum: number
  addedText: string // Only the text that was added
}

/**
 * Find what text was added at the end of a line (simple suffix matching)
 */
function findAddedSuffix(original: string, modified: string): string {
  if (!original) return modified
  if (!modified) return ''
  
  // If modified starts with original, the difference is the suffix
  if (modified.startsWith(original)) {
    return modified.slice(original.length)
  }
  
  // Otherwise do word-level comparison
  const origWords = original.split(' ')
  const modWords = modified.split(' ')
  
  // Find common prefix words
  let commonIdx = 0
  while (commonIdx < origWords.length && 
         commonIdx < modWords.length && 
         origWords[commonIdx] === modWords[commonIdx]) {
    commonIdx++
  }
  
  // Return the differing part
  return modWords.slice(commonIdx).join(' ')
}

/**
 * Find what text was added (for new lines or inline additions)
 */
function findAdditions(original: string, modified: string): string {
  const origTrimmed = original.trim()
  const modTrimmed = modified.trim()
  
  if (!origTrimmed) return modTrimmed
  if (!modTrimmed) return ''
  
  // Check if it's a simple suffix addition
  if (modTrimmed.startsWith(origTrimmed)) {
    return modTrimmed.slice(origTrimmed.length).trim()
  }
  
  // Check if it's a prefix addition
  if (modTrimmed.endsWith(origTrimmed)) {
    return modTrimmed.slice(0, modTrimmed.length - origTrimmed.length).trim()
  }
  
  // Check for inline additions (word boundaries)
  const origWords = origTrimmed.split(/\s+/)
  const modWords = modTrimmed.split(/\s+/)
  
  // If modified has more words, find the new ones
  if (modWords.length > origWords.length) {
    // Find where they differ
    let diffStart = 0
    while (diffStart < origWords.length && origWords[diffStart] === modWords[diffStart]) {
      diffStart++
    }
    
    // Return words from diffStart to end
    return modWords.slice(diffStart).join(' ')
  }
  
  // If same word count but different words
  if (modWords.length === origWords.length) {
    const diffs: string[] = []
    for (let i = 0; i < modWords.length; i++) {
      if (modWords[i] !== origWords[i]) {
        diffs.push(modWords[i])
      }
    }
    if (diffs.length > 0) {
      return diffs.join(' ')
    }
  }
  
  return modTrimmed
}

export function UnifiedDiff({ original, amendments }: UnifiedDiffProps) {
  const { baseLines, changes, amendmentColors } = useMemo(() => {
    // Generate colors
    const colors = ['#22c55e', '#3b82f6', '#a855f7', '#f59e0b', '#ec4899', '#14b8a6']
    const colorMap: Record<string, string> = {}
    amendments.forEach((a, i) => {
      colorMap[a.id] = colors[i % colors.length]
    })
    
    const originalLines = original.split('\n')
    const baseLines: Array<{ text: string; lineNum: number; hasChanges: boolean }> = []
    const allChanges: Change[] = []
    
    // Process each line
    originalLines.forEach((line, idx) => {
      const lineNum = idx + 1
      let hasChanges = false
      
      // Check each amendment for changes to this line
      amendments.forEach(amendment => {
        const proposedLines = (amendment.proposedBodyDiff || amendment.body).split('\n')
        const proposedLine = proposedLines[idx]
        
        if (proposedLine !== undefined && proposedLine !== line) {
          hasChanges = true
          const addedText = findAdditions(line, proposedLine)
          
          if (addedText) {
            allChanges.push({
              amendmentId: amendment.id,
              amendmentTitle: amendment.title,
              color: colorMap[amendment.id],
              lineNum,
              addedText,
            })
          }
        }
      })
      
      baseLines.push({ text: line, lineNum, hasChanges })
    })
    
    // Check for added lines (beyond original length)
    amendments.forEach(amendment => {
      const proposedLines = (amendment.proposedBodyDiff || amendment.body).split('\n')
      
      proposedLines.slice(originalLines.length).forEach((line, offset) => {
        allChanges.push({
          amendmentId: amendment.id,
          amendmentTitle: amendment.title,
          color: colorMap[amendment.id],
          lineNum: originalLines.length + offset + 1,
          addedText: line,
        })
      })
    })
    
    // Sort changes by line number, then by amendment
    allChanges.sort((a, b) => {
      if (a.lineNum !== b.lineNum) return a.lineNum - b.lineNum
      return amendments.findIndex(am => am.id === a.amendmentId) - 
             amendments.findIndex(am => am.id === b.amendmentId)
    })
    
    return { baseLines, changes: allChanges, amendmentColors: colorMap }
  }, [original, amendments])
  
  if (amendments.length === 0) {
    return (
      <div style={{
        padding: '16px',
        backgroundColor: 'var(--panel-2)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        color: 'var(--text-muted)',
        fontSize: 14,
        fontStyle: 'italic',
      }}>
        No amendments proposed
      </div>
    )
  }
  
  // Group changes by line number
  const changesByLine = changes.reduce((acc, change) => {
    if (!acc[change.lineNum]) acc[change.lineNum] = []
    acc[change.lineNum].push(change)
    return acc
  }, {} as Record<number, Change[]>)
  
  return (
    <div style={{
      fontSize: 14,
      lineHeight: 1.6,
      borderRadius: 'var(--radius-md)',
      border: '1px solid var(--border-subtle)',
      overflow: 'hidden',
      backgroundColor: 'var(--panel)',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        backgroundColor: 'var(--panel-2)',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: 'var(--text-secondary)',
          marginBottom: 10,
        }}>
          Unified Diff ({amendments.length} amendment{amendments.length !== 1 ? 's' : ''})
        </div>
        
        {/* Legend */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 20px' }}>
          {amendments.map(a => (
            <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                width: 10,
                height: 10,
                borderRadius: 2,
                backgroundColor: amendmentColors[a.id],
              }} />
              <span style={{
                fontSize: 12,
                color: 'var(--text-secondary)',
                maxWidth: 140,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {a.title}
              </span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Combined View */}
      <div style={{ maxHeight: '500px', overflow: 'auto' }}>
        {baseLines.map((baseLine) => {
          const lineChanges = changesByLine[baseLine.lineNum] || []
          
          return (
            <div
              key={baseLine.lineNum}
              style={{
                borderBottom: '1px solid var(--border-subtle)',
                backgroundColor: lineChanges.length > 0 ? 'rgba(59, 130, 246, 0.02)' : 'transparent',
              }}
            >
              {/* Base line */}
              <div style={{ display: 'flex', padding: '8px 16px' }}>
                <span style={{
                  width: 32,
                  color: 'var(--text-muted)',
                  fontSize: 12,
                  fontFamily: 'var(--font-mono)',
                  flexShrink: 0,
                }}>
                  {baseLine.lineNum}
                </span>
                <span style={{
                  flex: 1,
                  color: lineChanges.length > 0 ? 'var(--text-secondary)' : 'var(--text-primary)',
                  fontStyle: lineChanges.length > 0 ? 'italic' : 'normal',
                }}>
                  {baseLine.text || ' '}
                </span>
              </div>
              
              {/* Changes to this line */}
              {lineChanges.map((change, idx) => (
                <div
                  key={`${change.amendmentId}-${idx}`}
                  style={{
                    display: 'flex',
                    padding: '6px 16px 6px 48px',
                    borderLeft: `3px solid ${change.color}`,
                    marginLeft: 16,
                    backgroundColor: `${change.color}08`,
                  }}
                >
                  <span style={{
                    color: change.color,
                    fontWeight: 600,
                    marginRight: 8,
                    fontSize: 12,
                  }}>
                    +
                  </span>
                  <span style={{
                    flex: 1,
                    backgroundColor: `${change.color}20`,
                    color: change.color,
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontWeight: 500,
                  }}>
                    {change.addedText}
                  </span>
                  <span style={{
                    fontSize: 11,
                    color: change.color,
                    marginLeft: 8,
                    opacity: 0.8,
                  }}>
                    {change.amendmentTitle}
                  </span>
                </div>
              ))}
            </div>
          )
        })}
        
        {/* New lines (beyond original) */}
        {Object.entries(changesByLine)
          .filter(([lineNum]) => parseInt(lineNum) > baseLines.length)
          .map(([lineNum, lineChanges]) => (
            <div
              key={`new-${lineNum}`}
              style={{
                borderBottom: '1px solid var(--border-subtle)',
                backgroundColor: 'rgba(34, 197, 94, 0.03)',
              }}
            >
              {lineChanges.map((change, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    padding: '8px 16px',
                    borderLeft: `3px solid ${change.color}`,
                    marginLeft: 16,
                  }}
                >
                  <span style={{
                    width: 32,
                    color: change.color,
                    fontSize: 12,
                    fontFamily: 'var(--font-mono)',
                    flexShrink: 0,
                  }}>
                    {lineNum}
                  </span>
                  <span style={{
                    flex: 1,
                    backgroundColor: `${change.color}20`,
                    color: change.color,
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontWeight: 500,
                  }}>
                    {change.addedText}
                  </span>
                  <span style={{
                    fontSize: 11,
                    color: change.color,
                    marginLeft: 8,
                  }}>
                    {change.amendmentTitle}
                  </span>
                </div>
              ))}
            </div>
          ))}
      </div>
      
      {/* Footer legend */}
      <div style={{
        padding: '10px 16px',
        backgroundColor: 'var(--panel-2)',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: 12,
        color: 'var(--text-muted)',
        display: 'flex',
        gap: 20,
      }}>
        <span>Base text shown in black</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ padding: '2px 6px', backgroundColor: '#22c55e20', color: '#22c55e', borderRadius: 3, fontWeight: 500 }}>+ text</span>
          Additions by amendment
        </span>
      </div>
    </div>
  )
}
