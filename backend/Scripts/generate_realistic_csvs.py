# scripts/generate_realistic_csvs.py

import os
import csv
import random
from datetime import date, timedelta
from typing import List, Dict, Any
from faker import Faker
import collections

# --- Configuration ---
# Define the directory where you want to save the generated CSV files
OUTPUT_DIRECTORY = "realistic_csv_data_with_carryovers"

# --- Data Generation Settings ---
fake = Faker()

# --- Realistic Data Magnitudes ---
NUM_COURSES = 80
NUM_ROOMS = 40
NUM_STUDENTS = 100  # Adjusted back to 100 students
NUM_STAFF = 30
NUM_UNAVAILABILITY_PER_STAFF = (0, 3)
NUM_REGISTRATIONS_PER_STUDENT = (5, 8)
NUM_INSTRUCTORS_PER_COURSE = (1, 2)
CARRYOVER_REGISTRATION_CHANCE = 0.2  # 20% chance for a registration to be a carryover

# --- Expanded Static Data ---
FACULTIES = [
    {"code": "SCI", "name": "Science & Computing"},
    {"code": "MNGT", "name": "Management & Social Sciences"},
    {"code": "LAW", "name": "Law"},
]

DEPARTMENTS = [
    # SCI
    {"code": "CSC", "name": "Computer Science", "faculty_code": "SCI"},
    {"code": "MCS", "name": "Mathematics & Statistics", "faculty_code": "SCI"},
    {"code": "PHY", "name": "Physics", "faculty_code": "SCI"},
    {"code": "BIO", "name": "Biological Sciences", "faculty_code": "SCI"},
    # MNGT
    {"code": "ACC", "name": "Accounting", "faculty_code": "MNGT"},
    {"code": "BUS", "name": "Business Administration", "faculty_code": "MNGT"},
    {"code": "ECO", "name": "Economics", "faculty_code": "MNGT"},
    # LAW
    {"code": "PL", "name": "Public Law", "faculty_code": "LAW"},
]

