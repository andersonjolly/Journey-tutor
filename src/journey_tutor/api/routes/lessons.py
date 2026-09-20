"""Lesson HTTP routes — thin handlers that delegate to LessonService."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from journey_tutor.api.deps import get_lesson_service
from journey_tutor.api.schemas import CreateLessonRequest, CreateLessonResponse
from journey_tutor.domain.lesson_service import LessonService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["lessons"])


@router.post(
    "/lessons",
    response_model=CreateLessonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a structured lesson plan with narration",
)
async def create_lesson(
    body: CreateLessonRequest,
    service: Annotated[LessonService, Depends(get_lesson_service)],
) -> CreateLessonResponse:
    # Provider errors propagate as LessonGenerationError → HTTP via handlers.
    plan = await service.create_lesson(
        topic=body.topic,
        duration_minutes=body.duration_minutes,
        difficulty=body.difficulty,
    )
    logger.info("Lesson created title=%r sections=%s", plan.title, len(plan.sections))
    return CreateLessonResponse.model_validate(plan.model_dump())
