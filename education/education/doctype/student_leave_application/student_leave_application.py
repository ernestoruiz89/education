# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import timedelta

import frappe
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt, get_link_to_form, getdate

from education.education.doctype.student_attendance.student_attendance import (
	get_holiday_list,
)


class StudentLeaveApplication(Document):
	def validate(self):
		self.validate_from_to_dates("from_date", "to_date")
		self.validate_context()
		self.validate_holiday_list()
		self.validate_duplicate()

	def on_submit(self):
		self.update_attendance()

	def on_cancel(self):
		self.cancel_attendance()

	def validate_duplicate(self):
		filters = self.attendance_scope()
		filters.update(
			{
				"from_date": ("<=", self.to_date),
				"to_date": (">=", self.from_date),
				"name": ("!=", self.name),
				"docstatus": ("<", 2),
			}
		)
		existing = frappe.db.exists("Student Leave Application", filters)
		if existing:
			frappe.throw(
				_("Leave application {0} already exists against the student {1}").format(
					get_link_to_form("Student Leave Application", existing), frappe.bold(self.student)
				),
				title=_("Duplicate Entry"),
			)

	def attendance_scope(self):
		"""An application authorizes one group or one class, never a whole student."""
		filters = {"student": self.student, "attendance_based_on": self.attendance_based_on}
		if self.attendance_based_on == "Student Batch" and self.student_batch:
			filters["student_batch"] = self.student_batch
		elif self.attendance_based_on == "Subject Schedule" and self.subject_schedule:
			filters["subject_schedule"] = self.subject_schedule
		else:
			frappe.throw(_("Select a student batch or subject schedule for this application."))
		return filters

	def validate_context(self):
		self.attendance_scope()
		student = frappe.get_doc("Student", self.student)
		student.check_permission("read")
		if (
			not frappe.has_permission("Student Leave Application", "submit")
			and student.user != frappe.session.user
		):
			frappe.throw(
				_("You may only request leave for your own student profile."), frappe.PermissionError
			)
		if self.attendance_based_on == "Subject Schedule":
			schedule = frappe.get_doc("Subject Schedule", self.subject_schedule)
			schedule.check_permission("read")
			if schedule.docstatus == 2 or not getdate(self.from_date) <= getdate(
				schedule.schedule_date
			) <= getdate(self.to_date):
				frappe.throw(_("The class must be active and within the leave dates."))
			batch_name = schedule.student_batch
		else:
			batch_name = self.student_batch
		batch = frappe.get_doc("Student Batch Name", batch_name)
		# Student users may request leave without Desk access to the batch catalog.
		# Ownership is checked through a confirmed enrollment, not browser input.
		if not frappe.db.exists(
			"Course Enrollment",
			{
				"student": self.student,
				"student_batch": batch_name,
				"docstatus": 1,
				"enrollment_date": ("<=", self.from_date),
			},
		):
			frappe.throw(_("The student must be enrolled in the selected batch."), frappe.PermissionError)
		if getdate(self.from_date) < getdate(batch.start_date) or getdate(self.to_date) > getdate(
			batch.end_date
		):
			frappe.throw(_("Leave dates must be within the batch dates."))
		if student.date_of_leaving and getdate(self.to_date) >= getdate(student.date_of_leaving):
			frappe.throw(_("Leave dates must precede the student's leaving date."))

	def validate_holiday_list(self):
		batch = self.student_batch
		if self.attendance_based_on == "Subject Schedule":
			batch = frappe.db.get_value("Subject Schedule", self.subject_schedule, "student_batch")
		company = frappe.db.get_value("Student Batch Name", batch, "company")
		holiday_list = get_holiday_list(company)
		self.total_leave_days = get_number_of_leave_days(self.from_date, self.to_date, holiday_list)

	def update_attendance(self):
		"""Create linked attendance through native permissions; preserve existing records."""
		self.validate_context()
		frappe.has_permission("Student Attendance", "create", throw=True)
		frappe.has_permission("Student Attendance", "submit", throw=True)
		scope = self.attendance_scope()
		scope.pop("attendance_based_on")
		if self.attendance_based_on == "Subject Schedule":
			schedule = frappe.get_doc("Subject Schedule", self.subject_schedule, for_update=True)
			dates = [getdate(schedule.schedule_date)]
			batch_name = schedule.student_batch
		else:
			frappe.get_doc("Student Batch Name", self.student_batch, for_update=True)
			dates = list(daterange(getdate(self.from_date), getdate(self.to_date)))
			batch_name = self.student_batch
		company = frappe.db.get_value("Student Batch Name", batch_name, "company")
		holiday_list = get_holiday_list(company)
		for day in dates:
			if is_holiday(holiday_list, day):
				continue
			filters = {**scope, "date": day, "docstatus": ("!=", 2)}
			existing = frappe.get_all(
				"Student Attendance",
				filters=filters,
				fields=["name", "leave_application", "docstatus", "status"],
			)
			status = "Present" if self.mark_as_present else "Leave"
			if existing:
				if all(
					row.leave_application == self.name and row.docstatus == 1 and row.status == status
					for row in existing
				):
					continue
				frappe.throw(
					_(
						"Attendance already exists for this class or group and date. Resolve it before approving leave."
					)
				)
			doc = frappe.get_doc(
				{
					"doctype": "Student Attendance",
					**scope,
					"student_batch": batch_name,
					"student_name": self.student_name,
					"date": day,
					"leave_application": self.name,
					"status": status,
				}
			)
			doc.insert()
			doc.submit()

	def cancel_attendance(self):
		"""Cancel only attendance explicitly generated by this application."""
		if self.docstatus != 2:
			return
		for name in frappe.get_all(
			"Student Attendance",
			filters={"leave_application": self.name, "docstatus": ("!=", 2)},
			pluck="name",
		):
			doc = frappe.get_doc("Student Attendance", name, for_update=True)
			if doc.student != self.student or not getdate(self.from_date) <= getdate(doc.date) <= getdate(
				self.to_date
			):
				frappe.throw(_("Linked attendance does not match this leave application."))
			if self.attendance_based_on == "Student Batch":
				matches = doc.student_batch == self.student_batch and not doc.subject_schedule
			else:
				matches = doc.subject_schedule == self.subject_schedule
			if not matches:
				frappe.throw(_("Linked attendance does not match this leave application."))
			if doc.docstatus != 1:
				frappe.throw(_("Resolve linked draft attendance before cancelling leave."))
			doc.cancel()


def daterange(start_date, end_date):
	for n in range(int((end_date - start_date).days) + 1):
		yield start_date + timedelta(n)


def get_number_of_leave_days(from_date, to_date, holiday_list):
	number_of_days = date_diff(to_date, from_date) + 1

	holidays = frappe.db.sql(
		"""
		SELECT
			COUNT(DISTINCT holiday_date)
		FROM `tabHoliday` h1,`tabHoliday List` h2
		WHERE
			h1.parent = h2.name and
			h1.holiday_date between %s and %s and
			h2.name = %s""",
		(from_date, to_date, holiday_list),
	)[0][0]

	number_of_days = flt(number_of_days) - flt(holidays)

	return number_of_days


@frappe.whitelist()
def get_student_batches(student: str):
	"""Return the batches the student is enrolled in."""
	return frappe.db.get_all(
		"Course Enrollment",
		pluck="student_batch",
		filters={"student": student, "docstatus": 1, "student_batch": ("is", "set")},
		distinct=True,
	)
