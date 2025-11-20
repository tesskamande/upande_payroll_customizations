# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from pypika.functions import Cast

def execute(filters=None):
    """Main execution function for Payroll Earnings Report"""
    if filters and filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("To Date cannot be before From Date: {}").format(filters.to_date))

    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data


def get_columns(filters):
    """Define report columns - Employee info + Dynamic earnings components"""
    base_columns = [
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
        }
    ]

    # Define the order of components
    component_order = [
        "Basic salary",
        "Cash Housing Allowance",
        "Travel Allowance"
    ]

    # Get all unique earning components
    earnings_components = get_earnings_components(filters)
    
    # Sort components: ordered ones first, then the rest alphabetically
    ordered_components = []
    remaining_components = []
    
    for component in earnings_components:
        if component in component_order:
            ordered_components.append(component)
        else:
            remaining_components.append(component)
    
    # Sort ordered components by their position in component_order
    ordered_components.sort(key=lambda x: component_order.index(x))
    
    # Combine: ordered components + alphabetically sorted remaining
    final_components = ordered_components + sorted(remaining_components)
    
    # Add columns for each component
    for component in final_components:
        base_columns.append({
            "label": _(component),
            "fieldname": component.lower().replace(" ", "_"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150
        })

    # Add Gross Pay column at the end
    base_columns.append({
        "label": _("GROSS PAY"),
        "fieldname": "gross_pay",
        "fieldtype": "Float",
        "precision": 2,
        "width": 150
    })

    return base_columns


def get_earnings_components(filters):
    """Get all unique earning components based on filters"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    earnings = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.from_(earnings)
        .inner_join(salary_slip).on(earnings.parent == salary_slip.name)
        .select(earnings.salary_component)
        .distinct()
        .where(earnings.parentfield == "earnings")
        .where(earnings.salary_component != "Gross Pay")
        .where(earnings.salary_component != "Gross Salary")
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

    result = query.run(as_dict=True)
    return [row.salary_component for row in result]


def get_data(filters):
    """Fetch Earnings and pivot horizontally"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    earnings = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.from_(earnings)
        .inner_join(salary_slip).on(earnings.parent == salary_slip.name)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .select(
            employee.employee_number.as_("employee_number"),
            employee.employee_name.as_("employee_name"),
            earnings.salary_component.as_("salary_component"),
            earnings.amount.as_("amount"),
            salary_slip.gross_pay.as_("gross_pay")
        )
        .where(earnings.parentfield == "earnings")
        .where(earnings.salary_component != "Gross Pay")
        .where(earnings.salary_component != "Gross Salary")
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

    query = query.orderby(Cast(employee.employee_number, "int"))

    result_rows = query.run(as_dict=True)

    # Get all earnings components
    earnings_components = get_earnings_components(filters)

    # Pivot data - group by employee and create columns for each component
    employee_data = {}
    for row in result_rows:
        emp_key = row.employee_number
        
        if emp_key not in employee_data:
            employee_data[emp_key] = {
                "employee_number": row.employee_number,
                "full_name": row.employee_name,
                "gross_pay": row.gross_pay
            }
            # Initialize all components with 0.00
            for component in earnings_components:
                component_fieldname = component.lower().replace(" ", "_")
                employee_data[emp_key][component_fieldname] = 0.00
        
        # Add component amount to employee record
        component_fieldname = row.salary_component.lower().replace(" ", "_")
        employee_data[emp_key][component_fieldname] = float(row.amount)

    # Convert to list and format all values to 2 decimal places
    data = []
    for emp in employee_data.values():
        for key in emp:
            if key not in ["employee_number", "full_name"]:
                emp[key] = round(float(emp[key]), 2)
        data.append(emp)
    
    return data