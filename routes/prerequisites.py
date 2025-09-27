# routes/prerequisites.py
from flask import Blueprint, request, jsonify
from app import db
from models import Course, CoursePrerequisitesCourses, UserRole
from auth import get_current_user, instructor_required


prereq_bp = Blueprint("prereq_bp", __name__)

# CREATE prerequisites
@prereq_bp.route('/<int:course_id>/prerequisites', methods=['POST'])
def add_prerequisites(course_id):
    user = get_current_user()
    course = Course.query.get(course_id)

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    # ✅ Only admin or instructor (who owns course) can add prereqs
    if not (
        user.role == UserRole.ADMIN or 
        (user.role == UserRole.INSTRUCTOR and course.instructor_id == user.id)
    ):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    prereq_ids = data.get("prerequisite_course_ids", [])

    # Validate prereq IDs
    valid_ids = Course.query.filter(Course.id.in_(prereq_ids)).all()
    valid_ids_set = {c.id for c in valid_ids}

    for pid in valid_ids_set:
        existing = CoursePrerequisitesCourses.query.filter_by(
            course_id=course_id, prerequisite_course_id=pid
        ).first()
        if not existing:
            prereq = CoursePrerequisitesCourses(
                course_id=course_id,
                prerequisite_course_id=pid
            )
            db.session.add(prereq)

    db.session.commit()

    return jsonify({
        "message": "Prerequisites added",
        "course_id": course_id,
        "prerequisite_course_ids": list(valid_ids_set)
    }), 201


# READ prerequisites
@prereq_bp.route('/<int:course_id>/prerequisites', methods=['GET'])
def get_prerequisites(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    return jsonify({
        "course_id": course.id,
        "prerequisites": [
            {
                "id": p.prerequisite_course.id,
                "title": p.prerequisite_course.title,
                "difficulty_level": p.prerequisite_course.difficulty_level
            }
            for p in course.prerequisites_courses.all()
        ]
    }), 200


# DELETE prerequisites
@prereq_bp.route('/<int:course_id>/prerequisites/<int:prereq_id>', methods=['DELETE'])
def delete_prerequisite(course_id, prereq_id):
    user = get_current_user()
    course = Course.query.get(course_id)

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if not (
        user.role == UserRole.ADMIN or 
        (user.role == UserRole.INSTRUCTOR and course.instructor_id == user.id)
    ):
        return jsonify({'error': 'Unauthorized'}), 403

    prereq = CoursePrerequisitesCourses.query.filter_by(
        course_id=course_id, prerequisite_course_id=prereq_id
    ).first()

    if not prereq:
        return jsonify({'error': 'Prerequisite not found'}), 404

    db.session.delete(prereq)
    db.session.commit()

    return jsonify({
        "message": "Prerequisite removed",
        "course_id": course_id,
        "removed_prerequisite_id": prereq_id
    }), 200


# UPDATE prerequisites (replace all existing with new ones)
@prereq_bp.route('/<int:course_id>/prerequisites', methods=['PUT'])
def update_prerequisites(course_id):
    user = get_current_user()
    course = Course.query.get(course_id)

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if not (
        user.role == UserRole.ADMIN or 
        (user.role == UserRole.INSTRUCTOR and course.instructor_id == user.id)
    ):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    new_prereq_ids = set(data.get("prerequisite_course_ids", []))      

    # Validate
    valid_courses = Course.query.filter(Course.id.in_(new_prereq_ids)).all()
    valid_ids = {c.id for c in valid_courses}

    # Remove old prereqs
    CoursePrerequisitesCourses.query.filter_by(course_id=course_id).delete()

    # Add new prereqs
    for pid in valid_ids:
        prereq = CoursePrerequisitesCourses(
            course_id=course_id,
            prerequisite_course_id=pid
        )
        db.session.add(prereq)

    db.session.commit()

    return jsonify({
        "message": "Prerequisites updated",
        "course_id": course_id,
        "prerequisite_course_ids": list(valid_ids)
    }), 200
