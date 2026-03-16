const QR_VERSION = 5
const QR_SIZE = 37 // Version 5
const DATA_CODEWORDS = 108 // Version 5-L
const ECC_CODEWORDS = 26 // Version 5-L
const FORMAT_L_MASK_0 = 0b111011111000100

type Matrix = Array<Array<boolean | null>>

function gfMultiply(a: number, b: number): number {
  let x = a
  let y = b
  let result = 0
  while (y > 0) {
    if (y & 1) result ^= x
    y >>= 1
    x <<= 1
    if (x & 0x100) x ^= 0x11d
  }
  return result
}

function gfPow2(exp: number): number {
  let result = 1
  for (let i = 0; i < exp; i += 1) result = gfMultiply(result, 2)
  return result
}

function rsGeneratorPoly(degree: number): number[] {
  let poly = [1]
  for (let i = 0; i < degree; i += 1) {
    const next = new Array(poly.length + 1).fill(0)
    const factor = gfPow2(i)
    for (let j = 0; j < poly.length; j += 1) {
      next[j] ^= gfMultiply(poly[j], 1)
      next[j + 1] ^= gfMultiply(poly[j], factor)
    }
    poly = next
  }
  return poly
}

function rsComputeRemainder(data: number[], degree: number): number[] {
  const gen = rsGeneratorPoly(degree)
  const result = new Array(degree).fill(0)
  for (const byte of data) {
    const factor = byte ^ result[0]
    for (let i = 0; i < degree - 1; i += 1) {
      result[i] = result[i + 1] ^ gfMultiply(gen[i + 1], factor)
    }
    result[degree - 1] = gfMultiply(gen[degree], factor)
  }
  return result
}

function createEmptyMatrix(): { modules: Matrix; reserved: boolean[][] } {
  const modules: Matrix = Array.from({ length: QR_SIZE }, () => Array.from({ length: QR_SIZE }, () => null))
  const reserved: boolean[][] = Array.from({ length: QR_SIZE }, () => Array.from({ length: QR_SIZE }, () => false))
  return { modules, reserved }
}

function setModule(modules: Matrix, reserved: boolean[][], x: number, y: number, value: boolean, isReserved = true) {
  if (x < 0 || y < 0 || x >= QR_SIZE || y >= QR_SIZE) return
  modules[y][x] = value
  if (isReserved) reserved[y][x] = true
}

function placeFinder(modules: Matrix, reserved: boolean[][], x: number, y: number) {
  for (let dy = -1; dy <= 7; dy += 1) {
    for (let dx = -1; dx <= 7; dx += 1) {
      const xx = x + dx
      const yy = y + dy
      if (dx === -1 || dx === 7 || dy === -1 || dy === 7) {
        setModule(modules, reserved, xx, yy, false)
      } else {
        const isBorder = dx === 0 || dx === 6 || dy === 0 || dy === 6
        const isCenter = dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4
        setModule(modules, reserved, xx, yy, isBorder || isCenter)
      }
    }
  }
}

function placeAlignment(modules: Matrix, reserved: boolean[][], centerX: number, centerY: number) {
  for (let dy = -2; dy <= 2; dy += 1) {
    for (let dx = -2; dx <= 2; dx += 1) {
      const dist = Math.max(Math.abs(dx), Math.abs(dy))
      setModule(modules, reserved, centerX + dx, centerY + dy, dist !== 1)
    }
  }
}

function placePatterns(modules: Matrix, reserved: boolean[][]) {
  placeFinder(modules, reserved, 0, 0)
  placeFinder(modules, reserved, QR_SIZE - 7, 0)
  placeFinder(modules, reserved, 0, QR_SIZE - 7)
  placeAlignment(modules, reserved, QR_SIZE - 7, QR_SIZE - 7)

  for (let i = 8; i <= QR_SIZE - 9; i += 1) {
    setModule(modules, reserved, i, 6, i % 2 === 0)
    setModule(modules, reserved, 6, i, i % 2 === 0)
  }

  setModule(modules, reserved, 8, 4 * QR_VERSION + 9, true)

  for (let i = 0; i < 8; i += 1) {
    if (i !== 6) {
      reserved[8][i] = true
      reserved[i][8] = true
    }
  }
  for (let i = QR_SIZE - 8; i < QR_SIZE; i += 1) {
    reserved[8][i] = true
    reserved[i][8] = true
  }
  reserved[8][8] = true
}

