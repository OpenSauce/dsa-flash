<script setup lang="ts">
const props = defineProps<{
  pageType: string
  title: string
}>()

const url = useRequestURL()

const issueUrl = computed(() => {
  const title = encodeURIComponent(`[Content Issue] ${props.pageType}: ${props.title}`)
  const body = encodeURIComponent(`**Page:** ${url.href}\n**What's wrong:**\n\n`)
  return `https://github.com/OpenSauce/dsa-flash/issues/new?title=${title}&body=${body}&labels=content`
})
</script>

<template>
  <a
    :href="issueUrl"
    target="_blank"
    rel="noopener"
    class="inline-flex items-center min-h-[44px] text-[13px] text-gray-400 hover:text-gray-600 transition-colors"
  >
    Spotted a problem?
  </a>
</template>
