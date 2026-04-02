export interface CodingProblemOut {
  id: number
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  category: string
  tags: string[]
  due_status: 'due' | 'review' | 'new' | null
}

export interface ProblemExample {
  input: string
  output: string
  explanation?: string
}

export interface CodingProblemDetailOut {
  id: number
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  category: string
  tags: string[]
  due_status: 'due' | 'review' | 'new' | null
  description: string
  examples: ProblemExample[]
  constraints: string[]
  starter_code: string
  hints_count: number
  created_at: string
  updated_at: string
}

export interface TestResult {
  input: string
  expected: string
  actual: string
  passed: boolean
}

export interface SubmissionOut {
  passed: boolean
  test_results: TestResult[]
  stdout: string
  stderr: string
  status: string
  solve_time_ms: number
}

export interface HintOut {
  hint: string
  total: number
  index: number
}