function encodeData(payload: string): number[] {
  const bytes = Array.from(new TextEncoder().encode(payload))
  const maxPayloadBytes = DATA_CODEWORDS - 2
  if (bytes.length > maxPayloadBytes) {
    throw new Error('Payment request too long for local QR payload. Shorten memo and try again.')
  }
  const bits: number[] = []
  const pushBits = (value: number, count: number) => {
    for (let i = count - 1; i >= 0; i -= 1) bits.push((value >>> i) & 1)
  }

  pushBits(0b0100, 4) // byte mode
  pushBits(bytes.length, 8)
  for (const b of bytes) pushBits(b, 8)
  pushBits(0, Math.min(4, DATA_CODEWORDS * 8 - bits.length))
  while (bits.length % 8 !== 0) bits.push(0)

  const data: number[] = []
  for (let i = 0; i < bits.length; i += 8) {
    let byte = 0
    for (let j = 0; j < 8; j += 1) byte = (byte << 1) | bits[i + j]
    data.push(byte)
  }

  const pads = [0xec, 0x11]
  let padIndex = 0
  while (data.length < DATA_CODEWORDS) {
    data.push(pads[padIndex % 2])
    padIndex += 1
  }
  return data
}

function placeData(modules: Matrix, reserved: boolean[][], codewords: number[]) {
  const bits: number[] = []
  for (const codeword of codewords) {
    for (let i = 7; i >= 0; i -= 1) bits.push((codeword >>> i) & 1)
  }

  let bitIndex = 0
  let upward = true
  for (let x = QR_SIZE - 1; x >= 1; x -= 2) {
    if (x === 6) x -= 1
    for (let offset = 0; offset < QR_SIZE; offset += 1) {
      const y = upward ? QR_SIZE - 1 - offset : offset
      for (let xx = x; xx >= x - 1; xx -= 1) {
        if (reserved[y][xx]) continue
        const bit = bitIndex < bits.length ? bits[bitIndex] : 0
        const masked = ((y + xx) % 2 === 0) ? bit ^ 1 : bit // mask 0
        modules[y][xx] = masked === 1
        bitIndex += 1
      }
    }
    upward = !upward
  }
}

function placeFormatInfo(modules: Matrix) {
  const bits = Array.from({ length: 15 }, (_, i) => ((FORMAT_L_MASK_0 >>> (14 - i)) & 1) === 1)
  const a = [
    [8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8],
    [7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8],
  ] as const
  const b = [
    [QR_SIZE - 1, 8], [QR_SIZE - 2, 8], [QR_SIZE - 3, 8], [QR_SIZE - 4, 8], [QR_SIZE - 5, 8], [QR_SIZE - 6, 8], [QR_SIZE - 7, 8],
    [8, QR_SIZE - 8], [8, QR_SIZE - 7], [8, QR_SIZE - 6], [8, QR_SIZE - 5], [8, QR_SIZE - 4], [8, QR_SIZE - 3], [8, QR_SIZE - 2], [8, QR_SIZE - 1],
  ] as const
  for (let i = 0; i < 15; i += 1) {
    const [ax, ay] = a[i]
    const [bx, by] = b[i]
    modules[ay][ax] = bits[i]
    modules[by][bx] = bits[i]
  }
}

export function createQrSvg(payload: string, moduleSize = 8, margin = 4): string {
  const data = encodeData(payload)
  const ecc = rsComputeRemainder(data, ECC_CODEWORDS)
  const codewords = [...data, ...ecc]
  const { modules, reserved } = createEmptyMatrix()
  placePatterns(modules, reserved)
  placeData(modules, reserved, codewords)
  placeFormatInfo(modules)

  const size = (QR_SIZE + margin * 2) * moduleSize
  const rects: string[] = []
  for (let y = 0; y < QR_SIZE; y += 1) {
    for (let x = 0; x < QR_SIZE; x += 1) {
      if (!modules[y][x]) continue
      rects.push(
        `<rect x="${(x + margin) * moduleSize}" y="${(y + margin) * moduleSize}" width="${moduleSize}" height="${moduleSize}" />`,
      )
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="QR code"><rect width="${size}" height="${size}" fill="#fff"/><g fill="#000">${rects.join('')}</g></svg>`
}
