import asyncio
import psycopg
from config import DEBUG, DSN
from logging_setup import get_logger

logger = get_logger(__name__)

async def index_loop():
    async with psycopg.AsyncConnection.connect(DSN) as conn:
        async with conn.cursor() as cur:
            while True:
                await cur.execute("""
                    SELECT rec FROM vindexing_schedule
                    WHERE started_at IS NULL AND finished_at IS NULL
                    LIMIT 1
                """)
                row = await cur.fetchone()

                if row:
                    mem_id = row[0]

                    await cur.execute("""
                        UPDATE vindexing_schedule
                        SET started_at = NOW()
                        WHERE rec = %s AND started_at IS NULL
                    """, (mem_id,))

                    try:
                        if DEBUG:
                            await asyncio.sleep(1)  # Fake delay
                            logger.debug(f"🧪 Pretend indexing {mem_id}")
                        else:
                            await cur.execute("REFRESH MATERIALIZED VIEW memory_graph;")

                        await cur.execute("""
                            UPDATE vindexing_schedule
                            SET finished_at = NOW()
                            WHERE rec = %s
                        """, (mem_id,))

                        logger.info(f"✅ Indexed {mem_id}")

                    except Exception as e:
                        await cur.execute("""
                            UPDATE vindexing_schedule
                            SET error_msg = %s
                            WHERE rec = %s
                        """, (str(e), mem_id))

                        logger.error(f"❌ Index error: {mem_id} => {e}")

                else:
                    await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(index_loop())
