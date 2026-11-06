import unittest
from unittest.mock import patch

import frappe

from education.education.doctype.assessment_plan.assessment_plan import AssessmentPlan
from education.education.utils import OverlapError


class TestAssessmentScheduleConflicts(unittest.TestCase):
	def test_same_teacher_overlapping_other_group_and_room_is_rejected(self):
		doc = frappe.get_doc(
			{
				"doctype": "Assessment Plan",
				"faculty": "TEACHER",
				"student_batch": "NEW-GROUP",
				"room": "NEW-ROOM",
			}
		)

		def check(document, doctype, fieldname, value=None):
			if doctype == "Assessment Plan" and fieldname == "faculty":
				raise OverlapError("Teacher already assigned to an assessment")

		with patch("education.education.utils.validate_overlap_for", side_effect=check):
			with self.assertRaises(OverlapError):
				doc.validate_overlap()

	def test_no_teacher_does_not_conflict_with_other_unassigned_assessments(self):
		doc = frappe.get_doc({"doctype": "Assessment Plan", "student_batch": "GROUP"})
		with patch("education.education.utils.validate_overlap_for") as check:
			doc.validate_overlap()
		self.assertFalse(any(call.args[2] == "faculty" for call in check.call_args_list))
