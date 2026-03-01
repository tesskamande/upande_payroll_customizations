# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
    if filters and filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("To Date cannot be before From Date"))

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("PAYROLL NO"),
            "fieldname": "employee_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("FIRSTNAME"),
            "fieldname": "first_and_middle_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("LASTNAME"),
            "fieldname": "last_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("ID NUMBER"),
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
            "label": _("SHIF DEDUCTION"),
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
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    salary_detail = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .inner_join(salary_detail).on(salary_slip.name == salary_detail.parent)
        .select(
            employee.employee_number.as_("employee_number"),
            employee.employee_name.as_("employee_name"),
            employee.last_name.as_("last_name"),
            employee.custom_national_id.as_("custom_national_id"),
            employee.custom_kra_pin.as_("custom_kra_pin"),
            employee.custom_shif_number.as_("custom_shif_number"),
            employee.custom_nhif_number.as_("custom_nhif_number"),
            employee.cell_number.as_("cell_number"),
            salary_detail.amount.as_("amount")
        )
        .where(
            (salary_detail.salary_component == "SHIF") &
            (salary_detail.amount != 0)
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

    data = []
    for row in result_rows:
        
        if row.employee_name and row.last_name:
            first_and_middle = row.employee_name.replace(row.last_name, "").strip()
        else:
            first_and_middle = row.employee_name

    
        nhif_display_number = row.custom_shif_number or row.custom_nhif_number

        data.append({
            "employee_number": row.employee_number,
            "first_and_middle_name": first_and_middle,
            "last_name": row.last_name,
            "custom_national_id": row.custom_national_id,
            "custom_kra_pin": row.custom_kra_pin,
            "custom_nhif_number": nhif_display_number,
            "amount": row.amount,
            "cell_number": row.cell_number
        })

    return data
