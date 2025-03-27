// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tax_table = "Sales Taxes and Charges";

erpnext.accounts.taxes.setup_tax_filters("Sales Taxes and Charges");
erpnext.accounts.taxes.setup_tax_validations("Sales Order");
erpnext.sales_common.setup_selling_controller();

frappe.ui.form.on("Sales Order", {
	setup: function (frm) {
		frm.custom_make_buttons = {
			"Delivery Note": "Delivery Note",
			"Pick List": "Pick List",
			"Sales Invoice": "Sales Invoice",
			"Material Request": "Material Request",
			"Purchase Order": "Purchase Order",
			Project: "Project",
			"Payment Entry": "Payment",
			"Work Order": "Work Order",
		};
		frm.add_fetch("customer", "tax_id", "tax_id");

		// formatter for material request item
		frm.set_indicator_formatter("item_code", function (doc) {
			return doc.stock_qty <= doc.delivered_qty ? "green" : "orange";
		});

		frm.set_query("company_address", function (doc) {
			if (!doc.company) {
				frappe.throw(__("Please set Company"));
			}

			return {
				query: "frappe.contacts.doctype.address.address.address_query",
				filters: {
					link_doctype: "Company",
					link_name: doc.company,
				},
			};
		});

		frm.set_query("bom_no", "items", function (doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			return {
				filters: {
					item: row.item_code,
				},
			};
		});

		frm.set_df_property("packed_items", "cannot_add_rows", true);
		frm.set_df_property("packed_items", "cannot_delete_rows", true);
	},

	refresh: function (frm) {
		
		if (frm.doc.docstatus === 1) {
			if (
				frm.doc.status !== "Closed" &&
				flt(frm.doc.per_delivered, 2) < 100 &&
				flt(frm.doc.per_billed, 2) < 100
			) {
				// frm.add_custom_button(__("Update Items"), () => {
				// 	erpnext.utils.update_child_items({
				// 		frm: frm,
				// 		child_docname: "items",
				// 		child_doctype: "Sales Order Detail",
				// 		cannot_add_row: false,
				// 		has_reserved_stock: frm.doc.__onload && frm.doc.__onload.has_reserved_stock,
				// 	});
				// });

				// Stock Reservation > Reserve button should only be visible if the SO has unreserved stock and no Pick List is created against the SO.
				if (
					frm.doc.__onload &&
					frm.doc.__onload.has_unreserved_stock &&
					flt(frm.doc.per_picked) === 0
				) {
					frm.add_custom_button(
						__("Reserve"),
						() => frm.events.create_stock_reservation_entries(frm),
						__("Stock Reservation")
					);
				}
			}

			// Stock Reservation > Unreserve button will be only visible if the SO has un-delivered reserved stock.
			if (frm.doc.__onload && frm.doc.__onload.has_reserved_stock) {
				frm.add_custom_button(
					__("Unreserve"),
					() => frm.events.cancel_stock_reservation_entries(frm),
					__("Stock Reservation")
				);
			}

			frm.doc.items.forEach((item) => {
				if (flt(item.stock_reserved_qty) > 0) {
					frm.add_custom_button(
						__("Reserved Stock"),
						() => frm.events.show_reserved_stock(frm),
						__("Stock Reservation")
					);
					return;
				}
			});
		}

		if (frm.doc.docstatus === 0) {
			if (frm.doc.is_internal_customer) {
				frm.events.get_items_from_internal_purchase_order(frm);
			}

			if (frm.doc.docstatus === 0) {
				frappe.db.get_single_value("Stock Settings", "enable_stock_reservation").then((value) => {
					if (!value) {
						// If `Stock Reservation` is disabled in Stock Settings, set Reserve Stock to 0 and make the field read-only and hidden.
						frm.set_value("reserve_stock", 0);
						frm.set_df_property("reserve_stock", "read_only", 1);
						frm.set_df_property("reserve_stock", "hidden", 1);
						frm.fields_dict.items.grid.update_docfield_property("reserve_stock", "hidden", 1);
						frm.fields_dict.items.grid.update_docfield_property("reserve_stock", "default", 0);
						frm.fields_dict.items.grid.update_docfield_property("reserve_stock", "read_only", 1);
					}
				});
			}
		}

		// Hide `Reserve Stock` field description in submitted or cancelled Sales Order.
		if (frm.doc.docstatus > 0) {
			frm.set_df_property("reserve_stock", "description", null);
		}
	},

	get_items_from_internal_purchase_order(frm) {
		frm.add_custom_button(
			__("Purchase Order"),
			() => {
				erpnext.utils.map_current_doc({
					method: "erpnext.buying.doctype.purchase_order.purchase_order.make_inter_company_sales_order",
					source_doctype: "Purchase Order",
					target: frm,
					setters: [
						{
							label: "Supplier",
							fieldname: "supplier",
							fieldtype: "Link",
							options: "Supplier",
						},
					],
					get_query_filters: {
						company: frm.doc.company,
						is_internal_supplier: 1,
						docstatus: 1,
						status: ["!=", "Completed"],
					},
				});
			},
			__("Get Items From")
		);
	},

	onload: function (frm) {
		if (!frm.doc.transaction_date) {
			frm.set_value("transaction_date", frappe.datetime.get_today());
		}
		erpnext.queries.setup_queries(frm, "Warehouse", function () {
			return {
				filters: [["Warehouse", "company", "in", ["", cstr(frm.doc.company)]]],
			};
		});

		frm.set_query("warehouse", "items", function (doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			let query = {
				filters: [["Warehouse", "company", "in", ["", cstr(frm.doc.company)]]],
			};
			if (row.item_code) {
				query.query = "erpnext.controllers.queries.warehouse_query";
				query.filters.push(["Bin", "item_code", "=", row.item_code]);
			}
			return query;
		});

		// On cancel and amending a sales order with advance payment, reset advance paid amount
		if (frm.is_new()) {
			frm.set_value("advance_paid", 0);
			frm.set_value("master_order_id","");
		}

		frm.ignore_doctypes_on_cancel_all = ["Purchase Order"];
	},

	delivery_date: function (frm) {
		$.each(frm.doc.items || [], function (i, d) {
			if (!d.delivery_date) d.delivery_date = frm.doc.delivery_date;
		});
		refresh_field("items");
	},

	create_stock_reservation_entries(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Stock Reservation"),
			size: "extra-large",
			fields: [
				{
					fieldname: "set_warehouse",
					fieldtype: "Link",
					label: __("Set Warehouse"),
					options: "Warehouse",
					default: frm.doc.set_warehouse,
					get_query: () => {
						return {
							filters: [["Warehouse", "is_group", "!=", 1]],
						};
					},
					onchange: () => {
						if (dialog.get_value("set_warehouse")) {
							dialog.fields_dict.items.df.data.forEach((row) => {
								row.warehouse = dialog.get_value("set_warehouse");
							});
							dialog.fields_dict.items.grid.refresh();
						}
					},
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "add_item",
					fieldtype: "Link",
					label: __("Add Item"),
					options: "Sales Order Item",
					get_query: () => {
						return {
							query: "erpnext.controllers.queries.get_filtered_child_rows",
							filters: {
								parenttype: frm.doc.doctype,
								parent: frm.doc.name,
								reserve_stock: 1,
							},
						};
					},
					onchange: () => {
						let sales_order_item = dialog.get_value("add_item");

						if (sales_order_item) {
							frm.doc.items.forEach((item) => {
								if (item.name === sales_order_item) {
									let unreserved_qty =
										(flt(item.stock_qty) -
											(item.stock_reserved_qty
												? flt(item.stock_reserved_qty)
												: flt(item.delivered_qty) * flt(item.conversion_factor))) /
										flt(item.conversion_factor);

									if (unreserved_qty > 0) {
										dialog.fields_dict.items.df.data.forEach((row) => {
											if (row.sales_order_item === sales_order_item) {
												unreserved_qty -= row.qty_to_reserve;
											}
										});
									}

									dialog.fields_dict.items.df.data.push({
										sales_order_item: item.name,
										item_code: item.item_code,
										warehouse: dialog.get_value("set_warehouse") || item.warehouse,
										qty_to_reserve: Math.max(unreserved_qty, 0),
									});
									dialog.fields_dict.items.grid.refresh();
									dialog.set_value("add_item", undefined);
								}
							});
						}
					},
				},
				{ fieldtype: "Section Break" },
				{
					fieldname: "items",
					fieldtype: "Table",
					label: __("Items to Reserve"),
					allow_bulk_edit: false,
					cannot_add_rows: true,
					data: [],
					fields: [
						{
							fieldname: "sales_order_item",
							fieldtype: "Link",
							label: __("Sales Order Item"),
							options: "Sales Order Item",
							reqd: 1,
							in_list_view: 1,
							get_query: () => {
								return {
									query: "erpnext.controllers.queries.get_filtered_child_rows",
									filters: {
										parenttype: frm.doc.doctype,
										parent: frm.doc.name,
										reserve_stock: 1,
									},
								};
							},
							onchange: (event) => {
								if (event) {
									let name = $(event.currentTarget).closest(".grid-row").attr("data-name");
									let item_row =
										dialog.fields_dict.items.grid.grid_rows_by_docname[name].doc;

									frm.doc.items.forEach((item) => {
										if (item.name === item_row.sales_order_item) {
											item_row.item_code = item.item_code;
										}
									});
									dialog.fields_dict.items.grid.refresh();
								}
							},
						},
						{
							fieldname: "item_code",
							fieldtype: "Link",
							label: __("Item Code"),
							options: "Item",
							reqd: 1,
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldname: "warehouse",
							fieldtype: "Link",
							label: __("Warehouse"),
							options: "Warehouse",
							reqd: 1,
							in_list_view: 1,
							get_query: () => {
								return {
									filters: [["Warehouse", "is_group", "!=", 1]],
								};
							},
						},
						{
							fieldname: "qty_to_reserve",
							fieldtype: "Float",
							label: __("Qty"),
							reqd: 1,
							in_list_view: 1,
						},
					],
				},
			],
			primary_action_label: __("Reserve Stock"),
			primary_action: () => {
				var data = { items: dialog.fields_dict.items.grid.data };

				if (data.items && data.items.length > 0) {
					frappe.call({
						doc: frm.doc,
						method: "create_stock_reservation_entries",
						args: {
							items_details: data.items,
							notify: true,
						},
						freeze: true,
						freeze_message: __("Reserving Stock..."),
						callback: (r) => {
							frm.doc.__onload.has_unreserved_stock = false;
							frm.reload_doc();
						},
					});
				}

				dialog.hide();
			},
		});

		frm.doc.items.forEach((item) => {
			if (item.reserve_stock) {
				let unreserved_qty =
					(flt(item.stock_qty) -
						(item.stock_reserved_qty
							? flt(item.stock_reserved_qty)
							: flt(item.delivered_qty) * flt(item.conversion_factor))) /
					flt(item.conversion_factor);

				if (unreserved_qty > 0) {
					dialog.fields_dict.items.df.data.push({
						sales_order_item: item.name,
						item_code: item.item_code,
						warehouse: item.warehouse,
						qty_to_reserve: unreserved_qty,
					});
				}
			}
		});

		dialog.fields_dict.items.grid.refresh();
		dialog.show();
	},

	cancel_stock_reservation_entries(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Stock Unreservation"),
			size: "extra-large",
			fields: [
				{
					fieldname: "sr_entries",
					fieldtype: "Table",
					label: __("Reserved Stock"),
					allow_bulk_edit: false,
					cannot_add_rows: true,
					in_place_edit: true,
					data: [],
					fields: [
						{
							fieldname: "sre",
							fieldtype: "Link",
							label: __("Stock Reservation Entry"),
							options: "Stock Reservation Entry",
							reqd: 1,
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldname: "item_code",
							fieldtype: "Link",
							label: __("Item Code"),
							options: "Item",
							reqd: 1,
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldname: "warehouse",
							fieldtype: "Link",
							label: __("Warehouse"),
							options: "Warehouse",
							reqd: 1,
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldname: "qty",
							fieldtype: "Float",
							label: __("Qty"),
							reqd: 1,
							read_only: 1,
							in_list_view: 1,
						},
					],
				},
			],
			primary_action_label: __("Unreserve Stock"),
			primary_action: () => {
				var data = { sr_entries: dialog.fields_dict.sr_entries.grid.data };

				if (data.sr_entries && data.sr_entries.length > 0) {
					frappe.call({
						doc: frm.doc,
						method: "cancel_stock_reservation_entries",
						args: {
							sre_list: data.sr_entries.map((item) => item.sre),
						},
						freeze: true,
						freeze_message: __("Unreserving Stock..."),
						callback: (r) => {
							frm.doc.__onload.has_reserved_stock = false;
							frm.reload_doc();
						},
					});
				}

				dialog.hide();
			},
		});

		frappe
			.call({
				method: "erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry.get_stock_reservation_entries_for_voucher",
				args: {
					voucher_type: frm.doctype,
					voucher_no: frm.docname,
				},
				callback: (r) => {
					if (!r.exc && r.message) {
						r.message.forEach((sre) => {
							if (flt(sre.reserved_qty) > flt(sre.delivered_qty)) {
								dialog.fields_dict.sr_entries.df.data.push({
									sre: sre.name,
									item_code: sre.item_code,
									warehouse: sre.warehouse,
									qty: flt(sre.reserved_qty) - flt(sre.delivered_qty),
								});
							}
						});
					}
				},
			})
			.then((r) => {
				dialog.fields_dict.sr_entries.grid.refresh();
				dialog.show();
			});
	},

	show_reserved_stock(frm) {
		// Get the latest modified date from the items table.
		var to_date = moment(new Date(Math.max(...frm.doc.items.map((e) => new Date(e.modified))))).format(
			"YYYY-MM-DD"
		);

		frappe.route_options = {
			company: frm.doc.company,
			from_date: frm.doc.transaction_date,
			to_date: to_date,
			voucher_type: frm.doc.doctype,
			voucher_no: frm.doc.name,
		};
		frappe.set_route("query-report", "Reserved Stock");
	},
});

