#!/usr/bin/env python3
"""
Seed realistic development data for Critique local testing.

Usage:
    python scripts/seed_dev_data.py
    python scripts/seed_dev_data.py --reset
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure backend package is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine, init_db
from app.models import Project, Question, Response, User


def create_ip_hash(identifier: str) -> str:
    """Create a dummy SHA-256 hash for IP hashing."""
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()


def seed_data(reset: bool = False) -> None:
    """Populate database with sample users, projects, questions, and feedback."""
    init_db()

    db = SessionLocal()
    try:
        if reset:
            print("Resetting existing database tables...")
            Base.metadata.drop_all(bind=engine)
            init_db()

        # Check if users already exist
        existing_user = db.query(User).first()
        if existing_user and not reset:
            print("Database already contains data. Use --reset to re-seed from scratch.")
            return

        print("Seeding sample users...")
        now = datetime.now(timezone.utc)

        users = [
            User(
                username="dina_builder",
                github_id=10001,
                email="dina@example.com",
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80",
                feedback_given_count=8,
                feedback_helpful_count=6,
                feedback_score=14,
                created_at=now - timedelta(days=20),
            ),
            User(
                username="marcus_dev",
                github_id=10002,
                email="marcus@example.com",
                avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80",
                feedback_given_count=12,
                feedback_helpful_count=9,
                feedback_score=21,
                created_at=now - timedelta(days=15),
            ),
            User(
                username="elena_design",
                github_id=10003,
                email="elena@example.com",
                avatar_url="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80",
                feedback_given_count=5,
                feedback_helpful_count=4,
                feedback_score=9,
                created_at=now - timedelta(days=10),
            ),
            User(
                username="alex_founder",
                github_id=10004,
                email="alex@example.com",
                avatar_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80",
                feedback_given_count=3,
                feedback_helpful_count=2,
                feedback_score=5,
                created_at=now - timedelta(days=5),
            ),
        ]
        db.add_all(users)
        db.commit()

        for u in users:
            db.refresh(u)

        print("Seeding sample projects & questions...")
        projects_data = [
            {
                "owner": users[0],
                "title": "QueryPulse — Realtime SQL Query Performance Analyzer",
                "description": "Zero-dependency lightweight agent that profiles slow Postgres & MySQL queries, detecting missing indexes and N+1 queries automatically.",
                "url": "https://querypulse.dev",
                "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&auto=format&fit=crop&q=80",
                "question": "Is the differentiation against pg_stat_statements clear from the hero section?",
                "impressions": 48,
            },
            {
                "owner": users[1],
                "title": "DocuSift — Intelligent API Changelog Extractor",
                "description": "Turn messy git commit logs and pull requests into customer-friendly API release notes formatted for product changelogs.",
                "url": "https://docusift.io",
                "image_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&auto=format&fit=crop&q=80",
                "question": "Would you connect your GitHub repository for automated weekly changelogs?",
                "impressions": 34,
            },
            {
                "owner": users[2],
                "title": "PaletteCraft — Design System Contrast Checker",
                "description": "WCAG 2.2 accessible color palette generator tailored for design tokens in Tailwind CSS, CSS variables, and Figma variables.",
                "url": "https://palettecraft.design",
                "image_url": "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?w=800&auto=format&fit=crop&q=80",
                "question": "Does the export flow look intuitive for frontend teams?",
                "impressions": 26,
            },
            {
                "owner": users[3],
                "title": "KeyBeacon — SSL Certificate & Domain Expiry Guardian",
                "description": "Never wake up to an expired wildcard certificate or forgotten DNS domain renewal. Slack, Telegram, and Discord webhooks.",
                "url": "https://keybeacon.cloud",
                "image_url": "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=800&auto=format&fit=crop&q=80",
                "question": "Is free tier pricing sustainable and transparently explained?",
                "impressions": 19,
            },
        ]

        seeded_projects = []
        seeded_questions = []

        for p_info in projects_data:
            proj = Project(
                owner_id=p_info["owner"].id,
                title=p_info["title"],
                description=p_info["description"],
                url=p_info["url"],
                image_url=p_info["image_url"],
                discover_impressions=p_info["impressions"],
                created_at=now - timedelta(days=7),
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
            seeded_projects.append(proj)

            q = Question(
                project_id=proj.id,
                text=p_info["question"],
                is_active=True,
                created_at=now - timedelta(days=7),
            )
            db.add(q)
            db.commit()
            db.refresh(q)
            seeded_questions.append(q)

        print("Seeding sample responses & feedback...")
        sample_responses = [
            (
                seeded_questions[0],
                users[1],
                "very_clear",
                "yes",
                "The animated GIF showing the 20x speedup sold it for me. Would love a Docker quickstart command in the README.",
            ),
            (
                seeded_questions[0],
                users[2],
                "mostly_clear",
                "yes",
                "Headline is sharp. Highlight the Postgres 16 support more prominently.",
            ),
            (
                seeded_questions[0],
                users[3],
                "very_clear",
                "maybe",
                "Make sure self-hosted installation instructions are above the fold.",
            ),
            (
                seeded_questions[1],
                users[0],
                "very_clear",
                "yes",
                "Fantastic concept. We currently write changelogs by hand every Friday.",
            ),
            (
                seeded_questions[1],
                users[2],
                "somewhat_confusing",
                "maybe",
                "Show an example before-and-after of raw commit messages vs polished changelog output.",
            ),
            (
                seeded_questions[2],
                users[0],
                "very_clear",
                "yes",
                "Color contrast ratio math is clearly displayed. Love the instant Tailwind copy button.",
            ),
            (
                seeded_questions[2],
                users[1],
                "very_clear",
                "yes",
                "Figma plugin link worked great.",
            ),
            (
                seeded_questions[3],
                users[1],
                "mostly_clear",
                "yes",
                "Clean minimal design. Webhook integration docs are easy to follow.",
            ),
        ]

        for q, user, clarity, would_use, suggestion in sample_responses:
            resp = Response(
                question_id=q.id,
                user_id=user.id,
                clarity=clarity,
                would_use=would_use,
                suggestion=suggestion,
                ip_hash=create_ip_hash(f"{user.username}-ip"),
                created_at=now - timedelta(hours=12),
            )
            db.add(resp)

        db.commit()

        # Update project response counts & last_feedback_at
        for p in seeded_projects:
            count = (
                db.query(Response)
                .join(Question, Question.id == Response.question_id)
                .filter(Question.project_id == p.id)
                .count()
            )
            p.feedback_count = count
            p.last_feedback_at = now - timedelta(hours=2)
            db.add(p)

        db.commit()

        print("\nSeed data loaded successfully!")
        print("--------------------------------------------------")
        print(f"Users created:    {len(users)}")
        print(f"Projects created: {len(seeded_projects)}")
        print(f"Responses loaded: {len(sample_responses)}")
        print("--------------------------------------------------")
        print("You can now test Critique by running:")
        print("    uvicorn backend.app.main:app --reload")
        print("Visit: http://127.0.0.1:8000/discover\n")

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed sample development data for Critique")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate existing database tables before seeding",
    )
    args = parser.parse_args()
    seed_data(reset=args.reset)


if __name__ == "__main__":
    main()
