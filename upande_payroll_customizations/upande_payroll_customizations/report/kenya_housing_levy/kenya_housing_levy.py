# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _


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
            "fieldtype": "Data",
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
            "fieldtype": "currency",
            "width": 150
        }
    ]


def get_data(filters):
    """Fetch Housing Levy data from Salary Slips joined with Employee"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    salary_details = frappe.qb.DocType("Salary Detail")

    # Build query - employee_number is now a string (PK29, PK30, etc.)
    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .inner_join(salary_details).on(salary_slip.name == salary_details.parent)
        .select(
            employee.employee_number.as_("employee_number"),  # Keep as string
            employee.employee_name.as_("full_name"),
            employee.custom_national_id.as_("custom_national_id"),
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

    # Sort by employee_number as string (will sort alphabetically: PK1, PK10, PK2, PK29, PK3, PK30)
    # For better numeric sorting, extract the number part
    query = query.orderby(employee.employee_number)

    data = query.run(as_dict=True)
    
    # Optional: Sort data by numeric part of employee_number for better ordering
    # This ensures PK1, PK2, PK3, ... PK10, ... PK29, PK30
    def get_numeric_part(emp_num):
        if emp_num:
            import re
            match = re.search(r'\d+', emp_num)
            return int(match.group()) if match else 0
        return 0
    
    data.sort(key=lambda x: get_numeric_part(x.get('employee_number')))
    
    return data
