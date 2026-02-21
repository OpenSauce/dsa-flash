<script setup lang="ts">
useSeoMeta({
  title: 'About | dsaflash.cards',
  ogTitle: 'About dsaflash.cards – Spaced Repetition for Engineers',
  description: 'dsaflash.cards is a free spaced repetition flashcard app for engineers. Learn how SM-2 scheduling, active recall, and the spacing effect help you retain technical knowledge.',
  ogDescription: 'dsaflash.cards is a free spaced repetition flashcard app for engineers. Learn how SM-2 scheduling, active recall, and the spacing effect help you retain technical knowledge.',
  ogUrl: 'https://dsaflash.cards/about',
  ogType: 'article',
})

useHead({
  link: [{ rel: 'canonical', href: 'https://dsaflash.cards/about' }],
})
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-4xl font-bold mb-6">About dsaflash.cards</h1>

    <section class="mb-8">
      <h2 class="text-2xl font-bold mb-3">What it is</h2>
      <p class="text-gray-700 leading-relaxed mb-4">
        dsaflash.cards is a spaced repetition flashcard app for engineers. It covers the technical
        concepts that come up in interviews, system design discussions, code reviews, and
        on-call rotations — not just data structures and algorithms, but the full stack of
        knowledge a working engineer needs to recall quickly.
      </p>
      <p class="text-gray-700 leading-relaxed">
        The goal is retention, not exposure. You can read about how a B-tree works and forget
        it by next week. dsaflash.cards schedules reviews at precisely the right intervals so the
        knowledge sticks long-term with the minimum amount of time spent reviewing.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-2xl font-bold mb-3">Who it's for</h2>
      <p class="text-gray-700 leading-relaxed mb-4">
        Engineers preparing for technical interviews — particularly senior and staff-level
        interviews where system design, infrastructure, and breadth of knowledge matter as
        much as algorithmic fluency. Also useful for engineers who want to stay sharp across
        domains they don't touch daily, or who are ramping up in a new area like Kubernetes
        or AWS.
      </p>
      <p class="text-gray-700 leading-relaxed">
        No signup required to start. Browse any category and study cards immediately.
        Create a free account when you want the app to track your progress and schedule
        reviews based on what you know.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-2xl font-bold mb-3">How spaced repetition works</h2>
      <p class="text-gray-700 leading-relaxed mb-4">
        When you review a card, you rate how well you knew the answer: again, almost, or
        got it. The app uses the SM-2 algorithm to schedule the next review based on that
        rating. Cards you know well get pushed out — you might see them again in two weeks,
        then a month, then three months. Cards you struggle with come back sooner, sometimes
        the next day.
      </p>
      <p class="text-gray-700 leading-relaxed mb-4">
        This works because of the spacing effect: information reviewed at increasing intervals
        is retained far longer than information reviewed repeatedly in a short window. Reviewing
        a concept once a week for a month beats cramming it for an hour, and dsaflash.cards
        automates that scheduling for you.
      </p>
      <p class="text-gray-700 leading-relaxed">
        Active recall — the act of retrieving an answer from memory before flipping the card —
        is more effective than passive re-reading. Seeing a concept explained is easy; forcing
        yourself to recall it first is what builds durable memory.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-2xl font-bold mb-3">What's covered</h2>
      <p class="text-gray-700 leading-relaxed mb-4">
        The current library spans eleven topic areas:
      </p>
      <ul class="list-disc list-inside space-y-1 text-gray-700 mb-4">
        <li><strong>Data structures</strong> — arrays, hash maps, trees, heaps, linked lists, stacks, queues</li>
        <li><strong>Algorithms</strong> — sorting, searching, graph traversal</li>
        <li><strong>Dynamic Programming</strong> — memoization, tabulation, classic interview problems</li>
        <li><strong>Big O notation</strong> — time and space complexity analysis</li>
        <li><strong>System design</strong> — load balancing, caching, database scaling, CAP theorem</li>
        <li><strong>AWS</strong> — compute, storage, networking, IAM, messaging, CDN</li>
        <li><strong>Kubernetes</strong> — pods, deployments, services, config, networking, autoscaling</li>
        <li><strong>Docker and Linux</strong> — Dockerfile instructions, volumes, networking, Linux permissions, processes</li>
        <li><strong>Networking</strong> — TCP/IP, DNS, TLS, HTTP, proxies, WebSockets</li>
        <li><strong>Advanced data structures</strong> — tries, segment trees, bloom filters, LRU caches, union-find</li>
      </ul>
      <p class="text-gray-700 leading-relaxed">
        New categories are added based on what engineers actually need to recall. The content
        is written for people who already code — explanations assume familiarity with software
        development and focus on the conceptual distinctions and trade-offs that matter in practice.
      </p>
    </section>

    <div class="mt-10 flex flex-wrap items-center gap-4">
      <NuxtLink
        to="/"
        class="inline-block bg-indigo-600 text-white font-semibold px-6 py-3 rounded-lg hover:bg-indigo-700 transition-colors"
      >
        Start studying
      </NuxtLink>
      <a
        href="https://github.com/OpenSauce/dsa-flash"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
      >
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.726-4.042-1.61-4.042-1.61C4.422 17.07 3.633 16.7 3.633 16.7c-1.087-.744.083-.729.083-.729 1.205.084 1.84 1.236 1.84 1.236 1.07 1.834 2.809 1.304 3.495.997.108-.776.418-1.304.76-1.604-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.47-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23a11.5 11.5 0 013.003-.404c1.02.005 2.045.137 3.003.404 2.285-1.552 3.29-1.23 3.29-1.23.645 1.653.24 2.873.12 3.176.77.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.48 5.92.43.372.81 1.102.81 2.222 0 1.606-.015 2.896-.015 3.286 0 .322.21.694.825.577C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
        </svg>
        View on GitHub
      </a>
    </div>
  </div>
</template>
