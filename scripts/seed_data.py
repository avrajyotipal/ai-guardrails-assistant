"""
Seed script — creates tables then inserts:
  200 students, 60 courses, ~450 transactions  (710+ data points)

Usage:
    cd "C:/AI Automation/guardrails"
    python scripts/seed_data.py
"""

import os, sys, random, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from datetime import datetime, timedelta
from faker import Faker
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

fake = Faker()
random.seed(42)
Faker.seed(42)


# ── Connection ───────────────────────────────────────────────────────────────

def _parse_url(url: str) -> dict:
    rest = url.split("://", 1)[1]
    at_positions = [i for i, c in enumerate(rest) if c == "@"]
    last_at = at_positions[-1]
    creds   = rest[:last_at]
    host_db = rest[last_at + 1:]
    colon_pos = creds.index(":")
    user     = creds[:colon_pos]
    password = creds[colon_pos + 1:].strip("[]")
    host_port, dbname = host_db.rsplit("/", 1)
    host, port = host_port.rsplit(":", 1)
    return dict(host=host, port=int(port), dbname=dbname, user=user, password=password, sslmode="require")


def get_conn():
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL", "")
    if not url:
        print("ERROR: Set SUPABASE_URL or DATABASE_URL in .env")
        sys.exit(1)
    return psycopg2.connect(**_parse_url(url))


# ── Schema ───────────────────────────────────────────────────────────────────

CREATE_SQL = """
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

CREATE TABLE IF NOT EXISTS monitoring_logs (
    id                      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id              VARCHAR(100)  NOT NULL,
    timestamp               TIMESTAMPTZ   DEFAULT NOW(),
    user_input              TEXT,
    policy_passed           BOOLEAN,
    policy_block_reason     TEXT,
    input_passed            BOOLEAN,
    input_block_reason      TEXT,
    input_sanitized         TEXT,
    injection_detected      BOOLEAN       DEFAULT FALSE,
    instruction_passed      BOOLEAN,
    instruction_block_reason TEXT,
    jailbreak_detected      BOOLEAN       DEFAULT FALSE,
    tools_called            JSONB         DEFAULT '[]',
    tools_blocked           JSONB         DEFAULT '[]',
    tool_execution_details  JSONB         DEFAULT '[]',
    llm_raw_output          TEXT,
    output_passed           BOOLEAN,
    output_block_reason     TEXT,
    hallucination_detected  BOOLEAN       DEFAULT FALSE,
    hallucination_details   TEXT,
    pii_detected            BOOLEAN       DEFAULT FALSE,
    final_response          TEXT,
    total_blocked           BOOLEAN       DEFAULT FALSE,
    processing_time_ms      INTEGER,
    metadata                JSONB         DEFAULT '{}',
    created_at              TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_students_department   ON students(department);
CREATE INDEX IF NOT EXISTS idx_students_grade_level  ON students(grade_level);
CREATE INDEX IF NOT EXISTS idx_courses_department    ON courses(department);
CREATE INDEX IF NOT EXISTS idx_transactions_student  ON transactions(student_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status   ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_session    ON monitoring_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_timestamp  ON monitoring_logs(timestamp);
"""


# ── Data generators ──────────────────────────────────────────────────────────

DEPARTMENTS = [
    "Computer Science", "Mathematics", "Physics", "Chemistry",
    "Biology", "Engineering", "Business Administration", "Economics",
    "Psychology", "Art & Design"
]
GRADE_LEVELS = ["Freshman", "Sophomore", "Junior", "Senior", "Graduate"]
PAYMENT_METHODS = (
    ["credit_card"] * 3 + ["debit_card"] * 2 +
    ["bank_transfer"] * 2 + ["paypal"] + ["scholarship"] * 2
)
STATUSES = (
    ["completed"] * 7 + ["pending"] * 2 + ["refunded"] + ["failed"]
)
SEMESTERS = ["Fall", "Spring", "Summer"]
YEARS = [2023, 2024, 2025]

