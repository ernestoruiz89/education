import unittest
from unittest.mock import Mock, patch

import frappe

from education.education.doctype.student_attendance.student_attendance import StudentAttendance
from education.education.doctype.student_leave_application.student_leave_application import (
	StudentLeaveApplication,
)


class TestLeaveAttendanceScope(unittest.TestCase):
	def leave(self, **changes):
		values = dict(
			doctype="Student Leave Application",
			name="LEAVE",
			student="STUDENT",
			student_name="Student",
			attendance_based_on="Student Batch",
			student_batch="BATCH",
			from_date="2026-10-01",
			to_date="2026-10-02",
			docstatus=1,
			mark_as_present=0,
		)
		values.update(changes)
		return StudentLeaveApplication(values)

	def test_cancellation_reads_only_attendance_linked_to_this_application(self):
		leave = self.leave(docstatus=2)
		attendance = frappe._dict(
			student="STUDENT",
			student_batch="BATCH",
			subject_schedule=None,
			date="2026-10-01",
			docstatus=1,
			cancel=Mock(),
		)
		with (
			patch.object(frappe, "get_all", return_value=["OWN"]) as query,
			patch.object(frappe, "get_doc", return_value=attendance),
		):
			leave.cancel_attendance()
		self.assertEqual(
			query.call_args.kwargs["filters"], {"leave_application": "LEAVE", "docstatus": ("!=", 2)}
		)
		attendance.cancel.assert_called_once_with()

	def test_wrong_student_group_or_class_cannot_be_cancelled(self):
		for changes in (dict(student="OTHER"), dict(student_batch="OTHER"), dict(subject_schedule="CLASS")):
			attendance = frappe._dict(
				student="STUDENT",
				student_batch="BATCH",
				subject_schedule=None,
				date="2026-10-01",
				docstatus=1,
				cancel=Mock(),
			)
			attendance.update(changes)
			with (
				patch.object(frappe, "get_all", return_value=["OWN"]),
				patch.object(frappe, "get_doc", return_value=attendance),
			):
				with self.assertRaises(frappe.ValidationError):
					self.leave(docstatus=2).cancel_attendance()
			attendance.cancel.assert_not_called()

	def test_existing_attendance_is_never_overwritten(self):
		leave = self.leave(to_date="2026-10-01")
		existing = frappe._dict(name="EXISTING", leave_application=None, docstatus=1, status="Absent")
		with (
			patch.object(StudentLeaveApplication, "validate_context"),
			patch.object(frappe, "has_permission"),
			patch.object(frappe, "get_doc"),
			patch.object(frappe.db, "get_value", return_value="COMPANY"),
			patch(
				"education.education.doctype.student_leave_application.student_leave_application.get_holiday_list",
				return_value="HOLIDAYS",
			),
			patch(
				"education.education.doctype.student_leave_application.student_leave_application.is_holiday",
				return_value=False,
			),
			patch.object(frappe, "get_all", return_value=[existing]),
			patch.object(frappe.db, "set_value") as update,
		):
			with self.assertRaises(frappe.ValidationError):
				leave.update_attendance()
		update.assert_not_called()

	def test_application_cannot_bypass_attendance_create_permission(self):
		with (
			patch.object(StudentLeaveApplication, "validate_context"),
			patch.object(frappe, "has_permission", side_effect=frappe.PermissionError),
		):
			with self.assertRaises(frappe.PermissionError):
				self.leave().update_attendance()

	def test_unapproved_or_foreign_leave_cannot_authorize_attendance(self):
		leave = self.leave()
		attendance = StudentAttendance(
			dict(
				doctype="Student Attendance",
				student="STUDENT",
				student_batch="BATCH",
				date="2026-10-01",
				leave_application="LEAVE",
				status="Leave",
			)
		)
		for field, value in (("docstatus", 0), ("student", "OTHER"), ("student_batch", "OTHER")):
			foreign = self.leave()
			foreign.set(field, value)
			with (
				patch.object(frappe, "get_doc", return_value=foreign),
				self.assertRaises(frappe.PermissionError),
			):
				attendance.validate_leave_application()
		with patch.object(frappe, "get_doc", return_value=leave):
			attendance.validate_leave_application()

	def test_duplicate_scope_contains_group_or_exact_class(self):
		self.assertEqual(self.leave().attendance_scope()["student_batch"], "BATCH")
		scope = self.leave(
			attendance_based_on="Subject Schedule", subject_schedule="CLASS"
		).attendance_scope()
		self.assertEqual(scope["subject_schedule"], "CLASS")
		self.assertNotIn("student_batch", scope)
