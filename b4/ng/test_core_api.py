#!/usr/bin/env python3
import uuid
import asyncio
import time
import logging
from typing import Optional, List

# this whole file is almost certainly garbage

'''

from db_utils import (
    query, query_fetchone, query_fetchall, execute,
    get_current_user_id, set_current_user_id, close_pool, # Added close_pool
    search_memories_vector,
    get_memory_by_id, create_memory, create_memory_edge
)
from logging_setup import get_logger

logger = get_logger(__name__)
logger.setLevel(logging.INFO)

# Test user details for audit logging
TEST_USER_EMAIL = "test@example.com"

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
    """Cleanup test table"""
    logger.info("Cleaning up test table...")
    await execute("DROP TABLE IF EXISTS test_table;")
    logger.info("Test table cleanup complete")

async def get_or_create_test_user():
    """Get existing or create new test user in the database"""
    # Try to get existing test user first
    existing_user = await query_fetchone(
        "SELECT id FROM users WHERE email = %s",
        (TEST_USER_EMAIL,),
        as_dict=True # Ensure dictionary return
    )
    
    if existing_user:
        # Use existing user ID
        user_id = existing_user['id']
        logger.info(f"Using existing test user with ID: {user_id}")
    else:
        # Create new test user
        # Generate UUID in Python for simplicity in test setup, though DB can do it
        user_id = str(uuid.uuid4()) 
        logger.info(f"Creating new test user with ID: {user_id}")
        await execute(
            "INSERT INTO users (id, email) VALUES (%s, %s)",
            (user_id, TEST_USER_EMAIL)
        )
    
    # Return the user ID (either existing or new)
    return user_id

# Global variable to store test user ID once retrieved/created
test_user_id = None

async def test_query_streaming():
    """Test streaming results from query"""
    logger.info("Testing query streaming...")
    
    # Test streaming with async iterator
    count = 0
    start = time.time()
    async for row in query("""SELECT * FROM test_table ORDER BY id"""): # Corrected: no await on query()
        logger.info(f"Row {count}: {row}")
        count += 1
        # Simulate processing time to demonstrate streaming
        await asyncio.sleep(0.01) # Reduced sleep for faster tests
    
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

async def test_execute():
    """Test execute function for non-query operations"""
    logger.info("Testing execute...")
    
    # Test UPDATE operation
    await execute("UPDATE test_table SET name = %s WHERE id = %s", ("updated-name", 1))
    
    # Get the row and verify content without assuming format
    row = await query_fetchone("SELECT name FROM test_table WHERE id = 1")
    
    # Check if we got a result and log what format it is
    assert row is not None, "Expected a row result but got None"
    logger.info(f"Row type: {type(row)}, value: {row}")
    
    # Handle both possible formats (tuple or dict based on as_dict=True/False)
    if isinstance(row, dict):
        assert row['name'] == "updated-name", f"Expected 'updated-name', got {row['name']}"
    else:
        assert row[0] == "updated-name", f"Expected 'updated-name', got {row[0]}"
    
    # Test transaction handling (should be rolled back on exception)
    try:
        # This will fail because nonexistent_column does not exist
        await execute("UPDATE test_table SET nonexistent_column = 'test' WHERE id = 1")
        assert False, "Should have raised an exception"
    except Exception as e:
        logger.info(f"Expected error caught: {e.__class__.__name__}")
    
    logger.info("✅ All execute tests passed!")

async def test_create_memory():
    """Test create_memory function"""
    logger.info("Testing create_memory function...")
    
    # Ensure user context is set
    set_current_user_id(test_user_id)
    
    # Test create_memory
    memory_content = "Test memory content for create_memory"
    # Use created_by as per db_utils.py signature
    memory_id = await create_memory(test_user_id, memory_content) 
    assert memory_id is not None, "Failed to create memory"
    logger.info(f"Created memory with ID: {memory_id}")
    
    # Retrieve memory to verify content
    memory = await get_memory_by_id(memory_id)
    assert memory is not None, "Failed to retrieve created memory"
    assert memory['content'] == memory_content, "Memory content does not match"
    assert memory['created_by'] == uuid.UUID(test_user_id), "Memory created_by does not match" # Check created_by
    
    # Clean up the memory record - related records will be deleted by CASCADE
    await execute("DELETE FROM memories WHERE id = %s", (memory_id,))
    
    logger.info("✅ create_memory test passed!")

async def test_memory_operations():
    """Test memory-specific operations"""
    logger.info("Testing memory operations...")
    
    # Ensure user context is set
    set_current_user_id(test_user_id)
    
    # Test direct memory creation using execute (for setup, not testing create_memory itself)
    memory_content = "Test memory content for database operations"
    
    # Create memory directly with execute, ensuring created_by is set
    memory_id_result = await execute(
        "INSERT INTO memories (content, created_by, updated_by) VALUES (%s, %s, %s) RETURNING id",
        (memory_content, test_user_id, test_user_id)
    )
    assert memory_id_result, "Failed to create memory via execute"
    memory_id = memory_id_result[0][0] # execute returns list of tuples, get first element of first tuple
    logger.info(f"Created memory with ID: {memory_id}")
    
    # Test get_memory_by_id
    memory = await get_memory_by_id(memory_id)
    assert memory, f"Failed to retrieve memory with ID: {memory_id}"
    assert memory['content'] == memory_content, "Memory content does not match"
    assert memory['created_by'] == uuid.UUID(test_user_id), "Memory created_by does not match"
    logger.info(f"Retrieved memory: {memory['id']}")
    
    # Clean up the memory record - related records will be deleted by CASCADE
    await execute("DELETE FROM memories WHERE id = %s", (memory_id,))
    
    # Verify deletion
    deleted_memory = await get_memory_by_id(memory_id)
    assert deleted_memory is None, "Memory was not deleted"
    
    logger.info("✅ All memory operations tests passed!")

async def test_memory_edges():
    """Test memory edge operations"""
    logger.info("Testing memory edge operations...")
    
    # Set the user context for audit logging
    set_current_user_id(test_user_id)
    
    # Create two test memories directly, ensuring created_by is set
    memory1_result = await execute(
        "INSERT INTO memories (content, created_by, updated_by) VALUES (%s, %s, %s) RETURNING id",
        ("Source memory", test_user_id, test_user_id)
    )
    memory2_result = await execute(
        "INSERT INTO memories (content, created_by, updated_by) VALUES (%s, %s, %s) RETURNING id",
        ("Target memory", test_user_id, test_user_id)
    )
    
    # Extract IDs
    memory1_id = memory1_result[0][0]
    memory2_id = memory2_result[0][0]
    logger.info(f"Created test memories with IDs: {memory1_id}, {memory2_id}")
    
    # Create an edge, passing created_by
    edge_type = "references"
    edge_id_result = await create_memory_edge(memory1_id, memory2_id, edge_type, test_user_id) # Pass created_by
    assert edge_id_result, "Failed to create memory edge"
    edge_id = edge_id_result[0] # create_memory_edge returns a single value
    logger.info(f"Created edge with ID: {edge_id}")
    
    # Verify edge exists
    edge = await query_fetchone(
        "SELECT * FROM memory_edges WHERE id = %s", 
        (edge_id,), 
        as_dict=True
    )
    assert edge, f"Failed to retrieve edge with ID: {edge_id}"
    assert edge['source_id'] == uuid.UUID(memory1_id), "Edge source doesn't match"
    assert edge['target_id'] == uuid.UUID(memory2_id), "Edge target doesn't match"
    assert edge['relation'] == edge_type, "Edge type doesn't match"
    assert edge['created_by'] == uuid.UUID(test_user_id), "Edge created_by doesn't match"
    
    # Cleanup
    await execute("DELETE FROM memory_edges WHERE id = %s", (edge_id,))
    await execute("DELETE FROM memories WHERE id = %s", (memory1_id,))
    await execute("DELETE FROM memories WHERE id = %s", (memory2_id,))
    
    logger.info("✅ All memory edge tests passed!")

async def test_vector_search():
    """Test vector search operations"""
    logger.info("Testing vector search...")
    
    try:
        # Set the user context for audit logging
        set_current_user_id(test_user_id)
        
        # Create a memory with a test embedding
        vector_dimension = 1024  # As per schema
        # Create a simple unit vector for testing
        test_vector = [1.0] + [0.0] * (vector_dimension - 1) 
        
        # Insert a test memory with an embedding and created_by
        test_memory_id_result = await execute(
            "INSERT INTO memories (content, content_embedding, created_by, updated_by) VALUES (%s, %s, %s, %s) RETURNING id",
            ("Test memory for vector search", test_vector, test_user_id, test_user_id)
        )
        test_memory_id = test_memory_id_result[0][0]
        logger.info(f"Created test memory for vector search with ID: {test_memory_id}")
        
        # Run a vector search
        search_vector = [0.8] + [0.1] * (vector_dimension - 1)  # Different but similar vector
        results = await search_memories_vector(
            query_embedding=search_vector,
            created_by=test_user_id, # Filter by created_by
            limit=5,
            similarity_threshold=0.1  # Low threshold to get some results
        )
        
        logger.info(f"Vector search returned {len(results)} results")
        assert len(results) > 0, "Vector search returned no results"
        assert any(r['id'] == uuid.UUID(test_memory_id) for r in results), "Test memory not found in search results"
        if results:
            logger.info(f"Top result similarity: {results[0]['similarity']}")
            
        # Cleanup
        await execute("DELETE FROM memories WHERE id = %s", (test_memory_id,))
        
    except Exception as e:
        logger.error(f"Vector search test encountered an error: {e}", exc_info=True)
        assert False, f"Vector search test failed: {e}"
    
    logger.info("✅ Vector search tests completed")

async def update_log_memory_change():
    """Update the log_memory_change function in the database to use application_name"""
    logger.info("Updating log_memory_change function to use application_name")
    
    sql = """
    CREATE OR REPLACE FUNCTION log_memory_change()
    RETURNS TRIGGER AS $$
    DECLARE
        app_name text;
        user_id uuid;
    BEGIN
        -- Get application_name and parse user ID from it
        BEGIN
            app_name := current_setting('application_name');
            
            -- Parse user ID if in expected format 'user:uuid'
            IF app_name LIKE 'user:%' THEN
                user_id := substring(app_name from '^user:([0-9a-fA-F-]{36})$')::uuid; -- Corrected regex and cast
            ELSE
                -- Default to NULL if not in expected format
                user_id := NULL;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            -- Handle case when application_name is not set
            user_id := NULL;
        END;
        
        INSERT INTO audit_log (table_name, record_id, operation, old_values, new_values, changed_by)
        VALUES (
            TG_TABLE_NAME,
            COALESCE(NEW.id, OLD.id),
            TG_OP,
            row_to_json(OLD),
            row_to_json(NEW),
            user_id
        );
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
    
    await execute(sql)
    logger.info("Successfully updated log_memory_change function")

async def main():
    # Setup for basic tests
    await setup_test_table()
    
    # Get or create test user and set current user ID globally
    global test_user_id
    test_user_id = await get_or_create_test_user()
    
    # Update the log_memory_change function to use application_name
    await update_log_memory_change()
    
    # Set up user context in memory - database sessions will use this automatically
    set_current_user_id(test_user_id)
    
    try:
        # Run basic tests
        await test_query_streaming()
        await test_fetch_all()
        await test_execute()
        
        # Run memory-specific tests
        await test_create_memory() # Re-enabled
        await test_memory_operations()
        await test_memory_edges()
        await test_vector_search()
        
        logger.info("✅ All database utility tests passed!")
        
    finally:
        # Always cleanup
        await cleanup_test_table()
        await close_pool() # Ensure pool is closed after tests

if __name__ == "__main__":
    asyncio.run(main())
'''
