import asyncio
import random
import psycopg
import numpy as np
import ollama  # or remove if not installed
from config import DEBUG, DSN
from logging_setup import get_logger

logger = get_logger(__name__)

async def embed_loop():
    async with psycopg.AsyncConnection.connect(DSN) as conn:
        async with conn.cursor() as cur:
            while True:
                await cur.execute("""
                    SELECT id, content FROM memories
                    WHERE id IN (
                        SELECT rec FROM embedding_schedule WHERE started_at IS NULL AND finished_at IS NULL LIMIT 1
                    )
                """)
                row = await cur.fetchone()

                if row:
                    mem_id, content = row

                    await cur.execute("""
                        UPDATE embedding_schedule
                        SET started_at = NOW()
                        WHERE rec = %s AND started_at IS NULL
                    """, (mem_id,))

                    try:
                        if DEBUG:
                            await asyncio.sleep(1)  # Simulate delay
                            embedding = np.random.rand(1024).tolist()
                        else:
                            embedding = await ollama.embed(content)

                        await cur.execute("""
                            UPDATE memories
                            SET content_embedding = %s
                            WHERE id = %s
                        """, (embedding, mem_id))

                        await cur.execute("""
                            UPDATE embedding_schedule
                            SET finished_at = NOW()
                            WHERE rec = %s
                        """, (mem_id,))

                        logger.info(f"✅ Embedded {mem_id}")

                    except Exception as e:
                        await cur.execute("""
                            UPDATE embedding_schedule
                            SET error_msg = %s
                            WHERE rec = %s
                        """, (str(e), mem_id))

                        logger.error(f"❌ Embedding error: {mem_id} => {e}")

                else:
                    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(embed_loop())
