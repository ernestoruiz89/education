import unittest
from unittest.mock import Mock, patch

import frappe

from education.api import student_portal as portal
from education.hooks import website_redirects


class TestStudentPortal(unittest.TestCase):
	def setUp(self):
		self.user = frappe.session.user
		frappe.set_user("portal-test@example.com")
		self.profile = frappe._dict(
			name="OWN-STUDENT", enabled=1, joining_date="2026-01-01", date_of_leaving=None
		)
		self.enrollments = [frappe._dict(student_batch="OWN-BATCH", enrollment_date="2026-02-01")]
		self.batch = frappe._dict(
			name="OWN-BATCH", disabled=0, start_date="2026-02-01", end_date="2026-12-31"
		)

	def tearDown(self):
		frappe.set_user(self.user)

	def test_guest_cannot_read_personal_data(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.AuthenticationError):
			portal.get_dashboard()

	def test_portal_boot_uses_frappe_language_without_caching_user_context(self):
		from education.www.student_portal import get_context

		for language in ("es", "en"):
			with (
				patch.object(frappe.local, "lang", language),
				patch.object(frappe.db, "get_single_value", return_value=None),
			):
				context = frappe._dict()
				get_context(context)
			self.assertEqual(context.lang, language)
			self.assertEqual(context.portal_boot["language"], language)
			self.assertEqual(context.no_cache, 1)

	def test_account_without_student_is_a_valid_empty_state(self):
		with (
			patch.object(frappe.db, "get_value", return_value=None) as get_value,
			patch.object(frappe, "get_cached_doc", return_value=frappe._dict()),
			patch.object(frappe, "get_all") as get_all,
		):
			data = portal.get_dashboard()
		self.assertIsNone(data.student)
		self.assertEqual(get_value.call_args.args[1], {"user": "portal-test@example.com"})
		get_all.assert_not_called()
		for key in ("batches", "schedules", "grades", "attendance", "invoices"):
			self.assertEqual(data[key], [])

	def test_browser_cannot_choose_another_student(self):
		with self.assertRaises(TypeError):
			portal.get_dashboard(student="OTHER-STUDENT")
		with patch.object(frappe, "get_all", return_value=[]) as get_all:
			portal._enrollments(self.profile.name)
		self.assertEqual(get_all.call_args.kwargs["filters"], {"student": "OWN-STUDENT", "docstatus": 1})

	def test_schedule_respects_enrollment_and_student_dates(self):
		self.assertFalse(portal._in_enrollment("2026-01-31", "OWN-BATCH", self.enrollments, self.profile))
		self.assertTrue(portal._in_enrollment("2026-02-01", "OWN-BATCH", self.enrollments, self.profile))
		self.assertFalse(portal._in_enrollment("2026-02-01", "OTHER-BATCH", self.enrollments, self.profile))
		self.profile.date_of_leaving = "2026-03-01"
		self.assertFalse(portal._in_enrollment("2026-03-02", "OWN-BATCH", self.enrollments, self.profile))

	def test_foreign_batch_leave_is_denied(self):
		with (
			patch.object(portal, "_student", return_value=self.profile),
			patch.object(portal, "_enrollments", return_value=self.enrollments),
			patch.object(portal, "_batches", return_value=[self.batch]),
			patch.object(frappe, "has_permission", return_value=True),
			patch.object(frappe, "get_doc") as get_doc,
		):
			with self.assertRaises(frappe.PermissionError):
				portal.request_leave("OTHER-BATCH", "2026-03-01", "2026-03-02", "Appointment")
		get_doc.assert_not_called()

	def test_leave_requires_native_create_permission(self):
		with (
			patch.object(portal, "_student", return_value=self.profile),
			patch.object(frappe, "has_permission", return_value=False),
		):
			with self.assertRaises(frappe.PermissionError):
				portal.request_leave("OWN-BATCH", "2026-03-01", "2026-03-02", "Appointment")

	def test_leave_is_an_owned_draft_and_never_submits_attendance(self):
		doc = Mock(name="leave", docstatus=0)
		with (
			patch.object(portal, "_student", return_value=self.profile),
			patch.object(portal, "_enrollments", return_value=self.enrollments),
			patch.object(portal, "_batches", return_value=[self.batch]),
			patch.object(frappe, "has_permission", return_value=True),
			patch.object(frappe, "get_doc", return_value=doc) as get_doc,
		):
			result = portal.request_leave("OWN-BATCH", "2026-03-01", "2026-03-02", " Appointment ")
		payload = get_doc.call_args.args[0]
		self.assertEqual(payload["student"], "OWN-STUDENT")
		self.assertEqual(payload["mark_as_present"], 0)
		self.assertEqual(payload["reason"], "Appointment")
		self.assertEqual(result["docstatus"], 0)
		doc.insert.assert_called_once_with()
		doc.submit.assert_not_called()

	def test_leave_outside_batch_dates_is_rejected(self):
		with (
			patch.object(portal, "_student", return_value=self.profile),
			patch.object(portal, "_enrollments", return_value=self.enrollments),
			patch.object(portal, "_batches", return_value=[self.batch]),
			patch.object(frappe, "has_permission", return_value=True),
		):
			with self.assertRaises(frappe.ValidationError):
				portal.request_leave("OWN-BATCH", "2027-01-01", "2027-01-02", "Appointment")

	def test_legacy_redirect_preserves_page_and_query(self):
		from frappe.website.path_resolver import resolve_redirect

		for path, expected in (
			("education", "/student-portal?source=bookmark"),
			("education/grades", "/student-portal/grades?source=bookmark"),
		):
			with (
				patch.object(frappe, "get_hooks", return_value=website_redirects),
				patch.object(frappe.cache, "hget", return_value=None),
				patch.object(frappe.cache, "hset"),
				self.assertRaises(frappe.Redirect) as redirect,
			):
				resolve_redirect(path, b"source=bookmark")
			self.assertEqual(redirect.exception.http_status_code, 307)
			self.assertEqual(frappe.flags.redirect_location, expected)
