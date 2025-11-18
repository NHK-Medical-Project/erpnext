# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.document import Document


class SalesOrderItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		additional_notes: DF.Text | None
		against_blanket_order: DF.Check
		amount: DF.Currency
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		base_rate_with_margin: DF.Currency
		billed_amt: DF.Currency
		blanket_order: DF.Link | None
		blanket_order_rate: DF.Currency
		bom_no: DF.Link | None
		brand: DF.Link | None
		child_status: DF.Literal["Pending", "Approved", "Rental Device Assigned", "Ready for Delivery", "DISPATCHED", "DELIVERED", "Active", "Ready for Pickup", "Picked Up", "Submitted to Office", "On Hold", "Overdue", "Renewed", "Cancelled", "Closed", "Partially Closed", "Item Replaced", "Rental SO Completed"]
		conversion_factor: DF.Float
		customer_item_code: DF.Data | None
		delivered_by_supplier: DF.Check
		delivered_qty: DF.Float
		delivery_date: DF.Date | None
		description: DF.TextEditor | None
		discount_amount: DF.Currency
		discount_percentage: DF.Percent
		dispatch_date: DF.Date | None
		ensure_delivery_based_on_produced_serial_no: DF.Check
		grant_commission: DF.Check
		gross_profit: DF.Currency
		image: DF.Attach | None
		is_free_item: DF.Check
		is_stock_item: DF.Check
		item_code: DF.Link
		item_discount_amount: DF.Currency
		item_group: DF.Link | None
		item_name: DF.Data
		item_tax_rate: DF.Code | None
		item_tax_template: DF.Link | None
		line_total: DF.Currency
		margin_rate_or_amount: DF.Float
		margin_type: DF.Literal["", "Percentage", "Amount"]
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		net_amount: DF.Currency
		net_rate: DF.Currency
		old_item_code: DF.Link | None
		ordered_qty: DF.Float
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		picked_qty: DF.Float
		picked_up: DF.Datetime | None
		pickup_date: DF.Datetime | None
		pickup_reason: DF.Literal["", "Patient recovered", "Patient Expired", "Purchased Device from Us", "Purchased Device from Others", "Item Replacement", "Other Reason"]
		pickup_remark: DF.SmallText | None
		planned_qty: DF.Float
		prevdoc_docname: DF.Link | None
		price_list_rate: DF.Currency
		pricing_rules: DF.SmallText | None
		produced_qty: DF.Float
		production_plan_qty: DF.Float
		projected_qty: DF.Float
		purchase_order: DF.Link | None
		purchase_order_item: DF.Data | None
		qty: DF.Float
		quotation_item: DF.Data | None
		rate: DF.Currency
		rate_with_margin: DF.Currency
		read_only: DF.Check
		rental_delivery_date: DF.Datetime | None
		rental_tax_rate: DF.Currency
		replaced_datetime: DF.Datetime | None
		reserve_stock: DF.Check
		returned_qty: DF.Float
		serial_no: DF.SmallText | None
		stock_qty: DF.Float
		stock_reserved_qty: DF.Float
		stock_uom: DF.Link | None
		stock_uom_rate: DF.Currency
		submitted_date: DF.Datetime | None
		supplier: DF.Link | None
		target_warehouse: DF.Link | None
		tax_amount: DF.Currency
		technician_id_after_delivered: DF.Link | None
		technician_id_before_deliverd: DF.Link | None
		technician_mobile_after_delivered: DF.Data | None
		technician_mobile_before_delivered: DF.Data | None
		technician_name_after_delivered: DF.Link | None
		technician_name_before_delivered: DF.Link | None
		total_weight: DF.Float
		transaction_date: DF.Date | None
		uom: DF.Link
		valuation_rate: DF.Currency
		warehouse: DF.Link | None
		weight_per_unit: DF.Float
		weight_uom: DF.Link | None
		work_order_qty: DF.Float
	# end: auto-generated types

	pass


def on_doctype_update():
	frappe.db.add_index("Sales Order Item", ["item_code", "warehouse"])
