<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ content: string }>()

function escapeHtml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

function inline(value: string): string {
  return escapeHtml(value).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/\*([^*]+)\*/g, '<em>$1</em>')
}

const html = computed(() => {
  const lines = props.content.replace(/\r\n/g, '\n').split('\n')
  const output: string[] = []
  let listOpen = false
  let tableOpen = false
  const closeList = (): void => { if (listOpen) { output.push('</ul>'); listOpen = false } }
  const closeTable = (): void => { if (tableOpen) { output.push('</tbody></table>'); tableOpen = false } }
  for (const line of lines) {
    const heading = /^(#{1,3})\s+(.+)$/.exec(line)
    const item = /^[-*]\s+(.+)$/.exec(line)
    if (heading) { closeList(); closeTable(); output.push(`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`); continue }
    if (item) { closeTable(); if (!listOpen) { output.push('<ul>'); listOpen = true }; output.push(`<li>${inline(item[1])}</li>`); continue }
    closeList()
    if (/^\|.*\|$/.test(line)) {
      const cells = line.slice(1, -1).split('|').map(cell => cell.trim())
      if (cells.every(cell => /^:?-{3,}:?$/.test(cell))) continue
      if (!tableOpen) { output.push('<table><tbody>'); tableOpen = true }
      output.push(`<tr>${cells.map(cell => `<td>${inline(cell)}</td>`).join('')}</tr>`)
      continue
    }
    closeTable()
    if (/^>\s?/.test(line)) output.push(`<blockquote>${inline(line.replace(/^>\s?/, ''))}</blockquote>`)
    else if (line.trim()) output.push(`<p>${inline(line)}</p>`)
  }
  closeList()
  closeTable()
  return output.join('')
})
</script>

<template><article class="markdown-article" v-html="html" /></template>

<style scoped>
.markdown-article { max-width: 780px; color: var(--ink); font-size: 15px; line-height: 1.9; }.markdown-article :deep(h1),.markdown-article :deep(h2),.markdown-article :deep(h3) { margin: 1.4em 0 .55em; color: var(--ink); line-height: 1.45; }.markdown-article :deep(h1){font-size:1.55em}.markdown-article :deep(h2){font-size:1.28em}.markdown-article :deep(h3){font-size:1.08em}.markdown-article :deep(p){margin:.75em 0}.markdown-article :deep(ul){margin:.75em 0;padding-left:1.4em}.markdown-article :deep(li){margin:.28em 0}.markdown-article :deep(blockquote){margin:1em 0;padding:.55em 1em;color:var(--muted);background:var(--surface-soft);border-left:3px solid var(--primary)}.markdown-article :deep(code){padding:.1em .3em;background:var(--surface-soft);border-radius:3px}.markdown-article :deep(table){width:100%;margin:1em 0;border-collapse:collapse}.markdown-article :deep(td){padding:.45em .65em;border:1px solid var(--line);vertical-align:top}
</style>
