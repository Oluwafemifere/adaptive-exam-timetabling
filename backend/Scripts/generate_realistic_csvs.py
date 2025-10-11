# scripts/generate_realistic_csvs.py

import os
import csv
import random
import argparse
from datetime import date, timedelta
from typing import List, Dict, Any
from faker import Faker
import collections

# --- Configuration ---
# This will be set dynamically based on magnitude
# OUTPUT_DIRECTORY = "realistic_csv_data"

# --- Data Generation Settings ---
fake = Faker()

# --- Realistic Data Magnitudes ---
PROBLEM_SIZES = {
    1: {
        "name": "tiny",
        "NUM_COURSES": 20,
        "NUM_ROOMS": 10,
        "NUM_STUDENTS": 50,
        "NUM_STAFF": 15,
    },
    2: {
        "name": "small",
        "NUM_COURSES": 80,
        "NUM_ROOMS": 40,
        "NUM_STUDENTS": 250,
        "NUM_STAFF": 30,
    },
    3: {
        "name": "medium",
        "NUM_COURSES": 250,
        "NUM_ROOMS": 75,
        "NUM_STUDENTS": 1000,
        "NUM_STAFF": 60,
    },
    4: {
        "name": "large",
        "NUM_COURSES": 500,
        "NUM_ROOMS": 120,
        "NUM_STUDENTS": 4000,
        "NUM_STAFF": 100,
    },
    5: {
        "name": "huge",
        "NUM_COURSES": 1000,
        "NUM_ROOMS": 200,
        "NUM_STUDENTS": 10000,
        "NUM_STAFF": 180,
    },
}

# Common settings across all magnitudes
COMMON_SETTINGS = {
    "NUM_UNAVAILABILITY_PER_STAFF": (0, 3),
    "NUM_REGISTRATIONS_PER_STUDENT": (5, 8),
    "NUM_INSTRUCTORS_PER_COURSE": (1, 2),
    "CARRYOVER_REGISTRATION_CHANCE": 0.15,
    "MULTI_DEPT_COURSE_CHANCE": 0.1,  # 10% chance for a course to be cross-departmental
}

# --- Expanded Static Data ---
FACULTIES = [
    {"code": "SCI", "name": "Science & Computing"},
    {"code": "MNGT", "name": "Management & Social Sciences"},
    {"code": "LAW", "name": "Law"},
]

DEPARTMENTS = [
    {"code": "CSC", "name": "Computer Science", "faculty_code": "SCI"},
    {"code": "MCS", "name": "Mathematics & Statistics", "faculty_code": "SCI"},
    {"code": "PHY", "name": "Physics", "faculty_code": "SCI"},
    {"code": "BIO", "name": "Biological Sciences", "faculty_code": "SCI"},
    {"code": "ACC", "name": "Accounting", "faculty_code": "MNGT"},
    {"code": "BUS", "name": "Business Administration", "faculty_code": "MNGT"},
    {"code": "ECO", "name": "Economics", "faculty_code": "MNGT"},
    {"code": "PL", "name": "Public Law", "faculty_code": "LAW"},
]

PROGRAMMES = [
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
        "code": "BSc-MTH",
        "name": "BSc Mathematics",
        "department_code": "MCS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-PHY",
        "name": "BSc Physics",
        "department_code": "PHY",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-BIO",
        "name": "BSc Biology",
        "department_code": "BIO",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-ACC",
        "name": "BSc Accounting",
        "department_code": "ACC",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-BUS",
        "name": "BSc Business Administration",
        "department_code": "BUS",
        "degree_type": "BSc",
        "duration_years": 4,
    },
    {
        "code": "BSc-ECO",
        "name": "BSc Economics",
        "department_code": "ECO",
        "degree_type": "BSc",
        "duration_years": 4,
    },
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

