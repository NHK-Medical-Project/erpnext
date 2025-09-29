# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from typing import Literal

import frappe
import frappe.utils
from frappe import _, qb
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, cint, cstr, flt, get_link_to_form, getdate, nowdate, strip_html
from datetime import datetime
from webtoolex_whatsapp.webtoolex_whatsapp.doctype.whatsapp_instance.whatsapp_instance import send_custom_whatsapp_message

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
    unlink_inter_company_doc,
    update_linked_doc,
    validate_inter_company_party,
)
from erpnext.accounts.party import get_party_account
from erpnext.controllers.selling_controller import SellingController
from erpnext.manufacturing.doctype.blanket_order.blanket_order import (
    validate_against_blanket_order,
)
from erpnext.manufacturing.doctype.production_plan.production_plan import (
    get_items_for_material_requests,
)
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
    get_sre_reserved_qty_details_for_voucher,
    has_reserved_stock,
)
from erpnext.stock.get_item_details import get_default_bom, get_price_list_rate
from erpnext.stock.stock_balance import get_reserved_qty, update_bin_qty

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class WarehouseRequired(frappe.ValidationError):
    pass


class SalesOrder(SellingController):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
        from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
        from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import SalesTaxesandCharges
        from erpnext.selling.doctype.sales_order_item.sales_order_item import SalesOrderItem
        from erpnext.selling.doctype.sales_team.sales_team import SalesTeam
        from erpnext.stock.doctype.packed_item.packed_item import PackedItem
        from frappe.types import DF

        aadhar_card_attachment: DF.Attach | None
        additional_discount_percentage: DF.Float
        address_display: DF.SmallText | None
        adjustment_amount: DF.Currency
        advance_paid: DF.Currency
        advance_payment_status: DF.Literal["Not Requested", "Requested", "Partially Paid", "Fully Paid"]
        amended_from: DF.Link | None
        amount_eligible_for_commission: DF.Currency
        apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
        auto_repeat: DF.Link | None
        balance_amount: DF.Currency
        base_discount_amount: DF.Currency
        base_grand_total: DF.Currency
        base_in_words: DF.Data | None
        base_net_total: DF.Currency
        base_rounded_total: DF.Currency
        base_rounding_adjustment: DF.Currency
        base_total: DF.Currency
        base_total_taxes_and_charges: DF.Currency
        billing_status: DF.Literal["Not Billed", "Fully Billed", "Partly Billed", "Closed"]
        campaign: DF.Link | None
        commission_rate: DF.Float
        company: DF.Link
        company_address: DF.Link | None
        company_address_display: DF.SmallText | None
        contact_display: DF.SmallText | None
        contact_email: DF.Data | None
        contact_mobile: DF.SmallText | None
        contact_person: DF.Link | None
        contact_phone: DF.Data | None
        conversion_rate: DF.Float
        cost_center: DF.Link | None
        coupon_code: DF.Link | None
        created_by: DF.Link | None
        currency: DF.Link
        customer: DF.Link
        customer_address: DF.Link | None
        customer_email_id: DF.Data | None
        customer_group: DF.Link | None
        customer_mobile_no: DF.Data | None
        customer_name: DF.Data | None
        delivery_address: DF.SmallText | None
        delivery_date: DF.Date | None
        delivery_status: DF.Literal["Not Delivered", "Fully Delivered", "Partly Delivered", "Closed", "Not Applicable"]
        disable_rounded_total: DF.Check
        discount_amount: DF.Currency
        dispatch_address: DF.SmallText | None
        dispatch_address_name: DF.Link | None
        dispatch_date: DF.Date | None
        end_date: DF.Date | None
        from_date: DF.Date | None
        grand_total: DF.Currency
        group_same_items: DF.Check
        ignore_pricing_rule: DF.Check
        in_words: DF.Data | None
        incoterm: DF.Link | None
        inter_company_order_reference: DF.Link | None
        is_internal_customer: DF.Check
        is_renewed: DF.Check
        item_name: DF.SmallText | None
        items: DF.Table[SalesOrderItem]
        language: DF.Data | None
        letter_head: DF.Link | None
        loyalty_amount: DF.Currency
        loyalty_points: DF.Int
        master_order_id: DF.Link | None
        named_place: DF.Data | None
        naming_series: DF.Literal["SAL-ORD-.YYYY.-"]
        net_total: DF.Currency
        order_type: DF.Literal["", "Sales", "Service", "Shopping Cart", "Rental"]
        other_charges_calculation: DF.LongText | None
        outstanding_security_deposit_amount: DF.Currency
        overdue_status: DF.Literal["Active", "Overdue", "Renewed"]
        packed_items: DF.Table[PackedItem]
        paid_security_deposite_amount: DF.Currency
        party_account_currency: DF.Link | None
        payment_pending_reason: DF.SmallText | None
        payment_schedule: DF.Table[PaymentSchedule]
        payment_status: DF.Literal["Paid", "UnPaid", "Partially Paid"]
        payment_terms_template: DF.Link | None
        per_billed: DF.Percent
        per_delivered: DF.Percent
        per_picked: DF.Percent
        permanent_address: DF.SmallText | None
        picked_up: DF.Datetime | None
        pickup_date: DF.Datetime | None
        pickup_reason: DF.Literal["", "Patient recovered", "Patient Expired", "Purchased Device from Us", "Purchased Device from Others", "Item Replacement", "Other Reason"]
        pickup_remark: DF.SmallText | None
        plc_conversion_rate: DF.Float
        po_date: DF.Date | None
        po_no: DF.Data | None
        previous_order_id: DF.Data | None
        price_list_currency: DF.Link
        pricing_rules: DF.Table[PricingRuleDetail]
        project: DF.Link | None
        reason_for_payment_pending: DF.Link | None
        received_amount: DF.Currency
        refundable_security_deposit: DF.Currency
        renewal_order_count: DF.Int
        rental_delivery_date: DF.Datetime | None
        rental_order_agreement_attachment: DF.Attach | None
        represents_company: DF.Link | None
        reserve_stock: DF.Check
        rounded_total: DF.Currency
        rounding_adjustment: DF.Currency
        sales_partner: DF.Link | None
        sales_person: DF.Link | None
        sales_team: DF.Table[SalesTeam]
        security_deposit: DF.Data | None
        security_deposit_amount_return_to_client: DF.Currency
        security_deposit_revised_remark: DF.SmallText | None
        security_deposit_status: DF.Literal["Unpaid", "Paid", "Partially Paid"]
        select_print_heading: DF.Link | None
        selling_price_list: DF.Link
        set_warehouse: DF.Link | None
        shipping_address: DF.SmallText | None
        shipping_address_name: DF.Link | None
        shipping_rule: DF.Link | None
        skip_delivery_note: DF.Check
        source: DF.Link | None
        start_date: DF.Date | None
        status: DF.Literal["Draft", "Pending", "Approved", "Rental Device Assigned", "Ready for Delivery", "DISPATCHED", "DELIVERED", "Active", "Ready for Pickup", "Picked Up", "Submitted to Office", "On Hold", "Overdue", "RENEWED", "To Pay", "To Deliver and Bill", "To Bill", "To Deliver", "Completed", "Cancelled", "Closed", "Partially Closed", "Order", "Sales Completed", "Rental SO Completed"]
        submitted_date: DF.Datetime | None
        tax_category: DF.Link | None
        tax_id: DF.Data | None
        taxes: DF.Table[SalesTaxesandCharges]
        taxes_and_charges: DF.Link | None
        tc_name: DF.Link | None
        technician_mobile_after_delivered: DF.Data | None
        technician_mobile_before_delivered: DF.Data | None
        technician_name_after_delivered: DF.Link | None
        technician_name_before_delivered: DF.Link | None
        terms: DF.TextEditor | None
        territory: DF.Link | None
        title: DF.Data | None
        to_date: DF.Date | None
        total: DF.Currency
        total_commission: DF.Currency
        total_net_weight: DF.Float
        total_no_of_dates: DF.Data | None
        total_qty: DF.Float
        total_rental_amount: DF.Currency
        total_taxes_and_charges: DF.Currency
        transaction_date: DF.Date
    # end: auto-generated types

    def __init__(self, *args, **kwargs):
        super(SalesOrder, self).__init__(*args, **kwargs)

    def onload(self) -> None:
        if frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
            if self.has_unreserved_stock():
                self.set_onload("has_unreserved_stock", True)

        if has_reserved_stock(self.doctype, self.name):
            self.set_onload("has_reserved_stock", True)

    def validate(self):
        super(SalesOrder, self).validate()
        # if self.order_type == "Rental":
        if self.security_deposit not in [None, '']:  # Check if security_deposit is neither None nor empty string
            self.security_deposit = float(self.security_deposit)
        if self.order_type == 'Rental':
            self.total_rental_amount = self.rounded_total + (self.security_deposit or 0)
        else:
            self.total_rental_amount = self.rounded_total
        # self.validate_delivery_date()
        # self.validate_sales_order_payment_status(self)
        self.validate_proj_cust()
        self.validate_po()
        self.validate_uom_is_integer("stock_uom", "stock_qty")
        self.validate_uom_is_integer("uom", "qty")
        self.validate_for_items()
        self.validate_warehouse()
        self.validate_drop_ship()
        self.validate_reserved_stock()
        self.validate_serial_no_based_delivery()
        validate_against_blanket_order(self)
        validate_inter_company_party(
            self.doctype, self.customer, self.company, self.inter_company_order_reference
        )
        # if self.docstatus == 0:
        #     self.validate_item_status()
        if self.coupon_code:
            from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

            validate_coupon_code(self.coupon_code)

        from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

        make_packing_list(self)

        # self.validate_with_previous_doc()
        # self.set_status()	

        if not self.billing_status:
            self.billing_status = "Not Billed"
        if not self.delivery_status:
            self.delivery_status = "Not Delivered"
        if not self.advance_payment_status:
            self.advance_payment_status = "Not Requested"

        self.reset_default_field_value("set_warehouse", "items", "warehouse")

    # def validate_item_status(self):
    #     if self.order_type == 'Rental' and not self.previous_order_id and self.is_renewed == 0:
    #         for item in self.get('items'):
    #             if item.get('__islocal'):  # Check if the item is newly added
    #                 item_doc = frappe.get_doc('Item', item.item_code)
    #                 if item_doc:
    #                     item_doc.status = 'Pre Reserved'
    #                     item_doc.save()
    #                 else:
    #                     frappe.log_error(f"Item '{item.item_code}' not found.")
    #             elif item.get('__deleted'):  # Check if the item is being removed
    #                 item_doc = frappe.get_doc('Item', item.item_code)
    #                 if item_doc:
    #                     item_doc.status = 'Available'
    #                     item_doc.save()
    #                 else:
    #                     frappe.log_error(f"Item '{item.item_code}' not found.")
    # def validate_sales_order_payment_status(self):
    # 	# Access the rounded_total and advance_paid fields from the document
    # 	rounded_total = self.rounded_total
    # 	advance_paid = self.advance_paid

    # 	# Check if the rounded_total is equal to advance_paid
    # 	if rounded_total == advance_paid:
    # 		# If rounded_total equals advance_paid, set payment_status to 'Paid'
    # 		self.payment_status = 'Paid'
    # 	elif advance_paid == 0:
    # 		# If advance_paid is zero, set payment_status to 'Unpaid'
    # 		self.payment_status = 'Unpaid'
    # 	else:
    # 		# If rounded_total is not equal to advance_paid and advance_paid is not zero,
    # 		# set payment_status to 'Partially Paid'
    # 		self.payment_status = 'Partially Paid'

    # 	# Save the changes to the selfument
    # 	doc.save()

    def update_item_names(self):
        item_names = []

        for item in self.items:
            item_name_with_code = f"{item.item_name} ({item.item_code})"
            item_names.append(item_name_with_code)
        # print(item_names)
        self.item_name = ', '.join(item_names)
        
    def validate_po(self):
        # validate p.o date v/s delivery date
        if self.po_date and not self.skip_delivery_note:
            for d in self.get("items"):
                if d.delivery_date and getdate(self.po_date) > getdate(d.delivery_date):
                    frappe.throw(
                        _("Row #{0}: Expected Delivery Date cannot be before Purchase Order Date").format(d.idx)
                    )

        if self.po_no and self.customer and not self.skip_delivery_note:
            so = frappe.db.sql(
                "select name from `tabSales Order` \
                where ifnull(po_no, '') = %s and name != %s and docstatus < 2\
                and customer = %s",
                (self.po_no, self.name, self.customer),
            )
            if so and so[0][0]:
                if cint(
                    frappe.db.get_single_value("Selling Settings", "allow_against_multiple_purchase_orders")
                ):
                    frappe.msgprint(
                        _("Warning: Sales Order {0} already exists against Customer's Purchase Order {1}").format(
                            frappe.bold(so[0][0]), frappe.bold(self.po_no)
                        ),
                        alert=True,
                    )
                else:
                    frappe.throw(
                        _(
                            "Sales Order {0} already exists against Customer's Purchase Order {1}. To allow multiple Sales Orders, Enable {2} in {3}"
                        ).format(
                            frappe.bold(so[0][0]),
                            frappe.bold(self.po_no),
                            frappe.bold(_("'Allow Multiple Sales Orders Against a Customer's Purchase Order'")),
                            get_link_to_form("Selling Settings", "Selling Settings"),
                        )
                    )

    def validate_for_items(self):
        for d in self.get("items"):

            # used for production plan
            d.transaction_date = self.transaction_date

            tot_avail_qty = frappe.db.sql(
                "select projected_qty from `tabBin` \
                where item_code = %s and warehouse = %s",
                (d.item_code, d.warehouse),
            )
            d.projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0

    def product_bundle_has_stock_item(self, product_bundle):
        """Returns true if product bundle has stock item"""
        ret = len(
            frappe.db.sql(
                """select i.name from tabItem i, `tabProduct Bundle Item` pbi
            where pbi.parent = %s and pbi.item_code = i.name and i.is_stock_item = 1""",
                product_bundle,
            )
        )
        return ret

    def validate_sales_mntc_quotation(self):
        for d in self.get("items"):
            if d.prevdoc_docname:
                res = frappe.db.sql(
                    "select name from `tabQuotation` where name=%s and order_type = %s",
                    (d.prevdoc_docname, self.order_type),
                )
                if not res:
                    frappe.msgprint(_("Quotation {0} not of type {1}").format(d.prevdoc_docname, self.order_type))

    def validate_delivery_date(self):
        if self.order_type == "Sales" and not self.skip_delivery_note:
            delivery_date_list = [d.delivery_date for d in self.get("items") if d.delivery_date]
            max_delivery_date = max(delivery_date_list) if delivery_date_list else None
            if (max_delivery_date and not self.delivery_date) or (
                max_delivery_date and getdate(self.delivery_date) != getdate(max_delivery_date)
            ):
                self.delivery_date = max_delivery_date
            if self.delivery_date:
                for d in self.get("items"):
                    if not d.delivery_date:
                        d.delivery_date = self.delivery_date
                    if getdate(self.transaction_date) > getdate(d.delivery_date):
                        frappe.msgprint(
                            _("Expected Delivery Date should be after Sales Order Date"),
                            indicator="orange",
                            title=_("Invalid Delivery Date"),
                            raise_exception=True,
                        )
            else:
                frappe.throw(_("Please enter Delivery Date"))

        self.validate_sales_mntc_quotation()

    def validate_proj_cust(self):
        if self.project and self.customer_name:
            res = frappe.db.sql(
                """select name from `tabProject` where name = %s
                and (customer = %s or ifnull(customer,'')='')""",
                (self.project, self.customer),
            )
            if not res:
                frappe.throw(
                    _("Customer {0} does not belong to project {1}").format(self.customer, self.project)
                )

    def validate_warehouse(self):
        super(SalesOrder, self).validate_warehouse()

        for d in self.get("items"):
            if (
                (
                    frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1
                    or (self.has_product_bundle(d.item_code) and self.product_bundle_has_stock_item(d.item_code))
                )
                and not d.warehouse
                and not cint(d.delivered_by_supplier)
            ):
                frappe.throw(
                    _("Delivery warehouse required for stock item {0}").format(d.item_code), WarehouseRequired
                )

    def validate_with_previous_doc(self):
        super(SalesOrder, self).validate_with_previous_doc(
            {
                "Quotation": {"ref_dn_field": "prevdoc_docname", "compare_fields": [["company", "="]]},
                "Quotation Item": {
                    "ref_dn_field": "quotation_item",
                    "compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
                    "is_child_table": True,
                    "allow_duplicate_prev_row_id": True,
                },
            }
        )

        if cint(frappe.db.get_single_value("Selling Settings", "maintain_same_sales_rate")):
            self.validate_rate_with_reference_doc([["Quotation", "prevdoc_docname", "quotation_item"]])

    def update_enquiry_status(self, prevdoc, flag):
        enq = frappe.db.sql(
            "select t2.prevdoc_docname from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.name=%s",
            prevdoc,
        )
        if enq:
            frappe.db.sql("update `tabOpportunity` set status = %s where name=%s", (flag, enq[0][0]))

    def update_prevdoc_status(self, flag=None):
        for quotation in set(d.prevdoc_docname for d in self.get("items")):
            if quotation:
                doc = frappe.get_doc("Quotation", quotation)
                if doc.docstatus.is_cancelled():
                    frappe.throw(_("Quotation {0} is cancelled").format(quotation))

                # doc.set_status(update=True)
                doc.update_opportunity("Converted" if flag == "submit" else "Quotation")

    def validate_drop_ship(self):
        for d in self.get("items"):
            if d.delivered_by_supplier and not d.supplier:
                frappe.throw(_("Row #{0}: Set Supplier for item {1}").format(d.idx, d.item_code))

    def on_submit(self):
        
        # if self.order_type == 'Rental' and not self.previous_order_id and self.is_renewed == 0:

        #     all_items_pre_reserved = True
        #     for item in self.items:
        #         item_status = frappe.db.get_value("Item", item.item_code, "status")
        #         if item_status != "Available":
        #             all_items_pre_reserved = False
        #             break
            
        #     if not all_items_pre_reserved:
        #         frappe.throw(_("All items must have the status 'Pre Reserved' to submit this order."))

        self.check_credit_limit()
        self.update_item_names()
        self.update_reserved_qty()
        # if self.order_type == 'Sales':
        #     self.status = 'Order'
        if not self.previous_order_id:  # Check if previous_order_id is empty
            if self.order_type == 'Rental' and self.security_deposit and float(self.security_deposit) > 0:
                self.create_security_deposit_journal_entry()
        frappe.get_doc("Authorization Control").validate_approving_authority(
            self.doctype, self.company, self.base_grand_total, self
        )
        self.update_project()
        # self.update_prevdoc_status("submit")

        self.update_blanket_order()

        update_linked_doc(self.doctype, self.name, self.inter_company_order_reference)
        if self.coupon_code:
            from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

            update_coupon_code_count(self.coupon_code, "used")

        if self.get("reserve_stock"):
            self.create_stock_reservation_entries()
        self.update_sales_order_status()
        self.update_read_only_as_one()
        if self.order_type == 'Rental' and not self.previous_order_id and self.is_renewed == 0:
            self.update_item_statuses()


    def update_read_only_as_one(self):
        sales_order = frappe.get_doc('Sales Order', self.name)
        if self.is_renewed == 1 and self.previous_order_id:
            for item in sales_order.items:
                item_sales_order_update = frappe.get_doc('Item',item.item_code)
                item_sales_order_update.custom_sales_order_id = self.name
                item_sales_order_update.save()
        # Iterate through each item in the items table
        for item in sales_order.items:
            item.read_only = 1

        # Save the Sales Order document to persist the changes
        sales_order.save()



    def update_item_statuses(self):

        for item in self.items:
            
            # Get the item document
            item_doc = frappe.get_doc("Item", item.item_code)
            
            # Check current status
            current_status = item_doc.status
            
            if current_status == "Available":
                # Update the status to "Pre Reserved"
                item_doc.status = "Pre Reserved"
                # Save the changes
                item_doc.save()
                # Commit the transaction to ensure changes are saved
                frappe.db.commit()
            else:
                # Get sales orders containing this item
                # sales_orders = get_sales_orders_containing_item(item.item_code)
                result = get_sales_orders_containing_item(item.item_code)
                sales_orders = result['sales_orders']
                
                # Prepare message with Sales Order IDs and customer names
                sales_order_info = "<br>".join([
                    f"<a href='/app/sales-order/{order['name']}'>{order['name']}</a> - {order['customer_name']}"
                    for order in sales_orders
                ])
                
                # Show alert with item_code, current status, and associated sales orders
                frappe.throw(f"Item {item.item_code} cannot be Pre Reserved. Current status is {current_status}.<br><br>Sales Orders:<br>{sales_order_info}")





    def create_security_deposit_journal_entry(self):
        try:
            # sales_order = frappe.get_doc("Sales Order", self.name)

            # Create a new Journal Entry document
            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.sales_order_id = self.name
            journal_entry.master_order_id = self.master_order_id
            journal_entry.journal_entry_type = "Security Deposit"
            journal_entry.journal_entry = "Journal Entry"
            journal_entry.posting_date = frappe.utils.nowdate()
            journal_entry.security_deposite_type = "Booking as Outstanding SD From Client"
            journal_entry.customer_id = self.customer
            journal_entry.transactional_effect = "NA"


            # Add accounts for debit and credit
            journal_entry.append("accounts", {
                "account": "Debtors - INR",
                "party_type": "Customer",
                "party": self.customer,
                "debit_in_account_currency": self.security_deposit
            })
            journal_entry.append("accounts", {
                "account": "Rental Security Deposit Payable - INR",
                # "party_type": "Customer",
                # "party": self.customer,
                "credit_in_account_currency": self.security_deposit
            })

            # Save the Journal Entry document
            journal_entry.insert()
            journal_entry.submit()

            frappe.msgprint("Security Deposit Journal Entry created successfully")  # Debug message

            return True
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Failed to create Security Deposit Journal Entry"))
            frappe.throw(_("Failed to create Security Deposit Journal Entry. Please try again later."))


        
    
    def before_submit(self):
        if self.previous_order_id:
            # existing_renewal_orders = frappe.get_all("Sales Order", filters={"previous_order_id": self.previous_order_id})

            # if existing_renewal_orders:
            #     existing_order_id = existing_renewal_orders[0].name
            #     order_link = frappe.utils.get_url_to_form("Sales Order", existing_order_id)
            #     frappe.throw(_("A renewal order already exists for this sales order in Draft. <a href='{0}'>{1}</a>").format(order_link, existing_order_id))

            overlap = check_overlap(self)

            if overlap:
                frappe.throw("Current start and end dates overlap with the previous order.")	

    def update_sales_order_status(self):
        if self.previous_order_id:

            # Update status in parent Sales Order
            existing_orders = frappe.get_list("Sales Order", filters={"name": self.previous_order_id})
            # print('existing_ordersssssssssssssss',existing_orders)
            if existing_orders:
                sales_order_enddate = frappe.get_doc("Sales Order", existing_orders[0].name)
                existing_orders_end_date = sales_order_enddate.get("end_date")

                if existing_orders_end_date:
                    # Convert to dd-mmm-yyyy format
                    existing_orders_end_date_formatted_end_date = datetime.strptime(str(existing_orders_end_date), "%Y-%m-%d").strftime("%d-%b-%Y")
            for order in existing_orders:
                sales_order = frappe.get_doc("Sales Order", order.name)
                sales_order.status = "RENEWED"
                sales_order.save()

            # Update status in child table (Sales Order Item)
            child_table = frappe.get_all("Sales Order Item", filters={"parent": self.previous_order_id})
            for order_item in child_table:
                sales_order_item = frappe.get_doc("Sales Order Item", order_item.name)
                sales_order_item.child_status = "Renewed"
                sales_order_item.save()
            if self.customer_mobile_no:
                admin_settings = frappe.get_single("Admin Settings")
                
                if admin_settings.send_renewal_and_payment_message == 1:
                    self.send_renewal_whatsapp_message(existing_orders_end_date_formatted_end_date)

        # elif self.order_type == "Rental":
        # 	# Update master_order_id with the current doc name
        # 	self.master_order_id = self.name
        # 	self.save()
        # self.save()
    

    def send_renewal_whatsapp_message(self,existing_orders_end_date_formatted_end_date):
        """Send renewal message to client through WhatsApp"""
        customer_name = self.customer_name or "Customer"
        equipment_names = ", ".join([item.item_name for item in self.items]) if self.items else "No equipment"
        formatted_start_date = datetime.strptime(str(self.start_date), '%Y-%m-%d').strftime('%d-%b-%Y') if self.start_date else "N/A"
        formatted_end_date_current = datetime.strptime(str(self.end_date), '%Y-%m-%d').strftime('%d-%b-%Y') if self.end_date else "N/A"

        message = f"""
Hello Sir/Mam,

Patient Name: {customer_name}
Equipment Name: {equipment_names}

Your current rental period for medical devices is ending on {existing_orders_end_date_formatted_end_date}.

To continue, kindly make renewal payment of {self.grand_total} Rs for the period {formatted_start_date} to {formatted_end_date_current}.

For any query, call or WhatsApp on 8884880013.
    """

        # Check if customer has a mobile number
        if self.customer_mobile_no and len(self.customer_mobile_no) == 10:
            send_custom_whatsapp_message(self.customer_mobile_no, message)
    def before_cancel(self):
        if self.previous_order_id:
            # if self.status == 'Submitted to Office':
            #     frappe.throw('Submitted to Office Record cannot be canceled')
            
            sales_order_renewal = frappe.get_doc("Sales Order", self.previous_order_id)
            sales_order_renewal.status = self.status

            # Create a dictionary for current form items for quick lookup
            current_form_items = {item.item_code: item.child_status for item in self.items}

            for item in sales_order_renewal.items:
                # Set child_status from current form items
                if item.item_code in current_form_items:
                    item.child_status = current_form_items[item.item_code]
                else:
                    item.child_status = "Active"  # Default value if not found in current form items
                
                # Update item in Item doctype
                item_sales_order_update = frappe.get_doc('Item', item.item_code)
                if self.status != 'Submitted to Office':
                    item_sales_order_update.custom_sales_order_id = self.previous_order_id
                    item_sales_order_update.save()
            
            # Save the updated Sales Order
            sales_order_renewal.save()
        return super().before_cancel()

    def on_cancel(self):

        if self.status == 'RENEWED':
            frappe.throw(
            'Cannot cancel this record because it has been RENEWED'
        )
        else:
            self.status = "Cancelled"
        # if self.status == 'Submitted to Office' and self.is_renewed == 1:
        #         frappe.throw(
        #     'Cannot cancel this record because it has been submitted to office and is marked as renewed.'
        # )
        

        # if self.previous_order_id:
        #     sales_order_renewal = frappe.get_doc("Sales Order", self.previous_order_id)
        #     sales_order_renewal.status = "Active"

        #     for item in sales_order_renewal.items:
        #         item.child_status = "Active"
        #         item_sales_order_update = frappe.get_doc('Item',item.item_code)
        #         item_sales_order_update.custom_sales_order_id = self.previous_order_id
        #         item_sales_order_update.save()

        #     sales_order_renewal.save()
        # if not self.previous_order_id:
        if self.order_type == 'Rental' and not self.previous_order_id and self.is_renewed == 0:
            self.item_status_change_cancel()

        self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
        super(SalesOrder, self).on_cancel()

        # Cannot cancel closed SO
        if self.status == "Closed":
            frappe.throw(_("Closed order cannot be cancelled. Unclose to cancel."))

        # self.check_nextdoc_docstatus()
        self.update_reserved_qty()
        self.update_project()
        self.update_prevdoc_status("cancel")

        self.db_set("status", "Cancelled")

        self.update_blanket_order()
        self.cancel_stock_reservation_entries()

        unlink_inter_company_doc(self.doctype, self.name, self.inter_company_order_reference)
        if self.coupon_code:
            from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

            update_coupon_code_count(self.coupon_code, "cancelled")


    # def item_status_change_cancel(self):
    #     for item in self.get("items"):
    #         item_code = item.item_code
    #         # Initialize a list to store information about other orders
    #         other_order_info = []
    #         # Check if the item_code is present in any other sales order
    #         other_orders = frappe.get_all("Sales Order",
    #                                     filters={"docstatus": 1,  # Only consider submitted sales orders
    #                                             "name": ("!=", self.name),
    #                                             "status": ("not in", ["Submitted to Office"])},
    #                                     fields=["name", "status"])
    #         for order in other_orders:
    #             sales_order = frappe.get_doc("Sales Order", order.name)
    #             for order_item in sales_order.items:
    #                 if order_item.item_code == item_code:
    #                     other_order_info.append((sales_order.name, sales_order.status))
    #                     break  # No need to check other items in this order if the item is already found
    #         if other_order_info:
    #             # Construct a message with order IDs and statuses
    #             orders_info = ", ".join(["{} ({})".format(order[0], order[1]) for order in other_order_info])
    #             current_item_status = frappe.get_value("Item", item_code, "status")
    #             # If other orders exist, show alert and prevent cancellation
    #             frappe.throw(_("Item {} (current status: {}) is present in other sales orders ({}) . Cancel those orders before cancelling this one.".format(item_code, current_item_status, orders_info)))

    #         # If not present in any other order, update item status
    #         item_doc = frappe.get_doc("Item", item_code)
    #         if item_doc.status in ["Rented Out", "Reserved","Pre Reserved"]:
    #             item_doc.status = "Available"
    #             item_doc.customer_name = ""
    #             item_doc.customer_n = ""
                
    #             item_doc.save()

    #     frappe.db.commit()


    def item_status_change_cancel(self):
        for item in self.get("items"):
            item_code = item.item_code
            other_order_info = []
            
            # Check if the item_code is present in any other sales order
            other_orders = frappe.get_all("Sales Order",
                                        filters={"docstatus": 1,  # Only consider submitted sales orders
                                                "name": ("!=", self.name),
                                                "status": ("not in", ["Rental SO Completed","Submitted to Office","RENEWED","Partially Closed"])},
                                        fields=["name", "status"])
            
            for order in other_orders:
                sales_order = frappe.get_doc("Sales Order", order.name)
                for order_item in sales_order.items:
                    if order_item.item_code == item_code:
                        other_order_info.append((sales_order.name, sales_order.status))
                        break  # No need to check other items in this order if the item is already found
            
            if other_order_info:
                # Construct a message with order IDs and statuses
                orders_info = ", ".join(["{} ({})".format(order[0], order[1]) for order in other_order_info])
                current_item_status = frappe.get_value("Item", item_code, "status")
                
                # Show alert and prevent cancellation if other orders exist
                frappe.msgprint(_("Item {} (current status: {}) is present in other sales orders ({}) .<br><br> Note: The current order will be cancelled without updating the inventory status.".format(item_code, current_item_status, orders_info)))

            else:
                # If not present in any other order, update item status
                item_doc = frappe.get_doc("Item", item_code)
                if item_doc.status in ["Rented Out", "Reserved", "Pre Reserved"]:
                    item_doc.status = "Available"
                    item_doc.customer_name = ""
                    item_doc.customer_n = ""
                    item_doc.custom_sales_order_id = ""
                    
                    item_doc.save()

                orders_info = ", ".join(["{} ({})".format(order[0], order[1]) for order in other_order_info])
                current_item_status = frappe.get_value("Item", item_code, "status")
                
                frappe.msgprint(_("Item {} (current status: {}) is not present in any other sales orders ({}) .<br><br> Note: The current order will be cancelled with updating the inventory status to Available.".format(item_code, current_item_status, orders_info)))

        frappe.db.commit()



    def on_trash(self):
        # Check if the user has the 'System Manager' role
        if "System Manager" in frappe.get_roles(frappe.session.user):
            # Allow deletion for System Manager
            return

        # For other roles, check the docstatus
        if self.docstatus == 0:
            # Allow deletion if docstatus is 0
            return
        else:
            # Prevent deletion if docstatus is not 0
            frappe.throw(_("You cannot delete this document because its status is not Draft."))

        # if not self.previous_order_id:
        #     self.item_status_change_cancel()

    def update_project(self):
        if (
            frappe.db.get_single_value("Selling Settings", "sales_update_frequency") != "Each Transaction"
        ):
            return

        if self.project:
            project = frappe.get_doc("Project", self.project)
            project.update_sales_amount()
            project.db_update()

    def check_credit_limit(self):
        # if bypass credit limit check is set to true (1) at sales order level,
        # then we need not to check credit limit and vise versa
        if not cint(
            frappe.db.get_value(
                "Customer Credit Limit",
                {"parent": self.customer, "parenttype": "Customer", "company": self.company},
                "bypass_credit_limit_check",
            )
        ):
            check_credit_limit(self.customer, self.company)

    def check_nextdoc_docstatus(self):
        linked_invoices = frappe.db.sql_list(
            """select distinct t1.name
            from `tabSales Invoice` t1,`tabSales Invoice Item` t2
            where t1.name = t2.parent and t2.sales_order = %s and t1.docstatus = 0""",
            self.name,
        )

        if linked_invoices:
            linked_invoices = [get_link_to_form("Sales Invoice", si) for si in linked_invoices]
            frappe.throw(
                _("Sales Invoice {0} must be deleted before cancelling this Sales Order").format(
                    ", ".join(linked_invoices)
                )
            )

    def check_modified_date(self):
        mod_db = frappe.db.get_value("Sales Order", self.name, "modified")
        date_diff = frappe.db.sql("select TIMEDIFF('%s', '%s')" % (mod_db, cstr(self.modified)))
        if date_diff and date_diff[0][0]:
            frappe.throw(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name))

    def update_status(self, status):
        self.check_modified_date()
        # self.set_status(update=True, status=status)
        self.update_reserved_qty()
        self.notify_update()
        clear_doctype_notifications(self)

    def update_reserved_qty(self, so_item_rows=None):
        """update requested qty (before ordered_qty is updated)"""
        item_wh_list = []

        def _valid_for_reserve(item_code, warehouse):
            if (
                item_code
                and warehouse
                and [item_code, warehouse] not in item_wh_list
                and frappe.get_cached_value("Item", item_code, "is_stock_item")
            ):
                item_wh_list.append([item_code, warehouse])

        for d in self.get("items"):
            if (not so_item_rows or d.name in so_item_rows) and not d.delivered_by_supplier:
                if self.has_product_bundle(d.item_code):
                    for p in self.get("packed_items"):
                        if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
                            _valid_for_reserve(p.item_code, p.warehouse)
                else:
                    _valid_for_reserve(d.item_code, d.warehouse)

        for item_code, warehouse in item_wh_list:
            update_bin_qty(item_code, warehouse, {"reserved_qty": get_reserved_qty(item_code, warehouse)})

    def on_update(self):
        pass

    def on_update_after_submit(self):
        # self.validate_sales_order_payment_status()
        
        self.check_credit_limit()
  

  

    # def before_save(self):
    #     if self.order_type == 'Rental' and not self.previous_order_id and self.is_renewed == 0 and self.docstatus == 0:
    #         for item in self.get('items'):
    #             if item.get('__islocal'):  # Check if the item is newly added
    #                 # Set status of new item to 'Pre Reserved'
    #                 item_doc = frappe.get_doc('Item', item.item_code)
    #                 if item_doc:
    #                     item_doc.status = 'Pre Reserved'
    #                     item_doc.save()
    #                 else:
    #                     frappe.log_error(f"Item '{item.item_code}' not found.")
    #             elif item.get('__deleted'):  # Check if the item is being removed
    #                 # Set status of removed item to 'Available'
    #                 item_doc = frappe.get_doc('Item', item.item_code)
    #                 if item_doc:
    #                     item_doc.status = 'Available'
    #                     item_doc.save()
    #                 else:
    #                     frappe.log_error(f"Item '{item.item_code}' not found.")

        # Ensure to call the superclass's before_save method to maintain standard functionality
        # super(SalesOrder, self).before_save()


    # def after_save(self):
    #     if self.order_type == 'Rental' and self.is_renewed == 0 and self.docstatus == 0:
    #         for item in self.items:
    #             # Update status of each item to 'Pre Reserved' if currently 'Available'
    #             item_doc = frappe.get_doc('Item', item.item_code)
    #             if item_doc and item_doc.status == 'Available':
    #                 item_doc.status = 'Pre Reserved'
    #                 item_doc.save()
    #             else:
    #                 frappe.log_error(f"Item '{item.item_code}' not found or already reserved.")

    # def before_save(self):
        # if self.order_type == 'Rental' and self.is_renewed == 0 and self.docstatus == 0:
        #     for item in self.items:
        #         # Revert status of each item from 'Pre Reserved' back to 'Available'
        #         item_doc = frappe.get_doc('Item', item.item_code)
        #         if item_doc and item_doc.status == 'Pre Reserved':
        #             item_doc.status = 'Available'
        #             item_doc.save()
        #         else:
        #             frappe.log_error(f"Item '{item.item_code}' not found or not reserved.")
    def before_update_after_submit(self):
        # self.validate_sales_order_payment_status()
        self.update_item_names()
        self.validate_po()
        self.validate_drop_ship()
        self.validate_supplier_after_submit()
        # self.validate_delivery_date()

    def validate_supplier_after_submit(self):
        """Check that supplier is the same after submit if PO is already made"""
        exc_list = []

        for item in self.items:
            if item.supplier:
                supplier = frappe.db.get_value(
                    "Sales Order Item", {"parent": self.name, "item_code": item.item_code}, "supplier"
                )
                if item.ordered_qty > 0.0 and item.supplier != supplier:
                    exc_list.append(
                        _("Row #{0}: Not allowed to change Supplier as Purchase Order already exists").format(
                            item.idx
                        )
                    )

        if exc_list:
            frappe.throw("\n".join(exc_list))

    def update_delivery_status(self):
        """Update delivery status from Purchase Order for drop shipping"""
        tot_qty, delivered_qty = 0.0, 0.0

        for item in self.items:
            if item.delivered_by_supplier:
                item_delivered_qty = frappe.db.sql(
                    """select sum(qty)
                    from `tabPurchase Order Item` poi, `tabPurchase Order` po
                    where poi.sales_order_item = %s
                        and poi.item_code = %s
                        and poi.parent = po.name
                        and po.docstatus = 1
                        and po.status = 'Delivered'""",
                    (item.name, item.item_code),
                )

                item_delivered_qty = item_delivered_qty[0][0] if item_delivered_qty else 0
                item.db_set("delivered_qty", flt(item_delivered_qty), update_modified=False)

            delivered_qty += item.delivered_qty
            tot_qty += item.qty

        if tot_qty != 0:
            self.db_set("per_delivered", flt(delivered_qty / tot_qty) * 100, update_modified=False)

    def update_picking_status(self):
        total_picked_qty = 0.0
        total_qty = 0.0
        per_picked = 0.0

        for so_item in self.items:
            if cint(
                frappe.get_cached_value("Item", so_item.item_code, "is_stock_item")
            ) or self.has_product_bundle(so_item.item_code):
                total_picked_qty += flt(so_item.picked_qty)
                total_qty += flt(so_item.stock_qty)

        if total_picked_qty and total_qty:
            per_picked = total_picked_qty / total_qty * 100

        self.db_set("per_picked", flt(per_picked), update_modified=False)

    def set_indicator(self):
        """Set indicator for portal"""
        self.indicator_color = {
            "Draft": "red",
            "On Hold": "orange",
            "To Deliver and Bill": "orange",
            "To Bill": "orange",
            "To Deliver": "orange",
            "Completed": "green",
            "Cancelled": "red",
        }.get(self.status, "blue")

        self.indicator_title = _(self.status)

    def on_recurring(self, reference_doc, auto_repeat_doc):
        def _get_delivery_date(ref_doc_delivery_date, red_doc_transaction_date, transaction_date):
            delivery_date = auto_repeat_doc.get_next_schedule_date(schedule_date=ref_doc_delivery_date)

            if delivery_date <= transaction_date:
                delivery_date_diff = frappe.utils.date_diff(ref_doc_delivery_date, red_doc_transaction_date)
                delivery_date = frappe.utils.add_days(transaction_date, delivery_date_diff)

            return delivery_date

        self.set(
            "delivery_date",
            _get_delivery_date(
                reference_doc.delivery_date, reference_doc.transaction_date, self.transaction_date
            ),
        )

        for d in self.get("items"):
            reference_delivery_date = frappe.db.get_value(
                "Sales Order Item",
                {"parent": reference_doc.name, "item_code": d.item_code, "idx": d.idx},
                "delivery_date",
            )

            d.set(
                "delivery_date",
                _get_delivery_date(
                    reference_delivery_date, reference_doc.transaction_date, self.transaction_date
                ),
            )

    def validate_serial_no_based_delivery(self):
        reserved_items = []
        normal_items = []
        for item in self.items:
            if item.ensure_delivery_based_on_produced_serial_no:
                if item.item_code in normal_items:
                    frappe.throw(
                        _(
                            "Cannot ensure delivery by Serial No as Item {0} is added with and without Ensure Delivery by Serial No."
                        ).format(item.item_code)
                    )
                if item.item_code not in reserved_items:
                    if not frappe.get_cached_value("Item", item.item_code, "has_serial_no"):
                        frappe.throw(
                            _(
                                "Item {0} has no Serial No. Only serialized items can have delivery based on Serial No"
                            ).format(item.item_code)
                        )
                    if not frappe.db.exists("BOM", {"item": item.item_code, "is_active": 1}):
                        frappe.throw(
                            _("No active BOM found for item {0}. Delivery by Serial No cannot be ensured").format(
                                item.item_code
                            )
                        )
                reserved_items.append(item.item_code)
            else:
                normal_items.append(item.item_code)

            if not item.ensure_delivery_based_on_produced_serial_no and item.item_code in reserved_items:
                frappe.throw(
                    _(
                        "Cannot ensure delivery by Serial No as Item {0} is added with and without Ensure Delivery by Serial No."
                    ).format(item.item_code)
                )

    def validate_reserved_stock(self):
        """Clean reserved stock flag for non-stock Item"""

        enable_stock_reservation = frappe.db.get_single_value(
            "Stock Settings", "enable_stock_reservation"
        )

        for item in self.items:
            if item.reserve_stock and (not enable_stock_reservation or not cint(item.is_stock_item)):
                item.reserve_stock = 0

    def has_unreserved_stock(self) -> bool:
        """Returns True if there is any unreserved item in the Sales Order."""

        reserved_qty_details = get_sre_reserved_qty_details_for_voucher("Sales Order", self.name)

        for item in self.get("items"):
            if not item.get("reserve_stock"):
                continue

            unreserved_qty = get_unreserved_qty(item, reserved_qty_details)
            if unreserved_qty > 0:
                return True

        return False

    @frappe.whitelist()
    def create_stock_reservation_entries(
        self,
        items_details: list[dict] = None,
        from_voucher_type: Literal["Pick List", "Purchase Receipt"] = None,
        notify=True,
    ) -> None:
        """Creates Stock Reservation Entries for Sales Order Items."""

        from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
            create_stock_reservation_entries_for_so_items as create_stock_reservation_entries,
        )

        create_stock_reservation_entries(
            sales_order=self,
            items_details=items_details,
            from_voucher_type=from_voucher_type,
            notify=notify,
        )

    @frappe.whitelist()
    def cancel_stock_reservation_entries(self, sre_list=None, notify=True) -> None:
        """Cancel Stock Reservation Entries for Sales Order Items."""

        from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
            cancel_stock_reservation_entries,
        )

        cancel_stock_reservation_entries(
            voucher_type=self.doctype, voucher_no=self.name, sre_list=sre_list, notify=notify
        )


