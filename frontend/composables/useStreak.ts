export const useStreak = () => {
  const { apiFetch } = useApiFetch()
  const { tokenCookie, isLoggedIn } = useAuth()

  interface StreakData {
    current_streak: number
    longest_streak: number
    today_reviewed: number
  }

  const streak = useState<StreakData | null>('streak', () => null)

  const fetchStreak = async () => {
    if (!isLoggedIn.value || !tokenCookie.value) {
      streak.value = null
      return
    }
    try {
      streak.value = await apiFetch<StreakData>('/users/streak')
    } catch {
      streak.value = null
    }
  }

  const refreshStreak = fetchStreak

  return { streak, fetchStreak, refreshStreak }
}
