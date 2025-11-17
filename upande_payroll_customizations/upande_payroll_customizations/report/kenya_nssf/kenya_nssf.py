# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _

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
            "label": _("PAYROLL NUMBER"),
            "fieldname": "employee_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("SURNAME"),
            "fieldname": "last_name",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("OTHER NAMES"),
            "fieldname": "first_and_middle_name",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("ID NO"),
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
            "label": _("NSSF NO"),
            "fieldname": "custom_nssf_number",
            "fieldtype": "Data",
            "width": 150
        },

        {
            "label": _("GROSS PAY"),
            
            "width": 150
        },
        {
            "label": _("VOLUNTARY"),
            "fieldtype": "Data",
            "width": 150
        }

    ]


def get_data(filters):
    """Fetch employee NSSF data with voluntary hardcoded to 0"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")

    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .select(
            employee.employee_number.as_("employee_number"),
            employee.employee_name.as_("full_name"),
            employee.custom_national_id.as_("custom_national_id"),
            employee.custom_kra_pin.as_("custom_kra_pin"),
            employee.custom_nssf_number.as_("custom_nssf_number"),
            salary_slip.gross_pay.as_("gross_pay")
        )
    )

    # Apply filters
    if filters.get("from_date"):
        query = query.where(salary_slip.start_date >= filters.get("from_date"))
    if filters.get("to_date"):
        query = query.where(salary_slip.end_date <= filters.get("to_date"))
    if filters.get("company"):
        query = query.where(salary_slip.company == filters.get("company"))
    if filters.get("docstatus"):
        doc_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
        query = query.where(salary_slip.docstatus == doc_map[filters.get("docstatus")])

    result_rows = query.run(as_dict=True)

    # Prepare report-ready data
    data = []
    for row in result_rows:
        data.append({
            "employee_number": row.employee_number,
            "last_name": row.full_name.split(" ")[-1],
            "first_and_middle_name": " ".join(row.full_name.split(" ")[:-1]),
            "custom_national_id": row.custom_national_id,
            "custom_kra_pin": row.custom_kra_pin,
            "custom_nssf_number": row.custom_nssf_number,
            "gross_pay": row.gross_pay or 0.0,
            "voluntary": 0.0  
        })

    return data
