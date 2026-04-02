<script setup lang="ts">
import { shallowRef, watch } from 'vue'

const props = defineProps<{
  modelValue: string
  language?: string
  readonly?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'run'): void
  (e: 'submit'): void
}>()

const editorRef = shallowRef<any>(null)

function handleMount(editor: any) {
  editorRef.value = editor

  // Cmd+Enter to submit
  editor.addCommand(
    // Monaco.KeyMod.CtrlCmd | Monaco.KeyCode.Enter = 2048 | 3
    2048 | 3,
    () => emit('submit')
  )

  // Cmd+' to run
  editor.addCommand(
    // Monaco.KeyMod.CtrlCmd | Monaco.KeyCode.Quote = 2048 | 85 (US_QUOTE)
    2048 | 85,
    () => emit('run')
  )
}

function handleChange(value: string | undefined) {
  if (value !== undefined) {
    emit('update:modelValue', value)
  }
}
</script>

<template>
  <ClientOnly>
    <Suspense>
      <LazyProblemsMonacoWrapper
        :value="modelValue"
        :language="language || 'python'"
        :readonly="readonly || false"
        @mount="handleMount"
        @change="handleChange"
      />
    </Suspense>
    <template #fallback>
      <div class="w-full h-full bg-[#1e1e1e] flex items-center justify-center">
        <span class="text-gray-500 text-sm">Loading editor...</span>
      </div>
    </template>
  </ClientOnly>
</template>
