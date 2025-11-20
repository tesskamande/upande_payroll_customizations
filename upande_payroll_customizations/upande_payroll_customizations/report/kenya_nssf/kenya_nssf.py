# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
import re


def execute(filters=None):
    
    columns = get_columns()

    if not filters:
        frappe.throw(_("Please set filters before generating the report"))

    if filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("To Date cannot be before From Date: {}").format(filters.to_date))

    data = get_data(filters)
    return columns, data


def get_columns():
    """Define report columns"""
    return [
        {
            "label": _("Payroll No"),
            "fieldname": "employee_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Employee Name"),
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
            "label": _("NSSF Number"),
            "fieldname": "custom_nssf_number",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("GROSS PAY"),
            "fieldname": "gross_pay",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("VOLUNTARY"),
            "fieldname": "voluntary",
            "fieldtype": "Currency",
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
    """Fetch NSSF data from Salary Slips joined with Employee and sum Tier 1 & Tier 2"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    salary_details = frappe.qb.DocType("Salary Detail")

    # Fetch Tier 1 and Tier 2 amounts
    nssf_data = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .inner_join(salary_details).on(salary_slip.name == salary_details.parent)
        .select(
            employee.employee_number.as_("employee_number"),
            employee.employee_name.as_("full_name"),
            employee.custom_national_id.as_("custom_national_id"),
            employee.custom_kra_pin.as_("custom_kra_pin"),
            employee.custom_nssf_number.as_("custom_nssf_number"),
            salary_details.salary_component.as_("component"),
            salary_details.amount.as_("amount")
        )
        .where(
            (salary_details.salary_component.isin(["NSSF Tier 1", "NSSF Tier2"]))
            
        )
    )

    # Apply filters
    if filters:
        if filters.get("from_date"):
            query = nssf_data.where(salary_slip.start_date >= filters.get("from_date"))
        if filters.get("to_date"):
            query = nssf_data.where(salary_slip.end_date <= filters.get("to_date"))
        if filters.get("company"):
            query = nssf_data.where(salary_slip.company == filters.get("company"))
        if filters.get("docstatus"):
            docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
            query = nssf_data.where(salary_slip.docstatus == docstatus_map[filters.get("docstatus")])

    query = query.orderby(employee.employee_number)
    result_rows = query.run(as_dict=True)

    # Sum Tier 1 + Tier 2 per employee
    totals = {}
    for row in result_rows:
        # Split name into surname and other names
        name_parts = row.full_name.split(" ") if row.full_name else ["", ""]
        last_name = name_parts[-1] if len(name_parts) > 0 else ""
        first_and_middle = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""
        
        data.append({
            "employee_number": row.employee_number,
            "last_name": last_name,
            "first_and_middle_name": first_and_middle,
            "custom_national_id": row.custom_national_id,
            "custom_kra_pin": row.custom_kra_pin,
            "custom_nssf_number": row.custom_nssf_number,
            "gross_pay": row.gross_pay or 0.0,
            "voluntary": 0.0  
        })
    
    # Sort by numeric part of employee_number for proper ordering (PK1, PK2, ... PK29, PK30)
    data.sort(key=lambda x: get_numeric_part(x.get('employee_number')))

    return data
