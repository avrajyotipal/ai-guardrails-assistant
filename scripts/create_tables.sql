-- ============================================================
-- AI Database Assistant - Schema
-- Run this in your Supabase SQL Editor before seeding data
-- ============================================================

-- STUDENTS TABLE
CREATE TABLE IF NOT EXISTS students (
    id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id       VARCHAR(20)  UNIQUE NOT NULL,
    first_name       VARCHAR(100) NOT NULL,
    last_name        VARCHAR(100) NOT NULL,
    email            VARCHAR(255) UNIQUE NOT NULL,
    age              INTEGER      CHECK (age >= 16 AND age <= 60),
    department       VARCHAR(100) NOT NULL,
    grade_level      VARCHAR(20)  NOT NULL,
    gpa              DECIMAL(3,2) CHECK (gpa >= 0.0 AND gpa <= 4.0),
    enrollment_date  DATE         NOT NULL,
    phone            VARCHAR(25),
    address          TEXT,
    is_active        BOOLEAN      DEFAULT TRUE,
    created_at       TIMESTAMPTZ  DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  DEFAULT NOW()
);

-- COURSES TABLE
CREATE TABLE IF NOT EXISTS courses (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    course_id           VARCHAR(20)   UNIQUE NOT NULL,
    course_code         VARCHAR(20)   UNIQUE NOT NULL,
    course_name         VARCHAR(200)  NOT NULL,
    instructor          VARCHAR(100)  NOT NULL,
    department          VARCHAR(100)  NOT NULL,
    credits             INTEGER       CHECK (credits >= 1 AND credits <= 6),
    description         TEXT,
    max_capacity        INTEGER       DEFAULT 30,
    current_enrollment  INTEGER       DEFAULT 0,
    semester            VARCHAR(20)   NOT NULL,
    academic_year       INTEGER       NOT NULL,
    fee                 DECIMAL(10,2) NOT NULL,
    is_active           BOOLEAN       DEFAULT TRUE,
    created_at          TIMESTAMPTZ   DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   DEFAULT NOW()
);

-- TRANSACTIONS TABLE
CREATE TABLE IF NOT EXISTS transactions (
    id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    transaction_id   VARCHAR(30)   UNIQUE NOT NULL,
    student_id       VARCHAR(20)   REFERENCES students(student_id),
    course_id        VARCHAR(20)   REFERENCES courses(course_id),
    transaction_date TIMESTAMPTZ   NOT NULL,
    amount           DECIMAL(10,2) NOT NULL,
    payment_method   VARCHAR(50)   NOT NULL,
    status           VARCHAR(20)   NOT NULL CHECK (status IN ('completed','pending','failed','refunded')),
    description      TEXT,
    created_at       TIMESTAMPTZ   DEFAULT NOW()
);

-- MONITORING LOGS TABLE
CREATE TABLE IF NOT EXISTS monitoring_logs (
    id                      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id              VARCHAR(100)  NOT NULL,
    timestamp               TIMESTAMPTZ   DEFAULT NOW(),
    user_input              TEXT,

    -- Policy layer
    policy_passed           BOOLEAN,
    policy_block_reason     TEXT,

    -- Input layer
    input_passed            BOOLEAN,
    input_block_reason      TEXT,
    input_sanitized         TEXT,
    injection_detected      BOOLEAN       DEFAULT FALSE,

    -- Instruction layer
    instruction_passed      BOOLEAN,
    instruction_block_reason TEXT,
    jailbreak_detected      BOOLEAN       DEFAULT FALSE,

    -- Execution layer
    tools_called            JSONB         DEFAULT '[]',
    tools_blocked           JSONB         DEFAULT '[]',
    tool_execution_details  JSONB         DEFAULT '[]',

    -- Output layer
    llm_raw_output          TEXT,
    output_passed           BOOLEAN,
    output_block_reason     TEXT,
    hallucination_detected  BOOLEAN       DEFAULT FALSE,
    hallucination_details   TEXT,
    pii_detected            BOOLEAN       DEFAULT FALSE,

    -- Final
    final_response          TEXT,
    total_blocked           BOOLEAN       DEFAULT FALSE,
    processing_time_ms      INTEGER,
    metadata                JSONB         DEFAULT '{}',

    created_at              TIMESTAMPTZ   DEFAULT NOW()
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_students_department   ON students(department);
CREATE INDEX IF NOT EXISTS idx_students_grade_level  ON students(grade_level);
CREATE INDEX IF NOT EXISTS idx_students_gpa          ON students(gpa);
CREATE INDEX IF NOT EXISTS idx_courses_department    ON courses(department);
CREATE INDEX IF NOT EXISTS idx_courses_semester      ON courses(semester);
CREATE INDEX IF NOT EXISTS idx_transactions_student  ON transactions(student_id);
CREATE INDEX IF NOT EXISTS idx_transactions_course   ON transactions(course_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status   ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_session    ON monitoring_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_timestamp  ON monitoring_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_monitoring_blocked    ON monitoring_logs(total_blocked);
