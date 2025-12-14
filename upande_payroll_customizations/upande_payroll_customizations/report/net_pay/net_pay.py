# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import re


def execute(filters=None):
    """Main execution function for Net Pay report"""
    if filters and filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("To Date cannot be before From Date: {}").format(filters.to_date))

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    """Define report columns with multiline labels"""
    return [
        {
            "label": _("PAYROLL NUMBER"),
            "fieldname": "employee_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("EMPLOYEE"),
            "fieldname": "full_name",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("GROSS PAY"),
            "fieldname": "gross_pay",
            "fieldtype": "Currency",
            "precision": 2,
            "width": 150
        },
        {
            "label": _("TOTAL DEDUCTIONS"),
            "fieldname": "total_deduction",
            "fieldtype": "Currency",
            "precision": 2,
            "width": 150
        },
        {
            "label": _("NET PAY"),
            "fieldname": "net_pay",
            "fieldtype": "Currency",
            "precision": 2,
            "width": 150
        }
    ]


def get_numeric_part(emp_num):
    """Extract numeric part from employee number for proper sorting"""
    if emp_num:
        match = re.search(r'\d+', str(emp_num))
        return int(match.group()) if match else 0
    return 0


def get_data(filters):
    """Fetch Net Pay, Gross Pay, and Total Deductions from Salary Slips"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")

    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .select(
            employee.employee_name.as_("employee_name"),
            employee.employee_number.as_("employee_number"),
            salary_slip.gross_pay.as_("gross_pay"),
            salary_slip.total_deduction.as_("total_deduction"),
            salary_slip.net_pay.as_("net_pay")
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

    
    query = query.orderby(employee.employee_number)
    result_rows = query.run(as_dict=True)

    # Process data
    data = []
    for row in result_rows:
        data.append({
            "employee_number": row.employee_number,
            "full_name": row.employee_name,
            "gross_pay": row.gross_pay or 0.0,
            "total_deduction": row.total_deduction or 0.0,
            "net_pay": row.net_pay or 0.0
        })

    # Sort by numeric part of employee_number for proper ordering (PK1, PK2, ... PK29, PK30)
    data.sort(key=lambda x: get_numeric_part(x.get('employee_number')))

    return data