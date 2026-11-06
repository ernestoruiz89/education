"""Admission listings must resolve a real template before website rendering."""

import unittest
from unittest.mock import patch

import frappe
from frappe.utils import add_days, set_request, today
from frappe.website.serve import get_response_without_exception_handling
from frappe.www.list import get_list_context

from education.education.doctype.student_admission import student_admission


class TestAdmissionWebsite(unittest.TestCase):
	def setUp(self):
		self.user = frappe.session.user
		self.form_dict = frappe.local.form_dict
		self.request = getattr(frappe.local, "request", None)
		self.path = getattr(frappe.local, "path", None)
		frappe.set_user("Guest")
		frappe.local.form_dict = frappe._dict()

	def tearDown(self):
		frappe.set_user(self.user)
		frappe.local.form_dict = self.form_dict
		frappe.local.request = self.request
		frappe.local.path = self.path

	def render(self, path):
		set_request(method="GET", path=path)
		return get_response_without_exception_handling(path)

	def test_both_admission_listings_resolve_loadable_templates(self):
		for doctype in ("Student Admission", "Admission Register"):
			with self.subTest(doctype=doctype):
				context = get_list_context(frappe._dict(), doctype)
				self.assertTrue(context.template)
				source, _, _ = frappe.get_jloader().get_source(frappe.get_jenv(), context.template)
				self.assertIn('extends "templates/web.html"', source)
				self.assertIn("includes/list/list.html", source)

	def test_empty_admissions_page_renders_for_guests(self):
		with patch.object(student_admission, "get_admission_list", return_value=[]):
			response = self.render("/admissions")
		self.assertEqual(response.status_code, 200)
		self.assertIn("empty-apps-state", response.get_data(as_text=True))

	def test_admissions_page_renders_original_row_template(self):
		row = frappe._dict(
			name="Admission website fixture",
			title="Admission website fixture",
			academic_year="2026",
			modified=today(),
			admission_start_date=add_days(today(), -1),
			admission_end_date=add_days(today(), 10),
			route="admissions/website-fixture",
		)
		with patch.object(student_admission, "get_admission_list", return_value=[row]) as query:
			response = self.render("/admissions")
		self.assertEqual(response.status_code, 200)
		html = response.get_data(as_text=True)
		self.assertIn("Admission website fixture", html)
		self.assertIn('href = "admissions/website-fixture"', html)
		self.assertIn('data-doctype="Student Admission"', html)
		self.assertEqual(query.call_args.kwargs["filters"]["published"], 1)

	def test_admissions_page_preserves_native_pagination(self):
		rows = [
			frappe._dict(
				name=f"Website fixture {index}",
				title=f"Website fixture {index}",
				academic_year="2026",
				modified=today(),
				admission_start_date=today(),
				admission_end_date=add_days(today(), 10),
				route=f"admissions/website-fixture-{index}",
			)
			for index in range(21)
		]
		with patch.object(student_admission, "get_admission_list", return_value=rows) as query:
			response = self.render("/admissions")
		html = response.get_data(as_text=True)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(query.call_args.kwargs["limit_page_length"], 21)
		self.assertIn('href = "admissions/website-fixture-19"', html)
		self.assertNotIn('href = "admissions/website-fixture-20"', html)
		self.assertNotIn("more-block py-6 d-none", html)
