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
            "label": _("PAYROLL NUMBER"),
            "fieldname": "employee_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("FIRSTNAME"),
            "fieldname": "first_and_middle_name",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("LASTNAME"),
            "fieldname": "last_name",
            "fieldtype": "Data",
            "width": 150
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
            "label": _("NHIF NO"),
            "fieldname": "custom_nhif_number",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("CONTRIBUTION AMOUNT"),
            "fieldname": "amount",
            "fieldtype": "Float",
            "precision": 2,
            "width": 150
        },
        {
            "label": _("PHONE"),
            "fieldname": "cell_number",
            "fieldtype": "Data",
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
            employee.last_name.as_("last_name"),
            employee.employee_name.as_("employee_name"),  # fetch full name
            employee.employee_number.as_("employee_number"),
            employee.custom_kra_pin.as_("custom_kra_pin"),
            employee.custom_nhif_number.as_("custom_nhif_number"),
            salary_details.amount.as_("amount"),
            employee.cell_number.as_("cell_number")
        )
        .where(
            (salary_details.salary_component == "SHIF") &
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

    result_rows = query.run(as_dict=True)

    # Split full name into first_and_middle_name and last_name
    data = []
    for row in result_rows:
        data.append({
            "custom_national_id": row.custom_national_id,
            "last_name": row.last_name,
            "first_and_middle_name": " ".join(row.employee_name.split(" ")[:-1]),
            "employee_number": row.employee_number,
            "custom_kra_pin": row.custom_kra_pin,
            "custom_nhif_number": row.custom_nhif_number,
            "amount": row.amount,
            "cell_number": row.cell_number
        })

    return data
