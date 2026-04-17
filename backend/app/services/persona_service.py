from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaUpdate


async def create_persona(db: AsyncSession, data: PersonaCreate) -> Persona:
    if data.type == "coordinator":
        result = await db.execute(
            select(Persona).where(
                Persona.language_id == data.language_id,
                Persona.type == "coordinator",
                Persona.deleted_at.is_(None),
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            raise ValueError(
                "A coordinator already exists for this language"
            )

    persona = Persona(
        name=data.name,
        language_id=data.language_id,
        gender=data.gender,
        type=data.type,
        teaching_style=data.teaching_style,
        is_active=True,
    )
    db.add(persona)
    await db.flush()
    return persona


async def get_personas(
    db: AsyncSession, language_id: UUID | None = None
) -> list[Persona]:
    stmt = select(Persona).where(Persona.deleted_at.is_(None))
    if language_id is not None:
        stmt = stmt.where(Persona.language_id == language_id)
    stmt = stmt.order_by(Persona.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


list_personas = get_personas


async def get_persona(db: AsyncSession, persona_id: UUID) -> Persona | None:
    result = await db.execute(
        select(Persona).where(
            Persona.id == persona_id, Persona.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def update_persona(
    db: AsyncSession, persona_id: UUID, data: PersonaUpdate
) -> Persona | None:
    persona = await get_persona(db, persona_id)
    if persona is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(persona, key, value)

    await db.flush()
    return persona


async def delete_persona(db: AsyncSession, persona_id: UUID) -> bool:
    persona = await get_persona(db, persona_id)
    if persona is None:
        return False

    persona.deleted_at = datetime.now(timezone.utc)
    persona.is_active = False
    await db.flush()
    return True


async def get_teacher_for_language(
    db: AsyncSession, language_id: UUID
) -> Persona | None:
    result = await db.execute(
        select(Persona).where(
            Persona.language_id == language_id,
            Persona.type == "teacher",
            Persona.is_active.is_(True),
            Persona.deleted_at.is_(None),
        )
    )
    return result.scalars().first()


async def get_coordinator(db: AsyncSession) -> Persona | None:
    result = await db.execute(
        select(Persona).where(
            Persona.type == "coordinator",
            Persona.is_active.is_(True),
            Persona.deleted_at.is_(None),
        )
    )
    return result.scalars().first()
