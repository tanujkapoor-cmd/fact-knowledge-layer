import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function confidenceLabel(value: number) {
  return `${Math.round(value * 100)}%`
}

export function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  const kilobytes = bytes / 1024
  if (kilobytes < 1024) return `${kilobytes.toFixed(1)} KB`
  return `${(kilobytes / 1024).toFixed(1)} MB`
}

export function downloadJson(fileName: string, value: unknown) {
  const payload = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  )
  const anchor = document.createElement("a")
  anchor.href = payload
  anchor.download = fileName
  anchor.click()
  URL.revokeObjectURL(payload)
}

export function sentenceCase(value: string) {
  return value.replaceAll("_", " ").replace(/^./, (character) => character.toUpperCase())
}