def get_unreserved_qty(item: object, reserved_qty_details: dict) -> float:
    """Returns the unreserved quantity for the Sales Order Item."""

    existing_reserved_qty = reserved_qty_details.get(item.name, 0)
    return (
        item.stock_qty
        - flt(item.delivered_qty) * item.get("conversion_factor", 1)
        - existing_reserved_qty
    )


def get_list_context(context=None):
    from erpnext.controllers.website_list_for_contact import get_list_context

    list_context = get_list_context(context)
    list_context.update(
        {
            "show_sidebar": True,
            "show_search": True,
            "no_breadcrumbs": True,
            "title": _("Orders"),
        }
    )

    return list_context


@frappe.whitelist()
def close_or_unclose_sales_orders(names, status):
    if not frappe.has_permission("Sales Order", "write"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    names = json.loads(names)
    for name in names:
        so = frappe.get_doc("Sales Order", name)
        if so.docstatus == 1:
            if status == "Closed":
                if so.status not in ("Cancelled", "Closed") and (
                    so.per_delivered < 100 or so.per_billed < 100
                ):
                    so.update_status(status)
            else:
                if so.status == "Closed":
                    so.update_status("Draft")
            so.update_blanket_order()

    frappe.local.message_log = []


def get_requested_item_qty(sales_order):
    result = {}
    for d in frappe.db.get_all(
        "Material Request Item",
        filters={"docstatus": 1, "sales_order": sales_order},
        fields=["sales_order_item", "sum(qty) as qty", "sum(received_qty) as received_qty"],
        group_by="sales_order_item",
    ):
        result[d.sales_order_item] = frappe._dict({"qty": d.qty, "received_qty": d.received_qty})

    return result


@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
    requested_item_qty = get_requested_item_qty(source_name)

    def get_remaining_qty(so_item):
        return flt(
            flt(so_item.qty)
            - flt(requested_item_qty.get(so_item.name, {}).get("qty"))
            - max(
                flt(so_item.get("delivered_qty"))
                - flt(requested_item_qty.get(so_item.name, {}).get("received_qty")),
                0,
            )
        )

    def update_item(source, target, source_parent):
        # qty is for packed items, because packed items don't have stock_qty field
        target.project = source_parent.project
        target.qty = get_remaining_qty(source)
        target.stock_qty = flt(target.qty) * flt(target.conversion_factor)

        args = target.as_dict().copy()
        args.update(
            {
                "company": source_parent.get("company"),
                "price_list": frappe.db.get_single_value("Buying Settings", "buying_price_list"),
                "currency": source_parent.get("currency"),
                "conversion_rate": source_parent.get("conversion_rate"),
            }
        )

        # target.rate = flt(
        # 	get_price_list_rate(args=args, item_doc=frappe.get_cached_doc("Item", target.item_code)).get(
        # 		"price_list_rate"
        # 	)
        # )
        target.amount = target.qty * target.rate

    doc = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {"doctype": "Material Request", "validation": {"docstatus": ["=", 1]}},
            "Packed Item": {
                "doctype": "Material Request Item",
                "field_map": {"parent": "sales_order", "uom": "stock_uom"},
                "postprocess": update_item,
            },
            "Sales Order Item": {
                "doctype": "Material Request Item",
                "field_map": {"name": "sales_order_item", "parent": "sales_order"},
                "condition": lambda item: not frappe.db.exists(
                    "Product Bundle", {"name": item.item_code, "disabled": 0}
                )
                and get_remaining_qty(item) > 0,
                "postprocess": update_item,
            },
        },
        target_doc,
    )

    return doc


