import asyncio
import random
import numpy as np
import ollama  # or remove if not installed
from config import DEBUG
from db_utils import execute_query
from logging_setup import get_logger

logger = get_logger(__name__)

async def embed_loop():
    while True:
        # Find next memory to embed
        row = await execute_query("""
            SELECT id, content FROM memories
            WHERE id IN (
                SELECT rec FROM embedding_schedule WHERE started_at IS NULL AND finished_at IS NULL LIMIT 1
            )
        """, fetch_one=True)

        if row:
            mem_id, content = row

            # Mark as started
            await execute_query("""
                UPDATE embedding_schedule
                SET started_at = NOW()
                WHERE rec = %s AND started_at IS NULL
            """, params=(mem_id,))

            try:
                # Generate embedding
                if DEBUG:
                    await asyncio.sleep(1)  # Simulate delay
                    embedding = np.random.rand(1024).tolist()
                else:
                    embedding = await ollama.embed(content)

                # Update memory with embedding
                await execute_query("""
                    UPDATE memories
                    SET content_embedding = %s
                    WHERE id = %s
                """, params=(embedding, mem_id))

                # Mark as complete
                await execute_query("""
                    UPDATE embedding_schedule
                    SET finished_at = NOW()
                    WHERE rec = %s
                """, params=(mem_id,))

                logger.info(f"✅ Embedded {mem_id}")

            except Exception as e:
                # Record error
                await execute_query("""
                    UPDATE embedding_schedule
                    SET error_msg = %s
                    WHERE rec = %s
                """, params=(str(e), mem_id))

                logger.error(f"❌ Embedding error: {mem_id} => {e}")

        else:
            # No work to do, wait before checking again
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(embed_loop())
