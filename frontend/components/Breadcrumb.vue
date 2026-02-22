<script setup lang="ts">
interface BreadcrumbItem {
  label: string
  to?: string
  onClick?: () => void
}

defineProps<{
  items: BreadcrumbItem[]
}>()
</script>

<template>
  <nav class="text-sm text-gray-500 mb-6 pt-2">
    <template v-for="(item, idx) in items" :key="idx">
      <span v-if="idx > 0" class="mx-2">/</span>
      <NuxtLink v-if="item.to" :to="item.to" class="hover:text-gray-700">{{ item.label }}</NuxtLink>
      <button v-else-if="item.onClick" class="hover:text-gray-700" @click="item.onClick">{{ item.label }}</button>
      <span v-else class="text-gray-700">{{ item.label }}</span>
    </template>
  </nav>
</template>
