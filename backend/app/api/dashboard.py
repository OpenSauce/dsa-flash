from datetime import datetime, timedelta, timezone
from math import floor

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    MASTERY_INTERVAL_DAYS,
    DashboardDomain,
    DashboardKnowledgeSummary,
    DashboardOut,
    DashboardStreak,
    DashboardWeakCard,
    DashboardWeek,
    Flashcard,
    StudySession,
    User,
    UserFlashcard,
)
from .users import compute_streak, get_current_user

router = APIRouter(tags=["users"])


@router.get("/users/dashboard", response_model=DashboardOut)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = current_user.id

    # 1. Knowledge summary
    learned_count = session.exec(
        select(func.count()).select_from(UserFlashcard).where(UserFlashcard.user_id == uid)
    ).one()

    mastered_count = session.exec(
        select(func.count())
        .select_from(UserFlashcard)
        .where(UserFlashcard.user_id == uid, UserFlashcard.interval > MASTERY_INTERVAL_DAYS)
    ).one()

    domains_explored_count = session.exec(
        select(func.count(func.distinct(Flashcard.category)))
        .select_from(UserFlashcard)
        .join(Flashcard, Flashcard.id == UserFlashcard.flashcard_id)
        .where(UserFlashcard.user_id == uid, Flashcard.category.isnot(None))
    ).one()

    knowledge_summary = DashboardKnowledgeSummary(
        total_concepts_learned=learned_count,
        concepts_mastered=mastered_count,
        domains_explored=domains_explored_count,
    )

    # 2. Per-domain mastery -- all categories with user progress merged in
    category_totals = session.exec(
        select(Flashcard.category, func.count(Flashcard.id).label("total"))
        .where(Flashcard.category.isnot(None))
        .group_by(Flashcard.category)
    ).all()

    user_progress = session.exec(
        select(
            Flashcard.category,
            func.count(UserFlashcard.flashcard_id).label("learned"),
            func.sum(
                case((UserFlashcard.interval > MASTERY_INTERVAL_DAYS, 1), else_=0)
            ).label("mastered"),
        )
        .select_from(UserFlashcard)
        .join(Flashcard, Flashcard.id == UserFlashcard.flashcard_id)
        .where(UserFlashcard.user_id == uid, Flashcard.category.isnot(None))
        .group_by(Flashcard.category)
    ).all()

    progress_by_slug: dict[str, tuple[int, int]] = {
        row.category: (row.learned, int(row.mastered or 0)) for row in user_progress
    }

    domains: list[DashboardDomain] = []
    for row in category_totals:
        slug = row.category
        total = row.total
        learned, mastered = progress_by_slug.get(slug, (0, 0))
        mastery_pct = floor(mastered / total * 100) if total > 0 else 0
        learned_pct = floor(learned / total * 100) if total > 0 else 0
        name = slug.replace("-", " ").title()
        domains.append(
            DashboardDomain(
                name=name,
                slug=slug,
                total=total,
                learned=learned,
                mastered=mastered,
                mastery_pct=mastery_pct,
                learned_pct=learned_pct,
            )
        )

    # 3. Streak
    streak_out = compute_streak(session, uid)
    streak = DashboardStreak(
        current=streak_out.current_streak,
        longest=streak_out.longest_streak,
        today_reviewed=streak_out.today_reviewed,
    )

    # 4. This week (ISO week, Monday start)
    today = datetime.now(timezone.utc).date()
    week_start_date = today - timedelta(days=today.weekday())
    week_start_dt = datetime(
        week_start_date.year, week_start_date.month, week_start_date.day, tzinfo=timezone.utc
    )

    concepts_this_week = session.exec(
        select(func.count())
        .select_from(UserFlashcard)
        .where(UserFlashcard.user_id == uid, UserFlashcard.created_at >= week_start_dt)
    ).one()

    domains_studied_rows = session.exec(
        select(func.distinct(Flashcard.category))
        .select_from(UserFlashcard)
        .join(Flashcard, Flashcard.id == UserFlashcard.flashcard_id)
        .where(
            UserFlashcard.user_id == uid,
            UserFlashcard.last_reviewed >= week_start_dt,
            Flashcard.category.isnot(None),
        )
    ).all()
    domains_studied = [row for row in domains_studied_rows if row is not None]

    study_days_this_week = session.exec(
        select(func.count())
        .select_from(StudySession)
        .where(StudySession.user_id == uid, StudySession.study_date >= week_start_date)
    ).one()

    this_week = DashboardWeek(
        concepts_learned=concepts_this_week,
        domains_studied=domains_studied,
        study_days=study_days_this_week,
    )

    # 5. Weakest cards (easiness < 2.0, capped at 5, sorted ascending)
    weak_rows = session.exec(
        select(UserFlashcard, Flashcard)
        .join(Flashcard, Flashcard.id == UserFlashcard.flashcard_id)
        .where(UserFlashcard.user_id == uid, UserFlashcard.easiness < 2.0)
        .order_by(UserFlashcard.easiness.asc())
        .limit(5)
    ).all()

    weakest_cards: list[DashboardWeakCard] = [
        DashboardWeakCard(
            id=uf.flashcard_id,
            title=f.title,
            category=f.category or "",
            easiness=uf.easiness,
        )
        for uf, f in weak_rows
    ]

    # 6. Study calendar (current month)
    first_of_month = today.replace(day=1)
    calendar_rows = session.exec(
        select(StudySession.study_date)
        .where(
            StudySession.user_id == uid,
            StudySession.study_date >= first_of_month,
            StudySession.study_date <= today,
        )
        .order_by(StudySession.study_date)
    ).all()
    study_calendar = [d.isoformat() for d in calendar_rows]

    return DashboardOut(
        knowledge_summary=knowledge_summary,
        domains=domains,
        streak=streak,
        this_week=this_week,
        weakest_cards=weakest_cards,
        study_calendar=study_calendar,
    )
