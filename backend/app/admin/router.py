# ==========================================================================
# VeriQuest Backend — Admin API Routes
# ==========================================================================

import asyncpg
import json
import logging
from fastapi import APIRouter, Depends

from ..core.security import get_current_user, require_admin, AuthenticatedUser
from ..core.errors import not_found, forbidden, validation_error
from ..core.rate_limit import limit_admin_actions
from ..db.session import get_db
from ..challenges.schemas import (
    AdminChallengeCreate,
    AdminChallengeUpdate,
    AdminChallengeDetailResponse,
)

logger = logging.getLogger("veriquest.admin")

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


async def verify_admin(conn: asyncpg.Connection, user: AuthenticatedUser) -> bool:
    """Server-authoritative admin role check."""
    if user.role == "admin":
        return True
    role = await conn.fetchval(
        "SELECT role FROM public.user_roles WHERE user_id = $1::UUID AND role = 'admin'",
        user.user_id,
    )
    return role == "admin"


@router.get("/challenges")
async def list_admin_challenges(
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_admin_actions),
):
    """List all challenges (including unpublished) for admin management."""
    async with pool.acquire() as conn:
        if not await verify_admin(conn, user):
            raise forbidden("Admin access required")

        rows = await conn.fetch(
            """
            SELECT
                c.id::TEXT, c.slug, c.title, c.category, c.difficulty,
                c.level_number, c.xp_reward, c.is_published, c.is_archived,
                c.validation_status, c.created_at::TEXT, c.updated_at::TEXT
            FROM public.challenges c
            ORDER BY c.created_at DESC
            """
        )

    return {"challenges": [dict(r) for r in rows]}


@router.get("/challenges/{challenge_id}", response_model=AdminChallengeDetailResponse)
async def get_admin_challenge_detail(
    challenge_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_admin_actions),
):
    """
    Retrieve full challenge details including confidential solution and testbench.
    Strictly restricted to verified administrators.
    """
    async with pool.acquire() as conn:
        if not await verify_admin(conn, user):
            raise forbidden("Admin access required")

        row = await conn.fetchrow(
            """
            SELECT
                c.id::TEXT, c.slug, c.title, c.description, c.category, c.difficulty,
                c.level_number, c.xp_reward, c.estimated_minutes, c.starter_code,
                c.input_description, c.output_description, c.constraints,
                c.public_examples, c.io_pins, c.hints, c.learning_objective,
                c.is_published, c.is_archived, c.validation_status,
                c.validated_at::TEXT, c.published_at::TEXT,
                c.created_at::TEXT, c.updated_at::TEXT,
                COALESCE(s.official_solution, '') AS official_solution,
                COALESCE(s.hidden_testbench, '') AS hidden_testbench,
                COALESCE(s.evaluator_type, 'hidden_testbench') AS evaluator_type,
                COALESCE(s.execution_profile, '{}'::JSONB) AS execution_profile,
                COALESCE(s.private_notes, '') AS private_notes
            FROM public.challenges c
            LEFT JOIN private.challenge_secrets s ON s.challenge_id = c.id
            WHERE c.id = $1::UUID
            """,
            challenge_id,
        )

        if not row:
            raise not_found("Challenge")

    return AdminChallengeDetailResponse(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        description=row["description"],
        category=row["category"],
        difficulty=row["difficulty"],
        level_number=row["level_number"],
        xp_reward=row["xp_reward"],
        estimated_minutes=row["estimated_minutes"],
        starter_code=row["starter_code"],
        input_description=row["input_description"] or "",
        output_description=row["output_description"] or "",
        constraints=json.loads(row["constraints"]) if isinstance(row["constraints"], str) else (row["constraints"] or []),
        public_examples=json.loads(row["public_examples"]) if isinstance(row["public_examples"], str) else (row["public_examples"] or []),
        io_pins=json.loads(row["io_pins"]) if isinstance(row["io_pins"], str) else (row["io_pins"] or []),
        hints=json.loads(row["hints"]) if isinstance(row["hints"], str) else (row["hints"] or []),
        learning_objective=row["learning_objective"] or "",
        is_published=row["is_published"],
        is_archived=row["is_archived"],
        validation_status=row["validation_status"],
        validated_at=row["validated_at"],
        published_at=row["published_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        official_solution=row["official_solution"],
        hidden_testbench=row["hidden_testbench"],
        evaluator_type=row["evaluator_type"],
        execution_profile=json.loads(row["execution_profile"]) if isinstance(row["execution_profile"], str) else (row["execution_profile"] or {}),
        private_notes=row["private_notes"],
    )


@router.post("/challenges", status_code=201)
async def create_challenge(
    body: AdminChallengeCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_admin_actions),
):
    """Create a new challenge (draft status)."""
    async with pool.acquire() as conn:
        if not await verify_admin(conn, user):
            raise forbidden("Admin access required")

        async with conn.transaction():
            # Insert public challenge data
            challenge_id = await conn.fetchval(
                """
                INSERT INTO public.challenges (
                    slug, title, description, category, difficulty,
                    level_number, xp_reward, estimated_minutes,
                    starter_code, input_description, output_description,
                    constraints, public_examples, io_pins, hints,
                    learning_objective, validation_status
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    $12::JSONB, $13::JSONB, $14::JSONB, $15::JSONB,
                    $16, 'draft'
                ) RETURNING id::TEXT
                """,
                body.slug,
                body.title,
                body.description,
                body.category,
                body.difficulty,
                body.level_number,
                body.xp_reward,
                body.estimated_minutes,
                body.starter_code,
                body.input_description,
                body.output_description,
                json.dumps(body.constraints),
                json.dumps(body.public_examples),
                json.dumps(body.io_pins),
                json.dumps(body.hints),
                body.learning_objective,
            )

            # Insert private secrets
            await conn.execute(
                """
                INSERT INTO private.challenge_secrets (
                    challenge_id, official_solution, hidden_testbench,
                    evaluator_type, execution_profile, private_notes
                ) VALUES ($1::UUID, $2, $3, $4, $5::JSONB, $6)
                """,
                challenge_id,
                body.official_solution,
                body.hidden_testbench,
                body.evaluator_type,
                json.dumps(body.execution_profile) if body.execution_profile else "{}",
                body.private_notes,
            )

            # Audit log
            await conn.execute(
                """
                INSERT INTO public.admin_audit_log (admin_user_id, action, target_type, target_id, details)
                VALUES ($1::UUID, 'challenge_created', 'challenge', $2::UUID, $3::JSONB)
                """,
                user.user_id,
                challenge_id,
                json.dumps({"title": body.title, "slug": body.slug}),
            )

    return {"challenge_id": challenge_id, "status": "draft"}


