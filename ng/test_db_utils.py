#!/usr/bin/env python3
import asyncio
import logging
import time

from db_utils import query, query_fetchone, query_fetchall, execute
from logging_setup import get_logger

logger = get_logger(__name__)
logger.setLevel(logging.INFO)

async def setup_test_table():
    """Setup test table using execute for DDL and INSERT"""
    logger.info("Setting up test table...")
    await execute("""DROP TABLE IF EXISTS test_table;""")
    await execute("""CREATE TABLE test_table (id SERIAL PRIMARY KEY, name TEXT);""")
    
    # Insert test data
    for i in range(10):
        await execute("""INSERT INTO test_table (name) VALUES (%s)""", (f"test-{i}",))
    
    logger.info("Test table setup complete")

async def cleanup_test_table():
    """Clean up test table using execute"""
    logger.info("Cleaning up test table...")
    await execute("""DROP TABLE IF EXISTS test_table;""")
    logger.info("Test table cleanup complete")

async def test_query_streaming():
    """Test streaming results from query"""
    logger.info("Testing query streaming...")
    
    # Test streaming with async iterator
    count = 0
    start = time.time()
    async for row in query("""SELECT * FROM test_table ORDER BY id"""):
        logger.info(f"Row {count}: {row}")
        count += 1
        # Simulate processing time to demonstrate streaming
        await asyncio.sleep(0.1)
    
    duration = time.time() - start
    logger.info(f"Processed {count} rows in {duration:.2f}s")
    assert count == 10, f"Expected 10 rows, got {count}"
    
    # Test fetchone
    row = await query_fetchone("""SELECT * FROM test_table WHERE id = 5""")  
    logger.info(f"Fetched one: {row}")
    assert row and row[0] == 5, f"Expected row with id=5, got {row}"
    
    # Test fetching non-existent row
    row = await query_fetchone("""SELECT * FROM test_table WHERE id = 999""") 
    logger.info(f"Fetched non-existent: {row}")
    assert row is None, f"Expected None for non-existent row, got {row}"
    
    # Test error handling
    try:
        await query_fetchone("""SELECT * FROM nonexistent_table""") 
        assert False, "Should have raised an exception"
    except Exception as e:
        logger.info(f"Expected error caught: {e.__class__.__name__}")
        
    logger.info("✅ All streaming tests passed!")

async def test_fetch_all():
    """Test fetching multiple rows at once"""
    logger.info("Testing query_fetchall...")
    
    # Test basic fetch all
    rows = await query_fetchall("""SELECT * FROM test_table ORDER BY id""")
    logger.info(f"Fetched {len(rows)} rows at once")
    assert len(rows) == 10, f"Expected 10 rows, got {len(rows)}"
    
    # Test with parameters
    param_rows = await query_fetchall(
        """SELECT * FROM test_table WHERE id > %s AND id < %s ORDER BY id""", 
        (3, 8)
    )
    logger.info(f"Parameter query returned {len(param_rows)} rows")
    assert len(param_rows) == 4, f"Expected 4 rows, got {len(param_rows)}"
    
    # Test dictionary results
    dict_rows = await query_fetchall(
        """SELECT id, name FROM test_table WHERE id <= 5 ORDER BY id""",
        as_dict=True
    )
    logger.info(f"Dictionary row example: {dict_rows[0]}")
    assert 'id' in dict_rows[0], "Expected dictionary row with 'id' key"
    assert 'name' in dict_rows[0], "Expected dictionary row with 'name' key"
    
    logger.info("✅ All fetchall tests passed!")

async def main():
    # Setup
    await setup_test_table()
    
    try:
        # Run tests
        await test_query_streaming()
        await test_fetch_all()
        logger.info("✅ All database utility tests passed!")
    finally:
        # Cleanup
        await cleanup_test_table()

if __name__ == "__main__":
    asyncio.run(main())
