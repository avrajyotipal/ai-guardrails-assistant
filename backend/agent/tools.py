"""
LangChain tools — all READ-ONLY SQL queries via psycopg2.
No INSERT / UPDATE / DELETE exists in this file.
"""

import json
from typing import Optional
from langchain_core.tools import tool
from database import get_db, fetchall_as_dicts, fetchone_as_dict


def _json(data) -> str:
    return json.dumps(data, default=str, indent=2)


@tool
def get_students(
    department: Optional[str] = None,
    grade_level: Optional[str] = None,
    min_gpa: Optional[float] = None,
    max_gpa: Optional[float] = None,
    is_active: Optional[bool] = None,
    limit: int = 10,
) -> str:
    """
    Retrieve students from the database with optional filters.

    Args:
        department: Filter by department (partial match). E.g. "Computer Science"
        grade_level: One of Freshman, Sophomore, Junior, Senior, Graduate
        min_gpa: Minimum GPA (0.0-4.0)
        max_gpa: Maximum GPA (0.0-4.0)
        is_active: True=active only, False=inactive only, None=all
        limit: Max records (default 10, max 50)
    """
    limit = min(int(limit), 50)
    conditions, params = [], []

    if department:
        conditions.append("department ILIKE %s")
        params.append(f"%{department}%")
    if grade_level:
        conditions.append("grade_level ILIKE %s")
        params.append(f"%{grade_level}%")
    if min_gpa is not None:
        conditions.append("gpa >= %s")
        params.append(float(min_gpa))
    if max_gpa is not None:
        conditions.append("gpa <= %s")
        params.append(float(max_gpa))
    if is_active is not None:
        conditions.append("is_active = %s")
        params.append(bool(is_active))

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT student_id, first_name, last_name, email, age,
               department, grade_level, gpa, enrollment_date, is_active
        FROM students {where}
        ORDER BY student_id
        LIMIT %s
    """
    params.append(limit)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = fetchall_as_dicts(cur)

    return _json({"count": len(rows), "students": rows})


@tool
def get_student_by_id(student_id: str) -> str:
    """
    Get full details for a specific student by their student ID (e.g. STU00042).
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE student_id = %s", (student_id.upper(),))
        row = fetchone_as_dict(cur)

    if not row:
        return _json({"found": False, "student_id": student_id})
    return _json({"found": True, "student": row})


@tool
def search_students_by_name(name: str, limit: int = 10) -> str:
    """
    Search students by first name or last name (partial, case-insensitive).

    Args:
        name: Name string to search for
        limit: Max results (default 10, max 30)
    """
    limit = min(int(limit), 30)
    sql = """
        SELECT student_id, first_name, last_name, email, department, grade_level, gpa
        FROM students
        WHERE first_name ILIKE %s OR last_name ILIKE %s
        ORDER BY last_name, first_name
        LIMIT %s
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(sql, (f"%{name}%", f"%{name}%", limit))
        rows = fetchall_as_dicts(cur)

    return _json({"count": len(rows), "students": rows})


@tool
def get_courses(
    department: Optional[str] = None,
    semester: Optional[str] = None,
    academic_year: Optional[int] = None,
    min_credits: Optional[int] = None,
    is_active: Optional[bool] = None,
    limit: int = 10,
) -> str:
    """
    Retrieve courses from the database with optional filters.

    Args:
        department: Filter by department (partial match)
        semester: Filter by semester: Fall, Spring, or Summer
        academic_year: Filter by year (e.g. 2024)
        min_credits: Minimum credit hours
        is_active: True/False/None
        limit: Max records (default 10, max 50)
    """
    limit = min(int(limit), 50)
    conditions, params = [], []

    if department:
        conditions.append("department ILIKE %s")
        params.append(f"%{department}%")
    if semester:
        conditions.append("semester ILIKE %s")
        params.append(f"%{semester}%")
    if academic_year:
        conditions.append("academic_year = %s")
        params.append(int(academic_year))
    if min_credits is not None:
        conditions.append("credits >= %s")
        params.append(int(min_credits))
    if is_active is not None:
        conditions.append("is_active = %s")
        params.append(bool(is_active))

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT course_id, course_code, course_name, instructor, department,
               credits, semester, academic_year, fee, max_capacity,
               current_enrollment, is_active
        FROM courses {where}
        ORDER BY course_id
        LIMIT %s
    """
    params.append(limit)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = fetchall_as_dicts(cur)

    return _json({"count": len(rows), "courses": rows})


