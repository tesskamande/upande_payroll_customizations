# Copyright (c) 2025, dev@upande.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _


def execute(filters=None):
	"""Main execution function for the report"""
	if filters and filters.get("from_date") and filters.get("to_date"):
		if filters.from_date > filters.to_date:
			frappe.throw(_("To Date cannot be before From Date: {}").format(filters.to_date))

	company_currency = erpnext.get_company_currency(filters.get("company")) if filters.get("company") else "KES"
	columns = get_columns()
	data = get_data(filters, company_currency)

	return columns, data


def get_columns():
	"""Define report columns"""
	return [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Net Pay"),
			"fieldname": "net_pay",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Deduction Component"),
			"fieldname": "deduction_component",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Deduction Amount"),
			"fieldname": "deduction_amount",
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"label": _("1/3 Rule Threshold"),
			"fieldname": "threshold",
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"label": _("Shortfall"),
			"fieldname": "shortfall",
			"fieldtype": "Currency",
			"width": 120
		}
	]


def get_data(filters, company_currency):
	"""Fetch and process salary slip data"""
	salary_slip = frappe.qb.DocType("Salary Slip")
	employee = frappe.qb.DocType("Employee")

	# Build query
	query = (
		frappe.qb.from_(salary_slip)
		.inner_join(employee)
		.on(salary_slip.employee == employee.name)
		.select(
			salary_slip.name,
			salary_slip.employee,
			employee.employee_name,
			salary_slip.gross_pay,
			salary_slip.net_pay,
			salary_slip.total_deduction
		)
		.where(salary_slip.docstatus.isin([0, 1]))
	)

	# Apply filters
	if filters.get("from_date"):
		query = query.where(salary_slip.start_date >= filters.get("from_date"))
	if filters.get("to_date"):
		query = query.where(salary_slip.end_date <= filters.get("to_date"))
	if filters.get("company"):
		query = query.where(salary_slip.company == filters.get("company"))

	salary_data = query.run(as_dict=True)
	results = []

	# Process each salary slip
	for slip in salary_data:
		gross_pay = slip.gross_pay or 0
		net_pay = slip.net_pay or 0

		if gross_pay > 0:
			threshold = (1.0 / 3.0) * gross_pay
			
			# Check if employee violates 1/3 rule
			if net_pay < threshold:
				shortfall = threshold - net_pay
				
				# Fetch deductions for this salary slip
				deductions = frappe.get_all(
					"Salary Detail",
					filters={"parent": slip.name, "parentfield": "deductions"},
					fields=["salary_component", "amount"],
					order_by="idx"
				)

				# Create one row per deduction
				for idx, deduction in enumerate(deductions):
					results.append({
						"employee": slip.employee if idx == 0 else None,
						"employee_name": slip.employee_name if idx == 0 else None,
						"gross_pay": gross_pay if idx == 0 else None,
						"net_pay": net_pay if idx == 0 else None,
						"deduction_component": deduction.salary_component,
						"deduction_amount": deduction.amount or 0,
						"threshold": threshold if idx == 0 else None,
						"shortfall": shortfall if idx == 0 else None
					})

	return results