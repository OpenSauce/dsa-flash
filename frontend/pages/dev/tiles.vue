<script setup lang="ts">
interface MockCategory {
  slug: string
  name: string
  emoji: string
  description: string
  total: number
  mastery_pct: number | null
  mastered: number | null
  learned: number | null
  due: number | null
}

const masteryLevels = [0, 25, 50, 75, 100]

const mockCats: MockCategory[] = masteryLevels.map(pct => ({
  slug: `cat-${pct}`,
  name: `Category ${pct}%`,
  emoji: '🏗️',
  description: 'Load balancing, caching, scaling...',
  total: 24,
  mastery_pct: pct,
  mastered: Math.round(24 * pct / 100),
  learned: Math.round(24 * (pct + 10) / 100),
  due: 3,
}))

const anonCat: MockCategory = {
  slug: 'cat-anon',
  name: 'System Design',
  emoji: '🏗️',
  description: 'Load balancing, caching, scaling...',
  total: 24,
  mastery_pct: null,
  mastered: null,
  learned: null,
  due: null,
}

const allCats = [...mockCats, anonCat]

function colorForPct(pct: number): string {
  if (pct === 0) return '#d1d5db'
  if (pct === 100) return '#f59e0b'
  if (pct >= 50) return '#22c55e'
  return '#6366f1'
}
</script>

