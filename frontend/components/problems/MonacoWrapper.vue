<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps<{
  value: string
  language: string
  readonly: boolean
}>()

const emit = defineEmits<{
  (e: 'mount', editor: any): void
  (e: 'change', value: string): void
}>()

const containerRef = ref<HTMLElement | null>(null)
let editor: any = null
let monaco: any = null

onMounted(async () => {
  const monacoModule = await import('monaco-editor')
  monaco = monacoModule

  // Configure Monaco workers via CDN since bundling workers with Nuxt SSR is problematic
  ;(self as any).MonacoEnvironment = {
    getWorker(_workerId: string, _label: string) {
      return new Worker(
        URL.createObjectURL(
          new Blob(
            ['// no-op worker'],
            { type: 'text/javascript' }
          )
        )
      )
    },
  }

  if (!containerRef.value) return

  editor = monaco.editor.create(containerRef.value, {
    value: props.value,
    language: props.language,
    theme: 'vs-dark',
    readOnly: props.readonly,
    minimap: { enabled: false },
    fontSize: 14,
    fontFamily: '"JetBrains Mono", monospace',
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 4,
    wordWrap: 'on',
    padding: { top: 12, bottom: 12 },
    renderLineHighlight: 'line',
    scrollbar: {
      verticalScrollbarSize: 8,
      horizontalScrollbarSize: 8,
    },
  })

  editor.onDidChangeModelContent(() => {
    const val = editor.getValue()
    emit('change', val)
  })

  emit('mount', editor)
})

watch(() => props.value, (newVal) => {
  if (editor && editor.getValue() !== newVal) {
    editor.setValue(newVal)
  }
})

watch(() => props.language, (newLang) => {
  if (editor && monaco && newLang) {
    const model = editor.getModel()
    if (model) {
      monaco.editor.setModelLanguage(model, newLang)
    }
  }
})

onBeforeUnmount(() => {
  if (editor) {
    editor.dispose()
    editor = null
  }
})
</script>

<template>
  <div ref="containerRef" class="w-full h-full min-h-[300px]" />
</template>
