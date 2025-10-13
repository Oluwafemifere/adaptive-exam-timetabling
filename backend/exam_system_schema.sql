--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: exam_system; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA exam_system;


ALTER SCHEMA exam_system OWNER TO postgres;

--
-- Name: slot_generation_mode_enum; Type: TYPE; Schema: exam_system; Owner: postgres
--

CREATE TYPE exam_system.slot_generation_mode_enum AS ENUM (
    'fixed',
    'flexible'
);


ALTER TYPE exam_system.slot_generation_mode_enum OWNER TO postgres;

--
-- Name: admin_create_and_register_user(uuid, text, text, text, text, text, uuid, text, text, integer); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.admin_create_and_register_user(p_admin_user_id uuid, p_user_type text, p_email text, p_first_name text, p_last_name text, p_password text, p_session_id uuid, p_matric_number text DEFAULT NULL::text, p_programme_code text DEFAULT NULL::text, p_entry_year integer DEFAULT NULL::integer) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_is_admin boolean;
    v_new_user_id uuid;
    v_student_id uuid;
    v_programme_id uuid;
    v_password_hash text;
    v_current_year integer := EXTRACT(YEAR FROM CURRENT_DATE);
    v_student_level integer;
BEGIN
    -- 1. Authorization: Verify the user performing this action is an admin.
    SELECT is_superuser INTO v_is_admin
    FROM exam_system.users
    WHERE id = p_admin_user_id;

    IF NOT v_is_admin THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'Authorization failed. User is not an administrator.');
    END IF;

    -- 2. Validate that the email does not already exist.
    IF EXISTS (SELECT 1 FROM exam_system.users WHERE email = p_email) THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'A user with this email address already exists.');
    END IF;

    -- 3. Hash the password
    v_password_hash := crypt(p_password, gen_salt('bf'));

    -- 4. Handle user creation based on type.
    IF p_user_type = 'admin' THEN
        -- Create a new admin user
        INSERT INTO exam_system.users (email, first_name, last_name, password_hash, is_active, is_superuser, role)
        VALUES (p_email, p_first_name, p_last_name, v_password_hash, true, true, 'Admin')
        RETURNING id INTO v_new_user_id;

        -- Log the action
        PERFORM exam_system.log_audit_activity(p_admin_user_id, 'CREATE_ADMIN', 'USERS', p_notes := 'Admin user created', p_entity_id := v_new_user_id);

        RETURN jsonb_build_object('status', 'success', 'message', 'Administrator created successfully.', 'user_id', v_new_user_id);

    ELSIF p_user_type = 'student' THEN
        -- For students, matric number and session ID are required.
        IF p_matric_number IS NULL OR p_session_id IS NULL THEN
             RETURN jsonb_build_object('status', 'error', 'message', 'Matriculation number and session ID are required for student creation.');
        END IF;

        -- MODIFIED: Student lookup is now scoped to the session.
        SELECT id INTO v_student_id FROM exam_system.students WHERE matric_number = p_matric_number AND session_id = p_session_id;

        -- Create the user account
        INSERT INTO exam_system.users (email, first_name, last_name, password_hash, is_active, is_superuser, role)
        VALUES (p_email, p_first_name, p_last_name, v_password_hash, true, false, 'Student')
        RETURNING id INTO v_new_user_id;

        IF v_student_id IS NOT NULL THEN
            -- Student record exists for this session. Link the new user account.
            UPDATE exam_system.students
            SET user_id = v_new_user_id
            WHERE id = v_student_id; -- This is safe as 'id' is a primary key
            PERFORM exam_system.log_audit_activity(p_admin_user_id, 'CREATE_USER_FOR_STUDENT', 'STUDENTS', p_notes := 'User account created for existing student', p_entity_id := v_student_id);

        ELSE
            -- This is a new student for this session.
            IF p_programme_code IS NULL OR p_entry_year IS NULL THEN
                RETURN jsonb_build_object('status', 'error', 'message', 'Programme code and entry year are required for new students.');
            END IF;

            -- MODIFIED: Programme lookup is now scoped to the session.
            SELECT id INTO v_programme_id FROM exam_system.programmes WHERE code = p_programme_code AND session_id = p_session_id;
            IF v_programme_id IS NULL THEN
                RETURN jsonb_build_object('status', 'error', 'message', 'Invalid programme code specified for this session.');
            END IF;

            -- MODIFIED: New student record now includes the session_id.
            INSERT INTO exam_system.students (matric_number, first_name, last_name, entry_year, programme_id, user_id, session_id)
            VALUES (p_matric_number, p_first_name, p_last_name, p_entry_year, v_programme_id, v_new_user_id, p_session_id)
            RETURNING id INTO v_student_id;
            PERFORM exam_system.log_audit_activity(p_admin_user_id, 'CREATE_STUDENT', 'STUDENTS', p_notes := 'New student and user account created', p_entity_id := v_student_id);
        END IF;

        -- Enroll the student in the specified session.
        v_student_level := (v_current_year - p_entry_year) * 100;
        IF v_student_level < 100 THEN v_student_level := 100; END IF;

        INSERT INTO exam_system.student_enrollments (student_id, session_id, level, is_active)
        VALUES (v_student_id, p_session_id, v_student_level, true)
        ON CONFLICT (student_id, session_id) DO NOTHING;

        RETURN jsonb_build_object('status', 'success', 'message', 'Student user created and enrolled successfully.', 'user_id', v_new_user_id, 'student_id', v_student_id);
    ELSE
        RETURN jsonb_build_object('status', 'error', 'message', 'Invalid user type specified. Must be "student" or "admin".');
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('status', 'error', 'message', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.admin_create_and_register_user(p_admin_user_id uuid, p_user_type text, p_email text, p_first_name text, p_last_name text, p_password text, p_session_id uuid, p_matric_number text, p_programme_code text, p_entry_year integer) OWNER TO postgres;

--
-- Name: assign_role_to_user(uuid, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.assign_role_to_user(p_user_id uuid, p_role_name text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_role_id uuid;
BEGIN
    SELECT id INTO v_role_id FROM exam_system.user_roles WHERE name = p_role_name;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Role not found.');
    END IF;

    -- Avoid duplicate assignments
    IF EXISTS (SELECT 1 FROM exam_system.user_role_assignments WHERE user_id = p_user_id AND role_id = v_role_id) THEN
         RETURN jsonb_build_object('success', true, 'message', 'User already has this role.');
    END IF;

    INSERT INTO exam_system.user_role_assignments (user_id, role_id)
    VALUES (p_user_id, v_role_id);

    RETURN jsonb_build_object('success', true, 'message', 'Role assigned successfully.');
EXCEPTION
    WHEN others THEN
        RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.assign_role_to_user(p_user_id uuid, p_role_name text) OWNER TO postgres;

--
-- Name: authenticate_user(text, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.authenticate_user(p_email text, p_password text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_user RECORD;
    v_staff_id UUID;
    v_student_id UUID;
    v_primary_role TEXT;
    v_roles TEXT[];
BEGIN
    -- Find the user by email
    SELECT id, first_name, last_name, password_hash, is_superuser
    INTO v_user
    FROM exam_system.users
    WHERE email = p_email AND is_active = TRUE;

    -- If user not found or password does not match, return error
    IF NOT FOUND OR v_user.password_hash IS NULL OR crypt(p_password, v_user.password_hash) <> v_user.password_hash THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'Invalid email or password.');
    END IF;

    -- Determine the user's primary role and gather all roles
    v_primary_role := '';
    
    -- 1. Check for Administrator (Superuser)
    IF v_user.is_superuser THEN
        v_primary_role := 'administrator';
    END IF;

    -- 2. Check if the user is a staff member
    SELECT id INTO v_staff_id FROM exam_system.staff WHERE user_id = v_user.id;
    IF v_staff_id IS NOT NULL THEN
        IF v_primary_role = '' THEN
            v_primary_role := 'staff';
        END IF;
    END IF;

    -- 3. Check if the user is a student
    SELECT id INTO v_student_id FROM exam_system.students WHERE user_id = v_user.id;
    IF v_student_id IS NOT NULL THEN
        IF v_primary_role = '' THEN
            v_primary_role := 'student';
        END IF;
    END IF;
    
    -- If no specific role is found, default to a base role if they are not a superuser
    IF v_primary_role = '' THEN
       RETURN jsonb_build_object('status', 'error', 'message', 'User has no assigned role.');
    END IF;

    -- Get all assigned role names from user_roles
    SELECT array_agg(ur.name)
    INTO v_roles
    FROM exam_system.user_role_assignments ura
    JOIN exam_system.user_roles ur ON ura.role_id = ur.id
    WHERE ura.user_id = v_user.id;

    -- Return success with user details
    RETURN jsonb_build_object(
        'status', 'success',
        'user_id', v_user.id,
        'first_name', v_user.first_name,
        'last_name', v_user.last_name,
        'email', p_email,
        'primary_role', v_primary_role,
        'roles', COALESCE(v_roles, ARRAY[]::TEXT[])
    );
END;
$$;


ALTER FUNCTION exam_system.authenticate_user(p_email text, p_password text) OWNER TO postgres;

--
-- Name: check_user_permission(uuid, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.check_user_permission(p_user_id uuid, p_permission text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM exam_system.user_role_assignments ura
        JOIN exam_system.user_roles ur ON ura.role_id = ur.id
        WHERE ura.user_id = p_user_id
          AND ur.permissions ? p_permission
    );
END;
$$;


ALTER FUNCTION exam_system.check_user_permission(p_user_id uuid, p_permission text) OWNER TO postgres;

--
-- Name: compare_scenarios(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.compare_scenarios(p_scenario_id_1 uuid, p_scenario_id_2 uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    scenario_1_kpis jsonb;
    scenario_2_kpis jsonb;
    version_1_id uuid;
    version_2_id uuid;
BEGIN
    -- Get the latest version ID for scenario 1
    SELECT tv.id INTO version_1_id
    FROM exam_system.timetable_versions tv
    WHERE tv.scenario_id = p_scenario_id_1
    ORDER BY tv.created_at DESC
    LIMIT 1;

    -- Get the latest version ID for scenario 2
    SELECT tv.id INTO version_2_id
    FROM exam_system.timetable_versions tv
    WHERE tv.scenario_id = p_scenario_id_2
    ORDER BY tv.created_at DESC
    LIMIT 1;

    -- Calculate KPIs for scenario 1's latest version
    SELECT jsonb_build_object(
        'hard_constraint_violations', (SELECT COUNT(*) FROM exam_system.timetable_conflicts WHERE version_id = version_1_id AND type = 'hard'),
        'soft_constraint_violations', (SELECT COUNT(*) FROM exam_system.timetable_conflicts WHERE version_id = version_1_id AND type = 'soft'),
        'total_exams', (SELECT COUNT(DISTINCT exam_id) FROM exam_system.timetable_assignments WHERE version_id = version_1_id)
    ) INTO scenario_1_kpis;

    -- Calculate KPIs for scenario 2's latest version
    SELECT jsonb_build_object(
        'hard_constraint_violations', (SELECT COUNT(*) FROM exam_system.timetable_conflicts WHERE version_id = version_2_id AND type = 'hard'),
        'soft_constraint_violations', (SELECT COUNT(*) FROM exam_system.timetable_conflicts WHERE version_id = version_2_id AND type = 'soft'),
        'total_exams', (SELECT COUNT(DISTINCT exam_id) FROM exam_system.timetable_assignments WHERE version_id = version_2_id)
    ) INTO scenario_2_kpis;

    RETURN jsonb_build_object(
        'scenario_1', scenario_1_kpis,
        'scenario_2', scenario_2_kpis
    );
END;
$$;


ALTER FUNCTION exam_system.compare_scenarios(p_scenario_id_1 uuid, p_scenario_id_2 uuid) OWNER TO postgres;

--
-- Name: create_academic_session(text, date, date, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_academic_session(p_name text, p_start_date date, p_end_date date, p_timeslot_template_id uuid, p_template_id uuid DEFAULT NULL::uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_session_config JSONB;
    v_new_session_id UUID;
BEGIN
    -- If a template is provided, retrieve its configuration data
    IF p_template_id IS NOT NULL THEN
        SELECT template_data INTO v_session_config
        FROM exam_system.session_templates
        WHERE id = p_template_id;
    ELSE
        -- Otherwise, start with an empty configuration
        v_session_config := '{}'::jsonb;
    END IF;

    -- Insert the new academic session into the table
    INSERT INTO exam_system.academic_sessions (name, start_date, end_date, timeslot_template_id, session_config)
    VALUES (p_name, p_start_date, p_end_date, p_timeslot_template_id, v_session_config)
    RETURNING id INTO v_new_session_id;

    -- Return the ID of the newly created session
    RETURN jsonb_build_object('success', TRUE, 'session_id', v_new_session_id);
END;
$$;


ALTER FUNCTION exam_system.create_academic_session(p_name text, p_start_date date, p_end_date date, p_timeslot_template_id uuid, p_template_id uuid) OWNER TO postgres;

--
-- Name: create_assignment_change_request(uuid, uuid, character varying, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_assignment_change_request(p_user_id uuid, p_assignment_id uuid, p_reason character varying, p_description text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_staff_id UUID;
    v_session_id UUID;
    v_new_request RECORD;
BEGIN
    -- MODIFIED: Derive session_id from the assignment's exam
    SELECT e.session_id INTO v_session_id
    FROM exam_system.timetable_assignments ta
    JOIN exam_system.exams e ON ta.exam_id = e.id
    WHERE ta.id = p_assignment_id;

    IF v_session_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'Could not determine the academic session for this assignment.');
    END IF;

    -- MODIFIED: Find the staff_id associated with the user_id within the correct session
    SELECT id INTO v_staff_id FROM exam_system.staff WHERE user_id = p_user_id AND session_id = v_session_id;

    IF v_staff_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'No staff profile linked to this user account for the relevant session.');
    END IF;

    -- Verify the assignment belongs to this staff member
    IF NOT EXISTS (
        SELECT 1 FROM exam_system.exam_invigilators
        WHERE timetable_assignment_id = p_assignment_id AND staff_id = v_staff_id
    ) THEN
        RETURN jsonb_build_object('success', false, 'message', 'This assignment does not belong to the requesting staff member.');
    END IF;

    -- Insert the new change request
    INSERT INTO exam_system.assignment_change_requests (staff_id, timetable_assignment_id, reason, description, status)
    VALUES (v_staff_id, p_assignment_id, p_reason, p_description, 'pending')
    RETURNING * INTO v_new_request;

    RETURN jsonb_build_object('success', true, 'data', to_jsonb(v_new_request));

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'message', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.create_assignment_change_request(p_user_id uuid, p_assignment_id uuid, p_reason character varying, p_description text) OWNER TO postgres;

--
-- Name: FUNCTION create_assignment_change_request(p_user_id uuid, p_assignment_id uuid, p_reason character varying, p_description text); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.create_assignment_change_request(p_user_id uuid, p_assignment_id uuid, p_reason character varying, p_description text) IS 'Creates a new assignment change request submitted by a staff member.';


--
-- Name: create_conflict_report(uuid, uuid, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_conflict_report(p_user_id uuid, p_exam_id uuid, p_description text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_student_id UUID;
    v_session_id UUID;
    v_new_report RECORD;
BEGIN
    -- MODIFIED: Derive session_id from the exam
    SELECT session_id INTO v_session_id FROM exam_system.exams WHERE id = p_exam_id;

    IF v_session_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'Exam not found.');
    END IF;

    -- MODIFIED: Find the student_id associated with the user_id within the correct session
    SELECT id INTO v_student_id FROM exam_system.students WHERE user_id = p_user_id AND session_id = v_session_id;

    IF v_student_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'No student profile linked to this user account for the exam''s session.');
    END IF;

    -- Insert the new conflict report
    INSERT INTO exam_system.conflict_reports (student_id, exam_id, description, status)
    VALUES (v_student_id, p_exam_id, p_description, 'pending')
    RETURNING * INTO v_new_report;

    RETURN jsonb_build_object('success', true, 'data', to_jsonb(v_new_report));

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'message', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.create_conflict_report(p_user_id uuid, p_exam_id uuid, p_description text) OWNER TO postgres;

--
-- Name: FUNCTION create_conflict_report(p_user_id uuid, p_exam_id uuid, p_description text); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.create_conflict_report(p_user_id uuid, p_exam_id uuid, p_description text) IS 'Creates a new conflict report submitted by a student.';


--
-- Name: create_course(jsonb, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_course(p_data jsonb, p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_id uuid;
BEGIN
    INSERT INTO exam_system.courses (
        code, title, credit_units, course_level, semester,
        exam_duration_minutes, is_practical, morning_only, is_active,
        session_id -- MODIFIED: Added session_id column
    )
    VALUES (
        p_data->>'code',
        p_data->>'title',
        (p_data->>'credit_units')::int,
        (p_data->>'course_level')::int,
        (p_data->>'semester')::int,
        (p_data->>'exam_duration_minutes')::int,
        (p_data->>'is_practical')::boolean,
        (p_data->>'morning_only')::boolean,
        (p_data->>'is_active')::boolean,
        p_session_id -- MODIFIED: Use the provided session_id parameter
    ) RETURNING id INTO new_id;

    PERFORM exam_system.log_audit_activity(p_user_id, 'create', 'course', new_id, null, p_data);
    RETURN jsonb_build_object('success', true, 'id', new_id);
EXCEPTION WHEN others THEN RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.create_course(p_data jsonb, p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: create_exam(jsonb, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_exam(p_data jsonb, p_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_id uuid;
BEGIN
    INSERT INTO exam_system.exams (course_id, session_id, duration_minutes, expected_students, requires_special_arrangements, status, notes, is_practical, requires_projector, is_common, morning_only, instructor_id)
    VALUES (
        (p_data->>'course_id')::uuid,
        (p_data->>'session_id')::uuid,
        (p_data->>'duration_minutes')::integer,
        (p_data->>'expected_students')::integer,
        COALESCE((p_data->>'requires_special_arrangements')::boolean, false),
        COALESCE(p_data->>'status', 'PENDING'),
        p_data->>'notes',
        COALESCE((p_data->>'is_practical')::boolean, false),
        COALESCE((p_data->>'requires_projector')::boolean, false),
        COALESCE((p_data->>'is_common')::boolean, false),
        COALESCE((p_data->>'morning_only')::boolean, false),
        (p_data->>'instructor_id')::uuid
    ) RETURNING id INTO new_id;

    PERFORM exam_system.log_audit_activity(p_user_id, 'create', 'exam', new_id, null, p_data);
    RETURN jsonb_build_object('success', true, 'id', new_id);
EXCEPTION WHEN others THEN RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.create_exam(p_data jsonb, p_user_id uuid) OWNER TO postgres;

--
-- Name: create_exams_from_courses(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_exams_from_courses(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_created_count INT;
BEGIN
    -- Use a single, powerful INSERT ... SELECT statement to create all exams at once.
    -- This is more efficient and reliable than a procedural loop.
    WITH new_exams AS (
        INSERT INTO exam_system.exams (
            id, course_id, session_id, duration_minutes, expected_students,
            is_practical, morning_only, status, 
            requires_special_arrangements, requires_projector, is_common
        )
        -- 1. Select all courses that should have an exam
        SELECT
            gen_random_uuid(),
            c.id AS course_id,
            p_session_id,
            c.exam_duration_minutes,
            COUNT(cr.student_id) AS student_count, -- 2. Calculate the student count
            COALESCE(c.is_practical, false),
            COALESCE(c.morning_only, false),
            'pending' AS status,
            false, false, false -- Default values
        FROM
            exam_system.courses c
        JOIN
            exam_system.course_registrations cr ON c.id = cr.course_id
        WHERE
            c.is_active = true
            AND cr.session_id = p_session_id
            -- 3. Crucially, ensure we don't re-create exams that already exist
            AND NOT EXISTS (
                SELECT 1 FROM exam_system.exams ex
                WHERE ex.course_id = c.id AND ex.session_id = p_session_id
            )
        GROUP BY
            c.id
        HAVING
            COUNT(cr.student_id) > 0 -- Only create exams for courses with students
        RETURNING id
    )
    SELECT COUNT(*) INTO v_created_count FROM new_exams;

    -- Note: For simplicity, this version does not handle updates to student counts
    -- for pre-existing exams, but it correctly handles the primary creation logic.
    
    RETURN jsonb_build_object(
        'success', true,
        'message', 'Exam creation process completed.',
        'exams_created', v_created_count,
        'exams_updated', 0 -- This simplified version focuses on creation.
    );
END;
$$;


ALTER FUNCTION exam_system.create_exams_from_courses(p_session_id uuid) OWNER TO postgres;

--
-- Name: create_manual_timetable_edit(uuid, uuid, uuid, jsonb, jsonb, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_manual_timetable_edit(p_version_id uuid, p_exam_id uuid, p_edited_by uuid, p_new_values jsonb, p_old_values jsonb, p_reason text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_edit_id UUID;
    v_assignment RECORD;
BEGIN
    -- Update the actual assignment
    UPDATE exam_system.timetable_assignments
    SET exam_date = (p_new_values->>'exam_date')::DATE,
        time_slot_period = p_new_values->>'time_slot_period',
        room_id = (p_new_values->>'room_id')::UUID
    WHERE exam_id = p_exam_id AND version_id = p_version_id;

    -- Log the edit
    INSERT INTO exam_system.timetable_edits (version_id, exam_id, edited_by, edit_type, new_values, old_values, reason, validation_status)
    VALUES (p_version_id, p_exam_id, p_edited_by, 'manual_move', p_new_values, p_old_values, p_reason, 'pending')
    RETURNING id INTO new_edit_id;

    -- Optionally, return the newly created conflicts by this move
    -- (This would require calling a conflict detection function here)

    RETURN jsonb_build_object('status', 'success', 'edit_id', new_edit_id);
EXCEPTION
    WHEN others THEN
        -- Rollback the update if logging fails
        RETURN jsonb_build_object('status', 'error', 'message', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.create_manual_timetable_edit(p_version_id uuid, p_exam_id uuid, p_edited_by uuid, p_new_values jsonb, p_old_values jsonb, p_reason text) OWNER TO postgres;

--
-- Name: create_or_update_user_preset(uuid, character varying, character varying, jsonb); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_or_update_user_preset(p_user_id uuid, p_preset_name character varying, p_preset_type character varying, p_filters jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_preset_id UUID;
    v_result JSONB;
BEGIN
    INSERT INTO exam_system.user_filter_presets (user_id, preset_name, preset_type, filters)
    VALUES (p_user_id, p_preset_name, p_preset_type, p_filters)
    ON CONFLICT (user_id, preset_type, preset_name)
    DO UPDATE SET
        filters = EXCLUDED.filters,
        updated_at = NOW()
    RETURNING id INTO v_preset_id;

    SELECT to_jsonb(row) INTO v_result FROM exam_system.user_filter_presets row WHERE id = v_preset_id;

    RETURN jsonb_build_object('success', true, 'preset', v_result);
END;
$$;


ALTER FUNCTION exam_system.create_or_update_user_preset(p_user_id uuid, p_preset_name character varying, p_preset_type character varying, p_filters jsonb) OWNER TO postgres;

--
-- Name: create_room(jsonb, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_room(p_data jsonb, p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_id uuid;
    v_building_id uuid := (p_data->>'building_id')::uuid;
BEGIN
    -- MODIFIED: Validate that the building exists in the current session
    IF NOT EXISTS (SELECT 1 FROM exam_system.buildings WHERE id = v_building_id AND session_id = p_session_id) THEN
        RETURN jsonb_build_object('success', false, 'error', 'The specified building does not exist in this academic session.');
    END IF;

    INSERT INTO exam_system.rooms (
        code, name, building_id, room_type_id, capacity, exam_capacity,
        has_ac, has_projector, has_computers, is_active, overbookable,
        max_inv_per_room, notes, session_id -- MODIFIED: Added session_id column
    )
    VALUES (
        p_data->>'code',
        p_data->>'name',
        v_building_id,
        (p_data->>'room_type_id')::uuid,
        (p_data->>'capacity')::int,
        (p_data->>'exam_capacity')::int,
        (p_data->>'has_ac')::boolean,
        (p_data->>'has_projector')::boolean,
        (p_data->>'has_computers')::boolean,
        (p_data->>'is_active')::boolean,
        COALESCE((p_data->>'overbookable')::boolean, false),
        COALESCE((p_data->>'max_inv_per_room')::int, 2),
        p_data->>'notes',
        p_session_id -- MODIFIED: Use the provided session_id parameter
    ) RETURNING id INTO new_id;

    PERFORM exam_system.log_audit_activity(p_user_id, 'create', 'room', new_id, null, p_data);
    RETURN jsonb_build_object('success', true, 'id', new_id);
EXCEPTION WHEN others THEN RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.create_room(p_data jsonb, p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: create_scenario_from_version(uuid, text, text, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_scenario_from_version(p_parent_version_id uuid, p_scenario_name text, p_scenario_description text, p_created_by_user_id uuid) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_scenario_id UUID;
    v_new_version_id UUID;
    v_parent_job_id UUID;
BEGIN
    -- 1. Create a new scenario
    INSERT INTO exam_system.timetable_scenarios (parent_version_id, name, description, created_by)
    VALUES (p_parent_version_id, p_scenario_name, p_scenario_description, p_created_by_user_id)
    RETURNING id INTO v_scenario_id;

    -- Get the job_id from the parent version to link the new version
    SELECT job_id INTO v_parent_job_id FROM exam_system.timetable_versions WHERE id = p_parent_version_id;

    -- 2. Create a new 'draft' timetable version within the scenario
    INSERT INTO exam_system.timetable_versions (job_id, parent_version_id, version_type, is_published, version_number, is_active, scenario_id)
    VALUES (v_parent_job_id, p_parent_version_id, 'draft', FALSE, 1, TRUE, v_scenario_id)
    RETURNING id INTO v_new_version_id;

    -- 3. Copy all assignments from the parent version to the new version
    INSERT INTO exam_system.timetable_assignments (
        id, exam_id, room_id, student_count, is_confirmed, version_id,
        allocated_capacity, is_primary, seating_arrangement, time_slot_id
    )
    SELECT
        gen_random_uuid(), exam_id, room_id, student_count, is_confirmed, v_new_version_id,
        allocated_capacity, is_primary, seating_arrangement, time_slot_id
    FROM exam_system.timetable_assignments
    WHERE version_id = p_parent_version_id;

    RETURN v_scenario_id;
END;
$$;


ALTER FUNCTION exam_system.create_scenario_from_version(p_parent_version_id uuid, p_scenario_name text, p_scenario_description text, p_created_by_user_id uuid) OWNER TO postgres;

--
-- Name: create_student_user(uuid, character varying, character varying); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_student_user(p_student_id uuid, p_email character varying, p_plain_password character varying) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_user_id UUID;
    v_first_name VARCHAR;
    v_last_name VARCHAR;
    v_password_hash VARCHAR;
BEGIN
    -- Check if a user with the given email already exists
    IF EXISTS (SELECT 1 FROM exam_system.users WHERE email = p_email) THEN
        RAISE EXCEPTION 'User with email % already exists', p_email;
    END IF;

    -- Retrieve student's first and last name from the students table
    SELECT first_name, last_name INTO v_first_name, v_last_name
    FROM exam_system.students WHERE id = p_student_id;

    -- If student is not found, raise an exception
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Student with ID % not found', p_student_id;
    END IF;

    -- Generate a bcrypt hash compatible with passlib. 
    -- 'bf' specifies the Blowfish algorithm (bcrypt).
    -- 12 is the cost factor (salt rounds), matching your Python config.
    v_password_hash := crypt(p_plain_password, gen_salt('bf', 12));

    -- Insert the new user into the users table with the hashed password
    INSERT INTO exam_system.users (
        email, 
        first_name, 
        last_name, 
        password_hash, -- Storing the generated hash
        is_active, 
        is_superuser, 
        created_at, 
        updated_at, 
        role
    )
    VALUES (
        p_email,
        v_first_name,
        v_last_name,
        v_password_hash, -- Use the hashed password variable here
        TRUE, 
        FALSE, 
        NOW(), 
        NOW(), 
        'student'::exam_system.user_role_enum
    )
    RETURNING id INTO v_user_id;

    -- Update the students table to link the new user
    UPDATE exam_system.students
    SET user_id = v_user_id
    WHERE id = p_student_id;

    -- Return the ID of the newly created user
    RETURN v_user_id;
END;
$$;


ALTER FUNCTION exam_system.create_student_user(p_student_id uuid, p_email character varying, p_plain_password character varying) OWNER TO postgres;

--
-- Name: create_timetable_job(uuid, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_timetable_job(p_session_id uuid, p_initiated_by uuid, p_configuration_id uuid) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_job_id uuid;
BEGIN
    -- The INSERT statement is modified to include created_at and updated_at
    INSERT INTO exam_system.timetable_jobs (
        id,
        session_id,
        initiated_by,
        configuration_id,
        status,
        progress_percentage,
        hard_constraint_violations,
        can_pause,
        can_resume,
        can_cancel,
        created_at,  -- Added column
        updated_at   -- Added column
    ) VALUES (
        gen_random_uuid(),
        p_session_id,
        p_initiated_by,
        p_configuration_id,
        'queued',
        0,
        0,
        false,
        false,
        true,
        NOW(),  -- Set current timestamp
        NOW()   -- Set current timestamp
    ) RETURNING id INTO new_job_id;

    RETURN new_job_id;
END;
$$;


ALTER FUNCTION exam_system.create_timetable_job(p_session_id uuid, p_initiated_by uuid, p_configuration_id uuid) OWNER TO postgres;

--
-- Name: FUNCTION create_timetable_job(p_session_id uuid, p_initiated_by uuid, p_configuration_id uuid); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.create_timetable_job(p_session_id uuid, p_initiated_by uuid, p_configuration_id uuid) IS 'Creates a new timetable job, initializing all required fields including new job control flags.';


--
-- Name: create_upload_session(uuid, uuid, character varying, jsonb); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.create_upload_session(p_user_id uuid, p_session_id uuid, p_upload_type character varying, p_file_metadata jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_upload_session_id uuid;
    file_obj jsonb;
BEGIN
    -- Step 1: Create the main session record.
    -- The table's DEFAULT rules will now handle id, total_records, processed_records, etc.
    INSERT INTO exam_system.file_upload_sessions (
        uploaded_by,
        session_id,
        upload_type,
        status
    )
    VALUES (
        p_user_id,
        p_session_id,
        p_upload_type,
        'pending'
    )
    RETURNING id INTO new_upload_session_id;

    -- Step 2: Insert the file details into the 'uploaded_files' table.
    -- The table's DEFAULT rule will handle the 'id' for this table.
    FOR file_obj IN SELECT * FROM jsonb_array_elements(p_file_metadata)
    LOOP
        INSERT INTO exam_system.uploaded_files (
            upload_session_id,
            file_name,
            file_path,
            file_size,
            file_type,
            mime_type,
            row_count,
            validation_status
        )
        VALUES (
            new_upload_session_id,
            file_obj->>'file_name',
            file_obj->>'file_path',
            (file_obj->>'file_size')::bigint, -- Match the BIGINT type in the table
            'csv',
            file_obj->>'file_type',
            (file_obj->>'record_count')::integer,
            'pending'
        );
    END LOOP;

    -- Step 3: Return the ID of the new session.
    RETURN jsonb_build_object(
        'success', TRUE,
        'upload_session_id', new_upload_session_id
    );
EXCEPTION
    WHEN OTHERS THEN
        -- Log the error to the database console for debugging
        RAISE WARNING 'Error in create_upload_session: %', SQLERRM;
        RETURN jsonb_build_object('success', FALSE, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.create_upload_session(p_user_id uuid, p_session_id uuid, p_upload_type character varying, p_file_metadata jsonb) OWNER TO postgres;

--
-- Name: delete_course(uuid, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.delete_course(p_course_id uuid, p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    old_data jsonb;
BEGIN
    SELECT to_jsonb(c.*)
    INTO old_data
    FROM exam_system.courses c
    WHERE c.id = p_course_id AND c.session_id = p_session_id;

    IF old_data IS NOT NULL THEN
        PERFORM exam_system.log_audit_activity(p_user_id, 'delete', 'course', p_course_id, old_data, NULL);
        DELETE FROM exam_system.courses WHERE id = p_course_id AND session_id = p_session_id;
        RETURN jsonb_build_object('success', true);
    ELSE
        RETURN jsonb_build_object('success', false, 'error', 'Course not found in the specified session.');
    END IF;
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.delete_course(p_course_id uuid, p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: delete_exam(uuid, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.delete_exam(p_exam_id uuid, p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    old_data jsonb;
BEGIN
    SELECT to_jsonb(e.*)
    INTO old_data
    FROM exam_system.exams e
    WHERE e.id = p_exam_id AND e.session_id = p_session_id;

    IF old_data IS NOT NULL THEN
        PERFORM exam_system.log_audit_activity(p_user_id, 'delete', 'exam', p_exam_id, old_data, NULL);
        DELETE FROM exam_system.exams WHERE id = p_exam_id AND session_id = p_session_id;
        RETURN jsonb_build_object('success', true);
    ELSE
        RETURN jsonb_build_object('success', false, 'error', 'Exam not found in the specified session.');
    END IF;
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.delete_exam(p_exam_id uuid, p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: delete_room(uuid, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.delete_room(p_room_id uuid, p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    old_data jsonb;
BEGIN
    SELECT to_jsonb(r.*)
    INTO old_data
    FROM exam_system.rooms r
    WHERE r.id = p_room_id AND r.session_id = p_session_id;

    IF old_data IS NOT NULL THEN
        PERFORM exam_system.log_audit_activity(p_user_id, 'delete', 'room', p_room_id, old_data, NULL);
        DELETE FROM exam_system.rooms WHERE id = p_room_id AND session_id = p_session_id;
        RETURN jsonb_build_object('success', true);
    ELSE
        RETURN jsonb_build_object('success', false, 'error', 'Room not found in the specified session.');
    END IF;
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.delete_room(p_room_id uuid, p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: delete_scenario(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.delete_scenario(p_scenario_id uuid, p_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    deleted_scenario_id uuid;
BEGIN
    -- It's often better to archive than to delete permanently.
    UPDATE exam_system.timetable_scenarios
    SET archived_at = now()
    WHERE id = p_scenario_id
    RETURNING id INTO deleted_scenario_id;

    IF deleted_scenario_id IS NULL THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'Scenario not found.');
    END IF;

    -- Log this action
    PERFORM exam_system.log_audit_activity(
        p_user_id,
        'DELETE',
        'TIMETABLE_SCENARIO',
        'Scenario archived',
        p_entity_id := p_scenario_id
    );

    RETURN jsonb_build_object('status', 'success', 'message', 'Scenario successfully deleted.', 'scenario_id', deleted_scenario_id);
END;
$$;


ALTER FUNCTION exam_system.delete_scenario(p_scenario_id uuid, p_user_id uuid) OWNER TO postgres;

--
-- Name: delete_system_configuration(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.delete_system_configuration(p_config_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_constraint_config_id uuid;
    v_is_shared boolean;
BEGIN
    IF (SELECT is_default FROM exam_system.system_configurations WHERE id = p_config_id) THEN
        RAISE EXCEPTION 'Cannot delete the default system configuration.';
    END IF;
    
    SELECT constraint_config_id INTO v_constraint_config_id FROM exam_system.system_configurations WHERE id = p_config_id;

    DELETE FROM exam_system.system_configurations WHERE id = p_config_id;

    SELECT EXISTS (
        SELECT 1 FROM exam_system.system_configurations WHERE constraint_config_id = v_constraint_config_id
    ) INTO v_is_shared;

    IF NOT v_is_shared THEN
        DELETE FROM exam_system.constraint_configurations WHERE id = v_constraint_config_id;
    END IF;

    RETURN jsonb_build_object('success', true, 'message', 'System configuration deleted.');
END;
$$;


ALTER FUNCTION exam_system.delete_system_configuration(p_config_id uuid) OWNER TO postgres;

--
-- Name: delete_user(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.delete_user(p_user_id uuid, p_admin_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
BEGIN
    -- Retrieve the current state of the user for auditing
    SELECT to_jsonb(u) INTO v_old_data FROM exam_system.users u WHERE u.id = p_user_id;

    -- Check if user exists
    IF v_old_data IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found.');
    END IF;
    
    -- Perform a soft delete by setting the user to inactive
    UPDATE exam_system.users
    SET is_active = false, updated_at = NOW()
    WHERE id = p_user_id;

    -- Get the new state for the audit log
    SELECT to_jsonb(u) INTO v_new_data FROM exam_system.users u WHERE u.id = p_user_id;

    -- Log the audit activity
    PERFORM exam_system.log_audit_activity(
        p_user_id := p_admin_user_id,
        p_action := 'delete',
        p_entity_type := 'user',
        p_entity_id := p_user_id,
        p_old_values := v_old_data,
        p_new_values := v_new_data,
        p_notes := 'Admin performed a soft delete on the user.'
    );

    RETURN jsonb_build_object('success', true, 'message', 'User successfully deactivated.');
END;
$$;


ALTER FUNCTION exam_system.delete_user(p_user_id uuid, p_admin_user_id uuid) OWNER TO postgres;

--
-- Name: delete_user_preset(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.delete_user_preset(p_user_id uuid, p_preset_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_deleted_count INT;
BEGIN
    WITH deleted AS (
        DELETE FROM exam_system.user_filter_presets
        WHERE id = p_preset_id AND user_id = p_user_id
        RETURNING *
    )
    SELECT count(*) INTO v_deleted_count FROM deleted;

    IF v_deleted_count = 0 THEN
        RETURN jsonb_build_object('success', false, 'error', 'Preset not found or user does not have permission to delete it.');
    END IF;

    RETURN jsonb_build_object('success', true, 'message', 'Preset deleted successfully.');
END;
$$;


ALTER FUNCTION exam_system.delete_user_preset(p_user_id uuid, p_preset_id uuid) OWNER TO postgres;

--
-- Name: enforce_lowercase_role(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.enforce_lowercase_role() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Check if the role column exists and is not null before converting to lowercase
    IF NEW.role IS NOT NULL THEN
        NEW.role = lower(NEW.role);
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION exam_system.enforce_lowercase_role() OWNER TO postgres;

--
-- Name: generate_report(text, uuid, jsonb); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.generate_report(p_report_type text, p_session_id uuid, p_options jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF p_report_type = 'room_utilization' THEN
        RETURN (
            SELECT jsonb_agg(t) FROM (
                SELECT 
                    r.name as room_name,
                    b.name as building_name,
                    r.exam_capacity,
                    COALESCE(SUM(ta.student_count), 0) as total_students,
                    CASE WHEN r.exam_capacity > 0 
                         THEN ROUND((COALESCE(SUM(ta.student_count), 0) * 100.0) / (r.exam_capacity * (SELECT COUNT(DISTINCT (exam_date, time_slot_period)) FROM exam_system.timetable_assignments)), 2)
                         ELSE 0 END as utilization_percentage
                FROM exam_system.rooms r
                JOIN exam_system.buildings b ON r.building_id = b.id
                LEFT JOIN exam_system.timetable_assignments ta ON r.id = ta.room_id
                WHERE (p_options->>'building_id' IS NULL OR b.id = (p_options->>'building_id')::UUID)
                GROUP BY r.id, b.id
            ) t
        );
    ELSIF p_report_type = 'instructor_assignments' THEN
        RETURN (
            SELECT jsonb_agg(t) FROM (
                SELECT
                    s.first_name || ' ' || s.last_name as instructor_name,
                    d.name as department_name,
                    COUNT(ei.id) as total_assignments,
                    SUM(e.duration_minutes) / 60.0 as total_hours
                FROM exam_system.staff s
                JOIN exam_system.exam_invigilators ei ON s.id = ei.staff_id
                JOIN exam_system.timetable_assignments ta ON ei.timetable_assignment_id = ta.id
                JOIN exam_system.exams e ON ta.exam_id = e.id
                JOIN exam_system.departments d ON s.department_id = d.id
                WHERE e.session_id = p_session_id
                  AND (p_options->>'department_id' IS NULL OR s.department_id = (p_options->>'department_id')::UUID)
                GROUP BY s.id, d.id
            ) t
        );
    END IF;

    -- Add other report types like 'student_schedules' and 'conflicts_analysis' here
    
    RETURN '[]'::jsonb;
END;
$$;


ALTER FUNCTION exam_system.generate_report(p_report_type text, p_session_id uuid, p_options jsonb) OWNER TO postgres;

--
-- Name: get_active_academic_session(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_active_academic_session() RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'id', id,
        'name', name,
        'semester_system', semester_system,
        'start_date', start_date,
        'end_date', end_date
    )
    INTO v_result
    FROM exam_system.academic_sessions
    WHERE is_active = true
    -- Assuming business logic enforces only one active session at a time,
    -- but LIMIT 1 ensures the function doesn't fail if multiple exist.
    LIMIT 1;

    RETURN v_result;
END;
$$;


ALTER FUNCTION exam_system.get_active_academic_session() OWNER TO postgres;

--
-- Name: FUNCTION get_active_academic_session(); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.get_active_academic_session() IS 'Returns the details of the currently active academic session as a JSON object.';


--
-- Name: get_admin_notifications(character varying); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_admin_notifications(p_status character varying DEFAULT NULL::character varying) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN (
        SELECT COALESCE(jsonb_agg(
            jsonb_build_object(
                'notification_id', un.id,
                'event_title', se.title,
                'message', se.message,
                'priority', se.priority,
                'is_read', un.is_read,
                'created_at', se.created_at
            )
        ), '[]'::jsonb)
        FROM exam_system.user_notifications un
        JOIN exam_system.system_events se ON un.event_id = se.id
        JOIN exam_system.users u ON un.user_id = u.id
        JOIN exam_system.user_role_assignments ura ON u.id = ura.user_id
        JOIN exam_system.user_roles ur ON ura.role_id = ur.id
        WHERE ur.name = 'Administrator' -- Or some other logic to identify admins
          AND (p_status IS NULL OR (p_status = 'read' AND un.is_read = TRUE) OR (p_status = 'unread' AND un.is_read = FALSE))
    );
END;
$$;


ALTER FUNCTION exam_system.get_admin_notifications(p_status character varying) OWNER TO postgres;

--
-- Name: get_all_reports_and_requests(integer, text[], timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_all_reports_and_requests(p_limit integer DEFAULT NULL::integer, p_statuses text[] DEFAULT NULL::text[], p_start_date timestamp with time zone DEFAULT NULL::timestamp with time zone, p_end_date timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'exam_system', 'public'
    AS $$
DECLARE
    final_result jsonb;
BEGIN
    -- CTE for calculating summary counts across all records, independent of filters
    WITH summary_counts AS (
        SELECT
            (SELECT COUNT(*) FROM exam_system.conflict_reports) +
            (SELECT COUNT(*) FROM exam_system.assignment_change_requests) AS total_notifications,

            -- Unread/Urgent are defined as items with a 'pending' status
            (SELECT COUNT(*) FROM exam_system.conflict_reports WHERE status = 'pending') +
            (SELECT COUNT(*) FROM exam_system.assignment_change_requests WHERE status = 'pending') AS unread_notifications
    ),

    -- CTE for fetching and formatting Student Conflict Reports with filtering and limiting
    conflict_data AS (
        SELECT 
            cr.id,
            cr.status,
            cr.description,
            cr.submitted_at,
            cr.reviewed_at,
            jsonb_build_object(
                'id', s.id,
                'matric_number', s.matric_number,
                'first_name', s.first_name,
                'last_name', s.last_name,
                'email', u_stu.email
            ) AS student,
            jsonb_build_object(
                'exam_id', e.id,
                'course_code', c.code,
                'course_title', c.title,
                'session_name', asess.name
            ) AS exam_details,
            CASE WHEN cr.reviewed_by IS NOT NULL THEN
                jsonb_build_object(
                    'reviewed_by_user_id', u_rev.id,
                    'reviewer_email', u_rev.email,
                    'reviewer_name', u_rev.first_name || ' ' || u_rev.last_name,
                    'resolver_notes', cr.resolver_notes
                )
            ELSE NULL END AS review_details
        FROM exam_system.conflict_reports cr
        JOIN exam_system.students s ON cr.student_id = s.id
        LEFT JOIN exam_system.users u_stu ON s.user_id = u_stu.id
        JOIN exam_system.exams e ON cr.exam_id = e.id
        JOIN exam_system.courses c ON e.course_id = c.id
        JOIN exam_system.academic_sessions asess ON e.session_id = asess.id
        LEFT JOIN exam_system.users u_rev ON cr.reviewed_by = u_rev.id
        WHERE
            -- Apply filters only if parameters are not NULL
            (p_statuses IS NULL OR cr.status = ANY(p_statuses))
            AND (p_start_date IS NULL OR cr.submitted_at >= p_start_date)
            AND (p_end_date IS NULL OR cr.submitted_at <= p_end_date)
        ORDER BY cr.submitted_at DESC
        LIMIT p_limit -- Apply limit if provided
    ),
    
    -- CTE for fetching and formatting Staff Assignment Change Requests with filtering and limiting
    request_data AS (
        SELECT 
            acr.id,
            acr.status,
            acr.reason,
            acr.description,
            acr.submitted_at,
            acr.reviewed_at,
            jsonb_build_object(
                'id', st.id,
                'staff_number', st.staff_number,
                'first_name', st.first_name,
                'last_name', st.last_name,
                'email', u_st.email,
                'department_code', d.code
            ) AS staff,
            jsonb_build_object(
                'assignment_id', ta.id,
                'exam_date', ta.exam_date,
                'course_code', c.code,
                'course_title', c.title,
                'room_code', r.code,
                'room_name', r.name
            ) AS assignment_details,
            CASE WHEN acr.reviewed_by IS NOT NULL THEN
                jsonb_build_object(
                    'reviewed_by_user_id', u_rev.id,
                    'reviewer_email', u_rev.email,
                    'reviewer_name', u_rev.first_name || ' ' || u_rev.last_name,
                    'review_notes', acr.review_notes
                )
            ELSE NULL END AS review_details
        FROM exam_system.assignment_change_requests acr
        JOIN exam_system.staff st ON acr.staff_id = st.id
        LEFT JOIN exam_system.users u_st ON st.user_id = u_st.id
        LEFT JOIN exam_system.departments d ON st.department_id = d.id
        JOIN exam_system.timetable_assignments ta ON acr.timetable_assignment_id = ta.id
        JOIN exam_system.exams e ON ta.exam_id = e.id
        JOIN exam_system.courses c ON e.course_id = c.id
        JOIN exam_system.rooms r ON ta.room_id = r.id
        LEFT JOIN exam_system.users u_rev ON acr.reviewed_by = u_rev.id
        WHERE
            -- Apply filters only if parameters are not NULL
            (p_statuses IS NULL OR acr.status = ANY(p_statuses))
            AND (p_start_date IS NULL OR acr.submitted_at >= p_start_date)
            AND (p_end_date IS NULL OR acr.submitted_at <= p_end_date)
        ORDER BY acr.submitted_at DESC
        LIMIT p_limit -- Apply limit if provided
    )

    -- Aggregate all CTEs into the final JSON structure
    SELECT jsonb_build_object(
        'summary_counts', jsonb_build_object(
            'total', sc.total_notifications,
            'unread', sc.unread_notifications,
            'urgent_action_required', sc.unread_notifications -- Urgent is synonymous with unread ('pending')
        ),
        'conflict_reports', COALESCE(
            (SELECT jsonb_agg(to_jsonb(cd)) FROM conflict_data cd), 
            '[]'::jsonb
        ),
        'assignment_change_requests', COALESCE(
            (SELECT jsonb_agg(to_jsonb(rd)) FROM request_data rd), 
            '[]'::jsonb
        )
    )
    INTO final_result
    FROM summary_counts sc;

    RETURN final_result;
END;
$$;


ALTER FUNCTION exam_system.get_all_reports_and_requests(p_limit integer, p_statuses text[], p_start_date timestamp with time zone, p_end_date timestamp with time zone) OWNER TO postgres;

--
-- Name: get_all_roles_with_permissions(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_all_roles_with_permissions() RETURNS jsonb
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN (
        SELECT jsonb_agg(to_jsonb(row))
        FROM exam_system.user_roles row
    );
END;
$$;


ALTER FUNCTION exam_system.get_all_roles_with_permissions() OWNER TO postgres;

--
-- Name: get_all_scenarios(integer, integer); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_all_scenarios(p_page integer, p_page_size integer) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'page', p_page,
        'page_size', p_page_size,
        'total_count', (SELECT COUNT(*) FROM exam_system.timetable_scenarios WHERE archived_at IS NULL),
        'scenarios', COALESCE(jsonb_agg(
            jsonb_build_object(
                'id', ts.id,
                'name', ts.name,
                'description', ts.description,
                'created_by', u.email,
                'created_at', ts.created_at,
                'parent_version_id', ts.parent_version_id
            )
        ), '[]'::jsonb)
    )
    INTO result
    FROM exam_system.timetable_scenarios ts
    JOIN exam_system.users u ON ts.created_by = u.id
    WHERE ts.archived_at IS NULL
    ORDER BY ts.created_at DESC
    LIMIT p_page_size
    OFFSET (p_page - 1) * p_page_size;

    RETURN result;
END;
$$;


ALTER FUNCTION exam_system.get_all_scenarios(p_page integer, p_page_size integer) OWNER TO postgres;

--
-- Name: get_all_system_configurations(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_all_system_configurations() RETURNS jsonb
    LANGUAGE sql STABLE
    AS $$
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'id', sc.id,
            'name', sc.name,
            'description', sc.description,
            'is_default', sc.is_default
        ) ORDER BY sc.name
    ), '[]'::jsonb)
    FROM exam_system.system_configurations sc;
$$;


ALTER FUNCTION exam_system.get_all_system_configurations() OWNER TO postgres;

--
-- Name: FUNCTION get_all_system_configurations(); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.get_all_system_configurations() IS 'Retrieves a list of all available system configurations (solver settings + constraint profile link).';


--
-- Name: get_audit_history(integer, integer, text, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_audit_history(p_page integer, p_page_size integer, p_entity_type text DEFAULT NULL::text, p_entity_id uuid DEFAULT NULL::uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN (
        SELECT jsonb_build_object(
            'page', p_page,
            'page_size', p_page_size,
            'total_count', COUNT(*) OVER(),
            'logs', COALESCE(jsonb_agg(
                jsonb_build_object(
                    'id', al.id,
                    'user', u.email,
                    'action', al.action,
                    'entity_type', al.entity_type,
                    'entity_id', al.entity_id,
                    'notes', al.notes,
                    'created_at', al.created_at,
                    'old_values', al.old_values,
                    'new_values', al.new_values
                ) ORDER BY al.created_at DESC
            ), '[]'::jsonb)
        )
        FROM exam_system.audit_logs al
        JOIN exam_system.users u ON al.user_id = u.id
        WHERE (p_entity_type IS NULL OR al.entity_type = p_entity_type)
          AND (p_entity_id IS NULL OR al.entity_id = p_entity_id)
        LIMIT p_page_size
        OFFSET (p_page - 1) * p_page_size
    );
END;
$$;


ALTER FUNCTION exam_system.get_audit_history(p_page integer, p_page_size integer, p_entity_type text, p_entity_id uuid) OWNER TO postgres;

--
-- Name: get_conflict_hotspots(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_conflict_hotspots(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_latest_version_id uuid;
    v_latest_job_data jsonb;
    v_conflict_item jsonb;
    v_assignments jsonb;
    v_assignment jsonb;
    v_hotspots jsonb;
BEGIN
    -- Step 1: Get the latest published version and its job data
    SELECT tv.id, tj.result_data INTO v_latest_version_id, v_latest_job_data
    FROM exam_system.timetable_versions tv
    JOIN exam_system.timetable_jobs tj ON tv.job_id = tj.id
    WHERE tv.is_published = TRUE
      AND tj.session_id = p_session_id
    ORDER BY tv.created_at DESC
    LIMIT 1;

    -- Clear old conflicts for this version to prevent duplicates
    DELETE FROM exam_system.timetable_conflicts WHERE version_id = v_latest_version_id;

    -- Step 2: Parse conflicts from the JSON and insert them into the table
    FOR v_conflict_item IN SELECT * FROM jsonb_array_elements(v_latest_job_data -> 'solution' -> 'conflicts')
    LOOP
        INSERT INTO exam_system.timetable_conflicts (version_id, type, severity, message, details, is_resolved)
        VALUES (
            v_latest_version_id,
            v_conflict_item ->> 'type',
            v_conflict_item ->> 'severity',
            v_conflict_item ->> 'message',
            v_conflict_item -> 'details',
            FALSE
        );
    END LOOP;

    -- Step 3: Aggregate conflicts by time slot to find hotspots
    v_assignments := v_latest_job_data -> 'solution' -> 'assignments';
    
    SELECT jsonb_agg(hotspot)
    FROM (
        SELECT 
            TO_CHAR(TO_DATE(value ->> 'date', 'YYYY-MM-DD'), 'Dy') || ' ' || (value ->> 'start_time') as timeslot,
            COUNT(*) as conflict_count
        FROM jsonb_each(v_assignments) as assignments(key, value)
        WHERE jsonb_array_length(value -> 'conflicts') > 0
        GROUP BY timeslot
        ORDER BY conflict_count DESC
        LIMIT 5
    ) as hotspot INTO v_hotspots;
    
    RETURN COALESCE(v_hotspots, '[]'::jsonb);
END;
$$;


ALTER FUNCTION exam_system.get_conflict_hotspots(p_session_id uuid) OWNER TO postgres;

--
-- Name: get_dashboard_analytics(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_dashboard_analytics(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
    v_latest_job_data jsonb;
    v_kpis jsonb;
    v_conflict_hotspots jsonb;
    v_top_bottlenecks jsonb;
    v_recent_activity jsonb;
BEGIN
    -- Step 1: Find the result_data from the latest published and completed timetable job for the session.
    SELECT
        tj.result_data INTO v_latest_job_data
    FROM
        exam_system.timetable_versions tv
    JOIN
        exam_system.timetable_jobs tj ON tv.job_id = tj.id
    WHERE
        tv.is_published = TRUE
        AND tj.session_id = p_session_id
        AND tj.status = 'completed'
    ORDER BY
        tv.updated_at DESC
    LIMIT 1;

    -- Step 2: If no suitable job result is found, return a default structure with zeroed values.
    IF v_latest_job_data IS NULL THEN
        RETURN jsonb_build_object(
            'kpis', jsonb_build_object(
                'total_exams_scheduled', 0,
                'unresolved_hard_conflicts', 0,
                'total_soft_conflicts', 0,
                'overall_room_utilization', 0.0
            ),
            'conflict_hotspots', '[]'::jsonb,
            'top_bottlenecks', '[]'::jsonb,
            'recent_activity', '[]'::jsonb
        );
    END IF;

    -- Step 3: Extract KPIs directly from the 'solution' object within the JSON data.
    v_kpis := jsonb_build_object(
        'total_exams_scheduled', COALESCE((v_latest_job_data -> 'solution' -> 'statistics' ->> 'total_exams')::integer, 0),
        'unresolved_hard_conflicts', COALESCE((v_latest_job_data -> 'solution' -> 'quality_metrics' ->> 'hard_constraint_violations')::integer, 0),
        'total_soft_conflicts', COALESCE((v_latest_job_data -> 'solution' -> 'quality_metrics' ->> 'total_soft_constraint_penalty')::numeric::integer, 0),
        'overall_room_utilization', COALESCE((v_latest_job_data -> 'solution' -> 'statistics' ->> 'room_utilization_percentage')::numeric, 0.0)
    );

    -- Step 4: Calculate Conflict Hotspots by analyzing the 'assignments' within the JSON data.
    SELECT
        COALESCE(jsonb_agg(hotspot ORDER BY total_conflicts_in_slot DESC), '[]'::jsonb)
    INTO
        v_conflict_hotspots
    FROM (
        SELECT
            jsonb_build_object(
                'timeslot', (value ->> 'date') || ' ' || (value ->> 'start_time'),
                'conflict_count', SUM(jsonb_array_length(value -> 'conflicts'))
            ) AS hotspot,
            SUM(jsonb_array_length(value -> 'conflicts')) as total_conflicts_in_slot
        FROM
            jsonb_each(v_latest_job_data -> 'solution' -> 'assignments') AS assignments(key, value)
        WHERE
            jsonb_array_length(value -> 'conflicts') > 0
        GROUP BY
            (value ->> 'date'), (value ->> 'start_time')
        LIMIT 5
    ) AS hotspots;

    -- Step 5: Identify Top Bottlenecks from the conflict report summary in the JSON data.
    SELECT
        COALESCE(jsonb_agg(
            jsonb_build_object(
                'type', 'Conflict Type',
                'name', key,
                'issue', 'Number of violations',
                'value', value
            )
        ), '[]'::jsonb)
    INTO
        v_top_bottlenecks
    FROM
        jsonb_each_text(v_latest_job_data -> 'solution' -> 'quality_metrics' -> 'conflict_report');

    -- Step 6: Get the 5 most recent activities from the audit log (this is independent of the job data).
    SELECT
        COALESCE(jsonb_agg(activity ORDER BY created_at DESC), '[]'::jsonb)
    INTO
        v_recent_activity
    FROM (
        SELECT
            jsonb_build_object(
                'user', u.first_name || ' ' || u.last_name,
                'action', al.notes,
                'timestamp', al.created_at
            ) AS activity,
            al.created_at
        FROM
            exam_system.audit_logs al
        JOIN
            exam_system.users u ON al.user_id = u.id
        ORDER BY
            al.created_at DESC
        LIMIT 5
    ) AS recent_logs;

    -- Step 7: Assemble and return the complete dashboard analytics payload.
    RETURN jsonb_build_object(
        'kpis', v_kpis,
        'conflict_hotspots', v_conflict_hotspots,
        'top_bottlenecks', v_top_bottlenecks,
        'recent_activity', v_recent_activity
    );
END;
$$;


ALTER FUNCTION exam_system.get_dashboard_analytics(p_session_id uuid) OWNER TO postgres;

--
-- Name: get_dashboard_kpis(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_dashboard_kpis(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
    v_latest_job_data jsonb;
    v_kpis jsonb;
BEGIN
    -- Step 1: Find the result_data from the latest published timetable version for the given session
    SELECT tj.result_data INTO v_latest_job_data
    FROM exam_system.timetable_versions tv
    JOIN exam_system.timetable_jobs tj ON tv.job_id = tj.id
    WHERE tv.is_published = TRUE
      AND tj.session_id = p_session_id
      AND tj.status = 'completed'
    ORDER BY tv.created_at DESC
    LIMIT 1;

    -- Step 1.5: If no published job is found, return zeros
    IF v_latest_job_data IS NULL THEN
        RETURN jsonb_build_object(
            'total_exams_scheduled', 0,
            'unresolved_hard_conflicts', 0,
            'total_soft_conflicts', 0,
            'overall_room_utilization', 0.0
        );
    END IF;

    -- Step 2: Extract and structure the KPIs from the JSON data
    -- FIX: The data is nested under a 'solution' key within 'result_data'
    -- FIX: Cast total_soft_constraint_penalty to numeric before casting to integer to handle decimal values like "0.0".
    SELECT jsonb_build_object(
        'total_exams_scheduled', COALESCE((v_latest_job_data -> 'solution' -> 'statistics' ->> 'total_exams')::integer, 0),
        'unresolved_hard_conflicts', COALESCE((v_latest_job_data -> 'solution' -> 'quality_metrics' ->> 'hard_constraint_violations')::integer, 0),
        'total_soft_conflicts', COALESCE((v_latest_job_data -> 'solution' -> 'quality_metrics' ->> 'total_soft_constraint_penalty')::numeric::integer, 0),
        'overall_room_utilization', COALESCE((v_latest_job_data -> 'solution' -> 'statistics' ->> 'room_utilization_percentage')::numeric, 0.0)
    ) INTO v_kpis;

    -- Step 3: Return the structured KPI data
    RETURN v_kpis;
END;
$$;


ALTER FUNCTION exam_system.get_dashboard_kpis(p_session_id uuid) OWNER TO postgres;

--
-- Name: get_entity_by_id(text, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_entity_by_id(p_entity_type text, p_entity_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    result_json jsonb;
    table_name TEXT;
BEGIN
    -- Map the entity type to its corresponding table name to prevent SQL injection
    table_name := CASE
        WHEN p_entity_type = 'course' THEN 'courses'
        WHEN p_entity_type = 'exam' THEN 'exams'
        WHEN p_entity_type = 'room' THEN 'rooms'
        ELSE NULL
    END;

    IF table_name IS NULL THEN
        RAISE EXCEPTION 'Invalid entity type provided: %', p_entity_type;
    END IF;

    -- Dynamically execute the query to fetch the record
    EXECUTE format(
        'SELECT to_jsonb(t) FROM exam_system.%I t WHERE id = %L',
        table_name,
        p_entity_id
    ) INTO result_json;

    RETURN result_json;
END;
$$;


ALTER FUNCTION exam_system.get_entity_by_id(p_entity_type text, p_entity_id uuid) OWNER TO postgres;

--
-- Name: get_entity_data_as_json(text, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_entity_data_as_json(p_entity_type text, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    result jsonb;
BEGIN
    -- This function now requires a session_id to retrieve session-specific data.
    CASE p_entity_type
        WHEN 'courses' THEN
            SELECT jsonb_agg(to_jsonb(t)) INTO result FROM exam_system.courses t WHERE t.session_id = p_session_id;
        WHEN 'students' THEN
            SELECT jsonb_agg(to_jsonb(t)) INTO result FROM exam_system.students t WHERE t.session_id = p_session_id;
        WHEN 'staff' THEN
            SELECT jsonb_agg(to_jsonb(t)) INTO result FROM exam_system.staff t WHERE t.session_id = p_session_id;
        WHEN 'rooms' THEN
            SELECT jsonb_agg(to_jsonb(t)) INTO result FROM exam_system.rooms t WHERE t.session_id = p_session_id;
        WHEN 'departments' THEN
            SELECT jsonb_agg(to_jsonb(t)) INTO result FROM exam_system.departments t WHERE t.session_id = p_session_id;
        ELSE
            -- Default to empty if the entity type is not session-specific or unknown.
            result := '[]'::jsonb;
    END CASE;
    RETURN result;
END;
$$;


ALTER FUNCTION exam_system.get_entity_data_as_json(p_entity_type text, p_session_id uuid) OWNER TO postgres;

--
-- Name: get_full_timetable_with_details(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_full_timetable_with_details(p_version_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN (
        SELECT jsonb_agg(ta_details)
        FROM (
            SELECT
                ta.id AS assignment_id,
                e.id AS exam_id,
                c.code AS course_code,
                c.title AS course_name,
                d.name AS department_name,
                ed.exam_date AS date,
                ts.start_time,
                ts.end_time,
                e.duration_minutes,
                ta.student_count,
                r.id AS room_id,
                r.name AS room_name,
                r.exam_capacity AS room_capacity,
                b.name AS building_name,
                (
                    SELECT jsonb_agg(jsonb_build_object('id', s.id, 'name', s.first_name || ' ' || s.last_name, 'role', ei.role))
                    FROM exam_system.exam_invigilators ei
                    JOIN exam_system.staff s ON ei.staff_id = s.id
                    WHERE ei.timetable_assignment_id = ta.id
                ) AS invigilators
            FROM exam_system.timetable_assignments ta
            JOIN exam_system.exams e ON ta.exam_id = e.id
            JOIN exam_system.courses c ON e.course_id = c.id
            JOIN exam_system.departments d ON c.department_id = d.id
            JOIN exam_system.time_slots ts ON ta.time_slot_id = ts.id
            JOIN exam_system.exam_days ed ON ts.day_id = ed.id
            JOIN exam_system.rooms r ON ta.room_id = r.id
            JOIN exam_system.buildings b ON r.building_id = b.id
            WHERE ta.version_id = p_version_id
        ) AS ta_details
    );
END;
$$;


ALTER FUNCTION exam_system.get_full_timetable_with_details(p_version_id uuid) OWNER TO postgres;

--
-- Name: FUNCTION get_full_timetable_with_details(p_version_id uuid); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.get_full_timetable_with_details(p_version_id uuid) IS 'Retrieves a fully detailed timetable, including precise times, for rendering on the frontend grid.';


--
-- Name: get_history_page_data(integer, integer); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_history_page_data(p_page integer DEFAULT 1, p_page_size integer DEFAULT 20) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN (
        WITH activities AS (
            SELECT
                al.id,
                al.notes,
                al.action,
                al.entity_type,
                al.created_at,
                u.first_name || ' ' || u.last_name as user_name
            FROM exam_system.audit_logs al
            JOIN exam_system.users u ON al.user_id = u.id
            ORDER BY al.created_at DESC
        )
        SELECT jsonb_build_object(
            'kpis', (
                SELECT jsonb_build_object(
                    'total_activities', (SELECT COUNT(*) FROM exam_system.audit_logs),
                    'active_users', (SELECT COUNT(DISTINCT user_id) FROM exam_system.audit_logs WHERE created_at >= now() - interval '24 hours'),
                    'todays_activities', (SELECT COUNT(*) FROM exam_system.audit_logs WHERE created_at >= current_date),
                    'entity_types', (SELECT COUNT(DISTINCT entity_type) FROM exam_system.audit_logs)
                )
            ),
            'activities', (SELECT COALESCE(jsonb_agg(a), '[]'::jsonb) FROM (SELECT * FROM activities LIMIT p_page_size OFFSET (p_page - 1) * p_page_size) a),
            'pagination', jsonb_build_object(
                'current_page', p_page,
                'total_pages', CEIL((SELECT COUNT(*) FROM activities)::numeric / p_page_size),
                'total_count', (SELECT COUNT(*) FROM activities)
            )
        )
    );
END;
$$;


ALTER FUNCTION exam_system.get_history_page_data(p_page integer, p_page_size integer) OWNER TO postgres;

--
-- Name: get_job_status(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_job_status(p_job_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    job_status_details jsonb;
BEGIN
    SELECT
        row_to_json(tj)
    INTO
        job_status_details
    FROM
        exam_system.timetable_jobs AS tj
    WHERE
        tj.id = p_job_id; -- Corrected from tj.job_id to tj.id

    RETURN job_status_details;
END;
$$;


ALTER FUNCTION exam_system.get_job_status(p_job_id uuid) OWNER TO postgres;

--
-- Name: get_latest_successful_timetable_job(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_latest_successful_timetable_job(p_session_id uuid) RETURNS uuid
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
    v_job_id uuid;
BEGIN
    SELECT id
    INTO v_job_id
    FROM exam_system.timetable_jobs
    WHERE session_id = p_session_id
      AND LOWER(status) = 'completed'
      -- CORRECTED: Check for both 'feasible' and 'optimal' statuses
      AND result_data -> 'solution' ->> 'status' IN ('feasible', 'optimal')
    ORDER BY completed_at DESC
    LIMIT 1;

    RETURN v_job_id;
END;
$$;


ALTER FUNCTION exam_system.get_latest_successful_timetable_job(p_session_id uuid) OWNER TO postgres;

--
-- Name: FUNCTION get_latest_successful_timetable_job(p_session_id uuid); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.get_latest_successful_timetable_job(p_session_id uuid) IS 'Returns the UUID of the most recently successfully completed timetable job for the specified session.';


--
-- Name: get_paginated_entities(text, integer, integer, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_paginated_entities(p_entity_type text, p_page integer, p_page_size integer, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    result_json jsonb;
    table_name TEXT;
    offset_val INT;
    total_count INT;
    data_json jsonb;
BEGIN
    -- Map the entity type to its corresponding table name
    table_name := CASE
        WHEN p_entity_type = 'academic_sessions' THEN 'academic_sessions'
        WHEN p_entity_type = 'courses' THEN 'courses'
        WHEN p_entity_type = 'exams' THEN 'exams'
        WHEN p_entity_type = 'rooms' THEN 'rooms'
        ELSE NULL
    END;

    IF table_name IS NULL THEN
        RAISE EXCEPTION 'Invalid entity type provided: %', p_entity_type;
    END IF;

    offset_val := (p_page - 1) * p_page_size;

    -- Get the total number of records in the table, filtered by the session ID.
    EXECUTE format('SELECT count(*) FROM exam_system.%I WHERE session_id = %L', table_name, p_session_id) INTO total_count;

    -- Get the data for the current page, filtered by the session ID.
    EXECUTE format(
        'SELECT COALESCE(jsonb_agg(t), ''[]''::jsonb) FROM (SELECT * FROM exam_system.%I WHERE session_id = %L ORDER BY created_at DESC LIMIT %L OFFSET %L) t',
        table_name,
        p_session_id,
        p_page_size,
        offset_val
    ) INTO data_json;

    -- Assemble the final JSON response with pagination metadata
    result_json := jsonb_build_object(
        'total', total_count,
        'page', p_page,
        'page_size', p_page_size,
        'data', data_json
    );

    RETURN result_json;
END;
$$;


ALTER FUNCTION exam_system.get_paginated_entities(p_entity_type text, p_page integer, p_page_size integer, p_session_id uuid) OWNER TO postgres;

--
-- Name: get_portal_data(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_portal_data(p_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_user_role TEXT;
    v_role_specific_id UUID; -- Will hold either student_id or staff_id
    v_active_session_id UUID;
    v_latest_job_id UUID;
    v_portal_payload JSONB;
BEGIN
    -- Step 1: Find the currently active academic session.
    SELECT id INTO v_active_session_id
    FROM exam_system.academic_sessions
    WHERE is_active = TRUE
    LIMIT 1;

    IF v_active_session_id IS NULL THEN
        RETURN jsonb_build_object('error', 'No active academic session found.');
    END IF;

    -- Step 2: Determine the user's role (student, staff, or other) within the active session.
    -- MODIFIED: Lookups are now scoped to the active session ID.
    SELECT 'student', s.id INTO v_user_role, v_role_specific_id
    FROM exam_system.students s WHERE s.user_id = p_user_id AND s.session_id = v_active_session_id;

    IF NOT FOUND THEN
        SELECT 'staff', st.id INTO v_user_role, v_role_specific_id
        FROM exam_system.staff st WHERE st.user_id = p_user_id AND st.session_id = v_active_session_id;
    END IF;

    IF v_user_role IS NULL THEN
        RETURN jsonb_build_object('user_type', 'admin', 'message', 'User has no student or staff role in the active session.');
    END IF;

    -- Step 3: Find the job ID associated with the latest published timetable version for the active session.
    SELECT tv.job_id INTO v_latest_job_id
    FROM exam_system.timetable_versions tv
    JOIN exam_system.timetable_jobs tj ON tv.job_id = tj.id
    WHERE tj.session_id = v_active_session_id
      AND tv.is_published = TRUE
      AND tj.status = 'completed'
    ORDER BY tv.created_at DESC
    LIMIT 1;
    
    IF v_latest_job_id IS NULL THEN
        SELECT id INTO v_latest_job_id
        FROM exam_system.timetable_jobs
        WHERE session_id = v_active_session_id
          AND status = 'completed'
        ORDER BY completed_at DESC
        LIMIT 1;
    END IF;

    IF v_latest_job_id IS NULL THEN
        RETURN jsonb_build_object('error', 'No published or completed timetable found for the active session.');
    END IF;

    -- Step 4: Build the role-specific data payload. (No changes needed here as subqueries use the correct session ID)
    IF v_user_role = 'student' THEN
        WITH student_exams AS (
            SELECT e.id
            FROM exam_system.course_registrations cr
            JOIN exam_system.exams e ON cr.course_id = e.course_id AND cr.session_id = e.session_id
            WHERE cr.student_id = v_role_specific_id
              AND cr.session_id = v_active_session_id
        ),
        student_schedule AS (
            SELECT COALESCE(jsonb_agg(assignment.value), '[]'::jsonb) AS schedule
            FROM exam_system.timetable_jobs tj,
                 jsonb_each(tj.result_data->'solution'->'assignments') AS assignment
            WHERE tj.id = v_latest_job_id
              AND assignment.key IN (SELECT id::text FROM student_exams)
        ),
        conflict_reports AS (
            SELECT COALESCE(jsonb_agg(cr.* ORDER BY cr.submitted_at DESC), '[]'::jsonb) AS reports
            FROM exam_system.conflict_reports cr
            WHERE cr.student_id = v_role_specific_id
        )
        SELECT jsonb_build_object('schedule', ss.schedule, 'conflict_reports', cr.reports)
        INTO v_portal_payload
        FROM student_schedule ss, conflict_reports cr;

    ELSIF v_user_role = 'staff' THEN
        WITH staff_schedules AS (
            SELECT
                COALESCE(jsonb_agg(assignment.value) FILTER (WHERE assignment.value->'instructor_ids' @> to_jsonb(v_role_specific_id::text)), '[]'::jsonb) AS instructor_schedule,
                COALESCE(jsonb_agg(assignment.value) FILTER (WHERE EXISTS (
                    SELECT 1 FROM jsonb_array_elements(assignment.value->'invigilators') AS inv WHERE (inv->>'id')::uuid = v_role_specific_id
                )), '[]'::jsonb) AS invigilator_schedule
            FROM exam_system.timetable_jobs tj, jsonb_each(tj.result_data->'solution'->'assignments') AS assignment
            WHERE tj.id = v_latest_job_id
        ),
        change_requests AS (
            SELECT COALESCE(jsonb_agg(acr.* ORDER BY acr.submitted_at DESC), '[]'::jsonb) AS requests
            FROM exam_system.assignment_change_requests acr
            WHERE acr.staff_id = v_role_specific_id
        )
        SELECT jsonb_build_object('instructor_schedule', ss.instructor_schedule, 'invigilator_schedule', ss.invigilator_schedule, 'assignment_change_requests', cr.requests)
        INTO v_portal_payload
        FROM staff_schedules ss, change_requests cr;
    END IF;

    -- Step 5: Return the final payload.
    RETURN jsonb_build_object('user_type', v_user_role, 'data', v_portal_payload);
END;
$$;


ALTER FUNCTION exam_system.get_portal_data(p_user_id uuid) OWNER TO postgres;

--
-- Name: get_published_timetable_version(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_published_timetable_version(p_session_id uuid) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_version_id uuid;
BEGIN
    SELECT v.id
    INTO v_version_id
    FROM exam_system.timetable_versions v
    JOIN exam_system.timetable_jobs j ON v.job_id = j.id
    WHERE j.session_id = p_session_id
      AND v.is_published = true
    LIMIT 1; 

    RETURN v_version_id;
END;
$$;


ALTER FUNCTION exam_system.get_published_timetable_version(p_session_id uuid) OWNER TO postgres;

--
-- Name: FUNCTION get_published_timetable_version(p_session_id uuid); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.get_published_timetable_version(p_session_id uuid) IS 'Returns the UUID of the currently published timetable version for a given session.';


--
-- Name: get_room_schedule(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_room_schedule(p_room_id uuid, p_job_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN (
        SELECT jsonb_build_object(
            'room_id', r.id,
            'room_code', r.code,
            'room_name', r.name,
            'building_name', b.name,
            'job_id', p_job_id,
            'schedule', COALESCE(jsonb_agg(
                jsonb_build_object(
                    'exam_date', ta.exam_date,
                    'time_slot_period', ta.time_slot_period,
                    'course_code', c.code,
                    'course_title', c.title,
                    'student_count', ta.student_count
                ) ORDER BY ta.exam_date, ta.time_slot_period
            ) FILTER (WHERE ta.id IS NOT NULL), '[]'::jsonb)
        )
        FROM exam_system.rooms r
        LEFT JOIN exam_system.buildings b ON r.building_id = b.id
        LEFT JOIN exam_system.timetable_assignments ta ON r.id = ta.room_id
        LEFT JOIN exam_system.exams e ON ta.exam_id = e.id AND e.job_id = p_job_id
        LEFT JOIN exam_system.courses c ON e.course_id = c.id
        WHERE r.id = p_room_id
        GROUP BY r.id, b.name
    );
END;
$$;


ALTER FUNCTION exam_system.get_room_schedule(p_room_id uuid, p_job_id uuid) OWNER TO postgres;

--
-- Name: get_scenario_comparison_details(uuid[]); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_scenario_comparison_details(p_scenario_ids uuid[]) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    scenario_kpis jsonb;
    best_performer_id uuid;
BEGIN
    -- Step 1: Aggregate KPIs for the selected scenarios
    SELECT jsonb_agg(
        jsonb_build_object(
            'scenario_id', ts.id,
            'fitness_score', latest_job.fitness_score,
            'metrics', jsonb_build_object(
                'Total Exams', (SELECT COUNT(DISTINCT exam_id) FROM exam_system.timetable_assignments WHERE version_id = latest_job.id), -- Note: This assumes 1 version per job
                'Hard Conflicts', latest_job.hard_constraint_violations,
                'Soft Conflicts', latest_job.soft_constraints_violations,
                'Room Utilization', latest_job.room_utilization_percentage,
                'Overall Fitness Score', latest_job.fitness_score
            )
        )
    )
    INTO scenario_kpis
    FROM exam_system.timetable_scenarios ts
    LEFT JOIN LATERAL (
        SELECT *
        FROM exam_system.timetable_jobs tj
        WHERE tj.scenario_id = ts.id
        ORDER BY tj.created_at DESC
        LIMIT 1
    ) AS latest_job ON true
    WHERE ts.id = ANY(p_scenario_ids);

    -- Step 2: Determine the best performer
    SELECT s->>'scenario_id' INTO best_performer_id FROM jsonb_array_elements(scenario_kpis) s ORDER BY (s->>'fitness_score')::numeric DESC LIMIT 1;

    -- Step 3: Format the output as required by the frontend
    RETURN jsonb_build_object(
        'metrics', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'metric_name', m.key,
                    'values', (
                        SELECT jsonb_agg(
                            jsonb_build_object(
                                'scenario_id', v->>'scenario_id',
                                'value', v->'metrics'->>m.key
                            )
                        ) FROM jsonb_array_elements(scenario_kpis) v
                    )
                )
            )
            FROM (SELECT DISTINCT key FROM jsonb_array_elements(scenario_kpis) s, jsonb_object_keys(s->'metrics') AS key) AS m
        ),
        'best_performer', (SELECT jsonb_build_object('scenario_id', best_performer_id, 'reason', 'Highest overall fitness score.') FROM jsonb_array_elements(scenario_kpis) s WHERE s->>'scenario_id' = best_performer_id::text)
    );
END;
$$;


ALTER FUNCTION exam_system.get_scenario_comparison_details(p_scenario_ids uuid[]) OWNER TO postgres;

--
-- Name: get_scenarios_for_session(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_scenarios_for_session(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN COALESCE(jsonb_agg(scenarios), '[]'::jsonb) FROM (
        SELECT
            ts.id AS scenario_id,
            ts.name AS scenario_name,
            latest_job.status,
            ts.created_at,
            latest_job.total_runtime_seconds AS duration_seconds,
            latest_job.progress_percentage AS progress,
            jsonb_build_object(
                'hard_conflicts', latest_job.hard_constraint_violations,
                'soft_conflicts', latest_job.soft_constraints_violations,
                'room_util', latest_job.room_utilization_percentage,
                'fitness', latest_job.fitness_score
            ) AS kpis
        FROM exam_system.timetable_scenarios ts
        -- Find the latest job associated with each scenario
        LEFT JOIN LATERAL (
            SELECT *
            FROM exam_system.timetable_jobs tj
            WHERE tj.scenario_id = ts.id AND tj.session_id = p_session_id
            ORDER BY tj.created_at DESC
            LIMIT 1
        ) AS latest_job ON true
        WHERE ts.archived_at IS NULL
        -- This join chain ensures we only get scenarios for the correct session
        AND EXISTS (
            SELECT 1 FROM exam_system.timetable_versions tv
            JOIN exam_system.timetable_jobs tj ON tv.job_id = tj.id
            WHERE ts.parent_version_id = tv.id AND tj.session_id = p_session_id
        )
        ORDER BY ts.created_at DESC
    ) scenarios;
END;
$$;


ALTER FUNCTION exam_system.get_scenarios_for_session(p_session_id uuid) OWNER TO postgres;

--
-- Name: get_scheduling_data_summary(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_scheduling_data_summary(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN (
        SELECT jsonb_build_object(
            'duration_analysis', (
                SELECT jsonb_build_object(
                    'average_duration', COALESCE(AVG(duration_minutes), 0),
                    'shortest_exam', COALESCE(MIN(duration_minutes), 0),
                    'longest_exam', COALESCE(MAX(duration_minutes), 0)
                ) FROM exam_system.exams WHERE session_id = p_session_id
            ),
            'exam_distribution', (
                SELECT COALESCE(jsonb_agg(dist), '[]'::jsonb) FROM (
                    SELECT d.name as department, COUNT(e.id) as exam_count
                    FROM exam_system.exams e
                    JOIN exam_system.courses c ON e.course_id = c.id
                    JOIN exam_system.departments d ON c.department_id = d.id
                    WHERE e.session_id = p_session_id
                    GROUP BY d.name
                    ORDER BY exam_count DESC
                ) dist
            )
        )
    );
END;
$$;


ALTER FUNCTION exam_system.get_scheduling_data_summary(p_session_id uuid) OWNER TO postgres;

--
-- Name: get_scheduling_dataset(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_scheduling_dataset(p_job_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_result jsonb;
    v_session_id uuid;
    v_configuration_id uuid;
    v_scenario_id uuid;
    v_start_date date;
    v_end_date date;
    v_timeslot_template_id uuid;
    v_slot_generation_mode text;
    v_constraint_config_id uuid;
BEGIN
    -- Step 1: From the job ID, derive session, config, and exam period details.
    SELECT
        tj.session_id,
        tj.configuration_id,
        tj.scenario_id,
        s.start_date,
        s.end_date,
        s.timeslot_template_id,
        s.slot_generation_mode::text
    INTO
        v_session_id,
        v_configuration_id,
        v_scenario_id,
        v_start_date,
        v_end_date,
        v_timeslot_template_id,
        v_slot_generation_mode
    FROM exam_system.timetable_jobs tj
    JOIN exam_system.academic_sessions s ON tj.session_id = s.id
    WHERE tj.id = p_job_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Timetable job with ID % not found', p_job_id;
    END IF;

    -- Handle missing or invalid configuration_id by falling back to the default.
    IF v_configuration_id IS NULL OR NOT EXISTS (SELECT 1 FROM exam_system.system_configurations WHERE id = v_configuration_id) THEN
        RAISE NOTICE 'Configuration ID % for job % is invalid or NULL. Falling back to default system configuration.', v_configuration_id, p_job_id;
        SELECT id INTO v_configuration_id FROM exam_system.system_configurations WHERE is_default = true LIMIT 1;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No default system configuration found. Cannot proceed.';
        END IF;
        RAISE NOTICE 'Using default system configuration ID: %', v_configuration_id;
    END IF;

    -- Get the constraint_config_id from the determined system_configuration
    SELECT constraint_config_id INTO v_constraint_config_id FROM exam_system.system_configurations WHERE id = v_configuration_id;


    -- Step 2: Build the final JSON object using CTEs with direct session_id filtering.
    WITH exam_days_info AS (
        SELECT
            jsonb_agg(
                jsonb_build_object(
                    'exam_date', d.exam_date,
                    'time_periods', d.periods
                ) ORDER BY d.exam_date
            ) AS data
        FROM (
            SELECT
                gs.exam_date::date,
                (
                    SELECT COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'id', ttp.id,
                            'period_name', ttp.period_name,
                            'start_time', ttp.start_time,
                            'end_time', ttp.end_time
                        ) ORDER BY ttp.start_time
                    ), '[]'::jsonb)
                    FROM exam_system.timeslot_template_periods ttp
                    WHERE ttp.timeslot_template_id = v_timeslot_template_id
                ) AS periods
            FROM generate_series(v_start_date, v_end_date, '1 day'::interval) AS gs(exam_date)
            WHERE EXTRACT(ISODOW FROM gs.exam_date) < 6 -- Assuming exams are not on weekends
        ) d
    ),
    students_info AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', s.id,
                'matric_number', s.matric_number,
                'department', d.name
            )
        ) AS data
        FROM exam_system.students s
        JOIN exam_system.programmes p ON s.programme_id = p.id
        JOIN exam_system.departments d ON p.department_id = d.id
        WHERE s.session_id = v_session_id
    ),
    exams_info AS (
        SELECT jsonb_agg(exam_json) AS data
        FROM (
            SELECT
                jsonb_build_object(
                    'id', e.id,
                    'course_id', e.course_id,
                    'course_code', c.code,
                    'course_title', c.title,
                    'duration_minutes', e.duration_minutes,
                    'expected_students', e.expected_students,
                    'is_practical', e.is_practical,
                    'morning_only', e.morning_only,
                    'students', COALESCE(
                        (SELECT jsonb_object_agg(cr.student_id, cr.registration_type)
                         FROM exam_system.course_registrations cr
                         WHERE cr.course_id = e.course_id AND cr.session_id = v_session_id),
                    '{}'::jsonb),
                    'instructors', COALESCE(jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', st.id,
                            'first_name', st.first_name,
                            'last_name', st.last_name,
                            'email', u.email,
                            'department', staff_dept.name
                        )
                    ) FILTER (WHERE st.id IS NOT NULL), '[]'::jsonb),
                    'departments', COALESCE((
                        SELECT jsonb_agg(jsonb_build_object('id', d.id, 'name', d.name))
                        FROM exam_system.course_departments cd
                        JOIN exam_system.departments d ON cd.department_id = d.id
                        WHERE cd.course_id = c.id AND cd.session_id = v_session_id
                    ), '[]'::jsonb),
                    'faculties', COALESCE((
                        SELECT jsonb_agg(DISTINCT faculty_data)
                        FROM (
                            -- Faculties from direct course-faculty link
                            SELECT jsonb_build_object('id', f.id, 'name', f.name) AS faculty_data
                            FROM exam_system.course_faculties cf
                            JOIN exam_system.faculties f ON cf.faculty_id = f.id
                            WHERE cf.course_id = c.id AND cf.session_id = v_session_id
                            UNION
                            -- Faculties from indirect course-department-faculty link
                            SELECT jsonb_build_object('id', f.id, 'name', f.name)
                            FROM exam_system.course_departments cd
                            JOIN exam_system.departments d ON cd.department_id = d.id
                            JOIN exam_system.faculties f ON d.faculty_id = f.id
                            WHERE cd.course_id = c.id AND cd.session_id = v_session_id
                        ) AS all_faculties
                    ), '[]'::jsonb)
                ) AS exam_json
            FROM exam_system.exams e
            JOIN exam_system.courses c ON e.course_id = c.id
            LEFT JOIN exam_system.course_instructors ci ON ci.course_id = e.course_id AND ci.session_id = v_session_id
            LEFT JOIN exam_system.staff st ON st.id = ci.staff_id
            LEFT JOIN exam_system.users u ON st.user_id = u.id
            LEFT JOIN exam_system.departments staff_dept ON st.department_id = staff_dept.id
            WHERE e.session_id = v_session_id
            GROUP BY e.id, c.id
        ) AS exam_data
    ),
    rooms_info AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', r.id,
                'code', r.code,
                'capacity', r.capacity,
                'exam_capacity', r.exam_capacity,
                'overbookable', r.overbookable,
                'has_computers', r.has_computers,
                'building_name', b.name,
                'building_faculty_id', b.faculty_id,
                'departments', COALESCE((
                    SELECT jsonb_agg(jsonb_build_object('id', d.id, 'name', d.name))
                    FROM exam_system.room_departments rd
                    JOIN exam_system.departments d ON rd.department_id = d.id
                    -- FIX: The join condition below is sufficient as rooms and departments are already session-scoped.
                    WHERE rd.room_id = r.id
                ), '[]'::jsonb),
                'adjacent_seat_pairs', COALESCE(r.adjacency_pairs, '[]'::jsonb)
            )
        ) AS data
        FROM exam_system.rooms r
        JOIN exam_system.buildings b ON r.building_id = b.id
        WHERE r.is_active = true AND r.session_id = v_session_id
    ),
    invigilators_info AS (
         WITH staff_unavailability_agg AS (
            SELECT
                su.staff_id,
                jsonb_object_agg(
                    su.unavailable_date::text,
                     (SELECT jsonb_agg(DISTINCT p.period) FROM (SELECT unnest(string_to_array(su.time_slot_period, ',')) AS period) p)
                ) AS availability
            FROM exam_system.staff_unavailability su
            WHERE su.session_id = v_session_id
            GROUP BY su.staff_id
        )
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', s.id,
                'first_name', s.first_name,
                'last_name', s.last_name,
                'email', u.email,
                'department_id', s.department_id,
                'department', d.name,
                'staff_number', s.staff_number,
                'staff_type', s.staff_type,
                'can_invigilate', s.can_invigilate,
                'max_concurrent_exams', s.max_concurrent_exams,
                'max_students_per_exam', s.max_students_per_invigilator,
                'max_daily_sessions', s.max_daily_sessions,
                'max_consecutive_sessions', s.max_consecutive_sessions,
                'availability', COALESCE(sua.availability, '{}'::jsonb)
            )
        ) AS data
        FROM exam_system.staff s
        LEFT JOIN staff_unavailability_agg sua ON s.id = sua.staff_id
        LEFT JOIN exam_system.departments d ON s.department_id = d.id
        LEFT JOIN exam_system.users u ON s.user_id = u.id
        WHERE s.is_active = true AND s.can_invigilate = true AND s.session_id = v_session_id
    ),
    constraints_info AS (
        WITH rule_params AS (
             SELECT
                cp.rule_id,
                jsonb_object_agg(
                    cp.key,
                    -- Attempt to cast to a numeric or boolean if possible, otherwise keep as text
                    CASE
                        WHEN cp.data_type = 'integer' THEN to_jsonb(cp.default_value::bigint)
                        WHEN cp.data_type = 'float' THEN to_jsonb(cp.default_value::double precision)
                        WHEN cp.data_type = 'boolean' THEN to_jsonb(cp.default_value::boolean)
                        ELSE to_jsonb(cp.default_value)
                    END
                ) AS params
            FROM exam_system.constraint_parameters cp
            GROUP BY cp.rule_id
        )
        SELECT jsonb_build_object(
            'system_configuration_id', sc.id,
            'solver_parameters', sc.solver_parameters,
            'rules', COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', cr.id, -- database UUID
                            'code', cr.code, -- machine-readable code
                            'name', cr.name,
                            'description', cr.description,
                            'type', cr.type,
                            'category', cr.category,
                            'weight', crs.weight,
                            'is_enabled', crs.is_enabled,
                            -- Merge default params with overrides; overrides take precedence
                            'custom_parameters', COALESCE(rp.params, '{}'::jsonb) || COALESCE(crs.parameter_overrides, '{}'::jsonb)
                        )
                    )
                    FROM exam_system.configuration_rule_settings crs
                    JOIN exam_system.constraint_rules cr ON crs.rule_id = cr.id
                    LEFT JOIN rule_params rp ON cr.id = rp.rule_id
                    WHERE crs.configuration_id = v_constraint_config_id
                ),
                '[]'::jsonb
            )
        ) AS data
        FROM exam_system.system_configurations sc
        WHERE sc.id = v_configuration_id
    ),
    locks_info AS (
        SELECT COALESCE(jsonb_agg(
            jsonb_build_object(
                'exam_id', tl.exam_id,
                'exam_date', tl.exam_date,
                'timeslot_period_id', tl.timeslot_template_period_id,
                'room_ids', tl.room_ids
            )
        ), '[]'::jsonb) AS data
        FROM exam_system.timetable_locks tl
        WHERE tl.is_active = true AND (v_scenario_id IS NULL OR tl.scenario_id = v_scenario_id)
    ),
    course_registrations_info AS (
        SELECT COALESCE(jsonb_agg(
            jsonb_build_object(
                'student_id', cr.student_id,
                'course_id', cr.course_id,
                'registration_type', cr.registration_type
            )
        ), '[]'::jsonb) AS data
        FROM exam_system.course_registrations cr
        WHERE cr.session_id = v_session_id
    ),
    student_exam_mappings_info AS (
        SELECT COALESCE(jsonb_object_agg(
            student_id,
            exam_ids
        ), '{}'::jsonb) AS data
        FROM (
            SELECT
                cr.student_id,
                jsonb_agg(e.id) AS exam_ids
            FROM exam_system.course_registrations cr
            JOIN exam_system.exams e ON cr.course_id = e.course_id AND cr.session_id = e.session_id
            WHERE e.session_id = v_session_id
            GROUP BY cr.student_id
        ) AS student_mappings
    )

    -- Assemble the final JSON payload for the solver.
    SELECT jsonb_build_object(
        'session_id', v_session_id,
        'exam_period_start', v_start_date,
        'exam_period_end', v_end_date,
        'slot_generation_mode', v_slot_generation_mode,
        'days', COALESCE((SELECT data FROM exam_days_info), '[]'::jsonb),
        'exams', COALESCE((SELECT data FROM exams_info), '[]'::jsonb),
        'students', COALESCE((SELECT data FROM students_info), '[]'::jsonb),
        'rooms', COALESCE((SELECT data FROM rooms_info), '[]'::jsonb),
        'invigilators', COALESCE((SELECT data FROM invigilators_info), '[]'::jsonb),
        'constraints', (SELECT data FROM constraints_info),
        'locks', (SELECT data FROM locks_info),
        'course_registrations', (SELECT data FROM course_registrations_info),
        'student_exam_mappings', (SELECT data FROM student_exam_mappings_info)
    )
    INTO v_result;

    RETURN v_result;
END;
$$;


ALTER FUNCTION exam_system.get_scheduling_dataset(p_job_id uuid) OWNER TO postgres;

--
-- Name: get_scheduling_overview(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_scheduling_overview(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN (
        SELECT jsonb_build_object(
            'total_exams', (SELECT COUNT(*) FROM exam_system.exams WHERE session_id = p_session_id),
            'conflicts', 0, -- Placeholder for pre-scheduling conflict analysis
            'unique_rooms', (SELECT COUNT(*) FROM exam_system.rooms WHERE is_active = true AND session_id = p_session_id),
            'total_students', (SELECT COUNT(DISTINCT student_id) FROM exam_system.student_enrollments WHERE session_id = p_session_id),
            'active_session', (SELECT jsonb_build_object('id', id, 'name', name) FROM exam_system.academic_sessions WHERE id = p_session_id)
        )
    );
END;
$$;


ALTER FUNCTION exam_system.get_scheduling_overview(p_session_id uuid) OWNER TO postgres;

--
-- Name: get_session_setup_summary_and_validate(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_session_setup_summary_and_validate(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    session_details JSONB;
    data_summary JSONB;
    validation_results JSONB;
    warning_messages TEXT[] := ARRAY[]::TEXT[];
    error_messages TEXT[] := ARRAY[]::TEXT[];
    low_capacity_room RECORD;
    large_exam_threshold NUMERIC;
BEGIN
    -- 1. Get Session Details (This part is correct)
    SELECT jsonb_build_object(
        'name', s.name,
        'start_date', s.start_date::TEXT,
        'end_date', s.end_date::TEXT,
        'duration_days', (s.end_date - s.start_date + 1),
        'time_slots', (
            SELECT jsonb_agg(
                jsonb_build_object('start_time', p.start_time, 'end_time', p.end_time)
                ORDER BY p.start_time
            )
            FROM exam_system.timeslot_template_periods p
            WHERE p.timeslot_template_id = s.timeslot_template_id
        )
    )
    INTO session_details
    FROM exam_system.academic_sessions s
    WHERE s.id = p_session_id;

    -- 2. *** FIX: Get Data Summary by counting records from the STAGING tables ***
    SELECT jsonb_build_object(
        'faculties', (SELECT COUNT(*) FROM staging.faculties WHERE session_id = p_session_id),
        'departments', (SELECT COUNT(*) FROM staging.departments WHERE session_id = p_session_id),
        'buildings', (SELECT COUNT(*) FROM staging.buildings WHERE session_id = p_session_id),
        'rooms', (SELECT COUNT(*) FROM staging.rooms WHERE session_id = p_session_id),
        'programmes', (SELECT COUNT(*) FROM staging.programmes WHERE session_id = p_session_id),
        'courses', (SELECT COUNT(*) FROM staging.courses WHERE session_id = p_session_id),
        'staff', (SELECT COUNT(*) FROM staging.staff WHERE session_id = p_session_id),
        'students', (SELECT COUNT(*) FROM staging.students WHERE session_id = p_session_id),
        'enrollments', (SELECT COUNT(*) FROM staging.course_registrations WHERE session_id = p_session_id)
    )
    INTO data_summary;

    -- 3. Perform Validation Checks against staged data
    -- Validation 1: Identify rooms with very low capacity.
    FOR low_capacity_room IN
        SELECT code, exam_capacity
        FROM staging.rooms
        WHERE session_id = p_session_id AND exam_capacity < 15
    LOOP
        warning_messages := array_append(warning_messages, 'Warning: Room ' || low_capacity_room.code || ' has a very limited exam capacity (' || low_capacity_room.exam_capacity || ').');
    END LOOP;

    -- Validation 2: Check if room capacity is sufficient for "large exams".
    SELECT percentile_cont(0.75) WITHIN GROUP (ORDER BY student_count)
    INTO large_exam_threshold
    FROM (
        SELECT COUNT(student_matric_number) as student_count
        FROM staging.course_registrations
        WHERE session_id = p_session_id
        GROUP BY course_code
    ) as course_counts;

    IF large_exam_threshold > 0 AND NOT EXISTS (SELECT 1 FROM staging.rooms WHERE session_id = p_session_id AND exam_capacity >= large_exam_threshold) THEN
        warning_messages := array_append(warning_messages, 'Warning: No single room has enough capacity to host the largest exams (over ' || FLOOR(large_exam_threshold) || ' students).');
    END IF;

    validation_results := jsonb_build_object(
        'warnings', warning_messages,
        'errors', error_messages
    );

    -- 4. Combine all parts into a single JSONB response
    RETURN jsonb_build_object(
        'session_details', session_details,
        'data_summary', data_summary,
        'validation_results', validation_results
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'message', 'An error occurred while generating the summary: ' || SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.get_session_setup_summary_and_validate(p_session_id uuid) OWNER TO postgres;

--
-- Name: get_staff_change_requests(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_staff_change_requests(p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_staff_id uuid;
BEGIN
    -- MODIFIED: Lookup is now scoped to the session
    SELECT id INTO v_staff_id FROM exam_system.staff WHERE user_id = p_user_id AND session_id = p_session_id;

    IF v_staff_id IS NULL THEN
        RETURN '[]'::jsonb;
    END IF;

    RETURN (
        SELECT COALESCE(jsonb_agg(
            jsonb_build_object(
                'id', acr.id,
                'reason', acr.reason,
                'description', acr.description,
                'status', acr.status,
                'submitted_at', acr.submitted_at,
                'review_notes', acr.review_notes
            )
        ), '[]'::jsonb)
        FROM exam_system.assignment_change_requests acr
        WHERE acr.staff_id = v_staff_id
    );
END;
$$;


ALTER FUNCTION exam_system.get_staff_change_requests(p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: get_staff_schedule(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_staff_schedule(p_staff_id uuid, p_version_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    schedule jsonb;
    v_session_id uuid;
BEGIN
    -- MODIFIED: Derive session_id from the version
    SELECT tj.session_id INTO v_session_id
    FROM exam_system.timetable_versions tv
    JOIN exam_system.timetable_jobs tj ON tv.job_id = tj.id
    WHERE tv.id = p_version_id;

    IF v_session_id IS NULL THEN
        RAISE EXCEPTION 'Could not determine session for version ID %', p_version_id;
    END IF;

    SELECT jsonb_build_object(
        'staff_id', p_staff_id,
        'version_id', p_version_id,
        'schedule', COALESCE(jsonb_agg(assignments ORDER BY exam_date, start_time), '[]'::jsonb)
    )
    INTO schedule
    FROM (
        -- Get Invigilation Duties
        SELECT
            ta.id AS assignment_id, ta.exam_date, ttp.start_time, ttp.end_time,
            c.code AS course_code, c.title AS course_title, r.name AS room_name,
            b.name AS building_name, 'Invigilator' AS role
        FROM exam_system.timetable_assignments ta
        JOIN exam_system.exam_invigilators ei ON ta.id = ei.timetable_assignment_id
        JOIN exam_system.exams e ON ta.exam_id = e.id
        JOIN exam_system.courses c ON e.course_id = c.id
        JOIN exam_system.rooms r ON ta.room_id = r.id
        JOIN exam_system.buildings b ON r.building_id = b.id
        JOIN exam_system.timeslot_template_periods ttp ON ta.timeslot_template_period_id = ttp.id
        WHERE ei.staff_id = p_staff_id AND ta.version_id = p_version_id

        UNION ALL

        -- Get Instructor Duties (for their own courses)
        SELECT
            ta.id AS assignment_id, ta.exam_date, ttp.start_time, ttp.end_time,
            c.code AS course_code, c.title AS course_title, r.name AS room_name,
            b.name AS building_name, 'Instructor' AS role
        FROM exam_system.timetable_assignments ta
        JOIN exam_system.exams e ON ta.exam_id = e.id
        JOIN exam_system.courses c ON e.course_id = c.id
        -- MODIFIED: Join on course_instructors using the derived session_id
        JOIN exam_system.course_instructors ci ON c.id = ci.course_id AND ci.session_id = v_session_id
        JOIN exam_system.rooms r ON ta.room_id = r.id
        JOIN exam_system.buildings b ON r.building_id = b.id
        JOIN exam_system.timeslot_template_periods ttp ON ta.timeslot_template_period_id = ttp.id
        WHERE ci.staff_id = p_staff_id AND ta.version_id = p_version_id
    ) AS assignments;

    RETURN schedule;
END;
$$;


ALTER FUNCTION exam_system.get_staff_schedule(p_staff_id uuid, p_version_id uuid) OWNER TO postgres;

--
-- Name: get_staged_data(uuid, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_staged_data(p_session_id uuid, p_entity_type text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_table_name TEXT;
    v_query TEXT;
    v_result JSONB;
BEGIN
    -- Validate entity_type to prevent SQL injection
    SELECT table_name INTO v_table_name
    FROM information_schema.tables
    WHERE table_schema = 'staging' AND table_name = lower(p_entity_type);

    IF v_table_name IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'Invalid entity type specified.');
    END IF;

    -- Dynamically construct and execute the query
    v_query := format(
        'SELECT jsonb_agg(row_to_json(t)) FROM staging.%I t WHERE session_id = %L',
        v_table_name,
        p_session_id
    );

    EXECUTE v_query INTO v_result;

    -- Return the result, handling the case of no data
    RETURN jsonb_build_object('success', true, 'data', COALESCE(v_result, '[]'::jsonb));
EXCEPTION
    WHEN OTHERS THEN
        -- Log the error and return a failure message
        RAISE WARNING 'Error in get_staged_data for entity %: %', p_entity_type, SQLERRM;
        RETURN jsonb_build_object('success', false, 'message', 'An error occurred while fetching staged data.');
END;
$$;


ALTER FUNCTION exam_system.get_staged_data(p_session_id uuid, p_entity_type text) OWNER TO postgres;

--
-- Name: get_student_conflict_reports(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_student_conflict_reports(p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_student_id uuid;
BEGIN
    -- MODIFIED: Lookup is now scoped to the session
    SELECT id INTO v_student_id FROM exam_system.students WHERE user_id = p_user_id AND session_id = p_session_id;

    IF v_student_id IS NULL THEN
        RETURN '[]'::jsonb;
    END IF;

    RETURN (
        SELECT COALESCE(jsonb_agg(
            jsonb_build_object(
                'id', cr.id,
                'exam_course_code', c.code,
                'description', cr.description,
                'status', cr.status,
                'submitted_at', cr.submitted_at,
                'resolver_notes', cr.resolver_notes
            )
        ), '[]'::jsonb)
        FROM exam_system.conflict_reports cr
        JOIN exam_system.exams e ON cr.exam_id = e.id
        JOIN exam_system.courses c ON e.course_id = c.id
        WHERE cr.student_id = v_student_id
    );
END;
$$;


ALTER FUNCTION exam_system.get_student_conflict_reports(p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: get_student_course_registrations_by_session(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_student_course_registrations_by_session(session_uuid uuid) RETURNS TABLE(student_full_name text, number_of_courses bigint, registered_courses text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.first_name || ' ' || s.last_name AS student_full_name,
        COUNT(cr.course_id) AS number_of_courses,
        STRING_AGG(c.title, ', ' ORDER BY c.title) AS registered_courses
    FROM
        exam_system.course_registrations AS cr
    JOIN
        exam_system.students AS s ON cr.student_id = s.id
    JOIN
        exam_system.courses AS c ON cr.course_id = c.id
    WHERE
        cr.session_id = session_uuid
    GROUP BY
        s.first_name, s.last_name
    ORDER BY
        number_of_courses DESC;
END;
$$;


ALTER FUNCTION exam_system.get_student_course_registrations_by_session(session_uuid uuid) OWNER TO postgres;

--
-- Name: get_student_schedule(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_student_schedule(p_student_id uuid, p_job_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_result_data jsonb;
    v_session_id uuid;
    v_student_courses uuid[];
    v_schedule jsonb;
    v_student_details jsonb;
BEGIN
    SELECT result_data, session_id INTO v_result_data, v_session_id
    FROM exam_system.timetable_jobs
    WHERE id = p_job_id AND status = 'completed';

    IF v_result_data IS NULL THEN
        RETURN jsonb_build_object('error', 'Completed timetable job not found for the given ID.');
    END IF;

    SELECT ARRAY_AGG(course_id) INTO v_student_courses
    FROM exam_system.course_registrations
    WHERE student_id = p_student_id AND session_id = v_session_id;

    IF v_student_courses IS NULL THEN
        v_student_courses := ARRAY[]::uuid[];
    END IF;

    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'course_code', assignment.value ->> 'course_code',
            'course_title', assignment.value ->> 'course_title',
            'exam_date', assignment.value ->> 'date',
            'start_time', assignment.value ->> 'start_time',
            'end_time', assignment.value ->> 'end_time',
            'duration_minutes', assignment.value -> 'duration_minutes',
            'room_codes', assignment.value -> 'room_codes',
            'building_name', (SELECT string_agg(DISTINCT r ->> 'building_name', ', ') FROM jsonb_array_elements(assignment.value -> 'rooms') as r)
        ) ORDER BY (assignment.value ->> 'date'), (assignment.value ->> 'start_time')
    ), '[]'::jsonb)
    INTO v_schedule
    FROM jsonb_each(v_result_data -> 'solution' -> 'assignments') AS assignment
    WHERE (assignment.value ->> 'course_id')::uuid = ANY(v_student_courses);

    -- MODIFIED: Added session_id to the WHERE clause for a safer lookup
    SELECT jsonb_build_object(
            'student_id', s.id,
            'matric_number', s.matric_number,
            'full_name', s.first_name || ' ' || s.last_name
    ) INTO v_student_details
    FROM exam_system.students s
    WHERE s.id = p_student_id AND s.session_id = v_session_id;

    RETURN v_student_details || jsonb_build_object('job_id', p_job_id, 'schedule', v_schedule);
END;
$$;


ALTER FUNCTION exam_system.get_student_schedule(p_student_id uuid, p_job_id uuid) OWNER TO postgres;

--
-- Name: get_system_configuration_details(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_system_configuration_details(p_config_id uuid) RETURNS jsonb
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN (
        WITH rule_defaults AS (
            -- Aggregate all default parameters for every master rule
            SELECT
                r.id AS rule_id,
                r.code,
                r.name,
                r.description,
                r.type,
                r.category,
                COALESCE(jsonb_object_agg(p.key, p.default_value) FILTER (WHERE p.key IS NOT NULL), '{}'::jsonb) AS default_params
            FROM exam_system.constraint_rules r
            LEFT JOIN exam_system.constraint_parameters p ON r.id = p.rule_id
            GROUP BY r.id
        ),
        config_specifics AS (
            -- Get the specific settings for the selected configuration profile
            SELECT
                crs.rule_id,
                crs.is_enabled,
                crs.weight,
                crs.parameter_overrides
            FROM exam_system.configuration_rule_settings crs
            WHERE crs.configuration_id = (SELECT sc.constraint_config_id FROM exam_system.system_configurations sc WHERE sc.id = p_config_id)
        )
        SELECT jsonb_build_object(
            'id', sc.id,
            'name', sc.name,
            'description', sc.description,
            'is_default', sc.is_default,
            'solver_parameters', sc.solver_parameters,
            'constraint_config_id', sc.constraint_config_id,
            'rules', (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'rule_id', rd.rule_id,
                        'code', rd.code,
                        'name', rd.name,
                        'description', rd.description,
                        'type', rd.type,
                        'category', rd.category,
                        'is_enabled', COALESCE(cs.is_enabled, true), -- Default to enabled if not specified
                        'weight', COALESCE(cs.weight, 1.0),
                        'parameters', rd.default_params || COALESCE(cs.parameter_overrides, '{}'::jsonb) -- Merge defaults with overrides
                    ) ORDER BY rd.category, rd.name
                )
                FROM rule_defaults rd
                LEFT JOIN config_specifics cs ON rd.rule_id = cs.rule_id
            )
        )
        FROM exam_system.system_configurations sc
        WHERE sc.id = p_config_id
    );
END;
$$;


ALTER FUNCTION exam_system.get_system_configuration_details(p_config_id uuid) OWNER TO postgres;

--
-- Name: get_system_configuration_list(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_system_configuration_list() RETURNS jsonb
    LANGUAGE sql STABLE
    AS $$
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'id', sc.id,
            'name', sc.name,
            'description', sc.description,
            'is_default', sc.is_default
        ) ORDER BY sc.name
    ), '[]'::jsonb)
    FROM exam_system.system_configurations sc;
$$;


ALTER FUNCTION exam_system.get_system_configuration_list() OWNER TO postgres;

--
-- Name: get_timetable_conflicts(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_timetable_conflicts(p_version_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    conflicts JSONB;
BEGIN
    WITH student_clashes AS (
        -- Find students taking more than one exam in the same timeslot
        SELECT
            ta.exam_date,
            ta.time_slot_period,
            cr.student_id,
            jsonb_agg(ta.exam_id) as conflicting_exams
        FROM exam_system.timetable_assignments ta
        JOIN exam_system.exams e ON ta.exam_id = e.id
        JOIN exam_system.course_registrations cr ON e.course_id = cr.course_id AND e.session_id = cr.session_id
        WHERE ta.version_id = p_version_id
        GROUP BY ta.exam_date, ta.time_slot_period, cr.student_id
        HAVING count(ta.exam_id) > 1
    ),
    room_overages AS (
        -- Find rooms where the number of students exceeds exam capacity
        SELECT
            ta.exam_date,
            ta.time_slot_period,
            ta.room_id,
            r.exam_capacity,
            sum(e.expected_students) as total_students,
            jsonb_agg(ta.exam_id) as conflicting_exams
        FROM exam_system.timetable_assignments ta
        JOIN exam_system.exams e ON ta.exam_id = e.id
        JOIN exam_system.rooms r ON ta.room_id = r.id
        WHERE ta.version_id = p_version_id
        GROUP BY ta.exam_date, ta.time_slot_period, ta.room_id, r.exam_capacity
        HAVING sum(e.expected_students) > r.exam_capacity
    )
    SELECT jsonb_agg(conflict)
    INTO conflicts
    FROM (
        SELECT
            'student_clash_' || student_id as id,
            'hard' as type,
            'high' as severity,
            'Student has multiple exams in the same timeslot' as message,
            conflicting_exams as "examIds",
            false as "autoResolvable"
        FROM student_clashes
        UNION ALL
        SELECT
            'room_overage_' || room_id as id,
            'hard' as type,
            'high' as severity,
            'Room capacity exceeded. Expected ' || total_students || ' students in a room with capacity ' || exam_capacity as message,
            conflicting_exams as "examIds",
            true as "autoResolvable"
        FROM room_overages
    ) as conflict;

    RETURN COALESCE(conflicts, '[]');
END;
$$;


ALTER FUNCTION exam_system.get_timetable_conflicts(p_version_id uuid) OWNER TO postgres;

--
-- Name: get_timetable_job_results(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_timetable_job_results(p_job_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    results_data jsonb;
BEGIN
    -- Check if the user has the 'read' permission before proceeding.
    -- This is a placeholder for your actual permission checking logic.
    -- For example, you might call another function like:
    -- IF NOT exam_system.check_user_permission(current_user_id(), 'read:timetable_results') THEN
    --     RAISE EXCEPTION 'User does not have permission to view timetable results.';
    -- END IF;

    -- Retrieve the result_data for the given job ID
    SELECT
        result_data
    INTO
        results_data
    FROM
        exam_system.timetable_jobs
    WHERE
        id = p_job_id;

    -- Return the found data, which will be NULL if no record is found
    RETURN results_data;
END;
$$;


ALTER FUNCTION exam_system.get_timetable_job_results(p_job_id uuid) OWNER TO postgres;

--
-- Name: get_top_bottlenecks(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_top_bottlenecks(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_latest_job_data jsonb;
    v_bottlenecks jsonb;
BEGIN
    -- Step 1: Get the result_data from the latest published job
    SELECT tj.result_data INTO v_latest_job_data
    FROM exam_system.timetable_versions tv
    JOIN exam_system.timetable_jobs tj ON tv.job_id = tj.id
    WHERE tv.is_published = TRUE
      AND tj.session_id = p_session_id
    ORDER BY tv.created_at DESC
    LIMIT 1;

    -- Return early if no data is found
    IF v_latest_job_data IS NULL THEN
        RETURN '[]'::jsonb;
    END IF;

    -- Step 2: Analyze the JSON data to identify and count bottlenecks
    WITH conflict_details AS (
        SELECT 
            (jsonb_array_elements(c.value -> 'conflicts') ->> 'message') as reason,
            c.value ->> 'course_code' as item,
            (c.value -> 'rooms' -> 0 ->> 'code') as room
        FROM jsonb_each(v_latest_job_data -> 'solution' -> 'assignments') c
        -- Filter to only include assignments that have conflicts
        WHERE jsonb_array_length(c.value -> 'conflicts') > 0
    )
    SELECT jsonb_agg(bottleneck)
    FROM (
        SELECT 
            COALESCE(item, room, 'Unknown') as item, 
            reason, 
            COUNT(*) as issue_count
        FROM conflict_details
        -- CORRECTED GROUP BY CLAUSE: Group by the entire COALESCE expression
        GROUP BY COALESCE(item, room, 'Unknown'), reason
        ORDER BY issue_count DESC
        LIMIT 5
    ) as bottleneck INTO v_bottlenecks;

    -- Return the aggregated bottlenecks, or an empty array if none are found
    RETURN COALESCE(v_bottlenecks, '[]'::jsonb);
END;
$$;


ALTER FUNCTION exam_system.get_top_bottlenecks(p_session_id uuid) OWNER TO postgres;

--
-- Name: get_user_management_data(integer, integer, text, text, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_user_management_data(p_page integer, p_page_size integer, p_search_term text DEFAULT NULL::text, p_role_filter text DEFAULT NULL::text, p_status_filter text DEFAULT NULL::text) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'exam_system', 'public'
    AS $$
BEGIN
    RETURN (
        WITH
        filtered_users AS (
            SELECT
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                u.role,
                u.is_active,
                u.is_superuser,
                u.last_login
            FROM exam_system.users u
            WHERE
                (p_search_term IS NULL OR 
                 u.first_name ILIKE ('%' || p_search_term || '%') OR 
                 u.last_name ILIKE ('%' || p_search_term || '%') OR 
                 u.email ILIKE ('%' || p_search_term || '%'))
                AND (p_role_filter IS NULL OR u.role = p_role_filter)
                AND (p_status_filter IS NULL OR
                    (p_status_filter = 'active' AND u.is_active = TRUE) OR
                    (p_status_filter = 'inactive' AND u.is_active = FALSE))
        ),
        counts AS (
            SELECT
                (SELECT COUNT(*) FROM filtered_users) AS total_filtered_items,
                (SELECT COUNT(*) FROM exam_system.users WHERE is_active = TRUE) AS total_active,
                (SELECT COUNT(*) FROM exam_system.users WHERE role IN ('admin', 'superuser')) AS total_admins
        ),
        paginated_users AS (
            SELECT jsonb_agg(to_jsonb(fu) ORDER BY fu.first_name, fu.last_name) AS items
            FROM (
                SELECT *
                FROM filtered_users
                ORDER BY first_name, last_name
                LIMIT p_page_size
                OFFSET (p_page - 1) * p_page_size
            ) AS fu
        )
        SELECT jsonb_build_object(
            'page', p_page,
            'page_size', p_page_size,
            'total_items', c.total_filtered_items,
            'total_pages', CEIL(c.total_filtered_items::numeric / p_page_size),
            'items', COALESCE(pu.items, '[]'::jsonb),
            'total_active', c.total_active,
            'total_admins', c.total_admins
        )
        FROM counts c, paginated_users pu
    );
END;
$$;


ALTER FUNCTION exam_system.get_user_management_data(p_page integer, p_page_size integer, p_search_term text, p_role_filter text, p_status_filter text) OWNER TO postgres;

--
-- Name: get_user_presets(uuid, character varying); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_user_presets(p_user_id uuid, p_preset_type character varying DEFAULT NULL::character varying) RETURNS jsonb
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN (
        SELECT jsonb_agg(to_jsonb(row))
        FROM exam_system.user_filter_presets row
        WHERE user_id = p_user_id
        AND (p_preset_type IS NULL OR preset_type = p_preset_type)
    );
END;
$$;


ALTER FUNCTION exam_system.get_user_presets(p_user_id uuid, p_preset_type character varying) OWNER TO postgres;

--
-- Name: get_user_role_id(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_user_role_id(p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_staff_id uuid;
    v_student_id uuid;
    v_is_admin boolean;
BEGIN
    -- Check if the user is a superuser/admin (this is a global role)
    SELECT is_superuser INTO v_is_admin FROM exam_system.users WHERE id = p_user_id;

    IF v_is_admin THEN
        RETURN jsonb_build_object('type', 'admin', 'id', p_user_id);
    END IF;

    -- Check if the user is in the staff table for the specific session
    SELECT id INTO v_staff_id FROM exam_system.staff WHERE user_id = p_user_id AND session_id = p_session_id;
    IF FOUND THEN
        RETURN jsonb_build_object('type', 'staff', 'id', v_staff_id);
    END IF;

    -- Check if the user is in the students table for the specific session
    SELECT id INTO v_student_id FROM exam_system.students WHERE user_id = p_user_id AND session_id = p_session_id;
    IF FOUND THEN
        RETURN jsonb_build_object('type', 'student', 'id', v_student_id);
    END IF;

    -- If the user is not found in any of the roles for the given session
    RETURN jsonb_build_object('type', 'unknown', 'message', 'User not found as admin, staff, or student for the specified session.');
END;
$$;


ALTER FUNCTION exam_system.get_user_role_id(p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: get_user_roles(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_user_roles(p_user_id uuid) RETURNS text[]
    LANGUAGE plpgsql
    AS $$
DECLARE
    roles_array text[];
BEGIN
    SELECT array_agg(ur.name)
    INTO roles_array
    FROM exam_system.user_role_assignments ura
    JOIN exam_system.user_roles ur ON ura.role_id = ur.id
    WHERE ura.user_id = p_user_id;

    RETURN roles_array;
END;
$$;


ALTER FUNCTION exam_system.get_user_roles(p_user_id uuid) OWNER TO postgres;

--
-- Name: get_users_for_timetable_notification(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_users_for_timetable_notification(p_version_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_session_id uuid;
    v_session_name text;
    users_to_notify jsonb;
BEGIN
    SELECT tj.session_id, s.name
    INTO v_session_id, v_session_name
    FROM exam_system.timetable_versions tv
    JOIN exam_system.timetable_jobs tj ON tv.job_id = tj.id
    JOIN exam_system.academic_sessions s ON tj.session_id = s.id
    WHERE tv.id = p_version_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('users', '[]'::jsonb, 'session_name', 'Unknown Session');
    END IF;

    WITH relevant_users AS (
        -- Students registered for courses in this session
        SELECT u.id, u.first_name, u.email
        FROM exam_system.course_registrations cr
        JOIN exam_system.students s ON cr.student_id = s.id
        JOIN exam_system.users u ON s.user_id = u.id -- staff/students are linked to a global user
        WHERE cr.session_id = v_session_id
        UNION
        -- Staff (instructors and invigilators)
        SELECT u.id, u.first_name, u.email
        FROM exam_system.staff s
        JOIN exam_system.users u ON s.user_id = u.id
        -- MODIFIED: Filter staff by the session ID
        WHERE s.is_active = true AND s.session_id = v_session_id
    )
    SELECT jsonb_agg(jsonb_build_object(
        'id', ru.id,
        'first_name', ru.first_name,
        'email', ru.email
    ))
    INTO users_to_notify
    FROM relevant_users ru;

    RETURN jsonb_build_object(
        'users', COALESCE(users_to_notify, '[]'::jsonb),
        'session_name', v_session_name
    );
END;
$$;


ALTER FUNCTION exam_system.get_users_for_timetable_notification(p_version_id uuid) OWNER TO postgres;

--
-- Name: get_users_paginated(integer, integer, text, text, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.get_users_paginated(p_page integer, p_page_size integer, p_search_term text DEFAULT NULL::text, p_role_filter text DEFAULT NULL::text, p_status_filter text DEFAULT NULL::text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    -- Variable to hold overall stats
    v_total_active_users bigint;
    v_total_admin_users bigint;

    -- Variables for paginated results
    v_users jsonb;
    v_total_filtered_count bigint;
BEGIN
    -- Correctly calculate the overall statistics for the stat cards.
    SELECT COUNT(*) INTO v_total_active_users
    FROM exam_system.users
    WHERE is_active = TRUE;

    SELECT COUNT(*) INTO v_total_admin_users
    FROM exam_system.users
    WHERE role IN ('admin', 'superuser');

    -- Use a CTE to get both the paginated user list and the total count of filtered results.
    WITH filtered_users AS (
        SELECT
            u.id,
            u.first_name,
            u.last_name,
            u.email,
            u.role,
            u.is_active,
            u.is_superuser,
            u.last_login
        FROM exam_system.users u
        WHERE
            (p_search_term IS NULL
             OR u.first_name ILIKE ('%' || p_search_term || '%')
             OR u.last_name ILIKE ('%' || p_search_term || '%')
             OR u.email ILIKE ('%' || p_search_term || '%'))
            AND (p_role_filter IS NULL OR u.role = p_role_filter)
            AND (p_status_filter IS NULL
                 OR (p_status_filter = 'active' AND u.is_active = TRUE)
                 OR (p_status_filter = 'inactive' AND u.is_active = FALSE))
    )
    SELECT
        (SELECT COUNT(*) FROM filtered_users),
        COALESCE(jsonb_agg(paginated), '[]'::jsonb)
    INTO
        v_total_filtered_count,
        v_users
    FROM (
        SELECT *
        FROM filtered_users
        ORDER BY first_name, last_name
        LIMIT p_page_size
        OFFSET (p_page - 1) * p_page_size
    ) AS paginated;

    RETURN jsonb_build_object(
        'total_items', v_total_filtered_count,
        'total_pages', CEIL(v_total_filtered_count::numeric / p_page_size),
        'page', p_page,
        'page_size', p_page_size,
        'items', v_users,
        'total_active', v_total_active_users,
        'total_admins', v_total_admin_users
    );
END;
$$;


ALTER FUNCTION exam_system.get_users_paginated(p_page integer, p_page_size integer, p_search_term text, p_role_filter text, p_status_filter text) OWNER TO postgres;

--
-- Name: log_audit_activity(uuid, character varying, character varying, text, character varying, uuid, jsonb, jsonb, inet, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.log_audit_activity(p_user_id uuid, p_action character varying, p_entity_type character varying, p_notes text DEFAULT NULL::text, p_session_id character varying DEFAULT NULL::character varying, p_entity_id uuid DEFAULT NULL::uuid, p_old_values jsonb DEFAULT NULL::jsonb, p_new_values jsonb DEFAULT NULL::jsonb, p_ip_address inet DEFAULT NULL::inet, p_user_agent text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO exam_system.audit_logs (
        id,
        user_id,
        action,
        entity_type,
        notes,
        session_id,
        entity_id,
        old_values,
        new_values,
        ip_address,
        user_agent,
        created_at,
        updated_at
    )
    VALUES (
        gen_random_uuid(),
        p_user_id,
        p_action,
        p_entity_type,
        p_notes,
        p_session_id,
        p_entity_id,
        p_old_values,
        p_new_values,
        p_ip_address,
        p_user_agent,
        NOW(),
        NOW()
    );
END;
$$;


ALTER FUNCTION exam_system.log_audit_activity(p_user_id uuid, p_action character varying, p_entity_type character varying, p_notes text, p_session_id character varying, p_entity_id uuid, p_old_values jsonb, p_new_values jsonb, p_ip_address inet, p_user_agent text) OWNER TO postgres;

--
-- Name: manage_assignment_change_request(uuid, uuid, character varying, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.manage_assignment_change_request(p_admin_user_id uuid, p_request_id uuid, p_new_status character varying, p_notes text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_updated_request RECORD;
BEGIN
    -- Add permission check for p_admin_user_id here if needed

    UPDATE exam_system.assignment_change_requests
    SET
        status = p_new_status,
        review_notes = p_notes,
        reviewed_by = p_admin_user_id,
        reviewed_at = now()
    WHERE id = p_request_id
    RETURNING * INTO v_updated_request;

    IF v_updated_request IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'Request not found.');
    END IF;

    -- If approved, you might trigger logic here to find a replacement invigilator

    RETURN jsonb_build_object('success', true, 'data', to_jsonb(v_updated_request));
END;
$$;


ALTER FUNCTION exam_system.manage_assignment_change_request(p_admin_user_id uuid, p_request_id uuid, p_new_status character varying, p_notes text) OWNER TO postgres;

--
-- Name: FUNCTION manage_assignment_change_request(p_admin_user_id uuid, p_request_id uuid, p_new_status character varying, p_notes text); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.manage_assignment_change_request(p_admin_user_id uuid, p_request_id uuid, p_new_status character varying, p_notes text) IS 'Allows an administrator to approve or deny a staff assignment change request.';


--
-- Name: manage_conflict_report(uuid, uuid, character varying, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.manage_conflict_report(p_admin_user_id uuid, p_report_id uuid, p_new_status character varying, p_notes text) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_updated_report RECORD;
BEGIN
    -- Add permission check for p_admin_user_id here if needed

    UPDATE exam_system.conflict_reports
    SET
        status = p_new_status,
        resolver_notes = p_notes,
        reviewed_by = p_admin_user_id,
        reviewed_at = now()
    WHERE id = p_report_id
    RETURNING * INTO v_updated_report;

    IF v_updated_report IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'Report not found.');
    END IF;

    RETURN jsonb_build_object('success', true, 'data', to_jsonb(v_updated_report));
END;
$$;


ALTER FUNCTION exam_system.manage_conflict_report(p_admin_user_id uuid, p_report_id uuid, p_new_status character varying, p_notes text) OWNER TO postgres;

--
-- Name: FUNCTION manage_conflict_report(p_admin_user_id uuid, p_report_id uuid, p_new_status character varying, p_notes text); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.manage_conflict_report(p_admin_user_id uuid, p_report_id uuid, p_new_status character varying, p_notes text) IS 'Allows an administrator to update the status and notes of a student conflict report.';


--
-- Name: mark_notifications_as_read(uuid[], uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.mark_notifications_as_read(p_notification_ids uuid[], p_admin_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    updated_count integer;
BEGIN
    UPDATE exam_system.user_notifications
    SET is_read = TRUE, read_at = now()
    WHERE id = ANY(p_notification_ids)
      -- Ensure the user is an admin and is authorized to read these
      AND user_id IN (
          SELECT u.id
          FROM exam_system.users u
          JOIN exam_system.user_role_assignments ura ON u.id = ura.user_id
          JOIN exam_system.user_roles ur ON ura.role_id = ur.id
          WHERE ur.name = 'Administrator' AND u.id = p_admin_user_id
      );

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    RETURN jsonb_build_object(
        'status', 'success',
        'message', updated_count || ' notifications marked as read.'
    );
END;
$$;


ALTER FUNCTION exam_system.mark_notifications_as_read(p_notification_ids uuid[], p_admin_user_id uuid) OWNER TO postgres;

--
-- Name: process_all_staged_data(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_all_staged_data(p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
  v_seeding_session_id uuid;
  v_result jsonb;
  v_current_step TEXT;
BEGIN
  -- Find the data seeding session for the given academic session
  SELECT id INTO v_seeding_session_id
  FROM exam_system.data_seeding_sessions
  WHERE academic_session_id = p_session_id;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('status', 'failed', 'error', 'No matching data_seeding_session found for the provided academic session ID.');
  END IF;

  -- Update the status to 'processing'
  UPDATE exam_system.data_seeding_sessions
  SET status = 'processing', updated_at = now()
  WHERE id = v_seeding_session_id;

  BEGIN
    -- Process all the staged data in logical order of dependency
    v_current_step := 'faculties';
    PERFORM exam_system.process_staging_faculties(p_session_id);

    v_current_step := 'departments';
    PERFORM exam_system.process_staging_departments(p_session_id);

    v_current_step := 'buildings';
    PERFORM exam_system.process_staging_buildings(p_session_id);

    v_current_step := 'rooms';
    PERFORM exam_system.process_staging_rooms(p_session_id);

    v_current_step := 'programmes';
    PERFORM exam_system.process_staging_programmes(p_session_id);

    v_current_step := 'staff';
    PERFORM exam_system.process_staging_staff(p_session_id);

    v_current_step := 'students';
    PERFORM exam_system.process_staging_students(p_session_id);

    v_current_step := 'courses';
    PERFORM exam_system.process_staging_courses(p_session_id);

    v_current_step := 'course_departments';
    PERFORM exam_system.process_staging_course_departments(p_session_id);

    v_current_step := 'course_faculties';
    PERFORM exam_system.process_staging_course_faculties(p_session_id);

    v_current_step := 'course_instructors';
    PERFORM exam_system.process_staging_course_instructors(p_session_id);

    v_current_step := 'staff_unavailability';
    PERFORM exam_system.process_staging_staff_unavailability(p_session_id);

    v_current_step := 'registrations';
    PERFORM exam_system.process_staging_registrations(p_session_id);

    -- Mark as successful
    UPDATE exam_system.data_seeding_sessions
    SET status = 'completed', updated_at = now()
    WHERE id = v_seeding_session_id;

    v_result := jsonb_build_object('status', 'success', 'message', 'All staged data processed successfully');

  EXCEPTION
    WHEN OTHERS THEN
      UPDATE exam_system.data_seeding_sessions
      SET status = 'failed', updated_at = now()
      WHERE id = v_seeding_session_id;

      -- The error from the subordinate function will be raised and logged by PostgreSQL.
      v_result := jsonb_build_object('status', 'failed', 'error', 'Processing failed at step: ' || v_current_step || '. Details: ' || SQLERRM);
      
      -- Re-raise the original exception to ensure the transaction is rolled back and the error is logged.
      RAISE; 
  END;

  RETURN v_result;
END;
$$;


ALTER FUNCTION exam_system.process_all_staged_data(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_buildings(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_buildings(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged buildings for session_id: %', p_session_id;

    INSERT INTO exam_system.buildings (id, code, name, faculty_id, session_id, is_active, created_at, updated_at)
    SELECT
        gen_random_uuid(),
        stg.code,
        stg.name,
        fac.id,
        p_session_id,
        true,
        NOW(),
        NOW()
    FROM staging.buildings AS stg
    LEFT JOIN exam_system.faculties AS fac ON stg.faculty_code = fac.code AND fac.session_id = p_session_id
    WHERE stg.session_id = p_session_id
    ON CONFLICT (code, session_id) DO UPDATE SET
        name = EXCLUDED.name,
        faculty_id = EXCLUDED.faculty_id,
        is_active = EXCLUDED.is_active,
        updated_at = NOW();

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % buildings.', v_row_count;

    DELETE FROM staging.buildings WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged buildings.';

EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_buildings for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_buildings(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_course_departments(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_course_departments(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged course-department links for session_id: %', p_session_id;

    INSERT INTO exam_system.course_departments (course_id, department_id, session_id)
    SELECT
        c.id,
        d.id,
        p_session_id -- Assign the session ID
    FROM staging.course_departments AS stg
    -- Ensure we join to entities within the same session
    JOIN exam_system.courses AS c ON stg.course_code = c.code AND c.session_id = p_session_id
    JOIN exam_system.departments AS d ON stg.department_code = d.code AND d.session_id = p_session_id
    WHERE stg.session_id = p_session_id
    ON CONFLICT (course_id, department_id, session_id) DO NOTHING;

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Inserted % course-department links.', v_row_count;

    DELETE FROM staging.course_departments WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged course-department links.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_course_departments for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_course_departments(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_course_faculties(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_course_faculties(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged course-faculty links for session_id: %', p_session_id;

    INSERT INTO exam_system.course_faculties (course_id, faculty_id, session_id)
    SELECT
        c.id,
        f.id,
        p_session_id -- Assign the session ID
    FROM staging.course_faculties AS stg
    -- Ensure we join to entities within the same session
    JOIN exam_system.courses AS c ON stg.course_code = c.code AND c.session_id = p_session_id
    JOIN exam_system.faculties AS f ON stg.faculty_code = f.code AND f.session_id = p_session_id
    WHERE stg.session_id = p_session_id
    ON CONFLICT (course_id, faculty_id, session_id) DO NOTHING;

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Inserted % course-faculty links.', v_row_count;

    DELETE FROM staging.course_faculties WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged course-faculty links.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_course_faculties for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_course_faculties(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_course_instructors(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_course_instructors(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged course-instructor links for session_id: %', p_session_id;

    INSERT INTO exam_system.course_instructors (staff_id, course_id, session_id, created_at, updated_at)
    SELECT
        s.id,
        c.id,
        p_session_id, -- Assign the session ID
        NOW(),
        NOW()
    FROM staging.course_instructors AS stg
    -- Ensure we join to entities within the same session
    JOIN exam_system.staff AS s ON stg.staff_number = s.staff_number AND s.session_id = p_session_id
    JOIN exam_system.courses AS c ON stg.course_code = c.code AND c.session_id = p_session_id
    WHERE stg.session_id = p_session_id
    ON CONFLICT (staff_id, course_id, session_id) DO NOTHING;

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Inserted % course-instructor links.', v_row_count;

    DELETE FROM staging.course_instructors WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged course-instructor links.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_course_instructors for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_course_instructors(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_courses(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_courses(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged courses for session_id: %', p_session_id;

    INSERT INTO exam_system.courses (id, code, title, credit_units, session_id, is_active, course_level, semester, is_practical, morning_only, exam_duration_minutes)
    SELECT
        gen_random_uuid(),
        stg.code,
        stg.title,
        stg.credit_units,
        p_session_id,
        true,
        stg.course_level,
        stg.semester,
        stg.is_practical,
        stg.morning_only,
        stg.exam_duration_minutes
    FROM staging.courses AS stg
    WHERE stg.session_id = p_session_id
    ON CONFLICT (code, session_id) DO UPDATE SET
        title = EXCLUDED.title,
        credit_units = EXCLUDED.credit_units,
        is_active = EXCLUDED.is_active,
        course_level = EXCLUDED.course_level,
        semester = EXCLUDED.semester,
        is_practical = EXCLUDED.is_practical,
        morning_only = EXCLUDED.morning_only,
        exam_duration_minutes = EXCLUDED.exam_duration_minutes;
        -- FIX: Removed the non-existent "updated_at = NOW()" column from the update clause.

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % courses.', v_row_count;

    DELETE FROM staging.courses WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged courses.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_courses for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_courses(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_departments(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_departments(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged departments for session_id: %', p_session_id;

    INSERT INTO exam_system.departments (id, code, name, faculty_id, session_id, is_active, created_at, updated_at)
    SELECT
        gen_random_uuid(),
        stg.code,
        stg.name,
        fac.id,
        p_session_id,
        true,
        NOW(),
        NOW()
    FROM staging.departments AS stg
    JOIN exam_system.faculties AS fac ON stg.faculty_code = fac.code AND fac.session_id = p_session_id
    WHERE stg.session_id = p_session_id
    ON CONFLICT (code, session_id) DO UPDATE SET
        name = EXCLUDED.name,
        faculty_id = EXCLUDED.faculty_id,
        is_active = EXCLUDED.is_active,
        updated_at = NOW();

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % departments.', v_row_count;

    DELETE FROM staging.departments WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged departments.';

EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_departments for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_departments(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_faculties(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_faculties(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged faculties for session_id: %', p_session_id;

    INSERT INTO exam_system.faculties (id, code, name, session_id, is_active, created_at, updated_at)
    SELECT
        gen_random_uuid(),
        stg.code,
        stg.name,
        p_session_id,
        true,
        NOW(),
        NOW()
    FROM staging.faculties AS stg
    WHERE stg.session_id = p_session_id
    ON CONFLICT (code, session_id) DO UPDATE SET
        name = EXCLUDED.name,
        is_active = EXCLUDED.is_active,
        updated_at = NOW();

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % faculties.', v_row_count;

    DELETE FROM staging.faculties WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged faculties.';

EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_faculties for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_faculties(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_programmes(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_programmes(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged programmes for session_id: %', p_session_id;

    INSERT INTO exam_system.programmes (id, code, name, department_id, session_id, degree_type, duration_years, is_active, created_at, updated_at)
    SELECT
        gen_random_uuid(),
        stg.code,
        stg.name,
        dept.id,
        p_session_id,
        stg.degree_type,
        stg.duration_years,
        true,
        NOW(),
        NOW()
    FROM staging.programmes AS stg
    JOIN exam_system.departments AS dept ON stg.department_code = dept.code AND dept.session_id = p_session_id
    WHERE stg.session_id = p_session_id
    ON CONFLICT (code, session_id) DO UPDATE SET
        name = EXCLUDED.name,
        department_id = EXCLUDED.department_id,
        degree_type = EXCLUDED.degree_type,
        duration_years = EXCLUDED.duration_years,
        is_active = EXCLUDED.is_active,
        updated_at = NOW();

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % programmes.', v_row_count;

    DELETE FROM staging.programmes WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged programmes.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_programmes for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_programmes(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_registrations(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_registrations(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged registrations for session_id: %', p_session_id;

    INSERT INTO exam_system.course_registrations (id, student_id, course_id, session_id, registration_type, registered_at)
    SELECT
        gen_random_uuid(),
        stu.id,
        cour.id,
        p_session_id,
        stg.registration_type,
        NOW()
    FROM staging.course_registrations AS stg
    -- Ensure we join to entities within the same session
    JOIN exam_system.students AS stu ON stg.student_matric_number = stu.matric_number AND stu.session_id = p_session_id
    JOIN exam_system.courses AS cour ON stg.course_code = cour.code AND cour.session_id = p_session_id
    WHERE stg.session_id = p_session_id
    ON CONFLICT (student_id, course_id, session_id) DO UPDATE SET
        registration_type = EXCLUDED.registration_type;

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % course registrations.', v_row_count;

    DELETE FROM staging.course_registrations WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged registrations.';

    -- After registrations are processed, create the corresponding exams for this session
    RAISE NOTICE 'Calling create_exams_from_courses for session %.', p_session_id;
    PERFORM exam_system.create_exams_from_courses(p_session_id);
    RAISE NOTICE 'Finished create_exams_from_courses.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_registrations for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_registrations(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_rooms(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_rooms(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_default_room_type_id uuid;
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged rooms for session_id: %', p_session_id;

    RAISE NOTICE 'Ensuring default and staged room types exist.';

    -- FIX: Manually check for the 'Default' room type's existence before inserting,
    -- as there is no UNIQUE constraint on the 'name' column to support ON CONFLICT.
    SELECT id INTO v_default_room_type_id FROM exam_system.room_types WHERE name = 'Default';
    IF NOT FOUND THEN
        INSERT INTO exam_system.room_types (id, name, is_active)
        VALUES ('00000000-0000-0000-0000-000000000001', 'Default', true)
        RETURNING id INTO v_default_room_type_id;
    END IF;

    -- FIX: Insert new room types from the staging table only if they do not already exist by name.
    INSERT INTO exam_system.room_types (id, name, is_active)
    SELECT gen_random_uuid(), stg.room_type_code, true
    FROM (SELECT DISTINCT room_type_code FROM staging.rooms WHERE session_id = p_session_id AND room_type_code IS NOT NULL) as stg
    WHERE NOT EXISTS (
        SELECT 1 FROM exam_system.room_types rt WHERE rt.name = stg.room_type_code
    );

    RAISE NOTICE 'Upserting rooms from staging table.';
    INSERT INTO exam_system.rooms (id, code, name, building_id, room_type_id, session_id, capacity, exam_capacity, floor_number, has_ac, has_projector, has_computers, accessibility_features, notes, is_active, overbookable, max_inv_per_room, created_at, updated_at)
    SELECT
        gen_random_uuid(),
        stg.code,
        stg.name,
        b.id,
        COALESCE(rt.id, v_default_room_type_id),
        p_session_id,
        stg.capacity,
        stg.exam_capacity,
        stg.floor_number,
        COALESCE(stg.has_ac, false),
        COALESCE(stg.has_projector, false),
        COALESCE(stg.has_computers, false),
        stg.accessibility_features,
        stg.notes,
        true,
        false,
        COALESCE(stg.max_inv_per_room, 1),
        NOW(),
        NOW()
    FROM staging.rooms AS stg
    JOIN exam_system.buildings AS b ON stg.building_code = b.code AND b.session_id = p_session_id
    LEFT JOIN exam_system.room_types AS rt ON stg.room_type_code = rt.name
    WHERE stg.session_id = p_session_id
    ON CONFLICT (code, session_id) DO UPDATE SET
        name = EXCLUDED.name,
        building_id = EXCLUDED.building_id,
        room_type_id = EXCLUDED.room_type_id,
        capacity = EXCLUDED.capacity,
        exam_capacity = EXCLUDED.exam_capacity,
        floor_number = EXCLUDED.floor_number,
        has_ac = EXCLUDED.has_ac,
        has_projector = EXCLUDED.has_projector,
        has_computers = EXCLUDED.has_computers,
        accessibility_features = EXCLUDED.accessibility_features,
        notes = EXCLUDED.notes,
        max_inv_per_room = EXCLUDED.max_inv_per_room,
        updated_at = NOW();

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % rooms.', v_row_count;

    DELETE FROM staging.rooms WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged rooms.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_rooms for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_rooms(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_staff(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_staff(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged staff for session_id: %', p_session_id;

    INSERT INTO exam_system.staff (id, staff_number, first_name, last_name, department_id, user_id, session_id, staff_type, can_invigilate, is_active, max_daily_sessions, max_consecutive_sessions, max_concurrent_exams, max_students_per_invigilator, created_at, updated_at)
    SELECT
        gen_random_uuid(),
        stg.staff_number,
        stg.first_name,
        stg.last_name,
        dept.id,
        u.id,
        p_session_id,
        stg.staff_type,
        COALESCE(stg.can_invigilate, true),
        true,
        COALESCE(stg.max_daily_sessions, 2),
        COALESCE(stg.max_consecutive_sessions, 2),
        COALESCE(stg.max_concurrent_exams, 1),
        COALESCE(stg.max_students_per_invigilator, 30),
        NOW(),
        NOW()
    FROM staging.staff AS stg
    LEFT JOIN exam_system.departments AS dept ON stg.department_code = dept.code AND dept.session_id = p_session_id
    LEFT JOIN exam_system.users AS u ON stg.user_email = u.email
    WHERE stg.session_id = p_session_id
    ON CONFLICT (staff_number, session_id) DO UPDATE SET
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        department_id = EXCLUDED.department_id,
        user_id = EXCLUDED.user_id,
        staff_type = EXCLUDED.staff_type,
        can_invigilate = EXCLUDED.can_invigilate,
        max_daily_sessions = EXCLUDED.max_daily_sessions,
        max_consecutive_sessions = EXCLUDED.max_consecutive_sessions,
        max_concurrent_exams = EXCLUDED.max_concurrent_exams,
        max_students_per_invigilator = EXCLUDED.max_students_per_invigilator,
        updated_at = NOW();

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % staff members.', v_row_count;

    DELETE FROM staging.staff WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged staff.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_staff for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_staff(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_staff_unavailability(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_staff_unavailability(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged staff unavailability for session_id: %', p_session_id;

    INSERT INTO exam_system.staff_unavailability (id, staff_id, session_id, unavailable_date, time_slot_period, reason)
    SELECT
        gen_random_uuid(),
        s.id,
        p_session_id,
        stg.unavailable_date,
        stg.period_name,
        'Staged Unavailability'
    FROM staging.staff_unavailability AS stg
    -- Ensure we join to the staff member within the same session
    JOIN exam_system.staff AS s ON stg.staff_number = s.staff_number AND s.session_id = p_session_id
    WHERE stg.session_id = p_session_id
    ON CONFLICT (staff_id, session_id, unavailable_date, time_slot_period) DO NOTHING;

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Inserted % staff unavailability records.', v_row_count;

    DELETE FROM staging.staff_unavailability WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged staff unavailability.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_staff_unavailability for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_staff_unavailability(p_session_id uuid) OWNER TO postgres;

--
-- Name: process_staging_students(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.process_staging_students(p_session_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    RAISE NOTICE 'Processing staged students for session_id: %', p_session_id;

    INSERT INTO exam_system.students (id, matric_number, first_name, last_name, entry_year, programme_id, user_id, session_id, created_at, updated_at)
    SELECT
        gen_random_uuid(),
        stg.matric_number,
        stg.first_name,
        stg.last_name,
        stg.entry_year,
        prog.id,
        u.id,
        p_session_id,
        NOW(),
        NOW()
    FROM staging.students AS stg
    JOIN exam_system.programmes AS prog ON stg.programme_code = prog.code AND prog.session_id = p_session_id
    LEFT JOIN exam_system.users AS u ON stg.user_email = u.email
    WHERE stg.session_id = p_session_id
    ON CONFLICT (matric_number, session_id) DO UPDATE SET
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        entry_year = EXCLUDED.entry_year,
        programme_id = EXCLUDED.programme_id,
        user_id = EXCLUDED.user_id,
        updated_at = NOW();

    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    RAISE NOTICE 'Upserted % students.', v_row_count;

    DELETE FROM staging.students WHERE session_id = p_session_id;
    RAISE NOTICE 'Cleaned up staged students.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error in process_staging_students for session %: %', p_session_id, SQLERRM;
        RAISE;
END;
$$;


ALTER FUNCTION exam_system.process_staging_students(p_session_id uuid) OWNER TO postgres;

--
-- Name: publish_timetable_version(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.publish_timetable_version(p_job_id uuid, p_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_version_id UUID;
    v_session_id UUID;
    v_scenario_id UUID;
    v_job_status VARCHAR;
    v_new_version_number INT;
BEGIN
    -- Step 1: Validate the job and retrieve its associated version and session info.
    SELECT
        tv.id,
        tj.session_id,
        tj.status,
        tj.scenario_id
    INTO
        v_version_id,
        v_session_id,
        v_job_status,
        v_scenario_id
    FROM
        exam_system.timetable_jobs tj
    LEFT JOIN
        exam_system.timetable_versions tv ON tj.id = tv.job_id
    WHERE
        tj.id = p_job_id;

    IF v_session_id IS NULL THEN
        RAISE EXCEPTION 'Job ID % not found.', p_job_id;
    END IF;

    IF v_job_status <> 'completed' THEN
        RAISE EXCEPTION 'Cannot publish a timetable from a job that is not completed. Current status: %', v_job_status;
    END IF;

    -- Step 2: If no version exists for this completed job, create one.
    IF v_version_id IS NULL THEN
        SELECT COALESCE(MAX(version_number), 0) + 1
        INTO v_new_version_number
        FROM exam_system.timetable_versions
        WHERE scenario_id = v_scenario_id;

        INSERT INTO exam_system.timetable_versions (
            id, job_id, version_type, is_published, version_number, scenario_id, is_active, created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), p_job_id, 'generated', FALSE, v_new_version_number, v_scenario_id, TRUE, NOW(), NOW()
        )
        RETURNING id INTO v_version_id;
    END IF;

    -- Step 3: Un-publish ALL other versions for this academic session to ensure data integrity.
    -- This is more robust than the previous version as it corrects any data where multiple
    -- versions might have been incorrectly marked as published.
    UPDATE exam_system.timetable_versions
    SET is_published = FALSE, updated_at = NOW()
    WHERE id <> v_version_id -- Exclude the version we are about to publish
      AND is_published = TRUE
      AND job_id IN (
          SELECT id FROM exam_system.timetable_jobs WHERE session_id = v_session_id
      );

    -- Step 4: Publish the new version.
    UPDATE exam_system.timetable_versions
    SET is_published = TRUE, updated_at = NOW()
    WHERE id = v_version_id;

    -- Step 5: Log this action in the audit trail for accountability.
    PERFORM exam_system.log_audit_activity(
        p_user_id := p_user_id,
        p_action := 'PUBLISH_TIMETABLE',
        p_entity_type := 'timetable_version',
        p_entity_id := v_version_id,
        p_new_values := jsonb_build_object(
            'job_id', p_job_id,
            'is_published', true
        ),
        p_notes := 'Set version ' || v_version_id || ' as the published timetable for session ' || v_session_id
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'message', 'Timetable version has been successfully published.',
        'published_version_id', v_version_id,
        'job_id', p_job_id
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'error', SQLERRM
        );
END;
$$;


ALTER FUNCTION exam_system.publish_timetable_version(p_job_id uuid, p_user_id uuid) OWNER TO postgres;

--
-- Name: register_user(jsonb, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.register_user(p_user_data jsonb, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_user_id uuid;
    -- FIX: Changed type from user_role_enum to TEXT to match the 'users.role' column.
    user_role TEXT;
    result jsonb;
BEGIN
    -- Extract role and validate it
    -- FIX: Removed the invalid cast to a non-existent enum type.
    user_role := (p_user_data->>'role');
    IF user_role IS NULL THEN
        RAISE EXCEPTION 'User role is required.';
    END IF;

    -- Create the main user record
    INSERT INTO exam_system.users (
        email, password_hash, first_name, last_name, phone_number, is_active, is_superuser, role, created_at, updated_at
    )
    VALUES (
        p_user_data->>'email', p_user_data->>'password_hash', p_user_data->>'first_name', p_user_data->>'last_name',
        p_user_data->>'phone_number', true, false, user_role, now(), now()
    ) RETURNING id INTO new_user_id;

    -- Create role-specific profile records
    IF user_role = 'student' THEN
        INSERT INTO exam_system.students (user_id, matric_number, first_name, last_name, programme_id, entry_year, session_id, created_at, updated_at)
        VALUES (
            new_user_id, p_user_data->>'matric_number', p_user_data->>'first_name', p_user_data->>'last_name',
            (p_user_data->>'programme_id')::uuid, (p_user_data->>'entry_year')::int, p_session_id, now(), now()
        );
    ELSIF user_role = 'staff' THEN
        INSERT INTO exam_system.staff (user_id, staff_number, first_name, last_name, department_id, can_invigilate, session_id, created_at, updated_at, staff_type, max_daily_sessions, max_consecutive_sessions, is_active, max_concurrent_exams, max_students_per_invigilator)
        VALUES (
            new_user_id, p_user_data->>'staff_number', p_user_data->>'first_name', p_user_data->>'last_name',
            (p_user_data->>'department_id')::uuid, (p_user_data->>'can_invigilate')::boolean, p_session_id, now(), now(),
            'Default', 1, 1, true, 1, 30
        );
    END IF;

    -- FIX: Removed logic that referenced non-existent 'user_roles' and 'user_role_assignments' tables.
    -- The role is already correctly stored in the 'users' table.

    -- Return success message with new user ID and role
    result := jsonb_build_object(
        'status', 'success', 'message', 'User registered successfully.', 'user_id', new_user_id, 'role', user_role
    );
    RETURN result;
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('status', 'error', 'message', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.register_user(p_user_data jsonb, p_session_id uuid) OWNER TO postgres;

--
-- Name: save_system_configuration(jsonb, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.save_system_configuration(p_payload jsonb, p_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_sys_config_id uuid := p_payload->>'id';
    v_constraint_config_id uuid;
    v_rule record;
BEGIN
    -- Step 1: Find or Create the associated constraint_configuration profile.
    -- Each system_configuration has its own dedicated constraint_configuration.
    IF v_sys_config_id IS NOT NULL THEN
        -- For an existing system config, find its constraint config ID.
        SELECT constraint_config_id INTO v_constraint_config_id
        FROM exam_system.system_configurations WHERE id = v_sys_config_id;

        -- Update the name and description of the constraint config to match.
        UPDATE exam_system.constraint_configurations
        SET
            name = p_payload->>'name',
            description = p_payload->>'description'
        WHERE id = v_constraint_config_id;
    ELSE
        -- For a new system config, create a new constraint config.
        INSERT INTO exam_system.constraint_configurations (name, description, created_by)
        VALUES (p_payload->>'name', p_payload->>'description', p_user_id)
        RETURNING id INTO v_constraint_config_id;
    END IF;

    -- Step 2: Use ON CONFLICT to UPSERT the system_configuration itself.
    INSERT INTO exam_system.system_configurations (id, name, description, solver_parameters, constraint_config_id, created_by)
    VALUES (
        COALESCE(v_sys_config_id, gen_random_uuid()),
        p_payload->>'name',
        p_payload->>'description',
        p_payload->'solver_parameters',
        v_constraint_config_id,
        p_user_id
    )
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        solver_parameters = EXCLUDED.solver_parameters,
        updated_at = NOW()
    RETURNING id INTO v_sys_config_id;

    -- Step 3: Atomically update the rule settings for the profile.
    -- The "delete-then-insert" pattern is robust for ensuring the stored settings
    -- perfectly match the provided payload.
    DELETE FROM exam_system.configuration_rule_settings WHERE configuration_id = v_constraint_config_id;

    FOR v_rule IN SELECT * FROM jsonb_to_recordset(p_payload->'rules')
                  AS x(rule_id uuid, is_enabled boolean, weight double precision, parameters jsonb)
    LOOP
        INSERT INTO exam_system.configuration_rule_settings (configuration_id, rule_id, is_enabled, weight, parameter_overrides)
        VALUES (v_constraint_config_id, v_rule.rule_id, v_rule.is_enabled, v_rule.weight, v_rule.parameters);
    END LOOP;

    -- Return success status with the ID of the record.
    RETURN jsonb_build_object('success', true, 'id', v_sys_config_id);
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Error in save_system_configuration: %', SQLERRM;
        RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.save_system_configuration(p_payload jsonb, p_user_id uuid) OWNER TO postgres;

--
-- Name: seed_initial_constraints_and_configurations(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.seed_initial_constraints_and_configurations() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    -- User and Configuration IDs
    v_admin_user_id UUID;
    v_default_constraint_config_id UUID;
    v_fast_solve_constraint_config_id UUID;
    v_high_quality_constraint_config_id UUID;

    -- Helper variables for looping
    v_rule_id UUID;
    v_rule_record RECORD;
BEGIN
    RAISE NOTICE 'Seeding initial constraint and system configurations...';

    -- 1. Create a temporary admin user to own the configurations
    -- This ensures referential integrity.
    INSERT INTO exam_system.users (email, first_name, last_name, is_active, is_superuser, role)
    VALUES ('system_owner@example.com', 'System', 'Owner', true, true, 'admin')
    ON CONFLICT (email) DO UPDATE SET first_name = EXCLUDED.first_name
    RETURNING id INTO v_admin_user_id;

    RAISE NOTICE 'Upserted System Owner user with ID: %', v_admin_user_id;

    --------------------------------------------------------------------------------
    -- 2. Seed Master Constraint Rules and their associated Parameters
    --------------------------------------------------------------------------------
    RAISE NOTICE 'Seeding constraint rules and parameters...';

    -- Rule: UNIFIED_STUDENT_CONFLICT
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('UNIFIED_STUDENT_CONFLICT', 'Student Time Conflict', 'A student cannot take two exams at the same time.', 'hard', 'Student Constraints')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

    -- Rule: ROOM_CAPACITY_HARD
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('ROOM_CAPACITY_HARD', 'Room Capacity Exceeded', 'The number of students in a room cannot exceed its exam capacity.', 'hard', 'Spatial')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

    -- Rule: MINIMUM_INVIGILATORS (with a parameter)
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('MINIMUM_INVIGILATORS', 'Minimum Invigilators', 'Ensure enough invigilators are assigned per room based on student count.', 'hard', 'Resource')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
    RETURNING id INTO v_rule_id;
    -- Parameter for MINIMUM_INVIGILATORS
    INSERT INTO exam_system.constraint_parameters (rule_id, key, data_type, default_value, description)
    VALUES (v_rule_id, 'students_per_invigilator', 'integer', '50', 'The maximum number of students one invigilator can supervise.')
    ON CONFLICT (rule_id, key) DO UPDATE SET default_value = EXCLUDED.default_value;

    -- Rule: INSTRUCTOR_CONFLICT
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('INSTRUCTOR_CONFLICT', 'Instructor Self-Invigilation', 'An instructor for a course cannot invigilate the exam for that same course.', 'hard', 'Pedagogical')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;
    
    -- Rule: MAX_EXAMS_PER_STUDENT_PER_DAY (with a parameter)
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('MAX_EXAMS_PER_STUDENT_PER_DAY', 'Max Exams Per Student Per Day', 'A student cannot take more than a specified number of exams in a single day.', 'hard', 'Student Constraints')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
    RETURNING id INTO v_rule_id;
    -- Parameter for MAX_EXAMS_PER_STUDENT_PER_DAY
    INSERT INTO exam_system.constraint_parameters (rule_id, key, data_type, default_value, description)
    VALUES (v_rule_id, 'max_exams_per_day', 'integer', '2', 'The maximum number of exams a student can sit in one day.')
    ON CONFLICT (rule_id, key) DO UPDATE SET default_value = EXCLUDED.default_value;

    -- Rule: MINIMUM_GAP (with a parameter)
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('MINIMUM_GAP', 'Minimum Gap Between Exams', 'Penalizes scheduling a student''s exams too close together on the same day.', 'soft', 'Student Constraints')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
    RETURNING id INTO v_rule_id;
    -- Parameter for MINIMUM_GAP
    INSERT INTO exam_system.constraint_parameters (rule_id, key, data_type, default_value, description)
    VALUES (v_rule_id, 'min_gap_slots', 'integer', '1', 'The minimum number of empty timeslots between a student''s exams on the same day.')
    ON CONFLICT (rule_id, key) DO UPDATE SET default_value = EXCLUDED.default_value;

    -- Rule: OVERBOOKING_PENALTY
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('OVERBOOKING_PENALTY', 'Room Overbooking Penalty', 'Penalize assigning more students to a room than its capacity (for overbookable rooms).', 'soft', 'Spatial')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

    -- Rule: PREFERENCE_SLOTS
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('PREFERENCE_SLOTS', 'Course Slot Preference', 'Penalize scheduling exams outside of their preferred slots (e.g., ''morning only'').', 'soft', 'Pedagogical')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

    -- Rule: INVIGILATOR_LOAD_BALANCE
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('INVIGILATOR_LOAD_BALANCE', 'Invigilator Workload Balance', 'Penalize uneven distribution of total invigilation slots among staff.', 'soft', 'Fairness')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

    -- Rule: CARRYOVER_STUDENT_CONFLICT (with a parameter)
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('CARRYOVER_STUDENT_CONFLICT', 'Carryover Student Conflict', 'Allow, but penalize, scheduling conflicts for students with a ''carryover'' registration status.', 'soft', 'Student Constraints')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
    RETURNING id INTO v_rule_id;
    -- Parameter for CARRYOVER_STUDENT_CONFLICT
    INSERT INTO exam_system.constraint_parameters (rule_id, key, data_type, default_value, description)
    VALUES (v_rule_id, 'max_allowed_conflicts', 'integer', '3', 'The maximum number of soft conflicts allowed for a carryover student before penalties escalate.')
    ON CONFLICT (rule_id, key) DO UPDATE SET default_value = EXCLUDED.default_value;
    
    -- Rule: INVIGILATOR_AVAILABILITY
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('INVIGILATOR_AVAILABILITY', 'Invigilator Availability', 'Penalize assigning invigilators during their stated unavailable times.', 'soft', 'Resource')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

    -- Rule: DAILY_WORKLOAD_BALANCE
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('DAILY_WORKLOAD_BALANCE', 'Daily Exam Load Balance', 'Penalize uneven distribution of the total number of exams scheduled across different days.', 'soft', 'Fairness')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

    -- Rule: ROOM_SEQUENTIAL_USE
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('ROOM_SEQUENTIAL_USE', 'Room Sequential Use', 'Ensures no new exam starts in a room while another is ongoing (flexible mode only).', 'hard', 'Spatial')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

    -- Rule: ROOM_DURATION_HOMOGENEITY
    INSERT INTO exam_system.constraint_rules (code, name, description, type, category)
    VALUES ('ROOM_DURATION_HOMOGENEITY', 'Room Duration Homogeneity', 'Penalizes using a room for exams of different durations on the same day (flexible mode only).', 'soft', 'Fairness')
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;
    
    RAISE NOTICE 'Finished seeding rules.';

    --------------------------------------------------------------------------------
    -- 3. Seed Constraint Configuration Profiles
    --------------------------------------------------------------------------------
    RAISE NOTICE 'Seeding constraint configuration profiles...';

    -- Set all existing configurations to not be the default before creating new ones
    UPDATE exam_system.constraint_configurations SET is_default = FALSE;
    
    INSERT INTO exam_system.constraint_configurations (name, description, is_default, created_by)
    VALUES ('Default', 'A balanced set of constraints for general-purpose timetabling.', TRUE, v_admin_user_id)
    ON CONFLICT (name) DO UPDATE SET is_default = EXCLUDED.is_default
    RETURNING id INTO v_default_constraint_config_id;

    INSERT INTO exam_system.constraint_configurations (name, description, is_default, created_by)
    VALUES ('Fast Solve', 'A lightweight set of constraints for generating draft timetables quickly. Disables some complex soft constraints.', FALSE, v_admin_user_id)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_fast_solve_constraint_config_id;
    -- If the config already existed, we need to fetch its ID
    IF v_fast_solve_constraint_config_id IS NULL THEN
        SELECT id INTO v_fast_solve_constraint_config_id FROM exam_system.constraint_configurations WHERE name = 'Fast Solve';
    END IF;

    INSERT INTO exam_system.constraint_configurations (name, description, is_default, created_by)
    VALUES ('High Quality', 'A comprehensive set of constraints aiming for the highest quality timetable, may take longer to solve.', FALSE, v_admin_user_id)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO v_high_quality_constraint_config_id;
    -- If the config already existed, we need to fetch its ID
    IF v_high_quality_constraint_config_id IS NULL THEN
        SELECT id INTO v_high_quality_constraint_config_id FROM exam_system.constraint_configurations WHERE name = 'High Quality';
    END IF;
    
    RAISE NOTICE 'Finished seeding profiles.';

    --------------------------------------------------------------------------------
    -- 4. Link all rules to each configuration profile with specific settings
    --------------------------------------------------------------------------------
    RAISE NOTICE 'Linking rules to configuration profiles...';
    
    -- Loop through every master rule
    FOR v_rule_record IN SELECT id, code, type FROM exam_system.constraint_rules
    LOOP
        -- Link to 'Default' configuration
        INSERT INTO exam_system.configuration_rule_settings (configuration_id, rule_id, is_enabled, weight, parameter_overrides)
        VALUES (
            v_default_constraint_config_id,
            v_rule_record.id,
            TRUE, -- All rules enabled by default
            CASE WHEN v_rule_record.type = 'hard' THEN 100.0 ELSE 1.0 END,
            CASE v_rule_record.code
                WHEN 'MAX_EXAMS_PER_STUDENT_PER_DAY' THEN '{"max_exams_per_day": 2}'::jsonb
                WHEN 'MINIMUM_GAP' THEN '{"min_gap_slots": 1}'::jsonb
                ELSE NULL
            END
        )
        ON CONFLICT (configuration_id, rule_id) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, parameter_overrides = EXCLUDED.parameter_overrides;

        -- Link to 'Fast Solve' configuration
        INSERT INTO exam_system.configuration_rule_settings (configuration_id, rule_id, is_enabled, weight, parameter_overrides)
        VALUES (
            v_fast_solve_constraint_config_id,
            v_rule_record.id,
            -- Disable complex soft constraints for fast solve
            CASE 
                WHEN v_rule_record.code IN ('INVIGILATOR_LOAD_BALANCE', 'DAILY_WORKLOAD_BALANCE', 'ROOM_DURATION_HOMOGENEITY') THEN FALSE
                ELSE TRUE
            END,
            CASE WHEN v_rule_record.type = 'hard' THEN 100.0 ELSE 0.5 END, -- Lower weight for soft constraints
            CASE v_rule_record.code
                WHEN 'MAX_EXAMS_PER_STUDENT_PER_DAY' THEN '{"max_exams_per_day": 3}'::jsonb -- Relaxed rule
                WHEN 'MINIMUM_GAP' THEN '{"min_gap_slots": 0}'::jsonb -- Disabled gap
                ELSE NULL
            END
        )
        ON CONFLICT (configuration_id, rule_id) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, parameter_overrides = EXCLUDED.parameter_overrides;

        -- Link to 'High Quality' configuration
        INSERT INTO exam_system.configuration_rule_settings (configuration_id, rule_id, is_enabled, weight, parameter_overrides)
        VALUES (
            v_high_quality_constraint_config_id,
            v_rule_record.id,
            TRUE, -- All rules enabled
            CASE WHEN v_rule_record.type = 'hard' THEN 100.0 ELSE 2.0 END, -- Higher weight for soft constraints
            CASE v_rule_record.code
                WHEN 'MAX_EXAMS_PER_STUDENT_PER_DAY' THEN '{"max_exams_per_day": 2}'::jsonb
                WHEN 'MINIMUM_GAP' THEN '{"min_gap_slots": 2}'::jsonb -- Stricter gap rule
                ELSE NULL
            END
        )
        ON CONFLICT (configuration_id, rule_id) DO UPDATE SET is_enabled = EXCLUDED.is_enabled, parameter_overrides = EXCLUDED.parameter_overrides;
    END LOOP;
    
    RAISE NOTICE 'Finished linking rules.';
    
    --------------------------------------------------------------------------------
    -- 5. Seed System Configurations that use the Constraint Configurations
    --------------------------------------------------------------------------------
    RAISE NOTICE 'Seeding system configurations...';

    -- Set all existing system configurations to not be the default
    UPDATE exam_system.system_configurations SET is_default = FALSE;
    
    INSERT INTO exam_system.system_configurations (name, description, solver_parameters, constraint_config_id, is_default, created_by)
    VALUES (
        'Default System Setup',
        'Standard solver settings using the Default constraint profile.',
        '{"time_limit_seconds": 600, "solver_type": "CP-SAT"}'::jsonb,
        v_default_constraint_config_id,
        TRUE,
        v_admin_user_id
    )
    ON CONFLICT (name) DO UPDATE SET is_default = EXCLUDED.is_default, constraint_config_id = EXCLUDED.constraint_config_id;

    INSERT INTO exam_system.system_configurations (name, description, solver_parameters, constraint_config_id, is_default, created_by)
    VALUES (
        'Fast Draft System Setup',
        'Faster solver settings (3 minute limit) using the Fast Solve constraint profile.',
        '{"time_limit_seconds": 180, "solver_type": "CP-SAT"}'::jsonb,
        v_fast_solve_constraint_config_id,
        FALSE,
        v_admin_user_id
    )
    ON CONFLICT (name) DO UPDATE SET is_default = EXCLUDED.is_default, constraint_config_id = EXCLUDED.constraint_config_id;

    INSERT INTO exam_system.system_configurations (name, description, solver_parameters, constraint_config_id, is_default, created_by)
    VALUES (
        'High Quality System Setup',
        'Longer solver runtime (30 minutes) using the High Quality constraint profile for best results.',
        '{"time_limit_seconds": 1800, "solver_type": "CP-SAT"}'::jsonb,
        v_high_quality_constraint_config_id,
        FALSE,
        v_admin_user_id
    )
    ON CONFLICT (name) DO UPDATE SET is_default = EXCLUDED.is_default, constraint_config_id = EXCLUDED.constraint_config_id;
    
    RAISE NOTICE 'Seeding complete.';

END;
$$;


ALTER FUNCTION exam_system.seed_initial_constraints_and_configurations() OWNER TO postgres;

--
-- Name: set_active_academic_session(uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.set_active_academic_session(p_session_id uuid, p_user_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Deactivate all sessions
    UPDATE exam_system.academic_sessions
    SET is_active = false,
        updated_at = NOW()
    WHERE is_active = true;

    -- Activate the target session
    UPDATE exam_system.academic_sessions
    SET is_active = true,
        updated_at = NOW()
    WHERE id = p_session_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Academic session % not found.', p_session_id;
    END IF;

    -- Log the action
    PERFORM exam_system.log_audit_activity(
        p_user_id,
        'ACTIVATE',
        'academic_sessions',
        'Set session as active. All others deactivated.',
        NULL,
        p_session_id
    );
END;
$$;


ALTER FUNCTION exam_system.set_active_academic_session(p_session_id uuid, p_user_id uuid) OWNER TO postgres;

--
-- Name: FUNCTION set_active_academic_session(p_session_id uuid, p_user_id uuid); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.set_active_academic_session(p_session_id uuid, p_user_id uuid) IS 'Activates the specified academic session and ensures all other sessions are set to inactive.';


--
-- Name: set_default_system_configuration(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.set_default_system_configuration(p_config_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE exam_system.system_configurations
    SET is_default = false
    WHERE is_default = true;

    UPDATE exam_system.system_configurations
    SET is_default = true
    WHERE id = p_config_id;

    RETURN jsonb_build_object('success', true, 'message', 'Default system configuration updated.');
END;
$$;


ALTER FUNCTION exam_system.set_default_system_configuration(p_config_id uuid) OWNER TO postgres;

--
-- Name: setup_new_exam_session(uuid, text, date, date, exam_system.slot_generation_mode_enum, jsonb); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.setup_new_exam_session(p_user_id uuid, p_session_name text, p_start_date date, p_end_date date, p_slot_generation_mode exam_system.slot_generation_mode_enum, p_time_slots jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_timeslot_template_id uuid;
    new_session_id uuid;
    -- FIX START: Added a variable to hold the new data seeding session ID.
    new_seeding_session_id uuid;
    -- FIX END
    slot RECORD;
    period_counter INT := 1;
BEGIN
    -- Validate inputs
    IF p_start_date >= p_end_date THEN
        RETURN jsonb_build_object('success', false, 'message', 'Session end date must be after the start date.');
    END IF;

    IF EXISTS (SELECT 1 FROM exam_system.academic_sessions WHERE name = p_session_name AND archived_at IS NULL) THEN
        RETURN jsonb_build_object('success', false, 'message', 'An academic session with this name already exists.');
    END IF;

    -- Deactivate any other active sessions to ensure only one is active.
    UPDATE exam_system.academic_sessions
    SET is_active = false
    WHERE is_active = true;

    -- Create a new timeslot template specific to this session
    INSERT INTO exam_system.timeslot_templates (name, description)
    VALUES (p_session_name || ' Template', 'Custom time slots generated for the ' || p_session_name || ' session.')
    RETURNING id INTO new_timeslot_template_id;

    -- Create timeslot periods from the provided JSONB array
    FOR slot IN SELECT * FROM jsonb_to_recordset(p_time_slots) AS x(start_time TIME, end_time TIME)
    LOOP
        INSERT INTO exam_system.timeslot_template_periods (timeslot_template_id, period_name, start_time, end_time)
        VALUES (new_timeslot_template_id, 'Slot ' || period_counter, slot.start_time, slot.end_time);
        period_counter := period_counter + 1;
    END LOOP;

    -- Create the new academic session, linking the new timeslot template
    INSERT INTO exam_system.academic_sessions (name, start_date, end_date, is_active, timeslot_template_id, slot_generation_mode, semester_system)
    VALUES (p_session_name, p_start_date, p_end_date, true, new_timeslot_template_id, p_slot_generation_mode, 'semester')
    RETURNING id INTO new_session_id;
    
    -- FIX START: Create the corresponding data_seeding_session required for file uploads.
    INSERT INTO exam_system.data_seeding_sessions (academic_session_id, created_by, status)
    VALUES (new_session_id, p_user_id, 'pending')
    RETURNING id INTO new_seeding_session_id;
    -- FIX END

    -- Log this action in the audit trail
    PERFORM exam_system.log_audit_activity(
        p_user_id := p_user_id,
        p_action := 'CREATE',
        p_entity_type := 'ACADEMIC_SESSION',
        p_entity_id := new_session_id,
        p_new_values := jsonb_build_object(
            'name', p_session_name,
            'start_date', p_start_date,
            'end_date', p_end_date,
            'slot_generation_mode', p_slot_generation_mode
        )
    );

    -- FIX START: Return success with both the new academic session ID and the data seeding session ID, using the correct keys.
    RETURN jsonb_build_object(
        'success', true,
        'message', 'Academic session and data seeding session created successfully.',
        'academic_session_id', new_session_id,
        'data_seeding_session_id', new_seeding_session_id
    );
    -- FIX END

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'message', 'An unexpected error occurred: ' || SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.setup_new_exam_session(p_user_id uuid, p_session_name text, p_start_date date, p_end_date date, p_slot_generation_mode exam_system.slot_generation_mode_enum, p_time_slots jsonb) OWNER TO postgres;

--
-- Name: staff_self_register(text, text, text, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.staff_self_register(p_staff_number text, p_email text, p_password text, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_staff_record RECORD;
    v_new_user_id UUID;
    v_email_exists BOOLEAN;
BEGIN
    -- Check if a user with this email already exists
    SELECT EXISTS(SELECT 1 FROM exam_system.users WHERE email = p_email) INTO v_email_exists;
    IF v_email_exists THEN
        RETURN jsonb_build_object('success', false, 'message', 'A user with this email already exists.');
    END IF;

    -- Find the staff by staff number AND session_id
    SELECT id, user_id, first_name, last_name INTO v_staff_record
    FROM exam_system.staff WHERE staff_number = p_staff_number AND session_id = p_session_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'message', 'Staff with this ID not found in the current academic session.');
    END IF;

    -- Check if the staff member is already linked to a user account
    IF v_staff_record.user_id IS NOT NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'This staff member is already linked to a user account.');
    END IF;

    -- Create the new user, now including the 'role'
    INSERT INTO exam_system.users (first_name, last_name, email, password_hash, is_active, is_superuser, role)
    VALUES (v_staff_record.first_name, v_staff_record.last_name, p_email, crypt(p_password, gen_salt('bf')), true, false, 'staff')
    RETURNING id INTO v_new_user_id;

    -- Link the new user to the staff record
    UPDATE exam_system.staff SET user_id = v_new_user_id WHERE id = v_staff_record.id;

    RETURN jsonb_build_object('success', true, 'message', 'Staff user account created successfully.', 'user_id', v_new_user_id);
END;
$$;


ALTER FUNCTION exam_system.staff_self_register(p_staff_number text, p_email text, p_password text, p_session_id uuid) OWNER TO postgres;

--
-- Name: student_self_register(text, text, text, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.student_self_register(p_matric_number text, p_email text, p_password text, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_student_record RECORD;
    v_new_user_id UUID;
    v_email_exists BOOLEAN;
BEGIN
    -- Check if a user with this email already exists
    SELECT EXISTS(SELECT 1 FROM exam_system.users WHERE email = p_email) INTO v_email_exists;
    IF v_email_exists THEN
        RETURN jsonb_build_object('success', false, 'message', 'A user with this email already exists.');
    END IF;

    -- Find the student by matriculation number AND session_id
    SELECT id, user_id, first_name, last_name INTO v_student_record
    FROM exam_system.students WHERE matric_number = p_matric_number AND session_id = p_session_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'message', 'Student with this matriculation number not found in the current academic session.');
    END IF;

    -- Check if the student is already linked to a user account
    IF v_student_record.user_id IS NOT NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'This student is already linked to a user account.');
    END IF;

    -- Create the new user, now including the 'role'
    INSERT INTO exam_system.users (first_name, last_name, email, password_hash, is_active, is_superuser, role)
    VALUES (v_student_record.first_name, v_student_record.last_name, p_email, crypt(p_password, gen_salt('bf')), true, false, 'student')
    RETURNING id INTO v_new_user_id;

    -- Link the new user to the student record
    UPDATE exam_system.students SET user_id = v_new_user_id WHERE id = v_student_record.id;

    RETURN jsonb_build_object('success', true, 'message', 'Student user account created successfully.', 'user_id', v_new_user_id);
END;
$$;


ALTER FUNCTION exam_system.student_self_register(p_matric_number text, p_email text, p_password text, p_session_id uuid) OWNER TO postgres;

--
-- Name: unpublish_other_versions(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.unpublish_other_versions() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_session_id UUID;
BEGIN
    -- Find the session_id from the timetable_jobs table using the job_id of the version being updated.
    SELECT session_id INTO v_session_id
    FROM exam_system.timetable_jobs
    WHERE id = NEW.job_id;

    -- If a session is found, proceed to unpublish other versions in that session.
    IF v_session_id IS NOT NULL THEN
        UPDATE exam_system.timetable_versions
        SET is_published = false
        WHERE id <> NEW.id -- Exclude the current version being published.
          AND is_published = true
          AND job_id IN (
              -- Find all jobs that belong to the same academic session.
              SELECT id FROM exam_system.timetable_jobs WHERE session_id = v_session_id
          );
    END IF;

    -- Return the modified row to continue the original INSERT or UPDATE operation.
    RETURN NEW;
END;
$$;


ALTER FUNCTION exam_system.unpublish_other_versions() OWNER TO postgres;

--
-- Name: update_academic_session(uuid, text, date, date, uuid, boolean); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_academic_session(p_session_id uuid, p_name text DEFAULT NULL::text, p_start_date date DEFAULT NULL::date, p_end_date date DEFAULT NULL::date, p_timeslot_template_id uuid DEFAULT NULL::uuid, p_is_active boolean DEFAULT NULL::boolean) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Update the specified academic session, only modifying non-null parameters
    UPDATE exam_system.academic_sessions
    SET
        name = COALESCE(p_name, name),
        start_date = COALESCE(p_start_date, start_date),
        end_date = COALESCE(p_end_date, end_date),
        timeslot_template_id = COALESCE(p_timeslot_template_id, timeslot_template_id),
        is_active = COALESCE(p_is_active, is_active),
        updated_at = NOW()
    WHERE id = p_session_id;

    RETURN jsonb_build_object('success', TRUE, 'message', 'Academic session updated successfully.');
END;
$$;


ALTER FUNCTION exam_system.update_academic_session(p_session_id uuid, p_name text, p_start_date date, p_end_date date, p_timeslot_template_id uuid, p_is_active boolean) OWNER TO postgres;

--
-- Name: update_and_get_timetable_conflicts(uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_and_get_timetable_conflicts(p_version_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    -- In a real implementation, you would have complex logic here to detect conflicts.
    -- For demonstration, we will create a placeholder conflict.
    v_conflict_details JSONB;
BEGIN
    -- 1. Clear any existing conflicts for this version
    DELETE FROM exam_system.timetable_conflicts WHERE version_id = p_version_id;

    -- 2. Recalculate and insert new conflicts
    -- EXAMPLE: Find room double-bookings
    INSERT INTO exam_system.timetable_conflicts (version_id, type, severity, message, details)
    SELECT
        p_version_id,
        'hard',
        'high',
        'Room double-booking conflict in room ' || r.name,
        jsonb_build_object(
            'room_id', ta.room_id,
            'exam_date', ta.exam_date,
            'time_slot_id', ta.time_slot_id,
            'conflicting_exam_ids', jsonb_agg(ta.exam_id)
        )
    FROM exam_system.timetable_assignments ta
    JOIN exam_system.rooms r ON ta.room_id = r.id
    WHERE ta.version_id = p_version_id
    GROUP BY ta.room_id, r.name, ta.exam_date, ta.time_slot_id
    HAVING COUNT(*) > 1;

    -- Add more conflict detection logic here (e.g., staff clashes, student clashes) ...

    -- 3. Return all newly calculated conflicts for this version
    RETURN (SELECT jsonb_agg(row_to_json(tc)) FROM exam_system.timetable_conflicts tc WHERE tc.version_id = p_version_id);
END;
$$;


ALTER FUNCTION exam_system.update_and_get_timetable_conflicts(p_version_id uuid) OWNER TO postgres;

--
-- Name: FUNCTION update_and_get_timetable_conflicts(p_version_id uuid); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.update_and_get_timetable_conflicts(p_version_id uuid) IS 'Recalculates, stores, and then returns all scheduling conflicts for a given timetable version.';


--
-- Name: update_course(uuid, jsonb, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_course(p_course_id uuid, p_data jsonb, p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    old_data jsonb;
BEGIN
    SELECT to_jsonb(c.*)
    INTO old_data
    FROM exam_system.courses c
    WHERE c.id = p_course_id AND c.session_id = p_session_id;

    IF old_data IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Course not found in the specified session.');
    END IF;

    UPDATE exam_system.courses
    SET
        code = COALESCE(p_data->>'code', code),
        title = COALESCE(p_data->>'title', title),
        credit_units = COALESCE((p_data->>'credit_units')::int, credit_units),
        course_level = COALESCE((p_data->>'course_level')::int, course_level),
        semester = COALESCE((p_data->>'semester')::int, semester),
        exam_duration_minutes = COALESCE((p_data->>'exam_duration_minutes')::int, exam_duration_minutes),
        is_practical = COALESCE((p_data->>'is_practical')::boolean, is_practical),
        morning_only = COALESCE((p_data->>'morning_only')::boolean, morning_only),
        is_active = COALESCE((p_data->>'is_active')::boolean, is_active),
        updated_at = NOW()
    WHERE id = p_course_id AND session_id = p_session_id;

    PERFORM exam_system.log_audit_activity(p_user_id, 'update', 'course', p_course_id, old_data, p_data);
    RETURN jsonb_build_object('success', true, 'id', p_course_id);
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.update_course(p_course_id uuid, p_data jsonb, p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: update_exam(uuid, jsonb, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_exam(p_exam_id uuid, p_data jsonb, p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    old_data jsonb;
BEGIN
    SELECT to_jsonb(e.*)
    INTO old_data
    FROM exam_system.exams e
    WHERE e.id = p_exam_id AND e.session_id = p_session_id;

    IF old_data IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Exam not found in the specified session.');
    END IF;

    UPDATE exam_system.exams
    SET
        course_id = COALESCE((p_data->>'course_id')::uuid, course_id),
        duration_minutes = COALESCE((p_data->>'duration_minutes')::integer, duration_minutes),
        expected_students = COALESCE((p_data->>'expected_students')::integer, expected_students),
        requires_special_arrangements = COALESCE((p_data->>'requires_special_arrangements')::boolean, requires_special_arrangements),
        status = COALESCE(p_data->>'status', status),
        notes = COALESCE(p_data->>'notes', notes),
        is_practical = COALESCE((p_data->>'is_practical')::boolean, is_practical),
        requires_projector = COALESCE((p_data->>'requires_projector')::boolean, requires_projector),
        is_common = COALESCE((p_data->>'is_common')::boolean, is_common),
        morning_only = COALESCE((p_data->>'morning_only')::boolean, morning_only)
    WHERE id = p_exam_id AND session_id = p_session_id;

    PERFORM exam_system.log_audit_activity(p_user_id, 'update', 'exam', p_exam_id, old_data, p_data);
    RETURN jsonb_build_object('success', true, 'id', p_exam_id);
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.update_exam(p_exam_id uuid, p_data jsonb, p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: update_job_failed(uuid, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_job_failed(p_job_id uuid, p_error_message text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE exam_system.timetable_jobs
    SET
        status = 'failed',
        error_message = p_error_message,
        completed_at = NOW() AT TIME ZONE 'UTC',
        updated_at = NOW() AT TIME ZONE 'UTC'
    WHERE id = p_job_id;
END;
$$;


ALTER FUNCTION exam_system.update_job_failed(p_job_id uuid, p_error_message text) OWNER TO postgres;

--
-- Name: update_job_results(uuid, jsonb); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_job_results(p_job_id uuid, p_results_data jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE exam_system.timetable_jobs
    SET
        status = 'completed',
        progress_percentage = 100,
        result_data = p_results_data,
        completed_at = NOW() AT TIME ZONE 'UTC',
        updated_at = NOW() AT TIME ZONE 'UTC'
    WHERE id = p_job_id;
END;
$$;


ALTER FUNCTION exam_system.update_job_results(p_job_id uuid, p_results_data jsonb) OWNER TO postgres;

--
-- Name: update_job_status(uuid, character varying, integer, character varying, jsonb, boolean); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_job_status(p_job_id uuid, p_status character varying, p_progress integer DEFAULT NULL::integer, p_solver_phase character varying DEFAULT NULL::character varying, p_metrics jsonb DEFAULT NULL::jsonb, p_set_started_at boolean DEFAULT false) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_start_time timestamp := NULL;
BEGIN
    IF p_set_started_at THEN
        v_start_time := now();
    END IF;

    UPDATE exam_system.timetable_jobs
    SET
        status = p_status,
        progress_percentage = COALESCE(p_progress, progress_percentage),
        solver_phase = COALESCE(p_solver_phase, solver_phase),
        started_at = COALESCE(v_start_time, started_at),
        -- Update metrics from JSONB payload
        soft_constraints_violations = COALESCE((p_metrics->>'soft_constraints_violations')::numeric, soft_constraints_violations),
        fitness_score = COALESCE((p_metrics->>'fitness_score')::numeric, fitness_score),
        generation = COALESCE((p_metrics->>'generation')::integer, generation),
        processed_exams = COALESCE((p_metrics->>'processed_exams')::integer, processed_exams),
        total_exams = COALESCE((p_metrics->>'total_exams')::integer, total_exams),
        -- Logic for control flags can be updated here based on status
        can_pause = (CASE WHEN p_status = 'running' THEN true ELSE false END),
        can_resume = (CASE WHEN p_status = 'paused' THEN true ELSE false END),
        can_cancel = (CASE WHEN p_status IN ('running', 'paused', 'queued') THEN true ELSE false END)
    WHERE id = p_job_id;
END;
$$;


ALTER FUNCTION exam_system.update_job_status(p_job_id uuid, p_status character varying, p_progress integer, p_solver_phase character varying, p_metrics jsonb, p_set_started_at boolean) OWNER TO postgres;

--
-- Name: FUNCTION update_job_status(p_job_id uuid, p_status character varying, p_progress integer, p_solver_phase character varying, p_metrics jsonb, p_set_started_at boolean); Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON FUNCTION exam_system.update_job_status(p_job_id uuid, p_status character varying, p_progress integer, p_solver_phase character varying, p_metrics jsonb, p_set_started_at boolean) IS 'Updates job status and detailed metrics based on frontend data structures.';


--
-- Name: update_last_login_timestamp(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_last_login_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Set the last_login field of the new row to the current timestamp
    NEW.last_login = NOW();
    -- Return the modified row to be inserted
    RETURN NEW;
END;
$$;


ALTER FUNCTION exam_system.update_last_login_timestamp() OWNER TO postgres;

--
-- Name: update_role_permissions(character varying, jsonb, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_role_permissions(p_role_name character varying, p_permissions jsonb, p_admin_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_role_id UUID;
    v_old_permissions JSONB;
    v_updated_role JSONB;
BEGIN
    -- Find the role and its current permissions
    SELECT id, permissions INTO v_role_id, v_old_permissions
    FROM exam_system.user_roles WHERE name = p_role_name;

    IF v_role_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Role not found.');
    END IF;

    -- Update the permissions
    UPDATE exam_system.user_roles
    SET permissions = p_permissions, updated_at = NOW()
    WHERE id = v_role_id
    RETURNING to_jsonb(exam_system.user_roles.*) INTO v_updated_role;

    -- Log the audit activity
    PERFORM exam_system.log_audit_activity(
        p_user_id := p_admin_user_id,
        p_action := 'update_permissions',
        p_entity_type := 'user_role',
        p_entity_id := v_role_id,
        p_old_values := jsonb_build_object('permissions', v_old_permissions),
        p_new_values := jsonb_build_object('permissions', p_permissions),
        p_notes := format('Admin updated permissions for role ''%s''.', p_role_name)
    );

    RETURN jsonb_build_object('success', true, 'role', v_updated_role);
END;
$$;


ALTER FUNCTION exam_system.update_role_permissions(p_role_name character varying, p_permissions jsonb, p_admin_user_id uuid) OWNER TO postgres;

--
-- Name: update_room(uuid, jsonb, uuid, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_room(p_room_id uuid, p_data jsonb, p_user_id uuid, p_session_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    old_data jsonb;
BEGIN
    SELECT to_jsonb(r.*)
    INTO old_data
    FROM exam_system.rooms r
    WHERE r.id = p_room_id AND r.session_id = p_session_id;

    IF old_data IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Room not found in the specified session.');
    END IF;

    UPDATE exam_system.rooms
    SET
        code = COALESCE(p_data->>'code', code),
        name = COALESCE(p_data->>'name', name),
        building_id = COALESCE((p_data->>'building_id')::uuid, building_id),
        room_type_id = COALESCE((p_data->>'room_type_id')::uuid, room_type_id),
        capacity = COALESCE((p_data->>'capacity')::int, capacity),
        exam_capacity = COALESCE((p_data->>'exam_capacity')::int, exam_capacity),
        has_ac = COALESCE((p_data->>'has_ac')::boolean, has_ac),
        has_projector = COALESCE((p_data->>'has_projector')::boolean, has_projector),
        has_computers = COALESCE((p_data->>'has_computers')::boolean, has_computers),
        is_active = COALESCE((p_data->>'is_active')::boolean, is_active),
        overbookable = COALESCE((p_data->>'overbookable')::boolean, overbookable),
        max_inv_per_room = COALESCE((p_data->>'max_inv_per_room')::int, max_inv_per_room),
        notes = COALESCE(p_data->>'notes', notes),
        updated_at = NOW()
    WHERE id = p_room_id AND session_id = p_session_id;

    PERFORM exam_system.log_audit_activity(p_user_id, 'update', 'room', p_room_id, old_data, p_data);
    RETURN jsonb_build_object('success', true, 'id', p_room_id);
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION exam_system.update_room(p_room_id uuid, p_data jsonb, p_user_id uuid, p_session_id uuid) OWNER TO postgres;

--
-- Name: update_staff_availability(uuid, uuid, jsonb); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_staff_availability(p_user_id uuid, p_session_id uuid, p_availability_data jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    updated_staff_id uuid;
BEGIN
    -- MODIFIED: UPDATE statement is now scoped to a specific session
    UPDATE exam_system.staff
    SET generic_availability_preferences = p_availability_data
    WHERE user_id = p_user_id AND session_id = p_session_id
    RETURNING id INTO updated_staff_id;

    IF updated_staff_id IS NULL THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'Staff member not found for the specified user and session.');
    END IF;

    PERFORM exam_system.log_audit_activity(
        p_user_id,
        'UPDATE',
        'STAFF_AVAILABILITY',
        'Staff updated their availability preferences.',
        p_entity_id := updated_staff_id,
        p_new_values := p_availability_data
    );

    RETURN jsonb_build_object('status', 'success', 'message', 'Availability updated successfully.');
END;
$$;


ALTER FUNCTION exam_system.update_staff_availability(p_user_id uuid, p_session_id uuid, p_availability_data jsonb) OWNER TO postgres;

--
-- Name: update_staged_record(text, text, jsonb); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_staged_record(p_entity_type text, p_record_pk text, p_update_payload jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_table_name TEXT;
    v_pk_column TEXT;
    v_pk_type TEXT;
    v_set_clause TEXT;
    v_query TEXT;
    v_key TEXT;
    v_value JSONB;
BEGIN
    -- 1. Validate entity_type and get table details
    SELECT table_name INTO v_table_name
    FROM information_schema.tables
    WHERE table_schema = 'staging' AND table_name = lower(p_entity_type);

    IF v_table_name IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'Invalid entity type specified.');
    END IF;

    -- 2. Find the primary key column for the staging table
    SELECT c.column_name, c.data_type
    INTO v_pk_column, v_pk_type
    FROM information_schema.key_column_usage AS kcu
    JOIN information_schema.columns AS c ON kcu.column_name = c.column_name
    WHERE kcu.table_schema = 'staging'
      AND kcu.table_name = v_table_name
    LIMIT 1; -- Assuming single-column PK for staging tables

    IF v_pk_column IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'Could not determine primary key for the specified entity.');
    END IF;

    -- 3. Build the SET clause from the JSON payload
    SELECT string_agg(
        format('%I = %L', key, value ->> 0),
        ', '
    )
    INTO v_set_clause
    FROM jsonb_each(p_update_payload);

    IF v_set_clause IS NULL THEN
        RETURN jsonb_build_object('success', false, 'message', 'Update payload was empty.');
    END IF;

    -- 4. Construct and execute the dynamic UPDATE query
    v_query := format(
        'UPDATE staging.%I SET %s WHERE %I = %s RETURNING to_jsonb(staging.%I.*)',
        v_table_name,
        v_set_clause,
        v_pk_column,
        quote_literal(p_record_pk), -- Casting PK value later if needed
        v_table_name
    );

    EXECUTE v_query INTO v_value;

    RETURN jsonb_build_object('success', true, 'data', v_value);
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Error in update_staged_record: %', SQLERRM;
        RETURN jsonb_build_object('success', false, 'message', 'An error occurred during the update.');
END;
$$;


ALTER FUNCTION exam_system.update_staged_record(p_entity_type text, p_record_pk text, p_update_payload jsonb) OWNER TO postgres;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.updated_at = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION exam_system.update_updated_at_column() OWNER TO postgres;

--
-- Name: update_user(uuid, jsonb, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.update_user(p_user_id uuid, p_data jsonb, p_admin_user_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_user RECORD;
    v_old_data JSONB;
    v_new_data JSONB;
    v_update_clauses TEXT;
    v_query TEXT;
BEGIN
    -- Retrieve the current state of the user for auditing
    SELECT to_jsonb(u) INTO v_old_data FROM exam_system.users u WHERE u.id = p_user_id;

    -- Check if user exists
    IF v_old_data IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found.');
    END IF;

    -- Dynamically build the SET clause for the UPDATE statement
    v_update_clauses := (
        SELECT string_agg(
            format('%I = %L', key, value),
            ', '
        )
        FROM jsonb_each_text(p_data)
        WHERE key IN ('first_name', 'last_name', 'email', 'phone_number', 'is_active', 'role')
    );

    -- If no valid fields to update were provided, return an error
    IF v_update_clauses IS NULL OR v_update_clauses = '' THEN
        RETURN jsonb_build_object('success', false, 'error', 'No valid fields provided for update.');
    END IF;

    -- Construct and execute the dynamic UPDATE query
    v_query := format('UPDATE exam_system.users SET %s, updated_at = NOW() WHERE id = %L RETURNING *;', v_update_clauses, p_user_id);
    EXECUTE v_query INTO v_user;

    -- Get the new state of the user for auditing
    SELECT to_jsonb(u) INTO v_new_data FROM exam_system.users u WHERE u.id = p_user_id;

    -- Log the audit activity
    PERFORM exam_system.log_audit_activity(
        p_user_id := p_admin_user_id,
        p_action := 'update',
        p_entity_type := 'user',
        p_entity_id := p_user_id,
        p_old_values := v_old_data,
        p_new_values := v_new_data,
        p_notes := 'Admin updated user details.'
    );

    RETURN jsonb_build_object('success', true, 'user', v_new_data);
END;
$$;


ALTER FUNCTION exam_system.update_user(p_user_id uuid, p_data jsonb, p_admin_user_id uuid) OWNER TO postgres;

--
-- Name: user_login(text, text); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.user_login(p_email text, p_password text) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$DECLARE
    v_user record;
    is_password_valid boolean;
BEGIN
    -- Find the user by email
    SELECT id, email, password_hash, role, first_name, last_name
    INTO v_user
    FROM exam_system.users
    WHERE email = p_email AND is_active = true;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'error', 'message', 'Invalid credentials');
    END IF;

    -- In a real application, use a secure password verification function like pgcrypto.
    -- For this demo, we assume the password_hash is the plain text password 'demo'.
    is_password_valid := (v_user.password_hash = p_password);

    IF is_password_valid THEN
        -- This UPDATE now fires the trigger, which sets the last_login timestamp.
        UPDATE exam_system.users SET last_login = NOW() WHERE id = v_user.id;

        -- Return user details including the role for frontend redirection
        RETURN jsonb_build_object(
            'status', 'success',
            'message', 'Login successful',
            'user_id', v_user.id,
            'email', v_user.email,
            'full_name', v_user.first_name || ' ' || v_user.last_name,
            'role', v_user.role  -- This is the key field for the frontend
        );
    ELSE
        RETURN jsonb_build_object('status', 'error', 'message', 'Invalid credentials');
    END IF;
END;$$;


ALTER FUNCTION exam_system.user_login(p_email text, p_password text) OWNER TO postgres;

--
-- Name: validate_timetable(jsonb, uuid); Type: FUNCTION; Schema: exam_system; Owner: postgres
--

CREATE FUNCTION exam_system.validate_timetable(p_assignments jsonb, p_version_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
DECLARE
    conflicts jsonb := '[]'::jsonb;
    assignment jsonb;
    student_clashes jsonb;
    room_overcapacity jsonb;
    room_double_bookings jsonb;
    invigilator_clashes jsonb;
BEGIN
    -- Check for student clashes
    WITH student_schedules AS (
        SELECT
            cr.student_id,
            a.exam_date,
            a.time_slot_period,
            jsonb_agg(jsonb_build_object('exam_id', e.id, 'course_code', c.code)) AS exams
        FROM jsonb_to_recordset(p_assignments) AS a(exam_id uuid, exam_date date, time_slot_period text)
        JOIN exam_system.exams e ON e.id = a.exam_id
        JOIN exam_system.courses c ON c.id = e.course_id
        JOIN exam_system.course_registrations cr ON cr.course_id = c.id
        GROUP BY 1, 2, 3
        HAVING COUNT(*) > 1
    )
    SELECT jsonb_agg(jsonb_build_object(
            'type', 'student_conflict',
            'student_id', ss.student_id,
            'date', ss.exam_date,
            'timeslot', ss.time_slot_period,
            'conflicting_exams', ss.exams
        )) INTO student_clashes
    FROM student_schedules ss;

    IF student_clashes IS NOT NULL THEN
        conflicts := conflicts || student_clashes;
    END IF;

    -- Check for room overcapacity
    WITH capacity_checks AS (
        SELECT
            a.room_id,
            r.code AS room_code,
            r.exam_capacity,
            a.student_count,
            a.exam_date,
            a.time_slot_period
        FROM jsonb_to_recordset(p_assignments) AS a(room_id uuid, student_count int, exam_date date, time_slot_period text)
        JOIN exam_system.rooms r ON r.id = a.room_id
        WHERE a.student_count > r.exam_capacity
    )
    SELECT jsonb_agg(jsonb_build_object(
        'type', 'room_overcapacity',
        'room_code', cc.room_code,
        'assigned_students', cc.student_count,
        'exam_capacity', cc.exam_capacity,
        'date', cc.exam_date,
        'timeslot', cc.time_slot_period
    )) INTO room_overcapacity
    FROM capacity_checks cc;

    IF room_overcapacity IS NOT NULL THEN
        conflicts := conflicts || room_overcapacity;
    END IF;

    -- Check for room double-booking
    WITH room_bookings AS (
        SELECT
            a.room_id,
            a.exam_date,
            a.time_slot_period,
            jsonb_agg(jsonb_build_object('exam_id', e.id, 'course_code', c.code)) AS exams
        FROM jsonb_to_recordset(p_assignments) AS a(exam_id uuid, room_id uuid, exam_date date, time_slot_period text)
        JOIN exam_system.exams e ON e.id = a.exam_id
        JOIN exam_system.courses c ON c.id = e.course_id
        GROUP BY 1, 2, 3
        HAVING COUNT(*) > 1
    )
    SELECT jsonb_agg(jsonb_build_object(
            'type', 'room_double_booking',
            'room_code', r.code,
            'date', rb.exam_date,
            'timeslot', rb.time_slot_period,
            'conflicting_exams', rb.exams
        )) INTO room_double_bookings
    FROM room_bookings rb
    JOIN exam_system.rooms r ON r.id = rb.room_id;

    IF room_double_bookings IS NOT NULL THEN
        conflicts := conflicts || room_double_bookings;
    END IF;

    -- Check for invigilator clashes (based on the version_id)
    WITH invigilator_schedules AS (
        SELECT
            ei.staff_id,
            ta.exam_date,
            ta.time_slot_period,
            jsonb_agg(jsonb_build_object(
                'exam_id', ta.exam_id,
                'course_code', c.code,
                'room_code', r.code
            )) AS assignments
        FROM exam_system.timetable_assignments ta
        JOIN exam_system.exam_invigilators ei ON ei.timetable_assignment_id = ta.id
        JOIN exam_system.exams e ON e.id = ta.exam_id
        JOIN exam_system.courses c ON c.id = e.course_id
        JOIN exam_system.rooms r ON r.id = ta.room_id
        WHERE ta.version_id = p_version_id
        GROUP BY 1, 2, 3
        HAVING COUNT(*) > 1
    )
    SELECT jsonb_agg(jsonb_build_object(
        'type', 'invigilator_conflict',
        'staff_name', s.first_name || ' ' || s.last_name,
        'staff_id', inv.staff_id,
        'date', inv.exam_date,
        'timeslot', inv.time_slot_period,
        'conflicting_assignments', inv.assignments
    )) INTO invigilator_clashes
    FROM invigilator_schedules inv
    JOIN exam_system.staff s ON s.id = inv.staff_id;

    IF invigilator_clashes IS NOT NULL THEN
        conflicts := conflicts || invigilator_clashes;
    END IF;

    RETURN jsonb_build_object('success', jsonb_array_length(conflicts) = 0, 'conflicts', conflicts);
END;
$$;


ALTER FUNCTION exam_system.validate_timetable(p_assignments jsonb, p_version_id uuid) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: academic_sessions; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.academic_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying NOT NULL,
    semester_system character varying NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    is_active boolean,
    template_id uuid,
    archived_at timestamp without time zone,
    session_config jsonb,
    timeslot_template_id uuid,
    slot_generation_mode exam_system.slot_generation_mode_enum NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.academic_sessions OWNER TO postgres;

--
-- Name: assignment_change_requests; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.assignment_change_requests (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    staff_id uuid NOT NULL,
    timetable_assignment_id uuid NOT NULL,
    reason character varying(255) NOT NULL,
    description text,
    status character varying(20) NOT NULL,
    submitted_at timestamp with time zone DEFAULT now() NOT NULL,
    reviewed_at timestamp with time zone,
    reviewed_by uuid,
    review_notes text
);


ALTER TABLE exam_system.assignment_change_requests OWNER TO postgres;

--
-- Name: audit_logs; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.audit_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    action character varying(50) NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_id uuid,
    old_values jsonb,
    new_values jsonb,
    ip_address inet,
    user_agent text,
    session_id character varying(100),
    notes text,
    scenario_id uuid,
    action_type character varying(50),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.audit_logs OWNER TO postgres;

--
-- Name: buildings; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.buildings (
    id uuid NOT NULL,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    faculty_id uuid,
    session_id uuid
);


ALTER TABLE exam_system.buildings OWNER TO postgres;

--
-- Name: configuration_rule_settings; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.configuration_rule_settings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    configuration_id uuid NOT NULL,
    rule_id uuid NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    weight double precision DEFAULT 1.0 NOT NULL,
    parameter_overrides jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.configuration_rule_settings OWNER TO postgres;

--
-- Name: TABLE configuration_rule_settings; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON TABLE exam_system.configuration_rule_settings IS 'Stores the specific settings for a rule within a constraint configuration.';


--
-- Name: COLUMN configuration_rule_settings.weight; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.configuration_rule_settings.weight IS 'The penalty weight for violating a soft constraint.';


--
-- Name: COLUMN configuration_rule_settings.parameter_overrides; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.configuration_rule_settings.parameter_overrides IS 'JSON object with key-value pairs overriding default parameter values (e.g., { "max_exams": 3 }).';


--
-- Name: conflict_reports; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.conflict_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    student_id uuid NOT NULL,
    exam_id uuid NOT NULL,
    description text NOT NULL,
    status character varying(20) NOT NULL,
    submitted_at timestamp with time zone DEFAULT now() NOT NULL,
    reviewed_at timestamp with time zone,
    reviewed_by uuid,
    resolver_notes text
);


ALTER TABLE exam_system.conflict_reports OWNER TO postgres;

--
-- Name: constraint_configurations; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.constraint_configurations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_default boolean DEFAULT false NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.constraint_configurations OWNER TO postgres;

--
-- Name: TABLE constraint_configurations; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON TABLE exam_system.constraint_configurations IS 'A named collection of constraint settings, acting as a profile (e.g., "Fast Solve").';


--
-- Name: COLUMN constraint_configurations.is_default; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.constraint_configurations.is_default IS 'Indicates if this is the default set of constraints to be used.';


--
-- Name: constraint_parameters; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.constraint_parameters (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    rule_id uuid NOT NULL,
    key character varying(100) NOT NULL,
    data_type character varying(50) NOT NULL,
    default_value character varying(255) NOT NULL,
    description text,
    validation_rules jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT constraint_parameters_data_type_check CHECK (((data_type)::text = ANY ((ARRAY['integer'::character varying, 'float'::character varying, 'boolean'::character varying, 'string'::character varying])::text[])))
);


ALTER TABLE exam_system.constraint_parameters OWNER TO postgres;

--
-- Name: TABLE constraint_parameters; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON TABLE exam_system.constraint_parameters IS 'Defines configurable parameters for each constraint rule.';


--
-- Name: COLUMN constraint_parameters.key; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.constraint_parameters.key IS 'The machine-readable key for the parameter (e.g., max_exams).';


--
-- Name: COLUMN constraint_parameters.data_type; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.constraint_parameters.data_type IS 'The expected data type for the parameter value (e.g., integer, boolean).';


--
-- Name: COLUMN constraint_parameters.default_value; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.constraint_parameters.default_value IS 'The default value for the parameter, stored as a string and cast as needed.';


--
-- Name: COLUMN constraint_parameters.validation_rules; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.constraint_parameters.validation_rules IS 'JSON object defining validation logic, e.g., { "min": 1, "max": 5 }.';


--
-- Name: constraint_rules; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.constraint_rules (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    code character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    type character varying(20) NOT NULL,
    category character varying(50) DEFAULT 'Other'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT constraint_rules_type_check CHECK (((type)::text = ANY ((ARRAY['hard'::character varying, 'soft'::character varying])::text[])))
);


ALTER TABLE exam_system.constraint_rules OWNER TO postgres;

--
-- Name: TABLE constraint_rules; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON TABLE exam_system.constraint_rules IS 'Defines the master list of all available scheduling constraints.';


--
-- Name: COLUMN constraint_rules.code; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.constraint_rules.code IS 'A unique, machine-readable identifier for the constraint (e.g., MAX_EXAMS_PER_DAY).';


--
-- Name: COLUMN constraint_rules.type; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.constraint_rules.type IS 'The type of constraint, either ''hard'' (must be satisfied) or ''soft'' (a preference).';


--
-- Name: COLUMN constraint_rules.category; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.constraint_rules.category IS 'A UI-friendly grouping for constraints (e.g., Student, Room, Invigilator).';


--
-- Name: course_departments; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.course_departments (
    course_id uuid NOT NULL,
    department_id uuid NOT NULL,
    session_id uuid NOT NULL
);


ALTER TABLE exam_system.course_departments OWNER TO postgres;

--
-- Name: course_faculties; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.course_faculties (
    course_id uuid NOT NULL,
    faculty_id uuid NOT NULL,
    session_id uuid NOT NULL
);


ALTER TABLE exam_system.course_faculties OWNER TO postgres;

--
-- Name: course_instructors; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.course_instructors (
    course_id uuid NOT NULL,
    staff_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    session_id uuid NOT NULL
);


ALTER TABLE exam_system.course_instructors OWNER TO postgres;

--
-- Name: course_registrations; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.course_registrations (
    id uuid NOT NULL,
    student_id uuid NOT NULL,
    course_id uuid NOT NULL,
    session_id uuid NOT NULL,
    registration_type character varying NOT NULL,
    registered_at timestamp without time zone DEFAULT now()
);


ALTER TABLE exam_system.course_registrations OWNER TO postgres;

--
-- Name: courses; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.courses (
    id uuid NOT NULL,
    code character varying NOT NULL,
    title character varying NOT NULL,
    credit_units integer NOT NULL,
    course_level integer NOT NULL,
    semester integer,
    is_practical boolean,
    morning_only boolean,
    exam_duration_minutes integer,
    is_active boolean,
    session_id uuid
);


ALTER TABLE exam_system.courses OWNER TO postgres;

--
-- Name: data_seeding_sessions; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.data_seeding_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    academic_session_id uuid NOT NULL,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    created_by uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.data_seeding_sessions OWNER TO postgres;

--
-- Name: departments; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.departments (
    id uuid NOT NULL,
    code character varying NOT NULL,
    name character varying NOT NULL,
    faculty_id uuid NOT NULL,
    is_active boolean,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    session_id uuid
);


ALTER TABLE exam_system.departments OWNER TO postgres;

--
-- Name: exam_departments; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.exam_departments (
    id uuid NOT NULL,
    exam_id uuid NOT NULL,
    department_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.exam_departments OWNER TO postgres;

--
-- Name: exam_invigilators; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.exam_invigilators (
    id uuid NOT NULL,
    staff_id uuid NOT NULL,
    timetable_assignment_id uuid NOT NULL,
    role character varying(30) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.exam_invigilators OWNER TO postgres;

--
-- Name: exam_prerequisites_association; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.exam_prerequisites_association (
    exam_id uuid NOT NULL,
    prerequisite_id uuid NOT NULL
);


ALTER TABLE exam_system.exam_prerequisites_association OWNER TO postgres;

--
-- Name: exams; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.exams (
    id uuid NOT NULL,
    course_id uuid NOT NULL,
    session_id uuid NOT NULL,
    duration_minutes integer NOT NULL,
    expected_students integer NOT NULL,
    requires_special_arrangements boolean NOT NULL,
    status character varying NOT NULL,
    notes text,
    is_practical boolean NOT NULL,
    requires_projector boolean NOT NULL,
    is_common boolean NOT NULL,
    morning_only boolean NOT NULL
);


ALTER TABLE exam_system.exams OWNER TO postgres;

--
-- Name: faculties; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.faculties (
    id uuid NOT NULL,
    code character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    session_id uuid
);


ALTER TABLE exam_system.faculties OWNER TO postgres;

--
-- Name: file_upload_sessions; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.file_upload_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_type character varying NOT NULL,
    uploaded_by uuid NOT NULL,
    session_id uuid,
    status character varying NOT NULL,
    total_records integer DEFAULT 0,
    processed_records integer DEFAULT 0,
    validation_errors jsonb DEFAULT '{}'::jsonb,
    completed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.file_upload_sessions OWNER TO postgres;

--
-- Name: file_uploads; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.file_uploads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    data_seeding_session_id uuid NOT NULL,
    upload_type character varying NOT NULL,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    file_name character varying NOT NULL,
    file_path character varying NOT NULL,
    total_records integer,
    processed_records integer,
    validation_errors jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.file_uploads OWNER TO postgres;

--
-- Name: programmes; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.programmes (
    id uuid NOT NULL,
    name character varying NOT NULL,
    code character varying NOT NULL,
    degree_type character varying NOT NULL,
    duration_years integer NOT NULL,
    department_id uuid NOT NULL,
    is_active boolean,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    session_id uuid
);


ALTER TABLE exam_system.programmes OWNER TO postgres;

--
-- Name: room_departments; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.room_departments (
    room_id uuid NOT NULL,
    department_id uuid NOT NULL
);


ALTER TABLE exam_system.room_departments OWNER TO postgres;

--
-- Name: room_types; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.room_types (
    id uuid NOT NULL,
    name character varying NOT NULL,
    description character varying,
    is_active boolean NOT NULL
);


ALTER TABLE exam_system.room_types OWNER TO postgres;

--
-- Name: rooms; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.rooms (
    id uuid NOT NULL,
    code character varying NOT NULL,
    name character varying NOT NULL,
    building_id uuid NOT NULL,
    room_type_id uuid NOT NULL,
    capacity integer NOT NULL,
    exam_capacity integer,
    floor_number integer,
    has_ac boolean NOT NULL,
    has_projector boolean NOT NULL,
    has_computers boolean NOT NULL,
    accessibility_features character varying[],
    is_active boolean NOT NULL,
    overbookable boolean NOT NULL,
    max_inv_per_room integer NOT NULL,
    adjacency_pairs jsonb,
    notes text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    session_id uuid
);


ALTER TABLE exam_system.rooms OWNER TO postgres;

--
-- Name: session_templates; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.session_templates (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    source_session_id uuid,
    template_data jsonb,
    is_active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.session_templates OWNER TO postgres;

--
-- Name: staff; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.staff (
    id uuid NOT NULL,
    staff_number character varying NOT NULL,
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    department_id uuid,
    "position" character varying,
    staff_type character varying NOT NULL,
    can_invigilate boolean NOT NULL,
    max_daily_sessions integer NOT NULL,
    max_consecutive_sessions integer NOT NULL,
    is_active boolean NOT NULL,
    max_concurrent_exams integer NOT NULL,
    max_students_per_invigilator integer NOT NULL,
    generic_availability_preferences jsonb,
    user_id uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    session_id uuid
);


ALTER TABLE exam_system.staff OWNER TO postgres;

--
-- Name: staff_unavailability; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.staff_unavailability (
    id uuid NOT NULL,
    staff_id uuid NOT NULL,
    session_id uuid NOT NULL,
    time_slot_period character varying,
    unavailable_date date NOT NULL,
    reason character varying
);


ALTER TABLE exam_system.staff_unavailability OWNER TO postgres;

--
-- Name: student_enrollments; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.student_enrollments (
    id uuid NOT NULL,
    student_id uuid NOT NULL,
    session_id uuid NOT NULL,
    level integer NOT NULL,
    student_type character varying,
    is_active boolean
);


ALTER TABLE exam_system.student_enrollments OWNER TO postgres;

--
-- Name: students; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.students (
    id uuid NOT NULL,
    matric_number character varying NOT NULL,
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    entry_year integer NOT NULL,
    special_needs character varying[],
    programme_id uuid NOT NULL,
    user_id uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    session_id uuid
);


ALTER TABLE exam_system.students OWNER TO postgres;

--
-- Name: system_configurations; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.system_configurations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    solver_parameters jsonb,
    constraint_config_id uuid NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.system_configurations OWNER TO postgres;

--
-- Name: TABLE system_configurations; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON TABLE exam_system.system_configurations IS 'Defines system-level settings, including which constraint configuration to use.';


--
-- Name: COLUMN system_configurations.solver_parameters; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.system_configurations.solver_parameters IS 'JSON object for solver engine settings (e.g., { "time_limit_seconds": 600 }).';


--
-- Name: COLUMN system_configurations.constraint_config_id; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.system_configurations.constraint_config_id IS 'The set of constraint rules and settings to be used by this system configuration.';


--
-- Name: COLUMN system_configurations.is_default; Type: COMMENT; Schema: exam_system; Owner: postgres
--

COMMENT ON COLUMN exam_system.system_configurations.is_default IS 'Indicates if this is the default system configuration for running jobs.';


--
-- Name: system_events; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.system_events (
    id uuid NOT NULL,
    title character varying NOT NULL,
    message text NOT NULL,
    event_type character varying NOT NULL,
    priority character varying NOT NULL,
    entity_type character varying,
    entity_id uuid,
    event_metadata jsonb,
    affected_users uuid[],
    is_resolved boolean NOT NULL,
    resolved_by uuid,
    resolved_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.system_events OWNER TO postgres;

--
-- Name: timeslot_template_periods; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timeslot_template_periods (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    timeslot_template_id uuid NOT NULL,
    period_name character varying(100) NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL
);


ALTER TABLE exam_system.timeslot_template_periods OWNER TO postgres;

--
-- Name: timeslot_templates; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timeslot_templates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.timeslot_templates OWNER TO postgres;

--
-- Name: timetable_assignments; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timetable_assignments (
    id uuid NOT NULL,
    exam_id uuid NOT NULL,
    room_id uuid NOT NULL,
    exam_date date NOT NULL,
    timeslot_template_period_id uuid NOT NULL,
    student_count integer NOT NULL,
    is_confirmed boolean NOT NULL,
    version_id uuid,
    allocated_capacity integer NOT NULL,
    is_primary boolean NOT NULL,
    seating_arrangement jsonb
);


ALTER TABLE exam_system.timetable_assignments OWNER TO postgres;

--
-- Name: timetable_conflicts; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timetable_conflicts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    version_id uuid NOT NULL,
    type character varying(50) NOT NULL,
    severity character varying(20) NOT NULL,
    message text NOT NULL,
    details jsonb,
    is_resolved boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.timetable_conflicts OWNER TO postgres;

--
-- Name: timetable_edits; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timetable_edits (
    id uuid NOT NULL,
    version_id uuid NOT NULL,
    exam_id uuid NOT NULL,
    edited_by uuid NOT NULL,
    edit_type character varying(30) NOT NULL,
    old_values jsonb,
    new_values jsonb,
    reason text,
    validation_status character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.timetable_edits OWNER TO postgres;

--
-- Name: timetable_job_exam_days; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timetable_job_exam_days (
    timetable_job_id uuid NOT NULL,
    exam_date date NOT NULL
);


ALTER TABLE exam_system.timetable_job_exam_days OWNER TO postgres;

--
-- Name: timetable_jobs; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timetable_jobs (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    configuration_id uuid NOT NULL,
    initiated_by uuid NOT NULL,
    status character varying NOT NULL,
    progress_percentage integer NOT NULL,
    cp_sat_runtime_seconds integer,
    ga_runtime_seconds integer,
    total_runtime_seconds integer,
    hard_constraint_violations integer NOT NULL,
    scenario_id uuid,
    constraint_config_id uuid,
    checkpoint_data jsonb,
    soft_constraints_violations numeric,
    room_utilization_percentage numeric,
    solver_phase character varying,
    error_message text,
    result_data jsonb,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    can_pause boolean NOT NULL,
    can_resume boolean NOT NULL,
    can_cancel boolean NOT NULL,
    generation integer,
    processed_exams integer,
    total_exams integer,
    fitness_score numeric,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.timetable_jobs OWNER TO postgres;

--
-- Name: timetable_locks; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timetable_locks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    exam_id uuid NOT NULL,
    timeslot_template_period_id uuid,
    exam_date date,
    room_ids uuid[],
    locked_by uuid NOT NULL,
    locked_at timestamp with time zone DEFAULT now() NOT NULL,
    reason text,
    is_active boolean NOT NULL
);


ALTER TABLE exam_system.timetable_locks OWNER TO postgres;

--
-- Name: timetable_scenarios; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timetable_scenarios (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    parent_version_id uuid,
    name character varying(255) NOT NULL,
    description text,
    created_by uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    archived_at timestamp with time zone
);


ALTER TABLE exam_system.timetable_scenarios OWNER TO postgres;

--
-- Name: timetable_versions; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.timetable_versions (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    parent_version_id uuid,
    version_type character varying(20) NOT NULL,
    archive_date timestamp without time zone,
    is_published boolean NOT NULL,
    version_number integer NOT NULL,
    scenario_id uuid,
    is_active boolean NOT NULL,
    approval_level character varying,
    approved_by uuid,
    approved_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.timetable_versions OWNER TO postgres;

--
-- Name: uploaded_files; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.uploaded_files (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_session_id uuid NOT NULL,
    file_name character varying NOT NULL,
    file_path character varying NOT NULL,
    file_size bigint NOT NULL,
    file_type character varying NOT NULL,
    mime_type character varying,
    checksum character varying,
    row_count integer,
    validation_status character varying NOT NULL,
    validation_errors jsonb,
    uploaded_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.uploaded_files OWNER TO postgres;

--
-- Name: user_filter_presets; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.user_filter_presets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    preset_name character varying(255) NOT NULL,
    preset_type character varying(50) NOT NULL,
    filters jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.user_filter_presets OWNER TO postgres;

--
-- Name: user_notifications; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.user_notifications (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    event_id uuid NOT NULL,
    is_read boolean NOT NULL,
    read_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.user_notifications OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying NOT NULL,
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    phone character varying,
    phone_number character varying(255),
    password_hash character varying,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    last_login timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    role character varying(255)
);


ALTER TABLE exam_system.users OWNER TO postgres;

--
-- Name: version_dependencies; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.version_dependencies (
    id uuid NOT NULL,
    version_id uuid NOT NULL,
    depends_on_version_id uuid NOT NULL,
    dependency_type character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.version_dependencies OWNER TO postgres;

--
-- Name: version_metadata; Type: TABLE; Schema: exam_system; Owner: postgres
--

CREATE TABLE exam_system.version_metadata (
    id uuid NOT NULL,
    version_id uuid NOT NULL,
    title character varying(255),
    description text,
    tags jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE exam_system.version_metadata OWNER TO postgres;

--
-- Name: academic_sessions academic_sessions_name_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.academic_sessions
    ADD CONSTRAINT academic_sessions_name_key UNIQUE (name);


--
-- Name: academic_sessions academic_sessions_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.academic_sessions
    ADD CONSTRAINT academic_sessions_pkey PRIMARY KEY (id);


--
-- Name: assignment_change_requests assignment_change_requests_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.assignment_change_requests
    ADD CONSTRAINT assignment_change_requests_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: buildings buildings_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.buildings
    ADD CONSTRAINT buildings_pkey PRIMARY KEY (id);


--
-- Name: configuration_rule_settings configuration_rule_settings_configuration_id_rule_id_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.configuration_rule_settings
    ADD CONSTRAINT configuration_rule_settings_configuration_id_rule_id_key UNIQUE (configuration_id, rule_id);


--
-- Name: configuration_rule_settings configuration_rule_settings_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.configuration_rule_settings
    ADD CONSTRAINT configuration_rule_settings_pkey PRIMARY KEY (id);


--
-- Name: conflict_reports conflict_reports_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.conflict_reports
    ADD CONSTRAINT conflict_reports_pkey PRIMARY KEY (id);


--
-- Name: constraint_configurations constraint_configurations_name_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.constraint_configurations
    ADD CONSTRAINT constraint_configurations_name_key UNIQUE (name);


--
-- Name: constraint_configurations constraint_configurations_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.constraint_configurations
    ADD CONSTRAINT constraint_configurations_pkey PRIMARY KEY (id);


--
-- Name: constraint_parameters constraint_parameters_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.constraint_parameters
    ADD CONSTRAINT constraint_parameters_pkey PRIMARY KEY (id);


--
-- Name: constraint_parameters constraint_parameters_rule_id_key_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.constraint_parameters
    ADD CONSTRAINT constraint_parameters_rule_id_key_key UNIQUE (rule_id, key);


--
-- Name: constraint_rules constraint_rules_code_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.constraint_rules
    ADD CONSTRAINT constraint_rules_code_key UNIQUE (code);


--
-- Name: constraint_rules constraint_rules_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.constraint_rules
    ADD CONSTRAINT constraint_rules_pkey PRIMARY KEY (id);


--
-- Name: course_departments course_departments_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_departments
    ADD CONSTRAINT course_departments_pkey PRIMARY KEY (course_id, department_id, session_id);


--
-- Name: course_faculties course_faculties_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_faculties
    ADD CONSTRAINT course_faculties_pkey PRIMARY KEY (course_id, faculty_id, session_id);


--
-- Name: course_instructors course_instructors_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_instructors
    ADD CONSTRAINT course_instructors_pkey PRIMARY KEY (course_id, staff_id, session_id);


--
-- Name: course_instructors course_instructors_session_unique; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_instructors
    ADD CONSTRAINT course_instructors_session_unique UNIQUE (staff_id, course_id, session_id);


--
-- Name: course_registrations course_registrations_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_registrations
    ADD CONSTRAINT course_registrations_pkey PRIMARY KEY (id);


--
-- Name: course_registrations course_registrations_unique; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_registrations
    ADD CONSTRAINT course_registrations_unique UNIQUE (student_id, course_id, session_id);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: data_seeding_sessions data_seeding_sessions_academic_session_id_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.data_seeding_sessions
    ADD CONSTRAINT data_seeding_sessions_academic_session_id_key UNIQUE (academic_session_id);


--
-- Name: data_seeding_sessions data_seeding_sessions_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.data_seeding_sessions
    ADD CONSTRAINT data_seeding_sessions_pkey PRIMARY KEY (id);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: exam_departments exam_departments_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_departments
    ADD CONSTRAINT exam_departments_pkey PRIMARY KEY (id);


--
-- Name: exam_invigilators exam_invigilators_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_invigilators
    ADD CONSTRAINT exam_invigilators_pkey PRIMARY KEY (id);


--
-- Name: exam_prerequisites_association exam_prerequisites_association_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_prerequisites_association
    ADD CONSTRAINT exam_prerequisites_association_pkey PRIMARY KEY (exam_id, prerequisite_id);


--
-- Name: exams exams_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exams
    ADD CONSTRAINT exams_pkey PRIMARY KEY (id);


--
-- Name: faculties faculties_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.faculties
    ADD CONSTRAINT faculties_pkey PRIMARY KEY (id);


--
-- Name: file_upload_sessions file_upload_sessions_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.file_upload_sessions
    ADD CONSTRAINT file_upload_sessions_pkey PRIMARY KEY (id);


--
-- Name: file_uploads file_uploads_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.file_uploads
    ADD CONSTRAINT file_uploads_pkey PRIMARY KEY (id);


--
-- Name: programmes programmes_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.programmes
    ADD CONSTRAINT programmes_pkey PRIMARY KEY (id);


--
-- Name: room_departments room_departments_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.room_departments
    ADD CONSTRAINT room_departments_pkey PRIMARY KEY (room_id, department_id);


--
-- Name: room_types room_types_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.room_types
    ADD CONSTRAINT room_types_pkey PRIMARY KEY (id);


--
-- Name: rooms rooms_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.rooms
    ADD CONSTRAINT rooms_pkey PRIMARY KEY (id);


--
-- Name: session_templates session_templates_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.session_templates
    ADD CONSTRAINT session_templates_pkey PRIMARY KEY (id);


--
-- Name: staff staff_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff
    ADD CONSTRAINT staff_pkey PRIMARY KEY (id);


--
-- Name: staff_unavailability staff_unavailability_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff_unavailability
    ADD CONSTRAINT staff_unavailability_pkey PRIMARY KEY (id);


--
-- Name: staff_unavailability staff_unavailability_unique; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff_unavailability
    ADD CONSTRAINT staff_unavailability_unique UNIQUE (staff_id, unavailable_date, time_slot_period);


--
-- Name: staff staff_user_id_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff
    ADD CONSTRAINT staff_user_id_key UNIQUE (user_id);


--
-- Name: student_enrollments student_enrollments_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.student_enrollments
    ADD CONSTRAINT student_enrollments_pkey PRIMARY KEY (id);


--
-- Name: student_enrollments student_session_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.student_enrollments
    ADD CONSTRAINT student_session_key UNIQUE (student_id, session_id);


--
-- Name: students students_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.students
    ADD CONSTRAINT students_pkey PRIMARY KEY (id);


--
-- Name: students students_user_id_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.students
    ADD CONSTRAINT students_user_id_key UNIQUE (user_id);


--
-- Name: system_configurations system_configurations_name_key; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.system_configurations
    ADD CONSTRAINT system_configurations_name_key UNIQUE (name);


--
-- Name: system_configurations system_configurations_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.system_configurations
    ADD CONSTRAINT system_configurations_pkey PRIMARY KEY (id);


--
-- Name: system_events system_events_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.system_events
    ADD CONSTRAINT system_events_pkey PRIMARY KEY (id);


--
-- Name: timeslot_template_periods timeslot_template_periods_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timeslot_template_periods
    ADD CONSTRAINT timeslot_template_periods_pkey PRIMARY KEY (id);


--
-- Name: timeslot_templates timeslot_templates_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timeslot_templates
    ADD CONSTRAINT timeslot_templates_pkey PRIMARY KEY (id);


--
-- Name: timetable_assignments timetable_assignments_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_assignments
    ADD CONSTRAINT timetable_assignments_pkey PRIMARY KEY (id);


--
-- Name: timetable_conflicts timetable_conflicts_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_conflicts
    ADD CONSTRAINT timetable_conflicts_pkey PRIMARY KEY (id);


--
-- Name: timetable_edits timetable_edits_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_edits
    ADD CONSTRAINT timetable_edits_pkey PRIMARY KEY (id);


--
-- Name: timetable_job_exam_days timetable_job_exam_days_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_job_exam_days
    ADD CONSTRAINT timetable_job_exam_days_pkey PRIMARY KEY (timetable_job_id, exam_date);


--
-- Name: timetable_jobs timetable_jobs_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_jobs
    ADD CONSTRAINT timetable_jobs_pkey PRIMARY KEY (id);


--
-- Name: timetable_locks timetable_locks_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_locks
    ADD CONSTRAINT timetable_locks_pkey PRIMARY KEY (id);


--
-- Name: timetable_scenarios timetable_scenarios_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_scenarios
    ADD CONSTRAINT timetable_scenarios_pkey PRIMARY KEY (id);


--
-- Name: timetable_versions timetable_versions_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_versions
    ADD CONSTRAINT timetable_versions_pkey PRIMARY KEY (id);


--
-- Name: uploaded_files uploaded_files_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.uploaded_files
    ADD CONSTRAINT uploaded_files_pkey PRIMARY KEY (id);


--
-- Name: buildings uq_building_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.buildings
    ADD CONSTRAINT uq_building_code_session UNIQUE (code, session_id);


--
-- Name: buildings uq_buildings_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.buildings
    ADD CONSTRAINT uq_buildings_code_session UNIQUE (code, session_id);


--
-- Name: courses uq_course_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.courses
    ADD CONSTRAINT uq_course_code_session UNIQUE (code, session_id);


--
-- Name: courses uq_courses_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.courses
    ADD CONSTRAINT uq_courses_code_session UNIQUE (code, session_id);


--
-- Name: departments uq_department_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.departments
    ADD CONSTRAINT uq_department_code_session UNIQUE (code, session_id);


--
-- Name: departments uq_departments_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.departments
    ADD CONSTRAINT uq_departments_code_session UNIQUE (code, session_id);


--
-- Name: faculties uq_faculties_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.faculties
    ADD CONSTRAINT uq_faculties_code_session UNIQUE (code, session_id);


--
-- Name: faculties uq_faculty_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.faculties
    ADD CONSTRAINT uq_faculty_code_session UNIQUE (code, session_id);


--
-- Name: programmes uq_programme_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.programmes
    ADD CONSTRAINT uq_programme_code_session UNIQUE (code, session_id);


--
-- Name: programmes uq_programmes_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.programmes
    ADD CONSTRAINT uq_programmes_code_session UNIQUE (code, session_id);


--
-- Name: rooms uq_room_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.rooms
    ADD CONSTRAINT uq_room_code_session UNIQUE (code, session_id);


--
-- Name: rooms uq_rooms_code_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.rooms
    ADD CONSTRAINT uq_rooms_code_session UNIQUE (code, session_id);


--
-- Name: staff uq_staff_number_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff
    ADD CONSTRAINT uq_staff_number_session UNIQUE (staff_number, session_id);


--
-- Name: students uq_student_matric_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.students
    ADD CONSTRAINT uq_student_matric_session UNIQUE (matric_number, session_id);


--
-- Name: students uq_students_matric_number_session; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.students
    ADD CONSTRAINT uq_students_matric_number_session UNIQUE (matric_number, session_id);


--
-- Name: timeslot_template_periods uq_template_period_name; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timeslot_template_periods
    ADD CONSTRAINT uq_template_period_name UNIQUE (timeslot_template_id, period_name);


--
-- Name: user_filter_presets user_filter_presets_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.user_filter_presets
    ADD CONSTRAINT user_filter_presets_pkey PRIMARY KEY (id);


--
-- Name: user_notifications user_notifications_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.user_notifications
    ADD CONSTRAINT user_notifications_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: version_dependencies version_dependencies_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.version_dependencies
    ADD CONSTRAINT version_dependencies_pkey PRIMARY KEY (id);


--
-- Name: version_metadata version_metadata_pkey; Type: CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.version_metadata
    ADD CONSTRAINT version_metadata_pkey PRIMARY KEY (id);


--
-- Name: configuration_rule_settings_configuration_id_idx; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX configuration_rule_settings_configuration_id_idx ON exam_system.configuration_rule_settings USING btree (configuration_id);


--
-- Name: configuration_rule_settings_rule_id_idx; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX configuration_rule_settings_rule_id_idx ON exam_system.configuration_rule_settings USING btree (rule_id);


--
-- Name: constraint_parameters_rule_id_idx; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX constraint_parameters_rule_id_idx ON exam_system.constraint_parameters USING btree (rule_id);


--
-- Name: idx_academic_sessions_active; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_academic_sessions_active ON exam_system.academic_sessions USING btree (is_active);


--
-- Name: idx_academic_sessions_archived_at; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_academic_sessions_archived_at ON exam_system.academic_sessions USING btree (archived_at);


--
-- Name: idx_academic_sessions_template_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_academic_sessions_template_id ON exam_system.academic_sessions USING btree (template_id);


--
-- Name: idx_session_templates_active; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_session_templates_active ON exam_system.session_templates USING btree (is_active);


--
-- Name: idx_session_templates_source_session_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_session_templates_source_session_id ON exam_system.session_templates USING btree (source_session_id);


--
-- Name: idx_timetable_assignments_exam_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_timetable_assignments_exam_id ON exam_system.timetable_assignments USING btree (exam_id);


--
-- Name: idx_timetable_assignments_version_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_timetable_assignments_version_id ON exam_system.timetable_assignments USING btree (version_id);


--
-- Name: idx_timetable_conflicts_version_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_timetable_conflicts_version_id ON exam_system.timetable_conflicts USING btree (version_id);


--
-- Name: idx_timetable_locks_scenario_active; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_timetable_locks_scenario_active ON exam_system.timetable_locks USING btree (scenario_id, is_active);


--
-- Name: idx_timetable_versions_active; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_timetable_versions_active ON exam_system.timetable_versions USING btree (is_active);


--
-- Name: idx_timetable_versions_job_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_timetable_versions_job_id ON exam_system.timetable_versions USING btree (job_id);


--
-- Name: idx_timetable_versions_parent_version_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_timetable_versions_parent_version_id ON exam_system.timetable_versions USING btree (parent_version_id);


--
-- Name: idx_timetable_versions_published; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_timetable_versions_published ON exam_system.timetable_versions USING btree (is_published);


--
-- Name: idx_version_dependencies_depends_on_version_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_version_dependencies_depends_on_version_id ON exam_system.version_dependencies USING btree (depends_on_version_id);


--
-- Name: idx_version_dependencies_version_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_version_dependencies_version_id ON exam_system.version_dependencies USING btree (version_id);


--
-- Name: idx_version_metadata_version_id; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX idx_version_metadata_version_id ON exam_system.version_metadata USING btree (version_id);


--
-- Name: ix_exam_system_users_email; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE UNIQUE INDEX ix_exam_system_users_email ON exam_system.users USING btree (email);


--
-- Name: staff_unavailability_unique_idx; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE UNIQUE INDEX staff_unavailability_unique_idx ON exam_system.staff_unavailability USING btree (staff_id, session_id, unavailable_date, time_slot_period);


--
-- Name: system_configurations_constraint_config_id_idx; Type: INDEX; Schema: exam_system; Owner: postgres
--

CREATE INDEX system_configurations_constraint_config_id_idx ON exam_system.system_configurations USING btree (constraint_config_id);


--
-- Name: users trg_enforce_lowercase_role; Type: TRIGGER; Schema: exam_system; Owner: postgres
--

CREATE TRIGGER trg_enforce_lowercase_role BEFORE INSERT OR UPDATE ON exam_system.users FOR EACH ROW EXECUTE FUNCTION exam_system.enforce_lowercase_role();


--
-- Name: timetable_versions trigger_unpublish_other_versions; Type: TRIGGER; Schema: exam_system; Owner: postgres
--

CREATE TRIGGER trigger_unpublish_other_versions BEFORE INSERT OR UPDATE ON exam_system.timetable_versions FOR EACH ROW WHEN ((new.is_published = true)) EXECUTE FUNCTION exam_system.unpublish_other_versions();


--
-- Name: users trigger_users_last_login; Type: TRIGGER; Schema: exam_system; Owner: postgres
--

CREATE TRIGGER trigger_users_last_login BEFORE UPDATE ON exam_system.users FOR EACH ROW WHEN ((old.last_login IS DISTINCT FROM new.last_login)) EXECUTE FUNCTION exam_system.update_last_login_timestamp();


--
-- Name: configuration_rule_settings update_configuration_rule_settings_updated_at; Type: TRIGGER; Schema: exam_system; Owner: postgres
--

CREATE TRIGGER update_configuration_rule_settings_updated_at BEFORE UPDATE ON exam_system.configuration_rule_settings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: constraint_configurations update_constraint_configurations_updated_at; Type: TRIGGER; Schema: exam_system; Owner: postgres
--

CREATE TRIGGER update_constraint_configurations_updated_at BEFORE UPDATE ON exam_system.constraint_configurations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: constraint_parameters update_constraint_parameters_updated_at; Type: TRIGGER; Schema: exam_system; Owner: postgres
--

CREATE TRIGGER update_constraint_parameters_updated_at BEFORE UPDATE ON exam_system.constraint_parameters FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: constraint_rules update_constraint_rules_updated_at; Type: TRIGGER; Schema: exam_system; Owner: postgres
--

CREATE TRIGGER update_constraint_rules_updated_at BEFORE UPDATE ON exam_system.constraint_rules FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: system_configurations update_system_configurations_updated_at; Type: TRIGGER; Schema: exam_system; Owner: postgres
--

CREATE TRIGGER update_system_configurations_updated_at BEFORE UPDATE ON exam_system.system_configurations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: academic_sessions academic_sessions_timeslot_template_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.academic_sessions
    ADD CONSTRAINT academic_sessions_timeslot_template_id_fkey FOREIGN KEY (timeslot_template_id) REFERENCES exam_system.timeslot_templates(id);


--
-- Name: assignment_change_requests assignment_change_requests_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.assignment_change_requests
    ADD CONSTRAINT assignment_change_requests_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES exam_system.users(id);


--
-- Name: assignment_change_requests assignment_change_requests_staff_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.assignment_change_requests
    ADD CONSTRAINT assignment_change_requests_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES exam_system.staff(id);


--
-- Name: assignment_change_requests assignment_change_requests_timetable_assignment_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.assignment_change_requests
    ADD CONSTRAINT assignment_change_requests_timetable_assignment_id_fkey FOREIGN KEY (timetable_assignment_id) REFERENCES exam_system.timetable_assignments(id);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES exam_system.users(id);


--
-- Name: configuration_rule_settings configuration_rule_settings_configuration_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.configuration_rule_settings
    ADD CONSTRAINT configuration_rule_settings_configuration_id_fkey FOREIGN KEY (configuration_id) REFERENCES exam_system.constraint_configurations(id) ON DELETE CASCADE;


--
-- Name: configuration_rule_settings configuration_rule_settings_rule_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.configuration_rule_settings
    ADD CONSTRAINT configuration_rule_settings_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES exam_system.constraint_rules(id) ON DELETE CASCADE;


--
-- Name: conflict_reports conflict_reports_exam_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.conflict_reports
    ADD CONSTRAINT conflict_reports_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES exam_system.exams(id);


--
-- Name: conflict_reports conflict_reports_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.conflict_reports
    ADD CONSTRAINT conflict_reports_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES exam_system.users(id);


--
-- Name: conflict_reports conflict_reports_student_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.conflict_reports
    ADD CONSTRAINT conflict_reports_student_id_fkey FOREIGN KEY (student_id) REFERENCES exam_system.students(id);


--
-- Name: constraint_configurations constraint_configurations_created_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.constraint_configurations
    ADD CONSTRAINT constraint_configurations_created_by_fkey FOREIGN KEY (created_by) REFERENCES exam_system.users(id);


--
-- Name: constraint_parameters constraint_parameters_rule_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.constraint_parameters
    ADD CONSTRAINT constraint_parameters_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES exam_system.constraint_rules(id) ON DELETE CASCADE;


--
-- Name: course_departments course_departments_course_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_departments
    ADD CONSTRAINT course_departments_course_id_fkey FOREIGN KEY (course_id) REFERENCES exam_system.courses(id) ON DELETE CASCADE;


--
-- Name: course_departments course_departments_department_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_departments
    ADD CONSTRAINT course_departments_department_id_fkey FOREIGN KEY (department_id) REFERENCES exam_system.departments(id) ON DELETE CASCADE;


--
-- Name: course_faculties course_faculties_course_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_faculties
    ADD CONSTRAINT course_faculties_course_id_fkey FOREIGN KEY (course_id) REFERENCES exam_system.courses(id) ON DELETE CASCADE;


--
-- Name: course_faculties course_faculties_faculty_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_faculties
    ADD CONSTRAINT course_faculties_faculty_id_fkey FOREIGN KEY (faculty_id) REFERENCES exam_system.faculties(id) ON DELETE CASCADE;


--
-- Name: course_instructors course_instructors_course_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_instructors
    ADD CONSTRAINT course_instructors_course_id_fkey FOREIGN KEY (course_id) REFERENCES exam_system.courses(id) ON DELETE CASCADE;


--
-- Name: course_instructors course_instructors_staff_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_instructors
    ADD CONSTRAINT course_instructors_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES exam_system.staff(id) ON DELETE CASCADE;


--
-- Name: course_registrations course_registrations_course_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_registrations
    ADD CONSTRAINT course_registrations_course_id_fkey FOREIGN KEY (course_id) REFERENCES exam_system.courses(id);


--
-- Name: course_registrations course_registrations_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_registrations
    ADD CONSTRAINT course_registrations_session_id_fkey FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id);


--
-- Name: course_registrations course_registrations_student_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_registrations
    ADD CONSTRAINT course_registrations_student_id_fkey FOREIGN KEY (student_id) REFERENCES exam_system.students(id);


--
-- Name: data_seeding_sessions data_seeding_sessions_academic_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.data_seeding_sessions
    ADD CONSTRAINT data_seeding_sessions_academic_session_id_fkey FOREIGN KEY (academic_session_id) REFERENCES exam_system.academic_sessions(id);


--
-- Name: data_seeding_sessions data_seeding_sessions_created_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.data_seeding_sessions
    ADD CONSTRAINT data_seeding_sessions_created_by_fkey FOREIGN KEY (created_by) REFERENCES exam_system.users(id);


--
-- Name: departments departments_faculty_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.departments
    ADD CONSTRAINT departments_faculty_id_fkey FOREIGN KEY (faculty_id) REFERENCES exam_system.faculties(id);


--
-- Name: exam_departments exam_departments_department_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_departments
    ADD CONSTRAINT exam_departments_department_id_fkey FOREIGN KEY (department_id) REFERENCES exam_system.departments(id) ON DELETE CASCADE;


--
-- Name: exam_departments exam_departments_exam_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_departments
    ADD CONSTRAINT exam_departments_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES exam_system.exams(id) ON DELETE CASCADE;


--
-- Name: exam_invigilators exam_invigilators_staff_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_invigilators
    ADD CONSTRAINT exam_invigilators_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES exam_system.staff(id);


--
-- Name: exam_invigilators exam_invigilators_timetable_assignment_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_invigilators
    ADD CONSTRAINT exam_invigilators_timetable_assignment_id_fkey FOREIGN KEY (timetable_assignment_id) REFERENCES exam_system.timetable_assignments(id);


--
-- Name: exam_prerequisites_association exam_prerequisites_association_exam_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_prerequisites_association
    ADD CONSTRAINT exam_prerequisites_association_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES exam_system.exams(id);


--
-- Name: exam_prerequisites_association exam_prerequisites_association_prerequisite_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exam_prerequisites_association
    ADD CONSTRAINT exam_prerequisites_association_prerequisite_id_fkey FOREIGN KEY (prerequisite_id) REFERENCES exam_system.exams(id);


--
-- Name: exams exams_course_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exams
    ADD CONSTRAINT exams_course_id_fkey FOREIGN KEY (course_id) REFERENCES exam_system.courses(id);


--
-- Name: exams exams_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.exams
    ADD CONSTRAINT exams_session_id_fkey FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id);


--
-- Name: file_upload_sessions file_upload_sessions_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.file_upload_sessions
    ADD CONSTRAINT file_upload_sessions_session_id_fkey FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id);


--
-- Name: file_upload_sessions file_upload_sessions_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.file_upload_sessions
    ADD CONSTRAINT file_upload_sessions_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES exam_system.users(id);


--
-- Name: file_uploads file_uploads_data_seeding_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.file_uploads
    ADD CONSTRAINT file_uploads_data_seeding_session_id_fkey FOREIGN KEY (data_seeding_session_id) REFERENCES exam_system.data_seeding_sessions(id);


--
-- Name: buildings fk_buildings_faculty_id; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.buildings
    ADD CONSTRAINT fk_buildings_faculty_id FOREIGN KEY (faculty_id) REFERENCES exam_system.faculties(id) ON DELETE SET NULL;


--
-- Name: buildings fk_buildings_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.buildings
    ADD CONSTRAINT fk_buildings_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: course_departments fk_course_departments_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_departments
    ADD CONSTRAINT fk_course_departments_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: course_faculties fk_course_faculties_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_faculties
    ADD CONSTRAINT fk_course_faculties_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: course_instructors fk_course_instructors_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.course_instructors
    ADD CONSTRAINT fk_course_instructors_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: courses fk_courses_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.courses
    ADD CONSTRAINT fk_courses_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: departments fk_departments_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.departments
    ADD CONSTRAINT fk_departments_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: faculties fk_faculties_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.faculties
    ADD CONSTRAINT fk_faculties_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: programmes fk_programmes_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.programmes
    ADD CONSTRAINT fk_programmes_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: rooms fk_rooms_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.rooms
    ADD CONSTRAINT fk_rooms_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: staff fk_staff_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff
    ADD CONSTRAINT fk_staff_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: students fk_students_session; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.students
    ADD CONSTRAINT fk_students_session FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id) ON DELETE CASCADE;


--
-- Name: programmes programmes_department_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.programmes
    ADD CONSTRAINT programmes_department_id_fkey FOREIGN KEY (department_id) REFERENCES exam_system.departments(id);


--
-- Name: room_departments room_departments_department_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.room_departments
    ADD CONSTRAINT room_departments_department_id_fkey FOREIGN KEY (department_id) REFERENCES exam_system.departments(id) ON DELETE CASCADE;


--
-- Name: room_departments room_departments_room_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.room_departments
    ADD CONSTRAINT room_departments_room_id_fkey FOREIGN KEY (room_id) REFERENCES exam_system.rooms(id) ON DELETE CASCADE;


--
-- Name: rooms rooms_building_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.rooms
    ADD CONSTRAINT rooms_building_id_fkey FOREIGN KEY (building_id) REFERENCES exam_system.buildings(id);


--
-- Name: rooms rooms_room_type_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.rooms
    ADD CONSTRAINT rooms_room_type_id_fkey FOREIGN KEY (room_type_id) REFERENCES exam_system.room_types(id);


--
-- Name: session_templates session_templates_source_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.session_templates
    ADD CONSTRAINT session_templates_source_session_id_fkey FOREIGN KEY (source_session_id) REFERENCES exam_system.academic_sessions(id);


--
-- Name: staff staff_department_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff
    ADD CONSTRAINT staff_department_id_fkey FOREIGN KEY (department_id) REFERENCES exam_system.departments(id);


--
-- Name: staff_unavailability staff_unavailability_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff_unavailability
    ADD CONSTRAINT staff_unavailability_session_id_fkey FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id);


--
-- Name: staff_unavailability staff_unavailability_staff_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff_unavailability
    ADD CONSTRAINT staff_unavailability_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES exam_system.staff(id);


--
-- Name: staff staff_user_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.staff
    ADD CONSTRAINT staff_user_id_fkey FOREIGN KEY (user_id) REFERENCES exam_system.users(id);


--
-- Name: student_enrollments student_enrollments_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.student_enrollments
    ADD CONSTRAINT student_enrollments_session_id_fkey FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id);


--
-- Name: student_enrollments student_enrollments_student_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.student_enrollments
    ADD CONSTRAINT student_enrollments_student_id_fkey FOREIGN KEY (student_id) REFERENCES exam_system.students(id);


--
-- Name: students students_programme_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.students
    ADD CONSTRAINT students_programme_id_fkey FOREIGN KEY (programme_id) REFERENCES exam_system.programmes(id);


--
-- Name: students students_user_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.students
    ADD CONSTRAINT students_user_id_fkey FOREIGN KEY (user_id) REFERENCES exam_system.users(id) ON DELETE SET NULL;


--
-- Name: system_configurations system_configurations_constraint_config_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.system_configurations
    ADD CONSTRAINT system_configurations_constraint_config_id_fkey FOREIGN KEY (constraint_config_id) REFERENCES exam_system.constraint_configurations(id);


--
-- Name: system_configurations system_configurations_created_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.system_configurations
    ADD CONSTRAINT system_configurations_created_by_fkey FOREIGN KEY (created_by) REFERENCES exam_system.users(id);


--
-- Name: system_events system_events_resolved_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.system_events
    ADD CONSTRAINT system_events_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES exam_system.users(id);


--
-- Name: timeslot_template_periods timeslot_template_periods_timeslot_template_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timeslot_template_periods
    ADD CONSTRAINT timeslot_template_periods_timeslot_template_id_fkey FOREIGN KEY (timeslot_template_id) REFERENCES exam_system.timeslot_templates(id) ON DELETE CASCADE;


--
-- Name: timetable_assignments timetable_assignments_exam_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_assignments
    ADD CONSTRAINT timetable_assignments_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES exam_system.exams(id);


--
-- Name: timetable_assignments timetable_assignments_room_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_assignments
    ADD CONSTRAINT timetable_assignments_room_id_fkey FOREIGN KEY (room_id) REFERENCES exam_system.rooms(id);


--
-- Name: timetable_assignments timetable_assignments_timeslot_template_period_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_assignments
    ADD CONSTRAINT timetable_assignments_timeslot_template_period_id_fkey FOREIGN KEY (timeslot_template_period_id) REFERENCES exam_system.timeslot_template_periods(id);


--
-- Name: timetable_assignments timetable_assignments_version_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_assignments
    ADD CONSTRAINT timetable_assignments_version_id_fkey FOREIGN KEY (version_id) REFERENCES exam_system.timetable_versions(id);


--
-- Name: timetable_conflicts timetable_conflicts_version_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_conflicts
    ADD CONSTRAINT timetable_conflicts_version_id_fkey FOREIGN KEY (version_id) REFERENCES exam_system.timetable_versions(id) ON DELETE CASCADE;


--
-- Name: timetable_edits timetable_edits_edited_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_edits
    ADD CONSTRAINT timetable_edits_edited_by_fkey FOREIGN KEY (edited_by) REFERENCES exam_system.users(id);


--
-- Name: timetable_edits timetable_edits_exam_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_edits
    ADD CONSTRAINT timetable_edits_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES exam_system.exams(id);


--
-- Name: timetable_edits timetable_edits_version_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_edits
    ADD CONSTRAINT timetable_edits_version_id_fkey FOREIGN KEY (version_id) REFERENCES exam_system.timetable_versions(id);


--
-- Name: timetable_job_exam_days timetable_job_exam_days_timetable_job_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_job_exam_days
    ADD CONSTRAINT timetable_job_exam_days_timetable_job_id_fkey FOREIGN KEY (timetable_job_id) REFERENCES exam_system.timetable_jobs(id) ON DELETE CASCADE;


--
-- Name: timetable_jobs timetable_jobs_initiated_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_jobs
    ADD CONSTRAINT timetable_jobs_initiated_by_fkey FOREIGN KEY (initiated_by) REFERENCES exam_system.users(id);


--
-- Name: timetable_jobs timetable_jobs_scenario_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_jobs
    ADD CONSTRAINT timetable_jobs_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES exam_system.timetable_scenarios(id);


--
-- Name: timetable_jobs timetable_jobs_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_jobs
    ADD CONSTRAINT timetable_jobs_session_id_fkey FOREIGN KEY (session_id) REFERENCES exam_system.academic_sessions(id);


--
-- Name: timetable_locks timetable_locks_exam_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_locks
    ADD CONSTRAINT timetable_locks_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES exam_system.exams(id);


--
-- Name: timetable_locks timetable_locks_locked_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_locks
    ADD CONSTRAINT timetable_locks_locked_by_fkey FOREIGN KEY (locked_by) REFERENCES exam_system.users(id);


--
-- Name: timetable_locks timetable_locks_scenario_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_locks
    ADD CONSTRAINT timetable_locks_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES exam_system.timetable_scenarios(id);


--
-- Name: timetable_locks timetable_locks_timeslot_template_period_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_locks
    ADD CONSTRAINT timetable_locks_timeslot_template_period_id_fkey FOREIGN KEY (timeslot_template_period_id) REFERENCES exam_system.timeslot_template_periods(id);


--
-- Name: timetable_scenarios timetable_scenarios_created_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_scenarios
    ADD CONSTRAINT timetable_scenarios_created_by_fkey FOREIGN KEY (created_by) REFERENCES exam_system.users(id);


--
-- Name: timetable_versions timetable_versions_approved_by_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_versions
    ADD CONSTRAINT timetable_versions_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES exam_system.users(id);


--
-- Name: timetable_versions timetable_versions_job_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_versions
    ADD CONSTRAINT timetable_versions_job_id_fkey FOREIGN KEY (job_id) REFERENCES exam_system.timetable_jobs(id);


--
-- Name: timetable_versions timetable_versions_parent_version_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_versions
    ADD CONSTRAINT timetable_versions_parent_version_id_fkey FOREIGN KEY (parent_version_id) REFERENCES exam_system.timetable_versions(id);


--
-- Name: timetable_versions timetable_versions_scenario_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.timetable_versions
    ADD CONSTRAINT timetable_versions_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES exam_system.timetable_scenarios(id) ON DELETE CASCADE;


--
-- Name: uploaded_files uploaded_files_upload_session_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.uploaded_files
    ADD CONSTRAINT uploaded_files_upload_session_id_fkey FOREIGN KEY (upload_session_id) REFERENCES exam_system.file_upload_sessions(id);


--
-- Name: user_filter_presets user_filter_presets_user_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.user_filter_presets
    ADD CONSTRAINT user_filter_presets_user_id_fkey FOREIGN KEY (user_id) REFERENCES exam_system.users(id) ON DELETE CASCADE;


--
-- Name: user_notifications user_notifications_event_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.user_notifications
    ADD CONSTRAINT user_notifications_event_id_fkey FOREIGN KEY (event_id) REFERENCES exam_system.system_events(id);


--
-- Name: user_notifications user_notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.user_notifications
    ADD CONSTRAINT user_notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES exam_system.users(id);


--
-- Name: version_dependencies version_dependencies_depends_on_version_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.version_dependencies
    ADD CONSTRAINT version_dependencies_depends_on_version_id_fkey FOREIGN KEY (depends_on_version_id) REFERENCES exam_system.timetable_versions(id) ON DELETE CASCADE;


--
-- Name: version_dependencies version_dependencies_version_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.version_dependencies
    ADD CONSTRAINT version_dependencies_version_id_fkey FOREIGN KEY (version_id) REFERENCES exam_system.timetable_versions(id) ON DELETE CASCADE;


--
-- Name: version_metadata version_metadata_version_id_fkey; Type: FK CONSTRAINT; Schema: exam_system; Owner: postgres
--

ALTER TABLE ONLY exam_system.version_metadata
    ADD CONSTRAINT version_metadata_version_id_fkey FOREIGN KEY (version_id) REFERENCES exam_system.timetable_versions(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

