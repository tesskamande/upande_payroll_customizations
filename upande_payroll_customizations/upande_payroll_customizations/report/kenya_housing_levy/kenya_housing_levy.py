# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from pypika.functions import Cast


def execute(filters=None):
    """Main execution function for the Housing Levy report"""
    if filters and filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("To Date cannot be before From Date: {}").format(filters.to_date))

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    """Define report columns with original labels"""
    return [
        {
            "label": _("Payroll No"),
            "fieldname": "employee_number",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Employee"),
            "fieldname": "full_name",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("ID Number"),
            "fieldname": "custom_national_id",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("KRA PIN"),
            "fieldname": "custom_kra_pin",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Housing Levy Deduction"),
            "fieldname": "amount",
            "fieldtype": "Float",
            "precision": 2,
            "width": 150
        }
    ]


def get_data(filters):
    """Fetch Housing Levy data from Salary Slips joined with Employee"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    salary_details = frappe.qb.DocType("Salary Detail")

    # Build query with aliases
    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .inner_join(salary_details).on(salary_slip.name == salary_details.parent)
        .select(
            employee.custom_national_id.as_("custom_national_id"),
            employee.employee_name.as_("full_name"),
            Cast(employee.employee_number, "int").as_("employee_number"),
            employee.custom_kra_pin.as_("custom_kra_pin"),
            salary_details.amount.as_("amount")
        )
        .where(
            (salary_details.salary_component == "Housing Levy") &
            (salary_details.amount != 0)
        )
    )

    # Apply filters
    if filters:
        if filters.get("from_date"):
            query = query.where(salary_slip.start_date >= filters.get("from_date"))
        if filters.get("to_date"):
            query = query.where(salary_slip.end_date <= filters.get("to_date"))
        if filters.get("company"):
            query = query.where(salary_slip.company == filters.get("company"))
        if filters.get("docstatus"):
            docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
            query = query.where(salary_slip.docstatus == docstatus_map[filters.get("docstatus")])

    # Add numeric sorting - THIS WAS MISSING
    query = query.orderby(Cast(employee.employee_number, "int"))

    data = query.run(as_dict=True)
    
    return data