# backend/app/tests/unit/test_database_connection.py

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestDatabaseConnection:
    """Test database connection and schema validation"""

    @pytest.mark.asyncio
    async def test_database_connection(self, test_session: AsyncSession):
        """Test that we can connect to the database"""
        # Simple query to test connection
        result = await test_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        print("✓ Database connection successful")

    @pytest.mark.asyncio
    async def test_exam_system_schema_exists(self, test_session: AsyncSession):
        """Test that the exam_system schema exists"""
        # Query to check if the schema exists
        query = text(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'exam_system'
        """
        )
        result = await test_session.execute(query)
        schema = result.scalar()
        assert schema == "exam_system", "The exam_system schema does not exist"
        print("✓ exam_system schema exists")

    @pytest.mark.asyncio
    async def test_list_tables_in_exam_system_schema(self, test_session: AsyncSession):
        """Test to list all tables in the exam_system schema"""
        # Query to get all tables in the exam_system schema
        query = text(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'exam_system'
            ORDER BY table_name
        """
        )
        result = await test_session.execute(query)
        tables = [row[0] for row in result.fetchall()]

        print(f"Tables in exam_system schema: {tables}")
        assert len(tables) > 0, "No tables found in exam_system schema"
        print("✓ Found tables in exam_system schema")

    @pytest.mark.asyncio
    async def test_can_query_users_table(self, test_session: AsyncSession):
        """Test that we can query data from the users table"""
        # Count records in the users table
        result = await test_session.execute(
            text("SELECT COUNT(*) FROM exam_system.users")
        )
        count = result.scalar()
        print(f"Users table has {count} records")
        assert count >= 0, "Could not query data from users table"  # type: ignore
        print("✓ Can query users table")
