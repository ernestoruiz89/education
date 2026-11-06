import frappe


def get_context(context):
	context.no_cache = 1
	abbr = frappe.db.get_single_value("Education Settings", "school_college_name_abbreviation")
	logo = frappe.db.get_single_value("Education Settings", "school_college_logo")
	context.abbr = abbr or "Frappe Education"
	context.logo = logo or "/favicon.png"
	context.lang = frappe.local.lang or "en"
	context.portal_boot = {
		"language": context.lang,
		"name": context.abbr,
		"logo": context.logo,
	}