COURSES_BY_DEPT = {
    "Computer Science": [
        ("Introduction to Programming",    "CS101", 3, 299.99, "Dr. Alan Turing"),
        ("Data Structures & Algorithms",   "CS201", 4, 349.99, "Dr. Grace Hopper"),
        ("Database Management Systems",    "CS301", 3, 329.99, "Dr. Edgar Codd"),
        ("Machine Learning",               "CS401", 4, 399.99, "Dr. Andrew Ng"),
        ("Web Development",                "CS302", 3, 279.99, "Prof. Tim Lee"),
        ("Artificial Intelligence",        "CS402", 4, 419.99, "Dr. John McCarthy"),
    ],
    "Mathematics": [
        ("Calculus I",                     "MATH101", 4, 249.99, "Dr. Isaac Newton"),
        ("Linear Algebra",                 "MATH201", 3, 249.99, "Prof. Carl Gauss"),
        ("Statistics & Probability",       "MATH202", 3, 269.99, "Dr. Karl Pearson"),
        ("Discrete Mathematics",           "MATH203", 3, 249.99, "Prof. Euler Bernhard"),
        ("Numerical Analysis",             "MATH301", 3, 269.99, "Dr. James Hardy"),
        ("Differential Equations",         "MATH302", 4, 289.99, "Prof. Anna Sokolova"),
    ],
    "Physics": [
        ("Classical Mechanics",            "PHY101", 4, 279.99, "Dr. Richard Feynman"),
        ("Electromagnetism",               "PHY201", 4, 299.99, "Dr. James Maxwell"),
        ("Quantum Physics",                "PHY301", 4, 349.99, "Dr. Niels Bohr"),
        ("Thermodynamics",                 "PHY202", 3, 279.99, "Prof. Carnot Sadi"),
        ("Modern Physics",                 "PHY302", 3, 319.99, "Dr. Albert Einstein"),
        ("Optics & Waves",                 "PHY203", 3, 259.99, "Prof. Thomas Young"),
    ],
    "Chemistry": [
        ("General Chemistry I",            "CHEM101", 4, 289.99, "Dr. Marie Curie"),
        ("Organic Chemistry",              "CHEM201", 4, 329.99, "Dr. August Kekule"),
        ("Analytical Chemistry",           "CHEM202", 3, 309.99, "Prof. Justus Liebig"),
        ("Physical Chemistry",             "CHEM301", 4, 339.99, "Dr. Linus Pauling"),
        ("Biochemistry",                   "CHEM302", 3, 319.99, "Prof. Frederick Sanger"),
        ("Inorganic Chemistry",            "CHEM203", 3, 299.99, "Dr. Alfred Werner"),
    ],
    "Biology": [
        ("Cell Biology",                   "BIO101", 3, 269.99, "Dr. Robert Hooke"),
        ("Genetics",                       "BIO201", 4, 319.99, "Dr. Gregor Mendel"),
        ("Ecology",                        "BIO202", 3, 279.99, "Prof. Ernst Haeckel"),
        ("Microbiology",                   "BIO301", 4, 329.99, "Dr. Louis Pasteur"),
        ("Human Anatomy",                  "BIO102", 3, 299.99, "Prof. Andreas Vesalius"),
        ("Evolutionary Biology",           "BIO302", 3, 309.99, "Dr. Charles Darwin"),
    ],
    "Engineering": [
        ("Engineering Mechanics",          "ENG101", 4, 319.99, "Dr. Stephen Timoshenko"),
        ("Circuit Analysis",               "ENG201", 4, 349.99, "Prof. Georg Ohm"),
        ("Thermodynamics for Engineers",   "ENG202", 3, 309.99, "Dr. William Rankine"),
        ("Materials Science",              "ENG301", 3, 329.99, "Prof. William Callister"),
        ("Control Systems",                "ENG302", 4, 369.99, "Dr. Norbert Wiener"),
        ("Signal Processing",              "ENG303", 4, 369.99, "Prof. Claude Shannon"),
    ],
    "Business Administration": [
        ("Principles of Management",       "BUS101", 3, 259.99, "Prof. Peter Drucker"),
        ("Marketing Management",           "BUS201", 3, 269.99, "Dr. Philip Kotler"),
        ("Financial Accounting",           "BUS202", 4, 299.99, "Prof. William Cooper"),
        ("Operations Management",          "BUS301", 3, 279.99, "Dr. Frederick Taylor"),
        ("Strategic Management",           "BUS401", 4, 329.99, "Prof. Michael Porter"),
        ("Human Resource Management",      "BUS302", 3, 259.99, "Dr. Gary Dessler"),
    ],
    "Economics": [
        ("Microeconomics",                 "ECON101", 3, 249.99, "Dr. Alfred Marshall"),
        ("Macroeconomics",                 "ECON102", 3, 249.99, "Prof. John Keynes"),
        ("Econometrics",                   "ECON201", 4, 299.99, "Dr. Jan Tinbergen"),
        ("International Trade",            "ECON202", 3, 269.99, "Prof. David Ricardo"),
        ("Development Economics",          "ECON301", 3, 279.99, "Dr. Amartya Sen"),
        ("Behavioral Economics",           "ECON302", 3, 279.99, "Prof. Richard Thaler"),
    ],
    "Psychology": [
        ("Introduction to Psychology",     "PSY101", 3, 239.99, "Dr. William James"),
        ("Cognitive Psychology",           "PSY201", 3, 259.99, "Prof. Jean Piaget"),
        ("Social Psychology",              "PSY202", 3, 249.99, "Dr. Solomon Asch"),
        ("Abnormal Psychology",            "PSY301", 3, 269.99, "Prof. Aaron Beck"),
        ("Research Methods",               "PSY203", 4, 279.99, "Dr. Stanley Milgram"),
        ("Developmental Psychology",       "PSY302", 3, 259.99, "Prof. Erik Erikson"),
    ],
    "Art & Design": [
        ("Drawing Fundamentals",           "ART101", 3, 229.99, "Prof. Leonardo Da Vinci"),
        ("Digital Design",                 "ART201", 3, 259.99, "Dr. Paul Rand"),
        ("Photography",                    "ART202", 3, 249.99, "Prof. Ansel Adams"),
        ("Graphic Design",                 "ART301", 3, 269.99, "Dr. Jan Tschichold"),
        ("Art History",                    "ART102", 3, 219.99, "Prof. Ernst Gombrich"),
        ("3D Modeling",                    "ART302", 4, 299.99, "Dr. Ivan Sutherland"),
    ],
}


