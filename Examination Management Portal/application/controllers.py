
from datetime import datetime, date, time
from functools import wraps

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session
)

from sqlalchemy import or_

from application.database import db
from application.models import (
    User,
    Course,
    Examination,
    Rubric,
    ExaminationSlot,
    Booking,
    Evaluation,
    EvaluationDetail
)


def register_routes(app):

    # ==============================
    # COMMON FUNCTIONS
    # ==============================

    def role_required(required_role):
        def decorator(function):
            @wraps(function)
            def wrapper(*args, **kwargs):

                if "user_id" not in session:
                    return redirect(url_for("login"))

                if session.get("role") != required_role:
                    return redirect(url_for("login"))

                return function(*args, **kwargs)

            return wrapper
        return decorator

    def parse_datetime(value):
        return datetime.fromisoformat(value)

    def parse_date(value):
        return date.fromisoformat(value)

    def parse_time(value):
        return time.fromisoformat(value)

    # ==============================
    # HOME PAGE
    # ==============================

    @app.route("/")
    def index():
        return render_template("home.html")

    # ==============================
    # LOGIN
    # ==============================

    @app.route("/login", methods=["GET", "POST"])
    def login():

        if request.method == "POST":

            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")

            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):

                if user.status != "Active":
                    return render_template(
                        "login.html",
                        error="Your account is not active. Please contact the administrator."
                    )

                session.clear()
                session["user_id"] = user.id
                session["role"] = user.role

                if user.role == "admin":
                    return redirect(url_for("admin_dashboard"))

                elif user.role == "examiner":
                    return redirect(url_for("examiner_dashboard"))

                elif user.role == "student":
                    return redirect(url_for("student_dashboard"))

            return render_template(
                "login.html",
                error="Invalid email or password"
            )

        return render_template("login.html")

    # ==============================
    # LOGOUT
    # ==============================

    @app.route("/logout")
    def logout():

        session.clear()

        return redirect(url_for("login"))

    # ==============================
    # EXAMINER REGISTRATION
    # ==============================
    @app.route("/examiner_register", methods=["GET", "POST"])
    def examiner_register():

        if request.method == "POST":

            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            department = request.form.get("department", "").strip()

            if not all([full_name, username, email, password, department]):
                return render_template(
                    "examiner_register.html",
                    error="Please fill in all required fields."
                )

            existing_user = User.query.filter(
                or_(
                    User.username == username,
                    User.email == email
                )
            ).first()

            if existing_user:
                return render_template(
                    "examiner_register.html",
                    error="Username or email already exists."
                )

            examiner = User(
                full_name=full_name,
                username=username,
                email=email,
                role="examiner",
                department=department,
                status="Pending"
            )

            examiner.set_password(password)

            db.session.add(examiner)
            db.session.commit()

            return redirect(url_for("login"))

        return render_template("examiner_register.html")

    # ==============================
    # STUDENT REGISTRATION
    # ==============================

    @app.route("/student_register", methods=["GET", "POST"])
    def student_register():

        if request.method == "POST":

            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            department = request.form.get("department", "").strip()

            if not all([full_name, username, email, password, department]):
                return render_template(
                    "student_register.html",
                    error="Please fill in all required fields."
                )

            existing_user = User.query.filter(
                or_(
                    User.username == username,
                    User.email == email
                )
            ).first()

            if existing_user:
                return render_template(
                    "student_register.html",
                    error="Username or email already exists."
                )

            student = User(
                full_name=full_name,
                username=username,
                email=email,
                role="student",
                department=department,
                status="Active"
            )

            student.set_password(password)

            db.session.add(student)
            db.session.commit()

            return redirect(url_for("login"))

        return render_template("student_register.html")
    # ==============================
    # ADMIN DASHBOARD
    # ==============================

    @app.route("/admin_dashboard")
    @role_required("admin")
    def admin_dashboard():

        search = request.args.get("search", "").strip()

        examiner_query = User.query.filter_by(role="examiner")

        if search:
            examiner_query = examiner_query.filter(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.department.ilike(f"%{search}%")
                )
            )

        examiners = examiner_query.all()

        total_courses = Course.query.count()
        total_examinations = Examination.query.count()
        total_bookings = Booking.query.filter_by(status="Booked").count()

        return render_template(
            "admin_dashboard.html",
            examiners=examiners,
            total_courses=total_courses,
            total_examinations=total_examinations,
            total_bookings=total_bookings
        )

    # ==============================
    # EXAMINER APPROVAL
    # ==============================

    @app.route(
        "/update_examiner_status/<int:examiner_id>/<string:new_status>",
        methods=["POST"]
    )
    @role_required("admin")
    def update_examiner_status(examiner_id, new_status):

        if new_status not in ["Active", "Blocked"]:
            return redirect(url_for("admin_dashboard"))

        examiner = User.query.filter_by(
            id=examiner_id,
            role="examiner"
        ).first_or_404()

        examiner.status = new_status

        db.session.commit()

        return redirect(url_for("admin_dashboard"))

    # ==============================
    # COURSE MANAGEMENT
    # ==============================

    @app.route("/manage_courses", methods=["GET", "POST"])
    @role_required("admin")
    def manage_courses():

        if request.method == "POST":

            code = request.form.get("code", "").strip()
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()

            if not code or not name:
                return redirect(url_for("manage_courses"))

            existing_course = Course.query.filter_by(
                code=code
            ).first()

            if existing_course:
                return redirect(url_for("manage_courses"))

            course = Course(
                code=code,
                name=name,
                description=description,
                status="Active"
            )

            db.session.add(course)
            db.session.commit()

            return redirect(url_for("manage_courses"))

        courses = Course.query.order_by(Course.id.desc()).all()

        return render_template(
            "admin_courses.html",
            courses=courses
        )


    
    # ==============================
    # EXAMINATION MANAGEMENT
    # ==============================

    @app.route("/manage_examinations", methods=["GET", "POST"])
    @role_required("admin")
    def manage_examinations():

        if request.method == "POST":

            course_id = request.form.get("course_id")
            name = request.form.get("name", "").strip()
            exam_type = request.form.get("exam_type", "").strip()
            duration = request.form.get("duration_minutes")
            maximum_marks = request.form.get("maximum_marks")
            student_capacity = request.form.get("student_capacity")

            try:
                slot_start = parse_datetime(
                    request.form.get("slot_creation_start")
                )

                slot_end = parse_datetime(
                    request.form.get("slot_creation_end")
                )

                booking_start = parse_datetime(
                    request.form.get("booking_start")
                )

                booking_end = parse_datetime(
                    request.form.get("booking_end")
                )

                course_id = int(course_id)
                duration = int(duration)
                maximum_marks = int(maximum_marks)
                student_capacity = int(student_capacity)

            except (ValueError, TypeError):
                return redirect(url_for("manage_examinations"))

            course = db.session.get(Course, course_id)

            if (
                course is None
                or not name
                or not exam_type
                or duration <= 0
                or maximum_marks <= 0
                or student_capacity <= 0
                or slot_start is None
                or slot_end is None
                or booking_start is None
                or booking_end is None
                or slot_start >= slot_end
                or booking_start >= booking_end
            ):
                return redirect(url_for("manage_examinations"))

            # Get evaluation criteria from the form
            criterion_names = request.form.getlist("criterion_name")
            rubric_marks = request.form.getlist("rubric_maximum_marks")
            rubric_descriptions = request.form.getlist("rubric_description")

            # Validate rubric details
            if not criterion_names:
                return redirect(url_for("manage_examinations"))

            if not (
                len(criterion_names)
                == len(rubric_marks)
                == len(rubric_descriptions)
            ):
                return redirect(url_for("manage_examinations"))

            total_rubric_marks = 0
            rubric_details = []

            try:
                for criterion, marks, description in zip(
                    criterion_names,
                    rubric_marks,
                    rubric_descriptions
                ):

                    criterion = criterion.strip()
                    marks = float(marks)
                    description = description.strip()

                    if not criterion or marks <= 0:
                        return redirect(url_for("manage_examinations"))

                    total_rubric_marks += marks

                    rubric_details.append(
                        (criterion, marks, description)
                    )

            except (ValueError, TypeError):
                return redirect(url_for("manage_examinations"))

            if total_rubric_marks > maximum_marks:
                return redirect(url_for("manage_examinations"))

            # Create examination
            examination = Examination(
                course_id=course_id,
                name=name,
                exam_type=exam_type,
                duration_minutes=duration,
                maximum_marks=maximum_marks,
                student_capacity=student_capacity,
                slot_creation_start=slot_start,
                slot_creation_end=slot_end,
                booking_start=booking_start,
                booking_end=booking_end,
                status="Published"
            )

            db.session.add(examination)
            db.session.flush()

            # Save evaluation criteria
            for criterion, marks, description in rubric_details:

                rubric = Rubric(
                    examination_id=examination.id,
                    criterion_name=criterion,
                    maximum_marks=marks,
                    description=description
                )

                db.session.add(rubric)

            db.session.commit()

            return redirect(url_for("manage_examinations"))

        courses = Course.query.all()

        examinations = Examination.query.order_by(
            Examination.id.desc()
        ).all()

        return render_template(
            "admin_examinations.html",
            courses=courses,
            examinations=examinations
        )

    # ==============================
    # EXAM SLOT MANAGEMENT
    # ==============================

    @app.route("/manage_slots", methods=["GET", "POST"])
    @role_required("admin")
    def manage_slots():

        if request.method == "POST":

            try:
                examination_id = int(
                    request.form.get("examination_id")
                )

                examiner_id = int(
                    request.form.get("examiner_id")
                )

                exam_date = parse_date(
                    request.form.get("exam_date")
                )

                start_time = parse_time(
                    request.form.get("start_time")
                )

                end_time = parse_time(
                    request.form.get("end_time")
                )

                capacity = int(
                    request.form.get("capacity")
                )

            except (ValueError, TypeError):
                return redirect(url_for("manage_slots"))

            examination = db.session.get(
                Examination,
                examination_id
            )

            examiner = User.query.filter_by(
                id=examiner_id,
                role="examiner",
                status="Active"
            ).first()

            if (
                examination is None
                or examiner is None
                or start_time >= end_time
                or capacity <= 0
            ):
                return redirect(url_for("manage_slots"))

            now = datetime.now()

            if not (
                examination.slot_creation_start
                <= now
                <= examination.slot_creation_end
            ):
                return redirect(url_for("manage_slots"))

            slot = ExaminationSlot(
                examination_id=examination_id,
                examiner_id=examiner_id,
                exam_date=exam_date,
                start_time=start_time,
                end_time=end_time,
                capacity=capacity,
                status="Available"
            )

            db.session.add(slot)
            db.session.commit()

            return redirect(url_for("manage_slots"))

        search = request.args.get("search", "").strip()

        slot_query = ExaminationSlot.query.join(
            Examination
        )

        if search:
            slot_query = slot_query.filter(
                Examination.name.ilike(f"%{search}%")
            )

        slots = slot_query.order_by(
            ExaminationSlot.exam_date,
            ExaminationSlot.start_time
        ).all()

        total_slots = ExaminationSlot.query.count()

        available_seats = sum(
            slot.available_seats for slot in slots
        )

        booked_seats = sum(
            slot.booked_count for slot in slots
        )

        return render_template(
            "admin_exam_slot.html",
            slots=slots,
            total_slots=total_slots,
            available_seats=available_seats,
            booked_seats=booked_seats
        )


    
    
    # ==============================
    # ADMIN EDITS EXAMINATION
    # ==============================

    @app.route(
        "/edit_examination/<int:examination_id>",
        methods=["GET", "POST"]
    )
    @role_required("admin")
    def edit_examination(examination_id):

        examination = db.session.get(
            Examination,
            examination_id
        )

        if examination is None:
            return redirect(url_for("manage_examinations"))

        # Check whether any student has ever booked this examination
        existing_booking = Booking.query.join(
            ExaminationSlot,
            Booking.slot_id == ExaminationSlot.id
        ).filter(
            ExaminationSlot.examination_id == examination_id
        ).first()

        if existing_booking:
            return redirect(url_for("manage_examinations"))

        if request.method == "POST":

            course_id = request.form.get("course_id")
            name = request.form.get("name", "").strip()
            exam_type = request.form.get("exam_type", "").strip()

            duration = request.form.get("duration_minutes")
            maximum_marks = request.form.get("maximum_marks")
            student_capacity = request.form.get("student_capacity")

            try:
                course_id = int(course_id)
                duration = int(duration)
                maximum_marks = int(maximum_marks)
                student_capacity = int(student_capacity)

                slot_start = parse_datetime(
                    request.form.get("slot_creation_start")
                )

                slot_end = parse_datetime(
                    request.form.get("slot_creation_end")
                )

                booking_start = parse_datetime(
                    request.form.get("booking_start")
                )

                booking_end = parse_datetime(
                    request.form.get("booking_end")
                )

            except (ValueError, TypeError):
                return redirect(
                    url_for(
                        "edit_examination",
                        examination_id=examination_id
                    )
                )

            course = db.session.get(Course, course_id)

            if (
                course is None
                or not name
                or exam_type not in ["Theory", "Practical", "Viva", "Project"]
                or duration <= 0
                or maximum_marks <= 0
                or student_capacity <= 0
                or slot_start is None
                or slot_end is None
                or booking_start is None
                or booking_end is None
                or slot_start >= slot_end
                or booking_start >= booking_end
            ):
                return redirect(
                    url_for(
                        "edit_examination",
                        examination_id=examination_id
                    )
                )

            # Get updated evaluation criteria
            criterion_names = request.form.getlist("criterion_name")
            rubric_marks = request.form.getlist("rubric_maximum_marks")
            rubric_descriptions = request.form.getlist("rubric_description")

            if not (
                len(criterion_names)
                == len(rubric_marks)
                == len(rubric_descriptions)
                == len(examination.rubrics)
            ):
                return redirect(
                    url_for(
                        "edit_examination",
                        examination_id=examination_id
                    )
                )

            rubric_details = []
            total_rubric_marks = 0

            try:
                for criterion, marks, description in zip(
                    criterion_names,
                    rubric_marks,
                    rubric_descriptions
                ):

                    criterion = criterion.strip()
                    marks = float(marks)
                    description = description.strip()

                    if not criterion or marks <= 0:
                        return redirect(
                            url_for(
                                "edit_examination",
                                examination_id=examination_id
                            )
                        )

                    total_rubric_marks += marks

                    rubric_details.append(
                        (criterion, marks, description)
                    )

            except (ValueError, TypeError):
                return redirect(
                    url_for(
                        "edit_examination",
                        examination_id=examination_id
                    )
                )

            if total_rubric_marks > maximum_marks:
                return redirect(
                    url_for(
                        "edit_examination",
                        examination_id=examination_id
                    )
                )

            # Update examination details
            examination.course_id = course_id
            examination.name = name
            examination.exam_type = exam_type
            examination.duration_minutes = duration
            examination.maximum_marks = maximum_marks
            examination.student_capacity = student_capacity

            examination.slot_creation_start = slot_start
            examination.slot_creation_end = slot_end
            examination.booking_start = booking_start
            examination.booking_end = booking_end

            # Update existing evaluation criteria
            for rubric, details in zip(
                examination.rubrics,
                rubric_details
            ):

                rubric.criterion_name = details[0]
                rubric.maximum_marks = details[1]
                rubric.description = details[2]

            db.session.commit()

            return redirect(url_for("manage_examinations"))

        courses = Course.query.all()

        return render_template(
            "admin_edit_examination.html",
            examination=examination,
            courses=courses
        )


    # ==============================
    # BOOKING MANAGEMENT
    # ==============================

    @app.route("/manage_bookings")
    @role_required("admin")
    def manage_bookings():

        search = request.args.get("search", "").strip()

        booking_query = Booking.query.join(
            User,
            Booking.student_id == User.id
        ).join(
            ExaminationSlot
        ).join(
            Examination
        )

        if search:
            booking_query = booking_query.filter(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    Examination.name.ilike(f"%{search}%")
                )
            )

        bookings = booking_query.order_by(
            Booking.booked_at.desc()
        ).all()

        total_bookings = Booking.query.count()

        active_bookings = Booking.query.filter_by(
            status="Booked"
        ).count()

        cancelled_bookings = Booking.query.filter_by(
            status="Cancelled"
        ).count()

        return render_template(
            "admin_booking.html",
            bookings=bookings,
            total_bookings=total_bookings,
            active_bookings=active_bookings,
            cancelled_bookings=cancelled_bookings
        )

    # ==============================
    # RESULT MANAGEMENT
    # ==============================

    @app.route("/manage_results")
    @role_required("admin")
    def manage_results():

        search = request.args.get("search", "").strip()

        # Retrieve evaluation records with related information
        evaluation_query = Evaluation.query.join(
            Evaluation.booking
        ).join(
            Booking.student
        ).join(
            Booking.slot
        ).join(
            ExaminationSlot.examination
        )

        # Search by student name or examination name
        if search:
            evaluation_query = evaluation_query.filter(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    Examination.name.ilike(f"%{search}%")
                )
            )

        # Retrieve all matching evaluations
        evaluations = evaluation_query.order_by(
            Evaluation.submitted_at.desc()
        ).all()

        # Count evaluations
        total_evaluations = Evaluation.query.count()

        published_results = Evaluation.query.filter_by(
            published=True
        ).count()

        pending_results = Evaluation.query.filter_by(
            published=False
        ).count()

        return render_template(
            "admin_results.html",
            evaluations=evaluations,
            total_evaluations=total_evaluations,
            published_results=published_results,
            pending_results=pending_results,
            search=search
        )

    
    # ==============================
    # ADMIN PUBLISHES RESULTS
    # ==============================

    @app.route(
        "/publish_result/<int:evaluation_id>",
        methods=["POST"]
    )
    @role_required("admin")
    def publish_result(evaluation_id):

        evaluation = db.session.get(
            Evaluation,
            evaluation_id
        )

        if evaluation is None:
            return redirect(url_for("manage_results"))

        evaluation.published = True

        db.session.commit()

        return redirect(url_for("manage_results"))

    # ==============================
    # STUDENT DASHBOARD
    # ==============================

    @app.route("/student_dashboard")
    @role_required("student")
    def student_dashboard():

        student_id = session["user_id"]

        # Get all published examinations
        examinations = Examination.query.filter_by(
            status="Published"
        ).order_by(
            Examination.id.desc()
        ).all()

        # Get this student's active booking history
        bookings = Booking.query.filter(
            Booking.student_id == student_id,
            Booking.status != "Cancelled"
        ).order_by(
            Booking.booked_at.desc()
        ).all()

        # Get current date and time
        now = datetime.now()

        return render_template(
            "student_dashboard.html",
            examinations=examinations,
            bookings=bookings,
            now=now
        )

    # ==============================
    # STUDENT VIEWS AVAILABLE SLOTS
    # ==============================

    @app.route("/student_view_slots/<int:examination_id>")
    @role_required("student")
    def student_view_slots(examination_id):

        examination = db.session.get(
            Examination,
            examination_id
        )

        if examination is None:
            return redirect(url_for("student_dashboard"))

        now = datetime.now()

        slots = ExaminationSlot.query.filter_by(
            examination_id=examination_id,
            status="Available"
        ).all()

        available_slots = []

        for slot in slots:

            if (
                examination.booking_start <= now
                <= examination.booking_end
                and slot.available_seats > 0
            ):
                available_slots.append(slot)

        return render_template(
            "student_view_slots.html",
            examination=examination,
            slots=available_slots
        )
    
    # ==============================
    # STUDENT BOOKS EXAMINATION SLOT
    # ==============================

    @app.route("/book_slot/<int:slot_id>", methods=["POST"])
    @role_required("student")
    def book_slot(slot_id):

        student_id = session["user_id"]

        slot = db.session.get(
            ExaminationSlot,
            slot_id
        )

        if slot is None:
            return redirect(url_for("student_dashboard"))

        examination = slot.examination

        now = datetime.now()

        # Check booking period
        if not (
            examination.booking_start
            <= now
            <= examination.booking_end
        ):
            return redirect(
                url_for(
                    "student_view_slots",
                    examination_id=examination.id
                )
            )

        # Check slot availability
        if (
            slot.status != "Available"
            or slot.available_seats <= 0
        ):
            return redirect(
                url_for(
                    "student_view_slots",
                    examination_id=examination.id
                )
            )

        # Check existing booking
        existing_booking = Booking.query.filter_by(
            student_id=student_id,
            slot_id=slot_id,
            status="Booked"
        ).first()

        if existing_booking:
            return redirect(
                url_for(
                    "student_view_slots",
                    examination_id=examination.id
                )
            )

        # Create booking
        booking = Booking(
            student_id=student_id,
            slot_id=slot_id,
            status="Booked"
        )

        db.session.add(booking)

        # Update slot status
        if slot.booked_count + 1 >= slot.capacity:
            slot.status = "Full"

        db.session.commit()

        return redirect(
            url_for(
                "student_view_slots",
                examination_id=examination.id
            )
        )

    # ==============================
    # STUDENT CANCELS BOOKING
    # ==============================

    @app.route(
        "/cancel_booking/<int:booking_id>",
        methods=["POST"]
    )
    @role_required("student")
    def cancel_booking(booking_id):

        booking = Booking.query.filter_by(
            id=booking_id,
            student_id=session["user_id"],
            status="Booked"
        ).first_or_404()

        booking.status = "Cancelled"
        booking.slot.status = "Available"

        db.session.commit()

        return redirect(url_for("student_dashboard"))

        # ==============================
    # STUDENT VIEWS EXAMINATION RESULT
    # ==============================

    @app.route("/student_result/<int:booking_id>")
    @role_required("student")
    def student_view_booking_result(booking_id):

        # Get booking belonging to the logged-in student
        booking = Booking.query.filter_by(
            id=booking_id,
            student_id=session["user_id"]
        ).first_or_404()

        # Get evaluation for this booking
        evaluation = Evaluation.query.filter_by(
            booking_id=booking.id
        ).first()

        # Check whether result is published
        if evaluation and evaluation.published:

            return render_template(
                "student_results.html",
                booking=booking,
                evaluation=evaluation
            )

        # Result is not yet published
        return render_template(
            "wait_result.html",
            booking=booking
        )

    # ========================================
    # EXAMINER CREATES AND MANAGES OWN SLOTS
    # ========================================

    @app.route(
        "/examiner_slots/<int:examination_id>",
        methods=["GET", "POST"]
    )
    @role_required("examiner")
    def examiner_slots(examination_id):

        examiner_id = session["user_id"]

        # Get examination details
        examination = db.session.get(
            Examination,
            examination_id
        )

        if examination is None:
            return redirect(
                url_for("examiner_dashboard")
            )

        # Create a new slot
        if request.method == "POST":

            try:
                exam_date = datetime.strptime(
                    request.form.get("exam_date"),
                    "%Y-%m-%d"
                ).date()

                start_time = datetime.strptime(
                    request.form.get("start_time"),
                    "%H:%M"
                ).time()

                end_time = datetime.strptime(
                    request.form.get("end_time"),
                    "%H:%M"
                ).time()

                capacity = int(
                    request.form.get("capacity")
                )

            except (ValueError, TypeError):
                return redirect(
                    url_for(
                        "examiner_slots",
                        examination_id=examination_id
                    )
                )

            now = datetime.now()

            # Validate examination and slot details
            if (
                examination.status != "Published"
                or now < examination.slot_creation_start
                or now > examination.slot_creation_end
                or exam_date < date.today()
                or start_time >= end_time
                or capacity <= 0
                or capacity > examination.student_capacity
            ):
                return redirect(
                    url_for(
                        "examiner_slots",
                        examination_id=examination_id
                    )
                )

            # Create slot
            slot = ExaminationSlot(
                examination_id=examination_id,
                examiner_id=examiner_id,
                exam_date=exam_date,
                start_time=start_time,
                end_time=end_time,
                capacity=capacity,
                status="Available"
            )

            db.session.add(slot)
            db.session.commit()

            return redirect(
                url_for(
                    "examiner_slots",
                    examination_id=examination_id
                )
            )

        # Display slots created by this examiner
        slots = ExaminationSlot.query.filter_by(
            examiner_id=examiner_id,
            examination_id=examination_id
        ).order_by(
            ExaminationSlot.exam_date,
            ExaminationSlot.start_time
        ).all()

        return render_template(
            "examiner_slots.html",
            examination=examination,
            slots=slots,
            today=date.today().isoformat()
        )

    # ==============================
    # EXAMINER DASHBOARD
    # ==============================

    @app.route("/examiner_dashboard")
    @role_required("examiner")
    def examiner_dashboard():

        examiner_id = session["user_id"]

        # Get all published examinations
        examinations = Examination.query.filter_by(
            status="Published"
        ).order_by(
            Examination.id.desc()
        ).all()

        # Get slots created by this examiner
        slots = ExaminationSlot.query.filter_by(
            examiner_id=examiner_id
        ).order_by(
            ExaminationSlot.exam_date,
            ExaminationSlot.start_time
        ).all()

        # Get student bookings for this examiner's slots
        bookings = Booking.query.join(
            ExaminationSlot
        ).filter(
            ExaminationSlot.examiner_id == examiner_id,
            Booking.status == "Booked"
        ).all()

        return render_template(
            "examiner_dashboard.html",
            examinations=examinations,
            slots=slots,
            bookings=bookings
        )

    # ==============================
    # EXAMINER EVALUATES STUDENT
    # ==============================

    @app.route(
        "/evaluate/<int:booking_id>",
        methods=["GET", "POST"]
    )
    @role_required("examiner")
    def evaluate_student(booking_id):

        booking = Booking.query.filter_by(
            id=booking_id,
            status="Booked"
        ).first_or_404()

        if booking.slot.examiner_id != session["user_id"]:
            return redirect(url_for("examiner_dashboard"))

        examination = booking.slot.examination

        if request.method == "POST":

            existing_evaluation = Evaluation.query.filter_by(
                booking_id=booking_id
            ).first()

            if existing_evaluation:
                return redirect(url_for("examiner_dashboard"))

            rubrics = examination.rubrics

            if not rubrics:
                return redirect(url_for("examiner_dashboard"))

            total_marks = 0
            evaluation_details = []

            try:
                for rubric in rubrics:

                    marks = float(
                        request.form.get(
                            f"marks_{rubric.id}",
                            0
                        )
                    )

                    if marks < 0 or marks > rubric.maximum_marks:
                        return redirect(
                            url_for(
                                "evaluate_student",
                                booking_id=booking_id
                            )
                        )

                    total_marks += marks

                    evaluation_details.append(
                        (rubric.id, marks)
                    )

            except (ValueError, TypeError):
                return redirect(
                    url_for(
                        "evaluate_student",
                        booking_id=booking_id
                    )
                )

            if total_marks > examination.maximum_marks:
                return redirect(
                    url_for(
                        "evaluate_student",
                        booking_id=booking_id
                    )
                )

            evaluation = Evaluation(
                booking_id=booking_id,
                total_marks=total_marks,
                remarks=request.form.get("remarks", "").strip(),
                published=False
            )

            db.session.add(evaluation)
            db.session.flush()

            for rubric_id, marks in evaluation_details:

                detail = EvaluationDetail(
                    evaluation_id=evaluation.id,
                    rubric_id=rubric_id,
                    marks_awarded=marks
                )

                db.session.add(detail)

            db.session.commit()

            return redirect(url_for("examiner_dashboard"))

        return render_template(
            "examiner_evaluation.html",
            booking=booking,
            rubrics=examination.rubrics
        )

    # ==============================
    # STUDENT VIEW PUBLISHED RESULTS
    # ==============================

    @app.route("/student_results")
    @role_required("student")
    def student_results():

        student_id = session["user_id"]

        evaluations = Evaluation.query.join(
            Booking
        ).filter(
            Booking.student_id == student_id,
            Evaluation.published == True
        ).all()

        return render_template(
            "student_results.html",
            evaluations=evaluations,
        )

