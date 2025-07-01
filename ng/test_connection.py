#!/usr/bin/env python3

import asyncio
import sys
import time
from db_utils import execute_query, execute_query_fetchall, execute_query_fetchone, get_pool

async def test_connection_pool():
    print("\n1. Testing connection pool...")
    try:
        # Test get_pool
        pool = await get_pool()
        print(f"Pool obtained: min_size={pool.min_size}, max_size={pool.max_size}")
        
        # Test multiple connections from pool
        print("Testing multiple connections from pool...")
        async with pool.connection() as conn1:
            async with pool.connection() as conn2:
                print(f"Got two connections concurrently: {conn1 != conn2}")
                
        return True
    except Exception as e:
        print(f"Error testing pool: {e}")
        return False

async def test_fetchone():
    print("\n2. Testing execute_query_fetchone...")
    try:
        # Test basic scalar query
        result = await execute_query_fetchone("SELECT 1 as test")
        print(f"Simple scalar query result: {result}")
        
        # Test with parameters
        param_result = await execute_query_fetchone("SELECT %s::text as param_test", ("Hello",))
        print(f"Parameterized query result: {param_result}")
        
        # Test dictionary result
        dict_result = await execute_query_fetchone("SELECT 42 as answer, 'postgres' as db", as_dict=True)
        print(f"Dictionary result: {dict_result}")
        
        # Test no results
        no_result = await execute_query_fetchone("SELECT * FROM pg_tables WHERE tablename = 'nonexistent_table'")
        print(f"No results query returned: {no_result}")
        
        return True
    except Exception as e:
        print(f"Error testing fetchone: {e}")
        return False
        
async def test_fetchall():
    print("\n3. Testing execute_query_fetchall...")
    try:
        # Test with multiple rows
        rows = await execute_query_fetchall("SELECT generate_series(1, 20) as num")
        print(f"Fetched {len(rows)} rows at once")
        for i, row in enumerate(rows[:5]):
            print(f"Row {i+1}: {row}")
            
        # Test with parameters
        param_rows = await execute_query_fetchall(
            "SELECT * FROM generate_series(%s::int, %s::int) as nums", 
            (5, 10)
        )
        print(f"Parameter query returned {len(param_rows)} rows")
        
        # Test dictionary results
        dict_rows = await execute_query_fetchall(
            "SELECT generate_series(1, 5) as num, 'test' as text",
            as_dict=True
        )
        print(f"Dictionary row example: {dict_rows[0]}")
        
        # Test empty results
        empty_rows = await execute_query_fetchall("SELECT * FROM pg_tables WHERE tablename = 'nonexistent_table'")
        print(f"Empty result set has {len(empty_rows)} rows")
        
        return True
    except Exception as e:
        print(f"Error testing fetchall: {e}")
        return False

async def test_streaming():
    print("\n4. Testing execute_query (streaming)...")
    try:
        # Test basic streaming
        print("Basic streaming test:")
        count = 0
        async for row in execute_query("SELECT generate_series(1, 20) as num"):
            count += 1
            if count <= 3:
                print(f"Stream row {count}: {row}")
        print(f"Streamed {count} rows one by one")
        
        # Test with parameters
        print("\nStreaming with parameters:")
        param_count = 0
        async for row in execute_query(
            "SELECT * FROM generate_series(%s::int, %s::int) as nums",
            (50, 60)
        ):
            param_count += 1
            if param_count <= 3:
                print(f"Stream param row {param_count}: {row}")
        print(f"Streamed {param_count} parameterized rows")
        
        # Test with dictionary results
        print("\nStreaming with dictionary results:")
        dict_count = 0
        async for row in execute_query(
            "SELECT generate_series(1, 5) as num, 'test' as text",
            as_dict=True
        ):
            dict_count += 1
            print(f"Stream dict row {dict_count}: {row}")
        
        # Test empty results
        print("\nStreaming with empty results:")
        empty_count = 0
        async for row in execute_query("SELECT * FROM pg_tables WHERE tablename = 'nonexistent_table'"):
            empty_count += 1
        print(f"Empty stream returned {empty_count} rows")
        
        return True
    except Exception as e:
        print(f"Error testing streaming: {e}")
        return False

async def run_all_tests():
    print("Running comprehensive db_utils tests...")
    start_time = time.time()
    
    # Run all tests
    pool_success = await test_connection_pool()
    fetchone_success = await test_fetchone()
    fetchall_success = await test_fetchall()
    streaming_success = await test_streaming()
    
    # Report results
    duration = time.time() - start_time
    all_passed = all([pool_success, fetchone_success, fetchall_success, streaming_success])
    
    print("\n" + "=" * 50)
    print(f"Test Results (completed in {duration:.2f}s):")
    print(f"  Connection Pool Tests: {'✅ PASSED' if pool_success else '❌ FAILED'}")
    print(f"  execute_query_fetchone: {'✅ PASSED' if fetchone_success else '❌ FAILED'}")
    print(f"  execute_query_fetchall: {'✅ PASSED' if fetchall_success else '❌ FAILED'}")
    print(f"  execute_query (streaming): {'✅ PASSED' if streaming_success else '❌ FAILED'}")
    print("=" * 50)
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