@tool
def get_course_enrollment(course_id: str) -> str:
    """
    Get enrollment details for a specific course including fill rate and available seats.

    Args:
        course_id: Course ID (e.g. CRS0001) or course code (e.g. CS101)
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM courses WHERE course_id = %s", (course_id.upper(),))
        row = fetchone_as_dict(cur)
        if not row:
            cur.execute("SELECT * FROM courses WHERE course_code ILIKE %s", (course_id,))
            row = fetchone_as_dict(cur)

    if not row:
        return _json({"found": False, "course_id": course_id})

    row["fill_rate_pct"] = round(row["current_enrollment"] / max(row["max_capacity"], 1) * 100, 1)
    row["seats_available"] = row["max_capacity"] - row["current_enrollment"]
    return _json({"found": True, "course": row})


@tool
def get_transactions(
    student_id: Optional[str] = None,
    course_id: Optional[str] = None,
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    Retrieve transactions with optional filters.

    Args:
        student_id: Filter by student ID
        course_id: Filter by course ID
        status: completed, pending, failed, or refunded
        payment_method: credit_card, debit_card, bank_transfer, paypal, scholarship
        limit: Max records (default 10, max 50)
    """
    limit = min(int(limit), 50)
    conditions, params = [], []

    if student_id:
        conditions.append("student_id = %s")
        params.append(student_id.upper())
    if course_id:
        conditions.append("course_id = %s")
        params.append(course_id.upper())
    if status:
        conditions.append("status = %s")
        params.append(status.lower())
    if payment_method:
        conditions.append("payment_method = %s")
        params.append(payment_method.lower())

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT transaction_id, student_id, course_id, transaction_date,
               amount, payment_method, status, description
        FROM transactions {where}
        ORDER BY transaction_date DESC
        LIMIT %s
    """
    params.append(limit)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = fetchall_as_dicts(cur)

    return _json({"count": len(rows), "transactions": rows})


@tool
def get_enrollment_stats() -> str:
    """
    Get overall enrollment statistics: totals, by department, by grade level, average GPA.
    """
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(*) AS total_students,
                COUNT(*) FILTER (WHERE is_active) AS active_students,
                ROUND(AVG(gpa)::numeric, 2) AS average_gpa
            FROM students
        """)
        summary = fetchone_as_dict(cur)

        cur.execute("""
            SELECT department, COUNT(*) AS count
            FROM students
            GROUP BY department
            ORDER BY count DESC
        """)
        by_dept = {r["department"]: r["count"] for r in fetchall_as_dicts(cur)}

        cur.execute("""
            SELECT grade_level, COUNT(*) AS count
            FROM students
            GROUP BY grade_level
            ORDER BY count DESC
        """)
        by_grade = {r["grade_level"]: r["count"] for r in fetchall_as_dicts(cur)}

    return _json({
        "total_students": summary["total_students"],
        "active_students": summary["active_students"],
        "inactive_students": summary["total_students"] - summary["active_students"],
        "average_gpa": float(summary["average_gpa"] or 0),
        "by_department": by_dept,
        "by_grade_level": by_grade,
    })


@tool
def get_revenue_stats() -> str:
    """
    Get financial statistics: total revenue, by payment method, by transaction status.
    """
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(*) AS total_transactions,
                ROUND(SUM(CASE WHEN status='completed' THEN amount ELSE 0 END)::numeric, 2) AS total_revenue,
                ROUND(AVG(amount)::numeric, 2) AS avg_amount
            FROM transactions
        """)
        summary = fetchone_as_dict(cur)

        cur.execute("""
            SELECT status, COUNT(*) AS count
            FROM transactions
            GROUP BY status
            ORDER BY count DESC
        """)
        by_status = {r["status"]: r["count"] for r in fetchall_as_dicts(cur)}

        cur.execute("""
            SELECT payment_method,
                   ROUND(SUM(amount)::numeric, 2) AS revenue
            FROM transactions
            WHERE status = 'completed'
            GROUP BY payment_method
            ORDER BY revenue DESC
        """)
        by_method = {r["payment_method"]: float(r["revenue"]) for r in fetchall_as_dicts(cur)}

    return _json({
        "total_transactions": summary["total_transactions"],
        "total_revenue": float(summary["total_revenue"] or 0),
        "average_transaction_amount": float(summary["avg_amount"] or 0),
        "by_status": by_status,
        "revenue_by_payment_method": by_method,
    })


@tool
def get_department_stats() -> str:
    """
    Get per-department statistics: student count, average GPA, course count.
    """
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.department,
                COUNT(DISTINCT s.student_id) AS student_count,
                ROUND(AVG(s.gpa)::numeric, 2) AS average_gpa,
                (SELECT COUNT(*) FROM courses c WHERE c.department = s.department) AS course_count
            FROM students s
            GROUP BY s.department
            ORDER BY student_count DESC
        """)
        rows = fetchall_as_dicts(cur)

        cur.execute("""
            SELECT ROUND(SUM(t.amount)::numeric, 2) AS total_revenue
            FROM transactions t WHERE t.status = 'completed'
        """)
        rev = fetchone_as_dict(cur)

    stats = {
        r["department"]: {
            "student_count": r["student_count"],
            "average_gpa": float(r["average_gpa"] or 0),
            "course_count": r["course_count"],
        }
        for r in rows
    }

    return _json({
        "total_revenue_all_departments": float(rev["total_revenue"] or 0),
        "departments": stats,
    })


@tool
def get_transaction_summary(student_id: str) -> str:
    """
    Get a transaction summary for a specific student: history, total paid, courses enrolled.

    Args:
        student_id: The student's unique ID (e.g. STU00042)
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT transaction_id, course_id, transaction_date, amount, payment_method, status
            FROM transactions
            WHERE student_id = %s
            ORDER BY transaction_date DESC
        """, (student_id.upper(),))
        txns = fetchall_as_dicts(cur)

    total_paid = sum(t["amount"] for t in txns if t["status"] == "completed")
    courses = list({t["course_id"] for t in txns if t["status"] == "completed"})

    return _json({
        "student_id": student_id,
        "total_transactions": len(txns),
        "total_paid": round(float(total_paid), 2),
        "courses_enrolled": courses,
        "transaction_history": txns,
    })


ALL_TOOLS = [
    get_students,
    get_student_by_id,
    search_students_by_name,
    get_courses,
    get_course_enrollment,
    get_transactions,
    get_enrollment_stats,
    get_revenue_stats,
    get_department_stats,
    get_transaction_summary,
]
