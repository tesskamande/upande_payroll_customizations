# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()

    if not filters:
        frappe.throw(_("Please set filters before generating the report"))

    if filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("To Date cannot be before From Date"))

    data = get_data(filters)
    return columns, data


def get_columns():
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
            "fieldtype": "Int",
            "width": 120
        }
    ]


def get_data(filters):
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")

    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee)
        .on(salary_slip.employee == employee.name)
        .select(
            employee.employee_number.as_("employee_number"),
            employee.employee_name.as_("full_name"),
            employee.custom_national_id.as_("custom_national_id"),
            employee.custom_kra_pin.as_("custom_kra_pin"),
            employee.custom_nssf_number.as_("custom_nssf_number"),
            salary_slip.gross_pay.as_("gross_pay"),
            employee.custom_is_nssf_voluntary.as_("voluntary_raw")
        )
    )

    # Filters
    if filters.get("from_date"):
        query = query.where(salary_slip.start_date >= filters.get("from_date"))
    if filters.get("to_date"):
        query = query.where(salary_slip.end_date <= filters.get("to_date"))
    if filters.get("company"):
        query = query.where(salary_slip.company == filters.get("company"))
    if filters.get("docstatus"):
        docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
        query = query.where(
            salary_slip.docstatus == docstatus_map[filters.get("docstatus")]
        )

    query = query.orderby(employee.employee_number)

    rows = query.run(as_dict=True)

    data = []
    for row in rows:
        data.append({
            "employee_number": row.employee_number,
            "full_name": row.full_name,
            "custom_national_id": row.custom_national_id,
            "custom_kra_pin": row.custom_kra_pin,
            "custom_nssf_number": row.custom_nssf_number,
            "gross_pay": row.gross_pay or 0.0,
            "voluntary": 1 if str(row.voluntary_raw).lower() in ("1", "yes", "true") else 0
        })

    return data

