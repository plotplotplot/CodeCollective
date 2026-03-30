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
  showUnchanged?: boolean
}

type DiffSegment = {
  type: 'context' | 'added' | 'removed'
  text: string
  lineNum: number
  amendmentId?: string
  amendmentTitle?: string
}

/**
 * Compute unified diff showing all amendments applied sequentially
 */
function computeUnifiedDiff(
  original: string, 
  amendments: UnifiedDiffProps['amendments']
): DiffSegment[] {
  if (amendments.length === 0) return []
  
  const lines = original.split('\n')
  const result: DiffSegment[] = []
  let currentLineNum = 1
  
  // Track which lines are modified by which amendments
  const lineStates: Array<{
    text: string
    originalLineNum: number
    modifiedBy: string | null
    isDeleted: boolean
  }> = lines.map((text, idx) => ({
    text,
    originalLineNum: idx + 1,
    modifiedBy: null,
    isDeleted: false,
  }))
  
  // Process each amendment
  amendments.forEach((amendment) => {
    const proposedText = amendment.proposedBodyDiff || amendment.body
    const proposedLines = proposedText.split('\n')
    
    // Simple line-by-line comparison to find changes
    // For a more sophisticated approach, we'd use the Myers diff here too
    const maxLines = Math.max(lineStates.length, proposedLines.length)
    
    for (let i = 0; i < maxLines; i++) {
      const currentState = lineStates[i]
      const proposedLine = proposedLines[i]
      
      if (!currentState && proposedLine) {
        // Line added by this amendment
        lineStates.push({
          text: proposedLine,
          originalLineNum: i + 1,
          modifiedBy: amendment.id,
          isDeleted: false,
        })
      } else if (currentState && !proposedLine && !currentState.isDeleted) {
        // Line would be removed - mark it
        // But we keep it for the unified view to show what was removed
      } else if (currentState && proposedLine && currentState.text !== proposedLine) {
        // Line modified
        currentState.text = proposedLine
        currentState.modifiedBy = amendment.id
      }
    }
  })
  
  // Build the unified diff output
  // Show original with deletions and modifications, then additions
  
  // First pass: show original context with deletions (in red)
  lines.forEach((originalText, idx) => {
    const state = lineStates[idx]
    const amendsThatModified = amendments.filter(a => {
      const proposed = (a.proposedBodyDiff || a.body).split('\n')
      return proposed[idx] !== originalText
    })
    
    if (state && state.isDeleted) {
      // Line was deleted
      result.push({
        type: 'removed',
        text: originalText,
        lineNum: idx + 1,
        amendmentId: amendsThatModified[0]?.id,
        amendmentTitle: amendsThatModified[0]?.title,
      })
    } else if (amendsThatModified.length > 0) {
      // Line was modified - show as removal of original
      result.push({
        type: 'removed',
        text: originalText,
        lineNum: idx + 1,
        amendmentId: amendsThatModified[0]?.id,
        amendmentTitle: amendsThatModified[0]?.title,
      })
    } else {
      // Context line (unchanged)
      result.push({
        type: 'context',
        text: originalText,
        lineNum: idx + 1,
      })
    }
  })
  
  // Second pass: show all additions (in green)
  // This is a simplified approach - in reality we'd interleave them properly
  amendments.forEach((amendment) => {
    const proposedLines = (amendment.proposedBodyDiff || amendment.body).split('\n')
    
    proposedLines.forEach((line, idx) => {
      const originalLine = lines[idx]
      
      if (line !== originalLine) {
        // This is a new or modified line
        result.push({
          type: 'added',
          text: line,
          lineNum: idx + 1,
          amendmentId: amendment.id,
          amendmentTitle: amendment.title,
        })
      }
    })
  })
  
  return result
}

/**
 * Word-level diff for inline display
 */
