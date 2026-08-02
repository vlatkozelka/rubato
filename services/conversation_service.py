import json
import logging
from datetime import datetime, timezone
from typing import List

import psycopg

from app.config import POSTGRES_DSN
from models.turn import Turn

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