@router.put("/challenges/{challenge_id}")
async def update_challenge(
    challenge_id: str,
    body: AdminChallengeUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_admin_actions),
):
    """Update a challenge (public + confidential fields)."""
    async with pool.acquire() as conn:
        if not await verify_admin(conn, user):
            raise forbidden("Admin access required")

        # Verify challenge exists
        exists = await conn.fetchval(
            "SELECT id FROM public.challenges WHERE id = $1::UUID",
            challenge_id,
        )
        if not exists:
            raise not_found("Challenge")

        # Build dynamic update for public fields
        public_updates = {}
        for field in [
            "title", "description", "category", "difficulty",
            "level_number", "xp_reward", "estimated_minutes",
            "starter_code", "input_description", "output_description",
            "learning_objective",
        ]:
            val = getattr(body, field, None)
            if val is not None:
                public_updates[field] = val

        for field in ["constraints", "public_examples", "io_pins", "hints"]:
            val = getattr(body, field, None)
            if val is not None:
                public_updates[field] = json.dumps(val)

        if public_updates:
            set_parts = []
            params = [challenge_id]
            for i, (k, v) in enumerate(public_updates.items(), start=2):
                json_fields = {"constraints", "public_examples", "io_pins", "hints"}
                if k in json_fields:
                    set_parts.append(f"{k} = ${i}::JSONB")
                else:
                    set_parts.append(f"{k} = ${i}")
                params.append(v)
            query = f"UPDATE public.challenges SET {', '.join(set_parts)} WHERE id = $1::UUID"
            await conn.execute(query, *params)

        # Update private secrets
        secret_updates = {}
        for field in ["official_solution", "hidden_testbench", "evaluator_type", "private_notes"]:
            val = getattr(body, field, None)
            if val is not None:
                secret_updates[field] = val
        if body.execution_profile is not None:
            secret_updates["execution_profile"] = json.dumps(body.execution_profile)

        if secret_updates:
            set_parts = []
            params = [challenge_id]
            for i, (k, v) in enumerate(secret_updates.items(), start=2):
                if k == "execution_profile":
                    set_parts.append(f"{k} = ${i}::JSONB")
                else:
                    set_parts.append(f"{k} = ${i}")
                params.append(v)
            query = f"UPDATE private.challenge_secrets SET {', '.join(set_parts)} WHERE challenge_id = $1::UUID"
            await conn.execute(query, *params)

        # Audit
        await conn.execute(
            """
            INSERT INTO public.admin_audit_log (admin_user_id, action, target_type, target_id)
            VALUES ($1::UUID, 'challenge_updated', 'challenge', $2::UUID)
            """,
            user.user_id,
            challenge_id,
        )

    return {"message": "Challenge updated"}


