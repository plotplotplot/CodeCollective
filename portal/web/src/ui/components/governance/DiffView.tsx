import React, { useState, useMemo } from 'react'

interface DiffViewProps {
  original: string
  proposed: string
  showUnchanged?: boolean
}

type DiffSegment = {
  type: 'unchanged' | 'added' | 'removed'
  text: string
}

/**
 * Compute word-level diff between two strings using Myers' algorithm
 */
function diffWords(oldStr: string, newStr: string): DiffSegment[] {
  // Split into words and whitespace
  const tokenize = (s: string): string[] => {
    const tokens: string[] = []
    let current = ''
    for (const char of s) {
      if (/\s/.test(char)) {
        if (current) {
          tokens.push(current)
          current = ''
        }
        tokens.push(char)
      } else {
        current += char
      }
    }
    if (current) tokens.push(current)
    return tokens
  }
  
  const oldTokens = tokenize(oldStr)
  const newTokens = tokenize(newStr)
  
  if (oldTokens.length === 0 && newTokens.length === 0) return []
  if (oldTokens.length === 0) return [{ type: 'added', text: newStr }]
  if (newTokens.length === 0) return [{ type: 'removed', text: oldStr }]
  
  // Myers' diff on tokens
  const n = oldTokens.length
  const m = newTokens.length
  const max = n + m
  
  const v: Record<number, number> = { 1: 0 }
  const trace: Record<number, Record<number, number>>[] = []
  
  let found = false
  
  for (let d = 0; d <= max && !found; d++) {
    trace.push({ ...v })
    
    for (let k = -d; k <= d; k += 2) {
      let x: number
      
      if (k === -d || (k !== d && v[k - 1] < v[k + 1])) {
        x = v[k + 1]
      } else {
        x = v[k - 1] + 1
      }
      
      let y = x - k
      
      while (x < n && y < m && oldTokens[x] === newTokens[y]) {
        x++
        y++
      }
      
      v[k] = x
      
      if (x >= n && y >= m) {
        found = true
        break
      }
    }
  }
  
  // Backtrack
  const result: DiffSegment[] = []
  let x = n
  let y = m
  
  for (let d = trace.length - 1; d >= 0 && (x > 0 || y > 0); d--) {
    const v = trace[d]
    const k = x - y
    
    let prevK: number
    if (k === -d || (k !== d && v[k - 1] < v[k + 1])) {
      prevK = k + 1
    } else {
      prevK = k - 1
    }
    
    const prevX = v[prevK] || 0
    const prevY = prevX - prevK
    
    // Diagonal (unchanged)
    while (x > prevX && y > prevY) {
      x--
      y--
      const text = oldTokens[x]
      if (result.length > 0 && result[0].type === 'unchanged') {
        result[0].text = text + result[0].text
      } else {
        result.unshift({ type: 'unchanged', text })
      }
    }
    
    // Edit
    if (d > 0) {
      if (x === prevX && y > prevY) {
        // Insertion
        y--
        const text = newTokens[y]
        if (result.length > 0 && result[0].type === 'added') {
          result[0].text = text + result[0].text
        } else {
          result.unshift({ type: 'added', text })
        }
      } else if (y === prevY && x > prevX) {
        // Deletion
        x--
        const text = oldTokens[x]
        if (result.length > 0 && result[0].type === 'removed') {
          result[0].text = text + result[0].text
        } else {
          result.unshift({ type: 'removed', text })
        }
      }
    }
  }
  
  return result
}

/**
 * Split text into paragraphs/lines for display
 */
function splitIntoLines(text: string): string[] {
  return text.split('\n')
}

interface LineDiff {
  oldLineNum: number | null
  newLineNum: number | null
  segments: DiffSegment[]
  hasChanges: boolean
}

/**
 * Compute line-by-line diff with word-level granularity
 */