@frappe.whitelist()
def make_project(source_name, target_doc=None):
    def postprocess(source, doc):
        doc.project_type = "External"
        doc.project_name = source.name

    doc = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Project",
                "validation": {"docstatus": ["=", 1]},
                "field_map": {
                    "name": "sales_order",
                    "base_grand_total": "estimated_costing",
                    "net_total": "total_sales_amount",
                },
            },
        },
        target_doc,
        postprocess,
    )

    return doc


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
    from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
    from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
        get_sre_details_for_voucher,
        get_sre_reserved_qty_details_for_voucher,
        get_ssb_bundle_for_voucher,
    )

    if not kwargs:
        kwargs = {
            "for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
            "skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
        }

    kwargs = frappe._dict(kwargs)

    sre_details = {}
    if kwargs.for_reserved_stock:
        sre_details = get_sre_reserved_qty_details_for_voucher("Sales Order", source_name)

    mapper = {
        "Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
        "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
        "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
    }

    def set_missing_values(source, target):
        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        target.run_method("calculate_taxes_and_totals")
        target.run_method("set_use_serial_batch_fields")

        if source.company_address:
            target.update({"company_address": source.company_address})
        else:
            # set company address
            target.update(get_company_address(target.company))

        if target.company_address:
            target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

        # if invoked in bulk creation, validations are ignored and thus this method is nerver invoked
        if frappe.flags.bulk_transaction:
            # set target items names to ensure proper linking with packed_items
            target.set_new_name()

        make_packing_list(target)

    def condition(doc):
        if doc.name in sre_details:
            del sre_details[doc.name]
            return False

        # make_mapped_doc sets js `args` into `frappe.flags.args`
        if frappe.flags.args and frappe.flags.args.delivery_dates:
            if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
                return False
        if frappe.flags.args and frappe.flags.args.until_delivery_date:
            if cstr(doc.delivery_date) > frappe.flags.args.until_delivery_date:
                return False

        return abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1

    def update_item(source, target, source_parent):
        target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
        target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
        target.qty = flt(source.qty) - flt(source.delivered_qty)

        item = get_item_defaults(target.item_code, source_parent.company)
        item_group = get_item_group_defaults(target.item_code, source_parent.company)

        if item:
            target.cost_center = (
                frappe.db.get_value("Project", source_parent.project, "cost_center")
                or item.get("buying_cost_center")
                or item_group.get("buying_cost_center")
            )

    if not kwargs.skip_item_mapping:
        mapper["Sales Order Item"] = {
            "doctype": "Delivery Note Item",
            "field_map": {
                "rate": "rate",
                "name": "so_detail",
                "parent": "against_sales_order",
            },
            "condition": condition,
            "postprocess": update_item,
        }

    so = frappe.get_doc("Sales Order", source_name)
    target_doc = get_mapped_doc("Sales Order", so.name, mapper, target_doc)

    if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
        sre_list = get_sre_details_for_voucher("Sales Order", source_name)

        if sre_list:

            def update_dn_item(source, target, source_parent):
                update_item(source, target, so)

            so_items = {d.name: d for d in so.items if d.stock_reserved_qty}

            for sre in sre_list:
                if not condition(so_items[sre.voucher_detail_no]):
                    continue

                dn_item = get_mapped_doc(
                    "Sales Order Item",
                    sre.voucher_detail_no,
                    {
                        "Sales Order Item": {
                            "doctype": "Delivery Note Item",
                            "field_map": {
                                "rate": "rate",
                                "name": "so_detail",
                                "parent": "against_sales_order",
                            },
                            "postprocess": update_dn_item,
                        }
                    },
                    ignore_permissions=True,
                )

                dn_item.qty = flt(sre.reserved_qty) * flt(dn_item.get("conversion_factor", 1))

                if sre.reservation_based_on == "Serial and Batch" and (sre.has_serial_no or sre.has_batch_no):
                    dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre)

                target_doc.append("items", dn_item)
            else:
                # Correct rows index.
                for idx, item in enumerate(target_doc.items):
                    item.idx = idx + 1

    if not kwargs.skip_item_mapping and frappe.flags.bulk_transaction and not target_doc.items:
        # the (date) condition filter resulted in an unintendedly created empty DN; remove it
        del target_doc
        return

    # Should be called after mapping items.
    set_missing_values(so, target_doc)

    return target_doc


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
    def postprocess(source, target):
        set_missing_values(source, target)
        # Get the advance paid Journal Entries in Sales Invoice Advance
        if target.get("allocate_advances_automatically"):
            target.set_advances()
        if source.order_type == "Rental":
            target.rental_sales_invoice = 1
            target.allocate_advances_automatically = 1
            target.save()
            target.submit()

    def set_missing_values(source, target):
        target.flags.ignore_permissions = True
        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        target.run_method("calculate_taxes_and_totals")
        target.run_method("set_use_serial_batch_fields")

        if source.company_address:
            target.update({"company_address": source.company_address})
        else:
            # set company address
            target.update(get_company_address(target.company))

        if target.company_address:
            target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

        # set the redeem loyalty points if provided via shopping cart
        if source.loyalty_points and source.order_type == "Shopping Cart":
            target.redeem_loyalty_points = 1

        target.debit_to = get_party_account("Customer", source.customer, source.company)

    def update_item(source, target, source_parent):
        target.amount = flt(source.amount) - flt(source.billed_amt)
        target.base_amount = target.amount * flt(source_parent.conversion_rate)
        target.qty = (
            target.amount / flt(source.rate)
            if (source.rate and source.billed_amt)
            else source.qty - source.returned_qty
        )

        if source_parent.project:
            target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
        if target.item_code:
            item = get_item_defaults(target.item_code, source_parent.company)
            item_group = get_item_group_defaults(target.item_code, source_parent.company)
            cost_center = item.get("selling_cost_center") or item_group.get("selling_cost_center")

            if cost_center:
                target.cost_center = cost_center

    doclist = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "party_account_currency": "party_account_currency",
                    "payment_terms_template": "payment_terms_template",
                },
                "field_no_map": ["payment_terms_template"],
                "validation": {"docstatus": ["=", 1]},
            },
            "Sales Order Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "name": "so_detail",
                    "parent": "sales_order",
                },
                "postprocess": update_item,
                "condition": lambda doc: doc.qty
                and (doc.base_amount == 0 or abs(doc.billed_amt) < abs(doc.amount)),
            },
            "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
            "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
        },
        target_doc,
        postprocess,
        ignore_permissions=ignore_permissions,
    )

    automatically_fetch_payment_terms = cint(
        frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
    )
    if automatically_fetch_payment_terms:
        doclist.set_payment_schedule()

    return doclist


@frappe.whitelist()
def get_technician_records(sales_order_id):
    """
    Fetch technician records related to the provided sales order ID.
    """
    return frappe.db.sql("""
        SELECT technician_name,name, technician_mobile_no, notes ,status,type,charges,kilometers,payment_status
        FROM `tabTechnician Visit Entry` 
        WHERE sales_order_id = %s
    """, (sales_order_id,), as_dict=True)

@frappe.whitelist()
def make_maintenance_schedule(source_name, target_doc=None):
    maint_schedule = frappe.db.sql(
        """select t1.name
        from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2
        where t2.parent=t1.name and t2.sales_order=%s and t1.docstatus=1""",
        source_name,
    )

    if not maint_schedule:
        doclist = get_mapped_doc(
            "Sales Order",
            source_name,
            {
                "Sales Order": {"doctype": "Maintenance Schedule", "validation": {"docstatus": ["=", 1]}},
                "Sales Order Item": {
                    "doctype": "Maintenance Schedule Item",
                    "field_map": {"parent": "sales_order"},
                },
            },
            target_doc,
        )

        return doclist


@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None):
    visit = frappe.db.sql(
        """select t1.name
        from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
        where t2.parent=t1.name and t2.prevdoc_docname=%s
        and t1.docstatus=1 and t1.completion_status='Fully Completed'""",
        source_name,
    )

    if not visit:
        doclist = get_mapped_doc(
            "Sales Order",
            source_name,
            {
                "Sales Order": {"doctype": "Maintenance Visit", "validation": {"docstatus": ["=", 1]}},
                "Sales Order Item": {
                    "doctype": "Maintenance Visit Purpose",
                    "field_map": {"parent": "prevdoc_docname", "parenttype": "prevdoc_doctype"},
                },
            },
            target_doc,
        )

        return doclist


@frappe.whitelist()
def get_events(start, end, filters=None):
    """Returns events for Gantt / Calendar view rendering.

    :param start: Start date-time.
    :param end: End date-time.
    :param filters: Filters (JSON).
    """
    from frappe.desk.calendar import get_event_conditions

    conditions = get_event_conditions("Sales Order", filters)

    data = frappe.db.sql(
        """
        select
            distinct `tabSales Order`.name, `tabSales Order`.customer_name, `tabSales Order`.status,
            `tabSales Order`.delivery_status, `tabSales Order`.billing_status,
            `tabSales Order Item`.delivery_date
        from
            `tabSales Order`, `tabSales Order Item`
        where `tabSales Order`.name = `tabSales Order Item`.parent
            and `tabSales Order`.skip_delivery_note = 0
            and (ifnull(`tabSales Order Item`.delivery_date, '0000-00-00')!= '0000-00-00') \
            and (`tabSales Order Item`.delivery_date between %(start)s and %(end)s)
            and `tabSales Order`.docstatus < 2
            {conditions}
        """.format(
            conditions=conditions
        ),
        {"start": start, "end": end},
        as_dict=True,
        update={"allDay": 0},
    )
    return data


@frappe.whitelist()
def make_purchase_order_for_default_supplier(source_name, selected_items=None, target_doc=None):
    """Creates Purchase Order for each Supplier. Returns a list of doc objects."""

    from erpnext.setup.utils import get_exchange_rate

    if not selected_items:
        return

    if isinstance(selected_items, str):
        selected_items = json.loads(selected_items)

    def set_missing_values(source, target):
        target.supplier = supplier
        target.currency = frappe.db.get_value(
            "Supplier", filters={"name": supplier}, fieldname=["default_currency"]
        )
        company_currency = frappe.db.get_value(
            "Company", filters={"name": target.company}, fieldname=["default_currency"]
        )

        target.conversion_rate = get_exchange_rate(target.currency, company_currency, args="for_buying")

        target.apply_discount_on = ""
        target.additional_discount_percentage = 0.0
        target.discount_amount = 0.0
        target.inter_company_order_reference = ""
        target.shipping_rule = ""

        default_price_list = frappe.get_value("Supplier", supplier, "default_price_list")
        if default_price_list:
            target.buying_price_list = default_price_list

        if any(item.delivered_by_supplier == 1 for item in source.items):
            if source.shipping_address_name:
                target.shipping_address = source.shipping_address_name
                target.shipping_address_display = source.shipping_address
            else:
                target.shipping_address = source.customer_address
                target.shipping_address_display = source.address_display

            target.customer_contact_person = source.contact_person
            target.customer_contact_display = source.contact_display
            target.customer_contact_mobile = source.contact_mobile
            target.customer_contact_email = source.contact_email

        else:
            target.customer = ""
            target.customer_name = ""

        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(source, target, source_parent):
        target.schedule_date = source.delivery_date
        target.qty = flt(source.qty) - (flt(source.ordered_qty) / flt(source.conversion_factor))
        target.stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
        target.project = source_parent.project

    suppliers = [item.get("supplier") for item in selected_items if item.get("supplier")]
    suppliers = list(dict.fromkeys(suppliers))  # remove duplicates while preserving order

    items_to_map = [item.get("item_code") for item in selected_items if item.get("item_code")]
    items_to_map = list(set(items_to_map))

    if not suppliers:
        frappe.throw(
            _("Please set a Supplier against the Items to be considered in the Purchase Order.")
        )

    purchase_orders = []
    for supplier in suppliers:
        doc = get_mapped_doc(
            "Sales Order",
            source_name,
            {
                "Sales Order": {
                    "doctype": "Purchase Order",
                    "field_no_map": [
                        "address_display",
                        "contact_display",
                        "contact_mobile",
                        "contact_email",
                        "contact_person",
                        "taxes_and_charges",
                        "shipping_address",
                        "terms",
                    ],
                    "validation": {"docstatus": ["=", 1]},
                },
                "Sales Order Item": {
                    "doctype": "Purchase Order Item",
                    "field_map": [
                        ["name", "sales_order_item"],
                        ["parent", "sales_order"],
                        ["stock_uom", "stock_uom"],
                        ["uom", "uom"],
                        ["conversion_factor", "conversion_factor"],
                        ["delivery_date", "schedule_date"],
                    ],
                    "field_no_map": [
                        "rate",
                        "price_list_rate",
                        "item_tax_template",
                        "discount_percentage",
                        "discount_amount",
                        "pricing_rules",
                    ],
                    "postprocess": update_item,
                    "condition": lambda doc: doc.ordered_qty < doc.stock_qty
                    and doc.supplier == supplier
                    and doc.item_code in items_to_map,
                },
            },
            target_doc,
            set_missing_values,
        )

        doc.insert()
        frappe.db.commit()
        purchase_orders.append(doc)

    return purchase_orders


@frappe.whitelist()
def make_purchase_order(source_name, selected_items=None, target_doc=None):
    if not selected_items:
        return

    if isinstance(selected_items, str):
        selected_items = json.loads(selected_items)

    items_to_map = [
        item.get("item_code")
        for item in selected_items
        if item.get("item_code") and item.get("item_code")
    ]
    items_to_map = list(set(items_to_map))

    def is_drop_ship_order(target):
        drop_ship = True
        for item in target.items:
            if not item.delivered_by_supplier:
                drop_ship = False
                break

        return drop_ship

    def set_missing_values(source, target):
        target.supplier = ""
        target.apply_discount_on = ""
        target.additional_discount_percentage = 0.0
        target.discount_amount = 0.0
        target.inter_company_order_reference = ""
        target.shipping_rule = ""

        if is_drop_ship_order(target):
            target.customer = source.customer
            target.customer_name = source.customer_name
            target.shipping_address = source.shipping_address_name
        else:
            target.customer = target.customer_name = target.shipping_address = None

        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(source, target, source_parent):
        target.schedule_date = source.delivery_date
        target.qty = flt(source.qty) - (flt(source.ordered_qty) / flt(source.conversion_factor))
        target.stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
        target.project = source_parent.project

    def update_item_for_packed_item(source, target, source_parent):
        target.qty = flt(source.qty) - flt(source.ordered_qty)

    # po = frappe.get_list("Purchase Order", filters={"sales_order":source_name, "supplier":supplier, "docstatus": ("<", "2")})
    doc = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Purchase Order",
                "field_no_map": [
                    "address_display",
                    "contact_display",
                    "contact_mobile",
                    "contact_email",
                    "contact_person",
                    "taxes_and_charges",
                    "shipping_address",
                    "terms",
                ],
                "validation": {"docstatus": ["=", 1]},
            },
            "Sales Order Item": {
                "doctype": "Purchase Order Item",
                "field_map": [
                    ["name", "sales_order_item"],
                    ["parent", "sales_order"],
                    ["stock_uom", "stock_uom"],
                    ["uom", "uom"],
                    ["conversion_factor", "conversion_factor"],
                    ["delivery_date", "schedule_date"],
                ],
                "field_no_map": [
                    "rate",
                    "price_list_rate",
                    "item_tax_template",
                    "discount_percentage",
                    "discount_amount",
                    "supplier",
                    "pricing_rules",
                ],
                "postprocess": update_item,
                "condition": lambda doc: doc.ordered_qty < doc.stock_qty
                and doc.item_code in items_to_map
                and not is_product_bundle(doc.item_code),
            },
            "Packed Item": {
                "doctype": "Purchase Order Item",
                "field_map": [
                    ["name", "sales_order_packed_item"],
                    ["parent", "sales_order"],
                    ["uom", "uom"],
                    ["conversion_factor", "conversion_factor"],
                    ["parent_item", "product_bundle"],
                    ["rate", "rate"],
                ],
                "field_no_map": [
                    "price_list_rate",
                    "item_tax_template",
                    "discount_percentage",
                    "discount_amount",
                    "supplier",
                    "pricing_rules",
                ],
                "postprocess": update_item_for_packed_item,
                "condition": lambda doc: doc.parent_item in items_to_map,
            },
        },
        target_doc,
        set_missing_values,
    )

    set_delivery_date(doc.items, source_name)

    return doc


def set_delivery_date(items, sales_order):
    delivery_dates = frappe.get_all(
        "Sales Order Item", filters={"parent": sales_order}, fields=["delivery_date", "item_code"]
    )

    delivery_by_item = frappe._dict()
    for date in delivery_dates:
        delivery_by_item[date.item_code] = date.delivery_date

    for item in items:
        if item.product_bundle:
            item.schedule_date = delivery_by_item[item.product_bundle]


def is_product_bundle(item_code):
    return frappe.db.exists("Product Bundle", {"name": item_code, "disabled": 0})


@frappe.whitelist()
def make_work_orders(items, sales_order, company, project=None):
    """Make Work Orders against the given Sales Order for the given `items`"""
    items = json.loads(items).get("items")
    out = []

    for i in items:
        if not i.get("bom"):
            frappe.throw(_("Please select BOM against item {0}").format(i.get("item_code")))
        if not i.get("pending_qty"):
            frappe.throw(_("Please select Qty against item {0}").format(i.get("item_code")))

        work_order = frappe.get_doc(
            dict(
                doctype="Work Order",
                production_item=i["item_code"],
                bom_no=i.get("bom"),
                qty=i["pending_qty"],
                company=company,
                sales_order=sales_order,
                sales_order_item=i["sales_order_item"],
                project=project,
                fg_warehouse=i["warehouse"],
                description=i["description"],
            )
        ).insert()
        work_order.set_work_order_operations()
        work_order.flags.ignore_mandatory = True
        work_order.save()
        out.append(work_order)

    return [p.name for p in out]


@frappe.whitelist()
def update_status(status, name):
    so = frappe.get_doc("Sales Order", name)
    # so.update_status(status)


@frappe.whitelist()
def make_raw_material_request(items, company, sales_order, project=None):
    if not frappe.has_permission("Sales Order", "write"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if isinstance(items, str):
        items = frappe._dict(json.loads(items))

    for item in items.get("items"):
        item["include_exploded_items"] = items.get("include_exploded_items")
        item["ignore_existing_ordered_qty"] = items.get("ignore_existing_ordered_qty")
        item["include_raw_materials_from_sales_order"] = items.get(
            "include_raw_materials_from_sales_order"
        )

    items.update({"company": company, "sales_order": sales_order})

    raw_materials = get_items_for_material_requests(items)
    if not raw_materials:
        frappe.msgprint(
            _("Material Request not created, as quantity for Raw Materials already available.")
        )
        return

    material_request = frappe.new_doc("Material Request")
    material_request.update(
        dict(
            doctype="Material Request",
            transaction_date=nowdate(),
            company=company,
            material_request_type="Purchase",
        )
    )
    for item in raw_materials:
        item_doc = frappe.get_cached_doc("Item", item.get("item_code"))

        schedule_date = add_days(nowdate(), cint(item_doc.lead_time_days))
        row = material_request.append(
            "items",
            {
                "item_code": item.get("item_code"),
                "qty": item.get("quantity"),
                "schedule_date": schedule_date,
                "warehouse": item.get("warehouse"),
                "sales_order": sales_order,
                "project": project,
            },
        )

        if not (strip_html(item.get("description")) and strip_html(item_doc.description)):
            row.description = item_doc.item_name or item.get("item_code")

    material_request.insert()
    material_request.flags.ignore_permissions = 1
    material_request.run_method("set_missing_values")
    material_request.submit()
    return material_request


@frappe.whitelist()
def make_inter_company_purchase_order(source_name, target_doc=None):
    from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction

    return make_inter_company_transaction("Sales Order", source_name, target_doc)


@frappe.whitelist()
def create_pick_list(source_name, target_doc=None):
    from erpnext.stock.doctype.packed_item.packed_item import is_product_bundle

    def validate_sales_order():
        so = frappe.get_doc("Sales Order", source_name)
        for item in so.items:
            if item.stock_reserved_qty > 0:
                frappe.throw(
                    _(
                        "Cannot create a pick list for Sales Order {0} because it has reserved stock. Please unreserve the stock in order to create a pick list."
                    ).format(frappe.bold(source_name))
                )

    def update_item_quantity(source, target, source_parent) -> None:
        picked_qty = flt(source.picked_qty) / (flt(source.conversion_factor) or 1)
        qty_to_be_picked = flt(source.qty) - max(picked_qty, flt(source.delivered_qty))

        target.qty = qty_to_be_picked
        target.stock_qty = qty_to_be_picked * flt(source.conversion_factor)

    def update_packed_item_qty(source, target, source_parent) -> None:
        qty = flt(source.qty)
        for item in source_parent.items:
            if source.parent_detail_docname == item.name:
                picked_qty = flt(item.picked_qty) / (flt(item.conversion_factor) or 1)
                pending_percent = (item.qty - max(picked_qty, item.delivered_qty)) / item.qty
                target.qty = target.stock_qty = qty * pending_percent
                return

    def should_pick_order_item(item) -> bool:
        return (
            abs(item.delivered_qty) < abs(item.qty)
            and item.delivered_by_supplier != 1
            and not is_product_bundle(item.item_code)
        )

    # Don't allow a Pick List to be created against a Sales Order that has reserved stock.
    validate_sales_order()

    doc = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Pick List",
                "field_map": {"set_warehouse": "parent_warehouse"},
                "validation": {"docstatus": ["=", 1]},
            },
            "Sales Order Item": {
                "doctype": "Pick List Item",
                "field_map": {"parent": "sales_order", "name": "sales_order_item"},
                "postprocess": update_item_quantity,
                "condition": should_pick_order_item,
            },
            "Packed Item": {
                "doctype": "Pick List Item",
                "field_map": {
                    "parent": "sales_order",
                    "name": "sales_order_item",
                    "parent_detail_docname": "product_bundle_item",
                },
                "field_no_map": ["picked_qty"],
                "postprocess": update_packed_item_qty,
            },
        },
        target_doc,
    )

    doc.purpose = "Delivery"

    doc.set_item_locations()

    return doc


def update_produced_qty_in_so_item(sales_order, sales_order_item):
    # for multiple work orders against same sales order item
    linked_wo_with_so_item = frappe.db.get_all(
        "Work Order",
        ["produced_qty"],
        {"sales_order_item": sales_order_item, "sales_order": sales_order, "docstatus": 1},
    )

    total_produced_qty = 0
    for wo in linked_wo_with_so_item:
        total_produced_qty += flt(wo.get("produced_qty"))

    if not total_produced_qty and frappe.flags.in_patch:
        return

    frappe.db.set_value("Sales Order Item", sales_order_item, "produced_qty", total_produced_qty)