frappe.ui.form.on("Sales Order Item", {
	// item_code: function (frm, cdt, cdn) {
	// 	var row = locals[cdt][cdn];
	// 	if (frm.doc.delivery_date) {
	// 		row.delivery_date = frm.doc.delivery_date;
	// 		refresh_field("delivery_date", cdn, "items");
	// 	} else {
	// 		frm.script_manager.copy_from_first_row("items", row, ["delivery_date"]);
	// 	}
	// },
	// delivery_date: function (frm, cdt, cdn) {
	// 	if (!frm.doc.delivery_date) {
	// 		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "delivery_date");
	// 	}
	// },
});

erpnext.selling.SalesOrderController = class SalesOrderController extends erpnext.selling.SellingController {
	onload(doc, dt, dn) {
		super.onload(doc, dt, dn);
	}

	refresh(doc, dt, dn) {
		var me = this;
		super.refresh();
		let allow_delivery = false;

		if (doc.docstatus == 1) {
			if(this.frm.has_perm("submit")) {
				// 	if(doc.status === 'On Hold') {
				// 	   // un-hold
				// 	   this.frm.add_custom_button(__('Resume'), function() {
				// 		   me.frm.cscript.update_status('Resume', 'Draft')
				// 	   }, __("Status"));
	
				// 	   if(flt(doc.per_delivered, 2) < 100 || flt(doc.per_billed, 2) < 100) {
				// 		   // close
				// 		   this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
				// 	   }
				// 	}
				//    	else if(doc.status === 'Closed') {
				// 	   // un-close
				// 	   this.frm.add_custom_button(__('Re-open'), function() {
				// 		   me.frm.cscript.update_status('Re-open', 'Draft')
				// 	   }, __("Status"));
				//    }
				if (doc.status === 'On Hold') {
					// un-hold
					this.frm.add_custom_button(__('Resume'), function() {
						frappe.call({
							method: 'erpnext.selling.doctype.sales_order.sales_order.update_status',
							args: {
								docname: me.frm.doc.name,
								new_status: 'Pending'
							},
							callback: function(response) {
								if (!response.exc) {
									frappe.show_alert({
										message: __('Document Resumed successfully.'),
										indicator: 'green'
									});
									setTimeout(() => {
										window.location.reload();
									}, 1000); // 1000 milliseconds = 1 second
								} else {
									frappe.msgprint(__('Error while resuming document.'));
								}
							}
						});
					}, __("Status"));
				
					if (flt(doc.per_delivered, 2) < 100 || flt(doc.per_billed, 2) < 100) {
						// close
						this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"));
					}
				} else if (doc.status === 'Closed') {
					// un-close
					this.frm.add_custom_button(__('Re-open'), function() {
						frappe.call({
							method: 'erpnext.selling.doctype.sales_order.sales_order.update_status',
							args: {
								docname: me.frm.doc.name,
								new_status: 'Pending'
							},
							callback: function(response) {
								if (!response.exc) {
									frappe.show_alert({
										message: __('Document Reopened successfully.'),
										indicator: 'green'
									});
									setTimeout(() => {
										window.location.reload();
									}, 1000); // 1000 milliseconds = 1 second
								} else {
									frappe.msgprint(__('Error while reopening document.'));
								}
							}
						});
					}, __("Status"));
				}
				
				
				}
			if (doc.status !== "Closed") {
				if (doc.status !== "On Hold") {
					allow_delivery =
						this.frm.doc.items.some(
							(item) => item.delivered_by_supplier === 0 && item.qty > flt(item.delivered_qty)
						) && !this.frm.doc.skip_delivery_note;

					if (this.frm.has_perm("submit")) {
						// if (flt(doc.per_delivered, 2) < 100 || flt(doc.per_billed, 2) < 100) {
						// 	// hold
						// 	this.frm.add_custom_button(
						// 		__("Hold"),
						// 		() => this.hold_sales_order(),
						// 		__("Status")
						// 	);
						// 	// close
						// 	this.frm.add_custom_button(
						// 		__("Close"),
						// 		() => this.close_sales_order(),
						// 		__("Status")
						// 	);
						// }
						//if(flt(doc.per_delivered, 2) < 100 || flt(doc.per_billed, 2) < 100 || this.doc.status === "Pending") {
							// hold
							//this.frm.add_custom_button(__('Hold'), () => this.hold_rental_sales_order(), __("Status"))
							// close
							//this.frm.add_custom_button(__('Close'), () => this.close_rental_sales_order(), __("Status"))
						//}
					}

					// if (!doc.__onload || !doc.__onload.has_reserved_stock) {
					// 	// Don't show the `Reserve` button if the Sales Order has Picked Items.
					// 	if (flt(doc.per_picked, 2) < 100 && flt(doc.per_delivered, 2) < 100) {
					// 		this.frm.add_custom_button(
					// 			__("Pick List"),
					// 			() => this.create_pick_list(),
					// 			__("Create")
					// 		);
					// 	}
					// }

					const order_is_a_sale = ["Sales", "Shopping Cart"].indexOf(doc.order_type) !== -1;
					const order_is_maintenance = ["Maintenance"].indexOf(doc.order_type) !== -1;
					// order type has been customised then show all the action buttons
					const order_is_a_custom_sale =
						["Sales", "Shopping Cart", "Maintenance"].indexOf(doc.order_type) === -1;




					// Approved


					if (flt(doc.per_billed, 2) < 100 && doc.status === 'Pending' && doc.order_type === 'Rental') {
						this.frm.add_custom_button(__('Approved'), () => {
							// First confirmation dialog
							frappe.confirm(
								__('Are you sure you want to approve? It will Reserve the Item.'),
								() => {
									// User confirmed the first dialog
									// Create a custom dialog for further actions
									let d = new frappe.ui.Dialog({
										title: __('Select an Option'),
										fields: [
											{
												label: __('Share Payment Link and Approve'),
												fieldname: 'share_payment_link',
												fieldtype: 'Button'
											},
											{
												label: __('Approve Without Sharing the Payment Link'),
												fieldname: 'without_payment_link',
												fieldtype: 'Button'
											},
											{
												fieldtype: 'Section Break'
											},
											{
												label: __('Notify through whatsapp'),
												fieldname: 'notify_through_whatsapp',
												fieldtype: 'Check',
												default: 1
											},
											{
												label: __('Mobile No.'),
												fieldname: 'mobile_no',
												fieldtype: 'Data',
												default: doc.customer_mobile_no,
												depends_on: 'eval:doc.notify_through_whatsapp',
												reqd: 1,  // Make field required
												description: __('Only 10 digits are allowed.'),
												on_change: (value) => {
													// Remove any non-numeric characters
													const numericValue = value.replace(/\D/g, '');
											
													// Check if the value has exactly 10 digits
													if (numericValue.length !== 10) {
														frappe.msgprint({
															title: __('Invalid Mobile Number'),
															message: __('Please enter a valid 10-digit mobile number. Only numbers are allowed.'),
															indicator: 'red'
														});
											
														// Optionally, clear the field or reset the value to numeric characters only
													} 
												}
											},
											
											{
												label: __('Message'),
												fieldname: 'message',
												fieldtype: 'Small Text',
												default: `
Hello ${doc.customer_name},
Your order ID ${doc.name} has been successfully approved. 
For any query, call/WhatsApp on 8884880013.
${doc.custom_razorpay_payment_url ? `\n🔗 Payment Link: ${doc.custom_razorpay_payment_url}` : ''}`,
												depends_on: 'eval:doc.notify_through_whatsapp'
											},
											{
												fieldtype: 'Section Break'
											},
											{
												label: __('Cancel'),
												fieldname: 'cancel',
												fieldtype: 'Button'
											}
										]
									});
					
									d.fields_dict.share_payment_link.$input.click(() => {
										d.hide();
										me.make_approved_with_payment_link(d.get_values());
									});
					
									d.fields_dict.without_payment_link.$input.click(() => {
										d.hide();
										me.make_approved(d.get_values());
									});
					
									d.fields_dict.cancel.$input.click(() => {
										d.hide();
										// Do nothing on cancel
									});
					
									d.show();
								},
								() => {
									// User explicitly canceled the first dialog
									// Do nothing here
								}
							);
						}, __('Action'));
					}
										
					




					// if (flt(doc.per_billed, 2) < 100 && doc.status === 'Pending' && doc.order_type === 'Rental') {
					// 	this.frm.add_custom_button(__('Approved'), () => {
					// 		frappe.confirm(
					// 			__('Are you sure you want to approve? It will Reserve the Item.'),
					// 			() => {
					// 				// User confirmed, now ask if they want to share the payment link
					// 				frappe.confirm(
					// 					__('Do you want to share the payment link?'),
					// 					() => {
					// 						// User confirmed to share the payment link
					// 						// Call your new function here
					// 						me.make_approved_with_payment_link();
					// 					},
					// 					() => {
					// 						// User canceled sharing the payment link
					// 						me.make_approved(false); // Call the original function with false flag
					// 					}
					// 				);
					// 			},
					// 			() => {
					// 				// Do nothing on cancel
					// 			}
					// 		);
					// 	}, __('Action'));
					// }


                    // if (flt(doc.per_billed, 2) < 100 && doc.status === 'Pending' && doc.order_type === 'Rental') {
                    //     this.frm.add_custom_button(__('Approved'), () => {
                    //         frappe.confirm(
                    //             __('Are you sure you want to approve. It will Reserve the Item?'),
                    //             () => {
                    //                 me.make_approved(); // Call the JavaScript method
                    //             },
                    //             () => {
                    //                 // Do nothing on cancel
                    //             }
                    //         );
                    //     }, __('Action'));
                    // }

					if (flt(doc.per_billed, 2) < 100 && doc.status === 'Pending' && (doc.order_type === 'Sales' || doc.order_type === 'Service')) {
                        this.frm.add_custom_button(__('Approved'), () => {
							frappe.confirm(
								__('Are you sure you want to approve? It will Reserve the Item.'),
								() => {
									// User confirmed the first dialog
									// Create a custom dialog for further actions
									let d = new frappe.ui.Dialog({
										title: __('Select an Option'),
										fields: [
											{
												label: __('Share Payment Link and Approve'),
												fieldname: 'share_payment_link',
												fieldtype: 'Button'
											},
											{
												label: __('Approve Without Sharing the Payment Link'),
												fieldname: 'without_payment_link',
												fieldtype: 'Button'
											},
											{
												fieldtype: 'Section Break'
											},
											{
												label: __('Notify through whatsapp'),
												fieldname: 'notify_through_whatsapp',
												fieldtype: 'Check',
												default: 1
											},
											{
												label: __('Mobile No.'),
												fieldname: 'mobile_no',
												fieldtype: 'Data',
												default: doc.customer_mobile_no,
												depends_on: 'eval:doc.notify_through_whatsapp',
												reqd: 1,  // Make field required
												description: __('Only 10 digits are allowed.'),
												on_change: (value) => {
													// Remove any non-numeric characters
													const numericValue = value.replace(/\D/g, '');
											
													// Check if the value has exactly 10 digits
													if (numericValue.length !== 10) {
														frappe.msgprint({
															title: __('Invalid Mobile Number'),
															message: __('Please enter a valid 10-digit mobile number. Only numbers are allowed.'),
															indicator: 'red'
														});
											
														// Optionally, clear the field or reset the value to numeric characters only
													} 
												}
											},
											
											{
												label: __('Message'),
												fieldname: 'message',
												fieldtype: 'Small Text',
												default: `
Hello ${frm.doc.customer_name},
Your order ID ${frm.doc.name} has been successfully approved. 
For any query, call/WhatsApp on 8884880013.
${frm.doc.custom_razorpay_payment_url ? `\n🔗 Payment Link: ${frm.doc.custom_razorpay_payment_url}` : ''}`,
												depends_on: 'eval:doc.notify_through_whatsapp'
											},
											
											{
												fieldtype: 'Section Break'
											},
											{
												label: __('Cancel'),
												fieldname: 'cancel',
												fieldtype: 'Button'
											}
										]
									});
					
									d.fields_dict.share_payment_link.$input.click(() => {
										d.hide();
										// me.make_approved_with_payment_link();
										me.make_sales_approved_with_payment_link(d.get_values());
									});
					
									d.fields_dict.without_payment_link.$input.click(() => {
										d.hide();
										me.make_sales_approved(d.get_values());
									});
					
									d.fields_dict.cancel.$input.click(() => {
										d.hide();
										// Do nothing on cancel
									});
					
									d.show();
								},
								() => {
									// User explicitly canceled the first dialog
									// Do nothing here
								}
							);
							// frappe.confirm(
							// 	__('Are you sure you want to approve? It will Reserve the Item.'),
							// 	() => {
							// 		// User confirmed, now ask if they want to share the payment link
							// 		frappe.confirm(
							// 			__('Do you want to share the payment link?'),
							// 			() => {
							// 				// User confirmed to share the payment link
							// 				// Call your new function here
							// 				me.make_sales_approved_with_payment_link();
							// 			},
							// 			() => {
							// 				// User canceled sharing the payment link
							// 				me.make_sales_approved(false); // Call the original function with false flag
							// 			}
							// 		);
							// 	},
							// 	() => {
							// 		// Do nothing on cancel
							// 	}
							// );
                            // frappe.confirm(
                            //     __('Are you sure you want to approve?'),
                            //     () => {
                            //         me.make_sales_approved(); // Call the JavaScript method
                            //     },
                            //     () => {
                            //         // Do nothing on cancel
                            //     }
                            // );
                        }, __('Action'));
                    }

					if (flt(doc.per_billed, 2) < 100 && doc.status === 'Order' && (doc.order_type === 'Sales')) {
						this.frm.add_custom_button(__('Create Sales Invoice & Delivery Note'), () => {
							frappe.confirm(
								__('Are you sure you want to Create Sales Invoice & Delivery Note?'),
								() => {
									// Check the payment status before proceeding
									// if (doc.payment_status === 'Paid') {
										me.make_sales_invoice_delivery_note(); // Call the JavaScript method
									// } else {
									// 	frappe.msgprint(__('Payment is not done. Please complete the payment before proceeding.'));
									// }
								},
								() => {
									// Do nothing on cancel
								}
							);
						}, __('Action'));
					}
					

                    // if (flt(doc.per_billed, 2) < 100 && doc.status === 'Approved' && doc.order_type === 'Rental') {
                    //     this.frm.add_custom_button(__('Rental Device Assigned'), () => {
                    //         frappe.confirm(
                    //             __('Are you sure you want to Assign the Rental Device?'),
                    //             () => {
                    //                 me.make_rental_device_assign(); // Call the JavaScript method
                    //             },
                    //             () => {
                    //                 // Do nothing on cancel
                    //             }
                    //         );
                    //     }, __('Create'));
                    // }

                    if (flt(doc.per_billed, 2) < 100 && doc.status === 'Approved' && doc.order_type === 'Rental') {
                        this.frm.add_custom_button(__('Ready for Delivery'), () => {
                            frappe.confirm(
                                __('Are you sure you want make the status as Ready For Delivery?'),
                                () => {
                                    me.make_ready_for_delivery(); // Call the JavaScript method
                                },
                                () => {
                                    // Do nothing on cancel
                                }
                            );
                        }, __('Action'));
                    }


                    if (flt(doc.per_billed, 2) < 100 && doc.status === 'Ready for Delivery' && doc.order_type === 'Rental') {
                        this.frm.add_custom_button(__('DISPATCHED'), () => {
                            frappe.confirm(
                                __('Are you sure you want make the status as DISPATCHED?'),
                                () => {
                                    me.make_dispatch(); // Call the JavaScript method
                                },
                                () => {
                                    // Do nothing on cancel
                                }
                            );
                        }, __('Action'));
                    }


                    if (flt(doc.per_billed, 2) < 100 && doc.status === 'DISPATCHED' && doc.order_type === 'Rental') {
                        this.frm.add_custom_button(__('DELIVERED'), () => {
                            frappe.confirm(
                                __('Are you sure you want make the status as DELIVERED?'),
                                () => {
                                    me.make_delivered(); // Call the JavaScript method
                                },
                                () => {
                                    // Do nothing on cancel
                                }
                            );
                        }, __('Action'));
                    }

                    if (doc.status === 'Active' && doc.order_type === 'Rental') {
                        this.frm.add_custom_button(__('Ready for Pickup'), () => {
                            frappe.confirm(
                                __('Are you sure you want make the status as Ready for Pickup?'),
                                () => {
                                    me.make_ready_for_pickup(); // Call the JavaScript method
                                },
                                () => {
                                    // Do nothing on cancel
                                }
                            );
                        }, __('Action'));
                    }
					if (doc.status === 'Ready for Pickup' && doc.order_type === 'Rental') {
                        this.frm.add_custom_button(__('Picked Up'), () => {
                            frappe.confirm(
                                __('Are you sure you want make the status as Ready for Pickup?'),
                                () => {
                                    me.make_pickedup(); // Call the JavaScript method
                                },
                                () => {
                                    // Do nothing on cancel
                                }
                            );
                        }, __('Action'));
                    }
					if (doc.status === 'Picked Up' && doc.order_type === 'Rental') {
                        this.frm.add_custom_button(__('Submitted To Office'), () => {
                            frappe.confirm(
                                __('Are you sure you want make the status as Submitted To Office?'),
                                () => {
                                    me.make_submitted_to_office(); // Call the JavaScript method
                                },
                                () => {
                                    // Do nothing on cancel
                                }
                            );
                        }, __('Action'));
                    }


					if ((doc.status === 'Submitted to Office' || doc.status === 'RENEWED' || doc.status === 'Order') && (doc.order_type === 'Rental' || doc.order_type === 'Service'  )) {
						this.frm.add_custom_button(__('Order Completed'), () => {
							frappe.confirm(
								__('Are you sure you want to make the status as Order Closed?'),
								() => {
									this.make_order_completed(); // Call the JavaScript method
								},
								() => {
									// Do nothing on cancel
								}
							);
						}, __('Action'));
					}
					// delivery note
					if (
						flt(doc.per_delivered, 2) < 100 &&
						(order_is_a_sale || order_is_a_custom_sale) &&
						allow_delivery && doc.status === 'Order' && doc.order_type === 'Service'
					) {
						this.frm.add_custom_button(
							__("Delivery Note"),
							() => this.make_delivery_note_based_on_delivery_date(true),
							__("Action")
						);
						// this.frm.add_custom_button(
						// 	__("Work Order"),
						// 	() => this.make_work_order(),
						// 	__("Action")
						// );
					}

					// sales invoice
					// if (flt(doc.per_billed, 2) < 100 && doc.status != 'RENEWED' && (doc.order_type === 'Service' || doc.order_type === 'Rental')) {
					// 	this.frm.add_custom_button(
					// 		__("Sales Invoice"),
					// 		() => me.make_sales_invoice(),
					// 		__("Action")
					// 	);
					// }
					 // Check the status of the sales order
					 if (this.frm.doc.status === "Rental SO Completed") {
						// Lock all fields by making them read-only
						Object.keys(this.frm.fields_dict).forEach(fieldname => {
							if (!this.frm.fields_dict[fieldname].df.hidden && 
								this.frm.fields_dict[fieldname].df.fieldtype !== 'Button') {
								this.frm.set_df_property(fieldname, 'read_only', 1);
							}
						});
				
						// Hide primary action button if it exists
						if (this.frm.page.btn_primary) {
							this.frm.page.btn_primary.hide();
						}
				
						// Clear the secondary button menu
						this.frm.page.clear_menu(); // This clears all secondary buttons
				
						// Hide specific buttons using their class names or data-labels
						const buttonsToHide = [
							'Generate Payment Link',
							'Action',
							'Make Payment',
							'Adjust Deposit',
							'Return Security Deposit',
							'Update Current SD',
							'Order Option'
						];
				
						buttonsToHide.forEach(label => {
							// Hide button by data-label attribute
							const button = document.querySelector(`[data-label="${encodeURIComponent(label)}"]`);
							if (button) {
								button.style.display = 'none'; // Hide the button
							}
						});
				
						// If you want to hide the dropdown items in the menu
						const dropdownItems = document.querySelectorAll('.dropdown-menu a.dropdown-item');
						dropdownItems.forEach(item => {
							const itemLabel = decodeURIComponent(item.getAttribute('data-label'));
							if (buttonsToHide.includes(itemLabel)) {
								item.style.display = 'none'; // Hide the dropdown item
							}
						});
					} else {
						// If the status is not "Rental SO Completed", unlock fields and show buttons if needed
						
				
						// Show primary action button again if needed
						this.frm.page.set_primary_action(__('Save'), () => {
							// Define what happens when the primary action is clicked
						});
				
						// Optionally re-add secondary buttons or custom buttons if needed
					}
					// material request
					// if (
					// 	!doc.order_type ||
					// 	((order_is_a_sale || order_is_a_custom_sale) && flt(doc.per_delivered, 2) < 100)
					// ) {
					// 	this.frm.add_custom_button(
					// 		__("Material Request"),
					// 		() => this.make_material_request(),
					// 		__("Action")
					// 	);
					// 	this.frm.add_custom_button(
					// 		__("Request for Raw Materials"),
					// 		() => this.make_raw_material_request(),
					// 		__("Action")
					// 	);
					// }

					// Make Purchase Order
					// if (!this.frm.doc.is_internal_customer) {
					// 	this.frm.add_custom_button(
					// 		__("Purchase Order"),
					// 		() => this.make_purchase_order(),
					// 		__("Action")
					// 	);
					// }

					// maintenance
					// if (flt(doc.per_delivered, 2) < 100 && (order_is_maintenance || order_is_a_custom_sale)) {
					// 	this.frm.add_custom_button(
					// 		__("Maintenance Visit"),
					// 		() => this.make_maintenance_visit(),
					// 		__("Action")
					// 	);
					// 	this.frm.add_custom_button(
					// 		__("Maintenance Schedule"),
					// 		() => this.make_maintenance_schedule(),
					// 		__("Action")
					// 	);
					// }

					// // project
					// if (flt(doc.per_delivered, 2) < 100) {
					// 	this.frm.add_custom_button(__("Project"), () => this.make_project(), __("Action"));
					// }

					// if (doc.docstatus === 1 && !doc.inter_company_order_reference) {
					// 	let me = this;
					// 	let internal = me.frm.doc.is_internal_customer;
					// 	if (internal) {
					// 		let button_label =
					// 			me.frm.doc.company === me.frm.doc.represents_company
					// 				? "Internal Purchase Order"
					// 				: "Inter Company Purchase Order";

					// 		me.frm.add_custom_button(
					// 			button_label,
					// 			function () {
					// 				me.make_inter_company_order();
					// 			},
					// 			__("Action")
					// 		);
					// 	}
					// }
				}
				// payment request
				// if (
				// 	flt(doc.per_billed, precision("per_billed", doc)) <
				// 	100 + frappe.boot.sysdefaults.over_billing_allowance && doc.status != 'RENEWED'
				// ) {
				// 	this.frm.add_custom_button(
				// 		__("Payment Request"),
				// 		() => this.make_payment_request(),
				// 		__("Action")
				// 	);
				// 	this.frm.add_custom_button(__("Payment"), () => this.make_payment_entry(), __("Action"));
				// }
				// this.frm.page.set_inner_btn_group_as_primary(__("Action"));
			}
		}

		if (this.frm.doc.docstatus === 0) {
			this.frm.add_custom_button(
				__("Quotation"),
				function () {
					let d = erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
						source_doctype: "Quotation",
						target: me.frm,
						setters: [
							{
								label: "Customer",
								fieldname: "party_name",
								fieldtype: "Link",
								options: "Customer",
								default: me.frm.doc.customer || undefined,
							},
						],
						get_query_filters: {
							company: me.frm.doc.company,
							docstatus: 1,
							status: ["!=", "Lost"],
						},
					});
				},
				__("Get Items From")
			);
		}

		this.order_type(doc);
	}

	create_pick_list() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.create_pick_list",
			frm: this.frm,
		});
	}

	make_work_order() {
		var me = this;
		me.frm.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.get_work_order_items",
			args: {
				sales_order: this.frm.docname,
			},
			freeze: true,
			callback: function (r) {
				if (!r.message) {
					frappe.msgprint({
						title: __("Work Order not created"),
						message: __("No Items with Bill of Materials to Manufacture"),
						indicator: "orange",
					});
					return;
				} else {
					const fields = [
						{
							label: "Items",
							fieldtype: "Table",
							fieldname: "items",
							description: __("Select BOM and Qty for Production"),
							fields: [
								{
									fieldtype: "Read Only",
									fieldname: "item_code",
									label: __("Item Code"),
									in_list_view: 1,
								},
								{
									fieldtype: "Link",
									fieldname: "bom",
									options: "BOM",
									reqd: 1,
									label: __("Select BOM"),
									in_list_view: 1,
									get_query: function (doc) {
										return { filters: { item: doc.item_code } };
									},
								},
								{
									fieldtype: "Float",
									fieldname: "pending_qty",
									reqd: 1,
									label: __("Qty"),
									in_list_view: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "sales_order_item",
									reqd: 1,
									label: __("Sales Order Item"),
									hidden: 1,
								},
							],
							data: r.message,
							get_data: () => {
								return r.message;
							},
						},
					];
					var d = new frappe.ui.Dialog({
						title: __("Select Items to Manufacture"),
						fields: fields,
						primary_action: function () {
							var data = { items: d.fields_dict.items.grid.get_selected_children() };
							me.frm.call({
								method: "make_work_orders",
								args: {
									items: data,
									company: me.frm.doc.company,
									sales_order: me.frm.docname,
									project: me.frm.project,
								},
								freeze: true,
								callback: function (r) {
									if (r.message) {
										frappe.msgprint({
											message: __("Work Orders Created: {0}", [
												r.message
													.map(function (d) {
														return repl(
															'<a href="/app/work-order/%(name)s">%(name)s</a>',
															{ name: d }
														);
													})
													.join(", "),
											]),
											indicator: "green",
										});
									}
									d.hide();
								},
							});
						},
						primary_action_label: __("Create"),
					});
					d.show();
				}
			},
		});
	}

	order_type() {
		this.toggle_delivery_date();
	}

	tc_name() {
		this.get_terms();
	}

	make_material_request() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
			frm: this.frm,
		});
	}

	skip_delivery_note() {
		this.toggle_delivery_date();
	}

	toggle_delivery_date() {
		this.frm.fields_dict.items.grid.toggle_reqd(
			"delivery_date",
			this.frm.doc.order_type == "Sales" && !this.frm.doc.skip_delivery_note
		);
	}

	make_raw_material_request() {
		var me = this;
		this.frm.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.get_work_order_items",
			args: {
				sales_order: this.frm.docname,
				for_raw_material_request: 1,
			},
			callback: function (r) {
				if (!r.message) {
					frappe.msgprint({
						message: __("No Items with Bill of Materials."),
						indicator: "orange",
					});
					return;
				} else {
					me.make_raw_material_request_dialog(r);
				}
			},
		});
	}

	make_raw_material_request_dialog(r) {
		var me = this;
		var fields = [
			{ fieldtype: "Check", fieldname: "include_exploded_items", label: __("Include Exploded Items") },
			{
				fieldtype: "Check",
				fieldname: "ignore_existing_ordered_qty",
				label: __("Ignore Existing Ordered Qty"),
			},
			{
				fieldtype: "Table",
				fieldname: "items",
				description: __("Select BOM, Qty and For Warehouse"),
				fields: [
					{
						fieldtype: "Read Only",
						fieldname: "item_code",
						label: __("Item Code"),
						in_list_view: 1,
					},
					{
						fieldtype: "Link",
						fieldname: "warehouse",
						options: "Warehouse",
						label: __("For Warehouse"),
						in_list_view: 1,
					},
					{
						fieldtype: "Link",
						fieldname: "bom",
						options: "BOM",
						reqd: 1,
						label: __("BOM"),
						in_list_view: 1,
						get_query: function (doc) {
							return { filters: { item: doc.item_code } };
						},
					},
					{
						fieldtype: "Float",
						fieldname: "required_qty",
						reqd: 1,
						label: __("Qty"),
						in_list_view: 1,
					},
				],
				data: r.message,
				get_data: function () {
					return r.message;
				},
			},
		];
		var d = new frappe.ui.Dialog({
			title: __("Items for Raw Material Request"),
			fields: fields,
			primary_action: function () {
				var data = d.get_values();
				me.frm.call({
					method: "erpnext.selling.doctype.sales_order.sales_order.make_raw_material_request",
					args: {
						items: data,
						company: me.frm.doc.company,
						sales_order: me.frm.docname,
						project: me.frm.project,
					},
					freeze: true,
					callback: function (r) {
						if (r.message) {
							frappe.msgprint(
								__("Material Request {0} submitted.", [
									'<a href="/app/material-request/' +
										r.message.name +
										'">' +
										r.message.name +
										"</a>",
								])
							);
						}
						d.hide();
						me.frm.reload_doc();
					},
				});
			},
			primary_action_label: __("Create"),
		});
		d.show();
	}

	make_delivery_note_based_on_delivery_date(for_reserved_stock = false) {
		var me = this;

		var delivery_dates = this.frm.doc.items.map((i) => i.delivery_date);
		delivery_dates = [...new Set(delivery_dates)];

		var today = new Date();

		var item_grid = this.frm.fields_dict["items"].grid;
		if (!item_grid.get_selected().length && delivery_dates.length > 1) {
			var dialog = new frappe.ui.Dialog({
				title: __("Select Items based on Delivery Date"),
				fields: [{ fieldtype: "HTML", fieldname: "dates_html" }],
			});

			var html = $(`
				<div style="border: 1px solid #d1d8dd">
					<div class="list-item list-item--head">
						<div class="list-item__content list-item__content--flex-2">
							${__("Delivery Date")}
						</div>
					</div>
					${delivery_dates
						.map(
							(date) => `
						<div class="list-item">
							<div class="list-item__content list-item__content--flex-2">
								<label>
								<input
									type="checkbox"
									data-date="${date}"
									${frappe.datetime.get_day_diff(new Date(date), today) > 0 ? "" : 'checked="checked"'}
								/>
								${frappe.datetime.str_to_user(date)}
								</label>
							</div>
						</div>
					`
						)
						.join("")}
				</div>
			`);

			var wrapper = dialog.fields_dict.dates_html.$wrapper;
			wrapper.html(html);

			dialog.set_primary_action(__("Select"), function () {
				var dates = wrapper
					.find("input[type=checkbox]:checked")
					.map((i, el) => $(el).attr("data-date"))
					.toArray();

				if (!dates) return;

				me.make_delivery_note(dates, for_reserved_stock);
				dialog.hide();
			});
			dialog.show();
		} else {
			this.make_delivery_note([], for_reserved_stock);
		}
	}

	make_delivery_note(delivery_dates, for_reserved_stock = false) {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
			frm: this.frm,
			args: {
				delivery_dates,
				for_reserved_stock: for_reserved_stock,
			},
			freeze: true,
			freeze_message: __("Creating Delivery Note ..."),
		});
	}

	make_sales_invoice() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			frm: this.frm,
		});
	}
	// make_approved_with_payment_link() {
	// 	// Check if custom_razorpay_payment_url is present in the form data
	// 	const paymentUrl = this.frm.doc.custom_razorpay_payment_url;
	// 	if (!paymentUrl) {
	// 		// If custom_razorpay_payment_url is not set, show an error message
	// 		frappe.throw({
	// 			title: __('Error'),
	// 			message: __('Please generate the payment link first.'),
	// 			indicator: 'red'
	// 		});
	// 		return;
	// 	}
	
	// 	// Prompt to show the payment link and get customer_email_id
	// 	frappe.prompt([
	// 		{
	// 			label: __('Payment Link'),
	// 			fieldname: 'show_payment_link',
	// 			fieldtype: 'Data',
	// 			reqd: 1,
	// 			read_only: 1,
	// 			default: paymentUrl
	// 		},
	// 		{
	// 			label: __('Customer Email ID:'),
	// 			fieldname: 'customer_email_id',
	// 			fieldtype: 'Data',
	// 			reqd: 1,
	// 			default: this.frm.doc.customer_email_id || ''
	// 		}
	// 	], (values) => {
	// 		// Values will contain the user's input from the prompt
	// 		if (values.show_payment_link) {
	// 			// console.log('Showing payment link:', paymentUrl);
				
	// 			// Call make_approved and send email on success
	// 			this.make_approved(() => {
	// 				// Send approval email
	// 				this.send_approval_email(this.frm.doc.name, values.customer_email_id, values.show_payment_link);
	// 			});
	// 		} else {
	// 			console.log('User declined to show the payment link.');
	// 		}
	// 	}, __('Payment Link Confirmation'));
	// }

	make_approved_with_payment_link(values) {
		// Check if custom_razorpay_payment_url is present in the form data
		const paymentUrl = this.frm.doc.custom_razorpay_payment_url;
		if (!paymentUrl) {
			// If custom_razorpay_payment_url is not set, show an error message
			frappe.throw({
				title: __('Error'),
				message: __('Please generate the payment link first.'),
				indicator: 'red'
			});
			return;
		}
	
		// Prompt to show the payment link and get customer_email_id
		frappe.prompt([
			{
				label: __('Payment Link'),
				fieldname: 'show_payment_link',
				fieldtype: 'Data',
				reqd: 1,
				read_only: 1,
				default: paymentUrl
			},
			{
				label: __('Customer Email ID:'),
				fieldname: 'customer_email_id',
				fieldtype: 'Data',
				reqd: 1,
				default: this.frm.doc.customer_email_id || ''
			}
		], (promptValues) => {
			// Values will contain the user's input from the prompt
			if (promptValues.show_payment_link) {
				// Call make_approved and send email on success
				this.make_approved(values, () => {
					// Send approval email
					this.send_approval_email(this.frm.doc.name, promptValues.customer_email_id, promptValues.show_payment_link);
					
				});
			} else {
				console.log('User declined to show the payment link.');
			}
		}, __('Payment Link Confirmation'));
	}
	
	
	
	
	make_approved(values, callback) {
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.make_approved',
			args: {
				docname: this.frm.doc.name,
			},
			callback: (response) => {
				if (response.message === true) {
					console.log(response.message);
	
					frappe.msgprint({
						title: __('Success'),
						message: __('Rental Sales Order Approved successfully.'),
						indicator: 'green'
					});
					if (values.notify_through_whatsapp) {
						// Validate mobile number
						const mobile_no = values.mobile_no.replace(/\D/g, '');

						if (mobile_no.length !== 10) {
							frappe.msgprint({
								title: __('Invalid Mobile Number'),
								message: __('Please enter a valid 10-digit mobile number.'),
								indicator: 'red'
							});
							return;  // Stop execution if mobile number is invalid
						}
						this.send_whatsapp_message(values.mobile_no, values.message);
					}
					// Reload the page after a short delay
					setTimeout(() => {
						window.location.reload();
					}, 1000);
	
					// Call the callback function if approval is successful
					if (callback) callback();
				} else {
					console.error('Unexpected response:', response);
					frappe.msgprint({
						title: __('Error'),
						message: __('Failed to approve Rental Sales Order.'),
						indicator: 'red'
					});
				}
			}
		});
	}
	

	make_sales_approved(values, callback) {
        frappe.call({
            method: 'erpnext.selling.doctype.sales_order.sales_order.make_sales_approved',
            args: {
                docname: this.frm.doc.name,
            },
            callback: (response) => {
                // Handle the response
                if (response.message) {
                    // Log the result to the console
                    console.log(response.message);
    
                    // Display a success message
                    frappe.msgprint({
                        title: __('Success'),
                        message: __('Sales Order Approved successfully.'),
                        indicator: 'green'
                    });
					if (values.notify_through_whatsapp) {
						// Validate mobile number
						const mobile_no = values.mobile_no.replace(/\D/g, '');

						if (mobile_no.length !== 10) {
							frappe.msgprint({
								title: __('Invalid Mobile Number'),
								message: __('Please enter a valid 10-digit mobile number.'),
								indicator: 'red'
							});
							return;  // Stop execution if mobile number is invalid
						}
						this.send_whatsapp_message(values.mobile_no, values.message);
					}
                    // Reload the entire page after a short delay (adjust as needed)
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000); // 1000 milliseconds = 1 second
					if (callback) callback();
                } else {
                    // Handle the case where the response does not contain a message
                    console.error('Unexpected response:', response);
                }
            }
        });
    }


	make_sales_approved_with_payment_link(values) {
		// Check if custom_razorpay_payment_url is present in the form data
		const paymentUrl = this.frm.doc.custom_razorpay_payment_url;
		if (!paymentUrl) {
			// If custom_razorpay_payment_url is not set, show an error message
			frappe.throw({
				title: __('Error'),
				message: __('Please generate the payment link first.'),
				indicator: 'red'
			});
			return;
		}
	
		// Prompt to show the payment link and get customer_email_id
		frappe.prompt([
			{
				label: __('Payment Link'),
				fieldname: 'show_payment_link',
				fieldtype: 'Data',
				reqd: 1,
				read_only: 1,
				default: paymentUrl
			},
			{
				label: __('Customer Email ID:'),
				fieldname: 'customer_email_id',
				fieldtype: 'Data',
				reqd: 1,
				default: this.frm.doc.customer_email_id || ''
			}
		], (promptValues) => {
			// Values will contain the user's input from the prompt
			if (promptValues.show_payment_link) {
				console.log('Showing payment link:', paymentUrl);
	
				// Call make_approved and send email on success
				this.make_sales_approved(values,() => {
					// Send approval email
					this.send_approval_email(this.frm.doc.name, promptValues.customer_email_id, promptValues.show_payment_link);
				});
			} else {
				console.log('User declined to show the payment link.');
			}
		}, __('Payment Link Confirmation'));
	}



	send_approval_email(docname, customerEmailId, payment_link) {
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.send_approval_email',
			args: {
				docname: docname,
				customer_email_id: customerEmailId,
				payment_link: payment_link
			},
			callback: (response) => {
				if (response.message === true) {
					console.log('Approval email sent successfully.');
				} else {
					console.error('Failed to send approval email:', response);
					frappe.msgprint({
						title: __('Error'),
						message: __('Failed to send approval email.'),
						indicator: 'red'
					});
				}
			}
		});
	}
	
	
	send_whatsapp_message(mobile_no, message) {
		frappe.call({
			method: 'webtoolex_whatsapp.webtoolex_whatsapp.doctype.whatsapp_instance.whatsapp_instance.send_custom_whatsapp_message',
			args: {
				mobile_number: mobile_no,
				message: message,
				// instance_name: 'NHK' // Specify your WhatsApp instance name here
			},
			callback: (response) => {
				if (response.message && response.message.status === true) {
					frappe.msgprint({
						title: __('WhatsApp'),
						message: __('WhatsApp message sent successfully.'),
						indicator: 'green'
					});
				} else {
					frappe.msgprint({
						title: __('WhatsApp'),
						message: response.message ? response.message.msg : __('Failed to send WhatsApp message.'),
						indicator: 'red'
					});
				}
			}
		});
	}
	
	
	


	


	close_rental_sales_order() {
        frappe.call({
            method: 'erpnext.selling.doctype.sales_order.sales_order.close_rental_order',
            args: {
                docname: this.frm.doc.name,
            },
            callback: function (response) {
				// Handle the response
				if (response.message) {
					// Display an alert directly in the Frappe UI
					frappe.show_alert({
						message: __('Document Close successfully.'),
						indicator: 'green'
					});

					// Reload the entire page after a short delay (adjust as needed)
					setTimeout(() => {
						window.location.reload();
					}, 1000); // 1000 milliseconds = 1 second
				} else {
					// Handle the case where the response does not contain a message
					console.error('Unexpected response:', response);
				}
			}
        });
    }

    hold_rental_sales_order() {
		var me = this;
	
		var d = new frappe.ui.Dialog({
			title: __('Reason for Hold'),
			fields: [
				{
					"fieldname": "reason_for_hold",
					"fieldtype": "Text",
					"reqd": 1,
				}
			],
			primary_action: function () {
				var data = d.get_values();
				frappe.call({
					method: "frappe.desk.form.utils.add_comment",
					args: {
						reference_doctype: me.frm.doctype,
						reference_name: me.frm.docname,
						content: __('Reason for hold:') + ' ' + data.reason_for_hold,
						comment_email: frappe.session.user,
						comment_by: frappe.session.user_fullname
					},
					callback: function (r) {
						if (!r.exc) {
							// Comment added successfully, now proceed with holding the document
							// me.update_status('Hold', 'On Hold');
	
							// Hide the dialog
							d.hide();
	
							// Call the on_hold method
							frappe.call({
								method: 'erpnext.selling.doctype.sales_order.sales_order.on_hold',
								args: {
									docname: me.frm.doc.name,
								},
								callback: function (response) {
									// Handle the response
									if (response.message) {
										// Display an alert directly in the Frappe UI
										frappe.show_alert({
											message: __('Document Hold successfully.'),
											indicator: 'green'
										});
	
										// Reload the entire page after a short delay (adjust as needed)
										setTimeout(() => {
											window.location.reload();
										}, 1000); // 1000 milliseconds = 1 second
									} else {
										// Handle the case where the response does not contain a message
										console.error('Unexpected response:', response);
									}
								}
							});
						}
					}
				});
			}
		});
	
		d.show();
	}
	
    

	make_rental_device_assign() {
		const itemGroups = cur_frm.doc.items.map(item => item.item_group).filter(Boolean).filter((value, index, self) => self.indexOf(value) === index);
	
		frappe.prompt([
			{
				label: 'Item Group',
				fieldname: 'item_group',
				fieldtype: 'Link',
				options: 'Item Group',
				reqd: 1,
				read_only: 1,
				default: cur_frm.doc.items[0].item_group,  // Set a default value based on the first item's group (adjust as needed)
				get_query: function () {
					return {
						filters: {
							'name': ['in', itemGroups]
						}
					};
				}
			},
			{
				label: 'Item Code',
				fieldname: 'item_code1',
				fieldtype: 'Link',
				options: 'Item',
				reqd: 1,
				get_query: function (doc, cdt, cdn) {
					const selectedGroup = cur_dialog.fields_dict.item_group.get_value();
					return {
						filters: {
							'item_group': selectedGroup,
							'status': 'Available'  // Replace 'availability_status' with the actual field name for item availability
						}
					};
				}
			},
			// Add more fields as neededmake_submitted_to_office
		], (values) => {
			// values will contain the entered data
			// console.log(values);
	
			// Update Sales Order with the entered values
			this.frm.doc.item_group = values.item_group;
			this.frm.doc.item_code1 = values.item_code1;
	
			// Optionally, refresh the form to reflect the changes
			this.frm.refresh();
	
			// Now call the server-side method only after the user submits the device details
			this.callServerMethod(values);
		}, __('Rental Device Details'));
	}
	
	

	
    
    callServerMethod(values) {
        frappe.call({
            method: 'erpnext.selling.doctype.sales_order.sales_order.make_rental_device_assign',
            args: {
                docname: this.frm.doc.name,
                item_group: values.item_group,
                item_code1: values.item_code1
            },
            callback: (response) => {
                // Handle the response from the server
                if (response.message) {
                    // Display a success message
                    frappe.msgprint({
                        title: __('Success'),
                        message: __('Rental Device Assigned successfully.'),
                        indicator: 'green'
                    });
                    // this.frm.save();
                    // Reload the entire page after a short delay (adjust as needed)
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000); 
                }
            }
        });
    }



    make_ready_for_delivery() {
		const me = this; // Preserve reference to 'this' object
		// var role_profile = [
		// 	{ role_profile: "NHK Technician" }, // Example data, replace with actual data
		// 	{ role_profile: "Other Role" }
		// ];
		frappe.prompt([
			{
				fieldname: 'technician_name',
				fieldtype: 'Link',
				options: 'Technician Details',
				label: 'Technician Id',
				reqd: 1,
				// get_query: function() {
				// 	// Fetch NHK Technicians based on their role profile
				// 	var role_profiles = [];
		
				// 	// Iterate over the role profiles and extract the role_profile value for NHK Technicians
				// 	for (var i = 0; i < role_profile.length; i++) {
				// 		if (role_profile[i].role_profile === 'NHK Technician') {
				// 			role_profiles.push(role_profile[i].role_profile);
				// 		}
				// 	}
		
				// 	// Return filters to load NHK Users who are NHK Technicians
				// 	return {
				// 		filters: {
				// 			'role_profile': ['in', role_profiles]
				// 		}
				// 	};
				// },
				onchange: function() {
					// Function to dynamically update technician mobile based on selected technician
					var technicianName = this.value;
					if (technicianName) {
						frappe.call({
							method: 'frappe.client.get_value',
							args: {
								doctype: 'Technician Details',
								filters: { 'name': technicianName },
								fieldname: ['mobile_number','name','name1']
							},
							callback: function(response) {
								// console.log(response)
								if (response.message && response.message.mobile_number && response.message.name) {
									// Set the value of technician mobile
									cur_dialog.fields_dict.technician_mobile.set_input(response.message.mobile_number);
									cur_dialog.fields_dict.technician_id.set_input(response.message.name);
									cur_dialog.fields_dict.technician_name1.set_input(response.message.name1);
								}
							}
						});
					}
				}
			},
			{
				fieldname: 'technician_name1',
				fieldtype: 'Data',
				label: 'Technician Name',
				reqd: 1
			},
			{
				fieldname: 'technician_mobile',
				fieldtype: 'Data',
				label: 'Technician Mobile Number',
				reqd: 1
			},
			
			{
				fieldname: 'technician_id',
				fieldtype: 'Data',
				label: 'Technician Id',
				hidden:1,
				// reqd: 1
			}

		], function(values) {
			var technicianName = values.technician_name;
			var technicianid = values.technician_name;
			var technicianMobile = values.technician_mobile;
	
			// Call the Python function passing the technician details
			frappe.call({
				method: 'erpnext.selling.doctype.sales_order.sales_order.make_ready_for_delivery', // Change to your actual module, doctype, and file name
				args: {
					docname: me.frm.doc.name, // Use me.frm.doc.name instead of this.frm.doc.name
					technician_name: technicianName,
					technician_mobile: technicianMobile,
					technician_id: technicianid,

				},
				callback: function(response) {
					// Handle the response
					if (response.message) {
						// Log the result to the console
						console.log(response.message);
		
						// Display a success message
						frappe.msgprint({
							title: __('Success'),
							message: __('Device is Ready For Delivery.'),
							indicator: 'green'
						});
						// Reload the entire page after a short delay (adjust as needed)
						setTimeout(() => {
							window.location.reload();
						}, 1000); // 1000 milliseconds = 1 second
					} else {
						// Handle the case where the response does not contain a message
						console.error('Unexpected response:', response);
					}
				}
			});
		}, 'Technician Details', 'Submit');
	}


	
	make_sales_invoice_delivery_note() {
		const me = this; // Preserve reference to 'this' object
	
		// Call the Python function to create Sales Invoice and Delivery Note
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.create_sales_invoice_and_delivery_note',
			args: {
				docname: me.frm.doc.name, // Use me.frm.doc.name instead of this.frm.doc.name
			},
			callback: function(response) {
				// Handle the response
				if (response.message) {
					if (typeof response.message === 'string') {
						// Handle string message
						frappe.msgprint({
							title: __('Message'),
							message: response.message,
							indicator: 'orange'
						});
					} else if (response.message.sales_invoice && response.message.delivery_note) {
						const delivery_note_name = response.message.delivery_note;
	
						// Confirm if the user wants to select serial numbers
						// frappe.confirm(
						// 	__('Do you want to select serial numbers for the items in the Delivery Note?'),
						// 	function() {
								// If the user confirms, redirect to the Delivery Note
								frappe.set_route("Form", "Delivery Note", delivery_note_name);
							// },
							// function() {
							// 	// If the user declines, refresh and submit the Delivery Note automatically
							// 	frappe.call({
							// 		method: 'frappe.client.get',
							// 		args: {
							// 			doctype: 'Delivery Note',
							// 			name: delivery_note_name
							// 		},
							// 		callback: function(r) {
							// 			if (r.message) {
							// 				frappe.call({
							// 					method: 'erpnext.selling.doctype.sales_order.sales_order.submit_delivery_note',
							// 					args: {
							// 						docname: delivery_note_name
							// 					},
							// 					callback: function(r) {
							// 						if (!r.exc) {
							// 							frappe.msgprint({
							// 								title: __('Success'),
							// 								message: __('Delivery Note has been submitted successfully.'),
							// 								indicator: 'green'
							// 							});
	
							// 							// Fetch and update serial numbers in Sales Order
							// 							update_sales_order_serial_numbers(me.frm.doc.name, delivery_note_name);
	
							// 						} else {
							// 							frappe.msgprint({
							// 								title: __('Error'),
							// 								message: __('Failed to submit the Delivery Note.'),
							// 								indicator: 'red'
							// 							});
							// 						}
							// 					}
							// 				});
							// 			} else {
							// 				frappe.msgprint({
							// 					title: __('Error'),
							// 					message: __('Failed to refresh the Delivery Note.'),
							// 					indicator: 'red'
							// 				});
							// 			}
							// 		}
							// 	});
							// }
						// );
					} else {
						// Handle other object structures or errors
						frappe.msgprint({
							title: __('Error'),
							message: __('Sales Invoice and Delivery Note is Already Created. Check in Connection'),
							indicator: 'red'
						});
					}
				} else {
					console.error('Unexpected response:', response);
					frappe.msgprint({
						title: __('Error'),
						message: __('Failed to create Sales Invoice and Delivery Note.'),
						indicator: 'red'
					});
				}
			}
		});
	}
	
	
	
	
	
	
    
    

	make_dispatch() {
		frappe.prompt([
			{
				label: 'Dispatch Date',
				fieldname: 'dispatch_date',
				fieldtype: 'Date',
				default:'Today',
				reqd: 1
			}
		], (values) => {
			// values will contain the entered data
			// console.log(values);

			// Update RentalSales Order with the entered values
			this.frm.doc.dispatch_date = values.dispatch_date;

			// Save the document before calling the server-side method
			// this.frm.save(() => {
				// Optionally, refresh the form to reflect the changes
				this.frm.refresh();

				// Now call the server-side method only after the user submits the dispatch date
				this.callServerMethodForDispatch(values);
			// });
		}, __('DISPATCHED'));
	}
	callServerMethodForDispatch(values) {
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.make_dispatch',
			args: {
				docname: this.frm.doc.name,
				dispatch_date: values.dispatch_date  // Pass dispatch_date to the server
			},
			callback: (response) => {
				// Handle the response from the server
				if (response.message) {
					// Display a success message
					frappe.msgprint({
						title: __('Success'),
						message: __('Rental Device dispatch successfully.'),
						indicator: 'green'
					});

					// Reload the entire page after a short delay (adjust as needed)
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			}
		});
	}


		

	make_delivered() {
		let frm = this.frm;
		frappe.prompt([
			{
				fieldtype: 'Section Break'
			},
			{
				label: __('Notify through whatsapp'),
				fieldname: 'notify_through_whatsapp',
				fieldtype: 'Check',
				default: 1
			},
			{
				label: __('Mobile No.'),
				fieldname: 'mobile_no',
				fieldtype: 'Data',
				default: frm.doc.customer_mobile_no,
				depends_on: 'eval:doc.notify_through_whatsapp',
				reqd: 1,  // Make field required
				description: __('Only 10 digits are allowed.Make sure Number Must be in WhatsApp'),
				on_change: (value) => {
					// Remove any non-numeric characters
					const numericValue = value.replace(/\D/g, '');
			
					// Check if the value has exactly 10 digits
					if (numericValue.length !== 10) {
						frappe.msgprint({
							title: __('Invalid Mobile Number'),
							message: __('Please enter a valid 10-digit mobile number. Only numbers are allowed.'),
							indicator: 'red'
						});
			
						// Optionally, clear the field or reset the value to numeric characters only
					}
				}
			},
			
			{
				label: __('Message'),
				fieldname: 'message',
				fieldtype: 'Small Text',
				default: `Hello ${frm.doc.customer_name},
Your order has been delivered successfully. We have received your payment of ${ (frm.doc.paid_security_deposit_amount || 0) + (frm.doc.received_amount || 0) } rs successfully.` + 
((frm.doc.outstanding_security_deposit_amount || 0) + (frm.doc.balance_amount || 0) > 0 ? 
` You have an outstanding amount of ${ (frm.doc.outstanding_security_deposit_amount || 0) + (frm.doc.balance_amount || 0) } rs.` : ``) + 
			`                                                                                              
For any query call/WhatsApp on 8884880013.`,
				depends_on: 'eval:doc.notify_through_whatsapp'
			},
			
			{
				fieldtype: 'Section Break'
			},
			{
				label: 'Delivered Date',
				fieldname: 'delivered_date',
				fieldtype: 'Datetime',
				default: 'Now',
				reqd: 1
			},
			{
				fieldtype: 'Section Break'
			},
			{
				label: 'Payment Status',
				fieldname: 'payment_status',
				fieldtype: 'Data',
				default: frm.doc.payment_status,
				read_only: 1
			},
			{
				label: 'Balance Amount',
				fieldname: 'balance_amount',
				fieldtype: 'Currency',
				default: frm.doc.balance_amount,
				read_only: 1
			},
			{
				label: 'Payment Received Amount',
				fieldname: 'received_amount',
				fieldtype: 'Currency',
				default: frm.doc.received_amount,
				read_only: 1
			},
			
			{
				fieldtype: 'Column Break'
			},
			{
				label: 'Security Deposit Payment Status',
				fieldname: 'security_deposit_payment_status',
				fieldtype: 'Data',
				default: frm.doc.security_deposit_status,
				read_only: 1
			},
			{
				label: 'Payment Outstanding Security Deposit Amount',
				fieldname: 'outstanding_security_deposit_amount',
				fieldtype: 'Currency',
				default: frm.doc.outstanding_security_deposit_amount,
				read_only: 1
			},
			{
				label: 'Received Security Deposit Amount',
				fieldname: 'paid_security_deposite_amount',
				fieldtype: 'Currency',
				default: frm.doc.paid_security_deposite_amount,
				read_only: 1
			},
			{
				fieldtype: 'Section Break'
			},
			{
				label: 'Payment Pending Reason',
				fieldname: 'payment_pending_reason',
				fieldtype: 'Link',
				options: 'Payment Pending Reason',
				depends_on: 'eval: (doc.payment_status == "UnPaid" || doc.payment_status == "Partially Paid") || (doc.security_deposit_payment_status == "Unpaid" || doc.security_deposit_payment_status == "Partially Paid")',
				mandatory_depends_on: 'eval: (doc.payment_status == "UnPaid" || doc.payment_status == "Partially Paid") || (doc.security_deposit_payment_status == "Unpaid" || doc.security_deposit_payment_status == "Partially Paid")'
			},
			{
				label: 'Notes',
				fieldname: 'notes',
				fieldtype: 'Small Text',
				depends_on: 'eval: (doc.payment_status == "UnPaid" || doc.payment_status == "Partially Paid") || (doc.security_deposit_payment_status == "Unpaid" || doc.security_deposit_payment_status == "Partially Paid")',
				// mandatory_depends_on: 'eval:doc.mode_of_payment == "Bank Draft" || doc.mode_of_payment == "Cheque"'
			},
			{
				label: 'Rental Order Agreement Attachment',
				fieldname: 'rental_order_agreement_attachment',
				fieldtype: 'Attach',
				// reqd: 1
			},
			{
				label: 'Aadhar Card Attachment',
				fieldname: 'aadhar_card_attachment',
				fieldtype: 'Attach',
				// reqd: 1
			}
		], (values) => {
			// values will contain the entered data
			// console.log(values);

			// Update RentalSales Order with the entered values
			this.frm.doc.delivered_date = values.delivered_date;
			this.frm.doc.payment_pending_reason = values.payment_pending_reason;
			this.frm.doc.notes = values.notes;
			

			// Save the document before calling the server-side method
			// this.frm.save(() => {
				// Optionally, refresh the form to reflect the changes
				this.frm.refresh();

				// Now call the server-side method only after the user submits the dispatch date
				this.callServerMethodForDelivered(values);
			// });
		}, __('DELIVERED'));
	}

	callServerMethodForDelivered(values) {
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.make_delivered',
			args: {
				// item_code1: this.frm.doc.item_code1,
				docname: this.frm.doc.name,
				customer_name: this.frm.doc.customer,
				delivered_date: values.delivered_date , // Pass dispatch_date to the server
				payment_pending_reasons: values.payment_pending_reason,
				rental_order_agreement_attachment: values.rental_order_agreement_attachment,
            	aadhar_card_attachment: values.aadhar_card_attachment,
				notes: values.notes,
				
			},
			callback: (response) => {
				// Handle the response from the server
				if (response.message) {
					// Display a success message
					frappe.msgprint({
						title: __('Success'),
						message: __('Rental Device Delivered successfully.'),
						indicator: 'green'
					});
					if (values.notify_through_whatsapp) {
						// Validate mobile number
						const mobile_no = values.mobile_no.replace(/\D/g, '');

						if (mobile_no.length !== 10) {
							frappe.msgprint({
								title: __('Invalid Mobile Number'),
								message: __('Please enter a valid 10-digit mobile number.'),
								indicator: 'red'
							});
							return;  // Stop execution if mobile number is invalid
						}
						this.send_whatsapp_message(values.mobile_no, values.message);
					}
					// Reload the entire page after a short delay (adjust as needed)
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			}
		});
	}
	make_ready_for_pickup() {
		let frm = this.frm;
		var role_profile = [
			{ role_profile: "NHK Technician" }, // Example data, replace with actual data
			{ role_profile: "Other Role" }
		];
		frappe.prompt([
			{
				fieldname: 'technician_name',
				fieldtype: 'Link',
				options: 'Technician Details',
				label: 'Technician ID',
				reqd: 1,
				// get_query: function() {
				// 	// Fetch NHK Technicians based on their role profile
				// 	var role_profiles = [];
		
				// 	// Iterate over the role profiles and extract the role_profile value for NHK Technicians
				// 	for (var i = 0; i < role_profile.length; i++) {
				// 		if (role_profile[i].role_profile === 'NHK Technician') {
				// 			role_profiles.push(role_profile[i].role_profile);
				// 		}
				// 	}
		
				// 	// Return filters to load NHK Users who are NHK Technicians
				// 	return {
				// 		filters: {
				// 			'role_profile': ['in', role_profiles]
				// 		}
				// 	};
				// },
				onchange: function() {
					// Function to dynamically update technician mobile based on selected technician
					var technicianName = this.value;
					if (technicianName) {
						frappe.call({
							method: 'frappe.client.get_value',
							args: {
								doctype: 'Technician Details',
								filters: { 'name': technicianName },
								fieldname: ['mobile_number','name','name1']
							},
							callback: function(response) {
								// console.log(response)
								if (response.message && response.message.mobile_number && response.message.name) {
									// Set the value of technician mobile
									cur_dialog.fields_dict.technician_mobile.set_input(response.message.mobile_number);
									cur_dialog.fields_dict.technician_id.set_input(response.message.name);
									cur_dialog.fields_dict.technician_name1.set_input(response.message.name1);
								}
							}
						});
					}
				}
			},
			{
				fieldname: 'technician_name1',
				fieldtype: 'Data',
				label: 'Technician Name',
				reqd: 1
			},
			{
				fieldname: 'technician_mobile',
				fieldtype: 'Data',
				label: 'Technician Mobile Number',
				reqd: 1
			},
			{
				fieldname: 'technician_id',
				fieldtype: 'Data',
				label: 'Technician Id',
				hidden:1,
				// reqd: 1
			},
			{
				label: __('Notify through whatsapp'),
				fieldname: 'notify_through_whatsapp',
				fieldtype: 'Check',
				default: 1
			},
			{
				label: __('Mobile No.'),
				fieldname: 'mobile_no',
				fieldtype: 'Data',
				default: frm.doc.customer_mobile_no,
				depends_on: 'eval:doc.notify_through_whatsapp',
				reqd: 1,  // Make field required
				description: __('Only 10 digits are allowed.Make sure Number Must be in WhatsApp'),
				on_change: (value) => {
					// Remove any non-numeric characters
					const numericValue = value.replace(/\D/g, '');
			
					// Check if the value has exactly 10 digits
					if (numericValue.length !== 10) {
						frappe.msgprint({
							title: __('Invalid Mobile Number'),
							message: __('Please enter a valid 10-digit mobile number. Only numbers are allowed.'),
							indicator: 'red'
						});
			
						// Optionally, clear the field or reset the value to numeric characters only
					} 
				}
			},
			
			{
				label: __('Message'),
				fieldname: 'message',
				fieldtype: 'Small Text',
				default: `Hello Sir/Mam
			
Patient Name: ${frm.doc.customer_name}
Equipment Name: ${frm.doc.items ? frm.doc.items.map(item => item.item_name).join(', ') : 'No items'}
			
We have initiated pickup of the above equipment.
For any query call/WhatsApp on 8884880013.`,
				depends_on: 'eval:doc.notify_through_whatsapp'
			},
			
			{
				label: 'Pickup Date',
				fieldname: 'pickup_date',
				fieldtype: 'Datetime',
				default:'Now',
				reqd: 1
			},
			{
				fieldname: 'pickup_reason',
				fieldtype: 'Select',
				label: 'Pick Up Reason',
				options: 'Patient recovered\nPatient Expired\nPurchased Device from Us\nPurchased Device from Others\nItem Replacement\nOther Reason',
				reqd: 1
			},
			{
				fieldname: 'pickup_remark',
				fieldtype: 'Small Text',
				label: 'Pick Up Remark',
				reqd: 1
			}
		], (values) => {
			// Update RentalSales Order with the entered values
			this.frm.doc.technician_name = values.technician_name;
			this.frm.doc.technician_mobile = values.technician_mobile;
			this.frm.doc.technician_id = values.technician_id;
			this.frm.doc.Pickup_Date = values.pickup_date;
			this.frm.doc.pickup_reason = values.pickup_reason;
			this.frm.doc.pickup_remark = values.pickup_remark;

			// Save the document before calling the server-side method
			// this.frm.save(() => {
				// Optionally, refresh the form to reflect the changes
				this.frm.refresh();

				// Now call the server-side method only after the user submits the pickup date
				this.callServerMethodForReadyForPickup(values);
			// });
		}, __('Ready for Pickup'));
	}

	callServerMethodForReadyForPickup(values) {
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.make_ready_for_pickup',
			args: {
				docname: this.frm.doc.name,
				technician_name: values.technician_name,
				technician_mobile: values.technician_mobile,
				technician_id: values.technician_id,
				pickup_date: values.pickup_date,
				pickup_reason: values.pickup_reason,
				pickup_remark: values.pickup_remark
			},
			callback: (response) => {
				// Handle the response from the server
				if (response.message) {
					// Display a success message
					frappe.msgprint({
						title: __('Success'),
						message: __('RentalSales Order is Ready for Pickup.'),
						indicator: 'green'
					});
					if (values.notify_through_whatsapp) {
						// Validate mobile number
						const mobile_no = values.mobile_no.replace(/\D/g, '');

						if (mobile_no.length !== 10) {
							frappe.msgprint({
								title: __('Invalid Mobile Number'),
								message: __('Please enter a valid 10-digit mobile number.'),
								indicator: 'red'
							});
							return;  // Stop execution if mobile number is invalid
						}
						this.send_whatsapp_message(values.mobile_no, values.message);
					}
					// Reload the entire page after a short delay (adjust as needed)
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			}
		});
	}

	make_pickedup() {
		let frm = this.frm;
		frappe.prompt([
			// {
			// 	fieldname: 'technician_name',
			// 	fieldtype: 'Link',
			// 	options: 'Technician Details',
			// 	label: 'Technician Name',
			// 	reqd: 1,
			// 	onchange: function() {
			// 		// Function to dynamically update technician mobile based on selected technician
			// 		var technicianName = this.value;
			// 		if (technicianName) {
			// 			frappe.call({
			// 				method: 'frappe.client.get_value',
			// 				args: {
			// 					doctype: 'Technician Details',
			// 					filters: { 'name': technicianName },
			// 					fieldname: ['mobile_number']
			// 				},
			// 				callback: function(response) {
			// 					if (response.message && response.message.mobile_number) {
			// 						// Set the value of technician mobile
			// 						cur_dialog.fields_dict.technician_mobile.set_input(response.message.mobile_number);
			// 					}
			// 				}
			// 			});
			// 		}
			// 	}
			// },
			// {
			// 	fieldname: 'technician_mobile',
			// 	fieldtype: 'Data',
			// 	label: 'Technician Mobile Number',
			// 	// reqd: 1
			// }
			{
				label: 'Pick Up Date and Time',
				fieldname: 'pickup_date',
				fieldtype: 'Datetime',
				default:'Now',
				reqd: 1
			},
			{
				label: __('Notify through whatsapp'),
				fieldname: 'notify_through_whatsapp',
				fieldtype: 'Check',
				default: 1
			},
			{
				label: __('Mobile No.'),
				fieldname: 'mobile_no',
				fieldtype: 'Data',
				default: frm.doc.customer_mobile_no,
				depends_on: 'eval:doc.notify_through_whatsapp',
				reqd: 1,  // Make field required
				description: __('Only 10 digits are allowed.Make sure Number Must be in WhatsApp'),
				on_change: (value) => {
					// Remove any non-numeric characters
					const numericValue = value.replace(/\D/g, '');
			
					// Check if the value has exactly 10 digits
					if (numericValue.length !== 10) {
						frappe.msgprint({
							title: __('Invalid Mobile Number'),
							message: __('Please enter a valid 10-digit mobile number. Only numbers are allowed.'),
							indicator: 'red'
						});
			
						// Optionally, clear the field or reset the value to numeric characters only
					} 
				}
			},
			
			{
				label: __('Message'),
				fieldname: 'message',
				fieldtype: 'Small Text',
				default: `Hello Sir/Mam
			
Patient Name: ${frm.doc.customer_name}
Equipment Name: ${frm.doc.items ? frm.doc.items.map(item => item.item_name).join(', ') : 'No items'}
			
We have successfully received the rental equipment at our office. Thank you for returning it on time.
If you have any questions, feel free to call/what's app us on 8884880013.`,
				depends_on: 'eval:doc.notify_through_whatsapp'
			},
			// Add more fields as needed
		], (values) => {
			// values will contain the entered data

			// Update RentalSales Order with the entered values
			this.frm.doc.pickup_date = values.pickup_date;
			// this.frm.doc.technician_mobile = values.technician_mobile;

			// Optionally, refresh the form to reflect the changes
			this.frm.refresh();

			// Now call the server-side method only after the user submits the technician details
			this.callServerMethodForPickedup(values);
		}, __('Picked Up'));
	}

	callServerMethodForPickedup(values) {
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.make_pickedup',
			args: {
				docname: this.frm.doc.name,
				pickup_date: values.pickup_date,
				// technician_mobile: values.technician_mobile
			},
			callback: (response) => {
				// Handle the response from the server
				if (response.message) {
					// Display a success message	
					frappe.msgprint({
						title: __('Success'),
						message: __('RentalSales Order is picked up.'),
						indicator: 'green'
					});
					if (values.notify_through_whatsapp) {
						// Validate mobile number
						const mobile_no = values.mobile_no.replace(/\D/g, '');

						if (mobile_no.length !== 10) {
							frappe.msgprint({
								title: __('Invalid Mobile Number'),
								message: __('Please enter a valid 10-digit mobile number.'),
								indicator: 'red'
							});
							return;  // Stop execution if mobile number is invalid
						}
						this.send_whatsapp_message(values.mobile_no, values.message);
					}
					// this.frm.save();
					// Reload the entire page after a short delay (adjust as needed)
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			}
		});
	}
	make_submitted_to_office() {
		frappe.prompt([
			{
				label: 'Submitted Date',
				fieldname: 'submitted_date',
				fieldtype: 'Datetime',
				default:'Now',
				reqd: 1
			}
			// Add more fields as needed
		], (values) => {
			// values will contain the entered data

			// Update RentalSales Order with the entered values
			this.frm.doc.submitted_date = values.submitted_date;
			// this.frm.doc.rental_device_id = values.device_id;

			// Optionally, refresh the form to reflect the changes
			this.frm.refresh();

			// Now call the server-side method only after the user submits the device details
			this.callServerMethodForSubmittedToOffice(values);
		}, __('Rental Device Details'));
	}

	callServerMethodForSubmittedToOffice(values) {
		const itemCodes = this.frm.doc.items.map(item => item.item_code);
		console.log(itemCodes)
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.make_submitted_to_office',
			args: {
				docname: this.frm.doc.name,
				item_code: itemCodes,  // Pass the array of item codes
				submitted_date: values.submitted_date
				// device_id: values.device_id
			},
			callback: (response) => {
				// Handle the response from the server
				if (response.message) {
					// Display a success message
					frappe.msgprint({
						title: __('Success'),
						message: __('Submitted to Office successfully.'),
						indicator: 'green'
					});
					// this.frm.save();
					// Reload the entire page after a short delay (adjust as needed)
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			}
		});
	}

	make_order_completed() {
		// Check security deposit and payment status before proceeding
		if (this.frm.doc.security_deposit_status === 'Paid' && this.frm.doc.payment_status === 'Paid' && this.frm.doc.refundable_security_deposit === 0) {
			// Show confirmation dialog
			frappe.confirm(__('Are you sure you want to complete this order? This action will lock the entire sales order, and you won’t be able to make any further transactions on it.'), () => {
				// User confirmed, proceed with creating the Sales Invoice first
				this.createSalesInvoiceWithAdvance();
			}, () => {
				// User cancelled, do nothing
				frappe.msgprint(__('Order completion cancelled.'));
			});
		} else {
			// Prepare an error message summarizing the issues
			let issues = [];
	
			// Check if the order type is 'Rental'
			if (this.frm.doc.order_type === 'Rental') {
				// For 'Rental' order type, check for all three conditions
				if (this.frm.doc.security_deposit_status !== 'Paid') {
					issues.push(__('Security Deposit is not paid.'));
				}
				if (this.frm.doc.payment_status !== 'Paid') {
					issues.push(__('Rental Payment is not paid.'));
				}
				if (this.frm.doc.refundable_security_deposit > 0) {
					issues.push(__('Refundable Security Deposit must be zero.'));
				}
			} else {
				// For other order types, only check for payment status
				if (this.frm.doc.payment_status !== 'Paid') {
					issues.push(__('Rental Payment is not paid.'));
				}
			}
	
			// Join the issues into a single message
			let issueMessage = issues.length > 0 ? `<span style="color: #000000;text-decoration: underline;font-weight: bold;font-style: italic;">${issues.join(' ')}</span>` : ''; // Using mild orange color
	
			// Show confirmation dialog with the issue message
			frappe.confirm(__('Are you sure you want to complete this order? This action will lock the entire sales order, and you won’t be able to make any further transactions on it. Issues: ' + issueMessage), () => {
				// User confirmed, proceed with creating the Sales Invoice first
				this.createSalesInvoiceWithAdvance();
			}, () => {
				// User cancelled, do nothing
				frappe.msgprint(__('Order completion cancelled.'));
			});
		}
	}
	
	
	
	createSalesInvoiceWithAdvance() {
		// Prepare arguments for creating the Sales Invoice
		const args = {
			allocate_advances_automatically: 1,
			source_name: this.frm.doc.name  // Pass the Sales Order name
		};
	
		// Call the server-side method directly to create the Sales Invoice
		frappe.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			args: args,
			callback: (response) => {
				// After creating the Sales Invoice, redirect to the Sales Order
				if (response && response.message) {
					// Lock the Sales Order
					// this.lockSalesOrder();
					
					// Redirect to the Sales Order form
					const salesOrderName = this.frm.doc.name; // Get the current Sales Order name
					frappe.set_route('Form', 'Sales Order', salesOrderName);
	
					// After the page loads, execute the completion method
					frappe.after_ajax(() => {
						this.callServerMethodForOrderCompleted();
					});
				} else {
					frappe.throw(__('Failed to create Sales Invoice.'));
				}
			}
		});
	}
	
	callServerMethodForOrderCompleted() {
		const itemCodes = this.frm.doc.items.map(item => item.item_code);
	
		frappe.call({
			method: 'erpnext.selling.doctype.sales_order.sales_order.make_order_completed',
			args: {
				docname: this.frm.doc.name,
				item_code: itemCodes,  // Pass the array of item codes
			},
			callback: (response) => {
				if (response.message) {
					frappe.msgprint(__('Order completed successfully.'));
					setTimeout(() => {
						window.location.reload();
					}, 1000); // 1000 milliseconds = 1 second
				} else {
					frappe.throw(__('Failed to complete the order.'));
				}
			}
		});
	}
	
	// lockSalesOrder() {
	// 	// Lock all fields by making them read-only
	// 	Object.keys(this.frm.fields_dict).forEach(fieldname => {
	// 		// Make sure the field is not a button or a hidden field before setting it to read-only
	// 		if (!this.frm.fields_dict[fieldname].df.hidden && 
	// 			this.frm.fields_dict[fieldname].df.fieldtype !== 'Button') {
	// 			this.frm.set_df_property(fieldname, 'read_only', 1);
	// 		}
	// 	});
	
	// 	// Hide all buttons on the form
	// 	this.frm.page.set_primary_action(__(''), null); // Remove the primary action button
	// 	this.frm.page.clear_menu(); // Clears the menu where additional actions are located
	
	// 	// Optionally hide custom buttons if they are defined
	// 	if (this.frm.page.btn_primary) {
	// 		this.frm.page.btn_primary.hide(); // Hides primary action button
	// 	}
		
	// 	if (this.frm.page.btn_secondary) {
	// 		this.frm.page.btn_secondary.hide(); // Hides secondary buttons
	// 	}
	// }
	
	
	
	// make_order_completed() {
	// 	// Check security deposit and payment status before proceeding
	// 	if (this.frm.doc.security_deposit_status === 'Paid' && this.frm.doc.payment_status === 'Paid') {
	// 		// Proceed with creating the Sales Invoice first
	// 		this.createSalesInvoiceWithAdvance();
	// 	} else {
	// 		// Throw an error if either payment or security deposit is not paid
	// 		frappe.throw(__('Cannot complete order. Ensure both Security Deposit and Rental Payment are fully paid.'));
	// 	}
	// }
	
	// createSalesInvoiceWithAdvance() {
	// 	// Prepare arguments for creating the Sales Invoice
	// 	const args = {
	// 		allocate_advances_automatically: 1,
	// 		source_name: this.frm.doc.name  // Pass the Sales Order name
	// 	};
	
	// 	// Call the server-side method directly to create the Sales Invoice
	// 	frappe.call({
	// 		method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
	// 		args: args,
	// 		callback: (response) => {
	// 			// After creating the Sales Invoice, redirect to the Sales Order
	// 			if (response && response.message) {
	// 				// Redirect to the Sales Order form
	// 				const salesOrderName = this.frm.doc.name; // Get the current Sales Order name
	// 				frappe.set_route('Form', 'Sales Order', salesOrderName);
					
	// 				// After the page loads, execute the completion method
	// 				frappe.after_ajax(() => {
	// 					this.callServerMethodForOrderCompleted();
	// 				});
	// 			} else {
	// 				frappe.throw(__('Failed to create Sales Invoice.'));
	// 			}
	// 		}
	// 	});
	// }
	
	// callServerMethodForOrderCompleted() {
	// 	const itemCodes = this.frm.doc.items.map(item => item.item_code);
	
	// 	frappe.call({
	// 		method: 'erpnext.selling.doctype.sales_order.sales_order.make_order_completed',
	// 		args: {
	// 			docname: this.frm.doc.name,
	// 			item_code: itemCodes,  // Pass the array of item codes
	// 		},
	// 		callback: (response) => {
	// 			if (response.message) {
	// 				frappe.msgprint(__('Order completed successfully.'));
	// 				setTimeout(() => {
	// 					window.location.reload();
	// 				}, 1000); // 1000 milliseconds = 1 second
	// 			} else {
	// 				frappe.throw(__('Failed to complete the order.'));
	// 			}
	// 		}
	// 	});
	// }
	
	
	
	
	

	make_maintenance_schedule() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_schedule",
			frm: this.frm,
		});
	}

	make_project() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_project",
			frm: this.frm,
		});
	}

	make_inter_company_order() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_inter_company_purchase_order",
			frm: this.frm,
		});
	}

	make_maintenance_visit() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_visit",
			frm: this.frm,
		});
	}

	make_purchase_order() {
		let pending_items = this.frm.doc.items.some((item) => {
			let pending_qty = flt(item.stock_qty) - flt(item.ordered_qty);
			return pending_qty > 0;
		});
		if (!pending_items) {
			frappe.throw({
				message: __("Purchase Order already created for all Sales Order items"),
				title: __("Note"),
			});
		}

		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Select Items"),
			size: "large",
			fields: [
				{
					fieldtype: "Check",
					label: __("Against Default Supplier"),
					fieldname: "against_default_supplier",
					default: 0,
				},
				{
					fieldname: "items_for_po",
					fieldtype: "Table",
					label: "Select Items",
					fields: [
						{
							fieldtype: "Data",
							fieldname: "item_code",
							label: __("Item"),
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldtype: "Data",
							fieldname: "item_name",
							label: __("Item name"),
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldtype: "Float",
							fieldname: "pending_qty",
							label: __("Pending Qty"),
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldtype: "Link",
							read_only: 1,
							fieldname: "uom",
							label: __("UOM"),
							in_list_view: 1,
						},
						{
							fieldtype: "Data",
							fieldname: "supplier",
							label: __("Supplier"),
							read_only: 1,
							in_list_view: 1,
						},
					],
				},
			],
			primary_action_label: "Create Purchase Order",
			primary_action(args) {
				if (!args) return;

				let selected_items = dialog.fields_dict.items_for_po.grid.get_selected_children();
				if (selected_items.length == 0) {
					frappe.throw({
						message: "Please select Items from the Table",
						title: __("Items Required"),
						indicator: "blue",
					});
				}

				dialog.hide();

				var method = args.against_default_supplier
					? "make_purchase_order_for_default_supplier"
					: "make_purchase_order";
				return frappe.call({
					method: "erpnext.selling.doctype.sales_order.sales_order." + method,
					freeze_message: __("Creating Purchase Order ..."),
					args: {
						source_name: me.frm.doc.name,
						selected_items: selected_items,
					},
					freeze: true,
					callback: function (r) {
						if (!r.exc) {
							if (!args.against_default_supplier) {
								frappe.model.sync(r.message);
								frappe.set_route("Form", r.message.doctype, r.message.name);
							} else {
								frappe.route_options = {
									sales_order: me.frm.doc.name,
								};
								frappe.set_route("List", "Purchase Order");
							}
						}
					},
				});
			},
		});

		dialog.fields_dict["against_default_supplier"].df.onchange = () => set_po_items_data(dialog);

		function set_po_items_data(dialog) {
			var against_default_supplier = dialog.get_value("against_default_supplier");
			var items_for_po = dialog.get_value("items_for_po");

			if (against_default_supplier) {
				let items_with_supplier = items_for_po.filter((item) => item.supplier);

				dialog.fields_dict["items_for_po"].df.data = items_with_supplier;
				dialog.get_field("items_for_po").refresh();
			} else {
				let po_items = [];
				me.frm.doc.items.forEach((d) => {
					let ordered_qty = me.get_ordered_qty(d, me.frm.doc);
					let pending_qty = (flt(d.stock_qty) - ordered_qty) / flt(d.conversion_factor);
					if (pending_qty > 0) {
						po_items.push({
							doctype: "Sales Order Item",
							name: d.name,
							item_name: d.item_name,
							item_code: d.item_code,
							pending_qty: pending_qty,
							uom: d.uom,
							supplier: d.supplier,
						});
					}
				});

				dialog.fields_dict["items_for_po"].df.data = po_items;
				dialog.get_field("items_for_po").refresh();
			}
		}

		set_po_items_data(dialog);
		dialog.get_field("items_for_po").grid.only_sortable();
		dialog.get_field("items_for_po").refresh();
		dialog.wrapper.find(".grid-heading-row .grid-row-check").click();
		dialog.show();
	}

	get_ordered_qty(item, so) {
		let ordered_qty = item.ordered_qty;
		if (so.packed_items && so.packed_items.length) {
			// calculate ordered qty based on packed items in case of product bundle
			let packed_items = so.packed_items.filter((pi) => pi.parent_detail_docname == item.name);
			if (packed_items && packed_items.length) {
				ordered_qty = packed_items.reduce((sum, pi) => sum + flt(pi.ordered_qty), 0);
				ordered_qty = ordered_qty / packed_items.length;
			}
		}
		return ordered_qty;
	}

	hold_sales_order() {
		var me = this;
		var d = new frappe.ui.Dialog({
			title: __("Reason for Hold"),
			fields: [
				{
					fieldname: "reason_for_hold",
					fieldtype: "Text",
					reqd: 1,
				},
			],
			primary_action: function () {
				var data = d.get_values();
				frappe.call({
					method: "frappe.desk.form.utils.add_comment",
					args: {
						reference_doctype: me.frm.doctype,
						reference_name: me.frm.docname,
						content: __("Reason for hold:") + " " + data.reason_for_hold,
						comment_email: frappe.session.user,
						comment_by: frappe.session.user_fullname,
					},
					callback: function (r) {
						if (!r.exc) {
							me.update_status("Hold", "On Hold");
							d.hide();
						}
					},
				});
			},
		});
		d.show();
	}
	close_sales_order() {
		this.frm.cscript.update_status("Close", "Closed");
	}
	update_status(label, status) {
		var doc = this.frm.doc;
		var me = this;
		frappe.ui.form.is_saving = true;
		frappe.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.update_status",
			args: { status: status, name: doc.name },
			callback: function (r) {
				me.frm.reload_doc();
			},
			always: function () {
				frappe.ui.form.is_saving = false;
			},
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.selling.SalesOrderController({ frm: cur_frm }));
function getSerialNumbers(itemCode) {
    // Define a variable to hold the options
    let options = [];

    // Call Python function to get serial numbers
    frappe.call({
        method: 'erpnext.selling.doctype.sales_order.sales_order.get_serial_numbers',
        args: {
            item_code: itemCode
        },
        async: false, // Ensure synchronous execution
        callback: function(response) {
            if (response.message) {
                // Map the serial numbers to the required format
                options = response.message.map(serialNumber => {
                    return {
                        label: serialNumber,
                        value: serialNumber
                    };
                });
            } else {
                console.error('Failed to fetch serial numbers');
            }
        }
    });

    // Return the options
    return options;
}
function update_sales_order_serial_numbers(sales_order_name, delivery_note_name) {
	frappe.call({
		method: 'erpnext.selling.doctype.sales_order.sales_order.update_sales_order_with_serial_numbers',
		args: {
			sales_order_name: sales_order_name,
			delivery_note_name: delivery_note_name
		},
		callback: function(response) {
			if (response.message) {
				frappe.msgprint({
					title: __('Serial Numbers Updated'),
					message: __('Serial numbers have been updated in the Sales Order.'),
					indicator: 'blue'
				});
			} else {
				frappe.msgprint({
					title: __('Error'),
					message: __('Failed to update serial numbers in the Sales Order.'),
					indicator: 'red'
				});
			}
		}
	});
}
