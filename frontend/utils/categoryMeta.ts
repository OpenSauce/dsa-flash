export const CATEGORY_META: Record<string, { emoji: string; description: string; section: string }> = {
  'data-structures': { emoji: '📦', description: 'Arrays, stacks, trees, and more.', section: 'Coding' },
  'algorithms': { emoji: '⚙️', description: 'Sorting, searching, traversal...', section: 'Coding' },
  'advanced-data-structures': { emoji: '🚀', description: 'Fenwick trees, tries, unions...', section: 'Coding' },
  'big-o-notation': { emoji: '🧠', description: 'Complexity analysis essentials.', section: 'Coding' },
  'dynamic-programming': { emoji: '🧩', description: 'Memoization, tabulation, classic problems...', section: 'Coding' },
  'system-design': { emoji: '🏗️', description: 'Load balancing, caching, scaling...', section: 'System Design' },
  'aws': { emoji: '☁️', description: 'EC2, S3, Lambda, VPC, and more.', section: 'System Design' },
  'kubernetes': { emoji: '☸️', description: 'Pods, Deployments, Services, networking...', section: 'System Design' },
  'docker': { emoji: '🐳', description: 'Containers, images, Dockerfiles, networking, volumes...', section: 'Infrastructure' },
  'linux': { emoji: '🐧', description: 'Processes, permissions, filesystem, shell commands...', section: 'Infrastructure' },
  'networking': { emoji: '🌐', description: 'TCP/IP, DNS, TLS, HTTP, proxies...', section: 'System Design' },
}

export const DEFAULT_META = { emoji: '📘', description: 'Flashcard concepts.', section: 'Other' }

export const SECTION_ORDER = ['Coding', 'System Design', 'Infrastructure', 'Other']

const KNOWN_DISPLAY_NAMES: Record<string, string> = {
  'aws': 'AWS',
  'data-structures': 'Data Structures',
  'algorithms': 'Algorithms',
  'advanced-data-structures': 'Advanced Data Structures',
  'big-o-notation': 'Big O Notation',
  'system-design': 'System Design',
  'kubernetes': 'Kubernetes',
  'docker': 'Docker',
  'linux': 'Linux',
  'networking': 'Networking',
  'dynamic-programming': 'Dynamic Programming',
}

export function getCategoryDisplayName(slug: string): string {
  if (slug in KNOWN_DISPLAY_NAMES) return KNOWN_DISPLAY_NAMES[slug]
  return slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