function computeLineDiff(original: string, proposed: string): LineDiff[] {
  const oldLines = splitIntoLines(original)
  const newLines = splitIntoLines(proposed)
  
  // Simple approach: compare line by line
  const maxLines = Math.max(oldLines.length, newLines.length)
  const result: LineDiff[] = []
  
  let oldIdx = 0
  let newIdx = 0
  
  while (oldIdx < oldLines.length || newIdx < newLines.length) {
    const oldLine = oldLines[oldIdx] ?? ''
    const newLine = newLines[newIdx] ?? ''
    
    // Check if lines are identical
    if (oldLine === newLine && oldIdx < oldLines.length && newIdx < newLines.length) {
      result.push({
        oldLineNum: oldIdx + 1,
        newLineNum: newIdx + 1,
        segments: [{ type: 'unchanged', text: oldLine }],
        hasChanges: false,
      })
      oldIdx++
      newIdx++
    } else {
      // Lines differ - do word-level diff
      // Check if this might be a line that was modified vs added/removed
      const lookAhead = 2
      let foundMatch = false
      
      // Look ahead in new lines to see if this old line appears later
      for (let i = 0; i < lookAhead && newIdx + i < newLines.length && !foundMatch; i++) {
        if (oldLine === newLines[newIdx + i]) {
          // Old line exists later in new - lines before it were added
          for (let j = 0; j < i; j++) {
            const segments = diffWords('', newLines[newIdx + j])
            result.push({
              oldLineNum: null,
              newLineNum: newIdx + j + 1,
              segments,
              hasChanges: true,
            })
          }
          // Now the matching line
          result.push({
            oldLineNum: oldIdx + 1,
            newLineNum: newIdx + i + 1,
            segments: [{ type: 'unchanged', text: oldLine }],
            hasChanges: false,
          })
          newIdx += i + 1
          oldIdx++
          foundMatch = true
        }
      }
      
      if (!foundMatch) {
        // Look ahead in old lines to see if this new line appeared before
        for (let i = 0; i < lookAhead && oldIdx + i < oldLines.length && !foundMatch; i++) {
          if (newLine === oldLines[oldIdx + i]) {
            // New line existed earlier in old - lines before were removed
            for (let j = 0; j < i; j++) {
              const segments = diffWords(oldLines[oldIdx + j], '')
              result.push({
                oldLineNum: oldIdx + j + 1,
                newLineNum: null,
                segments,
                hasChanges: true,
              })
            }
            // Now the matching line
            result.push({
              oldLineNum: oldIdx + i + 1,
              newLineNum: newIdx + 1,
              segments: [{ type: 'unchanged', text: newLine }],
              hasChanges: false,
            })
            oldIdx += i + 1
            newIdx++
            foundMatch = true
          }
        }
      }
      
      if (!foundMatch) {
        // Lines are different - do word-level diff
        const segments = diffWords(oldLine, newLine)
        const hasChanges = segments.some(s => s.type !== 'unchanged')
        
        if (hasChanges || oldIdx < oldLines.length || newIdx < newLines.length) {
          result.push({
            oldLineNum: oldIdx < oldLines.length ? oldIdx + 1 : null,
            newLineNum: newIdx < newLines.length ? newIdx + 1 : null,
            segments,
            hasChanges,
          })
        }
        
        if (oldIdx < oldLines.length) oldIdx++
        if (newIdx < newLines.length) newIdx++
      }
    }
  }
  
  return result
}

