import frappe
from frappe.utils import today, getdate

def update_expired_employee_contracts():
    """Update employee status to Inactive when custom_until date is reached"""
    
    frappe.logger().info("=== Running Employee Status Update ===")
    frappe.logger().info(f"Today's date: {today()}")
    
    # First, let's see what we have
    all_employees = frappe.db.sql("""
        SELECT name, employee_name, employment_type, status, custom_until
        FROM tabEmployee
        WHERE custom_until IS NOT NULL
    """, as_dict=1)
    
    frappe.logger().info(f"Total employees with custom_until set: {len(all_employees)}")
    
    for emp in all_employees:
        frappe.logger().info(f"  {emp.name} - {emp.employee_name} | Type: {emp.employment_type} | Status: {emp.status} | Until: {emp.custom_until}")
    
    # Now get the ones to update
    employees = frappe.db.sql("""
        SELECT name, employee_name, custom_until
        FROM tabEmployee
        WHERE status = 'Active'
        AND employment_type IN ('Permanent', 'Annual Contract', 'Seasonal')
        AND custom_until IS NOT NULL
        AND custom_until <= %s
    """, (today()), as_dict=1)
    
    frappe.logger().info(f"Employees to update: {len(employees)}")
    
    for emp in employees:
        frappe.logger().info(f"Updating {emp.name} - {emp.employee_name} to Inactive")
        frappe.db.set_value("Employee", emp.name, "status", "Inactive", update_modified=True)
        
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Employee",
            "reference_name": emp.name,
            "content": f"Contract expired on {emp.custom_until}. Status set to Inactive automatically."
        }).insert(ignore_permissions=True)
    
    frappe.db.commit()
    
    if employees:
        frappe.logger().info(f"Successfully updated {len(employees)} employees to Inactive status")
