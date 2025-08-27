#!/usr/bin/env python3
# scripts/seed_data.py

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Any, Dict, Tuple
from datetime import datetime, date, time
import argparse

# Ensure backend in path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select  # NEW: async ORM query pattern [stackoverflow]
from sqlalchemy.orm import Session as SyncSession  # for run_sync callbacks

from app.database import db_manager, init_db
from app.models import (
    User, UserRole, UserRoleAssignment,
    Building, RoomType, Room,
    AcademicSession, Faculty, Department, Programme,
    TimeSlot, ConstraintCategory, ConstraintRule,
    Course, Student, CourseRegistration, Exam
)
from services.data_validation import (CSVProcessor, DataMapper, DataIntegrityChecker)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class DatabaseSeeder:
    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url
        self.csv_processor = CSVProcessor()
        self._setup_csv_schemas()

    def _setup_csv_schemas(self) -> None:
        # Register CSV schemas for key entities...
        self.csv_processor.register_schema("academic_sessions", {
            "required_columns": ["name", "start_date", "end_date", "semester_system"],
            "column_mappings": {"session_name": "name", "start": "start_date", "end": "end_date"},
            "transformers": {
                "start_date": lambda x: date.fromisoformat(str(x)) if x else None,
                "end_date":   lambda x: date.fromisoformat(str(x)) if x else None
            }
        })
        # faculties
        self.csv_processor.register_schema("faculties", {
            "required_columns": ["name", "code"],
            "column_mappings": {"faculty_name": "name", "faculty_code": "code"},
            "transformers": {"code": lambda x: str(x).upper(), "name": lambda x: str(x).strip()}
        })
        # departments
        self.csv_processor.register_schema("departments", {
            "required_columns": ["name", "code", "faculty_code"],
            "column_mappings": {"department_name": "name", "department_code": "code"},
            "transformers": {"code": lambda x: str(x).upper(), "name": lambda x: str(x).strip()}
        })
        # programmes
        self.csv_processor.register_schema("programmes", {
            "required_columns": ["name", "code", "department_code", "degree_type", "duration_years"],
            "column_mappings": {"programme_name": "name", "programme_code": "code"},
            "transformers": {"code": lambda x: str(x).upper(), "duration_years": lambda x: int(x)}
        })
        # ...repeat for courses, students, rooms, time_slots
        logger.info("CSV schemas configured")

    async def seed_all(self, drop_existing: bool = False, sample_data: bool = True) -> None:
        init_db(self.database_url, create_tables=True) # type: ignore
        if drop_existing:
            await db_manager.drop_all_tables()
            await db_manager.create_all_tables()
        await self._seed_users_and_roles()
        await self._seed_infrastructure()
        await self._seed_academic_structure()
        await self._seed_constraint_system()
        await self._seed_time_slots()
        if sample_data:
            await self._seed_sample_data()
        logger.info("Seeding complete")

    async def _seed_users_and_roles(self) -> None:
        async with db_manager.get_db_transaction() as session:
            roles_def = [
                ("super_admin", "System Super Admin", {"*": ["*"]}),
                ("admin", "Administrator", {"academic": ["*"], "scheduling": ["*"]}),
                ("dean", "Faculty Dean", {"academic": ["read"], "scheduling": ["read"]}),
                ("hod", "Head Dept", {"academic": ["read"], "scheduling": ["read"]}),
                ("scheduler", "Scheduler", {"scheduling": ["create", "read", "update"]}),
                ("staff", "Staff", {"academic": ["read"]}),
            ]
            roles = []
            for name, desc, perms in roles_def:
                r = UserRole(name=name, description=desc, permissions=perms)
                session.add(r)
                roles.append(r)
            await session.flush()

            admin_user = User(
                email="admin@baze.edu.ng", first_name="System",
                last_name="Administrator", password_hash="$2b$12$example", is_active=True
            )
            session.add(admin_user)
            await session.flush()

            super_role = next(r for r in roles if r.name == "super_admin")
            session.add(UserRoleAssignment(user_id=admin_user.id, role_id=super_role.id))
            logger.info("Seeded users and roles")

    async def _seed_infrastructure(self) -> None:
        async with db_manager.get_db_transaction() as session:
            names = ["Lecture Hall", "Classroom", "Computer Lab", "Laboratory"]
            for nm in names:
                session.add(RoomType(name=nm, description=nm))
            await session.flush()

            b = Building(name="Engineering", code="ENG")
            session.add(b)
            await session.flush()

            for i in range(1, 6):
                session.add(
                    Room(
                        code=f"ENG0{i}",
                        name=f"ENG Room {i}",
                        capacity=100,
                        exam_capacity=70,
                        building_id=b.id,
                        room_type_id=1,
                    )
                )
            logger.info("Seeded infrastructure")

    async def _seed_academic_structure(self) -> None:
        async with db_manager.get_db_transaction() as session:
            year0 = datetime.utcnow().year
            for dy in (-1, 0, 1):
                y = year0 + dy
                session.add(
                    AcademicSession(
                        name=f"{y}/{y+1}",
                        start_date=date(y, 9, 1),
                        end_date=date(y + 1, 8, 31),
                        semester_system="Two Semester",
                        is_active=(dy == 0),
                    )
                )
            await session.flush()

            f = Faculty(name="Engineering", code="ENG")
            session.add(f)
            await session.flush()

            d = Department(name="Computer Eng", code="CPE", faculty_id=f.id)
            session.add(d)
            await session.flush()

            session.add(
                Programme(
                    name="B.Eng Computer Eng",
                    code="BCPE",
                    department_id=d.id,
                    degree_type="Bachelor",
                    duration_years=5,
                )
            )
            logger.info("Seeded academic structure")

    async def _seed_constraint_system(self) -> None:
        async with db_manager.get_db_transaction() as session:
            cats = [("Hard Constraints", "solver"), ("Soft Constraints", "optimizer")]
            categories = []
            for nm, layer in cats:
                c = ConstraintCategory(name=nm, description=nm, enforcement_layer=layer)
                session.add(c)
                categories.append(c)
            await session.flush()

            session.add(
                ConstraintRule(
                    code="NO_STUDENT_CONFLICT",
                    name="No Conflicts",
                    constraint_type="temporal",
                    category_id=categories.id, # type: ignore
                    constraint_definition={"type": "no_overlap"},
                    default_weight=1.0,
                )
            )
            logger.info("Seeded constraint system")

    async def _seed_time_slots(self) -> None:
        async with db_manager.get_db_transaction() as session:
            slots = [
                ("Morning Slot", time(8, 0), time(11, 0)),
                ("Afternoon Slot", time(12, 0), time(15, 0)),
                ("Evening Slot", time(16, 0), time(19, 0)),
            ]
            for name, st, et in slots:
                session.add(
                    TimeSlot(name=name, start_time=st, end_time=et, duration_minutes=180)
                )
            logger.info("Seeded time slots")

    async def _seed_sample_data(self) -> None:
        async with db_manager.get_db_transaction() as session:
            # AsyncSession -> use select/execute, not .query(...)
            result = await session.execute(
                select(AcademicSession).where(AcademicSession.is_active.is_(True))
            )
            current = result.scalars().first()
            if not current:
                logger.warning("No active session; skipping sample")
                return

            cs_course = Course(
                code="CSC101",
                title="Intro CS",
                credit_units=3,
                course_level=100,
                department_id=1,
                semester=1,
            )
            session.add(cs_course)
            await session.flush()

            stud = Student(
                matric_number="BU/2020/CSC/001", programme_id=1, current_level=100, entry_year=2020
            )
            session.add(stud)
            await session.flush()

            session.add(
                CourseRegistration(
                    student_id=stud.id, course_id=cs_course.id, session_id=current.id
                )
            )
            session.add(
                Exam(
                    course_id=cs_course.id,
                    session_id=current.id,
                    expected_students=1,
                    duration_minutes=180,
                )
            )
            logger.info("Seeded minimal sample data")

    async def import_from_csv(
        self, entity_type: str, file_path: str, validate_integrity: bool = True
    ) -> Dict[str, Any]:
        logger.info(f"Importing {entity_type} from {file_path}")
        csv_res = self.csv_processor.process_csv_file(file_path, entity_type)
        if not csv_res["success"]:
            return csv_res

        async with db_manager.get_db_transaction() as session:
            # Run sync-only utilities inside run_sync so they receive a synchronous Session
            def _map_and_check(db_sess: SyncSession) -> Dict[str, Any]:
                mapper = DataMapper(db_sess)
                map_res = mapper.map_data(csv_res["data"], entity_type)
                if not map_res["success"]:
                    return map_res
                if validate_integrity:
                    checker = DataIntegrityChecker(db_sess)
                    inv = checker.check_integrity({entity_type: map_res["mapped_data"]})
                    if not inv.success:
                        return {
                            "success": False,
                            "errors": [e.message for e in inv.errors],
                        }
                return {"success": True, "mapped_data": map_res["mapped_data"]}

            map_out = await session.run_sync(_map_and_check)
            if not map_out["success"]:
                return map_out

            saved = 0
            for rec in map_out["mapped_data"]:
                rec.pop("_metadata", None)
                model = {
                    "academic_sessions": AcademicSession,
                    "faculties": Faculty,
                    "departments": Department,
                    "programmes": Programme,
                    "courses": Course,
                    "students": Student,
                    "rooms": Room,
                    "time_slots": TimeSlot,
                }.get(entity_type)
                if model:
                    session.add(model(**rec))
                    saved += 1
            return {"success": True, "saved_records": saved}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", help="DB URL")
    p.add_argument("--drop-existing", action="store_true")
    p.add_argument("--no-sample-data", action="store_true")
    p.add_argument("--csv-import", help="CSV path")
    p.add_argument("--entity-type", help="Entity to import")
    args = p.parse_args()

    seeder = DatabaseSeeder(args.database_url)

    async def runner() -> None:
        if args.csv_import:
            if not args.entity_type:
                logger.error("--entity-type is required for CSV import")
            else:
                res = await seeder.import_from_csv(args.entity_type, args.csv_import)
                logger.info(f"Import result: {res}")
        else:
            await seeder.seed_all(
                drop_existing=args.drop_existing, sample_data=not args.no_sample_data
            )

    asyncio.run(runner())


if __name__ == "__main__":
    main()
