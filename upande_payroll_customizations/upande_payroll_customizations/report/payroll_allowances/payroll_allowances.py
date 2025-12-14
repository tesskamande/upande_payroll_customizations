from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
    """Main execution function for Payroll Allowances Report"""
    if filters and filters.get("from_date") and filters.get("to_date"):
        if filters.from_date > filters.to_date:
            frappe.throw(_("To Date cannot be before From Date"))

    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data


def get_columns(filters):
    """Employee info + Allowance components"""
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

    # Allowance order
    component_order = [
        "Basic Pay",
        "House Allowance",
        "Transport Allowance"
    ]

    allowance_components = get_allowance_components(filters)

    ordered = [c for c in component_order if c in allowance_components]
    remaining = sorted([c for c in allowance_components if c not in component_order])

    final_components = ordered + remaining

    for component in final_components:
        base_columns.append({
            "label": _(component),
            "fieldname": component.lower().replace(" ", "_"),
            "fieldtype": "Float",
            "precision": 2,
            "width": 150
        })

    return base_columns


def get_allowance_components(filters):
    """Get all unique allowance (earning) components"""
    salary_slip = frappe.qb.DocType("Salary Slip")
    earnings = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.from_(earnings)
        .inner_join(salary_slip).on(earnings.parent == salary_slip.name)
        .select(earnings.salary_component)
        .distinct()
        .where(earnings.parentfield == "earnings")
        .where(earnings.salary_component.notin(["Gross Pay", "Gross Salary"]))
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
    """Fetch Allowances and pivot horizontally"""
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
            earnings.amount.as_("amount")
        )
        .where(earnings.parentfield == "earnings")
        .where(earnings.salary_component.notin(["Gross Pay", "Gross Salary"]))
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

    rows = query.run(as_dict=True)

    allowance_components = get_allowance_components(filters)
    employee_data = {}

    for row in rows:
        emp_key = row.employee_number

        if emp_key not in employee_data:
            employee_data[emp_key] = {
                "employee_number": row.employee_number,
                "full_name": row.employee_name
            }
            for comp in allowance_components:
                employee_data[emp_key][comp.lower().replace(" ", "_")] = 0.00

        fieldname = row.salary_component.lower().replace(" ", "_")
        employee_data[emp_key][fieldname] = float(row.amount)

    data = []
    for emp in employee_data.values():
        for k in emp:
            if k not in ["employee_number", "full_name"]:
                emp[k] = round(float(emp[k]), 2)
        data.append(emp)

    return data
