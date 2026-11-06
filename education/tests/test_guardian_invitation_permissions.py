import unittest
from unittest.mock import Mock, patch

import frappe

from education.education.doctype.guardian.guardian import invite_guardian


class TestGuardianInvitationPermissions(unittest.TestCase):
	def test_guardian_read_and_write_are_required_before_account_lookup(self):
		doc = Mock(email_address="family@example.invalid")
		doc.check_permission.side_effect = [None, frappe.PermissionError("Denied")]
		with patch.object(frappe, "get_doc", return_value=doc), patch.object(frappe, "get_value") as lookup:
			with self.assertRaises(frappe.PermissionError):
				invite_guardian("GUARDIAN")
		lookup.assert_not_called()

	def test_new_user_uses_native_insert_permission(self):
		guardian = Mock(email_address="family@example.invalid", guardian_name="Family")
		user = Mock()
		user.insert.side_effect = frappe.PermissionError("User creation denied")
		with (
			patch.object(frappe, "get_doc", side_effect=[guardian, user]),
			patch.object(frappe, "get_value", return_value=None),
		):
			with self.assertRaises(frappe.PermissionError):
				invite_guardian("GUARDIAN")
		user.insert.assert_called_once_with()

	def test_existing_account_requires_native_read_permission(self):
		guardian = Mock(email_address="family@example.invalid")
		user = Mock()
		user.check_permission.side_effect = frappe.PermissionError("User read denied")
		with (
			patch.object(frappe, "get_doc", side_effect=[guardian, user]),
			patch.object(frappe, "get_value", return_value="family@example.invalid"),
		):
			with self.assertRaises(frappe.PermissionError):
				invite_guardian("GUARDIAN")
		user.check_permission.assert_called_once_with("read")
