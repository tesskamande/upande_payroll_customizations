# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _


def execute(filters=None):
    """Main execution function for the Bank Payment Remittance report"""
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
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("ID No"),
            "fieldname": "custom_national_id",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Bank"),
            "fieldname": "bank_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Bank Account No"),
            "fieldname": "bank_ac_no",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 120
        }
    ]


def get_data(filters):
    """Fetch salary slip data joined with Employee data using aliases"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")

    # Build query with aliases
    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee)
        .on(salary_slip.employee == employee.name)
        .select(
            employee.employee_number.as_("employee_number"),
            employee.employee_name.as_("employee_name"),
            employee.custom_national_id.as_("custom_national_id"),
            employee.bank_name.as_("bank_name"),
            employee.bank_ac_no.as_("bank_ac_no"),
            salary_slip.net_pay.as_("amount")
        )
        .where(salary_slip.docstatus == 1)  # Only submitted salary slips
    )

    # Apply filters
    if filters:
        if filters.get("from_date"):
            query = query.where(salary_slip.start_date >= filters.get("from_date"))
        if filters.get("to_date"):
            query = query.where(salary_slip.end_date <= filters.get("to_date"))
        if filters.get("company"):
            query = query.where(salary_slip.company == filters.get("company"))
        if filters.get("bank"):
            query = query.where(employee.bank_name == filters.get("bank"))
        if filters.get("docstatus"):
            docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
            query = query.where(salary_slip.docstatus == docstatus_map[filters.get("docstatus")])


    salary_data = query.run(as_dict=True)

    # Map query results to report rows
    results = []
    for slip in salary_data:
        results.append({
            "employee_number": slip.employee_number,
            "employee_name": slip.employee_name,
            "custom_national_id": slip.custom_national_id,
            "bank_name": slip.bank_name,
            "bank_ac_no": slip.bank_ac_no,
            "amount": slip.amount
        })

    return results
