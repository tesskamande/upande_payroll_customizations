# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    if filters and filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("From Date cannot be greater than To Date"))

    return get_columns(), get_p10_report_data(filters)


def get_columns():
    """Sheet B columns for P10A Tax Deduction Card (KRA July 2025 format)"""
    columns = [
        {
            "fieldname": "pin",
            "label": _("PIN"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "residence_status",
            "label": _("Residence Status"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "total_cash_pay",
            "label": _("Total Cash Pay"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "value_of_car_benefit",
            "label": _("Value of Car Benefit"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "value_of_housing",
            "label": _("Value of Housing"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "value_of_meals",
            "label": _("Value of Meals"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "benefits_description",
            "label": _("Benefits Description"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "value_of_other_benefits",
            "label": _("Value of Other Benefits"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "mortgage_interest",
            "label": _("Mortgage Interest"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "nssf_contribution",
            "label": _("NSSF Contribution"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "prmf_contribution",
            "label": _("PRMF Contribution"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "shif_contribution",
            "label": _("SHIF Contribution"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "affordable_housing_levy",
            "label": _("Affordable Housing Levy"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "insurance_relief",
            "label": _("Insurance Relief"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "personal_relief",
            "label": _("Personal Relief"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
        {
            "fieldname": "paye_tax",
            "label": _("PAYE Tax"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150,
        },
    ]
    return columns


def get_p10_report_data(filters):
    salary_slip = frappe.qb.DocType("Salary Slip")
    employee = frappe.qb.DocType("Employee")
    salary_detail = frappe.qb.DocType("Salary Detail")

    # Define component mappings aligned to Sheet B
    component_mappings = {
        # Total Cash Pay (aggregated)
        "total_cash_pay": ["Basic Pay", "House Allowance", "Transport Allowance", 
                          "Chemical Allowance", "Cold Room Allowance", "Grading Bonus", 
                          "Loading Allowance", "Holiday Overtime", "Overtime", "Responsibility Allowance", 
                          "Travelling Allowance", "Absence Amount"],
        
        # Deductions
        "mortgage_interest": ["Mortgage Interest"],
        "nssf_contribution": ["NSSF Tier 1", "NSSF Tier 2"],
        "prmf_contribution": ["PRMF Contribution", "Registered Pension Fund"],
        "shif_contribution": ["SHIF"],
        "affordable_housing_levy": ["Housing Levy"],
        "insurance_relief": ["Insurance Relief"],
        "paye_tax": ["PAYE"],
    }

    # Build query
    query = (
        frappe.qb.from_(salary_slip)
        .inner_join(employee).on(employee.name == salary_slip.employee)
        .inner_join(salary_detail).on(salary_slip.name == salary_detail.parent)
        .select(
            employee.employee_number,
            employee.employee_name,
            employee.custom_kra_pin,
            salary_detail.salary_component,
            salary_detail.amount,
            salary_detail.parentfield
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
        else:
            query = query.where(salary_slip.docstatus == 1)

    query = query.orderby(salary_slip.employee)
    data = query.run(as_dict=True)

    # Organize data by employee
    employee_data = {}
    for row in data:
        emp_key = row["employee_number"]
        
        if emp_key not in employee_data:
            employee_data[emp_key] = {
                "pin": row["custom_kra_pin"],
                "employee_name": row["employee_name"],
                "residence_status": "Resident",
                "total_cash_pay": 0,
                "value_of_car_benefit": 0,
                "value_of_housing": 0,
                "value_of_meals": 0,
                "benefits_description": "",
                "value_of_other_benefits": 0,
                "mortgage_interest": 0,
                "nssf_contribution": 0,
                "prmf_contribution": 0,
                "shif_contribution": 0,
                "affordable_housing_levy": 0,
                "insurance_relief": 0,
                "personal_relief": 2400.00,
                "paye_tax": 0,
            }

        component = row["salary_component"]
        amount = float(row["amount"]) if row["amount"] else 0

        # Map components to fields
        for field, components in component_mappings.items():
            if component in components:
                employee_data[emp_key][field] += amount
                break

    # Convert to list and round all values
    report_data = []
    for emp_key, emp_details in employee_data.items():
        # Determine if benefits were given
        if (emp_details["value_of_car_benefit"] > 0 or
            emp_details["value_of_housing"] > 0 or 
            emp_details["value_of_meals"] > 0 or 
            emp_details["value_of_other_benefits"] > 0):
            emp_details["benefits_description"] = "Benefit given"
        else:
            emp_details["benefits_description"] = "Benefit not given"
        
        # Round all numeric values to 2 decimal places
        for key in emp_details:
            if isinstance(emp_details[key], (int, float)):
                emp_details[key] = round(emp_details[key], 2)
        report_data.append(emp_details)

    return report_data