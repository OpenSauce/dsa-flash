export const CATEGORY_META: Record<string, { emoji: string; description: string; section: string; displayName?: string }> = {
  'data-structures': { emoji: '📦', description: 'Arrays, stacks, trees, and more.', section: 'Coding' },
  'algorithms': { emoji: '⚙️', description: 'Sorting, searching, traversal...', section: 'Coding' },
  'advanced-data-structures': { emoji: '🚀', description: 'Fenwick trees, tries, unions...', section: 'Coding' },
  'big-o-notation': { emoji: '🧠', description: 'Complexity analysis essentials.', section: 'Coding' },
  'dynamic-programming': { emoji: '🧩', description: 'Memoization, tabulation, classic problems...', section: 'Coding' },
  'system-design': { emoji: '🏗️', description: 'Load balancing, caching, scaling...', section: 'System Design' },
  'aws': { emoji: '☁️', description: 'EC2, S3, Lambda, VPC, and more.', section: 'System Design', displayName: 'AWS' },
  'kubernetes': { emoji: '☸️', description: 'Pods, Deployments, Services, networking...', section: 'System Design' },
  'docker': { emoji: '🐳', description: 'Containers, images, Dockerfiles, networking, volumes...', section: 'Infrastructure' },
  'linux': { emoji: '🐧', description: 'Processes, permissions, filesystem, shell commands...', section: 'Infrastructure' },
  'networking': { emoji: '🌐', description: 'TCP/IP, DNS, TLS, HTTP, proxies...', section: 'System Design' },
}

export const DEFAULT_META = { emoji: '📘', description: 'Flashcard concepts.', section: 'Other' }

export const SECTION_ORDER = ['Coding', 'System Design', 'Infrastructure', 'Other']

export function getCategoryDisplayName(slug: string): string {
  const meta = CATEGORY_META[slug]
  if (meta?.displayName) return meta.displayName
  return slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