export function DiffView({ original, proposed, showUnchanged = true }: DiffViewProps) {
  const lineDiffs = useMemo(() => computeLineDiff(original, proposed), [original, proposed])
  
  const hasChanges = lineDiffs.some(line => line.hasChanges)
  
  if (!hasChanges) {
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
        No changes proposed
      </div>
    )
  }
  
  // Filter lines if not showing unchanged
  const displayLines = showUnchanged 
    ? lineDiffs 
    : lineDiffs.filter(line => line.hasChanges)
  
  return (
    <div style={{
      fontFamily: 'var(--font-mono, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace)',
      fontSize: 13,
      lineHeight: 1.6,
      borderRadius: 'var(--radius-md)',
      border: '1px solid var(--border-subtle)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        backgroundColor: 'var(--panel-2)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '8px 12px',
        fontSize: 12,
        fontWeight: 600,
        color: 'var(--text-secondary)',
      }}>
        <span>Original</span>
        <span>Proposed</span>
      </div>
      
      {/* Diff content */}
      <div style={{ maxHeight: '500px', overflow: 'auto' }}>
        {displayLines.map((line, idx) => {
          const isUnchanged = !line.hasChanges
          
          return (
            <div
              key={idx}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                backgroundColor: isUnchanged 
                  ? 'transparent'
                  : 'rgba(59, 130, 246, 0.03)',
              }}
            >
              {/* Left side - Original */}
              <div style={{
                display: 'flex',
                padding: '4px 0',
                borderRight: '1px solid var(--border-subtle)',
                minHeight: '28px',
              }}>
                <span style={{
                  width: '36px',
                  textAlign: 'right',
                  paddingRight: '10px',
                  color: line.oldLineNum ? 'var(--text-muted)' : 'transparent',
                  userSelect: 'none',
                  fontSize: 11,
                }}>
                  {line.oldLineNum ?? ''}
                </span>
                <span style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  paddingRight: '12px',
                }}>
                  {line.segments.map((seg, sidx) => (
                    <span
                      key={sidx}
                      style={{
                        backgroundColor: seg.type === 'removed' 
                          ? 'rgba(239, 68, 68, 0.2)' 
                          : 'transparent',
                        color: seg.type === 'removed' 
                          ? 'var(--accent-red)' 
                          : seg.type === 'unchanged' 
                            ? 'var(--text-primary)'
                            : 'var(--text-muted)',
                        textDecoration: seg.type === 'added' ? 'line-through' : 'none',
                        opacity: seg.type === 'added' ? 0.4 : 1,
                      }}
                    >
                      {seg.text}
                    </span>
                  ))}
                </span>
              </div>
              
              {/* Right side - Proposed */}
              <div style={{
                display: 'flex',
                padding: '4px 0',
                minHeight: '28px',
              }}>
                <span style={{
                  width: '36px',
                  textAlign: 'right',
                  paddingRight: '10px',
                  color: line.newLineNum ? 'var(--text-muted)' : 'transparent',
                  userSelect: 'none',
                  fontSize: 11,
                }}>
                  {line.newLineNum ?? ''}
                </span>
                <span style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  paddingRight: '12px',
                }}>
                  {line.segments.map((seg, sidx) => (
                    <span
                      key={sidx}
                      style={{
                        backgroundColor: seg.type === 'added' 
                          ? 'rgba(34, 197, 94, 0.2)' 
                          : 'transparent',
                        color: seg.type === 'added' 
                          ? 'var(--accent-green)' 
                          : seg.type === 'unchanged' 
                            ? 'var(--text-primary)'
                            : 'var(--text-muted)',
                        textDecoration: seg.type === 'removed' ? 'line-through' : 'none',
                        opacity: seg.type === 'removed' ? 0.4 : 1,
                      }}
                    >
                      {seg.text}
                    </span>
                  ))}
                </span>
              </div>
            </div>
          )
        })}
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
          <span style={{ 
            padding: '0 4px',
            backgroundColor: 'rgba(34, 197, 94, 0.2)',
            color: 'var(--accent-green)',
            borderRadius: 2,
            fontSize: 10,
          }}>
            added
          </span>
          Added
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ 
            padding: '0 4px',
            backgroundColor: 'rgba(239, 68, 68, 0.2)',
            color: 'var(--accent-red)',
            borderRadius: 2,
            fontSize: 10,
          }}>
            removed
          </span>
          Removed
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ 
            padding: '0 4px',
            textDecoration: 'line-through',
            opacity: 0.4,
            borderRadius: 2,
            fontSize: 10,
          }}>
            strikethrough
          </span>
          Not present
        </span>
      </div>
    </div>
  )
}

/**
 * Simplified inline diff stats for compact displays
 */
export function InlineDiff({ original, proposed }: { original: string; proposed: string }) {
  const lineDiffs = useMemo(() => computeLineDiff(original, proposed), [original, proposed])
  
  // Count actual changes
  let addedCount = 0
  let removedCount = 0
  
  lineDiffs.forEach(line => {
    line.segments.forEach(seg => {
      if (seg.type === 'added') {
        // Count words in added segments
        addedCount += seg.text.trim().split(/\s+/).filter(w => w).length
      } else if (seg.type === 'removed') {
        removedCount += seg.text.trim().split(/\s+/).filter(w => w).length
      }
    })
  })
  
  return (
    <div style={{
      display: 'flex',
      gap: '12px',
      fontSize: 12,
      fontWeight: 500,
    }}>
      {addedCount > 0 && (
        <span style={{ color: 'var(--accent-green)' }}>
          +{addedCount} words
        </span>
      )}
      {removedCount > 0 && (
        <span style={{ color: 'var(--accent-red)' }}>
          -{removedCount} words
        </span>
      )}
      {!addedCount && !removedCount && (
        <span style={{ color: 'var(--text-muted)' }}>
          no changes
        </span>
      )}
    </div>
  )
}
