# backend/app/tests/api/vv1/test_uploads.py

import pytest
import io
import uuid
import asyncio  # Import asyncio for sleeping
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Import the actual data models you want to verify
from app.models import FileUploadSession, User, AcademicSession, Faculty, Department

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


# NEW: Helper function to wait for the background task to finish
async def wait_for_upload_completion(
    db: AsyncSession, upload_session_id: uuid.UUID, timeout: int = 10
) -> FileUploadSession:
    """Polls the database until the upload session is no longer 'processing'."""
    for _ in range(timeout):
        await asyncio.sleep(1)  # Wait for 1 second before polling again
        stmt = select(FileUploadSession).where(
            FileUploadSession.id == upload_session_id
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record and record.status != "processing":
            return record
    raise TimeoutError(
        f"Upload session {upload_session_id} did not complete within {timeout} seconds."
    )


@pytest.mark.parametrize(
    "entity_type, model_class, csv_content, expected_data",
    [
        (
            "faculties",
            Faculty,
            "faculty_name,faculty_code,active\nFaculty of Science,FOS,true\nFaculty of Arts,FOA,false",
            [
                {"name": "Faculty of Science", "code": "FOS"},
                {"name": "Faculty of Arts", "code": "FOA"},
            ],
        ),
        (
            "departments",
            Department,
            "department_name,department_code,faculty_code\nComputer Science,CSC,SCI-FAC\nHistory,HIS,ART-FAC",
            [
                {"name": "Computer Science", "code": "CSC"},
                {"name": "History", "code": "HIS"},
            ],
        ),
    ],
)
async def test_upload_and_verify_seeding(
    client: AsyncClient,
    db_session: AsyncSession,
    complete_test_data: Dict[str, Any],
    entity_type: str,
    model_class: Any,
    csv_content: str,
    expected_data: list,
):
    """
    Tests successful upload and VERIFIES that the data is seeded into the target table.
    """
    # FIX: Dynamically insert correct foreign keys into test data
    if entity_type == "departments":
        sci_fac_code = complete_test_data["faculty_sci"].code
        art_fac_code = complete_test_data["faculty_art"].code
        csv_content = csv_content.replace("SCI-FAC", sci_fac_code)
        csv_content = csv_content.replace("ART-FAC", art_fac_code)

    # 1. Prepare CSV data
    file_to_upload = io.BytesIO(csv_content.encode("utf-8"))
    filename = f"test_{entity_type}.csv"

    # 2. Make API request
    response = await client.post(
        f"/api/v1/uploads/?entity_type={entity_type}",
        files={"file": (filename, file_to_upload, "text/csv")},
    )

    # 3. Assert HTTP response
    assert response.status_code == 202
    response_data = response.json()
    upload_session_id = uuid.UUID(response_data["upload_session_id"])

    # --- FIX: COMMIT THE TRANSACTION ---
    # Commit the session to ensure the 'processing' record is visible to the worker
    # and to allow our polling function to see the worker's subsequent updates.
    await db_session.commit()

    # 4. WAIT for the background task to complete and get the final record
    final_record = await wait_for_upload_completion(db_session, upload_session_id)

    # 5. Assert the upload session completed successfully
    assert (
        final_record.status == "completed"
    ), f"Upload failed with errors: {final_record.validation_errors}"

    # --- VERIFICATION STEP ---
    # 6. Query the target table to verify the data was inserted
    for item in expected_data:
        stmt = select(model_class).where(model_class.code == item["code"])
        result = await db_session.execute(stmt)
        seeded_record = result.scalar_one_or_none()

        assert (
            seeded_record is not None
        ), f"Record with code {item['code']} was not found in the database."
        assert seeded_record.name == item["name"]

    print(
        f"\nSuccessfully verified that {len(expected_data)} records were seeded for entity '{entity_type}'."
    )


# The other tests can remain as they are, as they test failure cases and session ID handling
async def test_upload_csv_success_with_session(
    client: AsyncClient,
    db_session: AsyncSession,
    complete_test_data: Dict[str, Any],
):
    """
    Tests successful upload for an entity that REQUIRES an academic session ID.
    """
    academic_session: AcademicSession = complete_test_data["academic_session"]
    entity_type = "course_registrations"
    csv_content = "student_matric_number,course_code\nSTUDENT001,COURSE101"
    file_to_upload = io.BytesIO(csv_content.encode("utf-8"))
    filename = "test_registrations.csv"

    # Make API request, providing the academic_session_id
    response = await client.post(
        f"/api/v1/uploads/?entity_type={entity_type}&academic_session_id={academic_session.id}",
        files={"file": (filename, file_to_upload, "text/csv")},
    )

    assert response.status_code == 202
    upload_session_id = uuid.UUID(response.json()["upload_session_id"])

    # Commit before checking the state from a different perspective (though not strictly necessary here)
    await db_session.commit()

    # Assert database state (initial check)
    stmt = select(FileUploadSession).where(FileUploadSession.id == upload_session_id)
    result = await db_session.execute(stmt)
    record = result.scalar_one()

    assert record.status == "processing"
    assert record.upload_type == entity_type
    assert record.session_id == academic_session.id


async def test_upload_unknown_entity_type(client: AsyncClient):
    """
    Tests that the API correctly rejects an upload for an unknown entity type.
    """
    entity_type = "dragons"
    csv_content = "name,color\nSmaug,Gold"
    file_to_upload = io.BytesIO(csv_content.encode("utf-8"))
    filename = "test_dragons.csv"

    response = await client.post(
        f"/api/v1/uploads/?entity_type={entity_type}",
        files={"file": (filename, file_to_upload, "text/csv")},
    )

    assert response.status_code == 400
    assert "Invalid entity_type 'dragons'" in response.json()["detail"]


async def test_upload_wrong_file_type(client: AsyncClient):
    """
    Tests that the API rejects files that are not CSV.
    """
    entity_type = "faculties"
    file_content = "This is just a plain text file."
    file_to_upload = io.BytesIO(file_content.encode("utf-8"))
    filename = "test_faculties.txt"

    response = await client.post(
        f"/api/v1/uploads/?entity_type={entity_type}",
        files={"file": (filename, file_to_upload, "text/plain")},
    )

    assert response.status_code == 400
    assert (
        "Invalid file type. Only .csv files are accepted" in response.json()["detail"]
    )
