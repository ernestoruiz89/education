# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import IfNull

from education.education.doctype.building.building import get_building_location, validate_building_type
from education.education.doctype.campus.campus import validate_campus
from education.education.doctype.facility.facility import validate_facilities
from education.education.doctype.floor.floor import validate_floor_in_building
from education.education.doctype.student_batch_name.student_batch_name import get_batch_occupancy


def get_batch_seat_requirement(student_batch):
	"""Plan for configured seats and already occupied/reserved places."""
	from frappe.utils import cint

	maximum = cint(frappe.db.get_value("Student Batch Name", student_batch, "max_strength"))
	return max(maximum, get_batch_occupancy(student_batch))


def validate_academic_room_capacity(doc):
	"""Classes and assessments must fit their group's planned capacity."""
	from frappe.utils import cint

	if not doc.get("room") or not doc.get("student_batch") or doc.docstatus == 2:
		return
	capacity = cint(frappe.db.get_value("Room", doc.room, "seating_capacity"))
	if not capacity:
		return
	required = get_batch_seat_requirement(doc.student_batch)
	if required > capacity:
		frappe.throw(
			_("Room {0} seats {1}, but Batch {2} requires {3} places.").format(
				frappe.bold(doc.room), capacity, frappe.bold(doc.student_batch), required
			)
		)


class Room(Document):
	def validate(self):
		self.set_location_from_building()
		validate_campus(self, required=True)
		validate_facilities(self, self.campus)
		validate_floor_in_building(self)

	def set_location_from_building(self):
		if not self.building:
			return

		building = get_building_location(self.building)
		if building.disabled and self.has_value_changed("building"):
			frappe.throw(_("Building {0} is disabled.").format(frappe.bold(self.building)))
		validate_building_type(self.building, building, "Academic")
		# The building is the source of truth for where the room is.
		self.company = building.company
		if building.campus:
			self.campus = building.campus


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def room_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict[str, Any],
):
	"""Enabled rooms on the selected campus, plus rooms shared across campuses."""
	filters = filters or {}
	room = frappe.qb.DocType("Room")
	query = (
		frappe.qb.get_query("Room", fields=["name", "room_name"], ignore_permissions=False)
		.where(room.disabled == 0)
		.where(room.name.like(f"%{txt}%") | room.room_name.like(f"%{txt}%"))
		.orderby(room.room_name)
		.limit(page_len)
		.offset(start)
	)

	campus = filters.get("campus")
	if campus:
		query = query.where((IfNull(room.campus, "") == "") | (room.campus == campus))

	return query.run()
