import json
import logging
from datetime import datetime, timezone
from typing import List

import psycopg

from app.config import POSTGRES_DSN
from models.llm_profile import default_non_thinking_model
from models.turn import Turn
from services.llm_factory import get_async_instructor_client

logger = logging.getLogger("rubato.services.conversation")


async def load_conversation_history(conversation_id: str) -> List[Turn]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()

    await cur.execute(
        "SELECT history FROM conversations WHERE conversation_id = %s",
        (conversation_id,),
    )
    row = await cur.fetchone()
    await cur.close()
    await conn.close()

    if row is None:
        return []
    return [Turn.model_validate(t) for t in row[0]]


async def save_conversation_turn(
    conversation_id: str,
    customer_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    now = datetime.now(timezone.utc)
    history = await load_conversation_history(conversation_id)
    history.append(Turn(role="user", content=user_message, timestamp=now))
    history.append(Turn(role="assistant", content=assistant_message, timestamp=now))

    history = await _compact_if_needed(history)

    serialized = json.dumps([t.model_dump(mode="json") for t in history])

    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()

    await cur.execute(
        """
        INSERT INTO conversations (conversation_id, customer_id, history, updated_at)
        VALUES (%s, %s, %s::jsonb, %s)
        ON CONFLICT (conversation_id)
        DO UPDATE SET history = EXCLUDED.history, updated_at = EXCLUDED.updated_at
        """,
        (conversation_id, customer_id, serialized, now),
    )
    await conn.commit()
    await cur.close()
    await conn.close()


HISTORY_TOKEN_BUDGET = 3000  # rough char/4 estimate, not exact tokenization
KEEP_VERBATIM_TURNS = 6

plain_client = get_async_instructor_client(default_non_thinking_model)


def _estimate_tokens(turns: list[Turn]) -> int:
    total_chars = sum(len(t.content) for t in turns)
    return total_chars // 4


async def _summarize_turns(turns: list[Turn]) -> Turn:
    transcript = "\n".join(f"{t.role}: {t.content}" for t in turns)
    response = await plain_client(
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarize this customer support exchange in 2-4 sentences. "
                    "Preserve concrete facts: order IDs, decisions made, amounts, "
                    "and outcomes. Drop pleasantries and small talk."
                ),
            },
            {"role": "user", "content": transcript},
        ],
    )
    summary_text = response.choices[0].message.content
    content = f"[Earlier conversation summary]: {summary_text}"
    return Turn(role="assistant", content=content, timestamp=datetime.now(timezone.utc))


async def _compact_if_needed(history: list[Turn]) -> list[Turn]:
    if _estimate_tokens(history) <= HISTORY_TOKEN_BUDGET:
        return history

    verbatim_tail = history[-KEEP_VERBATIM_TURNS:]
    older = history[:-KEEP_VERBATIM_TURNS]
    if not older:
        return history  # nothing old enough to summarize, budget just tight

    summary_turn = await _summarize_turns(older)
    return [summary_turn, *verbatim_tail]