PROGRAMMES = [
    # CSC
    {
        "code": "BSc-CS",
        "name": "BSc Computer Science",
        "department_code": "CSC",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-CY",
        "name": "BSc Cyber Security",
        "department_code": "CSC",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-IT",
        "name": "BSc Information Technology",
        "department_code": "CSC",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    # MCS
    {
        "code": "BSc-MTH",
        "name": "BSc Mathematics",
        "department_code": "MCS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-STA",
        "name": "BSc Statistics",
        "department_code": "MCS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    # PHY
    {
        "code": "BSc-PHY",
        "name": "BSc Physics",
        "department_code": "PHY",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    # BIO
    {
        "code": "BSc-BIO",
        "name": "BSc Biology",
        "department_code": "BIO",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-MB",
        "name": "BSc Microbiology",
        "department_code": "BIO",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    # ACC
    {
        "code": "BSc-ACC",
        "name": "BSc Accounting",
        "department_code": "ACC",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    # BUS
    {
        "code": "BSc-BUS",
        "name": "BSc Business Administration",
        "department_code": "BUS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-MKT",
        "name": "BSc Marketing",
        "department_code": "BUS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-PA",
        "name": "BSc Public Administration",
        "department_code": "BUS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    # ECO
    {
        "code": "BSc-ECO",
        "name": "BSc Economics",
        "department_code": "ECO",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-IR",
        "name": "BSc International Relations",
        "department_code": "ECO",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    # LAW
    {
        "code": "LLB",
        "name": "Bachelor of Laws",
        "department_code": "PL",
        "degree_type": "LLB",
        "duration_years": 5,
    },
]

BUILDINGS = [
    {"code": "AH", "name": "Ahmadu Abubakar Block"},
    {"code": "DTL", "name": "Donald Duke IT Centre"},
    {"code": "BGL", "name": "Bala Gambo Lawal Hall"},
    {"code": "MKO", "name": "M.K.O. Abiola Lecture Complex"},
]

# Create a mapping from programme code to its department for quick lookup
PROGRAMME_TO_DEPT_MAP = {p["code"]: p["department_code"] for p in PROGRAMMES}


# --- Helper Function ---
def create_csv_file(
    output_dir: str, filename: str, headers: List[str], data: List[Dict[str, Any]]
):
    """Creates a CSV file in the specified output directory."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    print(f"Successfully generated {file_path} with {len(data)} records.")


# --- Data Generation Functions (with enhanced realism) ---
def generate_courses_data(num: int, departments: List[Dict]) -> List[Dict[str, Any]]:
    """Generates a list of courses with guaranteed unique codes."""
    generated_codes = set()
    data = []
    while len(data) < num:
        dept = random.choice(departments)
        code = f"{dept['code']}{fake.unique.random_int(min=101, max=499)}"
        if code not in generated_codes:
            generated_codes.add(code)
            data.append(
                {
                    "code": code,
                    "title": fake.catch_phrase(),
                    "credit_units": fake.random_int(min=1, max=4),
                    "department_code": dept["code"],
                    "exam_duration_minutes": random.choice([60, 90, 120, 180]),
                    "course_level": random.choice([100, 200, 300, 400, 500]),
                    "semester": random.randint(1, 2),
                    "is_practical": fake.boolean(chance_of_getting_true=15),
                    "morning_only": fake.boolean(chance_of_getting_true=10),
                }
            )
    return data


def generate_rooms_data(num: int, buildings: List[Dict]) -> List[Dict[str, Any]]:
    """Generates a list of rooms with unique codes."""
    return [
        {
            "code": f"R{fake.unique.random_int(min=100, max=999)}",
            "name": f"{fake.random_element(elements=('Hall', 'Lab', 'Classroom'))} {fake.building_number()}",
            "building_code": (chosen_building := random.choice(buildings))["code"],
            "building_name": chosen_building["name"],
            "capacity": (capacity := random.randint(30, 250)),
            "exam_capacity": capacity // 2,
            "has_ac": fake.boolean(chance_of_getting_true=70),
            "has_projector": fake.boolean(chance_of_getting_true=50),
            "has_computers": fake.boolean(chance_of_getting_true=20),
            "max_inv_per_room": random.choice([1, 2, 3, 4]),
        }
        for _ in range(num)
    ]


def generate_students_data(num: int, programmes: List[Dict]) -> List[Dict[str, Any]]:
    """Generates student data, including internal fields for realistic course registration."""
    data = []
    current_year = date.today().year
    for _ in range(num):
        programme = random.choice(programmes)
        entry_year = current_year - random.randint(0, programme["duration_years"] - 1)
        level = max(
            100, ((current_year - entry_year) * 100)
        )  # e.g., 2023 entry, 2025 current -> (2)*100 = 200 level

        data.append(
            {
                # Data for CSV
                "matric_number": f"ST{fake.unique.random_number(digits=8)}",
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "entry_year": entry_year,
                "programme_code": programme["code"],
                # Internal data for generating realistic registrations
                "_internal_level": level,
                "_internal_dept_code": PROGRAMME_TO_DEPT_MAP[programme["code"]],
            }
        )
    return data


def generate_staff_data(num: int, departments: List[Dict]) -> List[Dict[str, Any]]:
    """Generates a list of staff members."""
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
    """Generates course registrations with realistic logic and some carryovers."""
    registrations = []
    # Pre-sort courses by department and level for efficiency
    courses_by_dept_level = collections.defaultdict(list)
    for c in courses:
        courses_by_dept_level[(c["department_code"], c["course_level"])].append(
            c["code"]
        )
    all_course_codes = [c["code"] for c in courses]

    for student in students:
        num_registrations = random.randint(*NUM_REGISTRATIONS_PER_STUDENT)
        student_level = student["_internal_level"]
        student_dept = student["_internal_dept_code"]

        # Find courses matching the student's department and levels around their current level
        # This makes it more likely to find suitable courses even with fewer students
        relevant_course_levels = [
            lvl for lvl in [100, 200, 300, 400, 500] if abs(lvl - student_level) <= 100
        ]

        possible_major_courses = []
        for lvl in relevant_course_levels:
            possible_major_courses.extend(
                courses_by_dept_level.get((student_dept, lvl), [])
            )

        registered_codes = set()

        # Prioritize major/relevant courses (aim for ~70-80% majors)
        num_majors_to_add = min(
            len(possible_major_courses),
            round(num_registrations * random.uniform(0.7, 0.8)),
        )
        if num_majors_to_add > 0:
            registered_codes.update(
                random.sample(possible_major_courses, num_majors_to_add)
            )

        # Fill remaining slots with electives (any course not already taken)
        remaining_slots = num_registrations - len(registered_codes)
        if remaining_slots > 0:
            possible_electives = [
                c for c in all_course_codes if c not in registered_codes
            ]
            num_electives_to_add = min(len(possible_electives), remaining_slots)
            if num_electives_to_add > 0:
                registered_codes.update(
                    random.sample(possible_electives, num_electives_to_add)
                )

        for course_code in registered_codes:
            registration_type = (
                "carryover"
                if random.random() < CARRYOVER_REGISTRATION_CHANCE
                else "regular"
            )
            registrations.append(
                {
                    "student_matric_number": student["matric_number"],
                    "course_code": course_code,
                    "registration_type": registration_type,
                }
            )
    return registrations


def generate_course_instructors_data(
    staff: List[Dict], courses: List[Dict]
) -> List[Dict]:
    """Assigns instructors to courses, prioritizing staff from the same department."""
    assignments = []
    # Group available instructors by department
    instructors_by_dept = collections.defaultdict(list)
    all_instructor_numbers = []
    for s in staff:
        if s.get("is_instructor"):
            instructors_by_dept[s["department_code"]].append(s["staff_number"])
            all_instructor_numbers.append(s["staff_number"])

    if not all_instructor_numbers:
        print(
            "Warning: No instructors found among staff. Course instructor assignments will be empty."
        )
        return []

    for course in courses:
        course_dept = course["department_code"]
        # Prefer instructors from the same department
        possible_instructors = instructors_by_dept.get(course_dept, [])

        # If no instructors in the same department, or not enough, fallback to any instructor
        if (
            not possible_instructors
            or len(possible_instructors) < NUM_INSTRUCTORS_PER_COURSE[0]
        ):
            # Try to supplement with other instructors if needed
            other_instructors = [
                sn for sn in all_instructor_numbers if sn not in possible_instructors
            ]
            possible_instructors.extend(
                random.sample(
                    other_instructors,
                    min(len(other_instructors), NUM_INSTRUCTORS_PER_COURSE[1]),
                )
            )

        num_instructors = min(
            len(possible_instructors), random.randint(*NUM_INSTRUCTORS_PER_COURSE)
        )
        if num_instructors > 0:
            assigned_staff = random.sample(possible_instructors, num_instructors)
            for staff_number in assigned_staff:
                assignments.append(
                    {"staff_number": staff_number, "course_code": course["code"]}
                )
    return assignments


def generate_staff_unavailability_data(
    staff: List[Dict], session_start_date: date
) -> List[Dict]:
    """Generates staff unavailability records."""
    data = []
    invigilators = [s["staff_number"] for s in staff if s.get("can_invigilate")]
    if not invigilators:
        print(
            "Warning: No invigilators found among staff. Staff unavailability will be empty."
        )
        return []

    for staff_number in invigilators:
        for _ in range(random.randint(*NUM_UNAVAILABILITY_PER_STAFF)):
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


# --- Main CSV Generation Logic ---
def main():
    """Main function to generate all necessary CSV files."""
    session_start_date = date.today() + timedelta(days=30)
    print(f"Generating realistic fake data in '{OUTPUT_DIRECTORY}' directory...")

    # Generate data in a logical dependency order
    faculties = FACULTIES
    departments = DEPARTMENTS
    programmes = PROGRAMMES
    buildings = BUILDINGS
    rooms = generate_rooms_data(NUM_ROOMS, buildings)
    courses = generate_courses_data(NUM_COURSES, departments)
    students_with_internal_data = generate_students_data(NUM_STUDENTS, programmes)
    staff = generate_staff_data(NUM_STAFF, departments)
    course_registrations = generate_course_registrations_data(
        students_with_internal_data, courses
    )
    course_instructors = generate_course_instructors_data(staff, courses)
    staff_unavailability = generate_staff_unavailability_data(staff, session_start_date)

    # Prepare student data for CSV (remove internal fields)
    students_for_csv = [
        {k: v for k, v in s.items() if not k.startswith("_internal")}
        for s in students_with_internal_data
    ]

    # Map entity data to filenames, headers, and the generated data
    data_to_generate = {
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
            students_for_csv,
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

    # Create a CSV file for each data mapping
    for entity_type, (filename, headers, data) in data_to_generate.items():
        if not data:
            print(f"Skipping {entity_type} as no data was generated.")
            continue
        create_csv_file(OUTPUT_DIRECTORY, filename, headers, data)

    print("\n--- CSV Generation Complete! ---")
    print(f"All files have been saved in the '{OUTPUT_DIRECTORY}' directory.")


if __name__ == "__main__":
    main()