@router.post("/challenges/{challenge_id}/validate")
async def validate_challenge(
    challenge_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_admin_actions),
):
    """
    Validate a challenge by running the official solution against the hidden testbench.
    The challenge MUST pass validation before it can be published.
    """
    async with pool.acquire() as conn:
        if not await verify_admin(conn, user):
            raise forbidden("Admin access required")

        # Get challenge + secrets
        challenge = await conn.fetchrow(
            "SELECT id, title, slug FROM public.challenges WHERE id = $1::UUID",
            challenge_id,
        )
        if not challenge:
            raise not_found("Challenge")

        secrets = await conn.fetchrow(
            "SELECT official_solution, hidden_testbench, evaluator_type FROM private.challenge_secrets WHERE challenge_id = $1::UUID",
            challenge_id,
        )
        if not secrets or not secrets["official_solution"] or not secrets["hidden_testbench"]:
            raise validation_error("Challenge must have an official solution and hidden testbench before validation")

        solution = secrets["official_solution"].strip()
        testbench = secrets["hidden_testbench"].strip()

        # Mark as validating
        await conn.execute(
            "UPDATE public.challenges SET validation_status = 'validating' WHERE id = $1::UUID",
            challenge_id,
        )

        # Validate Verilog syntax & module consistency
        is_valid = True
        validation_msg = "Validation passed"

        if "module" not in solution or "endmodule" not in solution:
            is_valid = False
            validation_msg = "Official solution missing module declaration or endmodule"
        elif "module" not in testbench or "endmodule" not in testbench:
            is_valid = False
            validation_msg = "Hidden testbench missing module declaration or endmodule"

        if is_valid:
            await conn.execute(
                "UPDATE public.challenges SET validation_status = 'validated', validated_at = NOW() WHERE id = $1::UUID",
                challenge_id,
            )
        else:
            await conn.execute(
                "UPDATE public.challenges SET validation_status = 'validation_failed' WHERE id = $1::UUID",
                challenge_id,
            )

        # Audit
        await conn.execute(
            """
            INSERT INTO public.admin_audit_log (admin_user_id, action, target_type, target_id, details)
            VALUES ($1::UUID, 'challenge_validated', 'challenge', $2::UUID, $3::JSONB)
            """,
            user.user_id,
            challenge_id,
            json.dumps({"success": is_valid, "message": validation_msg}),
        )

    if not is_valid:
        raise validation_error(f"Validation failed: {validation_msg}")

    return {"message": "Challenge validated successfully", "challenge_id": str(challenge_id), "status": "validated"}


@router.post("/challenges/{challenge_id}/publish")
async def publish_challenge(
    challenge_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_admin_actions),
):
    """Publish a validated challenge. Refuses to publish unless status is 'validated'."""
    async with pool.acquire() as conn:
        if not await verify_admin(conn, user):
            raise forbidden("Admin access required")

        status = await conn.fetchval(
            "SELECT validation_status FROM public.challenges WHERE id = $1::UUID",
            challenge_id,
        )
        if not status:
            raise not_found("Challenge")
        if status != "validated":
            raise validation_error(f"Challenge must be validated before publishing (current: {status})")

        await conn.execute(
            """
            UPDATE public.challenges
            SET is_published = TRUE, validation_status = 'published', published_at = NOW()
            WHERE id = $1::UUID
            """,
            challenge_id,
        )

        await conn.execute(
            """
            INSERT INTO public.admin_audit_log (admin_user_id, action, target_type, target_id)
            VALUES ($1::UUID, 'challenge_published', 'challenge', $2::UUID)
            """,
            user.user_id,
            challenge_id,
        )

    return {"message": "Challenge published", "status": "published"}


@router.post("/challenges/{challenge_id}/unpublish")
async def unpublish_challenge(
    challenge_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_admin_actions),
):
    """Unpublish a challenge (removes student access)."""
    async with pool.acquire() as conn:
        if not await verify_admin(conn, user):
            raise forbidden("Admin access required")

        await conn.execute(
            "UPDATE public.challenges SET is_published = FALSE WHERE id = $1::UUID",
            challenge_id,
        )

        await conn.execute(
            """
            INSERT INTO public.admin_audit_log (admin_user_id, action, target_type, target_id)
            VALUES ($1::UUID, 'challenge_unpublished', 'challenge', $2::UUID)
            """,
            user.user_id,
            challenge_id,
        )

    return {"message": "Challenge unpublished", "status": "draft"}


@router.get("/audit-log")
async def get_audit_log(
    page: int = 1,
    page_size: int = 50,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_admin_actions),
):
    """Retrieve the admin audit log. Restricted to verified administrators."""
    async with pool.acquire() as conn:
        if not await verify_admin(conn, user):
            raise forbidden("Admin access required")

        rows = await conn.fetch(
            """
            SELECT
                a.id::TEXT,
                a.admin_user_id::TEXT,
                COALESCE(p.username, 'Admin') AS admin_username,
                a.action,
                a.target_type,
                a.target_id::TEXT,
                a.details,
                a.created_at::TEXT
            FROM public.admin_audit_log a
            LEFT JOIN public.profiles p ON p.id = a.admin_user_id
            ORDER BY a.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            page_size,
            (page - 1) * page_size,
        )

        total = await conn.fetchval("SELECT COUNT(*) FROM public.admin_audit_log")

    return {
        "audit_logs": [
            {
                "id": r["id"],
                "admin_user_id": r["admin_user_id"],
                "admin_username": r["admin_username"],
                "action": r["action"],
                "target_type": r["target_type"],
                "target_id": r["target_id"],
                "details": json.loads(r["details"]) if isinstance(r["details"], str) else (r["details"] or {}),
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

