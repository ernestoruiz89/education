import unittest
from unittest.mock import Mock, patch

import frappe

from education.education.doctype.room import room


class TestAcademicRoomCapacity(unittest.TestCase):
	def test_planning_uses_configured_places_or_higher_existing_occupancy(self):
		for maximum, occupied, expected in ((12, 3, 12), (0, 6, 6), (4, 7, 7)):
			with (
				patch.object(frappe.db, "get_value", return_value=maximum),
				patch.object(room, "get_batch_occupancy", return_value=occupied),
			):
				self.assertEqual(room.get_batch_seat_requirement("GROUP"), expected)

	def test_insufficient_room_rejected_for_classes_and_assessments(self):
		for doctype in ("Subject Schedule", "Assessment Plan"):
			doc = frappe._dict(doctype=doctype, room="ROOM", student_batch="GROUP", docstatus=0)
			with (
				patch.object(frappe.db, "get_value", return_value=10),
				patch.object(room, "get_batch_seat_requirement", return_value=12),
			):
				with self.assertRaises(frappe.ValidationError):
					room.validate_academic_room_capacity(doc)

	def test_exact_capacity_and_unconfigured_capacity_are_allowed(self):
		doc = frappe._dict(room="ROOM", student_batch="GROUP", docstatus=0)
		for capacity in (0, 12, 20):
			with (
				patch.object(frappe.db, "get_value", return_value=capacity),
				patch.object(room, "get_batch_seat_requirement", return_value=12),
			):
				room.validate_academic_room_capacity(doc)

	def test_cancellation_and_unassigned_room_do_not_block_historical_records(self):
		for room_name, status in ((None, 0), ("ROOM", 2)):
			with patch.object(frappe.db, "get_value") as read:
				room.validate_academic_room_capacity(
					frappe._dict(room=room_name, student_batch="GROUP", docstatus=status)
				)
			read.assert_not_called()

	def test_native_slot_expansion_handles_year_boundary(self):
		from education.education.doctype.subject_scheduling_tool.subject_scheduling_tool import (
			SubjectSchedulingTool,
		)

		tool = frappe.get_doc(
			{
				"doctype": "Subject Scheduling Tool",
				"from_date": "2026-12-28",
				"to_date": "2027-01-03",
				"slots": [{"day": "Monday"}, {"day": "Wednesday"}],
			}
		)
		with patch.object(
			SubjectSchedulingTool, "make_subject_schedule", side_effect=lambda day, slot: str(day)
		):
			self.assertEqual(list(tool.iter_subject_schedules()), ["2026-12-28", "2026-12-30"])