@frappe.whitelist()
def get_work_order_items(sales_order, for_raw_material_request=0):
    """Returns items with BOM that already do not have a linked work order"""
    if sales_order:
        so = frappe.get_doc("Sales Order", sales_order)

        wo = qb.DocType("Work Order")

        items = []
        item_codes = [i.item_code for i in so.items]
        product_bundle_parents = [
            pb.new_item_code
            for pb in frappe.get_all(
                "Product Bundle", {"new_item_code": ["in", item_codes], "disabled": 0}, ["new_item_code"]
            )
        ]

        for table in [so.items, so.packed_items]:
            for i in table:
                bom = get_default_bom(i.item_code)
                stock_qty = i.qty if i.doctype == "Packed Item" else i.stock_qty

                if not for_raw_material_request:
                    total_work_order_qty = flt(
                        qb.from_(wo)
                        .select(Sum(wo.qty))
                        .where(
                            (wo.production_item == i.item_code)
                            & (wo.sales_order == so.name)
                            & (wo.sales_order_item == i.name)
                            & (wo.docstatus.lt(2))
                        )
                        .run()[0][0]
                    )
                    pending_qty = stock_qty - total_work_order_qty
                else:
                    pending_qty = stock_qty

                if pending_qty and i.item_code not in product_bundle_parents:
                    items.append(
                        dict(
                            name=i.name,
                            item_code=i.item_code,
                            description=i.description,
                            bom=bom or "",
                            warehouse=i.warehouse,
                            pending_qty=pending_qty,
                            required_qty=pending_qty if for_raw_material_request else 0,
                            sales_order_item=i.name,
                        )
                    )

        return items


# Custom Script

# @frappe.whitelist()
# def make_approved(docname):
#     # Your logic here
#     doc = frappe.get_doc('Sales Order', docname)
    
#     # Iterate through items in the child table
#     # for item in doc.items:
#     #     # Update item status before inserting and submitting Rental Order
#     #     if update_item_status(item.item_code):
#     #         # Create a new Rental Order document
#     #         new_rental_order = frappe.new_doc('Rental Order')
            
#     #         # Set fields based on the original document
#     #         new_rental_order.customer = doc.customer
#     #         new_rental_order.start_date = doc.start_date
#     #         new_rental_order.end_date = doc.end_date
#     #         new_rental_order.sales_order_id = doc.name
#     #         new_rental_order.order_type = doc.order_type
#     #         new_rental_order.taxes_and_charges = doc.taxes_and_charges

#     #         # Add other fields as needed
            
#     #         # Create a new items child table in the Rental Order document
#     #         new_item = new_rental_order.append('items')
            
#     #         # Set fields based on the item in the original document's child table
#     #         new_item.item_group = item.item_group
#     #         new_item.item_code1 = item.item_code
#     #         new_item.qty = item.qty
#     #         new_item.rate = item.rate
#     #         new_item.amount = item.amount
#     #         new_item.rental_tax_rate = item.rental_tax_rate
#     #         new_item.tax_amount = item.tax_amount
#     #         new_item.line_total = item.line_total
#     #         new_item.item_tax_template = item.item_tax_template
#     #         # Add other fields as needed

#     #         # Set new_rental_order.total based on the sum of item.amount and taxes
#     #         new_rental_order.total = item.amount

#     #         total_taxes_and_charges = 0  # Initialize the variable to store the sum of tax_amount
            
#     #         # Iterate through taxes in the original document
#     #         for tax in doc.get('taxes', []):
#     #             new_tax = new_rental_order.append('taxes')
#     #             new_tax.charge_type = tax.charge_type
#     #             new_tax.account_head = tax.account_head
#     #             new_tax.description = tax.description
#     #             new_tax.cost_center = tax.cost_center
#     #             new_tax.rate = tax.rate
#     #             new_tax.tax_amount = item.amount * tax.rate / 100
#     #             total_taxes_and_charges += new_tax.tax_amount  # Add tax_amount to the total

#     #         # Set new_rental_order.total_taxes_and_charges based on the sum of tax_amount
#     #         new_rental_order.total_taxes_and_charges = total_taxes_and_charges

#     #         # Set new_rental_order.grand_total and new_rental_order.rounded_total
#     #         new_rental_order.grand_total = new_rental_order.total + new_rental_order.total_taxes_and_charges
#     #         new_rental_order.rounded_total = new_rental_order.grand_total

#     #         # Save the new Rental Order document
#     #         new_rental_order.insert()
#     #         new_rental_order.submit()
    
#     # Update the status of the original document
#     doc.status = 'Approved'
#     doc.save()

#     return "Approved Success"


@frappe.whitelist()
def make_approved(docname):
    try:
        # Fetch Sales Order Item records with the given docname as parent
        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name", "item_code"])

        # Iterate through the fetched Sales Order Items
        for item in sales_order_items:
            # Fetch the Item document
            item_doc = frappe.get_doc('Item', item.item_code)

            # Update the item status to "Reserved" if it's available
            if item_doc.status in ["Available", "Pre Reserved"]:
                item_doc.status = 'Reserved'
                item_doc.save()
                frappe.msgprint(f'Item {item.item_code} status updated to Reserved')
            else:
                frappe.msgprint(f'Item {item.item_code} is already Booked')
                # If an item is already booked, don't continue to the next steps
                # break
                return False
            # Update child_status to "Approved" for items whose status was successfully updated
            sales_order_item = frappe.get_doc("Sales Order Item", item.name)
            sales_order_item.child_status = "Approved"
            sales_order_item.save()

        # Check if all items in the Sales Order have their status as "Reserved" in the Item master
        # if all(frappe.get_value("Item", {"item_code": item.item_code}, "status") == "Reserved" for item in sales_order_items):
            # Execute your additional code here
            sales_order = frappe.get_doc("Sales Order", docname)
            sales_order.status = "Approved"
            sales_order.save()

        return True

    except Exception as e:
        # Log the error details without the title parameter
        frappe.log_error(f"Error in make_approved: {e}")
        # Reraise the exception to propagate it
        raise
    


import frappe
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

@frappe.whitelist()
def send_approval_email(docname, customer_email_id, payment_link):
    try:
        # Fetch the document based on docname (e.g., Sales Order)
        doc = frappe.get_doc('Sales Order', docname)
        
        # Fetch CC email addresses from Admin Settings
        admin_settings = frappe.get_doc('Admin Settings')
        cc_email_entries = admin_settings.sales_order_email_notification_cc
        cc_email_list = [entry.user for entry in cc_email_entries] if cc_email_entries else []
        # print('cc_email_listttttttttttttttttttttttt',cc_email_list)
        # Determine the URL based on the order type
        if doc.order_type == "Sales":
            pdf_url = frappe.utils.get_url(f"/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Order&name={docname}&format=Nhk%20Sales%20Order&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en")
        elif doc.order_type == "Service":
            pdf_url = frappe.utils.get_url(f"/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Order&name={docname}&format=Nhk%20Service%20Order&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en")
        elif doc.order_type == "Rental":
            pdf_url = frappe.utils.get_url(f"/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Order&name={docname}&format=Nhk%20Rental%20Order&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en")
        else:
            pdf_url = frappe.utils.get_url(f"/api/method/frappe.utils.print_format.download_pdf?doctype=Sales%20Order&name={docname}&format=Nhk%20Rental%20Order&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en")

        # Customize your email subject and content as needed
        subject = f"Sales Order {docname} Approved"

        # Prepare the common part of the message
        message = f"""
            <p>Dear {doc.customer_name},</p>
            <p>Your sales order has been approved. You can proceed to make payment using the following link:</p>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr>
                    <th>Sales Order Id</th>
                    <td>{docname}</td>
                </tr>
                <tr>
                    <th>Order Type</th>
                    <td>{doc.order_type}</td>
                </tr>
                <tr>
                    <th>Order Date</th>
                    <td>{doc.transaction_date}</td>
                </tr>
            """

        # Add specific rows based on order_type
        if doc.order_type == "Rental":
            message += f"""
                <tr>
                    <th>Security Deposit</th>
                    <td>{doc.security_deposit}</td>
                </tr>
                <tr>
                    <th>Rental Amount</th>
                    <td>{doc.rounded_total}</td>
                </tr>
                """
        else:
            message += f"""
                <tr>
                    <th>Total Amount</th>
                    <td>{doc.grand_total}</td>
                </tr>
                """
        
        # Append the payment link row and closing message
        message += f"""
                 <tr>
                    <td colspan="2" style="text-align: center; padding-top: 20px;">
                        <a href="{payment_link}" style="background-color: #4CAF50; /* Green */
                                           border: none;
                                           color: white;
                                           padding: 10px 10px;
                                           text-align: center;
                                           text-decoration: none;
                                           display: inline-block;
                                           font-size: 14px;
                                           margin-top: 10px;
                                           cursor: pointer;">Make Payment</a>
                    </td>
                </tr>
            </table>
            
            <p>Best regards,<br>NHK MEDICAL PRIVATE LIMITED</p>
            """

        # Fetch the PDF content using requests library
        pdf_response = requests.get(pdf_url)
        pdf_content = pdf_response.content

        # Create email message container
        msg = MIMEMultipart()
        msg['From'] = "NHK MEDICAL PRIVATE LIMITED"
        msg['To'] = customer_email_id
        msg['Cc'] = ", ".join(cc_email_list)
        msg['Subject'] = subject
        
        # Attach body of email
        msg.attach(MIMEText(message, 'html'))
        
        # Attach the PDF file
        attachment = MIMEApplication(pdf_content, _subtype="pdf")
        attachment.add_header('Content-Disposition', 'attachment', filename=f'Sales_Order_{docname}.pdf')
        msg.attach(attachment)

        # SMTP setup
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_username = 'support@nhkmedical.com'
        smtp_password = 'zpvr bmkd nqaz qnxe'
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        server.login(smtp_username, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_username, [customer_email_id] + cc_email_list, text)
        server.quit()
        # print("Email sent successfully!")
        
        return True
    except Exception as e:
        frappe.log_error(f"Error sending approval email for Sales Order {docname}: {e}")
        return False







    
@frappe.whitelist()
def make_sales_approved(docname):
    try:
        sales_order = frappe.get_doc("Sales Order", docname)
        sales_order.status = "Order"
        sales_order.save()

        return "Approved Success"

    except Exception as e:
        # Log the error details without the title parameter
        frappe.log_error(f"Error in make_approved: {e}")
        # Reraise the exception to propagate it
        raise


@frappe.whitelist()
def make_rental_device_assign(docname, item_group, item_code):
    try:
        # Your logic here
        doc = frappe.get_doc('Sales Order', docname)

        # Check if the user has permission to update the Item doctype
        frappe.only_for('Item', 'write')

        item_status = frappe.get_value("Item", item_code, "status")

        if item_status == "Available":
            item_doc = frappe.get_doc("Item", item_code)
            item_doc.status = "Reserved"
            item_doc.save()
            # Optionally, you may want to commit the changes to the database
            frappe.db.commit()

            # Set values for rental device and update status
            doc.item_group = item_group
            doc.item_code = item_code
            doc.status = 'Rental Device Assigned'
            doc.save()

            return "Rental Device Assigned Success"
        else:
            frappe.msgprint("Item is not available for reservation.")

    except Exception as e:
        frappe.log_error(f"Error in make_rental_device_assign: {e}")
        frappe.throw("An error occurred while processing the request. Please try again.")



@frappe.whitelist()
def make_ready_for_delivery(docname, technician_name, technician_mobile, technician_id):
    try:
        # Get the 'Sales Order' document
        rental_group_order = frappe.get_doc('Sales Order', docname)
        technician_type = 'Delivery'
        patient_id = rental_group_order.customer
        # Update the status of the 'Sales Order'
        rental_group_order.status = 'Ready for Delivery'
        rental_group_order.custom_technician_id_before_delivered = technician_id
        
        # Fetch Sales Order Item records with the given docname as parent
        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])

        # Start a transaction
        frappe.db.begin()

        # Save the sales order
        rental_group_order.save(ignore_permissions=True)

        # Iterate through the fetched Sales Order Items and update their child_status to "Ready for Delivery"
        for item in sales_order_items:
            sales_order_item = frappe.get_doc("Sales Order Item", item.name)
            sales_order_item.child_status = "Ready for Delivery"
            sales_order_item.technician_id_before_deliverd = technician_id
            sales_order_item.save(ignore_permissions=True)
        if technician_id:
        # Create an entry in the Technician Visit Entry doctype
            create_technician_portal_entry(technician_id, technician_type, docname,patient_id)

        # Commit the transaction if everything is successful
        frappe.db.commit()
        
        return "Ready for Delivery Success"

    except Exception as e:
        # If any error occurs, rollback the transaction
        frappe.db.rollback()
        frappe.throw(f"An error occurred: {str(e)}")

# New function to create an entry in the Technician Visit Entry doctype
def create_technician_portal_entry(technician_id, technician_type, sales_order_id,patient_id=None,item_code=None):
    try:
        # Create a new document in the 'Technician Visit Entry' doctype
        technician_portal_entry = frappe.get_doc({
            "doctype": "Technician Visit Entry",
            "sales_order_id": sales_order_id,
            "technician_id": technician_id,
            "type": technician_type,
            "status": "Assigned",
            "patient_id":patient_id,
            "item_code":item_code
        })
        
        # Insert the new entry into the database
        technician_portal_entry.insert()
        
        # Get the technician_user_id from the inserted Technician Visit Entry entry
        technician_user_id = technician_portal_entry.technician_user_id  # Assuming the field is 'technician_user_id'
        
        # Share the document with the user
        share_document_with_user(technician_portal_entry.name, technician_user_id)

    except Exception as e:
        # If an exception occurs, throw an error
        frappe.throw(f"Error in creating Technician Visit Entry entry: {str(e)}")


def share_document_with_user(docname, user_id):
    try:
        # Share the document with a particular user
        frappe.share.add(
            doctype="Technician Visit Entry",  # Specify the doctype
            name=docname,                 # Specify the document name
            user=user_id,                 # Get the technician_user_id from the created entry
            read=1,                       # Grant read permission
            write=1,                      # Grant write permission if needed
        )
        frappe.msgprint(f"Document {docname} shared with user {user_id}.")

    except Exception as e:
        # If an exception occurs, throw an error
        frappe.throw(f"Error in sharing document: {str(e)}")



def apply_item_filter(doc, method):
    for item in doc.items:
        # Check if the item group is 'Rental'
        if frappe.get_value('Item', item.item_code, 'item_group') != 'Rental':
            frappe.throw(f"Item {item.item_code} is not in the 'Rental' item group. Remove it from the Sales Order.")

@frappe.whitelist()
def make_dispatch(docname, dispatch_date):
    try:
        # Get the 'Sales Order' document
        rental_sales_order = frappe.get_doc('Sales Order', docname)

        # Update Sales Order with the entered dispatch_date
        rental_sales_order.dispatch_date = dispatch_date
        rental_sales_order.status = "DISPATCHED"
        rental_sales_order.save(ignore_permissions=True)

        # Fetch Sales Order Item records with the given docname as parent
        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])

        # Iterate through the fetched Sales Order Items and update their child_status to "DISPATCHED"
        for item in sales_order_items:
            sales_order_item = frappe.get_doc("Sales Order Item", item.name)
            sales_order_item.child_status = "DISPATCHED"
            sales_order_item.dispatch_date = dispatch_date
            sales_order_item.save(ignore_permissions=True)

        # Optionally, you may want to commit the changes to the database
        # frappe.db.commit()

        return "Rental Device DISPATCHED Success"

    except Exception as e:
        # Log any errors that occur
        frappe.log_error(f"Error in make_dispatch: {e}")
        frappe.throw("An error occurred while processing the request. Please try again.")


@frappe.whitelist()
def make_rental_device_assign(docname, item_group, item_code):
    try:
        doc = frappe.get_doc('Sales Order', docname)

        # Check if the user has permission to update or cancel the Item doctype
        frappe.only_for('Item', ['write', 'cancel'])

        item_status = frappe.get_value("Item", item_code, "status")

        if item_status == "Available":
            # Update Item status to Reserved
            item_doc = frappe.get_doc("Item", item_code)
            item_doc.status = "Reserved"
            item_doc.save(ignore_permissions=True)
            frappe.db.commit()

            # Set values for rental device and update status
            doc.item_group = item_group
            doc.item_code = item_code
            doc.status = 'Rental Device Assigned'
            doc.save(ignore_permissions=True)

            return "Rental Device Assigned Success"
        else:
            frappe.msgprint("Item is not available for reservation.")

    except frappe.DoesNotExistError:
        # Handle the case where the sale order is canceled
        # Update Item status to Available
        item_doc = frappe.get_doc("Item", item_code)
        item_doc.status = "Available"
        item_doc.save()
        frappe.db.commit()

        # Set values for rental device and update status
        doc.item_group = None
        doc.item_code = None
        doc.status = 'Cancelled'
        doc.save()

        return "Rental Device Assignment Cancelled"

    except Exception as e:
        frappe.log_error(f"Error in make_rental_device_assign: {e}")
        frappe.throw("An error occurred while processing the request. Please try again.")



@frappe.whitelist()
def make_delivered(docname,customer_name, delivered_date, rental_order_agreement_attachment=None, aadhar_card_attachment=None, payment_pending_reasons=None, notes=None):
    try:
        # print (payment_pending_reasons,notes)
        # Get the 'Sales Order' document
        rental_group_order = frappe.get_doc('Sales Order', docname)

        # Update each child item and its status
        for item in rental_group_order.items:
            # Get the item code from the child table
            item_code = item.item_code
            # Update the item status to "Rented Out"
            item_doc = frappe.get_doc("Item", item_code)
            if item_doc.status == 'Reserved':
                item_doc.status = "Rented Out"
                item_doc.customer_n = customer_name
                item_doc.custom_sales_order_id = docname
                item_doc.save(ignore_permissions=True)
            else:
                frappe.throw('Item Is Not Reserved')

        # Update values for rental device and update status in Sales Order
        rental_group_order.rental_delivery_date = delivered_date
        rental_group_order.reason_for_payment_pending = payment_pending_reasons
        rental_group_order.payment_pending_reason = notes
        rental_group_order.rental_order_agreement_attachment = rental_order_agreement_attachment
        rental_group_order.aadhar_card_attachment = aadhar_card_attachment
        rental_group_order.status = 'Active'
        rental_group_order.save(ignore_permissions=True)

        # Update status in related Sales Order Items
        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])
        for item in sales_order_items:
            sales_order_item = frappe.get_doc("Sales Order Item", item.name)
            sales_order_item.child_status = "Active"
            sales_order_item.rental_delivery_date = delivered_date
            sales_order_item.save(ignore_permissions=True)

        return "Rental Device DELIVERED Success"

    except Exception as e:
        # Log any errors that occur
        frappe.log_error(f"Error in make_delivered: {e}")
        frappe.throw("An error occurred while processing the request. Please try again.")

@frappe.whitelist()
def make_ready_for_pickup(docname, pickup_date, pickup_reason,pickup_remark,technician_name=None,technician_mobile=None,technician_id=None ):
    try:
        # Get the 'Sales Order' document
        doc = frappe.get_doc('Sales Order', docname)
        technician_type = 'Pickup'
        patient_id = doc.customer
        # Set values for pickup date and update status
        doc.pickup_date = pickup_date
        doc.status = 'Ready for Pickup'
        doc.pickup_reason = pickup_reason
        doc.pickup_remark = pickup_remark
        doc.custom_technician_id_pickup = technician_id
        frappe.db.begin()
        # doc.technician_mobile_after_delivered = technician_mobile
        doc.save(ignore_permissions=True)

        # Update status and pickup date in related Sales Order Items
        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])
        for item in sales_order_items:
            sales_order_item = frappe.get_doc("Sales Order Item", item.name)
            sales_order_item.child_status = "Ready for Pickup"
            sales_order_item.pickup_date = pickup_date
            sales_order_item.pickup_reason = pickup_reason
            sales_order_item.pickup_remark = pickup_remark
            sales_order_item.technician_id_after_delivered = technician_id
            # sales_order_item.technician_mobile_after_delivered = technician_mobile
            sales_order_item.save(ignore_permissions=True)
        if technician_id:
            create_technician_portal_entry(technician_id, technician_type,docname,patient_id)

        return "Sales Order is Ready for Pickup"

    except Exception as e:
        frappe.db.rollback()
        # Log any errors that occur
        frappe.log_error(f"Error in make_ready_for_pickup: {e}")
        frappe.throw("An error occurred while processing the request. Please try again.")

@frappe.whitelist()
def make_pickedup(docname, pickup_date):
    try:
        # Get the 'Sales Order' document
        doc = frappe.get_doc('Sales Order', docname)

        # Set values for technician name and mobile
        doc.picked_up = pickup_date
        # doc.technician_mobile = technician_mobile

        # Update status to 'Picked Up'
        doc.status = 'Picked Up'
        doc.save(ignore_permissions=True)

        # Update status in related Sales Order Items
        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])
        for item in sales_order_items:
            sales_order_item = frappe.get_doc("Sales Order Item", item.name)
            sales_order_item.child_status = "Picked Up"
            sales_order_item.pickup_date = pickup_date
            # sales_order_item.technician_mobile = technician_mobile
            sales_order_item.save(ignore_permissions=True)

        return "Sales Order is marked as Picked Up."

    except Exception as e:
        # Log any errors that occur
        frappe.log_error(f"Error in make_pickedup: {e}")
        frappe.throw("An error occurred while processing the request. Please try again.")

import ast

@frappe.whitelist()
def make_submitted_to_office(docname, item_code, submitted_date):
    try:
        # Convert the string representation of the list to an actual list
        item_codes = ast.literal_eval(item_code)
        # print('asdddddddddddddddddddddddddddddddddddddddddddd',item_codes)
        # Get the 'Sales Order' document
        doc = frappe.get_doc('Sales Order', docname)

        # Update status of items to "Available"
        for item_code in item_codes:
            item_doc = frappe.get_doc("Item", item_code)
            if item_doc.status == 'Rented Out':
                item_doc.status = "Available"
                item_doc.customer_n = ""
                item_doc.customer_name = ""
                item_doc.custom_sales_order_id = ""
                item_doc.save(ignore_permissions=True)
            else:
                frappe.throw('Current item Status is Not Rented Out')

        # Set values for submission to office and update status
        doc.submitted_date = submitted_date
        doc.status = 'Submitted to Office'
        doc.save(ignore_permissions=True)

        # Update status in related Sales Order Items
        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])
        for item in sales_order_items:
            sales_order_item = frappe.get_doc("Sales Order Item", item.name)
            sales_order_item.child_status = "Submitted to Office"
            sales_order_item.submitted_date = submitted_date
            sales_order_item.save(ignore_permissions=True)

        return "Submitted to Office Success"

    except Exception as e:
        # Log any errors that occur
        frappe.log_error(f"Error in make_submitted_to_office: {e}")
        frappe.throw("An error occurred while processing the request. Please try again.")



@frappe.whitelist()
def make_order_completed(docname, item_code):
    try:
        # Start a database transaction
        frappe.db.sql("START TRANSACTION")

        # Convert the string representation of the list to an actual list
        item_codes = ast.literal_eval(item_code)

        # Get the 'Sales Order' document
        doc = frappe.get_doc('Sales Order', docname)

        # Check payment and security deposit status
        if doc.payment_status != "Paid" or doc.security_deposit_status != "Paid":
            frappe.throw(_("Both Payment Status and Security Deposit Status must be 'Paid' to complete the order."))

        # Update Sales Order status to 'Rental SO Completed'
        doc.status = 'Rental SO Completed'
        doc.save(ignore_permissions=True)

        # Update status in related Sales Order Items
        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])
        for item in sales_order_items:
            sales_order_item = frappe.get_doc("Sales Order Item", item.name)
            sales_order_item.child_status = "Rental SO Completed"
            sales_order_item.save(ignore_permissions=True)

        # Commit the transaction if no errors occurred
        frappe.db.commit()

        return "Rental SO Completed Success"

    except Exception as e:
        # Rollback the transaction to undo any changes if an error occurs
        frappe.db.rollback()
        frappe.log_error(f"Error in make_order_completed: {e}")
        frappe.throw(_("An error occurred while processing the request. No changes were made. Please try again."))



