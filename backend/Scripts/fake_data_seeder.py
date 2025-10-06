# scripts/fake_data_seeder.py

import asyncio
import os
import csv
import random
import time
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from uuid import UUID

import httpx
from faker import Faker

# --- Configuration ---
BASE_URL = "http://localhost:8000/api/v1"
AUTH_URL = f"{BASE_URL}/auth/token"
SESSION_SETUP_URL = f"{BASE_URL}/setup/session"
UPLOAD_URL = f"{BASE_URL}/uploads"
JOBS_URL = f"{BASE_URL}/jobs"

# --- Credentials ---
API_USER_EMAIL = os.getenv("API_USER_EMAIL", "admin@baze.edu.ng")
API_USER_PASSWORD = os.getenv("API_USER_PASSWORD", "demo")

# --- Data Generation Settings ---
fake = Faker()

FACULTIES = [
    {"code": "SCI", "name": "Science & Computing"},
    {"code": "LAW", "name": "Law"},
    {"code": "MNGT", "name": "Management & Social Sciences"},
]
DEPARTMENTS = [
    {"code": "CS", "name": "Computer Science", "faculty_code": "SCI"},
    {"code": "MATH", "name": "Mathematics", "faculty_code": "SCI"},
    {"code": "PHYS", "name": "Physics", "faculty_code": "SCI"},
    {"code": "ENGL", "name": "English", "faculty_code": "MNGT"},
    {"code": "BUS", "name": "Business Administration", "faculty_code": "MNGT"},
]
PROGRAMMES = [
    {
        "code": "BSC-CS",
        "name": "BSc Computer Science",
        "department_code": "CS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSC-MATH",
        "name": "BSc Mathematics",
        "department_code": "MATH",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BA-ENGL",
        "name": "BA English",
        "department_code": "ENGL",
        "degree_type": "BA",
        "duration_years": 4,
    },
    {
        "code": "BSC-PHYS",
        "name": "BSc Physics",
        "department_code": "PHYS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BBA",
        "name": "BBA",
        "department_code": "BUS",
        "degree_type": "BBA",
        "duration_years": 4,
    },
]
BUILDINGS = [
    {"code": "AH", "name": "Ahmadu Abubakar"},
    {"code": "DTL", "name": "Donald Duke"},
    {"code": "BGL", "name": "Bala Gambo Lawal"},
]

NUM_COURSES = 50
NUM_ROOMS = 20
NUM_STUDENTS = 200
NUM_STAFF = 30
NUM_UNAVAILABILITY_PER_STAFF = (0, 3)
NUM_REGISTRATIONS_PER_STUDENT = (3, 8)
NUM_INSTRUCTORS_PER_COURSE = (1, 2)