ROOM_TYPES = ["Lecture Hall", "Classroom", "Computer Lab", "Science Lab", "Auditorium"]
ACCESSIBILITY_FEATURES = [
    "Wheelchair Ramp",
    "Accessible Restroom",
    "Elevator Access",
    "Braille Signage",
]

# --- Mappings for quick lookup ---
PROGRAMME_TO_DEPT_MAP = {p["code"]: p["department_code"] for p in PROGRAMMES}
DEPT_TO_FACULTY_MAP = {d["code"]: d["faculty_code"] for d in DEPARTMENTS}


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


# --- Data Generation Functions (Updated to match validation schemas) ---
def generate_courses_data(num: int, departments: List[Dict]) -> List[Dict[str, Any]]:
    """
    Generates a list of courses.
    An internal `_internal_dept_code` field is added for linking purposes.
    """
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
                    "exam_duration_minutes": random.choice([60, 90, 120, 180]),
                    "course_level": random.choice([100, 200, 300, 400, 500]),
                    "semester": random.randint(1, 2),
                    "is_practical": fake.boolean(chance_of_getting_true=15),
                    "morning_only": fake.boolean(chance_of_getting_true=10),
                    "_internal_dept_code": dept["code"],
                }
            )
    return data


def generate_buildings_data(
    buildings: List[Dict], faculties: List[Dict]
) -> List[Dict[str, Any]]:
    """Generates building data, optionally linking some to faculties."""
    data = []
    faculty_codes = [f["code"] for f in faculties]
    for b in buildings:
        new_b = b.copy()
        if random.random() < 0.3:
            new_b["faculty_code"] = random.choice(faculty_codes)
        else:
            new_b["faculty_code"] = ""
        data.append(new_b)
    return data