@frappe.whitelist()
def on_hold(docname):
    doc = frappe.get_doc('Sales Order', docname)
    
    # Perform any server-side logic here, e.g., update some fields, perform calculations, etc.
    
    # Update the status to 'On Hold'
    doc.set('status', 'On Hold')
    doc.save()

    frappe.msgprint(_('Document Hold successfully.'))

    return True


# your_module/doctype/rental_group_order/rental_group_order.py
from frappe import _

@frappe.whitelist()
def update_status(docname, new_status):
    doc = frappe.get_doc('Sales Order', docname)
    
    # Perform any server-side logic here, e.g., update some fields, perform calculations, etc.
    
    # Update the status to the new status
    doc.set('status', new_status)
    doc.save()

    # frappe.msgprint(_('Document status updated successfully.'))
    return True



@frappe.whitelist()
def close_rental_order(docname):
    doc = frappe.get_doc('Sales Order', docname)

    # Perform any necessary validation or logic before closing the order

    # Update the status to 'Closed'
    doc.set('status', 'Closed')
    doc.save()

    frappe.msgprint(_('Rental Order Closed successfully.'))
    return True





# In sales_order.py

@frappe.whitelist()
def get_sales_order_items_status():
    sales_orders = frappe.db.get_all('Sales Order', filters={'status': ['in', ['Active', 'Ready for Pickup', 'Picked Up']],'docstatus':1}, fields=['name'])

    if not sales_orders:
        return {'message': 'No Sales Orders found with the specified statuses.'}

    item_code_map = {}
    results = []

    # Collect item codes and their corresponding sales order IDs
    for so in sales_orders:
        items = frappe.get_all('Sales Order Item', filters={'parent': so.name}, fields=['item_code'])
        for item in items:
            if item.item_code not in item_code_map:
                item_code_map[item.item_code] = []
            item_code_map[item.item_code].append(so.name)

    # Identify repeated item codes
    repeated_items = {item_code: so_ids for item_code, so_ids in item_code_map.items() if len(so_ids) > 1}

    if not repeated_items:
        return {'message': 'No repeated items found.'}

    # Fetch item status from Item doctype for repeated item codes
    for item_code, so_ids in repeated_items.items():
        item_status = frappe.db.get_value('Item', item_code, 'status')
        for so_id in so_ids:
            results.append({'sales_order': so_id, 'item_code': item_code, 'status': item_status})

    # Format results as a string
    formatted_results = "\n".join([f"Sales Order: {r['sales_order']}, Item Code: {r['item_code']}, Status: {r['status']}" for r in results])
    return {'message': formatted_results}




@frappe.whitelist()
def get_repeated_sales_orders():
    # Define the item statuses to filter
    item_statuses = ['Rented Out', 'Reserved', 'Pre Reserved']
    
    # Create a string for the IN clause in SQL
    status_list = "', '".join(item_statuses)
    
    # Construct the SQL query
    query = f"""
        SELECT 
            so.name AS sales_order,
            soi.item_code,
            i.status
        FROM
            `tabSales Order` AS so
        JOIN
            `tabSales Order Item` AS soi ON so.name = soi.parent
        JOIN
            `tabItem` AS i ON soi.item_code = i.name
        WHERE
            so.status = 'Active'
            AND so.docstatus = 1
            AND i.status IN ('{status_list}')
        ORDER BY 
            soi.item_code, so.name
    """

    results = frappe.db.sql(query, as_dict=True)

    # Find repeated sales orders
    repeated_orders = {}
    for row in results:
        if row['item_code'] not in repeated_orders:
            repeated_orders[row['item_code']] = set()
        repeated_orders[row['item_code']].add(row['sales_order'])
    
    repeated_sales_orders = []
    for item_code, orders in repeated_orders.items():
        if len(orders) > 1:  # If there are more than one sales orders for the item
            repeated_sales_orders.extend(orders)

    # Return results in the expected format
    return {'message': repeated_sales_orders}



import frappe

@frappe.whitelist()
def sales_order_for_html(sales_order_id):
    sales_order_items = frappe.get_all("Sales Order Item",
                                       filters={"parent": sales_order_id},
                                       fields=["name", "child_status", "item_code", "item_group", "rate", "amount", "tax_amount", "line_total","replaced_item_code"])

    items_data = []
    for item in sales_order_items:
        item_doc = frappe.get_doc("Item", item.item_code)
        item_status = item_doc.status if item_doc else None
        item_data = {
            "name": item.name,
            "child_status": item.child_status,
            "item_code": item.item_code,
            "item_group": item.item_group,
            "rate": item.rate,
            "amount": item.amount,
            "tax_amount": item.tax_amount,
            "line_total": item.line_total,
            "item_status": item_status
        }
        items_data.append(item_data)

    return items_data



@frappe.whitelist()
def update_status_to_ready_for_pickup(item_code, pickup_datetime, docname, child_name,pickupReason,pickupRemark,technician_id=None,technician_mobile=None):
    # print('qqqqqqqqqqqqqqqqqqqqqqqq',item_code, pickup_datetime, docname, child_name,pickupReason,pickupRemark)
    # Retrieve Rental Orders based on the item_code field in the items child table
    sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])
    sales_order_doc = frappe.get_doc("Sales Order", docname)
    patient_id = sales_order_doc.customer
    if sales_order_items:
        # If there is only one Sales Order Item, update both Sales Order and Sales Order Item statuses
        if len(sales_order_items) == 1:
            sales_order_item_doc = frappe.get_doc("Sales Order Item", sales_order_items[0].name)
            sales_order_item_doc.child_status = "Ready for Pickup"
            sales_order_item_doc.pickup_date = pickup_datetime
            sales_order_item_doc.pickup_remark = pickupRemark
            sales_order_item_doc.pickup_reason = pickupReason
            sales_order_item_doc.technician_id_after_delivered = technician_id
            # sales_order_item_doc.technician_mobile_after_delivered = technician_mobile
            sales_order_item_doc.save(ignore_permissions=True)

            # Retrieve the Sales Order document and update its status
            
            # print('patient_iddddddddddddddddddddddddddddddddddddd',patient_id)
            sales_order_doc.status = "Ready for Pickup"
            sales_order_doc.pickup_date = pickup_datetime
            sales_order_doc.pickup_remark = pickupRemark
            sales_order_doc.pickup_reason = pickupReason
            sales_order_doc.custom_technician_id_pickup = technician_id
            # sales_order_doc.technician_mobile_after_delivered = technician_mobile
            sales_order_doc.save(ignore_permissions=True)
            technician_type = 'Pickup'
            if technician_id:
                create_technician_portal_entry(technician_id, technician_type,docname,patient_id,item_code)

            return True
        else:
            
            # If there are multiple Sales Order Items, update only the Sales Order Item statuses
            sales_order_item_doc = frappe.get_doc("Sales Order Item", {"name": child_name})
            sales_order_item_doc.child_status = "Ready for Pickup"
            sales_order_item_doc.pickup_date = pickup_datetime
            sales_order_item_doc.pickup_remark = pickupRemark
            sales_order_item_doc.pickup_reason = pickupReason
            sales_order_item_doc.technician_id_after_delivered = technician_id
            # sales_order_item_doc.technician_mobile_after_delivered = technician_mobile
            sales_order_item_doc.save(ignore_permissions=True)
            technician_type = 'Pickup'
            if technician_id:
                create_technician_portal_entry(technician_id, technician_type,docname,patient_id,item_code)
            return True
    else:
        return False


@frappe.whitelist()
def update_status_to_picked_up(item_code, docname, child_name,picked_up_datetime):
    # print()
    # Retrieve Rental Orders based on the item_code field in the items child table
    sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])

    if sales_order_items:
        # If there is only one Sales Order Item, update both Sales Order and Sales Order Item statuses
        if len(sales_order_items) == 1:
            sales_order_item_doc = frappe.get_doc("Sales Order Item", sales_order_items[0].name)
            sales_order_item_doc.child_status = "Picked Up"
            sales_order_item_doc.pickup_date = picked_up_datetime
            # sales_order_item_doc.technician_mobile = technician_mobile
            # sales_order_item_doc.pickup_date = pickup_datetime
            sales_order_item_doc.save(ignore_permissions=True)

            # Retrieve the Sales Order document and update its status
            sales_order_doc = frappe.get_doc("Sales Order", sales_order_item_doc.parent)
            sales_order_doc.status = "Picked Up"
            sales_order_doc.pickup_date = picked_up_datetime
            # sales_order_doc.technician_mobile = technician_mobile
            # sales_order_doc.pickup_date = pickup_datetime
            sales_order_doc.save(ignore_permissions=True)

            return True
        else:
            # If there are multiple Sales Order Items, update only the Sales Order Item statuses
            sales_order_item_doc = frappe.get_doc("Sales Order Item", {"name": child_name})
            sales_order_item_doc.child_status = "Picked Up"
            sales_order_item_doc.pickup_date = picked_up_datetime
            # sales_order_item_doc.technician_mobile = technician_mobile
            sales_order_item_doc.save(ignore_permissions=True)

            return True
    else:
        return False




@frappe.whitelist()
def update_status_to_submitted_to_office(item_code, submission_datetime, docname, child_name):
    try:
        # Retrieve the item document
        item = frappe.get_doc("Item", item_code)
        # print(item.status)
        if item.status == 'Rented Out':
            item.status = "Available"
            item.customer_n = ""
            item.customer_name = ""
            item.custom_sales_order_id = ""
            item.save(ignore_permissions=True)
        else:
            frappe.throw("Item Status is Not Rented Out")

        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name","item_code"])

        if sales_order_items:
            # If there is only one Sales Order Item, update both Sales Order and Sales Order Item statuses
            if len(sales_order_items) == 1:
                sales_order_item_doc = frappe.get_doc("Sales Order Item", sales_order_items[0].name)
                sales_order_item_doc.child_status = "Submitted to Office"
                sales_order_item_doc.submitted_date = submission_datetime
                sales_order_item_doc.save(ignore_permissions=True)

                # Retrieve the Sales Order document and update its status
                sales_order_doc = frappe.get_doc("Sales Order", docname)
                sales_order_doc.status = "Submitted to Office"
                sales_order_doc.submitted_date = submission_datetime
                sales_order_doc.save(ignore_permissions=True)

                return True
            else:
                # If there are multiple Sales Order Items, update only the Sales Order Item statuses
                sales_order_item_doc = frappe.get_doc("Sales Order Item", {"name": child_name})
                sales_order_item_doc.child_status = "Submitted to Office"
                sales_order_item_doc.submitted_date = submission_datetime
                sales_order_item_doc.save(ignore_permissions=True)

                # Check the statuses of all Sales Order Items
                sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["child_status"])

                if sales_order_items:
                    # Check if all Sales Order Items have the status "Submitted to Office"
                    all_submitted_to_office = all(item.get("child_status") == "Submitted to Office" for item in sales_order_items)

                    # Retrieve the Sales Order document
                    sales_order_doc = frappe.get_doc("Sales Order", docname)

                    if all_submitted_to_office:
                        # If all Sales Order Items have the status "Submitted to Office", update Sales Order status
                        sales_order_doc.status = "Submitted to Office"
                    else:
                        # If any Sales Order Item doesn't have the status "Submitted to Office", set status to "Partially Closed"
                        sales_order_doc.status = "Partially Closed"

                    sales_order_doc.save(ignore_permissions=True)
                    return True
                else:
                    # Handle case when there are no sales order items found
                    return False
        else:
            # Handle case when there are no sales order items found
            return False

    except Exception as e:
        frappe.log_error(f"Error updating status to Submitted to Office: {e}", "Sales Order")
        return False




@frappe.whitelist()
def update_status_to_active(item_code, docname, child_name):
    sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])

    if sales_order_items:
        # If there is only one Sales Order Item, update both Sales Order and Sales Order Item statuses
        if len(sales_order_items) == 1:
            sales_order_item_doc = frappe.get_doc("Sales Order Item", sales_order_items[0].name)
            sales_order_item_doc.child_status = "Active"
            sales_order_item_doc.pickup_date = ""
            sales_order_item_doc.save(ignore_permissions=True)

            # Retrieve the Sales Order document and update its status
            sales_order_doc = frappe.get_doc("Sales Order", sales_order_item_doc.parent)
            sales_order_doc.status = "Active"
            sales_order_doc.pickup_date = ""
            sales_order_doc.save(ignore_permissions=True)

            return True
        else:
            # If there are multiple Sales Order Items, update only the Sales Order Item statuses
            sales_order_item_doc = frappe.get_doc("Sales Order Item", {"name": child_name})
            sales_order_item_doc.child_status = "Active"
            sales_order_item_doc.pickup_date = ""
            sales_order_item_doc.save(ignore_permissions=True)

            return True
    else:
        return False




@frappe.whitelist()
def update_status_back_to_ready_for_pickup(item_code, docname, child_name):
    sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])

    if sales_order_items:
        # If there is only one Sales Order Item, update both Sales Order and Sales Order Item statuses
        if len(sales_order_items) == 1:
            sales_order_item_doc = frappe.get_doc("Sales Order Item", sales_order_items[0].name)
            sales_order_item_doc.child_status = "Ready for Pickup"
            sales_order_item_doc.pickup_date = ""
            sales_order_item_doc.save(ignore_permissions=True)

            # Retrieve the Sales Order document and update its status
            sales_order_doc = frappe.get_doc("Sales Order", sales_order_item_doc.parent)
            sales_order_doc.status = "Ready for Pickup"
            sales_order_doc.pickup_date = ""
            sales_order_doc.save(ignore_permissions=True)

            return True
        else:
            # If there are multiple Sales Order Items, update only the Sales Order Item statuses
            sales_order_item_doc = frappe.get_doc("Sales Order Item", {"name": child_name})
            sales_order_item_doc.child_status = "Ready for Pickup"
            sales_order_item_doc.pickup_date = ""
            sales_order_item_doc.save(ignore_permissions=True)

            return True
    else:
        return False




@frappe.whitelist()
def update_status_to_pickup(item_code, docname, child_name):
    try:
        # Retrieve the item document
        item = frappe.get_doc("Item", item_code)
        sales_order_cus = frappe.get_doc('Sales Order',docname)
        customer_id = sales_order_cus.customer
        if item:
            item.status = "Rented Out"
            item.customer_n = customer_id
            item.custom_sales_order_id = docname


            item.save(ignore_permissions=True)

        sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name"])

        if sales_order_items:
            # If there is only one Sales Order Item, update both Sales Order and Sales Order Item statuses
            if len(sales_order_items) == 1:
                sales_order_item_doc = frappe.get_doc("Sales Order Item", sales_order_items[0].name)
                sales_order_item_doc.child_status = "Picked Up"
                sales_order_item_doc.submitted_date = ""
                sales_order_item_doc.save(ignore_permissions=True)

                # Retrieve the Sales Order document and update its status
                sales_order_doc = frappe.get_doc("Sales Order", docname)
                sales_order_doc.status = "Picked Up"
                sales_order_doc.submitted_date = ""
                sales_order_doc.save(ignore_permissions=True)

                return True
            else:
                # If there are multiple Sales Order Items, update only the Sales Order Item statuses
                sales_order_item_doc = frappe.get_doc("Sales Order Item", {"name": child_name})
                sales_order_item_doc.child_status = "Picked Up"
                sales_order_item_doc.submitted_date = ""
                sales_order_item_doc.save(ignore_permissions=True)

                # Update sales order status to "Active"
                sales_order_items_status = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name", "child_status"])

                all_not_submitted = all(item.child_status != "Submitted to Office" for item in sales_order_items_status)

                # Update sales order status
                sales_order_replace = frappe.get_doc("Sales Order", docname)
                if all_not_submitted:
                    sales_order_replace.status = "Active"
                else:
                    sales_order_replace.status = "Partially Closed"
                sales_order_replace.save(ignore_permissions=True)

                return True
                
        else:
            # Handle case when there are no sales order items found
            return False

    except Exception as e:
        frappe.log_error(f"Error updating status to Submitted to Office: {e}", "Sales Order")
        return False




from frappe import _, publish_realtime
from frappe.utils import today, getdate

# Method to change status of overdue Sales Orders
@frappe.whitelist()
def mark_overdue_sales_orders():
    # Get today's date as a datetime.date object
    today_date = getdate(today())
    
    # Get all Sales Orders
    sales_orders = frappe.get_list("Sales Order",
                                   fields=["name", "end_date", "overdue_status", "status"])

    for so in sales_orders:
        end_date = getdate(so.end_date)  # Convert end_date string to datetime.date object
        
        # Check if the status is 'RENEWED'
        if so.status == 'RENEWED':
            # Update overdue_status to 'Renewed'
            frappe.db.set_value("Sales Order", so.name, "overdue_status", "Renewed")
        elif end_date < today_date:
            # Update overdue_status to 'Overdue'
            frappe.db.set_value("Sales Order", so.name, "overdue_status", "Overdue")
        else:
            # Update overdue_status to 'Active'
            frappe.db.set_value("Sales Order", so.name, "overdue_status", "Active")

    # Publish a message to refresh the list view
    # publish_realtime('list_update', "Sales Order")


import frappe
from frappe.utils import add_days
@frappe.whitelist()
def create_renewal_order(sales_order_name):
    # Get original sales order
    existing_renewal_orders = frappe.get_all("Sales Order", filters={"previous_order_id": sales_order_name, "docstatus": ["!=", 2]})

    if existing_renewal_orders:
        existing_order_id = existing_renewal_orders[0].name
        order_link = frappe.utils.get_url_to_form("Sales Order", existing_order_id)
        frappe.throw(_("A renewal order already exists for this sales order in Draft. <a href='{0}'>{1}</a>").format(order_link, existing_order_id))

    original_sales_order = frappe.get_doc("Sales Order", sales_order_name)

    # Filter out items where child_status is 'Submitted to Office'
    filtered_items = [item for item in original_sales_order.items if item.child_status != 'Submitted to Office']

    # Create a new sales order based on the original one
    new_sales_order = frappe.copy_doc(original_sales_order)
    new_sales_order.previous_order_id = original_sales_order.name  # Pass original order ID to renewal_order_id
    new_sales_order.advance_paid = 0
    new_sales_order.is_renewed = 1
    new_sales_order.security_deposit = 0
    new_sales_order.received_amount = 0
    new_sales_order.payment_status = 'UnPaid'
    new_sales_order.outstanding_security_deposit_amount = 0
    new_sales_order.custom_razorpay_payment_url = ''
    new_sales_order.custom_razorpay_payment_link_log_id = ''
    new_sales_order.status = 'Active'
    new_sales_order.paid_security_deposite_amount = 0
    new_sales_order.refundable_security_deposit = 0

    # Replace items with the filtered items
    new_sales_order.items = filtered_items

    for item in new_sales_order.items:
        item.read_only = 1
        current_tax_rate = frappe.get_value("Item", item.item_code, "tax_rate") or 0
        item.tax_rate = current_tax_rate
        item.gst_treatment = "Non-GST"

    # Increment the renewal_order_count of the new sales order
    renewal_count = getattr(original_sales_order, "renewal_order_count", 0)
    new_sales_order.renewal_order_count = renewal_count + 1 if renewal_count > 0 else 1
    
    # Set the new order's start date to the original order's end date + 1 day
    if original_sales_order.end_date:
        new_start_date = add_days(original_sales_order.end_date, 1)
        new_sales_order.start_date = new_start_date
        new_sales_order.end_date = ""
        new_sales_order.total_no_of_dates = ""

    new_sales_order.insert()
    return new_sales_order.name
# @frappe.whitelist()
# def create_renewal_order(sales_order_name):
#     # Get original sales order
#     existing_renewal_orders = frappe.get_all("Sales Order", filters={"previous_order_id": sales_order_name, "docstatus": ["!=", 2]})

#     if existing_renewal_orders:
#         existing_order_id = existing_renewal_orders[0].name
#         order_link = frappe.utils.get_url_to_form("Sales Order", existing_order_id)
#         frappe.throw(_("A renewal order already exists for this sales order in Draft. <a href='{0}'>{1}</a>").format(order_link, existing_order_id))

#     original_sales_order = frappe.get_doc("Sales Order", sales_order_name)

#     # Create a new sales order based on the original one
#     new_sales_order = frappe.copy_doc(original_sales_order)
#     new_sales_order.previous_order_id = original_sales_order.name  # Pass original order ID to renewal_order_id
#     new_sales_order.advance_paid = 0
#     new_sales_order.is_renewed = 1
#     new_sales_order.security_deposit = 0
#     new_sales_order.received_amount = 0
#     new_sales_order.payment_status = 'UnPaid'
#     new_sales_order.outstanding_security_deposit_amount = 0
#     new_sales_order.custom_razorpay_payment_url = ''
#     new_sales_order.custom_razorpay_payment_link_log_id = ''
#     new_sales_order.status = 'Active'
#     new_sales_order.paid_security_deposite_amount = 0
#     new_sales_order.refundable_security_deposit = 0
#     for item in new_sales_order.items:
#         item.read_only = 1
#     # Increment the renewal_order_count of the new sales order
#     renewal_count = getattr(original_sales_order, "renewal_order_count", 0)
#     new_sales_order.renewal_order_count = renewal_count + 1 if renewal_count > 0 else 1
    
#     # Set the new order's start date to the original order's end date + 1 day
#     if original_sales_order.end_date:
#         new_start_date = add_days(original_sales_order.end_date, 1)
#         new_sales_order.start_date = new_start_date
#         new_sales_order.end_date = ""
#         new_sales_order.total_no_of_dates = ""

#     new_sales_order.insert()

#     # Update original sales order status only after the new sales order has been submitted
#     # frappe.enqueue(update_original_sales_order_status, original_sales_order=original_sales_order)

#     return new_sales_order.name


# def update_original_sales_order_status(original_sales_order):
#     original_sales_order.status = "RENEWED"
#     original_sales_order.save()




@frappe.whitelist()
def get_sales_orders_by_rental_group_id(docname):
    # Fetch sales orders based on the rental group ID
    sales_orders = frappe.get_all("Sales Order",
        filters={"master_order_id": docname},
        fields=["name", "start_date", "end_date", "total_no_of_dates", "rounded_total","status"])
    
    return sales_orders






import frappe
from frappe.utils.background_jobs import enqueue

@frappe.whitelist()
def validate_and_update_payment_status_for_all():
    # Get all Sales Orders
    sales_orders = frappe.get_all("Sales Order", filters={"docstatus": 1, "order_type": ["in", ["Sales", "Service"]]}, fields=["name"])

    # Iterate through each Sales Order
    for sales_order in sales_orders:
        docname = sales_order.name
        # Enqueue the function for each Sales Order
        enqueue(validate_and_update_payment_status, docname=docname)

@frappe.whitelist()
def validate_and_update_payment_status_for_all_rental():
    # Get all Sales Orders
    sales_orders = frappe.get_all("Sales Order", filters={"docstatus": 1, "order_type": "Rental"}, fields=["name","master_order_id"])

    # Iterate through each Sales Order
    for sales_order in sales_orders:
        docname = sales_order.name
        master_order_id = sales_order.master_order_id
        # Enqueue the function for each Sales Order
        enqueue(validate_and_update_payment_and_security_deposit_status, docname=docname, master_order_id=master_order_id)

# Add @frappe.whitelist() decorator if these functions will be called from client-side scripts.






