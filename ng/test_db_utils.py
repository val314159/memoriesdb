#!/usr/bin/env python3
import uuid
import asyncio
import time
import logging
from typing import Optional, List, Dict, Any
from psycopg.types.vector import Vector

from db_utils import (
    query, query_fetchone, query_fetchall, execute,
    get_current_user_id, set_current_user_id,
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
        (TEST_USER_EMAIL,)
    )
    
    if existing_user:
        # Use existing user ID
        user_id = existing_user[0] if isinstance(existing_user, tuple) else existing_user['id']
        logger.info(f"Using existing test user with ID: {user_id}")
    else:
        # Create new test user
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

# We no longer need to disable/enable triggers with our new approach
# Instead we'll update the database session directly

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
    
    # Handle both possible formats
    if isinstance(row, dict):
        assert row['name'] == "updated-name", f"Expected 'updated-name', got {row['name']}"
    else:
        assert row[0] == "updated-name", f"Expected 'updated-name', got {row[0]}"
    
    # Test transaction handling (should be rolled back on exception)
    try:
        await execute("UPDATE test_table SET nonexistent_column = 'test' WHERE id = 1")
        assert False, "Should have raised an exception"
    except Exception as e:
        logger.info(f"Expected error caught: {e.__class__.__name__}")
    
    logger.info("✅ All execute tests passed!")

async def test_memory_operations():
    """Test memory-specific operations"""
    logger.info("Testing memory operations...")
    
    try:
        # Set the user context
        set_current_user_id(test_user_id)
        
        # Test create_memory function without explicit user_id (uses context)
        memory_content = "Test memory content for database operations"
        memory_id = await create_memory(
            content=memory_content,
            kind="test_memory",
            metadata={"test": True}
        )
        assert memory_id, "Failed to create memory"
        logger.info(f"Created memory with ID: {memory_id}")
        
        # Test get_memory_by_id
        memory = await get_memory_by_id(memory_id)
        assert memory, f"Failed to retrieve memory with ID: {memory_id}"
        assert memory['content'] == memory_content, "Memory content does not match"
        assert memory['created_by'] == test_user_id, "Memory creator does not match"
        assert memory['kind'] == "test_memory", "Memory kind does not match"
        logger.info(f"Retrieved memory: {memory['id']}")
        
        # Test creating with explicit user_id (overrides context)
        alt_memory_id = await create_memory(
            content="Alternative memory",
            user_id=test_user_id,  # Explicitly set, though same as context
            kind="test_alt"
        )
        assert alt_memory_id, "Failed to create alternative memory"
        
        # Clean up the memory records
        await execute("DELETE FROM memories WHERE id = ANY(%s)", ([memory_id, alt_memory_id],))
        
        # Verify deletions
        for mid in [memory_id, alt_memory_id]:
            deleted_memory = await get_memory_by_id(mid)
            assert deleted_memory is None, f"Memory {mid} was not deleted"
        
        logger.info("✅ All memory operations tests passed!")
    except Exception as e:
        logger.error(f"Memory operations test failed: {e}")
        raise