def generate_rooms_data(num: int, buildings: List[Dict]) -> List[Dict[str, Any]]:
    """Generates a list of rooms with unique codes, matching the new schema."""
    return [
        {
            "code": f"R{fake.unique.random_int(min=100, max=999)}",
            "name": f"{fake.random_element(elements=('Hall', 'Lab', 'Classroom'))} {fake.building_number()}",
            "building_code": random.choice(buildings)["code"],
            "capacity": (capacity := random.randint(30, 250)),
            "exam_capacity": max(10, capacity // 2),
            "has_ac": fake.boolean(chance_of_getting_true=70),
            "has_projector": fake.boolean(chance_of_getting_true=50),
            "has_computers": fake.boolean(chance_of_getting_true=20),
            "max_inv_per_room": random.choice([1, 2, 3, 4]),
            "room_type_code": random.choice(ROOM_TYPES),
            "floor_number": random.randint(0, 5),
            "accessibility_features": ",".join(
                random.sample(ACCESSIBILITY_FEATURES, k=random.randint(0, 2))
            ),
            "notes": fake.sentence() if random.random() < 0.2 else "",
        }
        for _ in range(num)
    ]


def generate_students_data(num: int, programmes: List[Dict]) -> List[Dict[str, Any]]:
    """Generates student data, now including email."""
    data = []
    current_year = date.today().year
    for i in range(num):
        programme = random.choice(programmes)
        entry_year = current_year - random.randint(0, programme["duration_years"] - 1)
        level = max(100, ((current_year - entry_year) * 100))
        first_name = fake.first_name()
        last_name = fake.last_name()
        data.append(
            {
                "matric_number": f"ST{20200000 + i}",
                "first_name": first_name,
                "last_name": last_name,
                "email": f"{first_name.lower()}.{last_name.lower()}{i}@university.edu",
                "entry_year": entry_year,
                "programme_code": programme["code"],
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
    students: List[Dict], courses: List[Dict], config: Dict
) -> List[Dict]:
    """Generates course registrations with realistic logic and some carryovers."""
    registrations = []
    courses_by_dept_level = collections.defaultdict(list)
    for c in courses:
        courses_by_dept_level[(c["_internal_dept_code"], c["course_level"])].append(
            c["code"]
        )
    all_course_codes = [c["code"] for c in courses]

    for student in students:
        num_registrations = random.randint(*config["NUM_REGISTRATIONS_PER_STUDENT"])
        student_level = student["_internal_level"]
        student_dept = student["_internal_dept_code"]

        relevant_course_levels = [
            lvl for lvl in [100, 200, 300, 400, 500] if abs(lvl - student_level) <= 100
        ]
        possible_major_courses = []
        for lvl in relevant_course_levels:
            possible_major_courses.extend(
                courses_by_dept_level.get((student_dept, lvl), [])
            )

        registered_codes = set()
        num_majors_to_add = min(
            len(possible_major_courses),
            round(num_registrations * random.uniform(0.7, 0.8)),
        )
        if num_majors_to_add > 0:
            registered_codes.update(
                random.sample(possible_major_courses, num_majors_to_add)
            )

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
                if random.random() < config["CARRYOVER_REGISTRATION_CHANCE"]
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
    staff: List[Dict], courses: List[Dict], config: Dict
) -> List[Dict]:
    """Assigns instructors to courses, prioritizing staff from the same department."""
    assignments = []
    instructors_by_dept = collections.defaultdict(list)
    all_instructor_numbers = []
    for s in staff:
        if s.get("is_instructor"):
            instructors_by_dept[s["department_code"]].append(s["staff_number"])
            all_instructor_numbers.append(s["staff_number"])

    if not all_instructor_numbers:
        return []

    for course in courses:
        course_dept = course["_internal_dept_code"]
        possible_instructors = instructors_by_dept.get(course_dept, [])
        if (
            not possible_instructors
            or len(possible_instructors) < config["NUM_INSTRUCTORS_PER_COURSE"][0]
        ):
            other_instructors = [
                sn for sn in all_instructor_numbers if sn not in possible_instructors
            ]
            possible_instructors.extend(
                random.sample(
                    other_instructors,
                    min(
                        len(other_instructors), config["NUM_INSTRUCTORS_PER_COURSE"][1]
                    ),
                )
            )

        num_instructors = min(
            len(possible_instructors),
            random.randint(*config["NUM_INSTRUCTORS_PER_COURSE"]),
        )
        if num_instructors > 0:
            assigned_staff = random.sample(possible_instructors, num_instructors)
            for staff_number in assigned_staff:
                assignments.append(
                    {"staff_number": staff_number, "course_code": course["code"]}
                )
    return assignments


def generate_course_departments_data(
    courses: List[Dict], departments: List[Dict], config: Dict
) -> List[Dict]:
    """Assigns courses to their primary department and occasionally others."""
    assignments = []
    department_codes = [d["code"] for d in departments]
    for course in courses:
        primary_dept = course["_internal_dept_code"]
        assignments.append(
            {"course_code": course["code"], "department_code": primary_dept}
        )
        if random.random() < config["MULTI_DEPT_COURSE_CHANCE"]:
            other_depts = [d for d in department_codes if d != primary_dept]
            if other_depts:
                assignments.append(
                    {
                        "course_code": course["code"],
                        "department_code": random.choice(other_depts),
                    }
                )
    return assignments


def generate_course_faculties_data(
    course_department_assignments: List[Dict],
) -> List[Dict]:
    """Assigns courses to faculties based on their department assignments."""
    assignments_set = set()
    for assignment in course_department_assignments:
        faculty = DEPT_TO_FACULTY_MAP.get(assignment["department_code"])
        if faculty:
            assignments_set.add((assignment["course_code"], faculty))
    return [{"course_code": c, "faculty_code": f} for c, f in assignments_set]


def generate_staff_unavailability_data(
    staff: List[Dict], session_start_date: date, config: Dict
) -> List[Dict]:
    """Generates staff unavailability records."""
    data = []
    invigilators = [s["staff_number"] for s in staff if s.get("can_invigilate")]
    if not invigilators:
        return []

    for staff_number in invigilators:
        for _ in range(random.randint(*config["NUM_UNAVAILABILITY_PER_STAFF"])):
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


def main(magnitude: int):
    """Main function to generate all necessary CSV files for a given magnitude."""
    if magnitude not in PROBLEM_SIZES:
        print(
            f"Error: Invalid magnitude '{magnitude}'. Please choose from {list(PROBLEM_SIZES.keys())}."
        )
        return

    config = {**PROBLEM_SIZES[magnitude], **COMMON_SETTINGS}
    output_dir = f"realistic_csv_data/magnitude_{magnitude}_{config['name']}"

    session_start_date = date.today() + timedelta(days=30)
    print(
        f"Generating data for magnitude {magnitude} ({config['name']}) in '{output_dir}' directory..."
    )

    # Generate data in a logical dependency order
    faculties = FACULTIES
    departments = DEPARTMENTS
    programmes = PROGRAMMES
    buildings = generate_buildings_data(BUILDINGS, faculties)
    rooms = generate_rooms_data(config["NUM_ROOMS"], buildings)
    courses_with_internal_data = generate_courses_data(
        config["NUM_COURSES"], departments
    )
    students_with_internal_data = generate_students_data(
        config["NUM_STUDENTS"], programmes
    )
    staff = generate_staff_data(config["NUM_STAFF"], departments)

    course_registrations = generate_course_registrations_data(
        students_with_internal_data, courses_with_internal_data, config
    )
    course_instructors = generate_course_instructors_data(
        staff, courses_with_internal_data, config
    )
    staff_unavailability = generate_staff_unavailability_data(
        staff, session_start_date, config
    )
    course_departments = generate_course_departments_data(
        courses_with_internal_data, departments, config
    )
    course_faculties = generate_course_faculties_data(course_departments)

    # Prepare data for CSVs (remove internal fields)
    students_for_csv = [
        {k: v for k, v in s.items() if not k.startswith("_internal")}
        for s in students_with_internal_data
    ]
    courses_for_csv = [
        {k: v for k, v in c.items() if not k.startswith("_internal")}
        for c in courses_with_internal_data
    ]

    # HEADERS MUST PRECISELY MATCH THE VALIDATION SCHEMA
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
        "buildings": ("buildings.csv", ["code", "name", "faculty_code"], buildings),
        "rooms": (
            "rooms.csv",
            [
                "code",
                "name",
                "building_code",
                "capacity",
                "exam_capacity",
                "has_ac",
                "has_projector",
                "has_computers",
                "max_inv_per_room",
                "room_type_code",
                "floor_number",
                "accessibility_features",
                "notes",
            ],
            rooms,
        ),
        "courses": (
            "courses.csv",
            [
                "code",
                "title",
                "credit_units",
                "exam_duration_minutes",
                "course_level",
                "semester",
                "is_practical",
                "morning_only",
            ],
            courses_for_csv,
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
                "email",
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
        "course_departments": (
            "course_departments.csv",
            ["course_code", "department_code"],
            course_departments,
        ),
        "course_faculties": (
            "course_faculties.csv",
            ["course_code", "faculty_code"],
            course_faculties,
        ),
    }

    # Create a CSV file for each data mapping
    for entity_type, (filename, headers, data) in data_to_generate.items():
        if not data:
            print(f"Skipping {entity_type} as no data was generated.")
            continue
        prepared_data = [{h: row.get(h, "") for h in headers} for row in data]
        create_csv_file(output_dir, filename, headers, prepared_data)

    print("\n--- CSV Generation Complete! ---")
    print(f"All files have been saved in the '{output_dir}' directory.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate realistic CSV data for the exam timetabling system."
    )
    parser.add_argument(
        "magnitude",
        type=int,
        choices=PROBLEM_SIZES.keys(),
        help="The magnitude of the problem size (1=tiny, 2=small, 3=medium, 4=large, 5=huge).",
    )
    args = parser.parse_args()
    main(args.magnitude)