@frappe.whitelist()
def validate_and_update_payment_status(docname):
    sales_order = frappe.get_doc("Sales Order", docname)
    payment_entries = frappe.get_all(
            "Payment Entry",
            filters={
                "docstatus": 1,
                "sales_order_id":docname
            },
            fields=["paid_amount"]
        )

    # Calculate total allocated amount
    total_allocated_amount = sum(entry.paid_amount for entry in payment_entries if entry.paid_amount is not None)
    # total_allocated_amount = sum(entry.allocated_amount for entry in payment_entries)

    # print('dssssssssssssssssssssssssssssssssssssssssssssssssss',total_allocated_amount)
    sales_order.received_amount = total_allocated_amount
    # Access the rounded_total and advance_paid fields from the document object
    rounded_total = sales_order.rounded_total
    advance_paid = sales_order.received_amount

    # Calculate the balance amount
    balance_amount = rounded_total - advance_paid

    # Update the balance_amount field in the Sales Order document
    sales_order.balance_amount = balance_amount

    # Check if the rounded_total is equal to advance_paid
    if rounded_total == advance_paid:
        # If rounded_total equals advance_paid, set payment_status to 'Paid'
        sales_order.payment_status = 'Paid'
    elif advance_paid == 0:
        # If advance_paid is zero, set payment_status to 'Unpaid'
        sales_order.payment_status = 'UnPaid'
    else:
        # If rounded_total is not equal to advance_paid and advance_paid is not zero,
        # set payment_status to 'Partially Paid'
        sales_order.payment_status = 'Partially Paid'

    sales_order.save(ignore_permissions=True)
    
    return balance_amount



import frappe

@frappe.whitelist()
def validate_and_update_payment_and_security_deposit_status(docname,master_order_id):
    try:
        # Retrieve Sales Order document
        sales_order = frappe.get_doc("Sales Order", docname)
        payment_entries = frappe.get_all(
            "Payment Entry",
            filters={
                "docstatus": 1,
                "sales_order_id":docname
            },
            fields=["paid_amount"]
        )

        # Calculate total allocated amount
        # total_allocated_amount = sum(entry.paid_amount for entry in payment_entries)
        total_allocated_amount = sum(entry.paid_amount for entry in payment_entries if entry.paid_amount is not None)

        # print(total_allocated_amount)
        sales_order.received_amount = total_allocated_amount
        # Calculate balance amount
        balance_amount = sales_order.rounded_total - total_allocated_amount

        # Update balance amount field
        sales_order.balance_amount = balance_amount

        # Update payment status based on rounded total and advance paid
        if sales_order.rounded_total == sales_order.received_amount:
            sales_order.payment_status = 'Paid'
        elif sales_order.received_amount == 0:
            sales_order.payment_status = 'UnPaid'
        else:
            sales_order.payment_status = 'Partially Paid'
        if sales_order.is_renewed == 0:
            # Query Journal Entry records for cash received security deposit
            journal_entries = frappe.get_all("Journal Entry",
                                            filters={"master_order_id": master_order_id,
                                                    "security_deposite_type": "SD Amount Received From Client","docstatus": 1},
                                            fields=["name", "total_debit"])
            journal_entries_outstanding = frappe.get_all("Journal Entry",
                                            filters={"master_order_id": master_order_id,
                                                    "security_deposite_type": "Booking as Outstanding SD From Client","docstatus": 1},
                                            fields=["name", "total_debit"])

            # Query Journal Entry records for damage and refund
            journal_entries_damage = frappe.get_all("Journal Entry",
                                                    filters={"master_order_id": master_order_id,"docstatus": 1,
                                                            "security_deposite_type": ["in", ["Adjusted Device Damage Charges", "Adjusted Against Sales Order Rental Charges"]]},
                                                    fields=["name", "total_debit"])

            journal_entries_refund = frappe.get_all("Journal Entry",
                                                    filters={"master_order_id": master_order_id,"docstatus": 1,
                                                            "security_deposite_type": "Refunding SD to Client"},
                                                    fields=["name", "total_debit"])

            # Calculate total debit amounts
            total_debit_amount = sum(journal_entry.total_debit for journal_entry in journal_entries)
            total_debit_amount_damage = sum(journal_entry.total_debit for journal_entry in journal_entries_damage)
            total_debit_amount_refund = sum(journal_entry.total_debit for journal_entry in journal_entries_refund)
            # outstanding_amt = sum(journal_entry.total_debit for journal_entry in journal_entries_outstanding)
            
            # Update paid security deposit amount and adjustment amount fields
            sales_order.paid_security_deposite_amount = total_debit_amount
            sales_order.adjustment_amount = total_debit_amount_damage
            # sales_order.outstanding_security_deposit_amount = outstanding_amt
            security_deposit = float(sales_order.security_deposit)
            # Calculate outstanding security deposit amount
            outstanding_security_deposit_amount = float(sales_order.security_deposit) - total_debit_amount

            # Update outstanding security deposit amount field
            sales_order.outstanding_security_deposit_amount = outstanding_security_deposit_amount

            # Update security deposit amount return to client field
            sales_order.security_deposit_amount_return_to_client = total_debit_amount_refund

            # Calculate refundable security deposit
            # refundable_security_deposit = sales_order.paid_security_deposite_amount - sales_order.adjustment_amount - total_debit_amount_refund

            # Update refundable security deposit field
            sales_order.refundable_security_deposit = sales_order.paid_security_deposite_amount - sales_order.adjustment_amount - total_debit_amount_refund

            # Determine security deposit status based on outstanding amount
            if outstanding_security_deposit_amount == 0:
                sales_order.security_deposit_status = 'Paid'
            elif outstanding_security_deposit_amount == security_deposit:
                sales_order.security_deposit_status = 'Unpaid'
            else:
                sales_order.security_deposit_status = 'Partially Paid'
        # Convert strings to floats
            security_deposit = float(sales_order.security_deposit)
            rounded_total = float(sales_order.rounded_total)

        # Perform addition
        #total_rental_amount = security_deposit + rounded_total
        # if sales_order.is_renewed == 0:
            sales_order.total_rental_amount = float(sales_order.security_deposit) + float(sales_order.rounded_total)
        else:
            sales_order.total_rental_amount = float(sales_order.rounded_total)
        # Assign the result back to sales_order.total_rental_amount
        #sales_order.total_rental_amount = total_rental_amount        # Save changes to the document
        sales_order.save(ignore_permissions=True)

        # Return True to indicate successful update
        return True

    except Exception as e:
        # Log and raise any exceptions for debugging
        frappe.log_error(frappe.get_traceback(), _("Failed to update payment status"))
        frappe.throw(_("Failed to update payment status. Error: {0}".format(str(e))))




def check_overlap(self):
    previous_order = frappe.get_doc("Sales Order", self.previous_order_id)
    if previous_order:
        if self.start_date and self.end_date:
            # Convert string dates to datetime.date objects
            start_date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
            
            # Check for overlap
            overlap = (start_date <= previous_order.end_date and end_date >= previous_order.start_date)
            return overlap
    return False



@frappe.whitelist()
def item_replacement(item_code,customer, new_item,new_item_group, replacement_date, master_order_id, docname, old_item_status, reason=None):
    try:
        new_item_code = frappe.get_doc('Item',new_item)
        if new_item_code.status == 'Available':
            # Add a record in the Rental Order Replaced Item
            rental_order = frappe.new_doc("Rental Order Replaced Item")
            rental_order.master_order_id = master_order_id
            rental_order.sales_order_id = docname
            rental_order.replaced_datetime = replacement_date
            rental_order.old_item = item_code
            rental_order.new_item = new_item
            rental_order.reason = reason
            rental_order.save(ignore_permissions=True)
            
            # Update child_status and replacement_date in Sales Order Items
            sales_order_items = frappe.get_all("Sales Order Item", filters={"parent": docname, "item_code": item_code}, fields=["name", "child_status"])
            for item in sales_order_items:
                if item.child_status == "Picked Up":
                    sales_order_item = frappe.get_doc("Sales Order Item", item.name)
                    sales_order_item.child_status = "Active"
                    sales_order_item.replaced_datetime = replacement_date
                    sales_order_item.old_item_code = item_code
                    sales_order_item.item_group = new_item_group
                    sales_order_item.item_code = new_item
                    new_item_name = frappe.get_doc('Item',new_item)
                    sales_order_item.item_name = new_item_name.item_name
                    sales_order_item.save(ignore_permissions=True)

                    new_item_doc = frappe.get_doc("Item", new_item)
                    new_item_doc.status = "Rented Out"
                    new_item_doc.customer_n = customer
                    new_item_doc.custom_sales_order_id = docname

                    new_item_doc.save(ignore_permissions=True)
                else:
                    sales_order_item = frappe.get_doc("Sales Order Item", item.name)
                    sales_order_item.child_status = item.child_status
                    sales_order_item.replaced_datetime = replacement_date
                    sales_order_item.old_item_code = item_code
                    sales_order_item.item_group = new_item_group
                    sales_order_item.item_code = new_item
                    new_item_name = frappe.get_doc('Item',new_item)
                    sales_order_item.item_name = new_item_name.item_name
                    sales_order_item.save(ignore_permissions=True)

                    new_item_doc = frappe.get_doc("Item", new_item)
                    new_item_doc.status = "Reserved"
                    
                    new_item_doc.save()

            # Update the status of the old item
            old_item_doc = frappe.get_doc("Item", item_code)
            old_item_doc.status = old_item_status
            old_item_doc.customer_n = ''
            old_item_doc.customer_name = ''
            old_item_doc.custom_sales_order_id = ""
            old_item_doc.replaced_reason = reason
            old_item_doc.save()

            # Update sales order status to "Active"
            sales_order_items_status = frappe.get_all("Sales Order Item", filters={"parent": docname}, fields=["name", "child_status"])
            if any(item.child_status != "Ready for Delivery" and item.child_status != "DISPATCHED" for item in sales_order_items_status):
                all_active = all(item.child_status == "Active" for item in sales_order_items_status)
                any_submitted = any(item.child_status == "Submitted to Office" for item in sales_order_items_status)
                not_submitted = any(item.child_status != "Submitted to Office" for item in sales_order_items_status)

                # Update sales order status
                sales_order_replace = frappe.get_doc("Sales Order", docname)
                if all_active:
                    sales_order_replace.status = "Active"
                elif any_submitted:
                    sales_order_replace.status = "Partially Closed"
                elif not_submitted:
                    sales_order_replace.status = "Active"  # Handle the case when neither condition is met
                sales_order_replace.save()

            return True
        else:
            frappe.throw(_("Item Replacement Failed. New Item is not Available."))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Item Replacement Failed"))
        frappe.throw(_("Item Replacement Failed. Please try again later."))

import frappe
from frappe import _

# Define the server-side method to fetch replaced items
@frappe.whitelist()
def get_replaced_items(master_order_id):
    try:
        # Fetch replaced items associated with the sales order
        replaced_items = frappe.get_all("Rental Order Replaced Item",
                                        filters={"master_order_id": master_order_id},
                                        fields=["old_item", "new_item", "replaced_datetime", "reason"])
        return replaced_items
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to fetch replaced items"))
        return None




@frappe.whitelist()
def get_journal_entry_records(master_order_id):
    try:
        # Fetch replaced items associated with the sales order
        journal_entry_records = frappe.get_all("Journal Entry",
                                        filters={"master_order_id": master_order_id},
                                        fields=["name", "sales_order_id", "master_order_id", "security_deposite_type","total_debit","posting_date","mode_of__payment","transactional_effect","docstatus","custom_technician_id","custom_technician_name","custom_technician_visit_entry_id"])

        # Iterate through each journal entry record
        for entry in journal_entry_records:
            # Fetch accounts associated with the current journal entry
            accounts = frappe.get_all("Journal Entry Account",
                                       filters={"parent": entry["name"]},
                                       fields=["account", "debit_in_account_currency", "credit_in_account_currency"])

            # Add accounts data to the journal entry record
            entry["accounts"] = accounts

        return journal_entry_records
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to fetch replaced items"))
        return None


@frappe.whitelist()
def get_payment_entry_records(sales_order_id):
    try:
        # Fetch replaced items associated with the sales order
        payment_entry_records = frappe.get_all("Payment Entry",
                                        filters={"sales_order_id": sales_order_id},
                                        fields=["name", "references.reference_name","sales_order_id", "master_order_id","total_allocated_amount","posting_date","mode_of_payment","reference_no","reference_date","docstatus","custom_technician_id","custom_technician_name","custom_technician_visit_id"])
        return payment_entry_records
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to fetch replaced items"))
        return None


@frappe.whitelist()
def submit_journal_entry(journal_entry_id):
    try:
        # Fetch the Journal Entry document using the provided journal_entry_id
        journal_entry = frappe.get_doc('Journal Entry', journal_entry_id)

        # Check if the journal entry is in draft status
        if journal_entry.docstatus == 0:
            # Submit the Journal Entry
            journal_entry.submit()
        
            # Return success message
            return True
        else:
            # If the journal entry is already submitted or canceled
            return False
    except frappe.DoesNotExistError:
        frappe.throw(f"Journal Entry with ID {journal_entry_id} does not exist.")
    except Exception as e:
        frappe.throw(f"An error occurred while submitting the Journal Entry: {str(e)}")



@frappe.whitelist()
def cancel_and_delete_journal_entry(journal_entry_id):
    try:
        # Get the journal entry
        journal_entry = frappe.get_doc("Journal Entry", journal_entry_id)

        # Check if the journal entry is submitted
        if journal_entry.docstatus == 1:
            # Cancel the journal entry
            journal_entry.cancel()
            frappe.db.commit()

            # Check if the journal entry has security_deposite_type == 'Adjusted Against Sales Order Rental Charges'
            if journal_entry.security_deposite_type == 'Adjusted Against Sales Order Rental Charges':
                # Get payment entry ID related to this journal entry
                payment_entry_id = journal_entry.payment_entry_id_for_so_adjustment

                if payment_entry_id:
                    # Get the payment entry
                    payment_entry = frappe.get_doc("Payment Entry", payment_entry_id)

                    # Check if the payment entry is submitted
                    if payment_entry.docstatus == 1:
                        # Cancel the payment entry
                        payment_entry.cancel()
                        frappe.db.commit()

            return True, "Journal entry and associated payment entry cancelled successfully."
        else:
            return False, "Journal entry is not submitted."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to cancel journal entry: {0}").format(e))
        return False, str(e)


@frappe.whitelist()
def cancel_and_delete_payment_entry(payment_entry_id):
    # Get the journal entry
    payment_entry = frappe.get_doc("Payment Entry", payment_entry_id)

    # Check if the journal entry is submitted
    if payment_entry.docstatus == 1:
        # Cancel the journal entry
        payment_entry.cancel()

        # Commit the changes
        frappe.db.commit()

        # # Delete the journal entry
        # frappe.delete_doc("Payment Entry", payment_entry_id)

        # # Commit the deletion
        # frappe.db.commit()

        return True, "Payment entry cancelled and deleted successfully."
    else:
        return False, "Payment entry is not submitted."


@frappe.whitelist()
def submit_payment_entry(payment_entry_id):
    # Get the journal entry
    payment_entry = frappe.get_doc("Payment Entry", payment_entry_id)

    # Check if the journal entry is submitted
    if payment_entry.docstatus == 0:
        # Cancel the journal entry
        payment_entry.submit()

        # Commit the changes
        frappe.db.commit()

        # # Delete the journal entry
        # frappe.delete_doc("Payment Entry", payment_entry_id)

        # # Commit the deletion
        # frappe.db.commit()

        return True, "Payment entry Submit successfully."
    else:
        return False, "Payment entry is not submitted."

@frappe.whitelist()
def process_payment(balance_amount, outstanding_security_deposit_amount, customer_name, rental_payment_amount, sales_order_name, master_order_id, security_deposit_status, customer, payment_date,payment_account=None,security_deposit_account=None, reference_no=None, reference_date=None, mode_of_payment=None,
                    security_deposit_payment_amount=None, remark=None,from_technician_portal=None,technician_id=None,technician_visit_id=None):
    try:
        # Convert balance_amount and outstanding_security_deposit_amount to floats
        balance_amount = float(balance_amount)
        outstanding_security_deposit_amount = float(outstanding_security_deposit_amount)

        # Check if rental_payment_amount and security_deposit_payment_amount are not negative
        if float(rental_payment_amount) < 0 or float(security_deposit_payment_amount) < 0:
            frappe.throw("Payment amounts cannot be negative.")
            return False

        # Check if balance_amount and outstanding_security_deposit_amount are not negative
        if balance_amount < 0 or outstanding_security_deposit_amount < 0:
            frappe.throw("Balance amounts cannot be negative.")
            return False

        # Convert rental_payment_amount to a float
        rental_payment_amount = float(rental_payment_amount) if rental_payment_amount else 0
        security_deposit_payment_amount = float(security_deposit_payment_amount) if security_deposit_payment_amount else 0

        # Check if security_deposit_payment_amount and rental_payment_amount are greater than 0
        if security_deposit_payment_amount > 0 and rental_payment_amount > 0:
            # Check if security_deposit_payment_amount is greater than outstanding_security_deposit_amount
            if security_deposit_payment_amount > outstanding_security_deposit_amount:
                # Show an alert if security_deposit_payment_amount is greater
                frappe.throw("Security Deposit Payment Amount cannot be greater than the Security Deposit Amount.")
                return False
            
            # Check if rental_payment_amount is greater than balance_amount
            if rental_payment_amount > balance_amount:
                # Show an alert if rental_payment_amount is greater
                frappe.throw("Rental Payment Amount cannot be greater than the Balance Amount.")
                return False

            # Create a journal entry for the security deposit payment amount
            create_security_deposit_journal_entry_payment(customer_name,payment_date, security_deposit_payment_amount,mode_of_payment, sales_order_name, master_order_id,security_deposit_account, reference_no, reference_date, remark,from_technician_portal,technician_id,technician_visit_id)
            
            # Create a payment entry for the rental payment amount
            create_rental_payment_entry(customer_name,payment_date, rental_payment_amount, mode_of_payment, sales_order_name, security_deposit_status, customer, payment_account, master_order_id, reference_no, reference_date, remark,from_technician_portal,technician_id,technician_visit_id)
            
            return True

        elif security_deposit_payment_amount > 0:
            # Check if security_deposit_payment_amount is greater than outstanding_security_deposit_amount
            if security_deposit_payment_amount > outstanding_security_deposit_amount:
                # Show an alert if security_deposit_payment_amount is greater
                frappe.throw("Security Deposit Payment Amount cannot be greater than the Security Deposit Amount.")
                return False

            # Create a journal entry for the security deposit payment amount
            create_security_deposit_journal_entry_payment(customer_name, payment_date,security_deposit_payment_amount,mode_of_payment ,sales_order_name, master_order_id,security_deposit_account, reference_no, reference_date, remark,from_technician_portal,technician_id,technician_visit_id)
            return True
        
        elif rental_payment_amount > 0:
            # Check if rental_payment_amount is greater than balance_amount
            if rental_payment_amount > balance_amount:
                # Show an alert if rental_payment_amount is greater
                frappe.throw("Rental Payment Amount cannot be greater than the Balance Amount.")
                return False
    
            # Create a payment entry for the rental payment amount
            create_rental_payment_entry(customer_name,payment_date, rental_payment_amount, mode_of_payment, sales_order_name, security_deposit_status, customer, payment_account, master_order_id, reference_no, reference_date, remark,from_technician_portal,technician_id,technician_visit_id)
            return True


    except Exception as e:
        error_message = f"Failed to process payment: {str(e)}"
        frappe.log_error(frappe.get_traceback(), error_message)
        frappe.throw(error_message)

    return False


def create_security_deposit_journal_entry_payment(customer, payment_date,security_deposit_payment_amount,mode_of_payment, sales_order_name, master_order_id,security_deposit_account, reference_no=None, reference_date=None, remark=None,from_technician_portal=None,technician_id=None,technician_visit_id=None):
    try:
        # Create a new Journal Entry document
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.voucher_type = "Journal Entry"
        journal_entry.sales_order_id = sales_order_name
        journal_entry.journal_entry_type = "Security Deposit"
        journal_entry.security_deposite_type = "SD Amount Received From Client"
        journal_entry.master_order_id = master_order_id
        journal_entry.cheque_no = reference_no
        journal_entry.posting_date = payment_date
        journal_entry.cheque_date = reference_date
        journal_entry.user_remark = f"Security Deposit Payment Against Sales Order {sales_order_name} and Master Order Id is {master_order_id}. Remark: {remark}"
        journal_entry.customer_id = customer
        journal_entry.mode_of__payment = mode_of_payment
        journal_entry.transactional_effect = "Plus"
        journal_entry.custom_technician_visit_entry_id = technician_visit_id
        # Add accounts for debit and credit
        journal_entry.append("accounts", {
            "account": security_deposit_account,
            "debit_in_account_currency": security_deposit_payment_amount
        })
        journal_entry.append("accounts", {
            "account": "Debtors - INR",
            "party_type": "Customer",
            "party": customer,
            "credit_in_account_currency": security_deposit_payment_amount
        })
        if from_technician_portal:
            journal_entry.custom_from_technician_protal = 1,
            journal_entry.custom_technician_id = technician_id
        # Save and submit the Journal Entry document
        journal_entry.insert(ignore_permissions=True)
        if not from_technician_portal:
            journal_entry.submit()

        frappe.msgprint("Security Deposit Journal Entry created successfully.")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to create Security Deposit Journal Entry"))
        frappe.throw(_("Failed to create Security Deposit Journal Entry. Please try again later."))


# def create_rental_payment_entry(customer_name,payment_date, rental_payment_amount, mode_of_payment,
#                                 sales_order_name, security_deposit_status, customer, payment_account, master_order_id, reference_no=None, reference_date=None, remark=None):
#     try:
#         rental_payment_amount_numeric = float(rental_payment_amount)  # Convert rental_payment_amount to float

#         # Create a new Payment Entry document
#         payment_entry = frappe.get_doc({
#             "doctype": "Payment Entry",
#             "master_order_id": master_order_id,
#             "sales_order_id":sales_order_name,
#             "posting_date":payment_date,
#             "paid_from": "Debtors - INR",
#             "received_amount": rental_payment_amount_numeric,
#             "base_received_amount": rental_payment_amount_numeric,  # Assuming base currency is INR
#             "received_amount_currency": "INR",
#             "base_received_amount_currency": "INR",
#             "target_exchange_rate": 1,
#             "paid_amount": rental_payment_amount_numeric,
#             "references": [
#                 {
#                     "reference_doctype": "Sales Order",
#                     "reference_name": sales_order_name,
#                     "allocated_amount": rental_payment_amount_numeric
#                 }
#             ],
#             "reference_date": reference_date,
#             "party_type": "Customer",
#             "party": customer,
#             "mode_of_payment": mode_of_payment,
#             "reference_no": reference_no,
#             "paid_to": payment_account,
#             "payment_remark": f"Payment Against Sales Order {sales_order_name} and Master Order Id is {master_order_id} and Remark Is {remark}",
#         }, ignore_permissions=True)

#         payment_entry.insert(ignore_permissions=True)
#         payment_entry.submit()

#         frappe.msgprint("Payment Entry created successfully.")

#         frappe.log_error("Rental Payment Entry created successfully.", _("Rental Payment Entry"))
#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), _("Failed to create Rental Payment Entry"))
#         frappe.throw(_("Failed to create Rental Payment Entry. Please try again later. Error: {0}".format(str(e))))