def gen_students(n=200):
    rows, emails = [], set()
    for i in range(1, n + 1):
        dept = random.choice(DEPARTMENTS)
        first, last = fake.first_name(), fake.last_name()
        base = f"{first.lower()}.{last.lower()}"
        email = f"{base}{random.randint(1,9999)}@university.edu"
        while email in emails:
            email = f"{base}{random.randint(1,99999)}@university.edu"
        emails.add(email)
        days_ago = random.randint(30, 1460)
        rows.append((
            f"STU{str(i).zfill(5)}", first, last, email,
            random.randint(18, 35), dept, random.choice(GRADE_LEVELS),
            round(random.uniform(1.8, 4.0), 2),
            (datetime.now() - timedelta(days=days_ago)).date().isoformat(),
            fake.numerify("###-###-####"),
            fake.address().replace("\n", ", ")[:200],
            random.choices([True, False], weights=[85, 15])[0],
        ))
    return rows


def gen_courses():
    rows, cid = [], 1
    for dept, clist in COURSES_BY_DEPT.items():
        for (name, code, credits, fee, instructor) in clist:
            max_cap = random.randint(25, 60)
            rows.append((
                f"CRS{str(cid).zfill(4)}", code, name, instructor, dept,
                credits,
                f"Comprehensive course covering {name.lower()} with hands-on projects.",
                max_cap, random.randint(10, max_cap),
                random.choice(SEMESTERS), random.choice(YEARS),
                fee, random.choices([True, False], weights=[90, 10])[0],
            ))
            cid += 1
    return rows


