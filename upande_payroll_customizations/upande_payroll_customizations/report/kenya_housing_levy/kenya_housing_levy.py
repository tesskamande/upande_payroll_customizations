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
            "label": _("Payroll No"), 
            "fieldname": "employee_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("ID Number"), 
            "fieldname": "custom_national_id", 
            "fieldtype": "Data", 
            "width": 150
        },
        {
            "label": _("Employee Name"), 
            "fieldname": "employee_name", 
            "fieldtype": "Data", 
            "width": 250
        },
        {
            "label": _("KRA PIN"), 
            "fieldname": "custom_kra_pin", 
            "fieldtype": "Data", 
            "width": 150
        },
        {
            "label": _("Gross Salary"), 
            "fieldname": "gross_salary", 
            "fieldtype": "Currency", 
            "width": 150
        },
        {
            "label": _("Basic Salary"), 
            "fieldname": "basic_salary", 
            "fieldtype": "Currency", 
            "width": 150
        },
        {
            "label": _("Member Contribution"), 
            "fieldname": "member_contribution", 
            "fieldtype": "Currency", 
            "width": 150
        },
        {
            "label": _("Employer Contribution"), 
            "fieldname": "employer_contribution", 
            "fieldtype": "Currency", 
            "width": 150
        },
        {
            "label": _("Total Contribution"), 
            "fieldname": "total_contribution", 
            "fieldtype": "Currency", 
            "width": 150
        },
    ]


def get_data(filters):
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    sd = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .left_join(sd).on(
            (salary_slip.name == sd.parent) & 
            (sd.parenttype == "Salary Slip")
        )
        .select(
            salary_slip.name.as_("salary_slip_name"),
            employee.employee_number.as_("employee_number"),
            employee.employee_name.as_("employee_name"),
            employee.custom_national_id.as_("custom_national_id"),
            employee.custom_kra_pin.as_("custom_kra_pin"),
            salary_slip.gross_pay.as_("gross_pay"),
            sd.salary_component.as_("salary_component"),
            sd.amount.as_("amount"),
           
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
        if filters.get("employee"):
            query = query.where(salary_slip.employee == filters.get("employee"))
        if filters.get("docstatus"):
            docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
            query = query.where(salary_slip.docstatus == docstatus_map.get(filters.get("docstatus"), 1))

    # Order by employee for better grouping
    query = query.orderby(employee.employee_number)

    rows = query.run(as_dict=True)

    # Group data by employee
    result = {}
    for r in rows:
        key = r.employee_number

        if key not in result:
            result[key] = {
                "employee_number": r.employee_number,
                "custom_national_id": r.custom_national_id,
                "employee_name": r.employee_name,
                "custom_kra_pin": r.custom_kra_pin,
                "gross_salary": r.gross_pay or 0,
                "basic_salary": 0,
                "member_contribution": 0,
                "employer_contribution": 0,
                "total_contribution": 0,
            }

        # Process salary components
        if r.salary_component == "Basic Pay":
            result[key]["basic_salary"] += r.amount or 0

        # EMPLOYEE HOUSING LEVY (Regular Deduction)
        elif r.salary_component == "Housing Levy":
            result[key]["member_contribution"] += r.amount or 0

        # EMPLOYER HOUSING LEVY (Statistical Component)
        elif r.salary_component == "Employer Housing Levy":
            result[key]["employer_contribution"] += r.amount or 0

    # Convert to list and calculate totals
    data = []
    for row in result.values():
        # Calculate total contribution
        row["total_contribution"] = row["member_contribution"] + row["employer_contribution"]
        
        # Only add rows that have some contribution data
        if row["member_contribution"] > 0 or row["employer_contribution"] > 0:
            data.append(row)

    return data