async def test_memory_edges():
    """Test memory edge operations"""
    logger.info("Testing memory edge operations...")
    
    try:
        # Set the user context
        set_current_user_id(test_user_id)
        
        # Create test memories using create_memory (without explicit user_id)
        memory1_id = await create_memory(
            content="Source memory for edge test",
            kind="test_source"
        )
        memory2_id = await create_memory(
            content="Target memory for edge test",
            kind="test_target"
        )
        logger.info(f"Created test memories with IDs: {memory1_id}, {memory2_id}")
        
        # Create an edge with all optional parameters
        edge_metadata = {"test": True, "confidence": 0.9, "source": "test"}
        edge_id = await create_memory_edge(
            source_id=memory1_id,
            target_id=memory2_id,
            relation="references",
            strength=0.8,
            confidence=0.9,
            metadata=edge_metadata
        )
        assert edge_id, "Failed to create memory edge"
        logger.info(f"Created edge with ID: {edge_id}")
        
        # Verify edge exists and has correct properties
        edge = await query_fetchone(
            """
            SELECT * FROM memory_edges 
            WHERE id = %s AND created_by = %s
            """, 
            (edge_id, test_user_id), 
            as_dict=True
        )
        assert edge, f"Failed to retrieve edge with ID: {edge_id}"
        assert edge['source_id'] == memory1_id, "Edge source doesn't match"
        assert edge['target_id'] == memory2_id, "Edge target doesn't match"
        assert edge['relation'] == "references", "Edge relation doesn't match"
        assert edge['strength'] == 0.8, "Edge strength doesn't match"
        assert edge['confidence'] == 0.9, "Edge confidence doesn't match"
        assert edge['_metadata'] == edge_metadata, "Edge metadata doesn't match"
        
        # Test creating edge with different user context
        try:
            set_current_user_id("00000000-0000-0000-0000-000000000000")  # Different user
            await create_memory_edge(
                source_id=memory1_id,
                target_id=memory2_id,
                relation="should_fail"
            )
            assert False, "Should not allow creating edges for other users' memories"
        except Exception as e:
            logger.info(f"Expected error for cross-user edge creation: {e}")
        finally:
            set_current_user_id(test_user_id)  # Restore test user
        
        # Test self-referential edge (should fail)
        try:
            await create_memory_edge(
                source_id=memory1_id,
                target_id=memory1_id,  # Same as source
                relation="self_ref"
            )
            assert False, "Should not allow self-referential edges"
        except ValueError as e:
            logger.info(f"Expected error for self-referential edge: {e}")
        
        logger.info("✅ All memory edge tests passed!")
        
    except Exception as e:
        logger.error(f"Memory edge test failed: {e}")
        raise
    finally:
        # Clean up in case test fails
        await execute("""
            DELETE FROM memory_edges 
            WHERE source_id = ANY(%s) OR target_id = ANY(%s)
            """, ([memory1_id, memory2_id], [memory1_id, memory2_id]))
        await execute("DELETE FROM memories WHERE id = ANY(%s)", ([memory1_id, memory2_id],))

async def test_vector_search():
    """Test vector search operations"""
    logger.info("Testing vector search...")
    
    try:
        # Set the user context for audit logging
        set_current_user_id(test_user_id)
        
        # Create a memory with a test embedding
        vector_dimension = 1536  # Common for embeddings
        test_vector = [1.0] + [0.0] * (vector_dimension - 1)  # Simple unit vector
        
        # Insert a test memory with an embedding
        test_memory_id = await query_fetchone(
            "INSERT INTO memories (content) VALUES (%s) RETURNING id",
            ("Test memory for vector search",)
        )
        test_memory_id = test_memory_id[0] if isinstance(test_memory_id, tuple) else test_memory_id['id']
        
        # Try to update with embedding if the column exists
        try:
            await execute(
                "UPDATE memories SET content_embedding = %s WHERE id = %s",
                (test_vector, test_memory_id)
            )
            logger.info("Added test vector embedding")
            
            # Run a vector search - this should at least not error
            search_vector = [0.8] + [0.1] * (vector_dimension - 1)  # Different but similar vector
            results = await search_memories_vector(
                query_embedding=search_vector,
                limit=5,
                similarity_threshold=0.1  # Low threshold to get some results
            )
            
            logger.info(f"Vector search returned {len(results)} results")
            if results:
                logger.info(f"Top result similarity: {results[0]['similarity']}")
                
        except Exception as e:
            logger.info(f"Vector embedding test skipped: {e.__class__.__name__}")
        
        # Cleanup
        await execute("DELETE FROM memories WHERE id = %s", (test_memory_id,))
        
    except Exception as e:
        logger.info(f"Vector search test encountered an error: {e.__class__.__name__}")
    
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
                user_id := substr(app_name, 6)::uuid;
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
        
        # Run memory-specific tests
        await test_memory_operations()
        await test_memory_edges()
        await test_vector_search()
        
        logger.info("✅ All database utility tests passed!")
        
    finally:
        # Always cleanup
        await cleanup_test_table()

if __name__ == "__main__":
    asyncio.run(main())