def gen_transactions(student_ids, course_items, target=450):
    rows, tid = [], 1
    for sid in student_ids:
        num = random.randint(1, 4)
        selected = random.sample(course_items, min(num, len(course_items)))
        for cid, fee in selected:
            days_ago = random.randint(1, 730)
            tx_date = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
            status = random.choice(STATUSES)
            amount = fee if status != "refunded" else -fee
            rows.append((
                f"TXN{str(tid).zfill(6)}", sid, cid,
                tx_date.isoformat(), float(amount),
                random.choice(PAYMENT_METHODS), status,
                f"Course enrollment payment for {cid}",
            ))
            tid += 1
    while len(rows) < target:
        sid = random.choice(student_ids)
        cid, fee = random.choice(course_items)
        days_ago = random.randint(1, 365)
        tx_date = datetime.now() - timedelta(days=days_ago)
        status = random.choice(STATUSES)
        amount = fee if status != "refunded" else -fee
        rows.append((
            f"TXN{str(tid).zfill(6)}", sid, cid,
            tx_date.isoformat(), float(amount),
            random.choice(PAYMENT_METHODS), status,
            f"Supplemental enrollment for {cid}",
        ))
        tid += 1
    return rows


# ── Insert helpers ────────────────────────────────────────────────────────────

def batch_insert(conn, sql, rows, label, batch=50):
    cur = conn.cursor()
    inserted = 0
    for i in range(0, len(rows), batch):
        cur.executemany(sql, rows[i: i + batch])
        conn.commit()
        inserted += len(rows[i: i + batch])
        print(f"  {label}: {inserted}/{len(rows)}")
    print(f"  {label}: DONE")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Connecting to Supabase PostgreSQL...")
    conn = get_conn()
    print("Connected!")

    print("\nCreating tables...")
    cur = conn.cursor()
    cur.execute(CREATE_SQL)
    conn.commit()
    print("Tables created (or already existed).")

    # Check for existing data
    cur.execute("SELECT COUNT(*) FROM students")
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"\nFound {existing} existing students. Skipping seed to avoid duplicates.")
        print("To re-seed, truncate the tables first.")
        conn.close()
        return

    print("\nGenerating data...")
    students = gen_students(200)
    courses  = gen_courses()
    print(f"  Students    : {len(students)}")
    print(f"  Courses     : {len(courses)}")

    print("\nInserting students...")
    batch_insert(conn, """
        INSERT INTO students
          (student_id, first_name, last_name, email, age, department,
           grade_level, gpa, enrollment_date, phone, address, is_active)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (student_id) DO NOTHING
    """, students, "students")

    print("\nInserting courses...")
    batch_insert(conn, """
        INSERT INTO courses
          (course_id, course_code, course_name, instructor, department,
           credits, description, max_capacity, current_enrollment,
           semester, academic_year, fee, is_active)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (course_id) DO NOTHING
    """, courses, "courses")

    student_ids  = [s[0] for s in students]
    course_items = [(c[0], c[11]) for c in courses]   # (course_id, fee)

    transactions = gen_transactions(student_ids, course_items, target=450)
    print(f"\nGenerating {len(transactions)} transactions...")
    batch_insert(conn, """
        INSERT INTO transactions
          (transaction_id, student_id, course_id, transaction_date,
           amount, payment_method, status, description)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (transaction_id) DO NOTHING
    """, transactions, "transactions")

    # Summary
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students")
    ns = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM courses")
    nc = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM transactions")
    nt = cur.fetchone()[0]
    conn.close()

    print(f"\nSeed complete:")
    print(f"  Students    : {ns}")
    print(f"  Courses     : {nc}")
    print(f"  Transactions: {nt}")
    print(f"  TOTAL       : {ns + nc + nt} data points")


if __name__ == "__main__":
    main()
