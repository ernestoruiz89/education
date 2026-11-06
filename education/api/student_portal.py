"""Student self-service, scoped to the Student linked to the authenticated user.

Students do not need Desk access to Course Enrollment or Sales Invoice. These
queries deliberately bind every personal record to the session, never to an ID
supplied by the browser, and do not change DocType permissions.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate


def _student():
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication failed"), frappe.AuthenticationError)
	return frappe.db.get_value(
		"Student",
		{"user": frappe.session.user},
		[
			"name",
			"student_name",
			"email_address",
			"student_mobile_number",
			"image",
			"joining_date",
			"date_of_leaving",
			"date_of_birth",
			"enabled",
			"gender",
			"blood_group",
			"nationality",
			"address_line_1",
			"address_line_2",
			"city",
			"state",
			"country",
			"pincode",
		],
		as_dict=True,
	)


def _enrollments(student):
	return frappe.get_all(
		"Course Enrollment",
		filters={"student": student, "docstatus": 1},
		fields=["name", "program", "course", "student_batch", "enrollment_date", "status"],
		order_by="enrollment_date desc, creation desc",
	)


def _batches(enrollments):
	names = list({row.student_batch for row in enrollments if row.student_batch})
	if not names:
		return []
	return frappe.get_all(
		"Student Batch Name",
		filters={"name": ["in", names]},
		fields=["name", "batch_name", "program", "course", "start_date", "end_date", "disabled"],
		order_by="start_date desc, batch_name",
	)


def _in_enrollment(date, batch, enrollments, student):
	date = getdate(date)
	if student.joining_date and date < getdate(student.joining_date):
		return False
	if student.date_of_leaving and date > getdate(student.date_of_leaving):
		return False
	return any(
		row.student_batch == batch and (not row.enrollment_date or date >= getdate(row.enrollment_date))
		for row in enrollments
	)


@frappe.whitelist()
def get_dashboard():
	student = _student()
	settings = frappe.get_cached_doc("Education Settings")
	data = frappe._dict(
		student=student,
		school={
			"name": settings.school_college_name_abbreviation or "Education",
			"logo": settings.school_college_logo,
		},
		enrollments=[],
		batches=[],
		schedules=[],
		grades=[],
		attendance=[],
		invoices=[],
		can_request_leave=False,
		payment_enabled=False,
	)
	if not student:
		return data

	enrollments = data.enrollments = _enrollments(student.name)
	data.batches = _batches(enrollments)
	batch_names = [batch.name for batch in data.batches]
	if batch_names:
		schedules = frappe.get_all(
			"Subject Schedule",
			filters={"student_batch": ["in", batch_names], "docstatus": ["!=", 2]},
			fields=[
				"name",
				"student_batch",
				"schedule_date",
				"title",
				"course",
				"subject",
				"room",
				"faculty_name",
				"from_time",
				"to_time",
				"class_schedule_color",
			],
			order_by="schedule_date, from_time",
		)
		data.schedules = [
			row
			for row in schedules
			if _in_enrollment(row.schedule_date, row.student_batch, enrollments, student)
		]

	data.grades = frappe.get_all(
		"Assessment Result",
		filters={"student": student.name, "docstatus": 1},
		fields=[
			"name",
			"assessment_plan",
			"assessment_group",
			"course",
			"subject",
			"student_batch",
			"score",
			"maximum_score",
			"percentage",
			"comment",
		],
		order_by="creation desc",
	)
	plans = list({row.assessment_plan for row in data.grades if row.assessment_plan})
	plan_info = (
		{
			row.name: row
			for row in frappe.get_all(
				"Assessment Plan",
				filters={"name": ["in", plans]},
				fields=["name", "assessment_name", "schedule_date"],
			)
		}
		if plans
		else {}
	)
	for row in data.grades:
		plan = plan_info.get(row.assessment_plan, {})
		row.assessment_name = plan.get("assessment_name") or row.assessment_group
		row.schedule_date = plan.get("schedule_date")

	data.attendance = frappe.get_all(
		"Student Attendance",
		filters={"student": student.name, "docstatus": 1},
		fields=["name", "date", "status", "student_batch", "subject_schedule"],
		order_by="date desc, creation desc",
	)
	data.invoices = frappe.get_all(
		"Sales Invoice",
		filters={"student": student.name, "docstatus": 1},
		fields=[
			"name",
			"posting_date",
			"due_date",
			"status",
			"currency",
			"grand_total",
			"outstanding_amount",
		],
		order_by="due_date desc, name desc",
	)
	from education.education.api import get_fees_print_format

	data.print_format = get_fees_print_format() or "Standard"
	for row in data.invoices:
		row.can_print = bool(frappe.has_permission("Sales Invoice", "print", doc=row.name))
	data.can_request_leave = bool(
		cint(student.enabled)
		and data.batches
		and frappe.has_permission("Student Leave Application", "create")
	)
	# Do not expose an unconfigured gateway or its credentials to the browser.
	data.payment_enabled = bool(
		settings.razorpay_key and settings.get_password("razorpay_secret", raise_exception=False)
	)
	return data


@frappe.whitelist(methods=["POST"])
def request_leave(student_batch: str, from_date: str, to_date: str, reason: str):
	student = _student()
	if not student or not cint(student.enabled):
		frappe.throw(_("An active student profile is required."), frappe.PermissionError)
	if not frappe.has_permission("Student Leave Application", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	enrollments = _enrollments(student.name)
	batches = {row.name: row for row in _batches(enrollments)}
	batch = batches.get(student_batch)
	if not batch or batch.disabled:
		frappe.throw(_("Select a batch you are enrolled in."), frappe.PermissionError)
	if not from_date or not to_date or getdate(from_date) > getdate(to_date):
		frappe.throw(_("From Date must be before To Date"))
	for date in (from_date, to_date):
		if not _in_enrollment(date, student_batch, enrollments, student) or not (
			getdate(batch.start_date) <= getdate(date) <= getdate(batch.end_date)
		):
			frappe.throw(_("Leave dates must be within your enrollment and batch dates."))
	if not reason or not reason.strip():
		frappe.throw(_("Reason is required"))
	doc = frappe.get_doc(
		{
			"doctype": "Student Leave Application",
			"student": student.name,
			"student_name": student.student_name,
			"student_batch": student_batch,
			"attendance_based_on": "Student Batch",
			"from_date": from_date,
			"to_date": to_date,
			"reason": reason.strip(),
			"mark_as_present": 0,
		}
	)
	# Native permissions and validations apply. Approval remains with staff;
	# a student request must never submit or alter attendance records.
	doc.insert()
	return {"name": doc.name, "docstatus": doc.docstatus}
