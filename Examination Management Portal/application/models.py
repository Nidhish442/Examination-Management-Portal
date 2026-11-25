
from datetime import datetime

from application.database import db
from werkzeug.security import generate_password_hash, check_password_hash


# --------------------------------------------------
# 1. USERS: Admin, Examiner and Student
# --------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="Active", nullable=False)
    department = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# --------------------------------------------------
# 2. COURSES
# --------------------------------------------------
class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="Active", nullable=False)

    examinations = db.relationship(
        "Examination",
        back_populates="course"
    )


# --------------------------------------------------
# 3. EXAMINATIONS
# --------------------------------------------------
class Examination(db.Model):
    __tablename__ = "examinations"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id"),
        nullable=False
    )

    name = db.Column(db.String(150), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    maximum_marks = db.Column(db.Integer, nullable=False, default=100)
    student_capacity = db.Column(db.Integer, nullable=False, default=100)

    slot_creation_start = db.Column(db.DateTime, nullable=False)
    slot_creation_end = db.Column(db.DateTime, nullable=False)
    booking_start = db.Column(db.DateTime, nullable=False)
    booking_end = db.Column(db.DateTime, nullable=False)

    status = db.Column(db.String(30), default="Published", nullable=False)
    results_published = db.Column(db.Boolean, default=False, nullable=False)

    course = db.relationship(
        "Course",
        back_populates="examinations"
    )

    rubrics = db.relationship(
        "Rubric",
        back_populates="examination",
        cascade="all, delete-orphan"
    )

    slots = db.relationship(
        "ExaminationSlot",
        back_populates="examination",
        cascade="all, delete-orphan"
    )


# --------------------------------------------------
# 4. RUBRICS: Evaluation criteria
# --------------------------------------------------
class Rubric(db.Model):
    __tablename__ = "rubrics"

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(
        db.Integer,
        db.ForeignKey("examinations.id"),
        nullable=False
    )

    criterion_name = db.Column(db.String(150), nullable=False)
    maximum_marks = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)

    examination = db.relationship(
        "Examination",
        back_populates="rubrics"
    )


# --------------------------------------------------
# 5. EXAMINATION SLOTS
# --------------------------------------------------
class ExaminationSlot(db.Model):
    __tablename__ = "examination_slots"

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(
        db.Integer,
        db.ForeignKey("examinations.id"),
        nullable=False
    )
    examiner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), default="Available", nullable=False)

    examination = db.relationship(
        "Examination",
        back_populates="slots"
    )

    examiner = db.relationship("User")

    bookings = db.relationship(
        "Booking",
        back_populates="slot",
        cascade="all, delete-orphan"
    )

    @property
    def booked_count(self):
        return sum(
            booking.status == "Booked"
            for booking in self.bookings
        )

    @property
    def available_seats(self):
        return max(0, self.capacity - self.booked_count)


# --------------------------------------------------
# 6. BOOKINGS: Students reserve examination slots
# --------------------------------------------------
class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    slot_id = db.Column(
        db.Integer,
        db.ForeignKey("examination_slots.id"),
        nullable=False
    )

    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Booked", nullable=False)

    student = db.relationship(
        "User",
        foreign_keys=[student_id]
    )

    slot = db.relationship(
        "ExaminationSlot",
        back_populates="bookings"
    )

    evaluation = db.relationship(
        "Evaluation",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "slot_id",
            name="unique_student_slot"
        ),
    )


# --------------------------------------------------
# 7. EVALUATIONS: Marks and examiner remarks
# --------------------------------------------------
class Evaluation(db.Model):
    __tablename__ = "evaluations"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id"),
        unique=True,
        nullable=False
    )

    total_marks = db.Column(db.Float, default=0, nullable=False)
    remarks = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    published = db.Column(db.Boolean, default=False, nullable=False)

    booking = db.relationship(
        "Booking",
        back_populates="evaluation"
    )

    details = db.relationship(
        "EvaluationDetail",
        back_populates="evaluation",
        cascade="all, delete-orphan"
    )


# --------------------------------------------------
# 8. EVALUATION DETAILS: Marks for each criterion
# --------------------------------------------------
class EvaluationDetail(db.Model):
    __tablename__ = "evaluation_details"

    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(
        db.Integer,
        db.ForeignKey("evaluations.id"),
        nullable=False
    )
    rubric_id = db.Column(
        db.Integer,
        db.ForeignKey("rubrics.id"),
        nullable=False
    )
    marks_awarded = db.Column(db.Float, nullable=False, default=0)

    evaluation = db.relationship(
        "Evaluation",
        back_populates="details"
    )

    rubric = db.relationship("Rubric")

    __table_args__ = (
        db.UniqueConstraint(
            "evaluation_id",
            "rubric_id",
            name="unique_evaluation_rubric"
        ),
    )
