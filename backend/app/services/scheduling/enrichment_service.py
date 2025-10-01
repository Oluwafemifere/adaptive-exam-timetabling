# backend/app/services/scheduling/enrichment_service.py

"""
Service for enriching raw timetable solution data with human-readable content.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID

logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    Handles the post-processing of a raw timetable solution to add
    human-readable information for frontend consumption.
    """

    def __init__(self):
        """Initializes the enrichment service."""
        pass

    async def enrich_solution_data(
        self,
        job_results_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enriches the raw solution data using lookup metadata also found in the job results.
        """
        logger.info("Starting enrichment of timetable solution data.")
        try:
            solution = job_results_data.get("solution", {})
            metadata = job_results_data.get("lookup_metadata", {})
            raw_assignments = solution.get("assignments", {})

            # Use lookup maps provided in the job results metadata
            exams_map = metadata.get("exams", {})
            rooms_map = metadata.get("rooms", {})
            invigilators_map = metadata.get("invigilators", {})
            instructors_map = metadata.get("instructors", {})
            timeslots_map = metadata.get("timeslots", {})
            days_map = metadata.get("days", {})
            timeslot_to_day_map = metadata.get("timeslot_to_day_map", {})

            enriched_assignments = []

            # Calculate capacity statistics
            total_assigned_students = 0
            total_room_capacity = 0

            for exam_id_str, assignment_data in raw_assignments.items():
                exam_details = exams_map.get(exam_id_str)
                if not exam_details:
                    logger.warning(
                        f"Could not find details for exam {exam_id_str} during enrichment."
                    )
                    continue

                room_ids_str = [str(rid) for rid in assignment_data.get("room_ids", [])]
                assigned_rooms = [
                    rooms_map.get(rid) for rid in room_ids_str if rooms_map.get(rid)
                ]

                # Calculate capacity metrics for this assignment
                assignment_capacity = sum(
                    room.get("exam_capacity", 0) for room in assigned_rooms
                )
                assignment_students = exam_details.get("expected_students", 0)

                total_room_capacity += assignment_capacity
                total_assigned_students += assignment_students

                capacity_utilization = 0
                if assignment_capacity > 0:
                    capacity_utilization = (
                        assignment_students / assignment_capacity
                    ) * 100

                invigilator_ids_str = [
                    str(inv_id) for inv_id in assignment_data.get("invigilator_ids", [])
                ]
                assigned_invigilators = [
                    invigilators_map.get(inv_id)
                    for inv_id in invigilator_ids_str
                    if invigilators_map.get(inv_id)
                ]

                time_slot_id_str = (
                    str(assignment_data.get("time_slot_id"))
                    if assignment_data.get("time_slot_id")
                    else None
                )
                time_slot = (
                    timeslots_map.get(time_slot_id_str) if time_slot_id_str else None
                )

                day = None
                if time_slot_id_str:
                    day_id_str = timeslot_to_day_map.get(time_slot_id_str)
                    if day_id_str:
                        day = days_map.get(day_id_str)

                instructor_ids = exam_details.get("instructor_ids", [])
                assigned_instructors = [
                    instructors_map.get(str(inst_id))
                    for inst_id in instructor_ids
                    if instructors_map.get(str(inst_id))
                ]
                instructor_names = (
                    ", ".join(
                        [inst.get("name", "N/A") for inst in assigned_instructors]
                    )
                    or "Not Assigned"
                )

                enriched_data = {
                    "exam_id": exam_id_str,
                    "course_id": str(exam_details.get("course_id")),
                    "course_code": exam_details.get("course_code", "N/A"),
                    "course_title": exam_details.get("course_title", "N/A"),
                    "department_name": exam_details.get("department_name", "N/A"),
                    "instructor_name": instructor_names,
                    # --- START OF FIX: Add instructor IDs to enriched data ---
                    "instructor_ids": instructor_ids,
                    # --- END OF FIX ---
                    "student_count": exam_details.get("expected_students"),
                    "actual_student_count": exam_details.get("actual_student_count", 0),
                    "duration_minutes": exam_details.get("duration_minutes"),
                    "is_practical": exam_details.get("is_practical"),
                    "day_id": str(day["id"]) if day else None,
                    "date": day["date"] if day else None,
                    "time_slot_id": time_slot_id_str,
                    "time_slot_name": time_slot["name"] if time_slot else "Unscheduled",
                    "start_time": time_slot["start_time"] if time_slot else None,
                    "end_time": time_slot["end_time"] if time_slot else None,
                    "time_slot_label": (
                        f"{time_slot['start_time']} - {time_slot['end_time']}"
                        if time_slot
                        else "Unscheduled"
                    ),
                    "room_codes": [r["code"] for r in assigned_rooms],
                    "rooms": [
                        {
                            "id": str(r["id"]),
                            "code": r["code"],
                            "normal_capacity": r.get("capacity", 0),
                            "exam_capacity": r.get("exam_capacity", 0),
                            "has_computers": r.get("has_computers", False),
                            "building_name": r.get("building_name", "N/A"),
                        }
                        for r in assigned_rooms
                    ],
                    "invigilators": [
                        {
                            "id": str(inv["id"]),
                            "name": inv["name"],
                            "email": inv["email"],
                        }
                        for inv in assigned_invigilators
                    ],
                    "capacity_metrics": {
                        "total_assigned_capacity": assignment_capacity,
                        "expected_students": assignment_students,
                        "utilization_percentage": round(capacity_utilization, 2),
                        "has_sufficient_capacity": assignment_capacity
                        >= assignment_students,
                    },
                    "conflicts": assignment_data.get("conflicts", []),
                }
                enriched_assignments.append(enriched_data)

            # Convert the list of assignments to a dictionary, keyed by exam_id
            enriched_assignments_dict = {
                item["exam_id"]: item for item in enriched_assignments
            }
            solution["assignments"] = enriched_assignments_dict

            # Add overall capacity statistics to the solution
            overall_utilization = 0
            if total_room_capacity > 0:
                overall_utilization = (
                    total_assigned_students / total_room_capacity
                ) * 100

            solution["capacity_statistics"] = {
                "total_room_capacity": total_room_capacity,
                "total_assigned_students": total_assigned_students,
                "overall_utilization_percentage": round(overall_utilization, 2),
                "total_assignments": len(enriched_assignments),
            }

            logger.info(
                f"Successfully enriched {len(enriched_assignments)} assignments. "
                f"Overall capacity utilization: {overall_utilization:.1f}%"
            )

            job_results_data["solution"] = solution
            job_results_data.pop("lookup_metadata", None)
            job_results_data["is_enriched"] = True

            return job_results_data

        except Exception as e:
            logger.error(f"Error during solution enrichment: {e}", exc_info=True)
            job_results_data["enrichment_error"] = str(e)
            return job_results_data
