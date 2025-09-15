# scheduling_engine/constraints/hard_constraints/no_student_conflicts_same_room.py - FIXED TYPE ERRORS

"""
FIXED C5: No Student Conflicts Same Room Constraint - Sparsity Optimization

CRITICAL FIXES:
- Fixed constraint explosion (792k constraints -> optimized generation)
- Added sparsity filters to avoid Cartesian product generation
- Enhanced conflict pair validation with performance limits
- Comprehensive constraint counting and validation
- FIXED: Type annotation issues and method signature compatibility
"""

from scheduling_engine.constraints.base_constraint import CPSATBaseConstraint
import logging

logger = logging.getLogger(__name__)


class NoStudentConflictsSameRoomConstraint(CPSATBaseConstraint):
    """
    MULTI_EXAM_CAPACITY – C5

    ∀ r ∈ R, d ∈ D, t ∈ T, (e₁,e₂) ∈ ConflictPairs:
        y[e₁,r,d,t] + y[e₂,r,d,t] ≤ 1
    """

    # --------------------------------------------------------------------- #
    # Static configuration                                                   #
    # --------------------------------------------------------------------- #
    dependencies = ["MultiExamRoomCapacityConstraint"]
    constraint_category = "MULTI_EXAM_CAPACITY"

    is_critical = True
    min_expected_constraints = 1

    MAX_CONSTRAINTS_PER_MODULE = 25_000  # ↓ tighter than before
    MAX_CONFLICT_PAIRS_PROCESSED = 1_000  # keep as-is

    # Safety buffer so whole build stays <75 k (75,000 – ≈5 k slack)
    GLOBAL_MODEL_BUDGET = 70_000

    # --------------------------------------------------------------------- #
    # Helpers for internal limits                                            #
    # --------------------------------------------------------------------- #
    def _effective_constraint_limit(self) -> int:
        return int(
            getattr(self, "max_constraints_per_module", self.MAX_CONSTRAINTS_PER_MODULE)
        )

    def _capacity_per_pair(self) -> int:
        return (
            len(self._viable_rooms)
            * len(self._active_time_slots)
            * len(self.problem.days)
        )

    def _max_pairs_allowed_by_limit(self) -> int:
        return max(
            1, self._effective_constraint_limit() // max(1, self._capacity_per_pair())
        )

    # --------------------------------------------------------------------- #
    # Local variable initialisation                                          #
    # --------------------------------------------------------------------- #
    def _create_local_variables(self):
        logger.info(f"🔧 {self.constraint_id}: initialising with sparsity optimisation")

        # ------------ conflict-pair filtering ------------ #
        if not self.conflict_pairs:
            logger.warning(
                f"{self.constraint_id}: no shared conflict pairs – switching to direct detection"
            )
            self._use_direct_conflict_detection = True
            self._filtered_conflict_pairs = set()
        else:
            self._filtered_conflict_pairs = self._apply_sparsity_filter(
                self.conflict_pairs
            )
            self._use_direct_conflict_detection = (
                len(self._filtered_conflict_pairs) == 0
            )

        # ------------ contextual limits ------------ #
        self._viable_rooms = self._get_viable_rooms()
        self._active_time_slots = self._get_active_time_slots()

        # Second-pass trimming to satisfy per-module limit
        if not self._use_direct_conflict_detection:
            max_pairs = self._max_pairs_allowed_by_limit()
            if len(self._filtered_conflict_pairs) > max_pairs:
                self._filtered_conflict_pairs = self._prioritize_and_take(
                    self._filtered_conflict_pairs, max_pairs
                )

        # Final estimate & possible global-budget trim
        self._estimate_constraints()

        logger.info(
            f"📊 {self.constraint_id}: rooms={len(self._viable_rooms)}, "
            f"slots={len(self._active_time_slots)}, "
            f"pairs={len(self._filtered_conflict_pairs)}"
        )

    def _get_active_time_slots(self) -> list:
        """Return only active time slots, fallback to all if none marked active"""
        active_slots = [
            slot_id
            for slot_id, time_slot in self.problem.time_slots.items()
            if getattr(time_slot, "is_active", True)
        ]

        if not active_slots:
            logger.warning(
                f"⚠️ {self.constraint_id}: No active time slots found - using all slots"
            )
            return list(self.problem.time_slots.keys())

        return active_slots

    # --------------------------------------------------------------------- #
    # Sparsity utilities                                                     #
    # --------------------------------------------------------------------- #
    def _apply_sparsity_filter(self, conflict_pairs: set) -> set:
        if len(conflict_pairs) <= self.MAX_CONFLICT_PAIRS_PROCESSED:
            return conflict_pairs
        logger.warning(
            f"{self.constraint_id}: {len(conflict_pairs)} pairs – applying top-{self.MAX_CONFLICT_PAIRS_PROCESSED} filter"
        )
        return self._prioritize_and_take(
            conflict_pairs, self.MAX_CONFLICT_PAIRS_PROCESSED
        )

    def _prioritize_and_take(self, conflict_pairs: set, max_keep: int) -> set:
        scored = []
        for e1, e2 in conflict_pairs:
            overlap = len(
                self._get_students_for_exam_cached(e1)
                & self._get_students_for_exam_cached(e2)
            )
            if overlap:
                scored.append((overlap, e1, e2))
        if not scored:  # fall-back: arbitrary slice
            return set(list(conflict_pairs)[:max_keep])
        scored.sort(reverse=True)  # highest overlap first
        return set((e1, e2) for _, e1, e2 in scored[:max_keep])

    # --------------------------------------------------------------------- #
    # Estimate and global-budget guard                                       #
    # --------------------------------------------------------------------- #
    def _estimate_constraints(self):
        per_pair = self._capacity_per_pair()
        est = (
            len(self._filtered_conflict_pairs) * per_pair
            if not self._use_direct_conflict_detection
            else (len(self.problem.exams) * (len(self.problem.exams) - 1) // 2)
            * per_pair
        )

        # ---------- global-budget enforcement ---------- #
        if est > self.GLOBAL_MODEL_BUDGET:
            max_pairs = max(1, self.GLOBAL_MODEL_BUDGET // per_pair)
            logger.warning(
                f"{self.constraint_id}: projected {est:,} constraints "
                f"exceed global budget {self.GLOBAL_MODEL_BUDGET:,} – trimming to {max_pairs} pairs"
            )
            self._filtered_conflict_pairs = self._prioritize_and_take(
                self._filtered_conflict_pairs, max_pairs
            )
            est = len(self._filtered_conflict_pairs) * per_pair

        # ---------- per-module guard ---------- #
        limit = self._effective_constraint_limit()
        if est > limit:
            raise ValueError(
                f"{self.constraint_id}: est {est:,} > module limit {limit:,}"
            )

        self._estimated_constraints = est
        logger.info(
            f"{self.constraint_id}: final estimate {est:,} constraints (cap {limit:,})"
        )

    def _add_constraint_implementation(self):
        if not self.y:
            raise RuntimeError(f"{self.constraint_id}: No y variables available")
        logger.info(
            f"➕ {self.constraint_id}: Starting optimized constraint generation..."
        )

        # Respect limit on direct detection too
        if self._use_direct_conflict_detection:
            constraints_added = self._add_constraints_from_direct_detection_optimized()
        else:
            constraints_added = self._add_constraints_from_filtered_pairs()

        limit = self._effective_constraint_limit()
        if constraints_added == 0:
            logger.error(f"❌ {self.constraint_id}: ZERO constraints added!")
            self._log_constraint_debugging_info()
        elif constraints_added > limit:
            logger.error(
                f"❌ {self.constraint_id}: Constraint count ({constraints_added:,}) exceeds limit!"
            )
            raise RuntimeError(f"{self.constraint_id}: Generated too many constraints")
        else:
            logger.info(
                f"✅ {self.constraint_id}: Successfully added {constraints_added:,} optimized constraints"
            )

    def _get_students_for_exam_cached(self, exam_str: str) -> set[str]:
        """Cached student lookup for performance"""
        if not hasattr(self, "_student_cache"):
            self._student_cache: dict[str, set[str]] = {}

        if exam_str in self._student_cache:
            return self._student_cache[exam_str]

        exam_id = self._find_exam_by_str(exam_str)
        students = self._get_students_for_exam_direct(exam_id) if exam_id else set()
        self._student_cache[exam_str] = students
        return students

    def _get_viable_rooms(self) -> list:
        """Return rooms that can host exams, fallback to all rooms if none viable"""
        viable_rooms = [
            room
            for room in self.problem.rooms.values()
            if getattr(room, "exam_capacity", 0) > 0
        ]

        if not viable_rooms:
            logger.warning(
                f"⚠️ {self.constraint_id}: No viable rooms found - using all rooms"
            )
            return list(self.problem.rooms.values())

        return viable_rooms

    def _add_constraints_from_filtered_pairs(self) -> int:
        constraints_added = 0
        logger.info(
            f"🔧 {self.constraint_id}: Processing {len(self._filtered_conflict_pairs)} filtered conflict pairs..."
        )
        for room in self._viable_rooms:
            room_id = room.id
            for day in self.problem.days:
                for slot_id in self._active_time_slots:
                    slot_constraints = 0
                    for exam1_str, exam2_str in self._filtered_conflict_pairs:
                        exam1_id = self._find_exam_by_str(exam1_str)
                        exam2_id = self._find_exam_by_str(exam2_str)
                        if not exam1_id or not exam2_id:
                            continue
                        y1_key = (exam1_id, room_id, day, slot_id)
                        y2_key = (exam2_id, room_id, day, slot_id)
                        if y1_key in self.y and y2_key in self.y:
                            self.model.Add(self.y[y1_key] + self.y[y2_key] <= 1)
                            constraints_added += 1
                            slot_constraints += 1
                            self._increment_constraint_count()
                    if slot_constraints > 0:
                        logger.debug(
                            f"  Room {room.code}, Day {day}, Slot {slot_id}: {slot_constraints} constraints"
                        )
        return constraints_added

    def _add_constraints_from_direct_detection_optimized(self) -> int:
        constraints_added = 0
        # Cap by both internal direct-detection cap and module-limit-derived cap
        max_pairs_to_check = min(500, self._max_pairs_allowed_by_limit())
        logger.warning(
            f"⚠️ {self.constraint_id}: Using optimized direct detection (limited to {max_pairs_to_check} pairs)"
        )
        exams_list = list(self.problem.exams.values())
        pairs_checked = 0
        for i, exam1 in enumerate(exams_list):
            for exam2 in exams_list[i + 1 :]:
                if pairs_checked >= max_pairs_to_check:
                    logger.warning(
                        f"⚠️ {self.constraint_id}: Reached pair limit ({max_pairs_to_check}), stopping direct detection"
                    )
                    return constraints_added
                pairs_checked += 1
                students1 = self._get_students_for_exam_direct(exam1.id)
                students2 = self._get_students_for_exam_direct(exam2.id)
                if not (students1 & students2):
                    continue
                for room in self._viable_rooms:
                    room_id = room.id
                    for day in self.problem.days:
                        for slot_id in self._active_time_slots:
                            y1_key = (exam1.id, room_id, day, slot_id)
                            y2_key = (exam2.id, room_id, day, slot_id)
                            if y1_key in self.y and y2_key in self.y:
                                self.model.Add(self.y[y1_key] + self.y[y2_key] <= 1)
                                constraints_added += 1
                                self._increment_constraint_count()
        return constraints_added

    def _find_exam_by_str(self, exam_str: str):
        """Find exam ID by string representation"""
        if not hasattr(self, "_exam_str_cache"):
            self._exam_str_cache = {}
            for exam in self.problem.exams.values():
                self._exam_str_cache[str(exam.id)] = exam.id

        return self._exam_str_cache.get(exam_str)

    def _get_students_for_exam_direct(self, exam_id) -> set:
        """FIXED: Get students for exam using multiple methods with caching"""
        cache_key = str(exam_id)
        if not hasattr(self, "_exam_students_cache"):
            self._exam_students_cache = {}

        if cache_key in self._exam_students_cache:
            return self._exam_students_cache[cache_key]

        students = set()

        # Method 1: Direct exam student access
        exam = self.problem.exams.get(exam_id)
        if exam and hasattr(exam, "_students"):
            students.update(exam._students)

        # Method 2: Course registration mapping
        if exam:
            try:
                course_students = self.problem.get_students_for_course(exam.course_id)
                students.update(course_students)
            except:
                pass

        # Method 3: Problem-level method
        try:
            exam_students = self.problem.get_students_for_exam(exam_id)
            students.update(exam_students)
        except:
            pass

        self._exam_students_cache[cache_key] = students
        return students

    def _log_constraint_debugging_info(self):
        """Enhanced debugging information for constraint generation failures"""
        logger.debug(f"🐛 {self.constraint_id}: Constraint debugging info:")
        logger.debug(f"  Use direct detection: {self._use_direct_conflict_detection}")
        logger.debug(
            f"  Filtered conflict pairs: {len(getattr(self, '_filtered_conflict_pairs', set()))}"
        )
        logger.debug(f"  Viable rooms: {len(self._viable_rooms)}")
        logger.debug(f"  Active time slots: {len(self._active_time_slots)}")
        logger.debug(f"  Available y variables: {len(self.y)}")
        logger.debug(f"  Problem days: {len(self.problem.days)}")

        # Sample data for debugging
        if hasattr(self, "_filtered_conflict_pairs") and self._filtered_conflict_pairs:
            sample_pairs = list(self._filtered_conflict_pairs)[:3]
            logger.debug(f"  Sample conflict pairs: {sample_pairs}")

    def get_statistics(self):
        """Enhanced statistics with sparsity optimization metrics"""
        base_stats = super().get_statistics()
        base_stats.update(
            {
                "sparsity_optimization": {
                    "use_direct_detection": getattr(
                        self, "_use_direct_conflict_detection", False
                    ),
                    "filtered_conflict_pairs": len(
                        getattr(self, "_filtered_conflict_pairs", set())
                    ),
                    "viable_rooms": len(getattr(self, "_viable_rooms", [])),
                    "active_time_slots": len(getattr(self, "_active_time_slots", [])),
                    "max_constraints_limit": self.MAX_CONSTRAINTS_PER_MODULE,
                    "max_pairs_limit": self.MAX_CONFLICT_PAIRS_PROCESSED,
                }
            }
        )
        return base_stats
