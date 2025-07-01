#!/usr/bin/env python3

import asyncio
import sys
from db_utils import execute_query, execute_query_fetchone

async def test_connection():
    print("Testing database connection...")
    try:
        # Test simple query with fetchone
        print("\nTesting execute_query_fetchone:")
        result = await execute_query_fetchone("SELECT 1 as test")
        print(f"Query result: {result}")
        
        # Test execute_query with multiple rows
        print("\nTesting execute_query:")
        rows = await execute_query("SELECT generate_series(1, 5) as num")
        for row in rows:
            print(f"Row: {row}")
        
        print("\nAll tests passed! Connection successful!")
        return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
