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
-- Name: staging; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA staging;


ALTER SCHEMA staging OWNER TO postgres;

--
-- Name: add_building(uuid, character varying, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_building(p_session_id uuid, p_code character varying, p_name character varying, p_faculty_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.buildings (session_id, code, name, faculty_code)
    VALUES (p_session_id, p_code, p_name, p_faculty_code);
END;
$$;


ALTER FUNCTION staging.add_building(p_session_id uuid, p_code character varying, p_name character varying, p_faculty_code character varying) OWNER TO postgres;

--
-- Name: add_course(uuid, character varying, character varying, integer, integer, integer, integer, boolean, boolean); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_course(p_session_id uuid, p_code character varying, p_title character varying, p_credit_units integer, p_exam_duration_minutes integer, p_course_level integer, p_semester integer, p_is_practical boolean, p_morning_only boolean) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.courses (session_id, code, title, credit_units, exam_duration_minutes, course_level, semester, is_practical, morning_only)
    VALUES (p_session_id, p_code, p_title, p_credit_units, p_exam_duration_minutes, p_course_level, p_semester, p_is_practical, p_morning_only);
END;
$$;


ALTER FUNCTION staging.add_course(p_session_id uuid, p_code character varying, p_title character varying, p_credit_units integer, p_exam_duration_minutes integer, p_course_level integer, p_semester integer, p_is_practical boolean, p_morning_only boolean) OWNER TO postgres;

--
-- Name: add_course_department(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_course_department(p_session_id uuid, p_course_code character varying, p_department_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.course_departments (session_id, course_code, department_code)
    VALUES (p_session_id, p_course_code, p_department_code);
END;
$$;


ALTER FUNCTION staging.add_course_department(p_session_id uuid, p_course_code character varying, p_department_code character varying) OWNER TO postgres;

--
-- Name: add_course_faculty(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_course_faculty(p_session_id uuid, p_course_code character varying, p_faculty_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.course_faculties (session_id, course_code, faculty_code)
    VALUES (p_session_id, p_course_code, p_faculty_code);
END;
$$;


ALTER FUNCTION staging.add_course_faculty(p_session_id uuid, p_course_code character varying, p_faculty_code character varying) OWNER TO postgres;

--
-- Name: add_course_instructor(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_course_instructor(p_session_id uuid, p_staff_number character varying, p_course_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.course_instructors (session_id, staff_number, course_code)
    VALUES (p_session_id, p_staff_number, p_course_code);
END;
$$;


ALTER FUNCTION staging.add_course_instructor(p_session_id uuid, p_staff_number character varying, p_course_code character varying) OWNER TO postgres;

--
-- Name: add_course_registration(uuid, character varying, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_course_registration(p_session_id uuid, p_student_matric_number character varying, p_course_code character varying, p_registration_type character varying DEFAULT 'regular'::character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.course_registrations (session_id, student_matric_number, course_code, registration_type)
    VALUES (p_session_id, p_student_matric_number, p_course_code, p_registration_type);
END;
$$;


ALTER FUNCTION staging.add_course_registration(p_session_id uuid, p_student_matric_number character varying, p_course_code character varying, p_registration_type character varying) OWNER TO postgres;

--
-- Name: add_department(uuid, character varying, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_department(p_session_id uuid, p_code character varying, p_name character varying, p_faculty_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.departments (session_id, code, name, faculty_code)
    VALUES (p_session_id, p_code, p_name, p_faculty_code);
END;
$$;


ALTER FUNCTION staging.add_department(p_session_id uuid, p_code character varying, p_name character varying, p_faculty_code character varying) OWNER TO postgres;

--
-- Name: add_faculty(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_faculty(p_session_id uuid, p_code character varying, p_name character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.faculties (session_id, code, name)
    VALUES (p_session_id, p_code, p_name);
END;
$$;


ALTER FUNCTION staging.add_faculty(p_session_id uuid, p_code character varying, p_name character varying) OWNER TO postgres;

--
-- Name: add_programme(uuid, character varying, character varying, character varying, character varying, integer); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_programme(p_session_id uuid, p_code character varying, p_name character varying, p_department_code character varying, p_degree_type character varying, p_duration_years integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.programmes (session_id, code, name, department_code, degree_type, duration_years)
    VALUES (p_session_id, p_code, p_name, p_department_code, p_degree_type, p_duration_years);
END;
$$;


ALTER FUNCTION staging.add_programme(p_session_id uuid, p_code character varying, p_name character varying, p_department_code character varying, p_degree_type character varying, p_duration_years integer) OWNER TO postgres;

--
-- Name: add_room(uuid, character varying, character varying, character varying, integer, integer, boolean, boolean, boolean, integer, character varying, integer, character varying[], text); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_room(p_session_id uuid, p_code character varying, p_name character varying, p_building_code character varying, p_capacity integer, p_exam_capacity integer, p_has_ac boolean, p_has_projector boolean, p_has_computers boolean, p_max_inv_per_room integer, p_room_type_code character varying, p_floor_number integer, p_accessibility_features character varying[], p_notes text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.rooms (session_id, code, name, building_code, capacity, exam_capacity, has_ac, has_projector, has_computers, max_inv_per_room, room_type_code, floor_number, accessibility_features, notes)
    VALUES (p_session_id, p_code, p_name, p_building_code, p_capacity, p_exam_capacity, p_has_ac, p_has_projector, p_has_computers, p_max_inv_per_room, p_room_type_code, p_floor_number, p_accessibility_features, p_notes);
END;
$$;


ALTER FUNCTION staging.add_room(p_session_id uuid, p_code character varying, p_name character varying, p_building_code character varying, p_capacity integer, p_exam_capacity integer, p_has_ac boolean, p_has_projector boolean, p_has_computers boolean, p_max_inv_per_room integer, p_room_type_code character varying, p_floor_number integer, p_accessibility_features character varying[], p_notes text) OWNER TO postgres;

--
-- Name: add_staff(uuid, character varying, character varying, character varying, character varying, character varying, character varying, boolean, boolean, integer, integer, integer, integer, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_staff(p_session_id uuid, p_staff_number character varying, p_first_name character varying, p_last_name character varying, p_email character varying, p_department_code character varying, p_staff_type character varying, p_can_invigilate boolean, p_is_instructor boolean, p_max_daily_sessions integer, p_max_consecutive_sessions integer, p_max_concurrent_exams integer, p_max_students_per_invigilator integer, p_user_email character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.staff (session_id, staff_number, first_name, last_name, email, department_code, staff_type, can_invigilate, is_instructor, max_daily_sessions, max_consecutive_sessions, max_concurrent_exams, max_students_per_invigilator, user_email)
    VALUES (p_session_id, p_staff_number, p_first_name, p_last_name, p_email, p_department_code, p_staff_type, p_can_invigilate, p_is_instructor, p_max_daily_sessions, p_max_consecutive_sessions, p_max_concurrent_exams, p_max_students_per_invigilator, p_user_email);
END;
$$;


ALTER FUNCTION staging.add_staff(p_session_id uuid, p_staff_number character varying, p_first_name character varying, p_last_name character varying, p_email character varying, p_department_code character varying, p_staff_type character varying, p_can_invigilate boolean, p_is_instructor boolean, p_max_daily_sessions integer, p_max_consecutive_sessions integer, p_max_concurrent_exams integer, p_max_students_per_invigilator integer, p_user_email character varying) OWNER TO postgres;

--
-- Name: add_staff_unavailability(uuid, character varying, date, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_staff_unavailability(p_session_id uuid, p_staff_number character varying, p_unavailable_date date, p_period_name character varying, p_reason character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.staff_unavailability (session_id, staff_number, unavailable_date, period_name, reason)
    VALUES (p_session_id, p_staff_number, p_unavailable_date, p_period_name, p_reason);
END;
$$;


ALTER FUNCTION staging.add_staff_unavailability(p_session_id uuid, p_staff_number character varying, p_unavailable_date date, p_period_name character varying, p_reason character varying) OWNER TO postgres;

--
-- Name: add_student(uuid, character varying, character varying, character varying, integer, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.add_student(p_session_id uuid, p_matric_number character varying, p_first_name character varying, p_last_name character varying, p_entry_year integer, p_programme_code character varying, p_user_email character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO staging.students (session_id, matric_number, first_name, last_name, entry_year, programme_code, user_email)
    VALUES (p_session_id, p_matric_number, p_first_name, p_last_name, p_entry_year, p_programme_code, p_user_email);
END;
$$;


ALTER FUNCTION staging.add_student(p_session_id uuid, p_matric_number character varying, p_first_name character varying, p_last_name character varying, p_entry_year integer, p_programme_code character varying, p_user_email character varying) OWNER TO postgres;

--
-- Name: delete_building(uuid, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_building(p_session_id uuid, p_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.buildings
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.delete_building(p_session_id uuid, p_code character varying) OWNER TO postgres;

--
-- Name: delete_course(uuid, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_course(p_session_id uuid, p_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.courses
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.delete_course(p_session_id uuid, p_code character varying) OWNER TO postgres;

--
-- Name: delete_course_department(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_course_department(p_session_id uuid, p_course_code character varying, p_department_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.course_departments
    WHERE session_id = p_session_id AND course_code = p_course_code AND department_code = p_department_code;
END;
$$;


ALTER FUNCTION staging.delete_course_department(p_session_id uuid, p_course_code character varying, p_department_code character varying) OWNER TO postgres;

--
-- Name: delete_course_faculty(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_course_faculty(p_session_id uuid, p_course_code character varying, p_faculty_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.course_faculties
    WHERE session_id = p_session_id AND course_code = p_course_code AND faculty_code = p_faculty_code;
END;
$$;


ALTER FUNCTION staging.delete_course_faculty(p_session_id uuid, p_course_code character varying, p_faculty_code character varying) OWNER TO postgres;

--
-- Name: delete_course_instructor(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_course_instructor(p_session_id uuid, p_staff_number character varying, p_course_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.course_instructors
    WHERE session_id = p_session_id AND staff_number = p_staff_number AND course_code = p_course_code;
END;
$$;


ALTER FUNCTION staging.delete_course_instructor(p_session_id uuid, p_staff_number character varying, p_course_code character varying) OWNER TO postgres;

--
-- Name: delete_course_registration(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_course_registration(p_session_id uuid, p_student_matric_number character varying, p_course_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.course_registrations
    WHERE session_id = p_session_id AND student_matric_number = p_student_matric_number AND course_code = p_course_code;
END;
$$;


ALTER FUNCTION staging.delete_course_registration(p_session_id uuid, p_student_matric_number character varying, p_course_code character varying) OWNER TO postgres;

--
-- Name: delete_department(uuid, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_department(p_session_id uuid, p_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.departments
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.delete_department(p_session_id uuid, p_code character varying) OWNER TO postgres;

--
-- Name: delete_faculty(uuid, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_faculty(p_session_id uuid, p_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.faculties
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.delete_faculty(p_session_id uuid, p_code character varying) OWNER TO postgres;

--
-- Name: delete_programme(uuid, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_programme(p_session_id uuid, p_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.programmes
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.delete_programme(p_session_id uuid, p_code character varying) OWNER TO postgres;

--
-- Name: delete_room(uuid, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_room(p_session_id uuid, p_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.rooms
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.delete_room(p_session_id uuid, p_code character varying) OWNER TO postgres;

--
-- Name: delete_staff(uuid, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_staff(p_session_id uuid, p_staff_number character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.staff
    WHERE session_id = p_session_id AND staff_number = p_staff_number;
END;
$$;


ALTER FUNCTION staging.delete_staff(p_session_id uuid, p_staff_number character varying) OWNER TO postgres;

--
-- Name: delete_staff_unavailability(uuid, character varying, date, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_staff_unavailability(p_session_id uuid, p_staff_number character varying, p_unavailable_date date, p_period_name character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.staff_unavailability
    WHERE session_id = p_session_id AND staff_number = p_staff_number AND unavailable_date = p_unavailable_date AND period_name = p_period_name;
END;
$$;


ALTER FUNCTION staging.delete_staff_unavailability(p_session_id uuid, p_staff_number character varying, p_unavailable_date date, p_period_name character varying) OWNER TO postgres;

--
-- Name: delete_student(uuid, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.delete_student(p_session_id uuid, p_matric_number character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM staging.students
    WHERE session_id = p_session_id AND matric_number = p_matric_number;
END;
$$;


ALTER FUNCTION staging.delete_student(p_session_id uuid, p_matric_number character varying) OWNER TO postgres;

--
-- Name: get_session_data(uuid); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.get_session_data(p_session_id uuid) RETURNS json
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'buildings', COALESCE((SELECT json_agg(b) FROM (SELECT code, name, faculty_code FROM staging.buildings WHERE session_id = p_session_id) as b), '[]'::json),
            'course_departments', COALESCE((SELECT json_agg(cd) FROM (SELECT course_code, department_code FROM staging.course_departments WHERE session_id = p_session_id) as cd), '[]'::json),
            'course_faculties', COALESCE((SELECT json_agg(cf) FROM (SELECT course_code, faculty_code FROM staging.course_faculties WHERE session_id = p_session_id) as cf), '[]'::json),
            'course_instructors', COALESCE((SELECT json_agg(ci) FROM (SELECT staff_number, course_code FROM staging.course_instructors WHERE session_id = p_session_id) as ci), '[]'::json),
            'course_registrations', COALESCE((SELECT json_agg(cr) FROM (SELECT student_matric_number, course_code, registration_type FROM staging.course_registrations WHERE session_id = p_session_id) as cr), '[]'::json),
            'courses', COALESCE((SELECT json_agg(c) FROM (SELECT code, title, credit_units, exam_duration_minutes, course_level, semester, is_practical, morning_only FROM staging.courses WHERE session_id = p_session_id) as c), '[]'::json),
            'departments', COALESCE((SELECT json_agg(d) FROM (SELECT code, name, faculty_code FROM staging.departments WHERE session_id = p_session_id) as d), '[]'::json),
            'faculties', COALESCE((SELECT json_agg(f) FROM (SELECT code, name FROM staging.faculties WHERE session_id = p_session_id) as f), '[]'::json),
            'programmes', COALESCE((SELECT json_agg(p) FROM (SELECT code, name, department_code, degree_type, duration_years FROM staging.programmes WHERE session_id = p_session_id) as p), '[]'::json),
            'rooms', COALESCE((SELECT json_agg(r) FROM (SELECT code, name, building_code, capacity, exam_capacity, has_ac, has_projector, has_computers, max_inv_per_room, room_type_code, floor_number, accessibility_features, notes FROM staging.rooms WHERE session_id = p_session_id) as r), '[]'::json),
            'staff', COALESCE((SELECT json_agg(s) FROM (SELECT staff_number, first_name, last_name, email, department_code, staff_type, can_invigilate, is_instructor, max_daily_sessions, max_consecutive_sessions, max_concurrent_exams, max_students_per_invigilator, user_email FROM staging.staff WHERE session_id = p_session_id) as s), '[]'::json),
            'staff_unavailability', COALESCE((SELECT json_agg(su) FROM (SELECT staff_number, unavailable_date, period_name, reason FROM staging.staff_unavailability WHERE session_id = p_session_id) as su), '[]'::json),
            'students', COALESCE((SELECT json_agg(st) FROM (SELECT matric_number, first_name, last_name, entry_year, programme_code, user_email FROM staging.students WHERE session_id = p_session_id) as st), '[]'::json)
        )
    );
END;
$$;


ALTER FUNCTION staging.get_session_data(p_session_id uuid) OWNER TO postgres;

--
-- Name: update_building(uuid, character varying, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_building(p_session_id uuid, p_code character varying, p_name character varying, p_faculty_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.buildings
    SET name = p_name,
        faculty_code = p_faculty_code
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.update_building(p_session_id uuid, p_code character varying, p_name character varying, p_faculty_code character varying) OWNER TO postgres;

--
-- Name: update_course(uuid, character varying, character varying, integer, integer, integer, integer, boolean, boolean); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_course(p_session_id uuid, p_code character varying, p_title character varying, p_credit_units integer, p_exam_duration_minutes integer, p_course_level integer, p_semester integer, p_is_practical boolean, p_morning_only boolean) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.courses
    SET title = p_title,
        credit_units = p_credit_units,
        exam_duration_minutes = p_exam_duration_minutes,
        course_level = p_course_level,
        semester = p_semester,
        is_practical = p_is_practical,
        morning_only = p_morning_only
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.update_course(p_session_id uuid, p_code character varying, p_title character varying, p_credit_units integer, p_exam_duration_minutes integer, p_course_level integer, p_semester integer, p_is_practical boolean, p_morning_only boolean) OWNER TO postgres;

--
-- Name: update_course_department(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_course_department(p_session_id uuid, p_course_code character varying, p_department_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.course_departments
    SET department_code = p_department_code
    WHERE session_id = p_session_id AND course_code = p_course_code;
END;
$$;


ALTER FUNCTION staging.update_course_department(p_session_id uuid, p_course_code character varying, p_department_code character varying) OWNER TO postgres;

--
-- Name: update_course_department(uuid, character varying, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_course_department(p_session_id uuid, p_course_code character varying, p_old_department_code character varying, p_new_department_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- On a linking table where all columns are part of the primary key,
    -- an "update" is logically a delete followed by an insert.
    DELETE FROM staging.course_departments
    WHERE session_id = p_session_id
      AND course_code = p_course_code
      AND department_code = p_old_department_code;

    INSERT INTO staging.course_departments (session_id, course_code, department_code)
    VALUES (p_session_id, p_course_code, p_new_department_code)
    ON CONFLICT (session_id, course_code, department_code) DO NOTHING;
END;
$$;


ALTER FUNCTION staging.update_course_department(p_session_id uuid, p_course_code character varying, p_old_department_code character varying, p_new_department_code character varying) OWNER TO postgres;

--
-- Name: update_course_faculty(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_course_faculty(p_session_id uuid, p_course_code character varying, p_faculty_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.course_faculties
    SET faculty_code = p_faculty_code
    WHERE session_id = p_session_id AND course_code = p_course_code;
END;
$$;


ALTER FUNCTION staging.update_course_faculty(p_session_id uuid, p_course_code character varying, p_faculty_code character varying) OWNER TO postgres;

--
-- Name: update_course_faculty(uuid, character varying, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_course_faculty(p_session_id uuid, p_course_code character varying, p_old_faculty_code character varying, p_new_faculty_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- On a linking table where all columns are part of the primary key,
    -- an "update" is logically a delete followed by an insert.
    DELETE FROM staging.course_faculties
    WHERE session_id = p_session_id
      AND course_code = p_course_code
      AND faculty_code = p_old_faculty_code;

    INSERT INTO staging.course_faculties (session_id, course_code, faculty_code)
    VALUES (p_session_id, p_course_code, p_new_faculty_code)
    ON CONFLICT (session_id, course_code, faculty_code) DO NOTHING;
END;
$$;


ALTER FUNCTION staging.update_course_faculty(p_session_id uuid, p_course_code character varying, p_old_faculty_code character varying, p_new_faculty_code character varying) OWNER TO postgres;

--
-- Name: update_course_registration(uuid, character varying, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_course_registration(p_session_id uuid, p_student_matric_number character varying, p_course_code character varying, p_registration_type character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.course_registrations
    SET registration_type = p_registration_type
    WHERE session_id = p_session_id AND student_matric_number = p_student_matric_number AND course_code = p_course_code;
END;
$$;


ALTER FUNCTION staging.update_course_registration(p_session_id uuid, p_student_matric_number character varying, p_course_code character varying, p_registration_type character varying) OWNER TO postgres;

--
-- Name: update_department(uuid, character varying, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_department(p_session_id uuid, p_code character varying, p_name character varying, p_faculty_code character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.departments
    SET name = p_name,
        faculty_code = p_faculty_code
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.update_department(p_session_id uuid, p_code character varying, p_name character varying, p_faculty_code character varying) OWNER TO postgres;

--
-- Name: update_faculty(uuid, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_faculty(p_session_id uuid, p_code character varying, p_name character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.faculties
    SET name = p_name
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.update_faculty(p_session_id uuid, p_code character varying, p_name character varying) OWNER TO postgres;

--
-- Name: update_programme(uuid, character varying, character varying, character varying, character varying, integer); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_programme(p_session_id uuid, p_code character varying, p_name character varying, p_department_code character varying, p_degree_type character varying, p_duration_years integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.programmes
    SET name = p_name,
        department_code = p_department_code,
        degree_type = p_degree_type,
        duration_years = p_duration_years
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.update_programme(p_session_id uuid, p_code character varying, p_name character varying, p_department_code character varying, p_degree_type character varying, p_duration_years integer) OWNER TO postgres;

--
-- Name: update_room(uuid, character varying, character varying, character varying, integer, integer, boolean, boolean, boolean, integer, character varying, integer, character varying[], text); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_room(p_session_id uuid, p_code character varying, p_name character varying, p_building_code character varying, p_capacity integer, p_exam_capacity integer, p_has_ac boolean, p_has_projector boolean, p_has_computers boolean, p_max_inv_per_room integer, p_room_type_code character varying, p_floor_number integer, p_accessibility_features character varying[], p_notes text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.rooms
    SET name = p_name,
        building_code = p_building_code,
        capacity = p_capacity,
        exam_capacity = p_exam_capacity,
        has_ac = p_has_ac,
        has_projector = p_has_projector,
        has_computers = p_has_computers,
        max_inv_per_room = p_max_inv_per_room,
        room_type_code = p_room_type_code,
        floor_number = p_floor_number,
        accessibility_features = p_accessibility_features,
        notes = p_notes
    WHERE session_id = p_session_id AND code = p_code;
END;
$$;


ALTER FUNCTION staging.update_room(p_session_id uuid, p_code character varying, p_name character varying, p_building_code character varying, p_capacity integer, p_exam_capacity integer, p_has_ac boolean, p_has_projector boolean, p_has_computers boolean, p_max_inv_per_room integer, p_room_type_code character varying, p_floor_number integer, p_accessibility_features character varying[], p_notes text) OWNER TO postgres;

--
-- Name: update_staff(uuid, character varying, character varying, character varying, character varying, character varying, character varying, boolean, boolean, integer, integer, integer, integer, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_staff(p_session_id uuid, p_staff_number character varying, p_first_name character varying, p_last_name character varying, p_email character varying, p_department_code character varying, p_staff_type character varying, p_can_invigilate boolean, p_is_instructor boolean, p_max_daily_sessions integer, p_max_consecutive_sessions integer, p_max_concurrent_exams integer, p_max_students_per_invigilator integer, p_user_email character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.staff
    SET first_name = p_first_name,
        last_name = p_last_name,
        email = p_email,
        department_code = p_department_code,
        staff_type = p_staff_type,
        can_invigilate = p_can_invigilate,
        is_instructor = p_is_instructor,
        max_daily_sessions = p_max_daily_sessions,
        max_consecutive_sessions = p_max_consecutive_sessions,
        max_concurrent_exams = p_max_concurrent_exams,
        max_students_per_invigilator = p_max_students_per_invigilator,
        user_email = p_user_email
    WHERE session_id = p_session_id AND staff_number = p_staff_number;
END;
$$;


ALTER FUNCTION staging.update_staff(p_session_id uuid, p_staff_number character varying, p_first_name character varying, p_last_name character varying, p_email character varying, p_department_code character varying, p_staff_type character varying, p_can_invigilate boolean, p_is_instructor boolean, p_max_daily_sessions integer, p_max_consecutive_sessions integer, p_max_concurrent_exams integer, p_max_students_per_invigilator integer, p_user_email character varying) OWNER TO postgres;

--
-- Name: update_staff_unavailability(uuid, character varying, date, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_staff_unavailability(p_session_id uuid, p_staff_number character varying, p_unavailable_date date, p_period_name character varying, p_reason character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.staff_unavailability
    SET reason = p_reason
    WHERE session_id = p_session_id AND staff_number = p_staff_number AND unavailable_date = p_unavailable_date AND period_name = p_period_name;
END;
$$;


ALTER FUNCTION staging.update_staff_unavailability(p_session_id uuid, p_staff_number character varying, p_unavailable_date date, p_period_name character varying, p_reason character varying) OWNER TO postgres;

--
-- Name: update_student(uuid, character varying, character varying, character varying, integer, character varying, character varying); Type: FUNCTION; Schema: staging; Owner: postgres
--

CREATE FUNCTION staging.update_student(p_session_id uuid, p_matric_number character varying, p_first_name character varying, p_last_name character varying, p_entry_year integer, p_programme_code character varying, p_user_email character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE staging.students
    SET first_name = p_first_name,
        last_name = p_last_name,
        entry_year = p_entry_year,
        programme_code = p_programme_code,
        user_email = p_user_email
    WHERE session_id = p_session_id AND matric_number = p_matric_number;
END;
$$;


ALTER FUNCTION staging.update_student(p_session_id uuid, p_matric_number character varying, p_first_name character varying, p_last_name character varying, p_entry_year integer, p_programme_code character varying, p_user_email character varying) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: buildings; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.buildings (
    session_id uuid NOT NULL,
    code character varying,
    name character varying,
    faculty_code character varying
);


ALTER TABLE staging.buildings OWNER TO postgres;

--
-- Name: course_departments; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.course_departments (
    session_id uuid NOT NULL,
    course_code character varying,
    department_code character varying
);


ALTER TABLE staging.course_departments OWNER TO postgres;

--
-- Name: course_faculties; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.course_faculties (
    session_id uuid NOT NULL,
    course_code character varying,
    faculty_code character varying
);


ALTER TABLE staging.course_faculties OWNER TO postgres;

--
-- Name: course_instructors; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.course_instructors (
    session_id uuid NOT NULL,
    staff_number character varying,
    course_code character varying
);


ALTER TABLE staging.course_instructors OWNER TO postgres;

--
-- Name: course_registrations; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.course_registrations (
    session_id uuid NOT NULL,
    student_matric_number character varying,
    course_code character varying,
    registration_type character varying DEFAULT 'regular'::character varying
);


ALTER TABLE staging.course_registrations OWNER TO postgres;

--
-- Name: courses; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.courses (
    session_id uuid NOT NULL,
    code character varying,
    title character varying,
    credit_units integer,
    exam_duration_minutes integer,
    course_level integer,
    semester integer,
    is_practical boolean,
    morning_only boolean
);


ALTER TABLE staging.courses OWNER TO postgres;

--
-- Name: departments; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.departments (
    session_id uuid NOT NULL,
    code character varying,
    name character varying,
    faculty_code character varying
);


ALTER TABLE staging.departments OWNER TO postgres;

--
-- Name: faculties; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.faculties (
    session_id uuid NOT NULL,
    code character varying,
    name character varying
);


ALTER TABLE staging.faculties OWNER TO postgres;

--
-- Name: programmes; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.programmes (
    session_id uuid NOT NULL,
    code character varying,
    name character varying,
    department_code character varying,
    degree_type character varying,
    duration_years integer
);


ALTER TABLE staging.programmes OWNER TO postgres;

--
-- Name: rooms; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.rooms (
    session_id uuid NOT NULL,
    code character varying,
    name character varying,
    building_code character varying,
    capacity integer,
    exam_capacity integer,
    has_ac boolean,
    has_projector boolean,
    has_computers boolean,
    max_inv_per_room integer,
    room_type_code character varying,
    floor_number integer,
    accessibility_features character varying[],
    notes text
);


ALTER TABLE staging.rooms OWNER TO postgres;

--
-- Name: staff; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.staff (
    session_id uuid NOT NULL,
    staff_number character varying,
    first_name character varying,
    last_name character varying,
    email character varying,
    department_code character varying,
    staff_type character varying,
    can_invigilate boolean,
    is_instructor boolean,
    max_daily_sessions integer,
    max_consecutive_sessions integer,
    max_concurrent_exams integer,
    max_students_per_invigilator integer,
    user_email character varying
);


ALTER TABLE staging.staff OWNER TO postgres;

--
-- Name: staff_unavailability; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.staff_unavailability (
    session_id uuid NOT NULL,
    staff_number character varying,
    unavailable_date date,
    period_name character varying,
    reason character varying
);


ALTER TABLE staging.staff_unavailability OWNER TO postgres;

--
-- Name: students; Type: TABLE; Schema: staging; Owner: postgres
--

CREATE TABLE staging.students (
    session_id uuid NOT NULL,
    matric_number character varying,
    first_name character varying,
    last_name character varying,
    entry_year integer,
    programme_code character varying,
    user_email character varying
);


ALTER TABLE staging.students OWNER TO postgres;

--
-- Name: buildings uq_staging_buildings_code_session; Type: CONSTRAINT; Schema: staging; Owner: postgres
--

ALTER TABLE ONLY staging.buildings
    ADD CONSTRAINT uq_staging_buildings_code_session UNIQUE (code, session_id);


--
-- Name: courses uq_staging_courses_code_session; Type: CONSTRAINT; Schema: staging; Owner: postgres
--

ALTER TABLE ONLY staging.courses
    ADD CONSTRAINT uq_staging_courses_code_session UNIQUE (code, session_id);


--
-- Name: departments uq_staging_departments_code_session; Type: CONSTRAINT; Schema: staging; Owner: postgres
--

ALTER TABLE ONLY staging.departments
    ADD CONSTRAINT uq_staging_departments_code_session UNIQUE (code, session_id);


--
-- Name: faculties uq_staging_faculties_code_session; Type: CONSTRAINT; Schema: staging; Owner: postgres
--

ALTER TABLE ONLY staging.faculties
    ADD CONSTRAINT uq_staging_faculties_code_session UNIQUE (code, session_id);


--
-- Name: programmes uq_staging_programmes_code_session; Type: CONSTRAINT; Schema: staging; Owner: postgres
--

ALTER TABLE ONLY staging.programmes
    ADD CONSTRAINT uq_staging_programmes_code_session UNIQUE (code, session_id);


--
-- Name: rooms uq_staging_rooms_code_session; Type: CONSTRAINT; Schema: staging; Owner: postgres
--

ALTER TABLE ONLY staging.rooms
    ADD CONSTRAINT uq_staging_rooms_code_session UNIQUE (code, session_id);


--
-- Name: staff uq_staging_staff_number_session; Type: CONSTRAINT; Schema: staging; Owner: postgres
--

ALTER TABLE ONLY staging.staff
    ADD CONSTRAINT uq_staging_staff_number_session UNIQUE (staff_number, session_id);


--
-- Name: students uq_staging_students_matric_number_session; Type: CONSTRAINT; Schema: staging; Owner: postgres
--

ALTER TABLE ONLY staging.students
    ADD CONSTRAINT uq_staging_students_matric_number_session UNIQUE (matric_number, session_id);


--
-- Name: TABLE buildings; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.buildings TO PUBLIC;


--
-- Name: TABLE course_departments; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.course_departments TO PUBLIC;


--
-- Name: TABLE course_faculties; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.course_faculties TO PUBLIC;


--
-- Name: TABLE course_instructors; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.course_instructors TO PUBLIC;


--
-- Name: TABLE course_registrations; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.course_registrations TO PUBLIC;


--
-- Name: TABLE courses; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.courses TO PUBLIC;


--
-- Name: TABLE departments; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.departments TO PUBLIC;


--
-- Name: TABLE faculties; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.faculties TO PUBLIC;


--
-- Name: TABLE programmes; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.programmes TO PUBLIC;


--
-- Name: TABLE rooms; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.rooms TO PUBLIC;


--
-- Name: TABLE staff; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.staff TO PUBLIC;


--
-- Name: TABLE staff_unavailability; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.staff_unavailability TO PUBLIC;


--
-- Name: TABLE students; Type: ACL; Schema: staging; Owner: postgres
--

GRANT ALL ON TABLE staging.students TO PUBLIC;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: staging; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging GRANT ALL ON TABLES TO PUBLIC;


--
-- PostgreSQL database dump complete
--

