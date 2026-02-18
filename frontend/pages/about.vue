<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-4xl font-tektur font-bold mb-6">About DSA Flash</h1>

    <section class="mb-8">
      <h2 class="text-2xl font-tektur font-bold mb-3">What it is</h2>
      <p class="text-gray-700 leading-relaxed mb-4">
        DSA Flash is a spaced repetition flashcard app for engineers. It covers the technical
        concepts that come up in interviews, system design discussions, code reviews, and
        on-call rotations — not just data structures and algorithms, but the full stack of
        knowledge a working engineer needs to recall quickly.
      </p>
      <p class="text-gray-700 leading-relaxed">
        The goal is retention, not exposure. You can read about how a B-tree works and forget
        it by next week. DSA Flash schedules reviews at precisely the right intervals so the
        knowledge sticks long-term with the minimum amount of time spent reviewing.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-2xl font-tektur font-bold mb-3">Who it's for</h2>
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
      <h2 class="text-2xl font-tektur font-bold mb-3">How spaced repetition works</h2>
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
        a concept once a week for a month beats cramming it for an hour, and DSA Flash
        automates that scheduling for you.
      </p>
      <p class="text-gray-700 leading-relaxed">
        Active recall — the act of retrieving an answer from memory before flipping the card —
        is more effective than passive re-reading. Seeing a concept explained is easy; forcing
        yourself to recall it first is what builds durable memory.
      </p>
    </section>

    <section class="mb-8">
      <h2 class="text-2xl font-tektur font-bold mb-3">What's covered</h2>
      <p class="text-gray-700 leading-relaxed mb-4">
        The current library spans nine topic areas:
      </p>
      <ul class="list-disc list-inside space-y-1 text-gray-700 mb-4">
        <li><strong>Data structures</strong> — arrays, hash maps, trees, heaps, linked lists, stacks, queues</li>
        <li><strong>Algorithms</strong> — sorting, searching, graph traversal, dynamic programming</li>
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

    <div class="mt-10">
      <NuxtLink
        to="/"
        class="inline-block bg-indigo-600 text-white font-semibold px-6 py-3 rounded-lg hover:bg-indigo-700 transition-colors"
      >
        Start studying
      </NuxtLink>
    </div>
  </div>
</template>
