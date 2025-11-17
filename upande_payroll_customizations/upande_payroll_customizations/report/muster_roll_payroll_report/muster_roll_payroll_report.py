# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
    """Main execution function for Payroll Muster Roll Report"""
    if filters and filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("To Date cannot be before From Date: {}").format(filters.to_date))

    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data


def get_columns(filters):
    """Define report columns - Employee info + Earnings + Deductions"""
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

    # Define the order of earnings components
    earnings_order = [
        "Basic salary",
        "Cash Housing Allowance",
        "Travel Allowance"
    ]

    # Define the order of deduction components
    deduction_order = [
        "Housing Levy",
        "NSSF TIER 1",
        "NSSF TIER2",
        "SHIF",
        "PAYE"
    ]

    # Get all unique earnings and deduction components
    earnings_components = get_earnings_components(filters)
    deduction_components = get_deduction_components(filters)
    
    # Sort earnings components
    ordered_earnings = []
    remaining_earnings = []
    
    for component in earnings_components:
        if component in earnings_order:
            ordered_earnings.append(component)
        else:
            remaining_earnings.append(component)
    
    ordered_earnings.sort(key=lambda x: earnings_order.index(x))
    final_earnings = ordered_earnings + sorted(remaining_earnings)
    
    # Add earnings columns
    for component in final_earnings:
        base_columns.append({
            "label": _(component),
            "fieldname": component.lower().replace(" ", "_"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150
        })

    # Add Gross Pay column
    base_columns.append({
        "label": _("Gross Pay"),
        "fieldname": "gross_pay",
        "fieldtype": "Float",
        "precision": 2,
        "width": 150
    })

    # Sort deduction components
    ordered_deductions = []
    remaining_deductions = []
    
    for component in deduction_components:
        if component in deduction_order:
            ordered_deductions.append(component)
        else:
            remaining_deductions.append(component)
    
    ordered_deductions.sort(key=lambda x: deduction_order.index(x))
    # Remove NSSF TIER 1 and TIER2 from display, add only NSSF
    final_deductions = [c for c in (ordered_deductions + sorted(remaining_deductions)) if c not in ["NSSF TIER 1", "NSSF TIER2"]]
    # Insert NSSF after Housing Levy if not already there
    if "NSSF" not in final_deductions and any(c in deduction_components for c in ["NSSF TIER 1", "NSSF TIER2"]):
        if "Housing Levy" in final_deductions:
            idx = final_deductions.index("Housing Levy") + 1
            final_deductions.insert(idx, "NSSF")
    
    # Add deduction columns
    for component in final_deductions:
        if component != "Total Statutory":
            base_columns.append({
                "label": _(component),
                "fieldname": component.lower().replace(" ", "_"),
                "fieldtype": "Float",
                "precision": 2,
                "width": 150
            })

    # Find PAYE index and insert Total Statutory right after it
    paye_index = None
    for i, col in enumerate(base_columns):
        if col.get("fieldname") == "paye":
            paye_index = i
            break
    
    if paye_index is not None:
        base_columns.insert(paye_index + 1, {
            "label": _("Total Statutory"),
            "fieldname": "total_statutory",
            "fieldtype": "Float",
            "precision": 2,
            "width": 150
        })
    
    # Add Total Deductions column
    base_columns.append({
        "label": _("Total Deductions"),
        "fieldname": "total_deductions",
        "fieldtype": "Float",
        "precision": 2,
        "width": 150
    })

    # Add Net Pay column
    base_columns.append({
        "label": _("Net Pay"),
        "fieldname": "net_pay",
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


def get_deduction_components(filters):
    """Get all unique deduction components based on filters"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    deductions = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.from_(deductions)
        .inner_join(salary_slip).on(deductions.parent == salary_slip.name)
        .select(deductions.salary_component)
        .distinct()
        .where(deductions.parentfield == "deductions")
    )

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
    """Fetch all payroll data and create muster roll"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    earnings = frappe.qb.DocType("Salary Detail")
    deductions = frappe.qb.DocType("Salary Detail")

    # Get earnings data
    earnings_query = (
        frappe.qb.from_(earnings)
        .inner_join(salary_slip).on(earnings.parent == salary_slip.name)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .select(
            employee.employee_number.as_("employee_number"),
            employee.employee_name.as_("employee_name"),
            earnings.salary_component.as_("salary_component"),
            earnings.amount.as_("amount"),
            salary_slip.gross_pay.as_("gross_pay"),
            salary_slip.net_pay.as_("net_pay")
        )
        .where(earnings.parentfield == "earnings")
        .where(earnings.salary_component != "Gross Pay")
        .where(earnings.salary_component != "Gross Salary")
    )

    if filters:
        if filters.get("from_date"):
            earnings_query = earnings_query.where(salary_slip.start_date >= filters.get("from_date"))
        if filters.get("to_date"):
            earnings_query = earnings_query.where(salary_slip.end_date <= filters.get("to_date"))
        if filters.get("company"):
            earnings_query = earnings_query.where(salary_slip.company == filters.get("company"))
        if filters.get("docstatus"):
            docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
            earnings_query = earnings_query.where(salary_slip.docstatus == docstatus_map[filters.get("docstatus")])

    earnings_rows = earnings_query.run(as_dict=True)

    # Get deductions data
    deductions_query = (
        frappe.qb.from_(deductions)
        .inner_join(salary_slip).on(deductions.parent == salary_slip.name)
        .inner_join(employee).on(salary_slip.employee == employee.name)
        .select(
            employee.employee_number.as_("employee_number"),
            deductions.salary_component.as_("salary_component"),
            deductions.amount.as_("amount")
        )
        .where(deductions.parentfield == "deductions")
    )

    if filters:
        if filters.get("from_date"):
            deductions_query = deductions_query.where(salary_slip.start_date >= filters.get("from_date"))
        if filters.get("to_date"):
            deductions_query = deductions_query.where(salary_slip.end_date <= filters.get("to_date"))
        if filters.get("company"):
            deductions_query = deductions_query.where(salary_slip.company == filters.get("company"))
        if filters.get("docstatus"):
            docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
            deductions_query = deductions_query.where(salary_slip.docstatus == docstatus_map[filters.get("docstatus")])

    deductions_rows = deductions_query.run(as_dict=True)

    # Organize data by employee
    employee_data = {}

    # Process earnings
    for row in earnings_rows:
        emp_key = row.employee_number
        if emp_key not in employee_data:
            employee_data[emp_key] = {
                "employee_number": row.employee_number,
                "full_name": row.employee_name,
                "gross_pay": row.gross_pay,
                "net_pay": row.net_pay,
                "total_deductions": 0,
                "total_statutory": 0
            }
        
        component_fieldname = row.salary_component.lower().replace(" ", "_")
        employee_data[emp_key][component_fieldname] = float(row.amount)

    # Process deductions
    for row in deductions_rows:
        emp_key = row.employee_number
        if emp_key not in employee_data:
            employee_data[emp_key] = {
                "employee_number": row.employee_number,
                "total_deductions": 0,
                "total_statutory": 0
            }

        # Combine NSSF tiers
        if row.salary_component in ["NSSF TIER 1", "NSSF TIER2"]:
            component_fieldname = "nssf"
            if component_fieldname not in employee_data[emp_key]:
                employee_data[emp_key][component_fieldname] = 0.00
            employee_data[emp_key][component_fieldname] += float(row.amount)
        else:
            component_fieldname = row.salary_component.lower().replace(" ", "_")
            employee_data[emp_key][component_fieldname] = float(row.amount)

        employee_data[emp_key]["total_deductions"] += float(row.amount)
        
        # Statutory deductions: Housing Levy, NSSF, SHIF, PAYE
        if row.salary_component in ["Housing Levy", "NSSF TIER 1", "NSSF TIER2", "SHIF", "PAYE"]:
            employee_data[emp_key]["total_statutory"] += float(row.amount)

    # Get all earnings and deductions components for initialization
    earnings_components = get_earnings_components(filters)
    deduction_components = get_deduction_components(filters)

    # Initialize all components with 0.00 for all employees
    for emp in employee_data.values():
        for component in earnings_components:
            component_fieldname = component.lower().replace(" ", "_")
            if component_fieldname not in emp:
                emp[component_fieldname] = 0.00

        for component in deduction_components:
            if component not in ["NSSF TIER 1", "NSSF TIER2"]:
                component_fieldname = component.lower().replace(" ", "_")
                if component_fieldname not in emp:
                    emp[component_fieldname] = 0.00
        
        # Ensure NSSF is initialized
        if "nssf" not in emp:
            emp["nssf"] = 0.00

    # Convert to list and format all values to 2 decimal places
    data = []
    for emp in employee_data.values():
        for key in emp:
            if key not in ["employee_number", "full_name"]:
                emp[key] = round(float(emp[key]), 2)
        data.append(emp)
    
    return data