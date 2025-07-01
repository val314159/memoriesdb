#!/usr/bin/env python3

import asyncio
import sys
from db_utils import execute_query, execute_query_fetchall, execute_query_fetchone

async def test_connection():
    print("Testing database connection...")
    try:
        # Test simple query with fetchone
        print("\nTesting execute_query_fetchone:")
        result = await execute_query_fetchone("SELECT 1 as test")
        print(f"Query result: {result}")
        
        # Test execute_query_fetchall with multiple rows
        print("\nTesting execute_query_fetchall:")
        rows = await execute_query_fetchall("SELECT generate_series(1, 20) as num")
        print(f"Fetched {len(rows)} rows at once")
        for i, row in enumerate(rows[:5]):
            print(f"Row from fetchall {i+1}: {row}")
            
        # Test execute_query (streaming)
        print("\nTesting execute_query streaming:")
        count = 0
        async for row in execute_query("SELECT generate_series(21, 40) as num"):
            count += 1
            if count <= 5:  # Only show first 5 rows
                print(f"Streaming row {count}: {row}")
        print(f"Streamed {count} rows one by one")
        
        print("\nAll tests passed! Connection successful!")
        return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
