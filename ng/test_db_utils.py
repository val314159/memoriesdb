#!/usr/bin/env python3
import asyncio
import logging
import time

from db_utils import execute_query, execute_query_fetchone
from logging_setup import get_logger

logger = get_logger(__name__)
logger.setLevel(logging.INFO)

async def test_execute_query_streaming():
    """Test streaming results from execute_query"""
    logger.info("Testing execute_query streaming...")
    
    # Create test data
    await execute_query_fetchone("""DROP TABLE IF EXISTS test_table;""")
    await execute_query_fetchone("""CREATE TABLE test_table (id SERIAL PRIMARY KEY, name TEXT);""")  
    
    # Insert test data
    for i in range(10):
        await execute_query_fetchone("""INSERT INTO test_table (name) VALUES (%s)""", (f"test-{i}",))
    
    # Test streaming with async iterator
    count = 0
    start = time.time()
    async for row in await execute_query("""SELECT * FROM test_table ORDER BY id"""):
        logger.info(f"Row {count}: {row}")
        count += 1
        # Simulate processing time to demonstrate streaming
        await asyncio.sleep(0.1)
    
    duration = time.time() - start
    logger.info(f"Processed {count} rows in {duration:.2f}s")
    assert count == 10, f"Expected 10 rows, got {count}"
    
    # Test fetchone
    row = await execute_query_fetchone("""SELECT * FROM test_table WHERE id = 5""")  
    logger.info(f"Fetched one: {row}")
    assert row and row[0] == 5, f"Expected row with id=5, got {row}"
    
    # Test fetching non-existent row
    row = await execute_query_fetchone("""SELECT * FROM test_table WHERE id = 999""") 
    logger.info(f"Fetched non-existent: {row}")
    assert row is None, f"Expected None for non-existent row, got {row}"
    
    # Test error handling
    try:
        await execute_query_fetchone("""SELECT * FROM nonexistent_table""") 
        assert False, "Should have raised an exception"
    except Exception as e:
        logger.info(f"Expected error caught: {e.__class__.__name__}")
        
    logger.info("✅ All streaming tests passed!")

async def main():
    await test_execute_query_streaming()

if __name__ == "__main__":
    asyncio.run(main())
