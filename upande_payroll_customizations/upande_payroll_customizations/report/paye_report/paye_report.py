# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

# import frappe

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
            "label": _("PAYE Deduction"),
            "fieldname": "amount",
            "fieldtype": "currency",
            "width": 150
        }
    ]


def get_data(filters):
    """Fetch PAYE data including employees with zero deduction"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    salary_details = frappe.qb.DocType("Salary Detail")

    # Left join so employees without PAYE still appear
    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .left_join(salary_details)
        .on(
            (salary_slip.name == salary_details.parent) &
            (salary_details.salary_component == "PAYE")
        )
        .select(
            employee.custom_national_id.as_("custom_national_id"),
            employee.employee_name.as_("full_name"),
            employee.employee_number.as_("employee_number"),
            employee.custom_kra_pin.as_("custom_kra_pin"),
            salary_details.amount.as_("amount")
        )
        .where(salary_slip.docstatus == 1)
    )

    # Apply filters
    if filters:
        if filters.get("from_date"):
            query = query.where(salary_slip.start_date >= filters.get("from_date"))
        if filters.get("to_date"):
            query = query.where(salary_slip.end_date <= filters.get("to_date"))
        if filters.get("company"):
            query = query.where(salary_slip.company == filters.get("company"))

    data = query.run(as_dict=True)

    # Replace None amounts with 0
    for row in data:
        if row["amount"] is None:
            row["amount"] = 0

    return data
