import asyncio
from config import DEBUG
from db_utils import execute_query
from logging_setup import get_logger

logger = get_logger(__name__)

async def index_loop():
    while True:
        # Find next memory to index
        row = await execute_query("""
            SELECT rec FROM vindexing_schedule
            WHERE started_at IS NULL AND finished_at IS NULL
            LIMIT 1
        """, fetch_one=True)

        if row:
            mem_id = row[0]

            # Mark as started
            await execute_query("""
                UPDATE vindexing_schedule
                SET started_at = NOW()
                WHERE rec = %s AND started_at IS NULL
            """, params=(mem_id,))

            try:
                if DEBUG:
                    await asyncio.sleep(1)  # Fake delay
                    logger.debug(f"🧪 Pretend indexing {mem_id}")
                else:
                    # Refresh the materialized view
                    await execute_query("REFRESH MATERIALIZED VIEW memory_graph;")

                # Mark as complete
                await execute_query("""
                    UPDATE vindexing_schedule
                    SET finished_at = NOW()
                    WHERE rec = %s
                """, params=(mem_id,))

                logger.info(f"✅ Indexed {mem_id}")

            except Exception as e:
                # Record error
                await execute_query("""
                    UPDATE vindexing_schedule
                    SET error_msg = %s
                    WHERE rec = %s
                """, params=(str(e), mem_id))

                logger.error(f"❌ Index error: {mem_id} => {e}")

        else:
            # No work to do, wait before checking again
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(index_loop())