@frappe.whitelist()
def create_rental_payment_entry(customer_name, payment_date, rental_payment_amount, mode_of_payment,
                                sales_order_name, security_deposit_status, customer, payment_account, 
                                master_order_id, reference_no=None, reference_date=None, 
                                remark=None, from_technician_portal=None, technician_id=None,technician_visit_id=None):
    try:
        rental_payment_amount_numeric = float(rental_payment_amount)  # Convert rental_payment_amount to float
        # print('ccccccccccccccccccccccccccccccccccc',rental_payment_amount_numeric)
        # Create a new Payment Entry document
        payment_entry_data = {
            "doctype": "Payment Entry",
            "master_order_id": master_order_id,
            "sales_order_id": sales_order_name,
            "posting_date": payment_date,
            "paid_from": "Debtors - INR",  # Replace this if needed
            "received_amount": rental_payment_amount_numeric,
            "base_received_amount": rental_payment_amount_numeric,  # Assuming base currency is INR
            "received_amount_currency": "INR",
            "base_received_amount_currency": "INR",
            "target_exchange_rate": 1,
            "paid_amount": rental_payment_amount_numeric,
            "references": [
                {
                    "reference_doctype": "Sales Order",
                    "reference_name": sales_order_name,
                    "allocated_amount": rental_payment_amount_numeric
                }
            ],
            "reference_date": reference_date,
            "party_type": "Customer",
            "party": customer,
            "mode_of_payment": mode_of_payment,
            "reference_no": reference_no,
            "paid_to": payment_account,
            "payment_remark": f"Payment Against Sales Order {sales_order_name} and Master Order Id is {master_order_id} and Remark is {remark}",
        }
        
        # Add custom fields if from_technician_portal is true
        if from_technician_portal:
            payment_entry_data["custom_from_technician_protal"] = 1
            payment_entry_data["custom_technician_id"] = technician_id
            payment_entry_data["custom_technician_visit_id"] = technician_visit_id

        # Create the Payment Entry document
        payment_entry = frappe.get_doc(payment_entry_data)

        # Insert the document
        payment_entry.insert(ignore_permissions=True)

        if not from_technician_portal:
            payment_entry.submit()

        frappe.msgprint("Payment Entry created successfully.")
        frappe.log_error("Rental Payment Entry created successfully.", _("Rental Payment Entry"))
    
    except Exception as e:
        # Shorten error log title
        error_message = _("Failed to process payment: ") + str(e)
        frappe.log_error(frappe.get_traceback(), _("Rental Payment Error"))

        # Raise error with a shortened message
        frappe.throw(_("Failed to create Rental Payment Entry. Please try again later. Error: {0}").format(str(e)))


@frappe.whitelist()
def get_default_account(mode_of_payment):
    try:
        # Fetch the Mode Of Payment document
        mode_of_payment_doc = frappe.get_doc("Mode of Payment", mode_of_payment)

        # Initialize default_account and journal_entry_default_account
        default_account = None
        journal_entry_default_account = mode_of_payment_doc.journal_entry_default_account

        # Iterate through the child table entries
        for account in mode_of_payment_doc.get("accounts"):
            if account.default_account:
                default_account = account.default_account
                break

        if default_account:
            return {"default_account": default_account, "journal_entry_default_account": journal_entry_default_account}
        else:
            # Return "Bank Account - INR" if default account not found
            return {"default_account": "Bank Account - INR","journal_entry_default_account": "Kotak Bank Security Deposit Received - INR"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to fetch default account"))
        frappe.throw(_("Failed to fetch default account. Please try again later."))




@frappe.whitelist()
def return_security_deposit(amount_to_return, remark, master_order_id, sales_order_id, customer):
    try:
        # Create a journal entry to return the security deposit amount
        journal_entry = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": frappe.utils.today(),
            "company": frappe.defaults.get_user_default("company"),
            "accounts": [
                {
                    "account": "Rental Security Deposit Payable - INR",
                    "debit_in_account_currency": amount_to_return,
                    "credit_in_account_currency": 0,
                },
                {
                    "account": "Cash - INR",
                    "credit_in_account_currency": amount_to_return,
                }
            ],
            "user_remark": remark,
            "master_order_id": master_order_id,
            "sales_order_id": sales_order_id,
            "customer_id": customer,
            "journal_entry_type": "Security Deposit",
            "security_deposite_type": "Refunding SD to Client",
            "transactional_effect": "Minus",
        })

        # Save the journal entry
        journal_entry.insert()
        journal_entry.submit()

        # Uncomment the following code to update the Sales Order with returned security deposit amount
        # sales_order_update = frappe.get_doc("Sales Order", master_order_id)
        # current_amount_returned = sales_order_update.security_deposit_amount_return_to_client or 0
        # total_amount_returned = current_amount_returned + amount_to_return
        # sales_order_update.security_deposit_amount_return_to_client = total_amount_returned
        # sales_order_update.save()

        return True

    except Exception as e:
        # Log the error and return False
        frappe.log_error(frappe.get_traceback(), _("Failed to update Sales Order: {0}".format(str(e))))
        return False





import frappe
from frappe import _

@frappe.whitelist()
def process_adjustment(adjust_against,adjust_amount,sales_order_name,master_order_id,customer,item=None,item_remark=None,sales_order=None):
    # print("item:", item)
    # print("item_remark:", item_remark)
    if adjust_against == "Product Damaged":
        create_journal_entry_adjustment(adjust_against,adjust_amount,sales_order_name,master_order_id,customer, item, item_remark)
    elif adjust_against == "Sales Order":
        create_journal_entry_and_payment_entry(adjust_against,adjust_amount,sales_order_name,master_order_id,customer,item_remark,sales_order)
    else:
        frappe.throw(_("Invalid adjustment type."))



def create_journal_entry_and_payment_entry(adjust_against, adjust_amount, sales_order_name, master_order_id, customer, item_remark, sales_order):
    try:
        # Fetch Sales Order details
        sales_order_doc = frappe.get_doc("Sales Order", sales_order)

        # Check if Sales Order is submitted and not paid
        if sales_order_doc.docstatus != 1:
            frappe.msgprint(f"The Sales Order {sales_order} is not submitted. Please submit the Sales Order first.")
            return False

        if sales_order_doc.payment_status == "Paid":
            frappe.msgprint(f"The Sales Order {sales_order} is already paid. No further action needed.")
            return False

        # # Check if adjust_amount is greater than Sales Order balance_amount
        # if adjust_amount > sales_order_doc.balance_amount:
        #     frappe.msgprint(f"The Adjust Amount ({adjust_amount}) is greater than the Sales Order total amount ({sales_order_doc.balance_amount}).")
        #     return False
        
        amount_to_return = adjust_amount
        if adjust_against == 'Product Damaged':
            amount_to_return = 0

        # Create Payment Entry
        payment_entry = frappe.get_doc({
            "doctype": "Payment Entry",
            "paid_from": "Debtors - INR",  # Adjust this based on your actual account
            "paid_to": "Cash - INR",  # Adjust this based on your actual account
            "received_amount": adjust_amount,
            "base_received_amount": adjust_amount,
            "paid_amount": int(adjust_amount),
            "references": [{
                "reference_doctype": "Sales Order",
                "reference_name": sales_order,
                "allocated_amount": int(adjust_amount)
            }],
            "reference_date": frappe.utils.today(),
            "account": "Accounts Receivable",  # Adjust this based on your actual account
            "party_type": "Customer",
            "party": customer,
            "mode_of_payment": "SD Adjustment Cash",  # Adjust this based on your actual mode of payment
            "reference_no": "sales_order_adjustment",
            "sales_order_adjustment": 1,
            "sales_order_id": sales_order,
            "master_order_id": master_order_id,
        })

        # Save and submit the Payment Entry
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()

        # Check if Payment Entry is successfully created
        if payment_entry.docstatus == 1:
            # Create Journal Entry
            journal_entry = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "posting_date": frappe.utils.today(),
                "company": sales_order_doc.company,
                "payment_entry_id_for_so_adjustment": payment_entry.name,
                "accounts": [
                    {
                        "account": "Rental Security Deposit Payable - INR",
                        "debit_in_account_currency": amount_to_return,
                    },
                    {
                        "account": "Sales Order Adjustment - INR",
                        "credit_in_account_currency": amount_to_return,
                    }
                ],
                "remarks": f"Adjusted Security Deposit Against Sales Order {sales_order}. Remark: {item_remark}",
                "master_order_id": master_order_id,
                "sales_order_id": sales_order,
                "journal_entry_type": "Security Deposit",
                "security_deposite_type": "Adjusted Against Sales Order Rental Charges",
                "transactional_effect": "Minus",
                "customer_id": customer,
                "user_remark": f"Adjusted Security Deposit. Sales Order Id: {sales_order}. Remark: {item_remark}",
            })

            # Save and submit the Journal Entry
            journal_entry.insert()
            journal_entry.submit()
        frappe.msgprint("Adjustment processed successfully.");
        return True

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to create journal and payment entries: {0}").format(e))
        return False


def create_journal_entry_adjustment(adjust_against, adjust_amount, sales_order_name, master_order_id, customer,item=None,item_remark=None):
    try:
        
        amount_to_return = adjust_amount
        if adjust_against == 'Product Damaged':
            amount_to_return = 0

        journal_entry = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": frappe.utils.today(),
            "company": frappe.defaults.get_user_default("company"),
            "accounts": [
                {
                    "account": "Rental Security Deposit Payable - INR",
                    "debit_in_account_currency": adjust_amount,
                    # "credit_in_account_currency": 0,
                },
                {
                    "account": "Rental Device Damage Charges - INR",
                    # "debit_in_account_currency": 0,
                    "credit_in_account_currency": adjust_amount,
                }
            ],
            "remarks": f"Adjusted Security Deposit Against Sales Order {sales_order_name} and Item Code is {item} and Remark Is {item_remark}",
            "master_order_id": master_order_id,
            "sales_order_id": sales_order_name,
            "journal_entry_type": "Security Deposit",
            "security_deposite_type": "Adjusted Device Damage Charges",
            "transactional_effect":"Minus",
            "customer_id": customer,
            "user_remark": f"Adjusted Security Deposit Against Product Damage and Item Code is {item} and Remark Is {item_remark}",
        })

        # Save the journal entry
        journal_entry.insert()
        journal_entry.submit()

        item_product_damage = frappe.get_doc("Item", item)
        item_product_damage.item_damage_remark = item_remark
        item_product_damage.save()
        return True
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to create journal entry"))
        return False



def create_sales_invoice(adjust_against, adjust_amount, refundable_security_deposit, sales_order_name, master_order_id, customer, item_remark=None, sales_order=None):
    try:
        # Create a new Sales Invoice document
        sales_invoice = frappe.new_doc("Sales Invoice")

        # Set relevant fields for the Sales Invoice
        sales_invoice.customer = customer
        sales_invoice.company = frappe.defaults.get_user_default("company")
        sales_invoice.currency = frappe.defaults.get_user_default("currency")
        sales_invoice.sd_adjustment = 1
        sales_invoice.adjusted_sales_order_id = sales_order
        sales_invoice.remark = f"Adjusted Security Deposit Against Sales Order {sales_order} and Remark Is {item_remark}"

        # Add items based on adjust_amount from Sales Order Adjustment
        sales_invoice.append("items", {
            "item_code": "Sales Order Adjustment",  # Assuming adjust_against contains the item_code
            "qty": 1,  # Assuming quantity is 1 for each adjustment
            "rate": adjust_amount,
            "amount": adjust_amount
        })

        # Save and submit the Sales Invoice
        sales_invoice.insert()
        sales_invoice.submit()

        # Update status and save
        sales_invoice.status = "Paid"
        sales_invoice.save()

        # Optionally, you can update some fields in the Sales Order or perform other operations if needed
        create_journal_entry_for_sales_order_adjustment(adjust_against, adjust_amount, refundable_security_deposit, sales_order_name, master_order_id, customer, item_remark, sales_order)
        return sales_invoice.name  # Return the name of the created Sales Invoice

    except Exception as e:
        # Log and handle any exceptions
        frappe.log_error(frappe.get_traceback(), _("Failed to create sales invoice"))
        frappe.throw(_("Failed to create sales invoice. Error: {0}".format(str(e))))


def create_journal_entry_for_sales_order_adjustment(adjust_against, adjust_amount, refundable_security_deposit, sales_order_name, master_order_id, customer,item_remark=None,sales_order=None):
    try:
        # Create a new Journal Entry document
        journal_entry = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": frappe.utils.today(),
            "company": frappe.defaults.get_user_default("company"),
            "accounts": [
                {
                    "account": "Rental Security Deposit Payable - INR",
                    "debit_in_account_currency": adjust_amount,
                    # "credit_in_account_currency": 0,
                },
                {
                    "account": "Debtors - INR",
                    "party_type":"Customer",
                    "party":customer,
                    "credit_in_account_currency": adjust_amount,
                }
            ],
            # "remarks": f"Return Security Deposit for Sales Order {sales_order_name}",
            "master_order_id": master_order_id,
            "sales_order_id": sales_order_name,
            "journal_entry_type": "Security Deposit",
            "security_deposite_type": "Adjusted Against Sales Order Rental Charges",
            "transactional_effect":"Minus",
            "customer_id": customer,
            "user_remark": f"Adjusted Security Deposit Against Sales Order {sales_order}  and Remark Is {item_remark}",

        })

        # Save the journal entry
        journal_entry.insert()
        journal_entry.submit()

        return True

    except Exception as e:
        # Log and handle any exceptions
        frappe.log_error(frappe.get_traceback(), _("Failed to create journal entry"))
        frappe.throw(_("Failed to create journal entry. Error: {0}".format(str(e))))



@frappe.whitelist()
def update_security_deposit(master_order_id, remark, updated_security_deposit,amount,sales_order_id,customer):
    try:
        # Fetch the Sales Order document
        sales_order = frappe.get_doc("Sales Order", master_order_id)
        
       
        
        # Update the security deposit field
        sales_order.security_deposit = updated_security_deposit
        sales_order.security_deposit_revised_remark = remark
        
        # Save the changes
        sales_order.save()
        create_security_deposit_journal_entry_update_sd(master_order_id, remark, updated_security_deposit,amount,sales_order_id,customer)
        # frappe.db.commit()
        
        return True
    except frappe.DoesNotExistError:
        frappe.log_error(frappe.get_traceback())
        return False
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Failed to update security deposit")
        return False



def create_security_deposit_journal_entry_update_sd(master_order_id ,remark, updated_security_deposit,amount,sales_order_id,customer):
        try:
            # sales_order = frappe.get_doc("Sales Order", self.name)

            # Create a new Journal Entry document
            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.sales_order_id = sales_order_id
            journal_entry.master_order_id = master_order_id
            journal_entry.journal_entry_type = "Security Deposit"
            journal_entry.journal_entry = "Journal Entry"
            journal_entry.posting_date = frappe.utils.nowdate()
            journal_entry.security_deposite_type = "Booking as Outstanding SD From Client"
            journal_entry.customer_id = customer
            journal_entry.transactional_effect = "NA"


            # Add accounts for debit and credit
            journal_entry.append("accounts", {
                "account": "Debtors - INR",
                "party_type": "Customer",
                "party": customer,
                "debit_in_account_currency": amount
            })
            journal_entry.append("accounts", {
                "account": "Rental Security Deposit Payable - INR",
                # "party_type": "Customer",
                # "party": self.customer,
                "credit_in_account_currency": amount
            })

            # Save the Journal Entry document
            journal_entry.insert()
            journal_entry.submit()

            frappe.msgprint("Security Deposit Journal Entry created successfully")  # Debug message

            return True
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Failed to create Security Deposit Journal Entry"))
            frappe.throw(_("Failed to create Security Deposit Journal Entry. Please try again later."))



@frappe.whitelist()
def get_sales_orders(master_order_id):
    try:
        # Query sales orders based on the provided master_order_id
        sales_orders_names = frappe.get_all("Sales Order", filters={"master_order_id": master_order_id}, fields=["name"])
        
        # Extract the names from the result list
        # sales_order = [order.get("name") for order in sales_orders]
        
        # Return the list of sales order names
        # print(sales_orders_names)
        return sales_orders_names
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Failed to fetch sales orders")
        return None

@frappe.whitelist()
def get_item_tax_template(item_code):
    # Fetch the item_tax_template for the given item_code from the Item doctype
    item_tax_template = frappe.db.get_value('Item', item_code, 'tax_rate')
    return item_tax_template



@frappe.whitelist()
def get_user_by_role(role_id):
    # Fetch users based on the given role ID from User Role Profile
    users = frappe.get_all("UserRole", filters={"role": role_id}, fields=["parent"])

    # Extract user names from the fetched UserRole records
    user_names = [user["parent"] for user in users]

    # Fetch user details
    user_details = frappe.get_all("User", filters={"name": ["in", user_names]}, fields=["name", "full_name"])

    # Prepare the response with user details
    response = []
    for user in user_details:
        response.append({"value": user["name"], "description": user["full_name"]})

    return response



@frappe.whitelist()
def get_product_type(item_group):
    product_type1 = frappe.db.get_value('Item Group', item_group, 'product_type1')
    return product_type1



##############################################################################

# Razorpay

import requests
import random
import frappe