# --- Helper Functions (Unchanged) ---
def get_auth_token(client: httpx.Client) -> str:
    print("Authenticating with API...")
    try:
        response = client.post(
            AUTH_URL,
            data={"username": API_USER_EMAIL, "password": API_USER_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        token_data = response.json()
        print("Authentication successful.")
        return token_data["access_token"]
    except httpx.HTTPStatusError as e:
        print(f"Error authenticating: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during authentication: {e}")
        raise


def create_csv_file(
    filename: str, headers: List[str], data: List[Dict[str, Any]]
) -> str:
    temp_dir = "temp_seed_data"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    print(f"Generated {file_path} with {len(data)} records.")
    return file_path


# --- Data Generation Functions (Fully Aligned with Staging Schema) ---
def generate_courses_data(num: int, departments: List[Dict]) -> List[Dict[str, Any]]:
    return [
        {
            "code": f"{random.choice(departments)['code']}{fake.unique.random_int(min=101, max=499)}",
            "title": fake.catch_phrase(),
            "credit_units": fake.random_int(min=1, max=4),
            "department_code": random.choice(departments)["code"],
            "exam_duration_minutes": random.choice([60, 90, 120, 180]),
            "course_level": random.choice([100, 200, 300, 400]),
            "semester": random.randint(1, 2),
            "is_practical": fake.boolean(chance_of_getting_true=15),
            "morning_only": fake.boolean(chance_of_getting_true=10),
        }
        for _ in range(num)
    ]


def generate_rooms_data(num: int, buildings: List[Dict]) -> List[Dict[str, Any]]:
    data = []
    for _ in range(num):
        capacity = random.randint(20, 200)
        exam_capacity = capacity // 2
        # FIX: Choose the building once to ensure code and name are consistent
        chosen_building = random.choice(buildings)
        data.append(
            {
                "code": f"R{fake.unique.random_int(min=100, max=999)}",
                "name": f"{fake.random_element(elements=('Hall', 'Lab', 'Classroom'))} {fake.building_number()}",
                "building_code": chosen_building["code"],
                "building_name": chosen_building["name"],
                "capacity": capacity,
                "exam_capacity": exam_capacity,
                "has_ac": fake.boolean(chance_of_getting_true=70),
                "has_projector": fake.boolean(chance_of_getting_true=50),
                "has_computers": fake.boolean(chance_of_getting_true=20),
                "max_inv_per_room": random.choice([1, 2, 3]),
            }
        )
    return data


def generate_students_data(num: int, programmes: List[Dict]) -> List[Dict[str, Any]]:
    return [
        {
            "matric_number": f"ST{fake.unique.random_number(digits=8)}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "entry_year": fake.random_int(min=2019, max=2023),
            "programme_code": random.choice(programmes)["code"],
        }
        for _ in range(num)
    ]


def generate_staff_data(num: int, departments: List[Dict]) -> List[Dict[str, Any]]:
    return [
        {
            "staff_number": f"SF{fake.unique.random_number(digits=5)}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.unique.email(),
            "department_code": random.choice(departments)["code"],
            "staff_type": "Academic",
            "can_invigilate": fake.boolean(chance_of_getting_true=85),
            "is_instructor": True,
            "max_daily_sessions": random.choice([1, 2]),
            "max_consecutive_sessions": random.choice([1, 2]),
            "max_concurrent_exams": random.choice([1, 2, 3]),
            "max_students_per_invigilator": random.choice([25, 30, 50]),
        }
        for _ in range(num)
    ]


def generate_course_registrations_data(
    students: List[Dict], courses: List[Dict]
) -> List[Dict]:
    data = []
    course_codes = [c["code"] for c in courses]
    for student in students:
        num_registrations = random.randint(*NUM_REGISTRATIONS_PER_STUDENT)
        k = min(num_registrations, len(course_codes))
        registered_courses = random.sample(course_codes, k)
        for course_code in registered_courses:
            data.append(
                {
                    "student_matric_number": student["matric_number"],
                    "course_code": course_code,
                    "registration_type": "regular",
                }
            )
    return data


def generate_course_instructors_data(
    staff: List[Dict], courses: List[Dict]
) -> List[Dict]:
    data = []
    staff_numbers = [s["staff_number"] for s in staff if s.get("is_instructor", False)]
    if not staff_numbers:
        return []
    for course in courses:
        num_instructors = random.randint(*NUM_INSTRUCTORS_PER_COURSE)
        k = min(num_instructors, len(staff_numbers))
        assigned_staff = random.sample(staff_numbers, k)
        for staff_number in assigned_staff:
            data.append({"staff_number": staff_number, "course_code": course["code"]})
    return data


def generate_staff_unavailability_data(
    staff: List[Dict], session_start_date: date
) -> List[Dict]:
    data = []
    staff_numbers = [s["staff_number"] for s in staff if s.get("can_invigilate", False)]
    if not staff_numbers:
        return []
    for staff_number in staff_numbers:
        num_unavailable = random.randint(*NUM_UNAVAILABILITY_PER_STAFF)
        for _ in range(num_unavailable):
            unavailable_date = session_start_date + timedelta(
                days=random.randint(0, 14)
            )
            data.append(
                {
                    "staff_number": staff_number,
                    "unavailable_date": unavailable_date.isoformat(),
                    "period_name": random.choice(["Morning", "Afternoon"]),
                    "reason": fake.sentence(nb_words=4),
                }
            )
    return data


# --- Main Seeding Logic ---
async def create_exam_session(client: httpx.AsyncClient) -> tuple[UUID, date]:
    print("\nStep 1: Creating a new Exam Session...")
    start_date = date.today() + timedelta(days=30)
    end_date = start_date + timedelta(days=14)
    payload = {
        "session_name": f"Fake Exam Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "slot_generation_mode": "flexible",
        "time_slots": [
            {"name": "Morning", "start_time": "09:00:00", "end_time": "12:00:00"},
            {"name": "Afternoon", "start_time": "14:00:00", "end_time": "17:00:00"},
        ],
    }
    try:
        response = await client.post(SESSION_SETUP_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        session_id = result["data"]["session_id"]
        print(f"Exam Session created successfully. Session ID: {session_id}")
        return UUID(session_id), start_date
    except httpx.HTTPStatusError as e:
        print(f"Error creating session: {e.response.status_code} - {e.response.text}")
        raise


async def upload_file(
    client: httpx.AsyncClient, session_id: UUID, entity_type: str, file_path: str
):
    print(f"\nUploading {entity_type} data from {os.path.basename(file_path)}...")
    url = f"{UPLOAD_URL}/{session_id}/{entity_type}"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "text/csv")}
            response = await client.post(url, files=files)
            response.raise_for_status()
        upload_response = response.json()
        print(
            f"File '{entity_type}' accepted. Upload Session ID: {upload_response.get('upload_session_id')}"
        )
        # The call to monitor_job_status is now removed.
    except httpx.HTTPStatusError as e:
        print(
            f"Error uploading {entity_type}: {e.response.status_code} - {e.response.text}"
        )
        raise
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# scripts/fake_data_seeder.py


async def main():
    async with httpx.AsyncClient(timeout=60.0) as client:
        token = get_auth_token(httpx.Client())
        client.headers.update({"Authorization": f"Bearer {token}"})

        session_id, session_start_date = await create_exam_session(client)

        print("\nStep 2: Generating fake data and CSV files...")

        # Generate data in logical order
        faculties = FACULTIES
        departments = DEPARTMENTS
        programmes = PROGRAMMES
        buildings = BUILDINGS
        rooms = generate_rooms_data(NUM_ROOMS, buildings)
        courses = generate_courses_data(NUM_COURSES, departments)
        students = generate_students_data(NUM_STUDENTS, programmes)
        staff = generate_staff_data(NUM_STAFF, departments)
        course_registrations = generate_course_registrations_data(students, courses)
        course_instructors = generate_course_instructors_data(staff, courses)
        staff_unavailability = generate_staff_unavailability_data(
            staff, session_start_date
        )

        # Define all data to be uploaded with correct headers
        data_to_upload = {
            "faculties": ("faculties.csv", ["code", "name"], faculties),
            "departments": (
                "departments.csv",
                ["code", "name", "faculty_code"],
                departments,
            ),
            "programmes": (
                "programmes.csv",
                ["code", "name", "department_code", "degree_type", "duration_years"],
                programmes,
            ),
            "buildings": ("buildings.csv", ["code", "name"], buildings),
            "rooms": (
                "rooms.csv",
                [
                    "code",
                    "name",
                    "building_code",
                    "building_name",
                    "capacity",
                    "exam_capacity",
                    "has_ac",
                    "has_projector",
                    "has_computers",
                    "max_inv_per_room",
                ],
                rooms,
            ),
            "courses": (
                "courses.csv",
                [
                    "code",
                    "title",
                    "credit_units",
                    "department_code",
                    "exam_duration_minutes",
                    "course_level",
                    "semester",
                    "is_practical",
                    "morning_only",
                ],
                courses,
            ),
            "staff": (
                "staff.csv",
                [
                    "staff_number",
                    "first_name",
                    "last_name",
                    "email",
                    "department_code",
                    "staff_type",
                    "can_invigilate",
                    "is_instructor",
                    "max_daily_sessions",
                    "max_consecutive_sessions",
                    "max_concurrent_exams",
                    "max_students_per_invigilator",
                ],
                staff,
            ),
            "students": (
                "students.csv",
                [
                    "matric_number",
                    "first_name",
                    "last_name",
                    "entry_year",
                    "programme_code",
                ],
                students,
            ),
            "course_registrations": (
                "course_registrations.csv",
                ["student_matric_number", "course_code", "registration_type"],
                course_registrations,
            ),
            "course_instructors": (
                "course_instructors.csv",
                ["staff_number", "course_code"],
                course_instructors,
            ),
            "staff_unavailability": (
                "staff_unavailability.csv",
                ["staff_number", "unavailable_date", "period_name", "reason"],
                staff_unavailability,
            ),
        }

        print("\nStep 3: Uploading data to the backend in dependency order...")
        upload_order = [
            "faculties",
            "departments",
            "programmes",
            "buildings",
            "rooms",
            "courses",
            "staff",
            "students",
            "course_instructors",
            "staff_unavailability",
            "course_registrations",
        ]

        for entity_type in upload_order:
            if entity_type in data_to_upload:
                filename, headers, data = data_to_upload[entity_type]
                if not data:
                    print(f"Skipping {entity_type} as no data was generated.")
                    continue
                file_path = create_csv_file(filename, headers, data)
                await upload_file(client, session_id, entity_type, file_path)

        print("\nStep 4: All files uploaded. Triggering final processing...")
        try:
            # This uses the new endpoint you created in admin.py
            process_url = f"{BASE_URL}/admin/process-staged-data/{session_id}"
            response = await client.post(process_url)
            response.raise_for_status()
            print("Backend has successfully started final processing.")
        except httpx.HTTPStatusError as e:
            print(
                f"Error triggering final processing: {e.response.status_code} - {e.response.text}"
            )
            raise

        print("\n--- Seeding Complete! ---")
        print(f"You can now use Session ID: {session_id} in the application.")


if __name__ == "__main__":
    asyncio.run(main())