<template>
  <div class="max-w-5xl mx-auto px-6 py-8 space-y-16">
    <h1 class="text-3xl font-bold text-gray-900">Category tile layout preview</h1>
    <p class="text-gray-500 -mt-12">Dev only. Each section shows 0%, 25%, 50%, 75%, 100% mastery + one anon tile.</p>

    <!-- Option A: Ring replaces emoji (ring left, text right) -->
    <section>
      <h2 class="text-xl font-semibold text-gray-700 mb-4">Option A — ring replaces emoji (ring left, text right)</h2>
      <div class="grid sm:grid-cols-2 gap-6">
        <div v-for="cat in allCats" :key="cat.slug"
          class="border p-6 rounded-xl shadow">
          <div class="flex items-center gap-4">
            <div class="flex-shrink-0">
              <template v-if="cat.mastery_pct !== null">
                <svg viewBox="0 0 36 36" class="w-14 h-14">
                  <circle cx="18" cy="18" r="15.9155" fill="none" stroke="#e5e7eb" stroke-width="3" />
                  <circle
                    cx="18" cy="18" r="15.9155" fill="none"
                    :stroke="colorForPct(cat.mastery_pct)"
                    stroke-width="3"
                    stroke-dasharray="100"
                    :stroke-dashoffset="100 - cat.mastery_pct"
                    stroke-linecap="round"
                    transform="rotate(-90 18 18)"
                  />
                  <text v-if="cat.mastery_pct === 100" x="18" y="22" text-anchor="middle" font-size="12" fill="#f59e0b">&#10003;</text>
                  <text v-else x="18" y="21" text-anchor="middle" font-size="8" fill="#374151" font-weight="600">
                    {{ cat.mastery_pct }}%
                  </text>
                </svg>
              </template>
              <div v-else class="text-3xl">{{ cat.emoji }}</div>
            </div>
            <div class="min-w-0">
              <h2 class="text-xl font-semibold">{{ cat.name }}</h2>
              <p class="text-gray-500 text-sm">{{ cat.description }}</p>
              <p v-if="cat.mastery_pct !== null" class="text-sm text-gray-600 mt-1">
                <span class="font-medium">{{ cat.mastered }}</span> of {{ cat.total }} mastered
                &nbsp;&middot;&nbsp;
                <span class="font-medium">{{ cat.learned }}</span> learned
                &nbsp;&middot;&nbsp;
                <span class="font-medium">{{ cat.due }}</span> due
              </p>
              <p v-else class="text-sm text-gray-600 mt-1">
                <span class="font-medium">{{ cat.total }}</span> concepts
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Option B: Emoji top-left, ring top-right (CURRENT CHOICE) -->
    <section>
      <h2 class="text-xl font-semibold text-gray-700 mb-4">Option B — emoji top-left, ring top-right (current choice)</h2>
      <div class="grid sm:grid-cols-2 gap-6">
        <div v-for="cat in allCats" :key="cat.slug"
          class="border p-6 rounded-xl shadow">
          <div class="flex items-start justify-between">
            <div class="text-3xl mb-2">{{ cat.emoji }}</div>
            <div v-if="cat.mastery_pct !== null" class="flex-shrink-0">
              <svg viewBox="0 0 36 36" class="w-14 h-14">
                <circle cx="18" cy="18" r="15.9155" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle
                  cx="18" cy="18" r="15.9155" fill="none"
                  :stroke="colorForPct(cat.mastery_pct)"
                  stroke-width="3"
                  stroke-dasharray="100"
                  :stroke-dashoffset="100 - cat.mastery_pct"
                  stroke-linecap="round"
                  transform="rotate(-90 18 18)"
                />
                <text v-if="cat.mastery_pct === 100" x="18" y="22" text-anchor="middle" font-size="12" fill="#f59e0b">&#10003;</text>
                <text v-else x="18" y="21" text-anchor="middle" font-size="8" fill="#374151" font-weight="600">
                  {{ cat.mastery_pct }}%
                </text>
              </svg>
            </div>
          </div>
          <h2 class="text-xl font-semibold">{{ cat.name }}</h2>
          <p class="text-gray-500">{{ cat.description }}</p>
          <p v-if="cat.mastery_pct !== null" class="text-sm text-gray-600 mt-2">
            <span class="font-medium">{{ cat.mastered }}</span> of {{ cat.total }} mastered
            &nbsp;&middot;&nbsp;
            <span class="font-medium">{{ cat.learned }}</span> learned
            &nbsp;&middot;&nbsp;
            <span class="font-medium">{{ cat.due }}</span> due
          </p>
          <p v-else class="text-sm text-gray-600 mt-2">
            <span class="font-medium">{{ cat.total }}</span> concepts
          </p>
        </div>
      </div>
    </section>

    <!-- Option C: Emoji stays, small ring below description -->
    <section>
      <h2 class="text-xl font-semibold text-gray-700 mb-4">Option C — emoji stays, small ring below description</h2>
      <div class="grid sm:grid-cols-2 gap-6">
        <div v-for="cat in allCats" :key="cat.slug"
          class="border p-6 rounded-xl shadow">
          <div class="text-3xl mb-2">{{ cat.emoji }}</div>
          <h2 class="text-xl font-semibold">{{ cat.name }}</h2>
          <p class="text-gray-500">{{ cat.description }}</p>
          <div v-if="cat.mastery_pct !== null" class="flex items-center gap-3 mt-2">
            <svg viewBox="0 0 36 36" class="w-8 h-8 flex-shrink-0">
              <circle cx="18" cy="18" r="15.9155" fill="none" stroke="#e5e7eb" stroke-width="3" />
              <circle
                cx="18" cy="18" r="15.9155" fill="none"
                :stroke="colorForPct(cat.mastery_pct)"
                stroke-width="3"
                stroke-dasharray="100"
                :stroke-dashoffset="100 - cat.mastery_pct"
                stroke-linecap="round"
                transform="rotate(-90 18 18)"
              />
              <text v-if="cat.mastery_pct === 100" x="18" y="22" text-anchor="middle" font-size="12" fill="#f59e0b">&#10003;</text>
              <text v-else x="18" y="21" text-anchor="middle" font-size="8" fill="#374151" font-weight="600">
                {{ cat.mastery_pct }}%
              </text>
            </svg>
            <p class="text-sm text-gray-600">
              <span class="font-medium">{{ cat.mastered }}</span> of {{ cat.total }} mastered
              &nbsp;&middot;&nbsp;
              <span class="font-medium">{{ cat.learned }}</span> learned
              &nbsp;&middot;&nbsp;
              <span class="font-medium">{{ cat.due }}</span> due
            </p>
          </div>
          <p v-else class="text-sm text-gray-600 mt-2">
            <span class="font-medium">{{ cat.total }}</span> concepts
          </p>
        </div>
      </div>
    </section>
  </div>
</template>
