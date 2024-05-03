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
                            frappe.confirm(
                                __('Are you sure you want to approve. It will Reserve the Item?'),
                                () => {
                                    me.make_approved(); // Call the JavaScript method
                                },
                                () => {
                                    // Do nothing on cancel
                                }
                            );
                        }, __('Action'));
                    }

					if (flt(doc.per_billed, 2) < 100 && doc.status === 'Pending' && doc.order_type === 'Sales') {
                        this.frm.add_custom_button(__('Approved'), () => {
                            frappe.confirm(
                                __('Are you sure you want to approve. It will Reserve the Item?'),
                                () => {
                                    me.make_sales_approved(); // Call the JavaScript method
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

                    if (flt(doc.per_billed, 2) < 100 && doc.status === 'Active' && doc.order_type === 'Rental') {
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
					if (flt(doc.per_billed, 2) < 100 && doc.status === 'Ready for Pickup' && doc.order_type === 'Rental') {
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
					if (flt(doc.per_billed, 2) < 100 && doc.status === 'Picked Up' && doc.order_type === 'Rental') {
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
					// delivery note
					// if (
					// 	flt(doc.per_delivered, 2) < 100 &&
					// 	(order_is_a_sale || order_is_a_custom_sale) &&
					// 	allow_delivery
					// ) {
					// 	this.frm.add_custom_button(
					// 		__("Delivery Note"),
					// 		() => this.make_delivery_note_based_on_delivery_date(true),
					// 		__("Action")
					// 	);
					// 	this.frm.add_custom_button(
					// 		__("Work Order"),
					// 		() => this.make_work_order(),
					// 		__("Action")
					// 	);
					// }

					// sales invoice
					if (flt(doc.per_billed, 2) < 100 && doc.status != 'RENEWED') {
						this.frm.add_custom_button(
							__("Sales Invoice"),
							() => me.make_sales_invoice(),
							__("Action")
						);
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

	make_approved() {
        frappe.call({
            method: 'erpnext.selling.doctype.sales_order.sales_order.make_approved',
            args: {
                docname: this.frm.doc.name,
            },
            callback: (response) => {
                // Handle the response
                if (response.message === true) {
                    // Log the result to the console
                    console.log(response.message);
    
                    // Display a success message
                    frappe.msgprint({
                        title: __('Success'),
                        message: __('Rental Sales Order Approved successfully.'),
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

	make_sales_approved() {
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
	
		frappe.prompt([
			{
				fieldname: 'technician_name',
				fieldtype: 'Link',
				options: 'Technician Details',
				label: 'Technician Name',
				reqd: 1,
				onchange: function() {
					// Function to dynamically update technician mobile based on selected technician
					var technicianName = this.value;
					if (technicianName) {
						frappe.call({
							method: 'frappe.client.get_value',
							args: {
								doctype: 'Technician Details',
								filters: { 'name': technicianName },
								fieldname: ['mobile_number']
							},
							callback: function(response) {
								if (response.message && response.message.mobile_number) {
									// Set the value of technician mobile
									cur_dialog.fields_dict.technician_mobile.set_input(response.message.mobile_number);
								}
							}
						});
					}
				}
			},
			{
				fieldname: 'technician_mobile',
				fieldtype: 'Data',
				label: 'Technician Mobile Number',
				reqd: 1
			}
		], function(values) {
			var technicianName = values.technician_name;
			var technicianMobile = values.technician_mobile;
	
			// Call the Python function passing the technician details
			frappe.call({
				method: 'erpnext.selling.doctype.sales_order.sales_order.make_ready_for_delivery', // Change to your actual module, doctype, and file name
				args: {
					docname: me.frm.doc.name, // Use me.frm.doc.name instead of this.frm.doc.name
					technician_name: technicianName,
					technician_mobile: technicianMobile
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
				depends_on: 'eval:doc.payment_status == "UnPaid" || doc.payment_status == "Partially Paid"',
				mandatory_depends_on: 'eval:doc.payment_status == "UnPaid" || doc.payment_status == "Partially Paid"'
			},
			{
				label: 'Notes',
				fieldname: 'notes',
				fieldtype: 'Small Text',
				depends_on: 'eval:doc.payment_status == "UnPaid" || doc.payment_status == "Partially Paid"',
				// mandatory_depends_on: 'eval:doc.mode_of_payment == "Bank Draft" || doc.mode_of_payment == "Cheque"'
			},
			{
				label: 'Rental Order Agreement Attachment',
				fieldname: 'rental_order_agreement_attachment',
				fieldtype: 'Attach',
				reqd: 1
			},
			{
				label: 'Aadhar Card Attachment',
				fieldname: 'aadhar_card_attachment',
				fieldtype: 'Attach',
				reqd: 1
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

					// Reload the entire page after a short delay (adjust as needed)
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			}
		});
	}
	make_ready_for_pickup() {
		frappe.prompt([
			{
				fieldname: 'technician_name',
				fieldtype: 'Link',
				options: 'Technician Details',
				label: 'Technician Name',
				// reqd: 1,
				onchange: function() {
					// Function to dynamically update technician mobile based on selected technician
					var technicianName = this.value;
					if (technicianName) {
						frappe.call({
							method: 'frappe.client.get_value',
							args: {
								doctype: 'Technician Details',
								filters: { 'name': technicianName },
								fieldname: ['mobile_number']
							},
							callback: function(response) {
								if (response.message && response.message.mobile_number) {
									// Set the value of technician mobile
									cur_dialog.fields_dict.technician_mobile.set_input(response.message.mobile_number);
								}
							}
						});
					}
				}
			},
			{
				fieldname: 'technician_mobile',
				fieldtype: 'Data',
				label: 'Technician Mobile Number',
				// reqd: 1
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
				options: 'Patient recovered\nPatient Expired\nPurchased Device from Us\nPurchased Device from Others\nOther Reason',
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

					// Reload the entire page after a short delay (adjust as needed)
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			}
		});
	}

	make_pickedup() {
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
			}
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