function diffWords(oldStr: string, newStr: string): Array<{ type: 'same' | 'removed' | 'added'; text: string }> {
  const words1 = oldStr.split(/(\s+)/)
  const words2 = newStr.split(/(\s+)/)
  
  // Simple LCS
  const m = words1.length
  const n = words2.length
  const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0))
  
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (words1[i - 1] === words2[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }
  
  // Backtrack
  const result: Array<{ type: 'same' | 'removed' | 'added'; text: string }> = []
  let i = m, j = n
  
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && words1[i - 1] === words2[j - 1]) {
      result.unshift({ type: 'same', text: words1[i - 1] })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift({ type: 'added', text: words2[j - 1] })
      j--
    } else if (i > 0) {
      result.unshift({ type: 'removed', text: words1[i - 1] })
      i--
    }
  }
  
  return result
}

export function UnifiedDiff({ original, amendments, showUnchanged = true }: UnifiedDiffProps) {
  const diff = useMemo(() => {
    // For unified view, we'll show:
    // 1. The original with deletions marked
    // 2. Then all additions grouped by amendment
    
    const originalLines = original.split('\n')
    const result: Array<{
      type: 'header' | 'context' | 'removed' | 'added'
      text: string
      lineNum?: number
      amendmentId?: string
      amendmentTitle?: string
      amendmentColor?: string
    }> = []
    
    // Generate colors for amendments
    const amendmentColors = [
      '#22c55e', // green
      '#3b82f6', // blue  
      '#a855f7', // purple
      '#f59e0b', // amber
      '#ec4899', // pink
      '#14b8a6', // teal
    ]
    
    // Create a map of which amendment modified which line
    const lineModifications: Array<{
      original: string
      modifications: Array<{
        amendmentId: string
        amendmentTitle: string
        proposedText: string
        color: string
      }>
    }> = originalLines.map(text => ({
      original: text,
      modifications: [],
    }))
    
    amendments.forEach((amendment, idx) => {
      const color = amendmentColors[idx % amendmentColors.length]
      const proposedLines = (amendment.proposedBodyDiff || amendment.body).split('\n')
      
      proposedLines.forEach((proposedLine, lineIdx) => {
        if (lineIdx < lineModifications.length) {
          if (lineModifications[lineIdx].original !== proposedLine) {
            lineModifications[lineIdx].modifications.push({
              amendmentId: amendment.id,
              amendmentTitle: amendment.title,
              proposedText: proposedLine,
              color,
            })
          }
        } else {
          // New line added at the end
          if (!lineModifications[lineIdx]) {
            lineModifications[lineIdx] = {
              original: '',
              modifications: [],
            }
          }
          lineModifications[lineIdx].modifications.push({
            amendmentId: amendment.id,
            amendmentTitle: amendment.title,
            proposedText: proposedLine,
            color,
          })
        }
      })
    })
    
    // Build the unified output
    lineModifications.forEach((lineMod, idx) => {
      const lineNum = idx + 1
      
      if (lineMod.modifications.length === 0) {
        // Unchanged line
        if (showUnchanged) {
          result.push({
            type: 'context',
            text: lineMod.original,
            lineNum,
          })
        }
      } else {
        // Line was modified - show the original (removed)
        result.push({
          type: 'removed',
          text: lineMod.original,
          lineNum,
        })
        
        // Show each amendment's version
        lineMod.modifications.forEach((mod) => {
          result.push({
            type: 'added',
            text: mod.proposedText,
            lineNum,
            amendmentId: mod.amendmentId,
            amendmentTitle: mod.amendmentTitle,
            amendmentColor: mod.color,
          })
        })
      }
    })
    
    // Add any completely new lines from amendments
    amendments.forEach((amendment, idx) => {
      const color = amendmentColors[idx % amendmentColors.length]
      const proposedLines = (amendment.proposedBodyDiff || amendment.body).split('\n')
      
      proposedLines.slice(lineModifications.length).forEach((line, offsetIdx) => {
        const lineNum = lineModifications.length + offsetIdx + 1
        result.push({
          type: 'added',
          text: line,
          lineNum,
          amendmentId: amendment.id,
          amendmentTitle: amendment.title,
          amendmentColor: color,
        })
      })
    })
    
    return result
  }, [original, amendments, showUnchanged])
  
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
  
  // Generate legend colors
  const amendmentColors = [
    '#22c55e', '#3b82f6', '#a855f7', '#f59e0b', '#ec4899', '#14b8a6',
  ]
  
  return (
    <div style={{
      fontFamily: 'var(--font-mono, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace)',
      fontSize: 13,
      lineHeight: 1.6,
      borderRadius: 'var(--radius-md)',
      border: '1px solid var(--border-subtle)',
      overflow: 'hidden',
    }}>
      {/* Header with amendment legend */}
      <div style={{
        padding: '12px 16px',
        backgroundColor: 'var(--panel-2)',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: 'var(--text-secondary)',
          marginBottom: 8,
        }}>
          Unified Diff ({amendments.length} amendment{amendments.length !== 1 ? 's' : ''})
        </div>
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px 16px',
        }}>
          {amendments.map((a, idx) => (
            <div 
              key={a.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 11,
              }}
            >
              <span style={{
                width: 10,
                height: 10,
                borderRadius: 2,
                backgroundColor: amendmentColors[idx % amendmentColors.length],
              }} />
              <span style={{
                color: 'var(--text-secondary)',
                maxWidth: 150,
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
      
      {/* Diff content */}
      <div style={{ maxHeight: '600px', overflow: 'auto' }}>
        {diff.map((line, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              minHeight: '24px',
              backgroundColor: line.type === 'removed' 
                ? 'rgba(239, 68, 68, 0.08)'
                : line.type === 'added'
                  ? `${line.amendmentColor}15` // 15 = ~8% opacity in hex
                  : 'transparent',
            }}
          >
            {/* Line number */}
            <span style={{
              width: '45px',
              textAlign: 'right',
              paddingRight: '12px',
              color: line.type === 'context' ? 'var(--text-muted)' : 
                    line.type === 'removed' ? 'var(--accent-red)' :
                    line.amendmentColor,
              userSelect: 'none',
              fontSize: 11,
              paddingTop: '3px',
              borderRight: '1px solid var(--border-subtle)',
              flexShrink: 0,
            }}>
              {line.lineNum ?? ''}
            </span>
            
            {/* Change indicator */}
            <span style={{
              width: '24px',
              textAlign: 'center',
              color: line.type === 'removed' ? 'var(--accent-red)' :
                    line.type === 'added' ? line.amendmentColor :
                    'var(--text-muted)',
              fontWeight: 700,
              fontSize: 12,
              paddingTop: '3px',
              flexShrink: 0,
            }}>
              {line.type === 'removed' ? '-' : 
               line.type === 'added' ? '+' : 
               ' '}
            </span>
            
            {/* Content */}
            <span style={{
              flex: 1,
              color: line.type === 'context' ? 'var(--text-primary)' :
                    line.type === 'removed' ? 'var(--accent-red)' :
                    'var(--text-primary)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              padding: '3px 12px 3px 0',
            }}>
              {line.text || ' '}
            </span>
            
            {/* Amendment indicator for additions */}
            {line.type === 'added' && line.amendmentTitle && (
              <span style={{
                fontSize: 10,
                color: line.amendmentColor,
                padding: '3px 8px',
                backgroundColor: `${line.amendmentColor}20`,
                borderRadius: 'var(--radius-sm)',
                margin: '2px 8px 2px 0',
                whiteSpace: 'nowrap',
                maxWidth: 120,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
                {line.amendmentTitle}
              </span>
            )}
          </div>
        ))}
      </div>
      
      {/* Legend */}
      <div style={{
        display: 'flex',
        gap: '16px',
        padding: '8px 12px',
        backgroundColor: 'var(--panel-2)',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: 11,
        color: 'var(--text-muted)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ color: 'var(--accent-red)', fontWeight: 700 }}>-</span>
          Removed (original)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ color: 'var(--accent-green)', fontWeight: 700 }}>+</span>
          Added by amendment
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: '#22c55e' }} />
          Amendment color
        </span>
      </div>
    </div>
  )
}