@frappe.whitelist()
def create_razorpay_payment_link_sales_order(amount, invoice_name, customer, customer_name, actual_amount, order_type):
    payment_links = frappe.get_all("Payment Link Log", filters={"sales_order": invoice_name, "enabled": 1})
    if payment_links:
        return {"status": False, "msg": "Payment link already exists."}
    admin_settings = frappe.get_doc('Admin Settings')
    razorpay_base_url = admin_settings.razorpay_base_url
    razorpay_key_id = admin_settings.razorpay_api_key
    razorpay_key_secret = admin_settings.razorpay_secret
    razorpay_api_url = razorpay_base_url + "payment_links" 
    
    
    if not (razorpay_api_url and razorpay_key_id and razorpay_key_secret):
        return {"status": False, "msg": "Razorpay API credentials are missing or invalid."}
    
    # Convert the amount to paise
    amount_in_paise = int(float(amount) * 100)
    
    # Create order parameters
    order_params = {
        "amount": amount_in_paise,
        "currency": "INR",
        "description": f"Sales order type {order_type} NHK Medical Pvt Ltd",
        "accept_partial": False,
        # "first_min_partial_amount": 100,
        "notes": {
            "invoice_name": invoice_name,
            "company": "NHK Medical Pvt Ltd"
        },
        "reference_id": invoice_name,
        "callback_url": frappe.utils.get_url(f"/api/method/erpnext.selling.doctype.sales_order.sales_order.get_razorpay_payment_details?sales_order_id={invoice_name}&customer={customer}&actual_amount={actual_amount}&final_amount={amount}"),
        "callback_method": "get"
    }
    
    try:
        def generate_payment_link(order_params, retries=3):
            for _ in range(retries):
                response = requests.post(
                    razorpay_api_url,
                    json=order_params,
                    auth=(razorpay_key_id, razorpay_key_secret)
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    order_params["reference_id"] += f"-{random.randint(100, 999)}"
            response.raise_for_status()
        
        # Generate the payment link
        response_json = generate_payment_link(order_params)
        short_url = response_json.get('short_url')
        link_id = response_json.get('id')
        
        
        
        # Log the payment link
        new_payment_link = frappe.get_doc({
            "doctype": "Payment Link Log",
            "customer_id": customer,
            "sales_order": invoice_name,
            "total_amount": amount,
            "link_short_url": short_url,
            "link_id": link_id,
        })
        new_payment_link.insert()
        # Update the Sales Order with the payment link
        doc = frappe.get_doc('Sales Order', invoice_name)
        doc.custom_razorpay_payment_url = short_url
        doc.custom_razorpay_payment_link_log_id = new_payment_link.name
        doc.save()
        return {"status": True, "msg": f"Successfully created Razorpay order. Short URL: {short_url}"}
    
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Failed to generate the Razorpay payment link: {e}")
        return {"status": False, "msg": f"Failed to generate the Razorpay payment link: {e}"}

####################################with razorpay payment details################################################


import requests
from frappe.utils import nowdate

@frappe.whitelist(allow_guest=True)
def get_razorpay_payment_details(sales_order_id, customer, actual_amount, final_amount):
    try:
        frappe.msgprint("Payment Details Function Called")
        frappe.log_error("Payment Details Function Called")  # Debug log

        # Fetch the payment link based on provided filters
        payment_link = frappe.get_all("Payment Link Log", filters={
            "customer_id": customer,
            "sales_order": sales_order_id[:18],
            "total_amount": final_amount,
            "enabled": 1
        }, fields=["name", "link_id"])

        if not payment_link:
            frappe.msgprint("Payment link not found.")
            frappe.log_error("Payment link not found.")  # Debug log
            return
        
        razorpay_payment_link_id = payment_link[0].link_id

        # Get Razorpay API settings
        admin_settings = frappe.get_doc('Admin Settings')
        razorpay_base_url = admin_settings.razorpay_base_url
        razorpay_key_id = admin_settings.razorpay_api_key
        razorpay_key_secret = admin_settings.razorpay_secret
        razorpay_api_url = f"{razorpay_base_url}payment_links/{razorpay_payment_link_id}"
        
        # Fetch payment link details from Razorpay
        response = requests.get(razorpay_api_url, auth=(razorpay_key_id, razorpay_key_secret))

        if response.status_code == 200:
            razorpay_response = response.json()
            # print('Razorpay response:', razorpay_response)
            # frappe.log_error(f'Razorpay response: {razorpay_response}')  # Debug log
            
            payment_link_log = frappe.get_all("Payment Link Log", filters={"link_id": razorpay_payment_link_id})
            
            if payment_link_log:
                payment_link_log_doc = frappe.get_doc("Payment Link Log", payment_link_log[0].name)
                payment_link_log_id = payment_link_log_doc.name
                # print('payment_link_log_doc:', payment_link_log_doc)
                # frappe.log_error(f'payment_link_log_doc: {payment_link_log_doc}')  # Debug log
                raz_amount_paid = int(float(razorpay_response.get('amount_paid', 0)) / 100)
                
                # Update fields from Razorpay response
                payment_link_log_doc.paid_amount = raz_amount_paid
                payment_link_log_doc.balance_amount = payment_link_log_doc.total_amount - raz_amount_paid
                payment_link_log_doc.payment_status = razorpay_response.get('status')
                
                # Clear existing child table entries and append new payments
                payment_ids = []
                payment_link_log_doc.set("razorpay_payment_details", [])
                for payment in razorpay_response.get('payments', []):
                    payment_ids.append(payment.get('payment_id'))
                    payment_link_log_doc.append('razorpay_payment_details', {
                        'amount': int(float(payment.get('amount', 0)) / 100),
                        'payment_id': payment.get('payment_id'),
                        'status': payment.get('status'),
                        'method': payment.get('method'),
                        'description': payment.get('method'),  # Correct field name as needed
                        'created_at': frappe.utils.datetime.datetime.fromtimestamp(payment.get('created_at', 0))
                    })
                
                # Update the payment_ids field with a comma-separated list of payment IDs
                razorpay_payment_ids = ','.join(payment_ids)
                payment_link_log_doc.payment_ids = razorpay_payment_ids
                
                # Save the document
                try:
                    payment_link_log_doc.save(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.msgprint("Payment Link Log updated successfully.")
                    frappe.log_error("Payment Link Log updated successfully.")  # Debug log
                except Exception as e:
                    frappe.msgprint(f'Error saving Payment Link Log: {e}')
                    frappe.log_error(f'Error saving Payment Link Log: {e}')  # Debug log
                
                render_payment_success_page(raz_amount_paid, sales_order_id[:18])

                # Proceed if the payment status is 'paid'
                if payment_link_log_doc.payment_status == 'paid':
                    # print('mohaaaaaaaaaaaaaaaaaaaaa')
                    # payment_link_log_id = payment_link_log_doc.name
                    # Fetch Sales Order details
                    sales_order = frappe.get_doc("Sales Order", sales_order_id[:18])
                    # print('sales_orderrrrrrrrrrrrrrrrrrrrrrr',sales_order.order_type)
                    order_type = sales_order.order_type
                    rounded_total = sales_order.rounded_total
                    master_order_id = sales_order.master_order_id
                    razorpay_link_so = sales_order.custom_razorpay_payment_url
                    
                    if order_type == "Rental":
                        security_deposit = sales_order.security_deposit if sales_order.security_deposit else 0
                        if isinstance(security_deposit, str):
                            security_deposit = float(security_deposit) if '.' in security_deposit else int(security_deposit)

                        payment_entry = create_payment_entry(
                            rounded_total, 
                            sales_order_id[:18], 
                            customer, 
                            razorpay_payment_link_id, 
                            rounded_total, 
                            master_order_id,
                            razorpay_response,
                            razorpay_payment_ids
                        )
                        
                        journal_entry = None
                        if security_deposit > 0:
                            frappe.set_user("Administrator")
                            journal_entry = create_journal_entry_razorpay(
                                security_deposit, 
                                sales_order_id[:18], 
                                customer, 
                                razorpay_payment_link_id, 
                                master_order_id,
                                razorpay_payment_ids
                            )
                            # frappe.set_user("Guest")
                        
                        create_razorpay_payment_details(
                            payment_entry, 
                            journal_entry, 
                            sales_order_id[:18], 
                            order_type, 
                            customer, 
                            razorpay_payment_link_id, 
                            razorpay_link_so,
                            payment_link_log_id
                        )
                         
                    
                    else:
                        frappe.msgprint("Order type is not Rental. Proceeding with standard payment entry.")
                        payment_entry = create_payment_entry(
                            rounded_total, 
                            sales_order_id[:18], 
                            customer, 
                            razorpay_payment_link_id, 
                            payment_link_log_doc.paid_amount, 
                            master_order_id,
                            razorpay_response,
                            razorpay_payment_ids
                        )
                        frappe.set_user("Administrator")
                        create_razorpay_payment_details(
                            payment_entry, 
                            None,  # No journal entry for non-rental orders
                            sales_order_id[:18], 
                            order_type, 
                            customer, 
                            razorpay_payment_link_id, 
                            razorpay_link_so,
                            payment_link_log_id
                        )
                        frappe.set_user("Guest")
                        return render_payment_success_page(raz_amount_paid, sales_order_id[:18])
            else:
                frappe.msgprint(f'Payment Link Log not found for link_id: {razorpay_payment_link_id}')
                frappe.log_error(f'Payment Link Log not found for link_id: {razorpay_payment_link_id}')
        else:
            frappe.msgprint(f'Request failed with status code: {response.status_code}')
            frappe.log_error(f'Request failed with status code: {response.status_code}; Response text: {response.text}')
    except Exception as e:
        frappe.msgprint(f'Error: {e}')
        frappe.log_error(f'Error: {e}')



import frappe
from frappe.utils import nowdate

def create_journal_entry_razorpay(security_deposit, sales_order_id, customer, razorpay_payment_link_id, master_order_id,razorpay_payment_ids):
    try:
        # Check if the journal entry already exists
        if is_journal_entry_exists(sales_order_id):
            frappe.msgprint('Journal Entry already exists. Skipping creation.')
            return

        today = frappe.utils.nowdate()

        # Create a new Journal Entry document
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.voucher_type = "Journal Entry"
        journal_entry.sales_order_id = sales_order_id
        journal_entry.posting_date = today
        journal_entry.journal_entry_type = "Security Deposit"
        journal_entry.security_deposite_type = "SD Amount Received From Client"
        journal_entry.master_order_id = master_order_id
        journal_entry.cheque_no = razorpay_payment_ids
        journal_entry.cheque_date = today
        journal_entry.user_remark = f"Security Deposit Payment Against Sales Order {sales_order_id}. Remark: System Generated From RazorPay"
        # journal_entry.customer_id = customer
        journal_entry.mode_of__payment = 'Razorpay'
        journal_entry.transactional_effect = "Plus"
        journal_entry.custom_razorpay = 1

        # Add accounts for debit and credit
        journal_entry.append("accounts", {
            "account": 'Kotak Bank Current Account - INR',
            "debit_in_account_currency": security_deposit
        })
        journal_entry.append("accounts", {
            "account": "Debtors - INR",
            "party_type": "Customer",
            "party": customer,
            "credit_in_account_currency": security_deposit
        })

        # Save and submit the Journal Entry document
        journal_entry.insert(ignore_permissions=True)
        journal_entry.submit()
        frappe.db.commit()
        frappe.msgprint("Security Deposit Journal Entry created successfully.")
        return journal_entry.name
        # frappe.set_user("Guest")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to create Security Deposit Journal Entry"))
        frappe.throw(_("Failed to create Security Deposit Journal Entry. Please try again later."))


import frappe
from frappe.utils import now_datetime

def create_payment_entry(rounded_total, sales_order_id, customer, razorpay_payment_link_id, amount_paid_razorpay, master_order_id, razorpay_response,razorpay_payment_ids):
    try:
        frappe.msgprint("Payment Entry Function Called")
        frappe.set_user("Administrator")

        # Ensure 'payments' is a list
        razorpay_p_id_list = razorpay_response.get('payments', [])
        if not isinstance(razorpay_p_id_list, list):
            razorpay_p_id_list = []

        # Extract payment_id from the first payment entry
        if razorpay_p_id_list:
            razorpay_payment_id = razorpay_p_id_list[0].get('payment_id')
        else:
            frappe.msgprint('No payment details found in the response.')
            return
        
        if is_payment_entry_exists(razorpay_payment_id):
            frappe.msgprint('Payment Entry already exists. Skipping creation.')
            return
        
        # Create Payment Entry
        payment_entry = frappe.get_doc({
            "doctype": "Payment Entry",
            "voucher_type": "Payment Entry",
            "paid_from": "Debtors - INR",
            "paid_to": "Kotak Bank Current Account - INR",
            "received_amount": rounded_total,
            "base_received_amount": rounded_total,
            "paid_amount": int(amount_paid_razorpay),
            "references": [{
                "reference_doctype": "Sales Order",
                "reference_name": sales_order_id,
                "allocated_amount": int(amount_paid_razorpay)
            }],
            "sales_order_id": sales_order_id,
            "custom_system_generator_from_razorpay": 1,
            "reference_date": now_datetime(),
            "account": "Accounts Receivable",
            "party_type": "Customer",
            "party": customer,
            "custom_from_razorpay": 1,
            "master_order_id": master_order_id,
            "mode_of_payment": "Razorpay",
            "reference_no": razorpay_payment_ids
        }, ignore_permissions=True)
        
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()
        frappe.db.commit()

        # frappe.set_user("Guest")
        return payment_entry.name
    except frappe.exceptions.ValidationError as e:
        frappe.log_error(f"Error creating Payment Entry: {e}")
        frappe.msgprint(f'Error creating Payment Entry: {e}')
        return f"Error creating Payment Entry: {e}"
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to create Payment Entry"))
        frappe.throw(_("Failed to create Payment Entry. Please try again later."))




# def create_payment_entry(rounded_total, sales_order_id, customer, razorpay_payment_link_id, actual_amount,master_order_id):
#     try:
#         frappe.msgprint("Payment Entry Function Called")
#         frappe.set_user("Administrator")
        
#         if is_payment_entry_exists(razorpay_payment_link_id):
#             frappe.msgprint('Payment Entry already exists. Skipping creation.')
#             return
        
#         payment_entry = frappe.get_doc({
#             "doctype": "Payment Entry",
#             "paid_from": "Debtors - INR",
#             "paid_to": "Kotak Bank Current Account - INR",
#             "received_amount": rounded_total,
#             "base_received_amount": rounded_total,
#             "paid_amount": int(rounded_total),
#             "references": [{
#                 "reference_doctype": "Sales Order",
#                 "reference_name": sales_order_id,
#                 "allocated_amount": int(actual_amount)
#             }],
#             "sales_order_id": sales_order_id,
#             "custom_system_generator_from_razorpay": 1,
#             "reference_date": frappe.utils.today(),
#             "account": "Accounts Receivable",
#             "party_type": "Customer",
#             "party": customer,
#             "custom_from_razorpay": 1,
#             "master_order_id":master_order_id,
#             "mode_of_payment": "Razorpay",
#             "reference_no": razorpay_payment_link_id
#         }, ignore_permissions=True)
        
#         payment_entry.insert(ignore_permissions=True)
#         payment_entry.submit()
#         frappe.db.commit()
        
#         payment_link_log = frappe.get_all("Payment Link Log", filters={"link_id": razorpay_payment_link_id})
#         if payment_link_log:
#             payment_link_log_doc = frappe.get_doc("Payment Link Log", payment_link_log[0].name)
#             payment_link_log_doc.payment_status = "Paid"
#             payment_link_log_doc.paid_amount = int(actual_amount)
#             payment_link_log_doc.save(ignore_permissions=True)
        
#         frappe.set_user("Guest")
#         return payment_entry.name
#     except frappe.exceptions.ValidationError as e:
#         frappe.log_error(f"Error creating Payment Entry: {e}")
#         frappe.msgprint(f'Error creating Payment Entry: {e}')
#         return f"Error creating Payment Entry: {e}"

def create_razorpay_payment_details(payment_entry_id, journal_entry_id, sales_order_id, order_type, customer, razorpay_payment_link_id, razorpay_link_so, payment_link_log_id):
    try:
        # Check if Razorpay Payment Details already exists
        if is_razorpay_payment_details(razorpay_payment_link_id):
            frappe.msgprint('Razorpay Payment Details already exists. Skipping creation.')
            return
        
        # Create new Razorpay Payment Details document
        razorpay_payment_details = frappe.get_doc({
            "doctype": "Razorpay Payment Details",
            "payment_entry_id": payment_entry_id,
            "journal_entry_id": journal_entry_id,
            "sales_order_id": sales_order_id,
            "order_type": order_type,
            "date": frappe.utils.nowdate(),
            "customer_id": customer,
            "razorpay_link": razorpay_link_so,
            "reference_id": razorpay_payment_link_id
        })
        
        # Insert the new document and commit changes
        razorpay_payment_details.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Update Payment Link Log document with payment and journal entry IDs
        doc = frappe.get_doc('Payment Link Log', payment_link_log_id)
        doc.payment_entry_id = payment_entry_id
        doc.journal_entry_id = journal_entry_id
        doc.save()
        frappe.db.commit()  # Commit the changes to ensure they are saved
        
        # Provide user feedback
        frappe.msgprint("Razorpay Payment Details created and Payment Link Log updated successfully.")
    
    except Exception as e:
        # Log the exception and raise a user-friendly error message
        frappe.log_error(frappe.get_traceback(), "Failed to create Razorpay Payment Details")
        frappe.throw("Failed to create Razorpay Payment Details. Please try again later.")

def render_payment_success_page(amount_paid_razorpay, razorpay_payment_link_id):
    success_html = f"""
    <html>
        <head>
            <title>Payment Success!!!!</title>
            <style>
                .btn.btn-primary.btn-sm.btn-block {{
                    display: none !important;
                }}
            </style>
        </head>
        <body>
            <h1>Payment Successful</h1>
            <p>Transaction: {razorpay_payment_link_id}</p>
            <p>Amount: {amount_paid_razorpay}</p>
        </body>
    </html>
    """
    frappe.respond_as_web_page("Payment Success", success_html)


###############################################################################################


def is_payment_entry_exists(razorpay_payment_id):
    existing_payment_entry = frappe.get_value("Payment Entry", {"reference_no": razorpay_payment_id})
    return bool(existing_payment_entry)

def is_journal_entry_exists(reference_id):
    existing_journal_entry = frappe.get_value("Journal Entry", {
        "sales_order_id": reference_id,
        "security_deposite_type": "SD Amount Received From Client"
    })
    return bool(existing_journal_entry)


def is_razorpay_payment_details(reference_id):
    is_razorpay_payment_details = frappe.get_value("Razorpay Payment Details", {
        "reference_id": reference_id
    })
    return bool(is_razorpay_payment_details)



#####################################################################################




import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice, make_delivery_note

@frappe.whitelist()
def create_sales_invoice_and_delivery_note(docname):
    try:
        # Fetch the Sales Order document
        sales_order = frappe.get_doc("Sales Order", docname)

        # Check if a Sales Invoice already exists for this Sales Order
        existing_sales_invoices = frappe.get_all("Sales Invoice",
                                                 filters={"sales_order": docname},
                                                 fields=["name"])
        if existing_sales_invoices:
            return {"message": "A Sales Invoice has already been created for this Sales Order."}

        # Check if a Delivery Note already exists for this Sales Order
        existing_delivery_notes = frappe.get_all("Delivery Note",
                                                  filters={"against_sales_order": docname},
                                                  fields=["name"])
        if existing_delivery_notes:
            return {"message": "A Delivery Note has already been created for this Sales Order."}

        # Create Sales Invoice
        sales_invoice = make_sales_invoice(docname)
        sales_invoice.allocate_advances_automatically = 1
        sales_invoice.only_include_allocated_payments = 1
        sales_invoice.insert(ignore_permissions=True)
        # sales_invoice.submit()

        # Create Delivery Note in draft status
        delivery_note_name = None
        items_with_serial_numbers = []
        if sales_order.items:
            delivery_note = make_delivery_note(docname)
            delivery_note.insert(ignore_permissions=True)
            delivery_note_name = delivery_note.name

            # Collect items with serial numbers
            for item in delivery_note.items:
                if item.serial_no and item.item_code not in items_with_serial_numbers:
                    items_with_serial_numbers.append({
                        'item_code': item.item_code,
                        'serial_numbers': get_serial_numbers(item.item_code)
                    })

        return {
            "sales_invoice": sales_invoice.name,
            "delivery_note": delivery_note_name,
            "items_with_serial_numbers": items_with_serial_numbers
        }

    except frappe.exceptions.ValidationError as e:
        frappe.log_error(f"ValidationError while creating Sales Invoice and Delivery Note: {e}", "Sales Order Creation Error")
        return {"message": str(e)}
    except frappe.exceptions.DuplicateEntryError as e:
        frappe.log_error(f"DuplicateEntryError while creating Sales Invoice and Delivery Note: {e}", "Sales Order Creation Error")
        return {"message": str(e)}
    except Exception as e:
        frappe.log_error(f"Error creating Sales Invoice and Delivery Note: {e}", "Sales Order Creation Error")
        return {"message": str(e)}

@frappe.whitelist()
def update_delivery_note_serial_numbers(docname, serial_numbers, item_code):
    try:
        delivery_note = frappe.get_doc("Delivery Note", docname)
        for item in delivery_note.items:
            if item.item_code == item_code:
                item.serial_no = serial_numbers[item.name]
        delivery_note.save(ignore_permissions=True)
        delivery_note.submit()
        return {"message": "Delivery Note updated successfully"}
    except Exception as e:
        frappe.log_error(f"Error updating Delivery Note serial numbers: {e}", "Delivery Note Update Error")
        return {"message": str(e)}

@frappe.whitelist()
def get_serial_numbers(item_code):
    try:
        # Fetch serial numbers where item_name matches and status is Active
        serial_numbers = frappe.get_all("Serial No",
                                         filters={"item_code": item_code, "status": "Active"},
                                         fields=["name"])

        return [serial_number.name for serial_number in serial_numbers]

    except Exception as e:
        frappe.log_error(f"Error fetching serial numbers: {e}")
        return []

@frappe.whitelist()
def submit_delivery_note(docname):
    try:
        delivery_note = frappe.get_doc("Delivery Note", docname)
        delivery_note.submit()
        return {"message": "Delivery Note submitted successfully"}
    except Exception as e:
        frappe.log_error(f"Error submitting Delivery Note: {e}", "Delivery Note Submission Error")
        return {"message": str(e)}

@frappe.whitelist()
def get_delivery_note_serial_numbers(docname):
    try:
        delivery_note = frappe.get_doc("Delivery Note", docname)
        serial_numbers_data = []
        for item in delivery_note.items:
            serial_and_batch_bundle = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
            serial_numbers = [entry.serial_no for entry in serial_and_batch_bundle.entries]
            serial_numbers_data.append({
                "item_code": item.item_code,
                "serial_numbers": serial_numbers
            })
        return {"serial_numbers": serial_numbers_data}
    except Exception as e:
        frappe.log_error(f"Error fetching serial numbers for Delivery Note {docname}: {e}", "Delivery Note Serial Numbers Error")
        return {"message": str(e)}

@frappe.whitelist()
def update_sales_order_with_serial_numbers(sales_order_name, delivery_note_name):
    try:
        delivery_note = frappe.get_doc("Delivery Note", delivery_note_name)
        sales_order = frappe.get_doc("Sales Order", sales_order_name)

        for dn_item in delivery_note.items:
            for so_item in sales_order.items:
                if dn_item.item_code == so_item.item_code:
                    serial_and_batch_bundle = frappe.get_doc("Serial and Batch Bundle", dn_item.serial_and_batch_bundle)
                    serial_numbers = ', '.join([entry.serial_no for entry in serial_and_batch_bundle.entries])
                    so_item.serial_no = serial_numbers
        sales_order.status = "Sales Completed"
        sales_order.save(ignore_permissions=True)
        return {"message": "Sales Order updated with serial numbers successfully"}
    except Exception as e:
        frappe.log_error(f"Error updating Sales Order {sales_order_name} with serial numbers from Delivery Note {delivery_note_name}: {e}", "Sales Order Serial Numbers Update Error")
        return {"message": str(e)}






@frappe.whitelist()
def get_bin_data(item_codes):
    # Convert item_codes string to a list
    item_codes_list = list(set(frappe.parse_json(item_codes)))
 
 
    # Initialize a list to store warehouse quantities for each item
    items_data = []
    warehouse=[]
    # Query Bin data based on the provided item codes
    for item_code in item_codes_list:
        item_data = {'item_code': item_code, 'warehouse_qty': {}}
        bin_data = frappe.get_all('Bin',
                                  filters={'item_code': item_code},
                                  fields=['warehouse', 'actual_qty'])
        for data in bin_data:
            item_data['warehouse_qty'][data['warehouse']] = data['actual_qty']
            if data['warehouse'] not in warehouse:
                warehouse.append(data['warehouse'])
        items_data.append(item_data)
    # print(items_data)
 
    return {'items_data':items_data,'warehouse':warehouse}





@frappe.whitelist()
def check_sales_order_items(item_code):
    # Query Sales Order Items with item_code
    sales_order_items = frappe.get_all('Sales Order Item',
                                        filters={'item_code': item_code},
                                        fields=['parent'])

    return sales_order_items



@frappe.whitelist()
def get_rental_order_items_status():
    # Fetch all Sales Orders with status 'Active' and order_type 'Rental'
    sales_orders = frappe.get_all('Sales Order', filters={
        'status': 'Active',
        'order_type': 'Rental',
        'docstatus':1,
    }, fields=['name', 'status'])

    if not sales_orders:
        return "No active rental orders found."

    items_status = []
    for order in sales_orders:
        # Fetch all items in the Sales Order
        items = frappe.get_all('Sales Order Item', filters={
            'parent': order.name
        }, fields=['item_code'])
        
        for item in items:
            # Fetch the status of the item using item_code
            item_doc = frappe.get_doc('Item', item.item_code)
            item_status = item_doc.get('status', 'Unknown')  # Replace 'status' with the actual field name if different
            
            if item_status != 'Rented Out':
                items_status.append(f"Sales Order: {order.name}, Item: {item.item_code}, Item Status: {item_status}, Sales Order Status: {order.status}")

    if not items_status:
        return "No available items found for the specified sales orders."

    # Join the list into a single string with HTML line breaks
    return "<br>".join(items_status)





@frappe.whitelist()
def fetch_balance_amount_for_sales_order(sales_order):
    try:
        # Fetch the Sales Order document
        sales_order_doc = frappe.get_doc("Sales Order", sales_order)
        
        # Return the balance_amount from the Sales Order document
        return sales_order_doc.balance_amount

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Failed to fetch balance amount for Sales Order {0}").format(sales_order))
        return None
    


# find item code which is presant in other sales order (mohan code)

@frappe.whitelist()
def get_sales_orders_containing_item(item_code):
    item_status = frappe.db.get_value("Item", item_code, "status")
    item_group = frappe.db.get_value("Item", item_code, "item_group")
    sales_orders = frappe.db.sql("""
        SELECT
            so.name,
            so.customer_name,
            so.status
        FROM
            `tabSales Order` so
        JOIN
            `tabSales Order Item` soi ON soi.parent = so.name
        WHERE
            soi.item_code = %s
        AND
            so.docstatus < 2
        AND
            so.status != 'Submitted to Office'
    """, item_code, as_dict=True)
    # print(sales_orders)
    return {
        'item_status': item_status,
        'item_group': item_group,
        'sales_orders': sales_orders
    }



# @frappe.whitelist()
# def update_item_status(item_code, status):
#     try:
#         item = frappe.get_doc('Item', item_code)
#         if item:
#             item.status = status
#             item.save()
#             return 'success'
#         else:
#             frappe.throw(f"Item '{item_code}' not found.")
#     except Exception as e:
#         frappe.throw(f"Error updating item '{item_code}' status: {str(e)}")


@frappe.whitelist()
def update_item_status(item_code, status):
    # Fetch the item document
    item = frappe.get_doc('Item', item_code)
    # Update the status
    item.status = status
    # Save the changes
    item.save()
    # Commit the transaction
    frappe.db.commit()
    return f"Item {item_code} updated to status {status}"





import frappe

@frappe.whitelist()
def get_rental_order_details(item_code):
    """
    Fetches sales orders containing the specified item code in their items.
    """
    rental_orders = frappe.get_all(
        'Sales Order',
        filters={
            'docstatus': 0,  # Submitted orders have docstatus 1
        },
        fields=['name', 'customer_name', 'status']
    )

    orders_with_item = []

    for order in rental_orders:
        items = frappe.get_all(
            'Sales Order Item',
            filters={
                'parent': order.name,
                'item_code': item_code
            },
            fields=['name']
        )

        if items:
            orders_with_item.append(order)

    return orders_with_item

@frappe.whitelist()
def get_rental_orders_details_batch(item_codes):
    """
    Fetches Sales orders containing the specified item codes in their items.
    """
    orders_with_items = []

    for item_code in item_codes:
        sales_orders = frappe.get_all(
            'Sales Order',
            filters={
                'docstatus': 0,  # Submitted orders have docstatus 1
            },
            fields=['name', 'customer_name', 'status']
        )

        for order in sales_orders:
            items = frappe.get_all(
                'Sales Order Item',
                filters={
                    'parent': order.name,
                    'item_code': item_code
                },
                fields=['name']
            )

            if items:
                orders_with_items.append(order)

    return orders_with_items







@frappe.whitelist()
def get_payment_link_log_data(parent_id):
    if not parent_id:
        return []

    # Fetch records from Payment Link Log Child where parent matches
    payment_link_logs = frappe.get_all(
        "Payment Link Log Child",
        filters={"parent": parent_id},
        fields=["amount", "payment_id", "created_at", "method", "status"]
    )

    return payment_link_logs




@frappe.whitelist()
def get_sales_orders_with_payment_urls():
    sales_orders = frappe.get_all('Sales Order', filters={
        'custom_razorpay_payment_url': ['!=', ''],'docstatus':1
    }, fields=['name', 'custom_razorpay_payment_url'])
    return sales_orders
@frappe.whitelist()
def get_payment_link_log_id(custom_razorpay_payment_url):
    payment_link_log = frappe.get_value('Payment Link Log', {
        'link_short_url': custom_razorpay_payment_url,
        'enabled': 1
    }, 'name')
    return payment_link_log
